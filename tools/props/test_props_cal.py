"""Player props · punto 3, seguito (14/11/2026): il Modello B sovrastima in media del 5-15% (gli ingressi dalla panchina gonfiano i
valori ogni 90'). Correzione: fattore di scala per statistica (μ × c), stimato SOLO nel periodo "scelta", poi fisso su verifica e
holdout. Legge ricerca/props_rows.pkl scritto da test_props.py (stessi parametri DP, K, α)."""
import pickle, json, os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..")); import harness as H
sys.argv += ["ricerca"] if len(sys.argv) < 2 else []
R = sys.argv[1]
rows, _ = pickle.load(open(os.path.join(R, "props_rows.pkl"), "rb")); par = json.load(open(os.path.join(R, "props_esito.json")))["parametri"]
df = pd.DataFrame(rows)
from test_props_lib import p_over, ll, STATS, MARKETS, LAB, DPS
sc = df.date <= H.PERIODI["scelta"][1]
for st in STATS:
    i, K, al = DPS.index(par[st]["DP"]), par[st]["K"], par[st]["alpha"]; j = STATS.index(st)
    muA = np.vstack(df[f"A_{i}_{K}"].values)[:, j]; rat = df["r_" + st].astype(float).values; ok = np.isfinite(rat)
    muB = np.where(ok, muA * rat, np.nan)
    def tot(c, m):
        return sum(ll(p_over(c * muB[m & ok], L, al), (df["y_" + st].values[m & ok] > L).astype(float)).mean() for s2, L in MARKETS if s2 == st)
    cs = np.arange(0.70, 1.051, 0.01); c = cs[int(np.argmin([tot(x, sc.values) for x in cs]))]
    print(f"== {st}: fattore di scala scelto nel periodo scelta {c:.2f}")
    for s2, L in MARKETS:
        if s2 != st: continue
        y = (df["y_" + st].values > L).astype(int)
        d = pd.DataFrame({"date": df.date, "lg": df.lg, "season": df.season, "y": y * 2, "pB": [np.array([1 - q, 0, q]) for q in p_over(np.nan_to_num(muB, nan=1e-3), L, al)],
                          "pC": [np.array([1 - q, 0, q]) for q in p_over(np.nan_to_num(c * muB, nan=1e-3), L, al)]})[ok]
        r = H.confronta(d, "pB", "pC"); print(H.riepilogo(f"{LAB[(st, L)]} · B corretto contro B", r))
        hold = d.date >= H.PERIODI["holdout"][0]; q = np.array([x[2] for x in d.pC[hold]]); yy = d.y[hold].values / 2
        bins = np.quantile(q, np.linspace(0, 1, 11)); ix = np.clip(np.searchsorted(bins, q) - 1, 0, 9)
        print(f"   holdout corretto: media prevista {q.mean():.3f} reale {yy.mean():.3f} · decili " + " ".join(f"{q[ix==b].mean():.2f}→{yy[ix==b].mean():.2f}" for b in range(10)))
