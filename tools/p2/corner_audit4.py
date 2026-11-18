"""Corner · audit, quarta parte (18/11/2026, Denny). Solo analisi. Variante unica con tiri, tiri in porta e contrazione per sede
(la scelta tra le varianti si fa su sviluppo e verifica; l'holdout resta controllo). Uscita: ricerca/corner/audit4.json."""
import os
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "corner_audit3.py")).read()
src = src[:src.index('go("app+contrazione_sede"')]
exec(src)
FF = ["att_s", "def_s", "att_st", "def_st", "contrH", "contrA"]
bB, lhB, laB = go("tiri+tiri_porta+contrazione_sede", FF)
st = {}
for p in PER:
    m = M[p]; one = np.ones((m.sum(), 1)); Xh, Xa = fx(FF)
    bb, ss = pois_fit(np.vstack([np.hstack([one, Xh[m]]), np.hstack([one, Xa[m]])]), np.r_[J.yh.values[m], J.ya.values[m]], np.log(np.r_[J.l0h.values[m], J.l0a.values[m]]))
    st[p] = {n: [round(float(x), 4), round(float(s), 4)] for n, x, s in zip(["costante"] + FF, bb, ss)}
R3["stabilita_coefficienti"] = st; log("stabilità", st)
json.dump(R3, open(os.path.join(OUT, "audit4.json"), "w"), indent=1, ensure_ascii=False, default=float)
log("fatto")
