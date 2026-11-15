"""Basket · modello e test walk-forward (15/11/2026). Solo dati dell'archivio (ramo basket), per ogni partita solo le partite precedenti.
Periodi come l'harness del calcio: scelta = stagioni fino al 30/6/2024, verifica = 2024-25, holdout = da luglio 2025.

Modello (per campionato):
  possessi di una squadra in partita  P = FGA − OREB + TOV + 0,44·FTA  (dalle statistiche di squadra; senza statistiche: punti / media punti per possesso)
  ritmo della squadra (possessi a partita), attacco e difesa = punti fatti / subiti ogni 100 possessi: medie mobili con peso DP a partita,
  ristrette verso la media del campionato con K partite fittizie; vantaggio del campo = media mobile (casa − ospite) del campionato.
  Attesi: possessi = ritmo_casa · ritmo_ospite / ritmo_campionato; punti casa = possessi · att_casa · dif_ospite / rend_campionato / 100 + HCA/2, ospite − HCA/2.
  Distribuzioni: scarto (casa − ospite) ~ Normale(atteso, σ_s), totale ~ Normale(atteso, σ_t); σ stimate nel periodo scelta per campionato.
  Mercati valutati: vittoria (supplementari compresi), totale Over sulla linea arrotondata ±(0..3)·5, handicap casa a −(scarto atteso arrotondato).
Riferimento: media del campionato (stessi possessi e rendimento per tutti) + vantaggio del campo.

Uso: python tools/basket/modello.py CARTELLA_ARCHIVIO [USCITA.json]"""
import json, glob, os, sys, math, collections
import numpy as np
DIR = sys.argv[1] if len(sys.argv) > 1 else "basket"; OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(DIR, "..", "basket_esito.json")
SCELTA, VERIFICA = "2024-06-30", "2025-06-30"
def per(d): return "scelta" if d <= SCELTA else "verifica" if d <= VERIFICA else "holdout"
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))

rows = []   # (lega, data, id, casa, ospite, ph, pa, possh, possa)
for fn in sorted(glob.glob(os.path.join(DIR, "*.json"))):
    D = json.load(open(fn))
    for gid, v in D["partite"].items():
        if v[1] not in ("FT", "AOT"): continue
        h, a = v[4], v[5]
        if not h or not a or h[5] is None or a[5] is None: continue
        S = D["stat"].get(gid) or {}
        def poss(x): return None if not x or None in (x[1], x[7], x[12], x[5]) else x[1] - x[7] + x[12] + 0.44 * x[5]
        ot = (h[4] or 0) + (a[4] or 0) > 0
        reg = (sum(z or 0 for z in h[:4]), sum(z or 0 for z in a[:4])) if all(z is not None for z in h[:4] + a[:4]) else (None, None)
        rows.append((D["lega"], v[0][:10], gid, v[2], v[3], h[5], a[5], poss(S.get("h")), poss(S.get("a")), ot, reg, D["stagione"]))
# 15/11: fuori le partite non di campionato vero (All-Star: squadre con meno di 15 partite nella stagione) e quelle interrotte o a tavolino
# (totale sotto 100 o quarti mancanti), che gonfiavano l'incertezza (Eurocup σ 33,6, Serie A 23,8).
cnt = collections.Counter()
for r in rows: cnt[(r[0], r[11], r[3])] += 1; cnt[(r[0], r[11], r[4])] += 1
def season_of(r): return r[11]
n0 = len(rows)
rows = [r for r in rows if cnt[(r[0], season_of(r), r[3])] >= 15 and cnt[(r[0], season_of(r), r[4])] >= 15 and r[5] + r[6] >= 100 and r[10][0] is not None]
print("tolte (All-Star, interrotte, tavolino)", n0 - len(rows))
rows.sort(key=lambda r: (r[1], r[2]))
print("partite finite", len(rows), dict(collections.Counter(r[0] for r in rows)))

def run(DP, K, KEEP=None):
    T = collections.defaultdict(lambda: {"n": 0.0, "pace": 0.0, "off": 0.0, "dfn": 0.0})
    L = collections.defaultdict(lambda: {"n": 0.0, "pace": 0.0, "rtg": 0.0, "hca": 0.0})
    out = []
    for lg, d, gid, h, a, ph, pa, qh, qa, ot, reg, _s in rows:
        Lg = L[lg]
        if Lg["n"] >= 30:
            lp, lr, hca = Lg["pace"] / Lg["n"], Lg["rtg"] / Lg["n"], Lg["hca"] / Lg["n"]
            th, ta = T[(lg, h)], T[(lg, a)]
            def sh(t, k, base): return (t[k] + K * base) / (t["n"] + K)
            pace = sh(th, "pace", lp) * sh(ta, "pace", lp) / lp
            eh = pace * sh(th, "off", lr) * sh(ta, "dfn", lr) / lr / 100 + hca / 2
            ea = pace * sh(ta, "off", lr) * sh(th, "dfn", lr) / lr / 100 - hca / 2
            b = lp * lr / 100
            out.append((lg, d, gid, eh, ea, b + hca / 2, b - hca / 2, ph, pa, th["n"], ta["n"], ot, reg))
        # aggiornamento
        P = (qh + qa) / 2 if qh and qa else None
        if P is None and Lg["n"] > 0: P = (ph + pa) / 2 / (Lg["rtg"] / Lg["n"] / 100)
        if P is None: P = (ph + pa) / 2 / 1.1
        for t, pf, pa_ in ((T[(lg, h)], ph, pa), (T[(lg, a)], pa, ph)):
            for k in ("n", "pace", "off", "dfn"): t[k] *= DP
            t["n"] += 1; t["pace"] += P; t["off"] += 100 * pf / P; t["dfn"] += 100 * pa_ / P
        for k in ("n", "pace", "rtg", "hca"): Lg[k] *= 0.998
        Lg["n"] += 1; Lg["pace"] += P; Lg["rtg"] += 100 * (ph + pa) / 2 / P; Lg["hca"] += ph - pa
    return out

def ll(p, y): p = min(max(p, 1e-6), 1 - 1e-6); return -(y * math.log(p) + (1 - y) * math.log(1 - p))
def evaluate(out, sig, which="m"):
    """log-loss medio di vittoria, totale (linee ±0,5 ... ±15,5 attorno all'atteso) e handicap per periodo"""
    R = collections.defaultdict(lambda: collections.defaultdict(list))
    for lg, d, gid, eh, ea, bh, ba, ph, pa, nh, na, ot, reg in out:
        if nh < 5 or na < 5: continue
        ss, st = sig[lg]
        for nm, (xh, xa) in (("m", (eh, ea)), ("rif", (bh, ba))):
            if which != "all" and nm != which: continue
            ms, mt = xh - xa, xh + xa
            pw = Phi(ms / ss)
            R[nm][(per(d), "vittoria")].append(ll(pw, 1 if ph > pa else 0))
            Lt = round((eh + ea)) + 0.5   # linea comune (dal modello) per entrambi
            for off in (-10, -5, 0, 5, 10):
                L_ = Lt + off; R[nm][(per(d), "totale")].append(ll(1 - Phi((L_ - mt) / st), 1 if ph + pa > L_ else 0))
            Ls = -round(eh - ea) + 0.5   # handicap casa (es. −6,5)
            R[nm][(per(d), "handicap")].append(ll(1 - Phi((-Ls - ms) / ss), 1 if ph - pa > -Ls else 0))
    return R

def sigmas(out):
    S = {}
    by = collections.defaultdict(lambda: ([], []))
    for lg, d, gid, eh, ea, bh, ba, ph, pa, nh, na, ot, reg in out:
        if d <= SCELTA and nh >= 5 and na >= 5: by[lg][0].append((ph - pa) - (eh - ea)); by[lg][1].append((ph + pa) - (eh + ea))
    rob = lambda x: float(1.4826 * np.median(np.abs(np.array(x) - np.median(x))))   # robusta: i casi estremi non la gonfiano
    for lg, (s, t) in by.items(): S[lg] = (rob(s) or 12.0, rob(t) or 18.0)
    return S

best = None
for DP in (0.93, 0.95, 0.96, 0.97, 0.98):
    for K in (1.0, 3.0, 6.0):
        o = run(DP, K); sg = sigmas(o); R = evaluate(o, sg)
        sc = sum(np.mean(v) for (p, mk), v in R["m"].items() if p == "scelta")
        print(f"DP {DP} K {K}: log-loss somma nel periodo scelta {sc:.4f}")
        if best is None or sc < best[0]: best = (sc, DP, K)
_, DP, K = best
o = run(DP, K); sg = sigmas(o); R = evaluate(o, sg, "all")
res = {"parametri": {"DP": DP, "K": K}, "sigma": sg, "periodi": {}}
for p in ("scelta", "verifica", "holdout"):
    for mk in ("vittoria", "totale", "handicap"):
        m, r = R["m"].get((p, mk), []), R["rif"].get((p, mk), [])
        if m: res["periodi"][f"{p} · {mk}"] = {"n": len(m), "modello": round(float(np.mean(m)), 4), "riferimento": round(float(np.mean(r)), 4), "diff": round(float(np.mean(m) - np.mean(r)), 4)}
# errore medio dei punti attesi e calibrazione della vittoria (holdout)
mae = collections.defaultdict(list); cal = collections.defaultdict(lambda: [0, 0.0, 0])
for lg, d, gid, eh, ea, bh, ba, ph, pa, nh, na, ot, reg in o:
    if nh < 5 or na < 5: continue
    mae[(lg, per(d))].append(abs(ph + pa - eh - ea))
    if per(d) == "holdout":
        pw = Phi((eh - ea) / sg[lg][0]); b = min(9, int(pw * 10)); c = cal[b]; c[0] += 1; c[1] += pw; c[2] += ph > pa
res["errore_totale"] = {f"{lg} {p}": round(float(np.mean(v)), 2) for (lg, p), v in sorted(mae.items())}
res["calibrazione_vittoria_holdout"] = [(round(c[1] / c[0], 3), round(c[2] / c[0], 3), c[0]) for b, c in sorted(cal.items()) if c[0]]
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps(res, indent=1)[:4000])
for k, v in res["periodi"].items():
    print(f"::notice title=Basket · {k}::modello {v['modello']} · riferimento {v['riferimento']} · differenza {v['diff']:+.4f} · {v['n']} casi")
