"""Cartellini · studio sui soli dati (20/11/2026, Denny). Solo analisi: nessuna modifica all'app.
Ingresso: ricerca/cartellini/base.pkl (cart_dati.py: modello dell'app walk-forward). Il book NON entra nel modello: serve solo alla fine
come tabellone (giocate e rendimento sulle linee archiviate).
Varianti (coefficienti nuovi stimati SOLO nel periodo di sviluppo, fino al 30/6/2024; verifica 2024-25; holdout da luglio 2025):
  A  livello recente del campionato: cartellini reali / attesi dall'app negli ultimi 30, 60, 120, 365 giorni (shrinkage 50 partite)
  B  avanzamento della stagione (giorni dall'inizio della stagione del campionato)
  C  costante per campionato (stimata nello sviluppo)
  D  squadre: cartellini presi in casa / in trasferta rispetto all'atteso (ultime 10 nella stessa sede), cartellini presi in generale
  E  dispersione dei cartellini per squadra (oggi la stessa del totale, r = 1/alpha)
Metriche: log-loss NB del totale e per squadra, Over/Under totale (3,5 4,5 5,5 e linea vicina all'atteso), per squadra (0,5 1,5 2,5
e linea vicina), MAE; per campionato, mese, fascia; regola dell'harness (99% in verifica, stesso segno in holdout, maggioranza campionati).
Uscita: ricerca/cartellini/studio.json"""
import os, sys, json, math, collections
import numpy as np, pandas as pd
from scipy.stats import nbinom
from scipy.optimize import minimize_scalar
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(REPO, "tools", "lab"))
from comune import pois_fit, boot, per
OUT = os.path.join(REPO, "ricerca", "cartellini"); log = lambda *a: print(*a, flush=True)
B = pd.read_pickle(os.path.join(OUT, "base.pkl")); B = B[(B.d <= "2026-11-20") & (B["T"] <= 16)].reset_index(drop=True)
B["yh"], B["ya"], B["T"] = B.yh.astype(int), B.ya.astype(int), B["T"].astype(int)
B["per"] = B.d.map(per); B["wk"] = (pd.to_datetime(B.d) - pd.Timestamp("1970-01-01")).dt.days // 7; B["t"] = B.wk * 7 + 0
B["t"] = (pd.to_datetime(B.d) - pd.Timestamp("1970-01-01")).dt.days
B = B[B.per.isin(["scelta", "verifica", "holdout"])].reset_index(drop=True)
PER = ("scelta", "verifica", "holdout"); M = {p: (B.per == p).values for p in PER}; sc = M["scelta"]
log("partite", len(B), {p: int(M[p].sum()) for p in PER})
R = {}
# ---------------- caratteristiche pre-partita (solo giorni precedenti)
for days in (30, 60, 120, 365):
    out = np.zeros(len(B))
    for lg, G in B.groupby("lg"):
        t = G.t.values; cy = np.r_[0, np.cumsum(G["T"].values)]; cm = np.r_[0, np.cumsum(G.mu.values)]
        lo, hi = np.searchsorted(t, t - days, "left"), np.searchsorted(t, t, "left"); n = hi - lo
        sy, sm = cy[hi] - cy[lo], cm[hi] - cm[lo]; eb = np.where(n > 0, sm / np.maximum(n, 1), 4.0)
        out[G.index.values] = np.log((sy + 50 * eb) / (sm + 50 * eb))
    B[f"rec{days}"] = out
se_ = B.apply(lambda r: int(r.d[:4]) if r.lg in ("ARG", "BRA", "CHN", "FIN", "IRL", "JPN", "NOR", "SWE", "USA", "BLR") else (int(r.d[:4]) if r.d[5:7] >= "07" else int(r.d[:4]) - 1), axis=1)
B["se"] = se_; B["prog"] = np.clip((B.t - B.groupby(["lg", "se"]).t.transform("min")) / 300.0, 0, 1.3)
# squadre: cartellini presi rispetto all'atteso, ultime 10 nella stessa sede e ultime 10 in generale (shrinkage 5 partite)
hist = collections.defaultdict(list); fv = {k: np.zeros(len(B)) for k in ("h_sede", "a_sede", "h_tutte", "a_tutte")}
def rr(L, K=5.0):
    if not L: return 0.0
    y = sum(x[0] for x in L); e = sum(x[1] for x in L); eb = e / len(L); return math.log((y + K * eb) / (e + K * eb))
day_rows = collections.defaultdict(list)
for i, r in enumerate(B.itertuples(index=False)): day_rows[r.d].append(i)
for d in sorted(day_rows):
    for i in day_rows[d]:
        r = B.iloc[i]; Hh, Ha = hist[(r.lg, r.h)], hist[(r.lg, r.a)]
        fv["h_sede"][i] = rr([x for x in Hh if x[2] == "H"][-10:]); fv["a_sede"][i] = rr([x for x in Ha if x[2] == "A"][-10:])
        fv["h_tutte"][i] = rr(Hh[-10:]); fv["a_tutte"][i] = rr(Ha[-10:])
    for i in day_rows[d]:
        r = B.iloc[i]; hist[(r.lg, r.h)].append((r.yh, r.mh, "H")); hist[(r.lg, r.a)].append((r.ya, r.ma, "A"))
for k, v in fv.items(): B[k] = v
# ---------------- metriche
lp = lambda y, mu, r: nbinom.logpmf(y, r, r / (r + mu))
ovr = lambda L, mu, r: 1 - nbinom.cdf(np.floor(L), r, r / (r + mu))
def bll(p, o): return -np.log(np.clip(np.where(o == 1, p, 1 - p), 1e-12, 1))
r_app = 1 / B.alpha.values
def metrics(mu, mh, ma, rT=None):
    rT = r_app if rT is None else rT; rT = np.where(np.isfinite(rT), rT, 1e7); y, yh, ya = B["T"].values, B.yh.values, B.ya.values; o = pd.DataFrame(index=B.index)
    o["ll_tot"] = -lp(y, mu, r_app); o["ll_sq"] = -(lp(yh, mh, rT) + lp(ya, ma, rT)) / 2; o["ll_h"] = -lp(yh, mh, rT); o["ll_a"] = -lp(ya, ma, rT)
    L = np.floor(B.mu.values) + 0.5; p = ovr(L, mu, r_app); oo = (y > L).astype(float)   # linea vicina all'atteso dell'APP, uguale per tutti
    o["br_ou"], o["ll_ou"], o["pU"], o["U"] = (p - oo) ** 2, bll(p, oo), 1 - p, 1 - oo
    for L in (3.5, 4.5, 5.5): p = ovr(L, mu, r_app); oo = (y > L).astype(float); o[f"br_t{L}"] = (p - oo) ** 2; o[f"ll_t{L}"] = bll(p, oo)
    o["br_tfix"] = o[["br_t3.5", "br_t4.5", "br_t5.5"]].mean(1)
    bs, ls, pu, uu = [], [], [], []
    for m_, y_, ref in ((mh, yh, B.mh.values), (ma, ya, B.ma.values)):
        L = np.floor(ref) + 0.5; p = ovr(L, m_, rT); oo = (y_ > L).astype(float); bs.append((p - oo) ** 2); ls.append(bll(p, oo)); pu.append(1 - p); uu.append(1 - oo)
    o["br_sq"], o["ll_sqou"] = (bs[0] + bs[1]) / 2, (ls[0] + ls[1]) / 2; o["pUh"], o["Uh"], o["pUa"], o["Ua"] = pu[0], uu[0], pu[1], uu[1]
    fb = [];
    for L in (0.5, 1.5, 2.5):
        for m_, y_ in ((mh, yh), (ma, ya)): p = ovr(L, m_, rT); fb.append((p - (y_ > L)) ** 2)
    o["br_sqfix"] = np.mean(fb, 0); o["ae_t"] = np.abs(y - mu); o["ae_sq"] = (np.abs(yh - mh) + np.abs(ya - ma)) / 2
    o["mu"], o["mh"], o["ma"] = mu, mh, ma
    return o
KEYS = ["ll_tot", "ll_sq", "ll_ou", "br_ou", "br_tfix", "ll_sqou", "br_sq", "br_sqfix", "ae_t", "ae_sq"]
def summary(X):
    return {p: dict(n=int(M[p].sum()), **{k: round(float(X[k].values[M[p]].mean()), 5) for k in KEYS},
                    atteso=round(float(X.mu.values[M[p]].mean()), 3), reale=round(float(B["T"].values[M[p]].mean()), 3),
                    under_prev=round(float(X.pU.values[M[p]].mean()), 4), under_reale=round(float(X.U.values[M[p]].mean()), 4)) for p in PER}
def cmp(XA, XB, keys=KEYS):
    out = {}
    for key in keys:
        out[key] = {}
        for p in PER:
            m = M[p]; d = (XB[key] - XA[key]).values[m]; mu_, lo, hi = boot(d, B.wk.values[m]); _, lo95, hi95 = boot(d, B.wk.values[m], q=(2.5, 97.5))
            lg = pd.Series(d).groupby(B.lg.values[m]).mean()
            out[key][p] = dict(diff=round(mu_, 6), lo99=round(lo, 6), hi99=round(hi, 6), lo95=round(lo95, 6), hi95=round(hi95, 6), camp=f"{int((lg < 0).sum())}/{len(lg)}")
    return out
def passes(c):
    v, h = c["verifica"], c["holdout"]; a, b = map(int, v["camp"].split("/")); return bool(v["hi99"] < 0 and h["diff"] < 0 and a > b / 2)
X0 = metrics(B.mu.values, B.mh.values, B.ma.values); R["app"] = summary(X0)
def fit_tot(X):   # coefficienti sul totale (offset log mu dell'app), solo nello sviluppo
    Xm = np.hstack([np.ones((len(B), 1)), X]); b, se = pois_fit(Xm[sc], B["T"].values[sc], np.log(B.mu.values[sc])); return b, se, np.exp(Xm @ b)
def fit_sq(Xh, Xa):   # coefficienti sulle squadre (offset log mh / ma)
    one = np.ones((len(B), 1)); XH, XA = np.hstack([one, Xh]), np.hstack([one, Xa])
    b, se = pois_fit(np.vstack([XH[sc], XA[sc]]), np.r_[B.yh.values[sc], B.ya.values[sc]], np.log(np.r_[B.mh.values[sc], B.ma.values[sc]])); return b, se, np.exp(XH @ b), np.exp(XA @ b)
b, se, f = fit_tot(np.zeros((len(B), 0))); XC = metrics(B.mu.values * f, B.mh.values * f, B.ma.values * f); R["app_costante"] = dict(c=round(float(b[0]), 5), riepilogo=summary(XC))
VAR = {}
def add(name, mu, mh, ma, coef, rT=None):
    X = metrics(mu, mh, ma, rT); c = cmp(XC, X); VAR[name] = X
    R[name] = dict(coefficienti=coef, riepilogo=summary(X), contro_app_costante=c, regola={k: passes(c[k]) for k in ("ll_tot", "ll_sq", "ll_ou", "br_ou", "br_tfix", "br_sq", "br_sqfix")})
    log(f"{name:26s}", coef, " | ".join(f"{k} {c[k]['verifica']['diff']:+.5f}/{c[k]['holdout']['diff']:+.5f}" for k in ("ll_tot", "ll_sq", "br_ou", "br_sq")), R[name]["regola"])
# A, B: livello del campionato e avanzamento della stagione (fattore uguale per casa, ospite e totale)
for nm, cols in (("A rec30", ["rec30"]), ("A rec60", ["rec60"]), ("A rec120", ["rec120"]), ("A rec365", ["rec365"]), ("B stagione", ["prog"]), ("B stagione²", ["prog", "prog2"])):
    if "prog2" in cols: B["prog2"] = B.prog ** 2
    b, se, f = fit_tot(B[cols].values); add(nm, B.mu.values * f, B.mh.values * f, B.ma.values * f, {c: [round(float(x), 4), round(float(s), 4)] for c, x, s in zip(["costante"] + cols, b, se)})
# C: costante per campionato (campionati con almeno 150 partite nello sviluppo)
lgs = [g for g in sorted(B.lg.unique()) if (B.lg.values[sc] == g).sum() >= 150]
DL = np.array([[1.0 if l == g else 0.0 for g in lgs] for l in B.lg.values])
b, se, f = fit_tot(DL); add("C costante campionato", B.mu.values * f, B.mh.values * f, B.ma.values * f, {"campionati": len(lgs)})
# D: squadre (ripartizione e totale)
for nm, (ch, ca) in (("D sede", ("h_sede", "a_sede")), ("D tutte", ("h_tutte", "a_tutte"))):
    Xh = np.c_[B[ch].values, B[ca].values]; Xa = np.c_[B[ca].values, B[ch].values]   # propri cartellini, poi quelli dell'avversario
    b, se, fh, fa = fit_sq(Xh, Xa); mh, ma = B.mh.values * fh, B.ma.values * fa
    add(nm, mh + ma, mh, ma, {n: [round(float(x), 4), round(float(s), 4)] for n, x, s in zip(["costante", "propri", "avversario"], b, se)})
# F: contrazione verso la media del campionato (le previsioni lontane dalla media sono troppo estreme?)
B["contr"] = np.log(B.mu / B.lm)
b, se, f = fit_tot(B[["contr"]].values); add("F contrazione", B.mu.values * f, B.mh.values * f, B.ma.values * f, {c: [round(float(x), 4), round(float(s), 4)] for c, x, s in zip(["costante", "contr"], b, se)})
R["pendenza_calibrazione"] = {p: round(float(np.polyfit(B.mu.values[M[p]], B["T"].values[M[p]], 1)[0]), 3) for p in PER}; log("pendenza reale su atteso", R["pendenza_calibrazione"])
# E: dispersione per squadra (r stimato nello sviluppo)
def rml(y, mu):
    f = lambda lr: -lp(y, mu, math.exp(lr)).sum(); return math.exp(minimize_scalar(f, bounds=(0, 9), method="bounded").x)
r_sq = {p: round(rml(np.r_[B.yh.values[M[p]], B.ya.values[M[p]]], np.r_[B.mh.values[M[p]], B.ma.values[M[p]]]), 2) for p in PER}
r_tot = {p: round(rml(B["T"].values[M[p]], B.mu.values[M[p]]), 2) for p in PER}
R["dispersione"] = dict(r_squadra=r_sq, r_totale=r_tot, r_app_medio=round(float(r_app.mean()), 2)); log("dispersione", R["dispersione"])
add("E r squadra", B.mu.values * 1, B.mh.values, B.ma.values, {"r_squadra": r_sq["scelta"]}, rT=np.full(len(B), r_sq["scelta"]))
# combinazioni: contrazione + squadre con Poisson; livello recente + contrazione + Poisson
vF = VAR["F contrazione"]; add("F + E", vF.mu.values, vF.mh.values, vF.ma.values, {"vedi": "F contrazione + Poisson per squadra"}, rT=np.full(len(B), np.inf))
b, se, f = fit_tot(B[["contr", "rec30"]].values); add("F + A30 + E", B.mu.values * f, B.mh.values * f, B.ma.values * f, {c: [round(float(x), 4), round(float(s), 4)] for c, x, s in zip(["costante", "contr", "rec30"], b, se)}, rT=np.full(len(B), np.inf))
# calibrazione dell'app: Under sulla linea vicina per fasce, per mese, per campionato (holdout)
def calib(X):
    o = {}
    for p in ("verifica", "holdout"):
        m = M[p]; G = X[m]; q = pd.cut(G.pU, [0, .4, .5, .55, .6, .65, .7, 1])
        o[p] = dict(fasce_under_totale={str(k): dict(n=int(len(g)), prev=round(float(g.pU.mean()), 3), reale=round(float(g.U.mean()), 3)) for k, g in G.groupby(q, observed=True)})
        pu = np.r_[G.pUh.values, G.pUa.values]; uu = np.r_[G.Uh.values, G.Ua.values]; q2 = pd.cut(pu, [0, .4, .5, .55, .6, .65, .7, .8, 1])
        o[p]["fasce_under_squadra"] = {str(k): dict(n=int(len(g)), prev=round(float(pu[g.index].mean()), 3), reale=round(float(uu[g.index].mean()), 3)) for k, g in pd.Series(np.arange(len(pu))).groupby(q2, observed=True)}
        o[p]["casa"] = f"{G.mh.mean():.3f}/{B.yh.values[m].mean():.3f}"; o[p]["ospite"] = f"{G.ma.mean():.3f}/{B.ya.values[m].mean():.3f}"
    G = B.assign(mu_=X.mu)
    o["mesi"] = G[G.d >= "2024-07"].groupby(G.d.str[:7]).apply(lambda g: round(float(g["T"].sum() / g.mu_.sum()), 3)).to_dict()
    o["campionati_holdout"] = G[M["holdout"]].groupby("lg").apply(lambda g: round(float(g["T"].sum() / g.mu_.sum()), 3)).to_dict()
    return o
R["calibrazione_app"] = calib(X0)
json.dump(R, open(os.path.join(OUT, "studio.json"), "w"), indent=1, ensure_ascii=False, default=float)
pd.to_pickle({k: dict(mu=v.mu.values, mh=v.mh.values, ma=v.ma.values) for k, v in VAR.items()}, os.path.join(OUT, "varianti.pkl")); B.to_pickle(os.path.join(OUT, "feat.pkl"))
log("calibrazione app", json.dumps(R["calibrazione_app"], ensure_ascii=False)[:3000])
log("fatto")
