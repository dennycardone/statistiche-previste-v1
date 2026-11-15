"""Basket · funzioni comuni ai test (15/11/2026): lettura dell'archivio (ramo basket), filtri, modello delle squadre di Prevista
(lo stesso di modello.py / pubblica.py: ritmo × attacco/difesa ogni 100 possessi, DP 0,97, K 6, LD 0,998), periodi dell'harness.
Ogni previsione usa solo le partite precedenti."""
import json, glob, os, math, collections
SCELTA, VERIFICA = "2024-06-30", "2025-06-30"
def per(d): return "scelta" if d <= SCELTA else "verifica" if d <= VERIFICA else "holdout"
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
# NBA: le partite di preseason sono nello stesso file della stagione (stessa API). Inizio della stagione regolare (data UTC della prima partita)
NBA_START = {"2019-2020": "2019-10-23", "2020-2021": "2020-12-23", "2021-2022": "2021-10-19", "2022-2023": "2022-10-18",
             "2023-2024": "2023-10-24", "2024-2025": "2024-10-22", "2025-2026": "2025-10-21", "2026-2027": "2026-10-20"}

NUOVO_FORMATO = "2026-01-05"   # dall'8/1/2026 API-Basketball passa i tiri dal campo solo da 2 e i rimbalzi offensivi vuoti

def possessi(rows, fix=True, filt=None):
    filt = fix if filt is None else filt
    """possessi per squadra: FGA − OREB + TOV + 0,44·FTA. fix=True (15/11/2026): con il formato nuovo FGA = tiri da 2 + tiri da 3 e,
    quando mancano i rimbalzi offensivi, OREB = rimbalzi totali × quota offensiva del campionato (media mobile point-in-time).
    fix=False: com'era (senza rimbalzi offensivi niente possessi → ripiego su punti / rendimento)."""
    Q = collections.defaultdict(lambda: [0.0, 0.0])
    for r in sorted(rows, key=lambda r: (r["t"], r["id"])):
        q = Q[r["lg"]]
        for k, x in (("qph", r["sh"]), ("qpa", r["sa"])):
            r[k] = None
            if not x or None in (x[1], x[12], x[5]): continue
            if x[7] is not None:
                r[k] = x[1] - x[7] + x[12] + 0.44 * x[5]
                if x[6]: q[0] = q[0] * 0.998 + 1; q[1] = q[1] * 0.998 + x[7] / x[6]
            elif fix and x[6] and q[0] > 20:
                fga = x[1] + (x[3] or 0) if r["d"] >= NUOVO_FORMATO else x[1]
                r[k] = fga - q[1] / q[0] * x[6] + x[12] + 0.44 * x[5]
        # 15/11/2026: statistiche rotte (tiri o rimbalzi a zero o a centinaia, partite a metà): possessi buttati se i punti ogni 100 possessi
        # escono da 70-160 o se le due squadre differiscono di oltre il 12% (in una partita i possessi delle due squadre sono quasi uguali)
        if filt and r["qph"] and r["qpa"]:
            m_ = (r["qph"] + r["qpa"]) / 2
            if not (70 < 100 * r["ph"] / r["qph"] < 160 and 70 < 100 * r["pa"] / r["qpa"] < 160) or abs(r["qph"] - r["qpa"]) / m_ > 0.12: r["qph"] = r["qpa"] = None
    return rows

def load(DIR, preseason=False, fix=True, filt=None):
    """righe ordinate per data: dict con lega, stagione, data, id, h, a, ph, pa, qh/qa (quarti), stat h/a (S), gioc (lista), possessi"""
    rows = []
    for fn in sorted(glob.glob(os.path.join(DIR, "*.json"))):
        D = json.load(open(fn))
        lg, ss = D["lega"], D["stagione"]
        for gid, v in D["partite"].items():
            if v[1] not in ("FT", "AOT"): continue
            h, a = v[4], v[5]
            if not h or not a or h[5] is None or a[5] is None: continue
            if lg == "NBA" and not preseason and v[0][:10] < NBA_START.get(ss, "0000"): continue
            if not all(z is not None for z in h[:4] + a[:4]): continue
            if h[5] + a[5] < 100: continue
            S = D["stat"].get(gid) or {}
            def poss(x): return None if not x or None in (x[1], x[7], x[12], x[5]) else x[1] - x[7] + x[12] + 0.44 * x[5]
            rows.append(dict(lg=lg, ss=ss, d=v[0][:10], t=v[0], id=gid, h=v[2], a=v[3], ph=h[5], pa=a[5], qh=h[:5], qa=a[:5],
                             sh=S.get("h"), sa=S.get("a"), gi=D["gioc"].get(gid), qph=poss(S.get("h")), qpa=poss(S.get("a")),
                             po=v[6] is not None and not str(v[6]).isdigit() and "Season" not in str(v[6])))
    # All-Star e amichevoli: squadre con poche partite nella stagione (soglia relativa, come modello.py)
    cnt = collections.Counter()
    for r in rows: cnt[(r["lg"], r["ss"], r["h"])] += 1; cnt[(r["lg"], r["ss"], r["a"])] += 1
    med = collections.defaultdict(list)
    for (l_, s_, t_), n_ in cnt.items(): med[(l_, s_)].append(n_)
    THR = {k: min(15, max(2, sorted(v)[len(v) // 2] / 2)) for k, v in med.items()}
    rows = [r for r in rows if cnt[(r["lg"], r["ss"], r["h"])] >= THR[(r["lg"], r["ss"])] and cnt[(r["lg"], r["ss"], r["a"])] >= THR[(r["lg"], r["ss"])]]
    rows.sort(key=lambda r: (r["t"], r["id"]))
    return possessi(rows, fix, filt)

def team_model(rows, DP=0.97, K=6.0, LD=0.998, extra=None):
    """aggiunge a ogni riga (dalla 31ª partita del campionato) eh, ea (punti attesi), pace (possessi attesi), nh, na (partite della squadra),
    habh, haba (punti abituali della squadra: media mobile dei punti fatti), pch, pca (ritmo abituale)."""
    T = collections.defaultdict(lambda: {"n": 0.0, "pace": 0.0, "off": 0.0, "dfn": 0.0, "pts": 0.0})
    L = collections.defaultdict(lambda: {"n": 0.0, "pace": 0.0, "rtg": 0.0, "hca": 0.0})
    for r in rows:
        lg, h, a, ph, pa = r["lg"], r["h"], r["a"], r["ph"], r["pa"]
        Lg = L[lg]; r["eh"] = None
        if Lg["n"] >= 30:
            lp, lr, hca = Lg["pace"] / Lg["n"], Lg["rtg"] / Lg["n"], Lg["hca"] / Lg["n"]
            th, ta = T[(lg, h)], T[(lg, a)]
            def sh(t, k, base): return (t[k] + K * base) / (t["n"] + K)
            pace = sh(th, "pace", lp) * sh(ta, "pace", lp) / lp
            r.update(eh=pace * sh(th, "off", lr) * sh(ta, "dfn", lr) / lr / 100 + hca / 2, ea=pace * sh(ta, "off", lr) * sh(th, "dfn", lr) / lr / 100 - hca / 2,
                     pace=pace, lp=lp, lr=lr, hca=hca, nh=th["n"], na=ta["n"], habh=sh(th, "pts", lp * lr / 100), haba=sh(ta, "pts", lp * lr / 100),
                     pch=sh(th, "pace", lp), pca=sh(ta, "pace", lp))
        P = (r["qph"] + r["qpa"]) / 2 if r["qph"] and r["qpa"] else None
        if P is None and Lg["n"] > 0: P = (ph + pa) / 2 / (Lg["rtg"] / Lg["n"] / 100)
        if P is None: P = (ph + pa) / 2 / 1.1
        r["P"] = P
        for t, pf, pa_ in ((T[(lg, h)], ph, pa), (T[(lg, a)], pa, ph)):
            for k in ("n", "pace", "off", "dfn", "pts"): t[k] *= DP
            t["n"] += 1; t["pace"] += P; t["off"] += 100 * pf / P; t["dfn"] += 100 * pa_ / P; t["pts"] += pf
        for k in ("n", "pace", "rtg", "hca"): Lg[k] *= LD
        Lg["n"] += 1; Lg["pace"] += P; Lg["rtg"] += 100 * (ph + pa) / 2 / P; Lg["hca"] += ph - pa
    return rows

def rob(x):
    import numpy as np
    x = np.array(x); return float(1.4826 * np.median(np.abs(x - np.median(x))))

def ll(p, y):
    p = min(max(p, 1e-6), 1 - 1e-6); return -(y * math.log(p) + (1 - y) * math.log(1 - p))
