"""Basket · test delle statistiche di squadra attese (16/11/2026, Denny): triple segnate, assist, palle perse (rimbalzi come riferimento).
Modello come i rimbalzi della Lettura: quante ne fa e ne concede di solito la squadra ogni 100 possessi (media mobile DP, ristretta verso il
campionato con K partite fittizie) × possessi attesi della partita (Prevista). Riferimento: media del campionato × possessi attesi.
Mercati: totale sopra/sotto linee attorno al riferimento, chi ne fa di più. Periodi e regola come l'harness.
Uso: python tools/basket/test_statistiche.py ARCHIVIO [USCITA.json]"""
import sys, os, json, math, collections
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from bk_lib import load, team_model, per, Phi, rob, ll, SCELTA
DIR = sys.argv[1]; OUT = sys.argv[2] if len(sys.argv) > 2 else "basket_statistiche.json"
rows = team_model(load(DIR, preseason=True, fix=True))
ST = {"triple": 2, "assist": 9, "palle perse": 12, "rimbalzi": 6}
OFFS = {"triple": (-3, -1.5, 0, 1.5, 3), "assist": (-4, -2, 0, 2, 4), "palle perse": (-3, -1.5, 0, 1.5, 3), "rimbalzi": (-4, -2, 0, 2, 4)}
def run(idx, DP, K):
    T = collections.defaultdict(lambda: [0.0, 0.0, 0.0]); L = collections.defaultdict(lambda: [0.0, 0.0]); out = []
    for r in rows:
        sh, sa = r["sh"], r["sa"]
        have = sh and sa and sh[idx] is not None and sa[idx] is not None and r["P"] and (idx != 12 or (sh[idx] > 0 and sa[idx] > 0))
        lg = r["lg"]
        if have and r["eh"] is not None and r["nh"] >= 5 and r["na"] >= 5 and L[lg][0] > 30 and T[(lg, r["h"])][0] >= 3 and T[(lg, r["a"])][0] >= 3:
            lr = L[lg][1] / L[lg][0]
            def g_(t, i): x = T[(lg, t)]; return (x[i] + K * lr) / (x[0] + K)
            eh = r["pace"] * (g_(r["h"], 1) + g_(r["a"], 2)) / 2 / 100; ea = r["pace"] * (g_(r["a"], 1) + g_(r["h"], 2)) / 2 / 100
            b = r["pace"] * lr / 100
            out.append((lg, r["d"], sh[idx], sa[idx], eh, ea, b))
        if have:
            for t, f_, a_ in ((r["h"], sh[idx], sa[idx]), (r["a"], sa[idx], sh[idx])):
                x = T[(lg, t)]; x[0] = x[0] * DP + 1; x[1] = x[1] * DP + 100 * f_ / r["P"]; x[2] = x[2] * DP + 100 * a_ / r["P"]
            x = L[lg]; x[0] = x[0] * 0.998 + 2; x[1] = x[1] * 0.998 + 100 * (sh[idx] + sa[idx]) / r["P"]
    return out
def evaluate(out, name):
    sig = {}
    for lg in set(o[0] for o in out):
        S = [o for o in out if o[0] == lg and o[1] <= SCELTA]
        if len(S) > 100: sig[lg] = (rob([o[2] + o[3] - o[4] - o[5] for o in S]), rob([o[2] - o[3] - o[4] + o[5] for o in S]), rob([o[2] + o[3] - 2 * o[6] for o in S]))
    R = collections.defaultdict(lambda: collections.defaultdict(list)); mae = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for lg, d, fh, fa, eh, ea, b in out:
        if lg not in sig: continue
        st, ss, sb = sig[lg]; p = per(d); L0 = round(2 * b) + 0.5
        for o in OFFS[name]:
            Lx = L0 + o; y = 1 if fh + fa > Lx else 0
            R[(p, "totale")][lg].append(ll(1 - Phi((Lx - eh - ea) / st), y) - ll(1 - Phi((Lx - 2 * b) / sb), y))
        if fh != fa:
            y = 1 if fh > fa else 0; R[(p, "chi ne fa di più")][lg].append(ll(Phi((eh - ea) / ss), y) - ll(0.5, y))
        m = mae[p]; m[0] += abs(fh + fa - eh - ea); m[1] += abs(fh + fa - 2 * b); m[2] += 1
    res = {}
    for p in ("scelta", "verifica", "holdout"):
        for mk in ("totale", "chi ne fa di più"):
            d = R[(p, mk)]
            if not d: continue
            a = np.concatenate(list(d.values()))
            res[f"{p} · {mk}"] = {"diff log-loss (modello − media)": round(float(a.mean()), 5), "z": round(float(a.mean() / (a.std() / math.sqrt(len(a)))), 2),
                                  "campionati migliorati": f"{sum(np.mean(v) < 0 for v in d.values())}/{len(d)}", "casi": len(a)}
        m = mae[p]
        if m[2]: res[f"{p} · errore medio del totale (modello / media)"] = f"{m[0]/m[2]:.2f} / {m[1]/m[2]:.2f}"
    return res, sum(np.mean(np.concatenate(list(R[("scelta", "totale")].values()))) for _ in [0])
RES = {}
for name, idx in ST.items():
    best = None
    for DP in (0.9, 0.95, 0.97, 0.99):
        for K in (3.0, 6.0, 12.0):
            r_, sc = evaluate(run(idx, DP, K), name)
            if best is None or sc < best[0]: best = (sc, DP, K, r_)
    RES[name] = {"parametri (DP, K)": [best[1], best[2]], **best[3]}
json.dump(RES, open(OUT, "w"), indent=1, ensure_ascii=False)
for name, r_ in RES.items():
    print(name, r_["parametri (DP, K)"])
    for k, v in r_.items():
        if "·" in k and "scelta" not in k: print("  ", k, v if isinstance(v, str) else (v["diff log-loss (modello − media)"], "z", v["z"], v["campionati migliorati"]))
