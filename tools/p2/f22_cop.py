"""Fase 2.2 · correlazioni apprese. (1) Correlazione casa-ospite nel 1X2 di ogni statistica: copula gaussiana con ρ scelto sul periodo
"scelta" (griglia) contro quella fissa dell'app (corner −0,20, tiri −0,24, le altre 0), giudizio su verifica e holdout con l'harness.
(2) Correlazioni tra statistiche dei residui (PIT gaussianizzati, stessa squadra e tra le due squadre): falli↔cartellini, tiri↔corner…,
per capire se un modello congiunto ha qualcosa da imparare oltre a ciò che i modelli già usano."""
import os as _os
P2 = _os.environ.get("RICERCA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "ricerca"))   # 28/10/2026: archivio di ricerca (ramo ricerca)
REPO = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
import json, glob, sys, math, numpy as np, pandas as pd
from scipy.stats import nbinom, poisson, norm
sys.path.insert(0, REPO + "/tools"); import harness as H
B = []
for fn in glob.glob(P2 + "/base/*.json"):
    lg = fn.split("/")[-1][:-5]
    for r in json.load(open(fn)):
        if r["d"] >= "2023-07-01": r["lg"] = lg; B.append(r)
print("partite", len(B), flush=True)
GRID = [-0.35, -0.25, -0.15, -0.05, 0.0, 0.05]
REP = {}
for k in ("c", "s", "st", "f", "o"):
    rows = [r for r in B if r.get(k) and r["y"][k][0] is not None and r["y"][k][1] is not None]
    rt = lambda m: (None if m[2] in (-1, None) else m[2], float("inf") if m[3] == -1 else m[3])
    def P(r, rho): m = r[k]; a, b = rt(m); return H.h2h(m[0], m[1], a, b, rho)
    ys = np.array([0 if r["y"][k][0] > r["y"][k][1] else 1 if r["y"][k][0] == r["y"][k][1] else 2 for r in rows])
    dates = np.array([r["d"] for r in rows])
    sel = dates <= "2024-06-30"
    best = None
    for rho in GRID:
        Pm = np.array([P(r, rho) for r, s in zip(rows, sel) if s]); ll = H.logloss(Pm, ys[sel]).mean()
        print(f"{k} ρ={rho:+.2f} scelta log-loss {ll:.5f}", flush=True)
        if best is None or ll < best[0]: best = (ll, rho)
    rho = best[1]
    df = pd.DataFrame(dict(date=dates, lg=[r["lg"] for r in rows], season=[r["se"] for r in rows], y=ys))
    df["p_old"] = [P(r, r[k][4] or 0.0) for r in rows]; df["p_new"] = [P(r, rho) for r in rows]
    res = H.confronta(df); REP[k] = (rho, res)
    print(H.riepilogo(f"{k}: ρ appreso {rho:+.2f} contro app {rows[0][k][4] or 0:+.2f}", res), flush=True)
# (2) residui: PIT gaussianizzato per squadra con la distribuzione dell'app (Binomiale Negativa con rTeam, Poisson se infinito)
def z(y, mu, r):
    if r is None or not np.isfinite(r) or r <= 0: lo, hi = poisson.cdf(y - 1, mu), poisson.cdf(y, mu)
    else: q = r / (r + mu); lo, hi = nbinom.cdf(y - 1, r, q), nbinom.cdf(y, r, q)
    u = (lo + hi) / 2; return norm.ppf(np.clip(u, 1e-6, 1 - 1e-6))
Z = {}
for side in (0, 1):
    for k in ("c", "s", "st", "f", "o"):
        vals = []
        for r in B:
            m = r.get(k); y = r["y"].get(k)
            if not m or y is None or y[side] is None: vals.append(np.nan); continue
            rT = None if m[3] in (-1, None) else m[3]
            vals.append(z(y[side], m[side], rT))
        Z[f"{k}{'HA'[side]}"] = vals
    # cartellini: residuo grezzo (le previsioni per squadra non sono nei file base) → solo il valore reale standardizzato per campionato
D = pd.DataFrame(Z)
C = D.corr()
print("\ncorrelazioni dei residui (stessa partita): righe/colonne = statistica + H casa / A ospite")
print(C.round(2).to_string())
