"""Fase 2.1 · calibrazione specifica per mercato e campionato (walk-forward mensile). Eventi: previsioni dell'app con i soli dati precedenti
(q23_events.pkl: Over 1,5/2,5/3,5, Under 2,5, Gol/No gol, 1X2 gol e 1X2 di corner, tiri, tiri in porta, falli, fuorigioco, lato mostrato).
Modelli confrontati (pesi stimati sui soli mesi precedenti):
  A  app (nessuna correzione)
  B  correzione per mercato: logit p' = a_m + b_m·logit p
  C  B + scarto per campionato (a_ml, ristretto verso 0 con penalità ridge λ, scelta sul periodo "scelta")
Giudizio con harness: log-loss binaria, IC al 95% a blocchi per settimana, verifica (lug 2024 – giu 2025) e holdout (da lug 2025)."""
import os as _os
P2 = _os.environ.get("RICERCA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "ricerca"))   # 28/10/2026: archivio di ricerca (ramo ricerca)
REPO = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
import json, glob, math, sys, collections, numpy as np, pandas as pd
sys.path.insert(0, REPO + "/tools"); import harness as H
E = pd.read_pickle(P2 + "/q23_events.pkl")
B = []
for fn in glob.glob(P2 + "/base/*.json"):
    lg = fn.split("/")[-1][:-5]
    for r in json.load(open(fn)): B.append((lg, r["se"]))
E["lg"] = E.mid.map(lambda i: B[i][0]); E["season"] = E.mid.map(lambda i: B[i][1])
E["mk"] = E.mk.replace({"Gol": "GG", "No gol": "GG"})
E = E[(E.p > 0.01) & (E.p < 0.99)].copy()
E["lp"] = np.log(E.p / (1 - E.p)); E["mon"] = E.date.str[:7]
def fit(df, lam, per_league):
    """regressione logistica (L-BFGS) con intercetta e pendenza per mercato + (opzionale) scarti per mercato×campionato con ridge"""
    from scipy.optimize import minimize
    mks = sorted(df.mk.unique()); keys = sorted({(m, l) for m, l in zip(df.mk, df.lg)}) if per_league else []
    im = {m: i for i, m in enumerate(mks)}; ik = {k: i for i, k in enumerate(keys)}
    nm, nk = len(mks), len(keys); P = 2 * nm + nk
    rm = df.mk.map(im).values; rk = np.array([ik[(m, l)] for m, l in zip(df.mk, df.lg)]) if per_league else None
    y = df.y.values.astype(float); x = df.lp.values
    def f(w):
        z = w[rm] + w[nm + rm] * x + (w[2 * nm + rk] if per_league else 0)
        ll = np.sum(np.logaddexp(0, z) - y * z); p = 1 / (1 + np.exp(-z)); r = p - y
        g = np.zeros(P); np.add.at(g, rm, r); np.add.at(g, nm + rm, r * x)
        if per_league: np.add.at(g, 2 * nm + rk, r); ll += 0.5 * lam * np.sum(w[2 * nm:] ** 2); g[2 * nm:] += lam * w[2 * nm:]
        return ll, g
    w0 = np.zeros(P); w0[nm:2 * nm] = 1.0
    w = minimize(f, w0, jac=True, method="L-BFGS-B").x
    return dict(mks=im, keys=ik, w=w, nm=nm)
def pred(M, df):
    nm = M["nm"]; out = np.empty(len(df))
    for i, (m, l, x) in enumerate(zip(df.mk, df.lg, df.lp)):
        j = M["mks"].get(m)
        if j is None: out[i] = x; continue
        z = M["w"][j] + M["w"][nm + j] * x
        k = M["keys"].get((m, l))
        if k is not None: z += M["w"][2 * nm + k]
        out[i] = z
    return 1 / (1 + np.exp(-out))
def walk(lam=None):
    res = np.full(len(E), np.nan); mons = sorted(E.mon.unique())
    for mo in mons:
        tr = E[E.mon < mo]
        if len(tr) < 50000: continue
        M = fit(tr.sample(min(len(tr), 400000), random_state=1) if len(tr) > 400000 else tr, lam if lam is not None else 0, lam is not None)
        idx = np.where(E.mon.values == mo)[0]; res[idx] = pred(M, E.iloc[idx])
    return res
def to3(p): return np.stack([p, 1 - p, np.zeros_like(p)], 1)   # binaria nello schema dell'harness (pari a probabilità 0)
def compare(pnew, name):
    df = pd.DataFrame(dict(date=E.date.values, lg=E.lg.values, season=E.season.values, y=np.where(E.y.values == 1, 0, 1)))
    ok = ~np.isnan(pnew)
    df["p_old"] = list(to3(E.p.values)); df["p_new"] = list(to3(np.where(ok, pnew, E.p.values)))
    df = df[ok]
    res = H.confronta(df)
    print(H.riepilogo(name, res), flush=True)
    return res
pB = walk(None); compare(pB, "B · correzione per mercato")
best = None
for lam in (20, 100, 500):
    pC = walk(lam)
    r = compare(pC, f"C · per mercato e campionato (λ={lam})")
    sc = r.get("scelta", {}).get("diff", 9)
    if best is None or sc < best[0]: best = (sc, lam, pC)
print("λ scelto sul periodo di scelta:", best[1])
E["pB"] = pB; E["pC"] = best[2]; E.to_pickle(P2 + "/f21_events.pkl")
# per mercato (holdout): app contro C
H_ = E[(E.date >= "2025-07-01") & E.pC.notna()]
ll = lambda p, y: -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
for m, g in H_.groupby("mk"):
    print(f"holdout {m:10s} n={len(g):6d} app {ll(g.p.values, g.y.values):.4f} · per mercato {ll(g.pB.values, g.y.values):.4f} · per campionato {ll(g.pC.values, g.y.values):.4f} · dichiarata {g.p.mean()*100:.1f}% → {g.pC.mean()*100:.1f}% · presa {g.y.mean()*100:.1f}%")
