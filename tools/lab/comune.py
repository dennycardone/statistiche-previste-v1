"""Laboratorio di Prevista (18/11/2026, Denny: "un meccanismo che testi formule migliori, una volta al giorno").
Parti comuni: previsioni attuali dell'app (M0, ricerca/base: walk-forward con i soli dati precedenti) unite all'archivio API-Football
(ricerca/storico: nomi API, arbitro, giornata, coppe europee), stima dei coefficienti nuovi SOLO nel periodo scelta (fino al 30/6/2024)
con le previsioni dell'app fisse (offset), giudizio in verifica (2024-25) e holdout (da luglio 2025, solo confronto).
Regola del laboratorio, più severa dell'harness perché si provano molte idee: in verifica miglioramento con intervallo al 99% tutto sotto
zero, stesso segno in holdout, maggioranza dei campionati in verifica. Chi passa va in prova "in ombra" sulle partite nuove."""
import os, json, glob, math, numpy as np, pandas as pd
from scipy.stats import nbinom
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
RIC = os.environ.get("RICERCA", os.path.join(REPO, "ricerca"))
SCELTA, VERIFICA = "2024-06-30", "2025-06-30"
EUROPA = ("UCL", "UEL", "UECL")

def per(d): return "scelta" if d <= SCELTA else "verifica" if d <= VERIFICA else "holdout"

def load_storico():
    """partite API-Football: lega, data, casa, ospite, gol, arbitro, statistiche [tiri, in porta, corner, falli, gialli, rossi, xG], giornata"""
    R = []
    for f in glob.glob(os.path.join(RIC, "storico", "*_20*.json")):
        D = json.load(open(f)); lg = D.get("lega") or os.path.basename(f).split("_")[0]
        for fid, v in D["partite"].items():
            if v[3] is None or v[4] is None: continue
            sh, sa = v[6] or [None] * 7, v[7] or [None] * 7
            rnd = None
            try: rnd = int(str(v[8]).rsplit("-", 1)[1]) if v[8] and "Regular Season" in str(v[8]) else None
            except Exception: rnd = None
            R.append(dict(lg=lg, se=D.get("stagione"), fid=fid, dt=v[0], d=v[0][:10], h=v[1], a=v[2], hg=v[3], ag=v[4], ref=v[5],
                          hf=sh[3], af=sa[3], hy=sh[4], ay=sa[4], hc=sh[2], ac=sa[2], hs=sh[0], as_=sa[0], rnd=rnd))
    return pd.DataFrame(R)

def load_base(stat):
    """previsioni dell'app per statistica (λ casa, λ ospite, r totale, r squadra, correlazione) e valori reali"""
    R = []
    for f in glob.glob(os.path.join(RIC, "base", "*.json")):
        lg = os.path.basename(f)[:-5]
        for m in json.load(open(f)):
            p, y = m.get(stat), (m.get("y") or {}).get(stat)
            g, yg = m.get("g"), (m.get("y") or {}).get("g")
            if not p or not y or y[0] is None or y[1] is None or p[0] is None or not yg: continue
            R.append(dict(lg=lg, d=m["d"], h_app=m["h"], a_app=m["a"], l0h=p[0], l0a=p[1], r_tot=p[2], r_team=p[3], yh=y[0], ya=y[1],
                          ygh=yg[0], yga=yg[1], gh=g[0] if g else np.nan, ga=g[1] if g else np.nan))
    return pd.DataFrame(R)

def join(B, S, stat_cols):
    """unisce le previsioni dell'app (nomi dell'app) all'archivio API (nomi API): stessa lega e data, stessi gol e stessa statistica"""
    hc, ac = stat_cols
    S2 = S.dropna(subset=[hc, ac]).copy()
    S2["k"] = S2.lg + "|" + S2.d + "|" + S2.hg.astype(int).astype(str) + "-" + S2.ag.astype(int).astype(str) + "|" + S2[hc].astype(int).astype(str) + "-" + S2[ac].astype(int).astype(str)
    B = B.copy(); B["k"] = B.lg + "|" + B.d + "|" + B.ygh.astype(int).astype(str) + "-" + B.yga.astype(int).astype(str) + "|" + B.yh.astype(int).astype(str) + "-" + B.ya.astype(int).astype(str)
    S2 = S2[~S2.k.duplicated(keep=False)]; B = B[~B.k.duplicated(keep=False)]
    J = B.merge(S2[["k", "fid", "dt", "h", "a", "ref", "rnd", "se"]], on="k", how="inner")
    J["per"] = J.d.map(per); J["wk"] = (pd.to_datetime(J.d) - pd.Timestamp("1970-01-01")).dt.days // 7
    return J.sort_values(["d", "lg"]).reset_index(drop=True)

# ---- stima (offset: le previsioni dell'app restano fisse, si stimano solo i coefficienti nuovi)
def pois_fit(X, y, off):
    b = np.zeros(X.shape[1])
    for _ in range(60):
        eta = off + X @ b; mu = np.exp(eta); W = mu; z = (eta - off) + (y - mu) / mu
        XtW = X.T * W; bn = np.linalg.solve(XtW @ X + 1e-9 * np.eye(len(b)), XtW @ z)
        if np.max(np.abs(bn - b)) < 1e-10: b = bn; break
        b = bn
    mu = np.exp(off + X @ b); se = np.sqrt(np.diag(np.linalg.inv((X.T * mu) @ X)))
    return b, se

def fit_apply(J, Xh, Xa):
    """Xh, Xa: matrici delle caratteristiche (senza costante) per la squadra di casa e ospite; stima sul periodo scelta"""
    sc = (J.per == "scelta").values
    one = np.ones((len(J), 1)); XH = np.hstack([one, Xh]); XA = np.hstack([one, Xa])
    X = np.vstack([XH[sc], XA[sc]]); y = np.r_[J.yh.values[sc], J.ya.values[sc]]; off = np.log(np.r_[J.l0h.values[sc], J.l0a.values[sc]])
    b, se = pois_fit(X, y, off)
    return b, se, J.l0h.values * np.exp(XH @ b), J.l0a.values * np.exp(XA @ b)

# ---- metriche (Binomiale Negativa come l'app: r per squadra e r del totale; 1X2 con squadre indipendenti)
K = np.arange(0, 81)
def nb_pmf(mu, r):
    p = r / (r + np.asarray(mu)[:, None]); return nbinom.pmf(K[None, :], r, p)
def metrics(J, lh, la):
    r = J.r_team.values[0] if "r_team" in J else 200.0
    rt = J.r_tot.values[0] if "r_tot" in J else 150.0
    yh, ya = J.yh.values.astype(int), J.ya.values.astype(int)
    out = pd.DataFrame(index=J.index)
    lp = lambda y, mu, rr: nbinom.logpmf(y, rr, rr / (rr + mu))
    out["ll_team"] = -(lp(yh, lh, r) + lp(ya, la, r))
    Ph, Pa = nb_pmf(lh, r), nb_pmf(la, r)
    cA = np.cumsum(Pa, 1)
    p1 = (Ph[:, 1:] * cA[:, :-1]).sum(1); px = (Ph * Pa).sum(1); p2 = np.clip(1 - p1 - px, 1e-12, 1)
    o1, ox = (yh > ya).astype(float), (yh == ya).astype(float); o2 = 1 - o1 - ox
    out["ll_1x2"] = -np.log(np.clip(np.where(o1 == 1, p1, np.where(ox == 1, px, p2)), 1e-12, 1))
    out["br_1x2"] = (p1 - o1) ** 2 + (px - ox) ** 2 + (p2 - o2) ** 2
    tot = lh + la; L = np.floor(tot) + 0.5; yt = yh + ya
    pov = 1 - nbinom.cdf(np.floor(L), rt, rt / (rt + tot)); oo = (yt > L).astype(float)
    out["ll_ou"] = -np.log(np.clip(np.where(oo == 1, pov, 1 - pov), 1e-12, 1)); out["br_ou"] = (pov - oo) ** 2
    out["ae_t"] = np.abs(yt - tot); out["se_t"] = (yt - tot) ** 2
    out["p1"], out["o1"], out["tot"], out["yt"] = p1, o1, tot, yt
    return out

def boot(d, wk, B=800, seed=7, q=(0.5, 99.5)):
    g = pd.Series(d).groupby(wk); s = g.sum().values; c = g.count().values
    rng = np.random.default_rng(seed); idx = rng.integers(0, len(s), (B, len(s))); bs = s[idx].sum(1) / c[idx].sum(1)
    return float(np.mean(d)), float(np.percentile(bs, q[0])), float(np.percentile(bs, q[1]))

def compare(J, X0, X1, key):
    R = {}
    for p in ("scelta", "verifica", "holdout"):
        m = (J.per == p).values
        if not m.any(): continue
        d = (X1[key] - X0[key]).values[m]
        mu, lo, hi = boot(d, J.wk.values[m])
        lg = pd.Series(d).groupby(J.lg.values[m]).mean()
        R[p] = dict(diff=mu, lo99=lo, hi99=hi, pct=100 * mu / X0[key].values[m].mean(), camp=f"{int((lg < 0).sum())}/{len(lg)}", n=int(m.sum()))
    return R

def rule(R):
    v, h = R.get("verifica"), R.get("holdout")
    if not v or not h: return False
    a, b = map(int, v["camp"].split("/"))
    return bool(v["hi99"] < 0 and h["diff"] < 0 and a > b / 2)

_CTRL = {}
def control(J):
    """riferimento alla pari: previsioni dell'app con la sola costante stimata nel periodo scelta (così il guadagno di un'idea non è
    un semplice ritocco del livello medio)"""
    k = (len(J), float(J.l0h.sum()))
    if k not in _CTRL:
        z = np.zeros((len(J), 0)); b, se, lh, la = fit_apply(J, z, z); _CTRL[k] = (metrics(J, lh, la), float(b[0]))
    return _CTRL[k]
def evaluate(J, b, se, lh, la, names):
    X0, c0 = control(J); X1 = metrics(J, lh, la)
    res = {"riferimento": f"app + costante ({c0:+.4f}) stimata nel periodo scelta", "coefficienti": {n: [round(float(x), 5), round(float(s), 5)] for n, x, s in zip(["costante"] + names, b, se)},
           "confronti": {k: compare(J, X0, X1, k) for k in ("ll_team", "ll_1x2", "br_1x2", "ll_ou", "se_t", "ae_t")}}
    # passa: regola sul punteggio delle squadre (verosimiglianza dei falli di ciascuna) e 1X2 non peggiorato in modo sicuro (intervallo al 99%)
    res["passa"] = rule(res["confronti"]["ll_team"]) and res["confronti"]["ll_1x2"]["verifica"]["lo99"] <= 0
    res["passa_1x2"] = rule(res["confronti"]["ll_1x2"])
    return res
