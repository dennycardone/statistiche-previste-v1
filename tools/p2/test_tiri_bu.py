"""Prevista 2.0 · tiri e tiri in porta costruiti dal basso con la formazione ufficiale (28/10/2026, richiesta di Denny).

Per ogni partita, con le sole partite precedenti (point-in-time):
  tiri attesi dal basso di una squadra = somma sui titolari di (tiri ogni 90' del giocatore × minuti attesi / 90)
                                         + tiri abituali dei subentrati della squadra
  - tiri ogni 90' del giocatore: somme decadute (peso DP a partita) ristrette verso la media del suo ruolo con K×90 minuti fittizi
    (chi ha giocato poco pesa poco: shrinkage)
  - minuti attesi: media decaduta dei minuti giocati quando parte titolare (ristretta verso la media del ruolo), al massimo 90
  - subentrati: media decaduta per partita dei tiri dei non titolari della squadra
  Lo stesso per i tiri in porta.
Modello: valore atteso dell'app × e^(b·x) con x = ln(tiri dal basso / valore atteso dell'app): b = 0 è il modello attuale, b = 1 il
solo modello dal basso; b stimato mese per mese sulle sole partite precedenti (harness.walk_forward). 1X2 "chi ne fa di più" con le
stesse distribuzioni dell'app (harness.h2h). Scelta di K e della variante (minuti attesi o 90') sul periodo "scelta", giudizio su
verifica e holdout (harness.confronta, regola di adozione).
Dati: ricerca/form2 (ramo formazioni), ricerca/base (ramo ricerca). Uscita: ricerca/res_tiri_bu.json."""
import os, sys, json, glob, math, pickle, collections, datetime
import numpy as np, pandas as pd
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
P2 = os.environ.get("RICERCA", os.path.join(REPO, "ricerca"))
sys.path.insert(0, os.path.join(REPO, "tools")); import harness as H
log = lambda *a: print(*a, flush=True)
DP, DM = 0.97, 0.9
POS = {"G": 0, "D": 1, "M": 2, "F": 3}
FX = []
for fn in glob.glob(P2 + "/form2/*.json"):
    D = json.load(open(fn))
    if not isinstance(D.get("partite"), dict) or "lega" not in D: continue
    for fid, v in D["partite"].items(): FX.append((v[0], D["lega"], fid, v))
FX.sort()
log("partite nell'archivio formazioni", len(FX))

def build(K, use_min):
    """variabili dal basso per ogni partita: {(lg, data, casa API, ospite API, gol casa, gol ospite): {"h": {bu_sh, bu_sot}, "a": {...}}}"""
    pl = {}            # giocatore → [minuti, tiri, tiri in porta] decaduti
    mins = {}          # giocatore → [somma minuti da titolare decaduta, peso]
    role = {}
    G = np.full((4, 3), 1e-9)      # per ruolo: minuti, tiri, tiri in porta (prior)
    GM = np.full((4, 2), 1e-9)     # per ruolo: minuti da titolare, presenze da titolare
    bench = {}         # squadra → [tiri subentrati, tiri in porta subentrati, peso]
    OUT = {}
    def rate(pid):
        r = POS.get(role.get(pid, "M"), 2); g = G[r, 1:] / max(G[r, 0], 1e-9) * 90
        p = pl.get(pid)
        if p is None: return g
        return (p[1:] + K * g) / (p[0] / 90 + K)
    def emin(pid):
        if not use_min: return 90.0
        r = POS.get(role.get(pid, "M"), 2); gm = GM[r, 0] / max(GM[r, 1], 1e-9)
        m = mins.get(pid)
        if m is None: return gm
        return min(90.0, (m[0] + 3 * gm) / (m[1] + 3))
    for d, lg, fid, v in FX:
        _, hid, aid, hn, an, hg, ag, xh, xa, P = v
        if len(xh) >= 10 and len(xa) >= 10 and G[:, 0].sum() > 5e6:
            f = {}
            for side, tid, xi in (("h", hid, xh), ("a", aid, xa)):
                B = bench.get(tid)
                if B is None or B[2] < 3: f[side] = None; continue
                bu = sum(rate(p) * emin(p) / 90 for p in xi) + B[:2] / B[2]
                f[side] = {"bu_sh": float(bu[0]), "bu_sot": float(bu[1])}
            OUT[(lg, d[:10], hn, an, hg, ag)] = f
        # aggiornamento dopo la partita
        sub = {0: np.zeros(2), 1: np.zeros(2)}
        XI = {0: set(xh), 1: set(xa)}
        for r in P:
            pid, sd, mi = r[0], r[1], r[2] or 0
            if r[11]: role[pid] = r[11]
            x = np.array([mi, r[9] or 0, r[10] or 0], float)
            a = pl.setdefault(pid, np.zeros(3)); a *= DP; a += x
            rr = POS.get(role.get(pid, "M"), 2); G[rr] *= 0.9999; G[rr] += x
            if pid in XI.get(sd, ()):
                m = mins.setdefault(pid, [0.0, 0.0]); m[0] = m[0] * DM + mi; m[1] = m[1] * DM + 1
                GM[rr] *= 0.9999; GM[rr] += [mi, 1]
            elif mi > 0: sub[sd] += x[1:]
        for sd, tid in ((0, hid), (1, aid)):
            if len(XI[sd]) >= 10:
                b = bench.setdefault(tid, np.zeros(3)); b *= 0.9; b[:2] += sub[sd]; b[2] += 1
    return OUT

B = []
for fn in glob.glob(P2 + "/base/*.json"):
    lg = os.path.basename(fn)[:-5]
    for r in json.load(open(fn)): r["lg"] = lg; B.append(r)
log("previsioni dell'app (base)", len(B))
def mapper(FEAT):   # nomi API-Football → nomi dell'app: stessa data (±1) e stesso risultato, voto a maggioranza (come test1a.py)
    byk = collections.defaultdict(list)
    for k in FEAT: byk[(k[0], k[4], k[5])].append(k)
    votes = collections.defaultdict(collections.Counter)
    for r in B:
        if r["y"]["g"][0] is None: continue
        d0 = datetime.date.fromisoformat(r["d"])
        for k in byk.get((r["lg"], r["y"]["g"][0], r["y"]["g"][1]), []):
            if abs((datetime.date.fromisoformat(k[1]) - d0).days) <= 1: votes[(r["lg"], k[2])][r["h"]] += 1; votes[(r["lg"], k[3])][r["a"]] += 1
    MAP = {key: c.most_common(1)[0][0] for key, c in votes.items() if c.most_common(1)[0][1] >= 3}
    FK = {}
    for k, f in FEAT.items():
        h, a = MAP.get((k[0], k[2])), MAP.get((k[0], k[3]))
        if h and a: FK[(k[0], k[1], h, a)] = f
    return FK
def feat_of(FK, r):
    for dd in (0, -1, 1):
        f = FK.get((r["lg"], (datetime.date.fromisoformat(r["d"]) + datetime.timedelta(days=dd)).isoformat(), r["h"], r["a"]))
        if f: return f
    return None
POLD = {}
def evaluate(FK, k, var):
    rows = [(r, feat_of(FK, r)) for r in B]
    T = []
    for i, (r, f) in enumerate(rows):
        m = r.get(k); y = r["y"].get(k)
        if not m or y is None or y[0] is None or y[1] is None or not f or not f.get("h") or not f.get("a"): continue
        for side, j in (("h", 0), ("a", 1)):
            bu = f[side][var]; mu0 = m[j]
            if not (bu > 0 and mu0 > 0): continue
            T.append(dict(i=i, side=j, date=r["d"], lg=r["lg"], season=r["se"], mu0=mu0, y=y[j], x=math.log(bu / mu0)))
    T = pd.DataFrame(T)
    if not len(T): return None, None, 0
    rT = rows[T.i.iloc[0]][0][k][3]; rT = None if rT in (-1, None) else rT
    T2, coefs = H.walk_forward(T, ["x"], r=rT)
    P = []
    for i, g in T2.groupby("i"):
        if len(g) != 2 or g.mu.isna().any(): continue
        r = rows[i][0]; m = r[k]; y = r["y"][k]
        rt = None if m[2] in (-1, None) else m[2]; rT_ = float("inf") if m[3] == -1 else m[3]
        gh, ga = g[g.side == 0].iloc[0], g[g.side == 1].iloc[0]
        if (k, i) not in POLD: POLD[(k, i)] = H.h2h(m[0], m[1], rt, rT_, m[4] or 0.0)
        P.append(dict(date=r["d"], lg=r["lg"], season=r["se"], y=0 if y[0] > y[1] else 1 if y[0] == y[1] else 2, p_old=POLD[(k, i)],
                      p_new=H.h2h(gh.mu, ga.mu, rt, rT_, m[4] or 0.0)))
    last = list(coefs.items())[-1] if coefs else (None, [np.nan])
    return H.confronta(pd.DataFrame(P)), round(float(last[1][0]), 3), len(T)

REP = {}
for k, var, name in (("s", "bu_sh", "Tiri"), ("st", "bu_sot", "Tiri in porta")):
    best = None
    for K in (2.0, 5.0, 10.0):
        for use_min in (True, False):
            FK = mapper(build(K, use_min))
            res, b, n = evaluate(FK, k, var)
            if not res: continue
            sc = res.get("scelta", {}).get("diff", 9)
            log(f"{name} · K={K:g} · {'minuti attesi' if use_min else '90 minuti'}: righe {n} · peso b (ultimo mese) {b} · scelta {sc:+.5f}")
            if best is None or sc < best[0]: best = (sc, K, use_min, res, b)
    if best:
        sc, K, use_min, res, b = best
        lab = f"{name} dal basso (K={K:g}, {'minuti attesi' if use_min else '90 minuti'}, peso b={b})"
        REP[name] = dict(K=K, minuti_attesi=use_min, peso_b=b, **res)
        log(H.riepilogo(lab, res))
json.dump(REP, open(os.path.join(P2, "res_tiri_bu.json"), "w"), indent=1, default=float)
