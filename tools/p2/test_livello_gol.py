"""Prevista 2.0 · riallineamento del livello gol del campionato (28/10/2026, punto 2 di Denny).
Problema: negli ultimi 120 giorni l'app sottostima gli Over gol (O2,5 51,1 previsto contro 55,7 reale).
Ipotesi: un fattore di livello per campionato dagli ultimi W giorni corregge i gol attesi di entrambe le squadre:
  f = (gol reali nella finestra + K) / (gol attesi dall'app nella finestra + K)      (K = gol fittizi: prudenza a inizio stagione)
  lh' = lh·f, la' = la·f   (con le sole partite già giocate prima del giorno della partita)
W e K si scelgono SOLO sul periodo "scelta" (fino al 30/6/2024, log-loss Over 2,5); poi verifica e holdout con la regola dell'harness.
Mercati giudicati: Over/Under 1,5 · 2,5 · 3,5 e 1X2 (Poisson con la correzione di Dixon-Coles dell'app, rho delle previsioni)."""
import os, sys, json, glob, math, collections, datetime
import numpy as np, pandas as pd
from scipy.stats import poisson
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
P2 = os.environ.get("RICERCA", os.path.join(REPO, "ricerca"))
sys.path.insert(0, os.path.join(REPO, "tools")); import harness as H
log = lambda *a: print(*a, flush=True)
B = []
for fn in glob.glob(P2 + "/base/*.json"):
    lg = os.path.basename(fn)[:-5]
    for r in json.load(open(fn)):
        g = r.get("g"); y = r["y"]["g"]
        if not g or g[0] is None or g[1] is None or y[0] is None: continue
        B.append((r["d"], lg, r["se"], g[0], g[1], g[2] or 0, y[0], y[1]))
B.sort(); log("partite", len(B))
N = 10; KK = np.arange(N + 1)
def mat(lh, la, rho):
    M = np.outer(poisson.pmf(KK, lh), poisson.pmf(KK, la))
    if rho:
        M[0, 0] *= max(0, 1 - lh * la * rho); M[0, 1] *= max(0, 1 + lh * rho); M[1, 0] *= max(0, 1 + la * rho); M[1, 1] *= max(0, 1 - rho)
    return M / M.sum()
TOT = np.add.outer(KK, KK)
def mkts(lh, la, rho):
    M = mat(lh, la, rho)
    o = {L: float(M[TOT > L].sum()) for L in (1.5, 2.5, 3.5)}
    o["1x2"] = [float(np.tril(M, -1).sum()), float(np.trace(M)), float(np.triu(M, 1).sum())]
    return o
def factors(W, K, pool=False):
    """fattore per partita con le sole partite dei giorni precedenti dello stesso campionato"""
    q = collections.defaultdict(collections.deque); sy = collections.defaultdict(float); sm = collections.defaultdict(float)
    F = []; i = 0
    while i < len(B):
        d = B[i][0]; j = i
        while j < len(B) and B[j][0] == d: j += 1
        dd = datetime.date.fromisoformat(d)
        for k in range(i, j):
            lg = "*" if pool else B[k][1]; Q = q[lg]
            while Q and (dd - Q[0][0]).days > W: _, a, b = Q.popleft(); sy[lg] -= a; sm[lg] -= b
            F.append((sy[lg] + K) / (sm[lg] + K))
        for k in range(i, j):
            _, lg, _, lh, la, _, hg, ag = B[k]; lg = "*" if pool else lg; q[lg].append((dd, hg + ag, lh + la)); sy[lg] += hg + ag; sm[lg] += lh + la
        i = j
    return np.array(F)
BASE = [mkts(b[3], b[4], b[5]) for b in B]
def frame(F):
    rows = []
    for b, f, o in zip(B, F, BASE):
        n = mkts(b[3] * f, b[4] * f, b[5]); tg = b[6] + b[7]
        rows.append(dict(date=b[0], lg=b[1], season=b[2], f=f, tg=tg, y1=0 if b[6] > b[7] else 1 if b[6] == b[7] else 2, o=o, n=n))
    return rows
def ou(rows, L):
    return pd.DataFrame([dict(date=r["date"], lg=r["lg"], season=r["season"], y=0 if r["tg"] > L else 2,
                              p_old=np.array([r["o"][L], 0.0, 1 - r["o"][L]]), p_new=np.array([r["n"][L], 0.0, 1 - r["n"][L]])) for r in rows])
def x12(rows):
    return pd.DataFrame([dict(date=r["date"], lg=r["lg"], season=r["season"], y=r["y1"], p_old=np.array(r["o"]["1x2"]), p_new=np.array(r["n"]["1x2"])) for r in rows])
POOL = os.environ.get("POOL") == "1"
# scelta di W e K sul solo periodo "scelta"
best = None
for W in ((30, 60, 90, 120, 365) if POOL else (90, 120)):
    for K in ((50, 200) if POOL else (15, 30, 60, 120)):
        rows = frame(factors(W, K, POOL)); R = H.confronta(ou(rows, 2.5))["scelta"]
        log(f"scelta W={W} K={K}: O2,5 diff {R['diff']:+.5f} IC {R['ci95']}")
        if best is None or R["diff"] < best[0]: best = (R["diff"], W, K)
_, W, K = best; log("scelti W", W, "K", K)
F = factors(W, K, POOL); rows = frame(F)
REP = {"W": W, "K": K, "pool": POOL}
for L in (1.5, 2.5, 3.5):
    R = H.confronta(ou(rows, L)); log(H.riepilogo(f"Over {L} · livello gol {'globale' if POOL else 'per campionato'} W={W} K={K}", R)); REP[f"O{L}"] = R
R = H.confronta(x12(rows)); log(H.riepilogo(f"1X2 · livello gol {'globale' if POOL else 'per campionato'} W={W} K={K}", R)); REP["1X2"] = R
# calibrazione nelle ultime settimane: Over 2,5 previsto prima/dopo contro reale
for a, b in (("2025-07-01", "2026-06-30"), ("2026-06-30", "2026-12-31"), ("2026-09-01", "2026-12-31")):
    s = [r for r in rows if a <= r["date"] <= b]
    if s: log(f"{a}→{b} n={len(s)} O2,5 app {100*np.mean([r['o'][2.5] for r in s]):.1f} · riallineato {100*np.mean([r['n'][2.5] for r in s]):.1f} · reale {100*np.mean([r['tg'] > 2.5 for r in s]):.1f} · fattore medio {np.mean([r['f'] for r in s]):.3f}")
json.dump(REP, open(os.path.join(P2, "res_livello_gol%s.json" % ("_globale" if POOL else "")), "w"), indent=1, default=float)
