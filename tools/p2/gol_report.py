"""Gol attesi · fase 3: tabelle del report finale (Denny) da exp3_pred (M1-M4, stima completa), exp4_pred (forma, Dixon-Coles) e M0.
Uscita: ricerca/gol/report.json"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__)); from gol_eval import *
from scipy.stats import poisson
REPO = os.path.join(os.path.dirname(__file__), "..", "..")
df = pd.read_pickle(os.path.join(REPO, "ricerca", "gol", "feat.pkl")).sort_values(["d", "lg"]).reset_index(drop=True)
P3 = pd.read_pickle(os.path.join(REPO, "ricerca", "gol", "exp3_pred.pkl")); P4 = pd.read_pickle(os.path.join(REPO, "ricerca", "gol", "exp4_pred.pkl"))
k4 = {k: k for k in P4}
pick = lambda pref: next(k for k in P4 if k.startswith(pref))
MODELS = [("M0 (attuale)", df.lh0.values, df.la0.values, None),
          ("M0 + Dixon-Coles", *P4["M0 + Dixon-Coles"])]
for k in P3:
    MODELS.append((k.replace("B", "B (coefficienti stimati di nuovo)") if k == "B" else k, P3[k][0], P3[k][1], None))
fT = pick("M0 + forma solo tiri in porta"); fTD = [k for k in P4 if k.startswith("M0 + forma solo tiri in porta") and k.endswith("Dixon-Coles")][0]
MODELS += [("M0 + forma tiri in porta", *P4[fT]), ("M0 + forma tiri in porta + Dixon-Coles", *P4[fTD])]
XS, OUT = {}, {"modelli": [m[0] for m in MODELS]}
X0 = None; prev = None
for nm, lh, la, rho in MODELS:
    X = metrics(df, lh, la, rho); XS[nm] = X
    S = summary(df, X)
    if X0 is None: X0 = X
    row = {"riepilogo": S, "contro_M0": {k: compare(df, X0, X, k) for k in ("ll_score", "ll_1x2", "br_1x2", "ll_o15", "ll_o25", "ll_o35", "br_o25", "se_t", "ae_t")} if nm != MODELS[0][0] else None}
    if prev is not None: row["contro_precedente"] = {k: compare(df, XS[prev], X, k) for k in ("ll_score", "ll_1x2", "br_1x2")}
    OUT[nm] = row; prev = nm
# per campionato: modello finale contro M0
fin = MODELS[-1][0]; Xf = XS[fin]
pc = {}
for per in ("verifica", "holdout"):
    m = (df.per == per).values
    d = (Xf.ll_score - X0.ll_score)[m].groupby(df.lg[m]).agg(["mean", "count"])
    pc[per] = {l: [round(r["mean"], 5), int(r["count"])] for l, r in d.iterrows()}
OUT["per_campionato_finale"] = pc
# partite ad alto punteggio: 3+ e 4+ per quinti di gol attesi, per campionato (gruppi per livello), M0 e finale
hs = {}
for nm in (MODELS[0][0], fin):
    X = XS[nm]; H = {}
    for per in ("verifica", "holdout"):
        m = (df.per == per).values; x = X[m]; et = (x.e_h + x.e_a).values
        q = pd.qcut(et, 5, labels=False)
        H[per] = {"quinti": [dict(gol_attesi=round(et[q == i].mean(), 2), gol_reali=round((df.yh + df.ya).values[m][q == i].mean(), 2),
                                  p3=round((1 - x.p_b2[q == i] - x.p_b0_1[q == i] if False else (x.p_b3 + x["p_b4+"])[q == i].mean()) * 100, 1),
                                  o3=round(((x.o_b3 + x["o_b4+"])[q == i]).mean() * 100, 1),
                                  p4=round(x["p_b4+"][q == i].mean() * 100, 1), o4=round(x["o_b4+"][q == i].mean() * 100, 1)) for i in range(5)]}
        # λ o distribuzione? con λ riscalato al livello reale del periodo
        k = (df.yh + df.ya).values[m].mean() / et.mean()
        lh = (x.e_h * k).values; la = (x.e_a * k).values
        Xr = metrics(df[m], lh, la); H[per]["3+ con livello corretto"] = f"{(Xr.p_b3 + Xr['p_b4+']).mean()*100:.1f} / {(Xr.o_b3 + Xr['o_b4+']).mean()*100:.1f} (fattore {k:.3f})"
        H[per]["3+"] = f"{(x.p_b3 + x['p_b4+']).mean()*100:.1f} / {(x.o_b3 + x['o_b4+']).mean()*100:.1f}"; H[per]["4+"] = f"{x['p_b4+'].mean()*100:.1f} / {x['o_b4+'].mean()*100:.1f}"
        # per campionato: scarto 3+ (reale − previsto) e media gol
        g = pd.DataFrame(dict(lg=df.lg.values[m], p=(x.p_b3 + x["p_b4+"]).values, o=(x.o_b3 + x["o_b4+"]).values, gt=(df.yh + df.ya).values[m], et=et)).groupby("lg").mean()
        H[per]["per_campionato_3+"] = {l: [round(r["p"] * 100, 1), round(r["o"] * 100, 1), round(r["gt"], 2), round(r["et"], 2)] for l, r in g.iterrows()}
        H[per]["correlazione scarto 3+ / gol medi del campionato"] = round(float(np.corrcoef(g["o"] - g["p"], g["gt"])[0, 1]), 2)
    hs[nm] = H
OUT["alto_punteggio"] = hs
json.dump(OUT, open(os.path.join(REPO, "ricerca", "gol", "report.json"), "w"), indent=1, default=str, ensure_ascii=False)
# stampa compatta
for per in ("verifica", "holdout"):
    print(f"\n==== {per}")
    print(f"{'modello':48} {'ll ris.':>8} {'ll 1X2':>7} {'Br 1X2':>7} {'MAE':>6} {'RMSE':>6} {'ECE':>5} {'pareggi':>10} {'O1.5':>10} {'O2.5':>10} {'O3.5':>10} {'0-1':>10} {'2':>10} {'3':>10} {'4+':>10} {'5+':>10}")
    for nm in OUT["modelli"]:
        s = OUT[nm]["riepilogo"][per]
        print(f"{nm[:48]:48} {s['ll_score']:8.4f} {s['ll_1x2']:7.4f} {s['br_1x2']:7.4f} {s['mae_t']:6.3f} {s['rmse_t']:6.3f} {s['ece_1x2']:5.2f} {s['pareggi']:>10} {s['o15']:>10} {s['o25']:>10} {s['o35']:>10} {s['b0-1']:>10} {s['b2']:>10} {s['b3']:>10} {s['b4+']:>10} {s['b5+']:>10}")
for nm in (MODELS[0][0], fin):
    print("\n", nm, {p: {k: v for k, v in hs[nm][p].items() if k != "per_campionato_3+"} for p in hs[nm]})
print("\nper campionato (finale − M0, ll risultato esatto):", pc)
