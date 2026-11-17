"""Gol attesi · fase 3, controllo finale: la forma recente (unico gruppo che passa la regola contro il modello precedente in entrambe le
procedure) aggiunta direttamente a M0, senza M1/M2; quale parte serve (tiri in porta o gol); poi Dixon-Coles con rho unico mensile.
M0 resta com'è (offset log λ0): si stimano solo i coefficienti nuovi sul periodo scelta. Uscita: ricerca/gol/exp4_forma.json + tabella finale."""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__)); from gol_eval import *
REPO = os.path.join(os.path.dirname(__file__), "..", "..")
df = pd.read_pickle(os.path.join(REPO, "ricerca", "gol", "feat.pkl")).sort_values(["d", "lg"]).reset_index(drop=True)
df["mese"] = df.date.dt.to_period("M"); sc = (df.per == "scelta").values
def form(d, h, k, N, parts):
    s, o = ("H", "A") if h else ("A", "H"); gm = (d.muH + d.muA) / 2; sm = gm / d.conv; out = []
    if "g" in parts: out += [np.log((d[f"gf{N}{s}"] + k * gm) / (d[f"n{N}{s}"] + k) / gm), np.log((d[f"ga{N}{o}"] + k * gm) / (d[f"n{N}{o}"] + k) / gm)]
    if "s" in parts: out += [np.log((d[f"sf{N}{s}"] + k * sm) / (d[f"ns{N}{s}"] + k) / sm), np.log((d[f"sa{N}{o}"] + k * sm) / (d[f"ns{N}{o}"] + k) / sm)]
    return out
def fit(fn):
    X = lambda d, h: np.column_stack([np.ones(len(d))] + fn(d, h))
    A = np.vstack([X(df[sc], True), X(df[sc], False)]); y = np.r_[df.yh[sc], df.ya[sc]]; off = np.r_[np.log(df.lh0[sc]), np.log(df.la0[sc])]
    b = pois_fit(A, y, offset=off); return b, df.lh0.values * np.exp(X(df, True) @ b), df.la0.values * np.exp(X(df, False) @ b)
def ssc(lh, la): return metrics(df[sc], lh[sc], la[sc]).ll_score.mean()
X0 = metrics(df, df.lh0, df.la0); res = {"griglie": {}}; MOD = {}
for parts, nm in (("gs", "forma gol + tiri in porta"), ("s", "forma solo tiri in porta"), ("g", "forma solo gol")):
    best = None
    for N in (5, 10):
        for k in (5, 10, 20, 40, 80, 160, 320):
            b, lh, la = fit(lambda d, h, k=k, N=N: form(d, h, k, N, parts)); v = ssc(lh, la); res["griglie"][f"{nm} N{N} k{k}"] = round(v, 6)
            if best is None or v < best[0]: best = (v, N, k, b, lh, la)
    _, N, k, b, lh, la = best; MOD[f"M0 + {nm} (ultime {N}, k {k})"] = (lh, la, None, [round(x, 4) for x in b])
# Dixon-Coles mensile (rho unico, partite precedenti) su M0 e sul miglior modello con la forma
def rho_month(lh, la):
    R = np.zeros(len(df))
    for mo in sorted(df.mese.unique()):
        prev = (df.mese < mo).values; cur = (df.mese == mo).values
        R[cur] = fit_rho(lh[prev], la[prev], df.yh[prev], df.ya[prev]) if prev.sum() >= 1000 else 0.0
    return R
r0 = rho_month(df.lh0.values, df.la0.values); MOD["M0 + Dixon-Coles"] = (df.lh0.values, df.la0.values, r0, None)
for bestf in [k for k in list(MOD) if k.startswith("M0 + forma") and "solo gol" not in k]:
    lh, la = MOD[bestf][0], MOD[bestf][1]; MOD[bestf + " + Dixon-Coles"] = (lh, la, rho_month(lh, la), MOD[bestf][3])
XS = {"M0": X0}
for nm, (lh, la, rho, b) in MOD.items():
    X = metrics(df, lh, la, rho); XS[nm] = X
    res[nm] = dict(coef=b, riepilogo=summary(df, X), contro_M0={key: compare(df, X0, X, key) for key in ("ll_score", "ll_1x2", "br_1x2", "ll_o25", "br_o25", "se_t")})
    res[nm]["regola"] = rule(res[nm]["contro_M0"]["ll_score"]); res[nm]["regola_1x2"] = rule(res[nm]["contro_M0"]["ll_1x2"])
    if "Dixon-Coles" in nm and nm != "M0 + Dixon-Coles":
        res[nm]["contro_senza_DC"] = {key: compare(df, XS[nm.replace(" + Dixon-Coles", "")], X, key) for key in ("ll_score", "ll_1x2", "br_1x2")}
    m = (df.per != "scelta").values
    d = (X.ll_score - X0.ll_score)
    res[nm]["per_campionato"] = {per: {l: round(v, 5) for l, v in d[df.per == per].groupby(df.lg[df.per == per]).mean().items()} for per in ("verifica", "holdout")}
json.dump(res, open(os.path.join(REPO, "ricerca", "gol", "exp4_forma.json"), "w"), indent=1, default=str, ensure_ascii=False)
pd.to_pickle({k: (v[0], v[1], v[2]) for k, v in MOD.items()}, os.path.join(REPO, "ricerca", "gol", "exp4_pred.pkl"))
def show(R): return " | ".join(f"{p[:3]} {R[p]['diff']:+.5f} [{R[p]['lo']:+.5f},{R[p]['hi']:+.5f}] {R[p]['pct']:+.3f}% {R[p]['camp']}" for p in ("scelta", "verifica", "holdout"))
for nm in MOD:
    r = res[nm]; print(f"\n== {nm} · coef {r['coef']} · regola risultato esatto {r['regola']} · regola 1X2 {r['regola_1x2']}")
    for key in ("ll_score", "ll_1x2", "br_1x2", "ll_o25", "se_t"): print(f"   {key:8} {show(r['contro_M0'][key])}")
    if "contro_senza_DC" in r:
        for key in ("ll_score", "ll_1x2", "br_1x2"): print(f"   DC in più {key:8} {show(r['contro_senza_DC'][key])}")
