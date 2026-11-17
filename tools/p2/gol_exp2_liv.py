"""Gol attesi · fase 3, esperimento 2 (Denny): riequilibrio dei campionati (pendenza 1,12-1,14 tra livello previsto e reale).
A coefficienti attuali (M0) · B stessi ingredienti con coefficienti stimati di nuovo sui 31 campionati (solo periodo scelta, fissi dopo)
B2 come B ma stimati di nuovo ogni mese sulle sole partite precedenti · C fattore per campionato (gol reali / previsti nelle partite precedenti
della finestra W, ristretto verso 1 con k partite fittizie; W e k scelti nel periodo scelta) · D componente temporale: livello recente del
campionato (120 giorni) e della stagione in corso rispetto ai 365 giorni, come ingredienti in più di B. Holdout mai usato per stimare o scegliere."""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__)); from gol_eval import *
REPO = os.path.join(os.path.dirname(__file__), "..", "..")
df = pd.read_pickle(os.path.join(REPO, "ricerca", "gol", "feat.pkl")).sort_values(["d", "lg"]).reset_index(drop=True)
df["mese"] = df.date.dt.to_period("M"); sc = (df.per == "scelta").values
RHO = -0.04   # solo per i riepiloghi con Dixon-Coles; i confronti di questo esperimento sono a rho 0 come M0
def design(df, side, extra=()):
    h = side == "h"
    mu = df.muH if h else df.muA; tp = df.tpH if h else df.tpA; qx = (df.qxh if h else df.qxa).fillna(0)
    ed = df.ed if h else -df.ed; we = df.we.astype(float)
    cols = [np.ones(len(df)), np.log(mu) * we, np.full(len(df), 1.0 if h else 0.0) * we, np.log(tp) * we, ed * we, qx * we,
            (1 - we), np.log(mu) * (1 - we), np.full(len(df), 1.0 if h else 0.0) * (1 - we), np.log(tp) * (1 - we), qx * (1 - we)]
    for f in extra: cols.append(f(df, h))
    return np.column_stack(cols)
def fitpred(extra=(), mask=None):
    m = sc if mask is None else mask
    X = np.vstack([design(df[m], "h", extra), design(df[m], "a", extra)]); y = np.r_[df.yh[m], df.ya[m]]
    b = pois_fit(X, y)
    return b, np.exp(design(df, "h", extra) @ b), np.exp(design(df, "a", extra) @ b)
X0 = metrics(df, df.lh0, df.la0); OUT = {"A attuale": (df.lh0.values, df.la0.values)}
bB, lhB, laB = fitpred(); OUT["B stima nuova (scelta)"] = (lhB, laB)
# B2: stima mensile su tutte le partite precedenti
lh2, la2 = df.lh0.values.copy(), df.la0.values.copy()
for mo in sorted(df.mese.unique()):
    prev = (df.mese < mo).values
    if prev.sum() < 5000: continue
    _, ph, pa = fitpred(mask=prev); cur = (df.mese == mo).values; lh2[cur], la2[cur] = ph[cur], pa[cur]
OUT["B2 stima nuova ogni mese"] = (lh2, la2)
# C: fattore per campionato con prudenza (finestra W giorni, k partite fittizie), sulle partite precedenti, ricalcolato per giorno
def league_factor(lh, la, W, k):
    f = np.ones(len(df)); tot_y = (df.yh + df.ya).values; tot_l = lh + la
    for lg, g in df.groupby("lg"):
        ii = g.index.values; dd = df.d.values[ii]; ty = tot_y[ii]; tl = tot_l[ii]
        cy = np.r_[0, np.cumsum(ty)]; cl = np.r_[0, np.cumsum(tl)]
        lo = np.searchsorted(dd, dd - W, "left"); hi = np.searchsorted(dd, dd, "left")
        Y, Lm, n = cy[hi] - cy[lo], cl[hi] - cl[lo], hi - lo
        lbar = np.where(n > 0, Lm / np.maximum(n, 1), tl.mean())
        f[ii] = (Y + k * lbar) / (Lm + k * lbar)
    return f
best = None; grid = {}
for W in (120, 365, 730):
    for k in (25, 50, 100, 200, 400):
        f = league_factor(df.lh0.values, df.la0.values, W, k)
        v = metrics(df[sc], df.lh0[sc] * f[sc], df.la0[sc] * f[sc]).ll_score.mean(); grid[f"W{W} k{k}"] = round(v, 6)
        if best is None or v < best[0]: best = (v, W, k)
_, W, k = best; f = league_factor(df.lh0.values, df.la0.values, W, k); OUT[f"C fattore campionato (W {W}, k {k})"] = (df.lh0.values * f, df.la0.values * f)
fB = league_factor(lhB, laB, W, k); OUT[f"B + C"] = (lhB * fB, laB * fB)
# D: livello recente e stagione come ingredienti (log rapporto rispetto ai 365 giorni, ristretto con le partite disponibili)
def rec120(d, h): return np.log(((d.g120 + 20 * (d.muH + d.muA)) / (d.n120 + 20)) / (d.muH + d.muA))
def season(d, h): return np.log(((d.gse + 20 * (d.muH + d.muA)) / (d.nse + 20)) / (d.muH + d.muA))
bD, lhD, laD = fitpred(extra=(rec120, season)); OUT["D = B + livello recente e stagione"] = (lhD, laD)
res = {"griglia C (scelta, ll risultato esatto)": grid, "coefficienti B": [round(x, 4) for x in bB], "coefficienti D (ultimi 2: 120 gg, stagione)": [round(x, 4) for x in bD]}
XS = {}
for nm, (lh, la) in OUT.items():
    X = metrics(df, lh, la); XS[nm] = X
    res[nm] = dict(pendenza_campionati={p: round(league_slope(df, lh, la, p), 3) for p in ("scelta", "verifica", "holdout")},
                   riepilogo=summary(df, X))
    if nm != "A attuale":
        res[nm]["contro A"] = {key: compare(df, X0, X, key) for key in ("ll_score", "ll_1x2", "br_o25", "ll_o25", "se_t")}
        res[nm]["regola"] = rule(res[nm]["contro A"]["ll_score"])
json.dump(res, open(os.path.join(REPO, "ricerca", "gol", "exp2_liv.json"), "w"), indent=1, default=str, ensure_ascii=False)
def show(R): return " | ".join(f"{p[:3]} {R[p]['diff']:+.5f} [{R[p]['lo']:+.5f},{R[p]['hi']:+.5f}] {R[p]['camp']}" for p in ("scelta", "verifica", "holdout"))
for nm in OUT:
    r = res[nm]; S = r["riepilogo"]
    print(f"\n== {nm} · pendenza {r['pendenza_campionati']} · " + " ".join(f"{p[:3]} O2.5 {S[p]['o25']} 3+tot {S[p]['b3']}" for p in S))
    if "contro A" in r:
        print(f"   regola: {r['regola']}")
        for key in ("ll_score", "ll_1x2", "ll_o25", "se_t"): print(f"   {key:8} {show(r['contro A'][key])}")
print("\n", res["coefficienti B"], res["coefficienti D (ultimi 2: 120 gg, stagione)"], best)
