"""Corner · audit, seconda parte (18/11/2026, Denny). Solo analisi: nessuna modifica all'app.
Riusa le funzioni di corner_audit.py (stessi dati, metriche e periodi) e prova: contrazione verso la media del campionato (calibrazione per
fasce), dispersione r (totale e per squadra, casa/ospite), combinazione delle varianti promosse, risultati per campionato, stagione, fascia,
sede e capacità di distinguere le squadre. Uscita: ricerca/corner/audit2.json."""
import os, re
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "corner_audit.py")).read()
exec(src[:src.index("# ================= 1. modello attuale")])
X0 = metrics(J.l0h.values, J.l0a.values)
b, se, lhC, laC = fit(np.zeros((len(J), 0)), np.zeros((len(J), 0)), J.l0h.values, J.l0a.values); XC = metrics(lhC, laC)
MP = pd.read_pickle(os.path.join(OUT, "modelli.pkl")); A1 = json.load(open(os.path.join(OUT, "audit.json")))
R2 = {}
mH, mA = J.mH_c.values, J.mA_c.values
# ---------------- 1. contrazione: le previsioni dell'app sono troppo distanti dalla media del campionato?
J["h_contr"] = np.log(J.l0h / mH); J["a_contr"] = np.log(J.l0a / mA)
MOD2 = {}
def run2(name, Xh, Xa, bh, ba, names, rT=RT, rt=RTOT):
    b, se, lh, la = fit(Xh, Xa, bh, ba); X = metrics(lh, la, rt=rt, rT=rT)
    c = cmp(XC, X); MOD2[name] = dict(lh=lh, la=la, X=X)
    R2[name] = dict(coefficienti={n: [round(float(x), 5), round(float(s), 5)] for n, x, s in zip(["costante"] + names, b, se)}, riepilogo=summary(X), contro_app_costante=c,
                    regola_squadra=passes(c["ll_team"]), regola_totale=passes(c["ll_tot"]), regola_1x2=passes(c["ll_1x2"]))
    log(name, R2[name]["coefficienti"], {p: (c["ll_team"][p]["diff"], c["ll_team"][p]["hi99"], c["ll_team"][p]["camp"], c["ll_tot"][p]["diff"], c["ll_1x2"][p]["diff"]) for p in PER},
        R2[name]["regola_squadra"], R2[name]["regola_totale"])
    return X
run2("app+contrazione", *fx(["contr"]), J.l0h.values, J.l0a.values, ["contr"])
# contrazione separata per casa e ospite
J["h_contrH"], J["a_contrH"] = J.h_contr, 0.0; J["h_contrA"], J["a_contrA"] = 0.0, J.a_contr
run2("app+contrazione_sede", *fx(["contrH", "contrA"]), J.l0h.values, J.l0a.values, ["contrH", "contrA"])
# ---------------- 2. dispersione: r stimati (sviluppo) al posto di 12 e 60
def rml(y, mu):
    f = lambda lr: -lp(y, mu, math.exp(lr)).sum(); r = minimize_scalar(f, bounds=(0, 8), method="bounded"); return math.exp(r.x)
r_tot_s = rml(J.yt.values[sc], (J.l0h + J.l0a).values[sc]); r_sq_s = rml(np.r_[J.yh.values[sc], J.ya.values[sc]], np.r_[J.l0h.values[sc], J.l0a.values[sc]])
log("r stimati nello sviluppo: totale", r_tot_s, "squadra", r_sq_s)
XR = metrics(J.l0h.values, J.l0a.values, rt=round(r_tot_s), rT=round(r_sq_s, 1))
R2["dispersione"] = dict(r_tot_sviluppo=round(r_tot_s, 2), r_squadra_sviluppo=round(r_sq_s, 2), app_r_stimati=summary(XR), contro_app=cmp(X0, XR, ("ll_tot", "ll_ou", "br_ou", "ll_team", "ll_sq", "br_sq", "ll_1x2")))
for rt in (60, 70, 80, 100):
    Xr = metrics(J.l0h.values, J.l0a.values, rt=rt); R2["dispersione"][f"tot_r{rt}"] = {p: dict(ll_tot=round(float(Xr.ll_tot.values[M[p]].mean()), 5), ll_ou=round(float(Xr.ll_ou.values[M[p]].mean()), 5), br_ou=round(float(Xr.br_ou.values[M[p]].mean()), 5), ll_tfix=round(float(Xr.ll_tfix.values[M[p]].mean()), 5)) for p in PER}
log("dispersione", json.dumps(R2["dispersione"], default=float)[:3000])
# ---------------- 3. risultati per campionato, stagione, fascia, sede (app, app + costante e varianti promosse)
def breakdown(X, Xref):
    o = {}
    J_ = J.assign(d_sq=X.ll_team.values - Xref.ll_team.values, d_tot=X.ll_tot.values - Xref.ll_tot.values, d_12=X.ll_1x2.values - Xref.ll_1x2.values)
    for p in ("verifica", "holdout"):
        G = J_[J_.per == p]
        o[p] = dict(campionati=G.groupby("lg")[["d_sq", "d_tot", "d_12"]].mean().round(5).to_dict("index"),
                    stagioni=G.groupby("se")[["d_sq", "d_tot", "d_12"]].mean().round(5).to_dict("index"),
                    fasce=G.groupby(pd.cut(G.l0h + G.l0a, [0, 8.5, 9.5, 10.5, 11.5, 99]).astype(str))[["d_sq", "d_tot", "d_12"]].agg(["mean", "size"]).round(5).pipe(lambda T: {k: {f"{a}_{b}": v for (a, b), v in r.items()} for k, r in T.to_dict("index").items()}))
    return o
def calib(lh, la):
    o = {}
    for p in PER:
        m = M[p]; G = J[m]; tot = (lh + la)[m]
        fas = pd.cut(tot, [0, 8.5, 9.5, 10.5, 11.5, 99]); o[p] = {}
        o[p]["fasce_totale"] = {str(k): dict(n=int(v.size), atteso=round(float(tot[v.index].mean()), 3), reale=round(float(G.yt.values[v.index].mean()), 3)) for k, v in pd.Series(np.arange(m.sum())).groupby(fas, observed=True)}
        for side, l, y in (("casa", lh[m], G.yh.values), ("ospite", la[m], G.ya.values)):
            q = pd.qcut(l, 5, labels=False, duplicates="drop")
            o[p][side] = [dict(atteso=round(float(l[q == i].mean()), 3), reale=round(float(y[q == i].mean()), 3)) for i in range(int(q.max()) + 1)]
            # pendenza di calibrazione: regressione di reale su atteso (1 = perfetta)
            o[p][side + "_pendenza"] = round(float(np.polyfit(l, y, 1)[0]), 3)
        o[p]["campionati"] = (G.assign(t=tot).groupby("lg").apply(lambda g: round(float(g.yt.sum() / g.t.sum()), 3))).to_dict()
        # squadre: chi batte molti corner e chi ne concede molti (media per squadra e stagione, almeno 10 partite)
        rows = []
        for (lg, se_, team), g in pd.concat([pd.DataFrame(dict(lg=G.lg, se=G.se, team=G.h, f=G.yh, ef=lh[m], c=G.ya, ec=la[m])),
                                             pd.DataFrame(dict(lg=G.lg, se=G.se, team=G.a, f=G.ya, ef=la[m], c=G.yh, ec=lh[m]))]).groupby(["lg", "se", "team"]):
            if len(g) >= 10: rows.append((g.f.mean(), g.ef.mean(), g.c.mean(), g.ec.mean()))
        T = np.array(rows)
        o[p]["squadre"] = dict(n=len(T), corr_fatti=round(float(np.corrcoef(T[:, 0], T[:, 1])[0, 1]), 3), corr_concessi=round(float(np.corrcoef(T[:, 2], T[:, 3])[0, 1]), 3),
                               pendenza_fatti=round(float(np.polyfit(T[:, 1], T[:, 0], 1)[0]), 3), pendenza_concessi=round(float(np.polyfit(T[:, 3], T[:, 2], 1)[0]), 3))
    return o
R2["calibrazione_app"] = calib(J.l0h.values, J.l0a.values)
log("calibrazione app", json.dumps(R2["calibrazione_app"], default=float)[:4000])
# ---------------- 4. combinazione: le varianti che passano la regola al 95% sulla verosimiglianza per squadra (scelta fatta SOLO su sviluppo e verifica)
VAR = {"+forma10": ["att10", "def10"], "+formaE": ["attE", "defE"], "+campo": ["attV", "defV"], "+rating365": ["att365", "def365"], "+tiri": ["att_s", "def_s"],
       "+tiri_porta": ["att_st", "def_st"], "+bloccati": ["att_bl", "def_bl"], "+in_area": ["att_ib", "def_ib"], "+xg": ["att_xg", "def_xg"], "+possesso": ["poss"], "+forza": ["forza"],
       "+calibrazione_mobile": ["cal"], "+inizio_stagione": ["inizio"], "+contrazione": ["contr"]}
J["h_forza"] = np.log(J.gh / J.ga).fillna(0); J["a_forza"] = -J.h_forza
lgs = sorted(J.lg.unique())
cal_h, cal_a = np.zeros(len(J)), np.zeros(len(J))
for g, G in J.groupby("lg"):
    t = G.t.values; idx = G.index.values
    for yc, lc, out in (("yh", "l0h", cal_h), ("ya", "l0a", cal_a)):
        cy = np.r_[0, np.cumsum(G[yc].values)]; cl = np.r_[0, np.cumsum(G[lc].values)]
        lo = np.searchsorted(t, t - 180, "left"); hi = np.searchsorted(t, t, "left"); n = hi - lo
        sy, sl = cy[hi] - cy[lo], cl[hi] - cl[lo]; eb = np.where(n > 0, sl / np.maximum(n, 1), 1.0)
        out[idx] = np.log((sy + 100 * eb) / (sl + 100 * eb))
J["h_cal"], J["a_cal"] = cal_h, cal_a
st0 = J.groupby(["lg", "se"]).t.transform("min"); J["h_inizio"] = (J.t - st0 < 35).astype(float); J["a_inizio"] = J.h_inizio
def verdict(key):
    v = R2.get(key) or A1["modelli"].get(key)
    if v is None: return None
    c = v["contro_app_costante"]["ll_team"]["verifica"]; a, b_ = map(int, c["camp"].split("/"))
    return bool(c["hi95"] < 0 and a > b_ / 2)
sel = [nm for nm in VAR if verdict("app" + nm)]
log("varianti promosse in verifica (95%, maggioranza campionati):", sel)
R2["promosse_in_verifica"] = sel
if sel:
    ff = sum((VAR[n] for n in sel), [])
    Xb = run2("app+combinazione", *fx(ff), J.l0h.values, J.l0a.values, ff)
    R2["combinazione_dettaglio"] = breakdown(Xb, XC); R2["calibrazione_combinazione"] = calib(MOD2["app+combinazione"]["lh"], MOD2["app+combinazione"]["la"])
# combinazione per obiettivo: tiri in porta (squadra, 1X2) + contrazione per sede (totale); scelta su sviluppo e verifica, holdout solo controllo
ff = ["att_st", "def_st", "contrH", "contrA"]
Xb2 = run2("app+tiri_porta+contrazione_sede", *fx(ff), J.l0h.values, J.l0a.values, ff)
R2["combinazione2_dettaglio"] = breakdown(Xb2, XC); R2["calibrazione_combinazione2"] = calib(MOD2["app+tiri_porta+contrazione_sede"]["lh"], MOD2["app+tiri_porta+contrazione_sede"]["la"])
R2["app_costante_dettaglio"] = breakdown(XC, X0)
json.dump(R2, open(os.path.join(OUT, "audit2.json"), "w"), indent=1, ensure_ascii=False, default=float)
log("fatto")
