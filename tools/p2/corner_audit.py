"""Corner · audit e backtest (18/11/2026, Denny). Solo analisi: nessuna modifica all'app.
Ingresso: ricerca/corner/feat.pkl (corner_dati.py): corner attesi dell'app (M0, soli dati precedenti) + caratteristiche pre-partita.
Periodi: sviluppo (stima) fino al 30/6/2024, verifica 2024-25, holdout da luglio 2025 (mai usato per stimare o scegliere).
Metriche come l'app: corner per squadra Binomiale Negativa r = 12, totale r = 60, 1X2 con copula gaussiana −0,20.
Uscita: ricerca/corner/audit.json + stampa delle tabelle."""
import os, sys, json, math, numpy as np, pandas as pd
from scipy.stats import nbinom, norm, poisson
from scipy.optimize import minimize_scalar
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lab"))
from comune import RIC, pois_fit, boot
OUT = os.path.join(RIC, "corner"); R = {}
log = lambda *a: print(*a, flush=True)
J = pd.read_pickle(os.path.join(OUT, "feat.pkl"))
J["yt"] = J.yh + J.ya
# riferimento del campionato per sede (ultimi 365 giorni): dove manca (campionato appena entrato) media del campionato nel periodo di sviluppo
for c in ("mH_c", "mA_c"):
    J[c] = J[c].fillna(J.groupby("lg")[c].transform("mean")).fillna(J[c].mean())
PER = ("scelta", "verifica", "holdout"); M = {p: (J.per == p).values for p in PER}; sc = M["scelta"]
RT, RTOT, COP = 12.0, 60.0, -0.20
log("partite:", len(J), {p: int(M[p].sum()) for p in PER})
# ---------------- copula gaussiana su due Binomiali Negative (stessa formula di h2hCop nell'app)
BX = np.array([.9815606342467191, .9041172563704750, .7699026741943050, .5873179542866171, .3678314989981802, .1252334085114692])
BW = np.array([.04717533638651177, .1069393259953183, .1600783285433464, .2031674267230659, .2334925365383547, .2491470458134029])
KM = 31; KK = np.arange(KM)
def nbp(mu, r): return nbinom.pmf(KK[None, :], r, r / (r + np.asarray(mu, float)[:, None]))
def joint(lh, la, r=RT, rho=COP, chunk=2500):
    """per ogni partita: P(1), P(X), P(2) e la matrice congiunta (restituita solo se serve) con la copula"""
    out = []
    for s in range(0, len(lh), chunk):
        ph, pa = nbp(lh[s:s + chunk], r), nbp(la[s:s + chunk], r)
        Fh, Fa = np.clip(np.cumsum(ph, 1), 1e-13, 1 - 1e-13), np.clip(np.cumsum(pa, 1), 1e-13, 1 - 1e-13)
        zh, za = norm.ppf(Fh), norm.ppf(Fa)
        if rho == 0: C = Fh[:, :, None] * Fa[:, None, :]
        else:
            asr = math.asin(rho) / 2; xs = np.r_[1 - BX, 1 + BX]; ws = np.r_[BW, BW]; sn = np.sin(asr * xs); iv = 1 / (1 - sn ** 2)
            hk = zh[:, :, None] * za[:, None, :]; hs = (zh[:, :, None] ** 2 + za[:, None, :] ** 2) / 2
            t = np.zeros_like(hk)
            for q in range(12): t += ws[q] * np.exp((sn[q] * hk - hs) * iv[q])
            C = t * asr / (2 * math.pi) + Fh[:, :, None] * Fa[:, None, :]
        C = np.pad(C, ((0, 0), (1, 0), (1, 0)))
        P = np.clip(C[:, 1:, 1:] - C[:, :-1, 1:] - C[:, 1:, :-1] + C[:, :-1, :-1], 0, None); P /= P.sum((1, 2), keepdims=True)
        out.append(P)
    return np.concatenate(out)
def x12(P):
    i, j = np.meshgrid(KK, KK, indexing="ij")
    return (P * (i > j)).sum((1, 2)), (P * (i == j)).sum((1, 2))
# ---------------- metriche per partita
TL = (7.5, 8.5, 9.5, 10.5, 11.5, 12.5); SL = (3.5, 4.5, 5.5, 6.5)
lp = lambda y, mu, r: nbinom.logpmf(y, r, r / (r + mu))
def ovr(L, mu, r): return 1 - nbinom.cdf(np.floor(L), r, r / (r + mu))
def bll(p, o): return -np.log(np.clip(np.where(o == 1, p, 1 - p), 1e-12, 1))
def metrics(lh, la, rt=RTOT, rT=RT, rho=COP):
    yh, ya = J.yh.values, J.ya.values; yt = yh + ya; tot = lh + la
    o = pd.DataFrame(index=J.index)
    o["ll_team"] = -(lp(yh, lh, rT) + lp(ya, la, rT)) / 2; o["ll_h"] = -lp(yh, lh, rT); o["ll_a"] = -lp(ya, la, rT)
    o["ll_tot"] = -lp(yt, tot, rt)
    p1, px = np.zeros(len(lh)), np.zeros(len(lh))
    for c0 in range(0, len(lh), 2500):
        P = joint(lh[c0:c0 + 2500], la[c0:c0 + 2500], rT, rho); p1[c0:c0 + 2500], px[c0:c0 + 2500] = x12(P)
    p2 = np.clip(1 - p1 - px, 1e-12, 1)
    o1, ox = (yh > ya).astype(float), (yh == ya).astype(float); o2 = 1 - o1 - ox
    o["ll_1x2"] = -np.log(np.clip(np.where(o1 == 1, p1, np.where(ox == 1, px, p2)), 1e-12, 1)); o["br_1x2"] = (p1 - o1) ** 2 + (px - ox) ** 2 + (p2 - o2) ** 2
    o["p1"], o["o1"], o["px"], o["ox"] = p1, o1, px, ox
    # Over/Under totale: linea vicina all'atteso (come le linee dei book) e linee fisse
    # stessa linea per tutti i modelli: quella vicina all'atteso dell'APP (le linee dei book seguono l'atteso; così i modelli si confrontano sulle stesse linee)
    L = np.floor(J.l0h.values + J.l0a.values) + 0.5; p = ovr(L, tot, rt); oo = (yt > L).astype(float)
    o["br_ou"], o["ll_ou"], o["p_ou"], o["o_ou"] = (p - oo) ** 2, bll(p, oo), p, oo
    for L in TL:
        p = ovr(L, tot, rt); oo = (yt > L).astype(float); o[f"br_t{L}"], o[f"ll_t{L}"] = (p - oo) ** 2, bll(p, oo)
    o["br_tfix"] = o[[f"br_t{L}" for L in TL]].mean(1); o["ll_tfix"] = o[[f"ll_t{L}" for L in TL]].mean(1)
    # Over/Under per squadra (r = 12): linea vicina all'atteso e linee fisse
    br, lls, ps, os_ = [], [], [], []
    for mu, y, mapp in ((lh, yh, J.l0h.values), (la, ya, J.l0a.values)):
        L = np.floor(mapp) + 0.5; p = ovr(L, mu, rT); oo = (y > L).astype(float); br.append((p - oo) ** 2); lls.append(bll(p, oo)); ps.append(p); os_.append(oo)
    o["br_sq"], o["ll_sq"] = (br[0] + br[1]) / 2, (lls[0] + lls[1]) / 2; o["p_sqh"], o["o_sqh"], o["p_sqa"], o["o_sqa"] = ps[0], os_[0], ps[1], os_[1]
    fb, fl = [], []
    for L in SL:
        for mu, y in ((lh, yh), (la, ya)):
            p = ovr(L, mu, rT); oo = (y > L).astype(float); fb.append((p - oo) ** 2); fl.append(bll(p, oo))
    o["br_sqfix"], o["ll_sqfix"] = np.mean(fb, 0), np.mean(fl, 0)
    o["ae_t"], o["se_t"] = np.abs(yt - tot), (yt - tot) ** 2
    o["ae_sq"], o["se_sq"] = (np.abs(yh - lh) + np.abs(ya - la)) / 2, ((yh - lh) ** 2 + (ya - la) ** 2) / 2
    o["tot"], o["lh"], o["la"] = tot, lh, la
    return o
def ece(p, y, b=10):
    q = np.clip((p * b).astype(int), 0, b - 1); return float(sum(abs(p[q == i].mean() - y[q == i].mean()) * (q == i).sum() for i in range(b) if (q == i).any()) / len(p))
KEYS = ["ll_team", "ll_tot", "ll_1x2", "br_1x2", "ll_ou", "br_ou", "ll_tfix", "br_tfix", "ll_sq", "br_sq", "ll_sqfix", "br_sqfix", "ae_t", "se_t", "ae_sq", "se_sq"]
def summary(X, mask=None):
    out = {}
    for p in PER:
        m = M[p] if mask is None else M[p] & mask; x = X[m]
        if not m.any(): continue
        out[p] = dict(n=int(m.sum()), mae_tot=round(x.ae_t.mean(), 4), rmse_tot=round(math.sqrt(x.se_t.mean()), 4), mae_sq=round(x.ae_sq.mean(), 4), rmse_sq=round(math.sqrt(x.se_sq.mean()), 4),
                      ll_team=round(x.ll_team.mean(), 5), ll_tot=round(x.ll_tot.mean(), 5), ll_1x2=round(x.ll_1x2.mean(), 5), br_1x2=round(x.br_1x2.mean(), 5),
                      ll_ou=round(x.ll_ou.mean(), 5), br_ou=round(x.br_ou.mean(), 5), ll_tfix=round(x.ll_tfix.mean(), 5), br_tfix=round(x.br_tfix.mean(), 5),
                      ll_sq=round(x.ll_sq.mean(), 5), br_sq=round(x.br_sq.mean(), 5), br_sqfix=round(x.br_sqfix.mean(), 5),
                      ece_ou=round(ece(x.p_ou.values, x.o_ou.values) * 100, 2), ece_sq=round(ece(np.r_[x.p_sqh.values, x.p_sqa.values], np.r_[x.o_sqh.values, x.o_sqa.values]) * 100, 2),
                      ece_1=round(ece(x.p1.values, x.o1.values) * 100, 2), ece_x=round(ece(x.px.values, x.ox.values) * 100, 2),
                      atteso_reale=f"{x.tot.mean():.2f}/{J.yt.values[m].mean():.2f}", over_linea=f"{x.p_ou.mean()*100:.1f}/{x.o_ou.mean()*100:.1f}",
                      casa=f"{x.lh.mean():.2f}/{J.yh.values[m].mean():.2f}", ospite=f"{x.la.mean():.2f}/{J.ya.values[m].mean():.2f}")
    return out
def cmp(XA, XB, keys=("ll_team", "ll_tot", "ll_1x2", "br_1x2", "ll_ou", "br_ou", "ll_sq", "br_sq", "ae_t", "se_t", "ae_sq")):
    out = {}
    for key in keys:
        out[key] = {}
        for p in PER:
            m = M[p]; d = (XB[key] - XA[key]).values[m]
            mu, lo, hi = boot(d, J.wk.values[m]); _, lo95, hi95 = boot(d, J.wk.values[m], q=(2.5, 97.5))
            lg = pd.Series(d).groupby(J.lg.values[m]).mean()
            out[key][p] = dict(diff=round(mu, 6), lo95=round(lo95, 6), hi95=round(hi95, 6), lo99=round(lo, 6), hi99=round(hi, 6), pct=round(100 * mu / XA[key].values[m].mean(), 3), camp=f"{int((lg < 0).sum())}/{len(lg)}")
    return out
def passes(c):
    v, h = c["verifica"], c["holdout"]; a, b = map(int, v["camp"].split("/"))
    return dict(regola95=bool(v["hi95"] < 0 and h["diff"] < 0 and a > b / 2), regola99=bool(v["hi99"] < 0 and h["diff"] < 0 and a > b / 2))
def fit(Xh, Xa, base_h, base_a):
    one = np.ones((len(J), 1)); XH = np.hstack([one, Xh]); XA = np.hstack([one, Xa])
    b, se = pois_fit(np.vstack([XH[sc], XA[sc]]), np.r_[J.yh.values[sc], J.ya.values[sc]], np.log(np.r_[base_h[sc], base_a[sc]]))
    return b, se, base_h * np.exp(XH @ b), base_a * np.exp(XA @ b)
def fx(names):
    return J[["h_" + n for n in names]].values.astype(float), J[["a_" + n for n in names]].values.astype(float)
# ================= 1. modello attuale
X0 = metrics(J.l0h.values, J.l0a.values); R["app"] = summary(X0)
b, se, lh, la = fit(np.zeros((len(J), 0)), np.zeros((len(J), 0)), J.l0h.values, J.l0a.values); XC = metrics(lh, la)
R["app_costante"] = dict(costante=round(float(b[0]), 5), riepilogo=summary(XC))
log("app", json.dumps(R["app"], ensure_ascii=False)); log("app + costante", round(float(b[0]), 5))
# ================= 2. distribuzione
yh, ya, yt = J.yh.values, J.ya.values, J.yt.values; lh0, la0 = J.l0h.values, J.l0a.values
D = {}
for p in PER:
    m = M[p]
    def rml(y, mu):
        f = lambda lr: -lp(y, mu, math.exp(lr)).sum(); r = minimize_scalar(f, bounds=(0, 8), method="bounded"); return round(math.exp(r.x), 2)
    ys = np.r_[yh[m], ya[m]]
    D[p] = dict(media_squadra=round(ys.mean(), 3), var_squadra=round(ys.var(), 3), media_tot=round(yt[m].mean(), 3), var_tot=round(yt[m].var(), 3),
                asimmetria_tot=round(float(pd.Series(yt[m]).skew()), 3), curtosi_tot=round(float(pd.Series(yt[m]).kurt()), 3),
                r_ml_squadra=rml(np.r_[yh[m], ya[m]], np.r_[lh0[m], la0[m]]), r_ml_casa=rml(yh[m], lh0[m]), r_ml_ospite=rml(ya[m], la0[m]), r_ml_tot=rml(yt[m], lh0[m] + la0[m]),
                # dispersione condizionata: varianza dei residui contro la media prevista (Poisson = 1)
                disp_squadra=round(float(((ys - np.r_[lh0[m], la0[m]]) ** 2).mean() / np.r_[lh0[m], la0[m]].mean()), 3),
                disp_tot=round(float(((yt[m] - lh0[m] - la0[m]) ** 2).mean() / (lh0[m] + la0[m]).mean()), 3),
                corr_grezza=round(float(np.corrcoef(yh[m], ya[m])[0, 1]), 4), corr_residui=round(float(np.corrcoef(yh[m] - lh0[m], ya[m] - la0[m])[0, 1]), 4),
                ll_poisson_squadra=round(float(-(poisson.logpmf(yh[m], lh0[m]) + poisson.logpmf(ya[m], la0[m])).mean() / 2), 5),
                ll_nb12_squadra=round(float(X0.ll_team.values[m].mean()), 5),
                ll_poisson_tot=round(float(-poisson.logpmf(yt[m], lh0[m] + la0[m]).mean()), 5), ll_nb60_tot=round(float(X0.ll_tot.values[m].mean()), 5))
    # code: frequenze osservate e attese (NB r=60) di totali estremi
    tot = lh0[m] + la0[m]
    for L in (5, 15, 18):
        if L == 5: obs, exp = (yt[m] <= L).mean(), nbinom.cdf(L, RTOT, RTOT / (RTOT + tot)).mean()
        else: obs, exp = (yt[m] >= L).mean(), (1 - nbinom.cdf(L - 1, RTOT, RTOT / (RTOT + tot))).mean()
        D[p][f"coda_{'<=' if L == 5 else '>='}{L}"] = f"{obs*100:.2f}% osservato / {exp*100:.2f}% previsto"
R["distribuzione"] = D; log("distribuzione", json.dumps(D, ensure_ascii=False, indent=0))
# totale: NB r=60 diretto contro somma delle due squadre con la copula (stesse λ): verosimiglianza del totale
DT = {}
for rho in (0.0, -0.1, -0.2, -0.3):
    P = joint(lh0, la0, RT, rho)
    Pf = P[:, :, ::-1]; ptot = np.stack([np.trace(Pf, offset=KM - 1 - k, axis1=1, axis2=2) for k in range(2 * KM - 1)], 1)
    llt = -np.log(np.clip(ptot[np.arange(len(J)), yt], 1e-12, 1)); llj = -np.log(np.clip(P[np.arange(len(J)), np.minimum(yh, KM - 1), np.minimum(ya, KM - 1)], 1e-12, 1))
    p1, px = x12(P); p2 = np.clip(1 - p1 - px, 1e-12, 1); o1, ox = (yh > ya), (yh == ya)
    l12 = -np.log(np.clip(np.where(o1, p1, np.where(ox, px, p2)), 1e-12, 1))
    DT[str(rho)] = {p: dict(ll_tot_somma=round(float(llt[M[p]].mean()), 5), ll_congiunta=round(float(llj[M[p]].mean()), 5), ll_1x2=round(float(l12[M[p]].mean()), 5)) for p in PER}
    del P
for p in PER: DT["nb60_diretto"] = DT.get("nb60_diretto", {}); DT["nb60_diretto"][p] = round(float(X0.ll_tot.values[M[p]].mean()), 5)
R["totale_somma_o_diretto"] = DT; log("totale: somma con copula o NB diretto", json.dumps(DT))
# ================= 3. modelli da zero (riferimento del campionato) e varianti sull'app
mH, mA = J.mH_c.values, J.mA_c.values; mP = (mH + mA) / 2
Z = np.zeros((len(J), 0))
MOD = {}
def run(name, Xh, Xa, bh, ba, names):
    b, se, lh, la = fit(Xh, Xa, bh, ba); X = metrics(lh, la)
    MOD[name] = dict(X=X, lh=lh, la=la, coef={n: [round(float(x), 5), round(float(s), 5)] for n, x, s in zip(["costante"] + names, b, se)})
    log(name, MOD[name]["coef"], {p: round(float(X.ll_team.values[M[p]].mean() - XC.ll_team.values[M[p]].mean()), 5) for p in PER})
    return X
# 2. media del campionato: (a) unica per le due sedi + casa, (b) per sede
home = np.ones((len(J), 1)); away = np.zeros((len(J), 1))
run("lega_unica+casa", home, away, mP, mP, ["casa"])
run("lega_per_sede", Z, Z, mH, mA, [])
# 3. rating attacco/difesa (365 giorni, shrinkage 5 partite)
R_ = ["att365", "def365"]; run("rating", *fx(R_), mH, mA, R_)
# 4. forma: ultime 5, ultime 10, decadimento (emivita 60 giorni)
for nm, ff in (("forma5", ["att5", "def5"]), ("forma10", ["att10", "def10"]), ("formaE", ["attE", "defE"])):
    run(nm, *fx(ff), mH, mA, ff); run("rating+" + nm, *fx(R_ + ff), mH, mA, R_ + ff)
# 5. fattore campo della squadra (sede rispetto al suo solito)
run("rating+campo", *fx(R_ + ["attV", "defV"]), mH, mA, R_ + ["attV", "defV"])
# 6. contesto (storico delle squadre, ultime 10, shrinkage)
J["h_forza"] = np.log(J.gh / J.ga).fillna(0); J["a_forza"] = -J.h_forza
CT = ["att_s", "def_s", "att_st", "def_st", "att_bl", "def_bl", "att_ib", "def_ib", "poss", "forza"]
run("rating+contesto", *fx(R_ + CT), mH, mA, R_ + CT)
ALL = R_ + ["att5", "def5", "att10", "def10", "attV", "defV"] + CT
run("tutto_da_zero", *fx(ALL), mH, mA, ALL)
# varianti sull'app (previsione dell'app fissa, coefficienti nuovi stimati nel periodo di sviluppo)
VAR = {"+forma10": ["att10", "def10"], "+formaE": ["attE", "defE"], "+campo": ["attV", "defV"], "+rating365": R_,
       "+tiri": ["att_s", "def_s"], "+tiri_porta": ["att_st", "def_st"], "+bloccati": ["att_bl", "def_bl"], "+in_area": ["att_ib", "def_ib"], "+xg": ["att_xg", "def_xg"],
       "+possesso": ["poss"], "+forza": ["forza"]}
for nm, ff in VAR.items(): run("app" + nm, *fx(ff), J.l0h.values, J.l0a.values, ff)
# calibrazione del campionato: (a) costante per campionato stimata nello sviluppo, (b) mobile: corner reali / attesi dell'app negli ultimi 180 giorni (shrinkage 100 partite)
lgs = sorted(J.lg.unique()); DL = np.array([[1.0 if l == g else 0.0 for g in lgs] for l in J.lg.values])
DLs = DL[:, [k for k, g in enumerate(lgs) if (J.lg.values[sc] == g).sum() >= 100]]
# lo stesso coefficiente per casa e ospite (una costante per campionato), stimato nello sviluppo; i campionati con meno di 100 partite nello sviluppo restano all'app
b, se, lh, la = fit(DLs, DLs, J.l0h.values, J.l0a.values); MOD["app+costante_campionato"] = dict(X=metrics(lh, la), lh=lh, la=la, coef={"n_campionati": DLs.shape[1]})
cal_h, cal_a = np.zeros(len(J)), np.zeros(len(J))
for g, G in J.groupby("lg"):
    t = G.t.values; idx = G.index.values
    for yc, lc, out in (("yh", "l0h", cal_h), ("ya", "l0a", cal_a)):
        cy = np.r_[0, np.cumsum(G[yc].values)]; cl = np.r_[0, np.cumsum(G[lc].values)]
        lo = np.searchsorted(t, t - 180, "left"); hi = np.searchsorted(t, t, "left"); n = hi - lo
        sy, sl = cy[hi] - cy[lo], cl[hi] - cl[lo]; eb = np.where(n > 0, sl / np.maximum(n, 1), 1.0)
        out[idx] = np.log((sy + 100 * eb) / (sl + 100 * eb))
J["h_cal"], J["a_cal"] = cal_h, cal_a
run("app+calibrazione_mobile", *fx(["cal"]), J.l0h.values, J.l0a.values, ["cal"])
# stagionalità: inizio di stagione (primi 35 giorni del campionato nella stagione)
st0 = J.groupby(["lg", "se"]).t.transform("min"); J["h_inizio"] = (J.t - st0 < 35).astype(float); J["a_inizio"] = J.h_inizio
run("app+inizio_stagione", *fx(["inizio"]), J.l0h.values, J.l0a.values, ["inizio"])
# ---------------- confronto con l'app + costante
TAB = {}
for nm, v in MOD.items():
    c = cmp(XC, v["X"]); TAB[nm] = dict(coefficienti=v["coef"], riepilogo=summary(v["X"]), contro_app_costante=c, regola_squadra=passes(c["ll_team"]), regola_totale=passes(c["ll_tot"]),
                                        regola_1x2=passes(c["ll_1x2"]))
R["modelli"] = TAB
log("\n=== confronto con app + costante (diff ll per squadra; negativo = meglio) ===")
for nm, v in TAB.items():
    c = v["contro_app_costante"]
    log(f"{nm:28s} " + " | ".join(f"{p[:4]} sq {c['ll_team'][p]['diff']:+.5f} [{c['ll_team'][p]['lo99']:+.5f},{c['ll_team'][p]['hi99']:+.5f}] {c['ll_team'][p]['camp']} tot {c['ll_tot'][p]['diff']:+.5f} 1x2 {c['ll_1x2'][p]['diff']:+.5f}" for p in PER)
        + f"  regole sq {v['regola_squadra']} tot {v['regola_totale']} 1x2 {v['regola_1x2']}")
pickle_path = os.path.join(OUT, "modelli.pkl"); pd.to_pickle({k: dict(lh=v["lh"], la=v["la"]) for k, v in MOD.items()}, pickle_path)
json.dump(R, open(os.path.join(OUT, "audit.json"), "w"), indent=1, ensure_ascii=False, default=float)
log("fatto")
