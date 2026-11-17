"""Gol attesi · fase 3, M1-M4 (Denny). Ogni modello = il precedente + un gruppo di ingredienti, tutti i coefficienti stimati insieme
(regressione di Poisson) sul solo periodo scelta, poi fissi in verifica e holdout. Le prudenze (k) si scelgono nel periodo scelta.
  B  : ingredienti di M0 con coefficienti stimati di nuovo (stessa procedura dei modelli nuovi: confronto "alla pari")
  M1 : B + volume e precisione: log tiri attesi (rating tiri totali), conversione della squadra (gol / tiri in porta, ristretta verso la lega)
  M2 : M1 + difesa: conversione concessa dall'avversaria (gol subiti / tiri in porta concessi, ristretta); i tiri concessi sono già nei rating
  M3 : M2 + forma recente: gol e tiri in porta delle ultime 5 o 10 (fatti dalla squadra, concessi dall'avversaria), ristretti verso la lega
  M4 : M3 + calibrazione campionato-stagione: gol della stagione in corso rispetto al previsto, ristretti
Confronti: ogni modello contro il precedente e contro M0 (app), risultato esatto, 1X2, Over 2,5, errore quadratico del totale."""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__)); from gol_eval import *
REPO = os.path.join(os.path.dirname(__file__), "..", "..")
df = pd.read_pickle(os.path.join(REPO, "ricerca", "gol", "feat.pkl")).sort_values(["d", "lg"]).reset_index(drop=True)
sc = (df.per == "scelta").values
for c in ("etH", "etA", "eiH", "eiA"): df[c] = df[c].astype(float)
ok = df.etH.notna() & df.etA.notna()
print("partite con i tiri totali:", ok.mean())
df.loc[~ok, "etH"] = df.loc[~ok, "esH"] * 3; df.loc[~ok, "etA"] = df.loc[~ok, "esA"] * 3   # pochissime: sostituto neutro
gmean = (df.muH + df.muA) / 2; smean = gmean / df.conv
def base(d, h):
    mu = d.muH if h else d.muA; tp = d.tpH if h else d.tpA; qx = (d.qxh if h else d.qxa).fillna(0); ed = d.ed if h else -d.ed
    return [np.log(mu), np.full(len(d), 1.0 if h else 0.0), np.log(tp), ed, qx]
S = "HA"
def F_vol(d, h, k):
    s, o = ("H", "A") if h else ("A", "H")
    et = d["et" + s]; es = d["es" + s]
    conv = (d["cg" + s] + k * d.conv * 1.0 * (d["cs" + s] > -1)) / (d["cs" + s] + k)   # gol fatti / tiri in porta fatti, prudenza k tiri in porta
    return [np.log(et / es), np.log(conv / d.conv)]
def F_def(d, h, k):
    s, o = ("H", "A") if h else ("A", "H")
    convc = (d["kg" + o] + k * d.conv) / (d["ks" + o] + k)
    return [np.log(convc / d.conv)]
def F_form(d, h, k, N):
    s, o = ("H", "A") if h else ("A", "H")
    gm, sm = (d.muH + d.muA) / 2, (d.muH + d.muA) / 2 / d.conv
    g = (d[f"gf{N}{s}"] + k * gm) / (d[f"n{N}{s}"] + k) / gm; ga = (d[f"ga{N}{o}"] + k * gm) / (d[f"n{N}{o}"] + k) / gm
    sf = (d[f"sf{N}{s}"] + k * sm) / (d[f"ns{N}{s}"] + k) / sm; sa = (d[f"sa{N}{o}"] + k * sm) / (d[f"ns{N}{o}"] + k) / sm
    return [np.log(g), np.log(ga), np.log(sf), np.log(sa)]
def F_sea(d, h, k, prev_l):
    # gol reali della stagione rispetto a quelli previsti dal modello precedente nelle partite già giocate della stagione (stesso campionato)
    return [np.log(prev_l)]
OFFSET = os.environ.get("GOL_OFFSET") == "1"
def design(d, h, groups):
    cols = [np.ones(len(d))] + ([] if OFFSET else base(d, h))
    for g in groups: cols += g(d, h)
    return np.column_stack(cols)
def fit(groups):
    X = np.vstack([design(df[sc], True, groups), design(df[sc], False, groups)]); y = np.r_[df.yh[sc], df.ya[sc]]
    if OFFSET:
        off = np.r_[np.log(df.lh0[sc]), np.log(df.la0[sc])]; b = pois_fit(X, y, offset=off)
        return b, df.lh0.values * np.exp(design(df, True, groups) @ b), df.la0.values * np.exp(design(df, False, groups) @ b)
    b = pois_fit(X, y); return b, np.exp(design(df, True, groups) @ b), np.exp(design(df, False, groups) @ b)
def score_sc(lh, la): return metrics(df[sc], lh[sc], la[sc]).ll_score.mean()
MOD, LOG = {}, {}
b, lh, la = fit([]); MOD["B"] = (lh, la, b)
# M1: scelta di k (prudenza della conversione)
best = None
for k in (25, 100, 200, 400, 800, 1600):
    g = [lambda d, h, k=k: F_vol(d, h, k)]; b, lh, la = fit(g); v = score_sc(lh, la); LOG[f"M1 k={k}"] = round(v, 6)
    if best is None or v < best[0]: best = (v, k, g, b, lh, la)
_, k1, g1, b, lh, la = best; MOD[f"M1 (k {k1})"] = (lh, la, b)
best = None
for k in (25, 100, 200, 400, 800, 1600):
    g = g1 + [lambda d, h, k=k: F_def(d, h, k)]; b, lh, la = fit(g); v = score_sc(lh, la); LOG[f"M2 k={k}"] = round(v, 6)
    if best is None or v < best[0]: best = (v, k, g, b, lh, la)
_, k2, g2, b, lh, la = best; MOD[f"M2 (k {k2})"] = (lh, la, b)
best = None
for N in (5, 10):
    for k in (2, 5, 10, 20, 40, 80):
        g = g2 + [lambda d, h, k=k, N=N: F_form(d, h, k, N)]; b, lh, la = fit(g); v = score_sc(lh, la); LOG[f"M3 N={N} k={k}"] = round(v, 6)
        if best is None or v < best[0]: best = (v, (N, k), g, b, lh, la)
_, nk3, g3, b, lh, la = best; MOD[f"M3 (ultime {nk3[0]}, k {nk3[1]})"] = (lh, la, b)
# M4: fattore campionato-stagione sul modello M3 (gol reali / previsti nelle partite precedenti della stessa stagione, k partite fittizie)
def sea_factor(lh, la, k):
    f = np.ones(len(df)); ty = (df.yh + df.ya).values; tl = lh + la
    for (lg, se), g in df.groupby(["lg", "se"]):
        ii = g.index.values; dd = df.d.values[ii]
        cy = np.r_[0, np.cumsum(ty[ii])]; cl = np.r_[0, np.cumsum(tl[ii])]; hi = np.searchsorted(dd, dd, "left")
        lb = tl[ii].mean(); f[ii] = (cy[hi] + k * lb) / (cl[hi] + k * lb)
    return f
best = None
for k in (100, 200, 400, 800, 1600, 3200):
    f = sea_factor(lh, la, k); v = score_sc(lh * f, la * f); LOG[f"M4 k={k}"] = round(v, 6)
    if best is None or v < best[0]: best = (v, k, f)
_, k4, f4 = best; MOD[f"M4 (k {k4})"] = (lh * f4, la * f4, None)
X0 = metrics(df, df.lh0, df.la0); res = {"griglie (scelta)": LOG}; prevX = X0; prevn = "M0"; XS = {"M0": X0}
order = list(MOD)
for nm in order:
    lh, la, b = MOD[nm]; X = metrics(df, lh, la); XS[nm] = X
    res[nm] = dict(coef=None if b is None else [round(x, 4) for x in b], riepilogo=summary(df, X),
                   pendenza={p: round(league_slope(df, lh, la, p), 3) for p in ("verifica", "holdout")},
                   contro_M0={key: compare(df, X0, X, key) for key in ("ll_score", "ll_1x2", "br_1x2", "ll_o25", "se_t")})
    if nm != "B":
        res[nm]["contro_precedente"] = {key: compare(df, XS[prevn], X, key) for key in ("ll_score", "ll_1x2", "br_1x2", "ll_o25", "se_t")}
        res[nm]["regola_contro_precedente"] = rule(res[nm]["contro_precedente"]["ll_score"])
    res[nm]["regola_contro_M0"] = rule(res[nm]["contro_M0"]["ll_score"])
    prevn = nm
json.dump(res, open(os.path.join(REPO, "ricerca", "gol", "exp3_m14" + ("_offset" if OFFSET else "") + ".json"), "w"), indent=1, default=str, ensure_ascii=False)
pd.to_pickle({nm: (MOD[nm][0], MOD[nm][1]) for nm in MOD}, os.path.join(REPO, "ricerca", "gol", "exp3_pred" + ("_offset" if OFFSET else "") + ".pkl"))
def show(R): return " | ".join(f"{p[:3]} {R[p]['diff']:+.5f} [{R[p]['lo']:+.5f},{R[p]['hi']:+.5f}] {R[p]['camp']}" for p in ("scelta", "verifica", "holdout"))
for nm in order:
    r = res[nm]; print(f"\n== {nm} coef {r['coef']}")
    if "contro_precedente" in r:
        print(f"   contro precedente (regola {r['regola_contro_precedente']}):")
        for key in ("ll_score", "ll_1x2", "ll_o25"): print(f"     {key:8} {show(r['contro_precedente'][key])}")
    print(f"   contro M0 (regola {r['regola_contro_M0']}):")
    for key in ("ll_score", "ll_1x2", "ll_o25", "se_t"): print(f"     {key:8} {show(r['contro_M0'][key])}")
print(LOG)
