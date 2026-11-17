"""Gol attesi · fase 3, esperimento 1 (Denny): Dixon-Coles con rho stimato SOLO sulle partite precedenti, contro M0 (rho = 0).
Varianti: rho unico (tutti i campionati), rho per campionato, rho per campionato ristretto verso quello unico (k partite fittizie,
k scelto nel periodo scelta). Stima ripetuta all'inizio di ogni mese su tutte le partite giocate prima (finestra crescente), λ di M0."""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__)); from gol_eval import *
REPO = os.path.join(os.path.dirname(__file__), "..", "..")
df = pd.read_pickle(os.path.join(REPO, "ricerca", "gol", "feat.pkl")).sort_values(["d", "lg"]).reset_index(drop=True)
df["mese"] = df.date.dt.to_period("M")
months = sorted(df.mese.unique())
lgs = sorted(df.lg.unique())
RG, RL, NL = {}, {}, {}
for mo in months:
    prev = df[df.mese < mo]
    if len(prev) < 1000: RG[mo] = 0.0
    else: RG[mo] = fit_rho(prev.lh0, prev.la0, prev.yh, prev.ya)
    for lg in lgs:
        p = prev[prev.lg == lg]; NL[(mo, lg)] = len(p)
        RL[(mo, lg)] = fit_rho(p.lh0, p.la0, p.yh, p.ya) if len(p) >= 100 else 0.0
rg = df.mese.map(RG).values
rl = np.array([RL[(m, l)] for m, l in zip(df.mese, df.lg)]); nl = np.array([NL[(m, l)] for m, l in zip(df.mese, df.lg)])
X0 = metrics(df, df.lh0, df.la0)
res = {"rho unico (ultimo mese)": round(RG[months[-1]], 4), "rho unico a inizio verifica / holdout": [round(RG[pd.Period("2024-07", "M")], 4), round(RG[pd.Period("2025-07", "M")], 4)]}
V = {"unico": rg, "per campionato": rl}
# shrinkage: k scelto nel periodo scelta (log-loss del risultato esatto)
sc = (df.per == "scelta").values; best = None
for k in (100, 300, 1000, 3000, 10000):
    r = (nl * rl + k * rg) / (nl + k); X = metrics(df[sc], df.lh0[sc], df.la0[sc], r[sc])
    v = X.ll_score.mean(); res[f"scelta · ll risultato esatto con k={k}"] = round(v, 6)
    if best is None or v < best[0]: best = (v, k)
k = best[1]; V[f"ristretto (k={k})"] = (nl * rl + k * rg) / (nl + k); res["k scelto"] = k
OUT = {"M0 (rho 0)": summary(df, X0)}
for nm, r in V.items():
    X = metrics(df, df.lh0, df.la0, r); OUT[nm] = summary(df, X)
    res[nm] = {key: compare(df, X0, X, key) for key in ("ll_score", "ll_1x2", "br_1x2", "br_o25")}
    res[nm]["regola (ll risultato esatto)"] = rule(res[nm]["ll_score"])
    # per campionato in holdout e verifica
    d = (X.ll_score - X0.ll_score)
    res[nm]["per campionato verifica"] = {l: round(v, 5) for l, v in d[df.per == "verifica"].groupby(df.lg[df.per == "verifica"]).mean().items()}
json.dump({"confronti": res, "riepiloghi": OUT}, open(os.path.join(REPO, "ricerca", "gol", "exp1_dc.json"), "w"), indent=1, default=str, ensure_ascii=False)
def show(R):
    return " | ".join(f"{p[:3]} {R[p]['diff']:+.5f} [{R[p]['lo']:+.5f},{R[p]['hi']:+.5f}] {R[p]['pct']:+.2f}% {R[p]['camp']}" for p in ("scelta", "verifica", "holdout"))
for nm in V:
    print(f"\n== {nm}  (regola: {res[nm]['regola (ll risultato esatto)']})")
    for key in ("ll_score", "ll_1x2", "br_1x2", "br_o25"): print(f"  {key:9} {show(res[nm][key])}")
for nm, S in OUT.items():
    print(f"\n{nm}: " + " · ".join(f"{p[:3]} pareggi {S[p]['pareggi']} ECE1x2 {S[p]['ece_1x2']:.2f}" for p in S))
print({k: v for k, v in res.items() if not isinstance(v, dict)})
