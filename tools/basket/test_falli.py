"""Basket · test dei falli di squadra attesi (15/11/2026, Denny). Harness come gli altri test basket.
Falli della partita: API-Basketball fino all'8/1/2026 (tutti i campionati) + archivio falli (ramo basket-falli: ESPN per NBA, sito Eurolega per EL/EC).
Modello: falli commessi attesi della squadra = media di (falli che commette di solito, falli che l'avversaria subisce di solito), medie mobili DP 0,97
ristrette verso il campionato con K partite fittizie, + metà del vantaggio casa/trasferta dei falli del campionato.
Riferimento: media del campionato (con lo stesso vantaggio del campo). Mercati valutati: falli totali sopra/sotto linee attorno all'atteso,
chi commette più falli. Uso: python tools/basket/test_falli.py ARCHIVIO [CARTELLA_FALLI] [USCITA.json]"""
import sys, os, json, math, collections
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from bk_lib import load, per, Phi, rob, ll, SCELTA
DIR = sys.argv[1]; FD = sys.argv[2] if len(sys.argv) > 2 and os.path.isdir(sys.argv[2]) else None
OUT = sys.argv[3] if len(sys.argv) > 3 else "basket_falli_test.json"
rows = load(DIR)
EXT = {}
if FD:
    import glob
    for fn in glob.glob(os.path.join(FD, "*.json")):
        for gid, v in json.load(open(fn))["partite"].items():
            if v["h"][0] is not None and v["a"][0] is not None: EXT[gid] = (v["h"][0], v["a"][0])
def fouls(r):
    if r["id"] in EXT: return EXT[r["id"]]
    if r["sh"] and r["sa"] and r["sh"][13] is not None and r["sa"][13] is not None and r["sh"][13] > 5 and r["sa"][13] > 5: return (r["sh"][13], r["sa"][13])
    return None
best = None; RES = {}
for K in (0.5, 1.0, 2.0, 4.0):
    for DP in (0.8, 0.85, 0.9, 0.93):
        T = collections.defaultdict(lambda: [0.0, 0.0, 0.0]); L = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
        out = []
        for r in rows:
            f = fouls(r)
            if not f: continue
            lg = r["lg"]; Lg = L[lg]
            if Lg[0] > 30:
                lf, lh = Lg[1] / Lg[0], Lg[2] / Lg[0]   # falli medi di una squadra, differenza casa − ospite
                def g_(t, i): x = T[(lg, t)]; return (x[i] + K * lf) / (x[0] + K)
                th, ta = T[(lg, r["h"])], T[(lg, r["a"])]
                if th[0] >= 3 and ta[0] >= 3:
                    eh = (g_(r["h"], 1) + g_(r["a"], 2)) / 2 + lh / 2; ea = (g_(r["a"], 1) + g_(r["h"], 2)) / 2 - lh / 2
                    out.append((lg, r["d"], f[0], f[1], eh, ea, lf + lh / 2, lf - lh / 2))
            for t, fc, fd in ((r["h"], f[0], f[1]), (r["a"], f[1], f[0])):
                x = T[(lg, t)]; x[0] = x[0] * DP + 1; x[1] = x[1] * DP + fc; x[2] = x[2] * DP + fd
            Lg[0] = Lg[0] * 0.998 + 1; Lg[1] = Lg[1] * 0.998 + (f[0] + f[1]) / 2; Lg[2] = Lg[2] * 0.998 + f[0] - f[1]
        sig = {}
        for lg in set(o[0] for o in out):
            S = [o for o in out if o[0] == lg and o[1] <= SCELTA]
            if len(S) > 100: sig[lg] = (rob([o[2] + o[3] - o[4] - o[5] for o in S]), rob([o[2] - o[3] - o[4] + o[5] for o in S]))
        R = collections.defaultdict(lambda: collections.defaultdict(list))
        for lg, d, fh, fa, eh, ea, bh, ba in out:
            if lg not in sig: continue
            st, ss = sig[lg]; p = per(d); L0 = round(bh + ba) + 0.5
            for o in (-4, -2, 0, 2, 4):
                Lx = L0 + o; y = 1 if fh + fa > Lx else 0
                R[(p, "totale")][lg].append(ll(1 - Phi((Lx - eh - ea) / st), y) - ll(1 - Phi((Lx - bh - ba) / st), y))
            if fh != fa:
                y = 1 if fh > fa else 0
                R[(p, "chi ne fa di più")][lg].append(ll(Phi((eh - ea) / ss), y) - ll(Phi((bh - ba) / ss), y))
            R[(p, "errore")][lg].append((abs(fh + fa - eh - ea), abs(fh + fa - bh - ba)))
        sc = np.mean(np.concatenate([v for v in R[("scelta", "totale")].values()]))
        RES[(K, DP)] = (R, sig)
        if best is None or sc < best[0]: best = (sc, K, DP)
_, K, DP = best; R, sig = RES[(K, DP)]
res = {"parametri": {"K": K, "DP": DP}, "partite_con_falli": sum(len(v) for v in R[("scelta", "errore")].values()) + sum(len(v) for v in R[("verifica", "errore")].values()) + sum(len(v) for v in R[("holdout", "errore")].values()),
       "sigma totale/scarto": {lg: [round(a, 2), round(b, 2)] for lg, (a, b) in sorted(sig.items())}}
for p in ("verifica", "holdout"):
    for mk in ("totale", "chi ne fa di più"):
        d = R[(p, mk)]
        if not d: continue
        a = np.concatenate(list(d.values()))
        res[f"{p} · {mk}"] = {"diff logloss (modello − media campionato)": round(float(a.mean()), 5), "z": round(float(a.mean() / (a.std() / math.sqrt(len(a)))), 2),
                              "campionati migliorati": f"{sum(np.mean(v) < 0 for v in d.values())}/{len(d)}", "per campionato": {lg: round(float(np.mean(v)), 4) for lg, v in sorted(d.items())}, "casi": len(a)}
    e = R[(p, "errore")]
    res[f"{p} · errore medio falli totali (modello / media)"] = {lg: f"{np.mean([x[0] for x in v]):.2f} / {np.mean([x[1] for x in v]):.2f} ({len(v)})" for lg, v in sorted(e.items())}
json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
