"""Fase 2.1 · nuovo Grado come meta-modello. Dati: backtest walk-forward del Grado (out/bt_*.csv di conf_bt2.js, una riga per previsione
con probabilità del modello e fattori). Grado attuale: regressione logistica per mercato su logit(p) (gli altri fattori non aiutavano).
Fattori nuovi, tutti calcolati con le sole partite precedenti:
  storia_lm   scarto medio (uscito − probabilità) delle previsioni dello stesso mercato e campionato negli ultimi 60 giorni (ristretto)
  storia_sq   lo stesso per la squadra che "ha" l'esito, ultime 15 previsioni
  inizio      1 nelle prime 5 partite della stagione di una delle due squadre
  ln_tot      partite in stagione (già esistente)
Scelta in avanti dei fattori in walk-forward per stagione (come conf_fit2.py), giudizio sulle stagioni 2024-26."""
import glob, numpy as np, pandas as pd, collections
from sklearn.linear_model import LogisticRegression
D = pd.concat([pd.read_csv(f) for f in sorted(glob.glob("/tmp/claude-0/b2/out/bt_*.csv"))], ignore_index=True)
D = D[(D.base == "dyn") & D.p.notna() & (D.mk != "g15")].copy()
D = D.sort_values("date").reset_index(drop=True)
D["team"] = np.where(D.side.isin(["1"]), D.home, np.where(D.side.isin(["2"]), D.away, D.home))
# storia per mercato×campionato (ultimi 60 giorni, giorni precedenti) e per squadra (ultime 15), ristrette verso 0
D["dt"] = pd.to_datetime(D.date)
slm = np.zeros(len(D)); ssq = np.zeros(len(D))
hist_lm = collections.defaultdict(collections.deque); hist_sq = collections.defaultdict(collections.deque)
cur, pend = None, []
for i, r in enumerate(D.itertuples()):
    if r.date != cur:   # le previsioni dello stesso giorno entrano nella storia solo dal giorno dopo
        for k1, k2, dt, res in pend: hist_lm[k1].append((dt, res)); q = hist_sq[k2]; q.append(res); (len(q) > 15 and q.popleft())
        pend = []; cur = r.date
    k1, k2 = (r.mk, r.lg), (r.mk, r.lg, r.team)
    q = hist_lm[k1]
    while q and (r.dt - q[0][0]).days > 60: q.popleft()
    slm[i] = sum(x[1] for x in q) / (len(q) + 30); ssq[i] = sum(hist_sq[k2]) / (len(hist_sq[k2]) + 10)
    pend.append((k1, k2, r.dt, r.hit - r.p))
D["storia_lm"] = slm; D["storia_sq"] = ssq; D["inizio"] = (D.n_tot < 5).astype(int)
SEAS = sorted(D.season.unique()); TESTS = [s for s in SEAS if s >= 2024]
def ll(y, q): q = np.clip(q, 1e-6, 1 - 1e-6); return -np.mean(y * np.log(q) + (1 - y) * np.log(1 - q))
def oos(d, feats):
    ys, qs = [], []
    for Y in TESTS:
        tr, te = d[d.season < Y], d[d.season == Y]
        if len(tr) < 500 or not len(te): continue
        m = LogisticRegression(C=10.0, max_iter=2000).fit(tr[feats].values, tr.hit.values); ys.append(te.hit.values); qs.append(m.predict_proba(te[feats].values)[:, 1])
    return ll(np.concatenate(ys), np.concatenate(qs)), np.concatenate(ys), np.concatenate(qs)
CAND = ["storia_lm", "storia_sq", "inizio", "ln_tot", "ln_ven"]
tot_old = tot_new = n_all = 0
for mk, d in D.groupby("mk"):
    d = d[d.p >= 0.5]
    if len(d) < 3000: continue
    base, y, q0 = oos(d, ["lp"]); feats = ["lp"]; cur = base
    while True:
        best = None
        for c in CAND:
            if c in feats: continue
            v = oos(d, feats + [c])[0]
            if best is None or v < best[1]: best = (c, v)
        if not best or cur - best[1] < 3e-4: break
        feats.append(best[0]); cur = best[1]
    _, y, q1 = oos(d, feats)
    cls = lambda q: np.select([q >= .85, q >= .80, q >= .75, q >= .70], ["A+", "A", "B", "C"], "D")
    c0, c1 = cls(q0), cls(q1)
    rep = " · ".join(f"{k}: {int((c1 == k).sum())} prese {y[c1 == k].mean()*100:.0f}% (prima {int((c0 == k).sum())}, {y[c0 == k].mean()*100 if (c0 == k).sum() else float('nan'):.0f}%)" for k in ["A+", "A", "B"])
    print(f"{mk:4s} n={len(y):6d} log-loss Grado attuale {base:.4f} → meta-modello {cur:.4f} ({cur - base:+.4f}) fattori {feats} | {rep}", flush=True)
    tot_old += base * len(y); tot_new += cur * len(y); n_all += len(y)
print(f"TUTTI: {tot_old / n_all:.4f} → {tot_new / n_all:.4f}")
