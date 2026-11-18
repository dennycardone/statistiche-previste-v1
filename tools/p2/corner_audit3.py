"""Corner · audit, terza parte (18/11/2026, Denny). Solo analisi: nessuna modifica all'app.
Ricalcola i modelli principali con le linee Over/Under UGUALI per tutti (quelle vicine all'atteso dell'app: confronto sulle stesse linee),
controlla la stabilità dei coefficienti della combinazione (stimati a parte su verifica e holdout: solo controllo, non scelta) e due varianti
di sensibilità (tiri totali o in area al posto dei tiri in porta). Uscita: ricerca/corner/audit3.json."""
import os
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "corner_audit.py")).read()
exec(src[:src.index("# ================= 1. modello attuale")])
J["h_contrH"] = np.log(J.l0h / J.mH_c); J["a_contrH"] = 0.0; J["h_contrA"] = 0.0; J["a_contrA"] = np.log(J.l0a / J.mA_c)
X0 = metrics(J.l0h.values, J.l0a.values)
b, se, lhC, laC = fit(np.zeros((len(J), 0)), np.zeros((len(J), 0)), J.l0h.values, J.l0a.values); XC = metrics(lhC, laC)
R3 = {"app": summary(X0), "app_costante": summary(XC)}
def go(name, ff):
    b, se, lh, la = fit(*fx(ff), J.l0h.values, J.l0a.values); X = metrics(lh, la); c = cmp(XC, X, KEYS)
    R3[name] = dict(coefficienti={n: [round(float(x), 5), round(float(s), 5)] for n, x, s in zip(["costante"] + ff, b, se)}, riepilogo=summary(X), contro_app_costante=c,
                    contro_app=cmp(X0, X, ("ll_team", "ll_tot", "ll_1x2", "ll_ou", "br_ou", "ll_sq", "br_sq")),
                    regola={k: passes(c[k]) for k in ("ll_team", "ll_tot", "ll_1x2", "ll_ou", "br_ou", "ll_sq", "br_sq", "ll_tfix", "br_tfix", "br_sqfix")})
    log(name, R3[name]["coefficienti"]); log("   regole", R3[name]["regola"])
    for k in ("ll_team", "ll_tot", "ll_1x2", "br_1x2", "ll_ou", "br_ou", "ll_tfix", "br_tfix", "ll_sq", "br_sq", "br_sqfix", "ae_t", "ae_sq"):
        log(f"   {k:8s}", " | ".join(f"{p[:4]} {c[k][p]['diff']:+.6f} 95[{c[k][p]['lo95']:+.6f},{c[k][p]['hi95']:+.6f}] 99[{c[k][p]['lo99']:+.6f},{c[k][p]['hi99']:+.6f}] {c[k][p]['camp']}" for p in PER))
    return b, lh, la
go("app+contrazione_sede", ["contrH", "contrA"])
go("app+tiri_porta", ["att_st", "def_st"])
FF = ["att_st", "def_st", "contrH", "contrA"]
bB, lhB, laB = go("app+tiri_porta+contrazione_sede", FF)
go("sens: tiri+contrazione_sede", ["att_s", "def_s", "contrH", "contrA"])
go("sens: in_area+contrazione_sede", ["att_ib", "def_ib", "contrH", "contrA"])
# stabilità dei coefficienti (stima separata per periodo, solo controllo)
st = {}
for p in PER:
    m = M[p]; one = np.ones((m.sum(), 1)); Xh, Xa = fx(FF)
    XH = np.hstack([one, Xh[m]]); XA = np.hstack([one, Xa[m]])
    bb, ss = pois_fit(np.vstack([XH, XA]), np.r_[J.yh.values[m], J.ya.values[m]], np.log(np.r_[J.l0h.values[m], J.l0a.values[m]]))
    st[p] = {n: [round(float(x), 4), round(float(s), 4)] for n, x, s in zip(["costante"] + FF, bb, ss)}
R3["stabilita_coefficienti"] = st; log("stabilità", st)
# esempio di quanto cambia la previsione: distribuzione del rapporto nuovo/app
rh, ra = lhB / J.l0h.values, laB / J.l0a.values; rt_ = (lhB + laB) / (J.l0h.values + J.l0a.values)
R3["spostamento"] = {k: dict(p5=round(float(np.percentile(v, 5)), 4), p50=round(float(np.percentile(v, 50)), 4), p95=round(float(np.percentile(v, 95)), 4), oltre_5pct=round(float((abs(v - 1) > 0.05).mean() * 100), 1))
                     for k, v in (("casa", rh), ("ospite", ra), ("totale", rt_))}
log("spostamento", R3["spostamento"])
json.dump(R3, open(os.path.join(OUT, "audit3.json"), "w"), indent=1, ensure_ascii=False, default=float)
log("fatto")
