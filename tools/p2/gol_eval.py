"""Gol attesi · fase 3: metriche e confronti (stesse partite, stessi periodi dell'harness: scelta ≤ 30/6/2024, verifica 2024-25, holdout da 7/2025).
metrics(df, lh, la, rho) → per partita: log-loss del risultato esatto, log-loss e Brier 1X2, Over 1,5/2,5/3,5, fasce dei gol totali, errori.
compare(df, A, B) → differenze partita per partita con intervallo al 95% (bootstrap a blocchi per settimana), campionati migliorati."""
import numpy as np, pandas as pd
from scipy.stats import poisson
from scipy.optimize import minimize_scalar
K = np.arange(11)

def matrices(lh, la, rho=None):
    Ph = poisson.pmf(K[None, :], np.asarray(lh)[:, None]); Pa = poisson.pmf(K[None, :], np.asarray(la)[:, None])
    M = Ph[:, :, None] * Pa[:, None, :]
    if rho is not None:
        r = np.broadcast_to(np.asarray(rho, float), (len(M),))
        lh, la = np.asarray(lh), np.asarray(la)
        M[:, 0, 0] *= np.maximum(0, 1 - lh * la * r); M[:, 0, 1] *= np.maximum(0, 1 + lh * r)
        M[:, 1, 0] *= np.maximum(0, 1 + la * r); M[:, 1, 1] *= np.maximum(0, 1 - r)
    return M / M.sum((1, 2), keepdims=True)

TOT = np.add.outer(K, K)
BANDS = [("0-1", 0, 1), ("2", 2, 2), ("3", 3, 3), ("4+", 4, 99), ("5+", 5, 99)]

def metrics(df, lh, la, rho=None):
    M = matrices(lh, la, rho); n = len(M)
    yh = np.minimum(df.yh.values.astype(int), 10); ya = np.minimum(df.ya.values.astype(int), 10); yt = df.yh.values + df.ya.values
    eps = 1e-12
    out = pd.DataFrame(index=df.index)
    out["ll_score"] = -np.log(np.maximum(M[np.arange(n), yh, ya], eps))
    p1 = np.tril(M, -1).sum((1, 2)); px = np.trace(M, axis1=1, axis2=2); p2 = np.triu(M, 1).sum((1, 2))
    o1 = (df.yh.values > df.ya.values).astype(float); ox = (df.yh.values == df.ya.values).astype(float); o2 = 1 - o1 - ox
    out["ll_1x2"] = -np.log(np.maximum(np.where(o1 == 1, p1, np.where(ox == 1, px, p2)), eps))
    out["br_1x2"] = (p1 - o1) ** 2 + (px - ox) ** 2 + (p2 - o2) ** 2
    out["p_x"], out["o_x"], out["p_1"], out["o_1"] = px, ox, p1, o1
    for L in (1.5, 2.5, 3.5):
        po = M[:, TOT > L].sum(1); oo = (yt > L).astype(float); k = str(L).replace(".", "")
        out["p_o" + k], out["o_o" + k] = po, oo
        out["br_o" + k] = (po - oo) ** 2; out["ll_o" + k] = -np.log(np.maximum(np.where(oo == 1, po, 1 - po), eps))
    for nm, lo, hi in BANDS:
        mask = (TOT >= lo) & (TOT <= hi); out["p_b" + nm] = M[:, mask].sum(1); out["o_b" + nm] = ((yt >= lo) & (yt <= hi)).astype(float)
    eh = (M.sum(2) * K).sum(1); ea = (M.sum(1) * K).sum(1)
    out["e_h"], out["e_a"] = eh, ea
    out["ae_t"] = np.abs(yt - eh - ea); out["se_t"] = (yt - eh - ea) ** 2
    out["ae_h"] = np.abs(df.yh.values - eh); out["ae_a"] = np.abs(df.ya.values - ea)
    out["se_h"] = (df.yh.values - eh) ** 2; out["se_a"] = (df.ya.values - ea) ** 2
    return out

def ece(p, o, bins=10):
    q = np.clip((p * bins).astype(int), 0, bins - 1); e = 0
    for b in range(bins):
        m = q == b
        if m.any(): e += abs(p[m].mean() - o[m].mean()) * m.sum()
    return e / len(p)

def summary(df, X):
    """riga di riepilogo per periodo"""
    R = {}
    for per in ("scelta", "verifica", "holdout"):
        m = (df.per == per).values; x = X[m]
        r = dict(n=int(m.sum()), ll_score=x.ll_score.mean(), ll_1x2=x.ll_1x2.mean(), br_1x2=x.br_1x2.mean(),
                 mae_t=x.ae_t.mean(), rmse_t=np.sqrt(x.se_t.mean()), mae_h=x.ae_h.mean(), mae_a=x.ae_a.mean(),
                 rmse_h=np.sqrt(x.se_h.mean()), rmse_a=np.sqrt(x.se_a.mean()),
                 pareggi=f"{x.p_x.mean()*100:.1f}/{x.o_x.mean()*100:.1f}",
                 ece_1x2=np.mean([ece(x.p_1.values, x.o_1.values), ece(x.p_x.values, x.o_x.values)]) * 100)
        for k in ("15", "25", "35"):
            r["br_o" + k] = x["br_o" + k].mean(); r["ll_o" + k] = x["ll_o" + k].mean()
            r["o" + k] = f"{x['p_o'+k].mean()*100:.1f}/{x['o_o'+k].mean()*100:.1f}"; r["ece_o" + k] = ece(x["p_o" + k].values, x["o_o" + k].values) * 100
        for nm, _, _ in BANDS: r["b" + nm] = f"{x['p_b'+nm].mean()*100:.1f}/{x['o_b'+nm].mean()*100:.1f}"
        R[per] = r
    return R

def boot_ci(d, week, B=600, seed=1):
    """media e IC 95% con bootstrap a blocchi per settimana"""
    g = pd.Series(d).groupby(week.values); s = g.sum().values; c = g.count().values
    rng = np.random.default_rng(seed); k = len(s)
    if k < 3: return d.mean(), np.nan, np.nan
    idx = rng.integers(0, k, (B, k)); bs = s[idx].sum(1) / c[idx].sum(1)
    return d.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)

def compare(df, XA, XB, key="ll_score"):
    """B contro A: differenza media (B − A, negativa = B migliore), IC 95%, % campionati migliorati, per periodo"""
    d = (XB[key] - XA[key]).values; week = (df.d // 7)
    R = {}
    for per in ("scelta", "verifica", "holdout"):
        m = (df.per == per).values
        mu, lo, hi = boot_ci(d[m], week[m])
        lg = pd.Series(d[m]).groupby(df.lg.values[m]).mean()
        base = XA[key].values[m].mean()
        R[per] = dict(diff=mu, lo=lo, hi=hi, pct=100 * mu / base, camp=f"{(lg < 0).sum()}/{len(lg)}", sig=bool(hi < 0) if mu < 0 else (bool(lo > 0) and "peggio"))
    return R

def rule(R):
    v, h = R["verifica"], R["holdout"]
    nv, tv = map(int, v["camp"].split("/"))
    return bool(v["hi"] < 0 and h["diff"] < 0 and nv > tv / 2)

def fit_rho(lh, la, yh, ya):
    lh, la, yh, ya = map(np.asarray, (lh, la, yh, ya))
    m00, m01, m10, m11 = (yh == 0) & (ya == 0), (yh == 0) & (ya == 1), (yh == 1) & (ya == 0), (yh == 1) & (ya == 1)
    def nll(r):
        # verosimiglianza Dixon-Coles con la normalizzazione della griglia (come l'app)
        t = np.zeros(len(lh))
        t[m00] = np.log(np.maximum(1e-9, 1 - lh[m00] * la[m00] * r)); t[m01] = np.log(np.maximum(1e-9, 1 + lh[m01] * r))
        t[m10] = np.log(np.maximum(1e-9, 1 + la[m10] * r)); t[m11] = np.log(max(1e-9, 1 - r))
        # costante di normalizzazione: 1 + r·(lh·la·p00·(-1)... ) → calcolata esatta sui 4 casi
        p0h, p1h, p0a, p1a = np.exp(-lh), lh * np.exp(-lh), np.exp(-la), la * np.exp(-la)
        z = 1 + r * (-lh * la * p0h * p0a + lh * p0h * p1a + la * p1h * p0a - p1h * p1a)
        return -(t - np.log(z)).sum()
    return minimize_scalar(nll, bounds=(-0.25, 0.25), method="bounded").x

def pois_fit(X, y, w=None, offset=None, iters=50):
    """regressione di Poisson (IRLS): log μ = offset + X·b"""
    X = np.asarray(X, float); y = np.asarray(y, float); n, p = X.shape
    w = np.ones(n) if w is None else w; off = np.zeros(n) if offset is None else offset
    b = np.zeros(p); b[0] = np.log(max(y.mean(), 1e-6)) if np.allclose(X[:, 0], 1) else 0
    for _ in range(iters):
        eta = off + X @ b; mu = np.exp(eta); z = eta - off + (y - mu) / mu; W = w * mu
        XtW = X.T * W; bn = np.linalg.solve(XtW @ X + 1e-9 * np.eye(p), XtW @ z)
        if np.max(np.abs(bn - b)) < 1e-10: b = bn; break
        b = bn
    return b

def league_slope(df, lh, la, per):
    m = (df.per == per).values
    S = pd.DataFrame(dict(lg=df.lg.values[m], t=(lh + la)[m], y=(df.yh + df.ya).values[m])).groupby("lg").mean()
    return np.polyfit(np.log(S.t), np.log(S.y), 1)[0]
