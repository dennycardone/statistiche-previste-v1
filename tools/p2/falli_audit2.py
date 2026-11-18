"""Falli · audit, seconda parte (18/11/2026): confronto contro il modello COME IN PRODUZIONE (M0 × arbitro di extra.json con tetto +4%),
perché nello storico dell'app l'arbitro c'è solo dall'autunno 2025. Varianti: arbitro senza tetto, arbitro sui residui del modello,
derby, dispersione (r stimati nello sviluppo). Tabelle per campionato, stagione e fasce di falli attesi. Solo analisi."""
import os, sys, json, math, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lab"))
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
P = pd.read_pickle(os.path.join(REPO, "ricerca", "falli", "audit.pkl"))
J, fA, fR, db = P["J"], P["fA"], P["fR"], P["db"]
from comune import boot, pois_fit
from scipy.stats import nbinom
KK = np.arange(0, 91)
def nbp(mu, r): return nbinom.pmf(KK[None, :], r, r / (r + np.asarray(mu)[:, None]))
def metrics(lh, la, rT=200.0, rt=150.0):
    lh, la = np.asarray(lh), np.asarray(la); yh, ya = J.yh.values.astype(int), J.ya.values.astype(int); yt = yh + ya; tot = lh + la; o = pd.DataFrame(index=J.index)
    lp = lambda y, mu, r: nbinom.logpmf(y, r, r / (r + mu))
    o["ll_team"] = -(lp(yh, lh, rT) + lp(ya, la, rT)); o["ll_tot"] = -lp(yt, tot, rt)
    Ph, Pa = nbp(lh, rT), nbp(la, rT); cA = np.cumsum(Pa, 1); p1 = (Ph[:, 1:] * cA[:, :-1]).sum(1); px = (Ph * Pa).sum(1); p2 = np.clip(1 - p1 - px, 1e-12, 1)
    o1, ox = (yh > ya).astype(float), (yh == ya).astype(float); o2 = 1 - o1 - ox
    o["ll_1x2"] = -np.log(np.clip(np.where(o1 == 1, p1, np.where(ox == 1, px, p2)), 1e-12, 1)); o["br_1x2"] = (p1 - o1) ** 2 + (px - ox) ** 2 + (p2 - o2) ** 2
    for j, off in enumerate((-3, 0, 3)):
        L = np.round(tot) + 0.5 + off; pov = 1 - nbinom.cdf(np.floor(L), rt, rt / (rt + tot)); oo = (yt > L).astype(float)
        o[f"br_ou{j}"] = (pov - oo) ** 2; o[f"ll_ou{j}"] = -np.log(np.clip(np.where(oo == 1, pov, 1 - pov), 1e-12, 1)); o[f"p_ou{j}"] = pov; o[f"o_ou{j}"] = oo
    o["ae_t"] = np.abs(yt - tot); o["se_t"] = (yt - tot) ** 2; o["ae_h"] = np.abs(yh - lh); o["ae_a"] = np.abs(ya - la)
    o["p1"], o["o1"], o["px"], o["ox"], o["tot"] = p1, o1, px, ox, tot
    return o
def ece(p, y, b=10):
    q = np.clip((p * b).astype(int), 0, b - 1); return float(sum(abs(p[q == i].mean() - y[q == i].mean()) * (q == i).sum() for i in range(b) if (q == i).any()) / len(p))
def summ(X):
    out = {}
    for p in ("scelta", "verifica", "holdout"):
        m = (J.per == p).values; x = X[m]
        out[p] = dict(n=int(m.sum()), MAE_tot=round(x.ae_t.mean(), 3), RMSE_tot=round(math.sqrt(x.se_t.mean()), 3), MAE_sq=round((x.ae_h.mean() + x.ae_a.mean()) / 2, 3),
                      LL_sq=round(x.ll_team.mean(), 4), LL_tot=round(x.ll_tot.mean(), 4), LL_1x2=round(x.ll_1x2.mean(), 4), BR_1x2=round(x.br_1x2.mean(), 4),
                      BR_ou=round(np.mean([x[f"br_ou{j}"].mean() for j in range(3)]), 4), LL_ou=round(np.mean([x[f"ll_ou{j}"].mean() for j in range(3)]), 4),
                      ECE_ou=round(np.mean([ece(x[f"p_ou{j}"].values, x[f"o_ou{j}"].values) for j in range(3)]) * 100, 2), ECE_1x2=round((ece(x.p1.values, x.o1.values) + ece(x.px.values, x.ox.values)) / 2 * 100, 2),
                      atteso_reale=f"{x.tot.mean():.2f}/{J.yt.values[m].mean():.2f}")
    return out
def cmp(XA, XB, key):
    out = {}
    for p in ("scelta", "verifica", "holdout"):
        m = (J.per == p).values; d = (XB[key] - XA[key]).values[m]
        mu, lo, hi = boot(d, J.wk.values[m]); _, lo95, hi95 = boot(d, J.wk.values[m], q=(2.5, 97.5)); lg = pd.Series(d).groupby(J.lg.values[m]).mean()
        out[p] = dict(diff=round(mu, 6), lo95=round(lo95, 6), hi95=round(hi95, 6), hi99=round(hi, 6), pct=round(100 * mu / XA[key].values[m].mean(), 4), camp=f"{int((lg < 0).sum())}/{len(lg)}")
    return out
def rule(c, q="hi95"):
    v, h = c["verifica"], c["holdout"]; a, b = map(int, v["camp"].split("/")); return bool(v[q] < 0 and h["diff"] < 0 and a > b / 2)
sc = (J.per == "scelta").values
def fit_offset(Xh, Xa, bh, ba):
    one = np.ones((len(J), 1)); XH = np.hstack([one, Xh]); XA = np.hstack([one, Xa])
    b, se = pois_fit(np.vstack([XH[sc], XA[sc]]), np.r_[J.yh.values[sc], J.ya.values[sc]], np.log(np.r_[bh[sc], ba[sc]]))
    return b, se, bh * np.exp(XH @ b), ba * np.exp(XA @ b)
R = {}
# produzione: M0 × arbitro (extra.json ricostruito per tutti i periodi, tetto +4%)
ph, pa = J.l0h.values * fA, J.l0a.values * fA
fA0 = np.array(fA)   # con tetto
XP = metrics(ph, pa)
# arbitro senza tetto: ricostruisco dal pickle dei modelli
MOD = P["MODELS"]
k_nocap = [k for k in MOD if "senza tetto" in k][0]; k_res = [k for k in MOD if "residui del modello" in k][0]
V = {"P produzione (M0 × arbitro, tetto +4%)": (ph, pa)}
V["P1 arbitro senza tetto"] = MOD[k_nocap]
V["P2 arbitro sui residui del modello (K 10)"] = MOD[k_res]
b, se, lh, la = fit_offset(db[:, None], db[:, None], ph, pa); V["P3 produzione + derby"] = (lh, la); R["coef_derby_su_P"] = [round(b[1], 4), round(se[1], 4)]
b, se, lh, la = fit_offset(db[:, None], db[:, None], *map(np.asarray, MOD[k_nocap])); V["P4 arbitro senza tetto + derby"] = (lh, la); R["coef_derby_su_P1"] = [round(b[1], 4), round(se[1], 4)]
XS = {nm: metrics(*v) for nm, v in V.items()}
# dispersione: r stimati nello sviluppo sulla produzione
from scipy.optimize import minimize_scalar
def r_ml(y, l):
    f = lambda lr: -nbinom.logpmf(y, math.exp(lr), math.exp(lr) / (math.exp(lr) + l)).sum()
    return math.exp(minimize_scalar(f, bounds=(math.log(5), math.log(5000)), method="bounded").x)
rT = r_ml(np.r_[J.yh[sc], J.ya[sc]], np.r_[V["P4 arbitro senza tetto + derby"][0][sc], V["P4 arbitro senza tetto + derby"][1][sc]]); rt = r_ml(J.yt.values[sc], (V["P4 arbitro senza tetto + derby"][0] + V["P4 arbitro senza tetto + derby"][1])[sc])
R["r_ML_sviluppo"] = [round(rT, 1), round(rt, 1)]
rTr, rtr = float(round(rT, -1)), float(round(rt, -1))
XS[f"P5 = P4 con r squadra {rTr:.0f} e r totale {rtr:.0f}"] = metrics(*V["P4 arbitro senza tetto + derby"], rT=rTr, rt=rtr)
R["modelli"] = {}
print(f"{'modello':52} {'LL sq.':>8} {'LL tot':>8} {'LL 1X2':>8} {'Br 1X2':>7} {'Br O/U':>7} {'ECE O/U':>7} {'ECE 1X2':>7} {'MAE':>6} {'RMSE':>6} att/reale")
for nm, X in XS.items():
    S_ = summ(X); R["modelli"][nm] = {"riepilogo": S_}
    if nm != "P produzione (M0 × arbitro, tetto +4%)":
        c = {k: cmp(XP, X, k) for k in ("ll_team", "ll_tot", "ll_1x2", "br_1x2", "br_ou1", "ll_ou1", "se_t", "ae_t")}
        R["modelli"][nm]["contro_produzione"] = c; R["modelli"][nm]["regola"] = {"ll_squadra_95": rule(c["ll_team"]), "ll_squadra_99": rule(c["ll_team"], "hi99"), "ll_totale_95": rule(c["ll_tot"]), "1x2_95": rule(c["ll_1x2"])}
    for p in ("verifica", "holdout"):
        s = S_[p]; print(f"{(nm[:44] + ' · ' + p[:3]):52} {s['LL_sq']:8.4f} {s['LL_tot']:8.4f} {s['LL_1x2']:8.4f} {s['BR_1x2']:7.4f} {s['BR_ou']:7.4f} {s['ECE_ou']:7.2f} {s['ECE_1x2']:7.2f} {s['MAE_tot']:6.3f} {s['RMSE_tot']:6.3f} {s['atteso_reale']}")
print()
for nm, r in R["modelli"].items():
    if "contro_produzione" not in r: continue
    c = r["contro_produzione"]
    print(nm, r["regola"]); [print("   ", k, {p: (v["diff"], v["lo95"], v["hi95"], v["pct"], v["camp"]) for p, v in c[k].items() if p != "scelta"}) for k in ("ll_team", "ll_tot", "ll_1x2", "br_ou1")]
# finale scelto per le tabelle di dettaglio: il migliore che passa
best = "P4 arbitro senza tetto + derby"; XB = XS[best]
det = {}
for p in ("verifica", "holdout"):
    m = (J.per == p).values
    d = (XB.ll_team - XP.ll_team)[m]; dt = (XB.ll_tot - XP.ll_tot)[m]
    det[p] = {"per_campionato_ll_squadra": {l: round(v, 5) for l, v in d.groupby(J.lg[m]).mean().items()},
              "per_campionato_ll_totale": {l: round(v, 5) for l, v in dt.groupby(J.lg[m]).mean().items()}}
seas = {}
for s_, g in J.groupby(J.d.str[:7].map(lambda x: x[:4] + ("-2" if x[5:7] >= "07" else "-1"))):
    idx = g.index; seas[s_] = dict(n=len(idx), produzione=round(XP.ll_team[idx].mean(), 4), nuovo=round(XB.ll_team[idx].mean(), 4))
det["per_semestre"] = seas
q = pd.qcut(XP.tot, 5, labels=False)
det["per_fasce_falli_attesi"] = {int(i): dict(atteso_prod=round(XP.tot[q == i].mean(), 2), atteso_nuovo=round(XB.tot[q == i].mean(), 2), reale=round(J.yt[q == i].mean(), 2),
                                           over_prod=f"{XP.p_ou1[q == i].mean()*100:.1f}/{XP.o_ou1[q == i].mean()*100:.1f}", over_nuovo=f"{XB.p_ou1[q == i].mean()*100:.1f}/{XB.o_ou1[q == i].mean()*100:.1f}") for i in range(5)}
R["dettaglio_finale"] = det
print(json.dumps(det["per_fasce_falli_attesi"], ensure_ascii=False)); print(json.dumps(det["per_semestre"], ensure_ascii=False))
for p in ("verifica", "holdout"):
    v = det[p]["per_campionato_ll_squadra"]; print(p, "campionati peggiorati:", {k: x for k, x in v.items() if x > 0})
print("r ML", R["r_ML_sviluppo"], "derby su P", R["coef_derby_su_P"], "su P1", R["coef_derby_su_P1"])
json.dump(R, open(os.path.join(REPO, "ricerca", "falli", "audit2.json"), "w"), indent=1, ensure_ascii=False, default=float)
# confronti a coppie per il passo finale (ogni modifica da sola)
pairs = {"r stimati (su P3) contro P3": (metrics(*V["P3 produzione + derby"]), metrics(*V["P3 produzione + derby"], rT=rTr, rt=rtr)),
         "togliere il tetto (P4 contro P3)": (XS["P3 produzione + derby"], XS["P4 arbitro senza tetto + derby"]),
         "r stimati (P5 contro P4)": (XS["P4 arbitro senza tetto + derby"], XS[f"P5 = P4 con r squadra {rTr:.0f} e r totale {rtr:.0f}"]),
         "solo r stimati (su P) contro P": (XP, metrics(ph, pa, rT=rTr, rt=rtr))}
R["coppie"] = {}
for nm, (A, B) in pairs.items():
    c = {k: cmp(A, B, k) for k in ("ll_team", "ll_tot", "ll_1x2", "br_1x2", "br_ou1")}
    R["coppie"][nm] = {"confronti": c, "regola": {k: rule(c[k]) for k in c}}
    print(nm, {k: rule(c[k]) for k in c}); [print("   ", k, {p: (v["diff"], v["lo95"], v["hi95"], v["pct"], v["camp"]) for p, v in c[k].items() if p != "scelta"}) for k in ("ll_team", "ll_tot", "ll_1x2", "br_ou1")]
XQ = metrics(*V["P3 produzione + derby"], rT=rTr, rt=rtr); R["modelli"]["P6 = P3 (con tetto) + r stimati"] = {"riepilogo": summ(XQ), "contro_produzione": {k: cmp(XP, XQ, k) for k in ("ll_team", "ll_tot", "ll_1x2", "br_1x2", "br_ou1", "ll_ou1", "se_t", "ae_t")}}
for p in ("verifica", "holdout"):
    s = R["modelli"]["P6 = P3 (con tetto) + r stimati"]["riepilogo"][p]; print("P6", p, s)
for p in ("verifica", "holdout"):
    m = (J.per == p).values; print(p, "Over sulla linea vicina prod", f"{XP.p_ou1[m].mean()*100:.1f}/{XP.o_ou1[m].mean()*100:.1f}", "P6", f"{XQ.p_ou1[m].mean()*100:.1f}/{XQ.o_ou1[m].mean()*100:.1f}",
          "linea -3", f"{XP.p_ou0[m].mean()*100:.1f}/{XQ.p_ou0[m].mean()*100:.1f}/{XP.o_ou0[m].mean()*100:.1f}", "linea +3", f"{XP.p_ou2[m].mean()*100:.1f}/{XQ.p_ou2[m].mean()*100:.1f}/{XP.o_ou2[m].mean()*100:.1f}")
json.dump(R, open(os.path.join(REPO, "ricerca", "falli", "audit2.json"), "w"), indent=1, ensure_ascii=False, default=float)
