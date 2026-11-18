"""Corner V2 in ombra · verifica tecnica (18/11/2026, Denny). Solo analisi.
Ingresso: ricerca/corner_v2/<lg>.json (corner_v2_dump.js: corner ufficiali dell'app, Corner V2 calcolato in JavaScript, partite grezze).
1) Replica INDIPENDENTE in Python degli otto indici e di λ_V2 dalle partite grezze (stessa definizione dell'audit) e confronto con JavaScript.
2) Ricaduta: dove i dati non bastano λ_V2 deve essere identico al valore ufficiale.
3) Backtest della versione JavaScript (coefficienti congelati) contro l'app su sviluppo, verifica e holdout, stesse metriche dell'audit.
Uso: python corner_v2_check.py [CARTELLA_DUMP] → ricerca/corner/v2_check.json"""
import os, sys, json, glob, math, numpy as np, pandas as pd
DUMP = sys.argv[1] if len(sys.argv) > 1 else None
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "corner_audit.py")).read()
exec(src[src.index("import os"):src.index("J = pd.read_pickle")])
from comune import per
PER = ("scelta", "verifica", "holdout"); RT, RTOT, COP = 12.0, 60.0, -0.20
exec(src[src.index("# ---------------- copula"):src.index("# ================= 1. modello attuale")].replace("def fit(", "def _fit_unused("))
DUMP = DUMP or os.path.join(RIC, "corner_v2")
C = dict(c=0.0054715, s_att=0.1043709, s_def=0.0711996, st_att=0.0727421, st_def=0.1112512, kH=-0.2057728, kA=-0.1658093, N=10, K=3, MIN=5, LOOK=365, MINM=30)
day = lambda s: (pd.Timestamp(s) - pd.Timestamp("1970-01-01")).days
rows, comp = [], []
for f in sorted(glob.glob(os.path.join(DUMP, "*.json"))):
    lg = os.path.basename(f)[:-5]; D = json.load(open(f))
    R = pd.DataFrame(D["raw"], columns=["d", "h", "a", "hc", "ac", "hs", "as_", "hst", "ast"])
    R = R[R.hc.notna() & R.ac.notna()].copy(); R["t"] = R.d.map(day); R = R.sort_values(["t", "h"]).reset_index(drop=True)
    t = R.t.values
    # attesi per sede dai 365 giorni precedenti (almeno 30 partite con il dato)
    for col in ("hs", "as_", "hst", "ast"):
        v = pd.to_numeric(R[col], errors="coerce").values.astype(float); ok = ~np.isnan(v)
        cs = np.r_[0, np.cumsum(np.where(ok, v, 0))]; cn = np.r_[0, np.cumsum(ok)]
        lo, hi = np.searchsorted(t, t - C["LOOK"], "left"), np.searchsorted(t, t, "left"); n = cn[hi] - cn[lo]
        R["e_" + col] = np.where(n >= C["MINM"], (cs[hi] - cs[lo]) / np.maximum(n, 1), np.nan)
    hist = {}
    for i, (hh, aa) in enumerate(zip(R.h.values, R.a.values)): hist.setdefault(hh, []).append(i); hist.setdefault(aa, []).append(i)
    A_ = {c: pd.to_numeric(R[c], errors="coerce").values.astype(float) for c in ("hs", "as_", "hst", "ast", "e_hs", "e_as_", "e_hst", "e_ast")}; Hn, An = R.h.values, R.a.values
    def index(team, tt, k, side):
        idx = [i for i in hist.get(team, []) if t[i] < tt][-C["N"]:]; sy = se = 0.0; n = 0
        for i in idx:
            own = (Hn[i] == team) == (side == "f")
            col = ("hst" if k else "hs") if own else ("ast" if k else "as_"); y, e = A_[col][i], A_["e_" + col][i]
            if np.isnan(y) or np.isnan(e): continue
            sy += y; se += e; n += 1
        if not n: return 0.0, 0
        eb = se / n; return math.log((sy + C["K"] * eb) / (se + C["K"] * eb)), n
    for r in D["rows"]:
        d, h, a, hc, ac, lh, la, muH, muA, vh, va, on, ix = r
        if lh is None: continue
        tt = day(d)
        py = [index(h, tt, 0, "f"), index(a, tt, 0, "a"), index(h, tt, 1, "f"), index(a, tt, 1, "a"), index(a, tt, 0, "f"), index(h, tt, 0, "a"), index(a, tt, 1, "f"), index(h, tt, 1, "a")]
        if any(x[1] < C["MIN"] for x in py) or not (muH and muH > 0 and muA and muA > 0): ph, pa, pon = lh, la, 0
        else:
            ph = lh * math.exp(C["c"] + C["s_att"] * py[0][0] + C["s_def"] * py[1][0] + C["st_att"] * py[2][0] + C["st_def"] * py[3][0] + C["kH"] * math.log(lh / muH))
            pa = la * math.exp(C["c"] + C["s_att"] * py[4][0] + C["s_def"] * py[5][0] + C["st_att"] * py[6][0] + C["st_def"] * py[7][0] + C["kA"] * math.log(la / muA)); pon = 1
        comp.append(dict(lg=lg, d=d, on_js=on, on_py=pon, dh=abs(ph - vh), da=abs(pa - va), dix=max(abs(p[0] - j[0]) for p, j in zip(py, ix)), dn=max(abs(p[1] - j[1]) for p, j in zip(py, ix)),
                         fall_exact=(on == 1) or (vh == lh and va == la)))
        rows.append(dict(lg=lg, d=d, yh=hc, ya=ac, l0h=lh, l0a=la, vh=vh, va=va, on=on))
Cc = pd.DataFrame(comp); B = pd.DataFrame(rows)
OUT_ = {"partite": len(Cc), "campionati": int(Cc.lg.nunique()),
        "attivo_js": int(Cc.on_js.sum()), "attivo_py": int(Cc.on_py.sum()), "stesso_stato_attivo": float((Cc.on_js == Cc.on_py).mean()),
        "max_diff_lambda": float(max(Cc.dh.max(), Cc.da.max())), "max_diff_indici": float(Cc.dix.max()), "max_diff_partite_utili": int(Cc.dn.max()),
        "ricaduta_esatta_quando_spento": bool(Cc.fall_exact.all()), "spente_per_campionato": Cc[Cc.on_js == 0].groupby("lg").size().to_dict()}
log(json.dumps(OUT_))
# ---------------- backtest della versione JavaScript (coefficienti congelati) contro l'app
B["per"] = B.d.map(per); B["wk"] = (pd.to_datetime(B.d) - pd.Timestamp("1970-01-01")).dt.days // 7; B["yh"] = B.yh.astype(int); B["ya"] = B.ya.astype(int); B["yt"] = B.yh + B.ya
J = B.reset_index(drop=True); M = {p: (J.per == p).values for p in PER}
X0 = metrics(J.l0h.values, J.l0a.values); X1 = metrics(J.vh.values, J.va.values)
OUT_["backtest"] = dict(app=summary(X0), v2=summary(X1), v2_meno_app=cmp(X0, X1, ("ll_team", "ll_tot", "ll_1x2", "br_1x2", "ll_ou", "br_ou", "ll_tfix", "br_tfix", "ll_sq", "br_sq", "ae_t", "se_t", "ae_sq")))
for k, c in OUT_["backtest"]["v2_meno_app"].items():
    log(f"{k:8s}", " | ".join(f"{p[:4]} {c[p]['diff']:+.6f} 99[{c[p]['lo99']:+.6f},{c[p]['hi99']:+.6f}] {c[p]['camp']}" for p in PER))
json.dump(OUT_, open(os.path.join(RIC, "corner", "v2_check.json"), "w"), indent=1, ensure_ascii=False, default=float)
log("fatto")
