"""Corner · audit, quinta parte (18/11/2026, Denny). Solo analisi. Calibrazione e dettaglio (campionati, stagioni, fasce, casa/ospite,
squadre) del candidato tiri + tiri in porta + contrazione per sede, accanto all'app. Uscita: ricerca/corner/audit5.json."""
import os
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "corner_audit.py")).read()
exec(src[:src.index("# ================= 1. modello attuale")])
J["h_contrH"] = np.log(J.l0h / J.mH_c); J["a_contrH"] = 0.0; J["h_contrA"] = 0.0; J["a_contrA"] = np.log(J.l0a / J.mA_c)
FF = ["att_s", "def_s", "att_st", "def_st", "contrH", "contrA"]
b, se, lhB, laB = fit(*fx(FF), J.l0h.values, J.l0a.values)
b0, se0, lhC, laC = fit(np.zeros((len(J), 0)), np.zeros((len(J), 0)), J.l0h.values, J.l0a.values)
XB, XC = metrics(lhB, laB), metrics(lhC, laC)
R5 = {"coefficienti": {n: [float(x), float(s)] for n, x, s in zip(["costante"] + FF, b, se)}}
def calib(lh, la):
    o = {}
    for p in PER:
        m = M[p]; G = J[m]; tot = (lh + la)[m]; o[p] = {}
        fas = pd.cut(tot, [0, 8.5, 9.5, 10.5, 11.5, 99])
        o[p]["fasce_totale"] = {str(k): dict(n=int(v.size), atteso=round(float(tot[v.values].mean()), 3), reale=round(float(G.yt.values[v.values].mean()), 3)) for k, v in pd.Series(np.arange(m.sum())).groupby(fas, observed=True)}
        for side, l, y in (("casa", lh[m], G.yh.values), ("ospite", la[m], G.ya.values)):
            q = pd.qcut(l, 5, labels=False, duplicates="drop")
            o[p][side] = [dict(atteso=round(float(l[q == i].mean()), 3), reale=round(float(y[q == i].mean()), 3)) for i in range(int(q.max()) + 1)]
            o[p][side + "_pendenza"] = round(float(np.polyfit(l, y, 1)[0]), 3)
        rows = []
        for _, g in pd.concat([pd.DataFrame(dict(lg=G.lg, se=G.se, team=G.h, f=G.yh, ef=lh[m], c=G.ya, ec=la[m])), pd.DataFrame(dict(lg=G.lg, se=G.se, team=G.a, f=G.ya, ef=la[m], c=G.yh, ec=lh[m]))]).groupby(["lg", "se", "team"]):
            if len(g) >= 10: rows.append((g.f.mean(), g.ef.mean(), g.c.mean(), g.ec.mean()))
        T = np.array(rows)
        o[p]["squadre"] = dict(n=len(T), corr_fatti=round(float(np.corrcoef(T[:, 0], T[:, 1])[0, 1]), 3), corr_concessi=round(float(np.corrcoef(T[:, 2], T[:, 3])[0, 1]), 3))
        o[p]["casa_ll"] = round(float(-lp(G.yh.values, lh[m], RT).mean()), 5); o[p]["ospite_ll"] = round(float(-lp(G.ya.values, la[m], RT).mean()), 5)
    return o
R5["calibrazione_app"] = calib(J.l0h.values, J.l0a.values); R5["calibrazione_candidato"] = calib(lhB, laB)
d = J.assign(d_sq=XB.ll_team.values - XC.ll_team.values, d_tot=XB.ll_tot.values - XC.ll_tot.values, d_12=XB.ll_1x2.values - XC.ll_1x2.values, d_ou=XB.br_ou.values - XC.br_ou.values,
             d_h=XB.ll_h.values - XC.ll_h.values, d_a=XB.ll_a.values - XC.ll_a.values)
for p in PER:
    G = d[d.per == p]
    R5[p] = dict(campionati=G.groupby("lg")[["d_sq", "d_tot", "d_12"]].mean().round(5).to_dict("index"), stagioni=G.groupby("se")[["d_sq", "d_tot", "d_12", "d_ou"]].mean().round(5).to_dict("index"),
                 fasce={str(k): dict(n=int(len(g)), d_sq=round(float(g.d_sq.mean()), 5), d_tot=round(float(g.d_tot.mean()), 5), d_12=round(float(g.d_12.mean()), 5), d_ou=round(float(g.d_ou.mean()), 5))
                        for k, g in G.groupby(pd.cut(G.l0h + G.l0a, [0, 8.5, 9.5, 10.5, 11.5, 99]), observed=True)},
                 casa=round(float(G.d_h.mean()), 5), ospite=round(float(G.d_a.mean()), 5))
    # linee fisse una per una
    R5[p]["linee_totale"] = {str(L): dict(app=round(float(XC[f"br_t{L}"].values[(J.per == p).values].mean()), 5), candidato=round(float(XB[f"br_t{L}"].values[(J.per == p).values].mean()), 5)) for L in TL}
json.dump(R5, open(os.path.join(OUT, "audit5.json"), "w"), indent=1, ensure_ascii=False, default=float)
print(json.dumps(R5, ensure_ascii=False, default=float))
