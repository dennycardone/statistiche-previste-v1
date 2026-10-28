"""Quota 2 / Quota 3 · distorsione da selezione del massimo (winner's curse), solo con le probabilità di Prevista (47.000 partite).
Per ogni partita giocata dal 2023 le probabilità dell'app calcolate con i soli dati precedenti (base/*.json): Over 1,5/2,5/3,5,
Under 2,5, Gol/No gol, 1X2 gol (lato favorito), 1X2 di corner, tiri, tiri in porta, falli, fuorigioco (lato favorito).
Ogni giorno si sceglie la combinazione "migliore" (probabilità congiunta massima dentro la fascia che corrisponde a una quota 2 o 3),
come singola, doppia o tripla di partite diverse. Si confronta la probabilità dichiarata con l'uscita reale, poi si stima una
calibrazione sulle sole giornate precedenti (binning isotonico) e si ricontrolla. Nessuna quota: le fasce sono di probabilità."""
import os as _os
P2 = _os.environ.get("RICERCA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "ricerca"))   # 28/10/2026: archivio di ricerca (ramo ricerca)
REPO = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
import json, glob, math, sys, itertools, collections, numpy as np, pandas as pd
sys.path.insert(0, REPO + "/tools"); import harness as H
from scipy.stats import poisson
ev = []   # (date, match_id, mercato, p, esito)
B = []
for fn in glob.glob(P2 + "/base/*.json"):
    lg = fn.split("/")[-1][:-5]
    for r in json.load(open(fn)): r["lg"] = lg; B.append(r)
def dc_matrix(lh, la, rho, N=10):
    M = np.outer(poisson.pmf(np.arange(N + 1), lh), poisson.pmf(np.arange(N + 1), la))
    if rho:
        M[0, 0] *= 1 - lh * la * rho; M[0, 1] *= 1 + lh * rho; M[1, 0] *= 1 + la * rho; M[1, 1] *= 1 - rho
    return M / M.sum()
import os
for mid, r in enumerate(B):
    if os.path.exists(P2 + "/q23_events.pkl"): break
    if r["d"] < "2023-07-01": continue
    y = r["y"]
    if r.get("g") and y["g"][0] is not None:
        M = dc_matrix(*r["g"]); hg, ag = y["g"]; T = hg + ag
        tot = np.add.outer(np.arange(11), np.arange(11))
        for L in (1.5, 2.5, 3.5):
            po = M[tot > L].sum(); ev.append((r["d"], mid, f"Over {L}", po, int(T > L)))
        ev.append((r["d"], mid, "Under 2.5", M[tot < 2.5].sum(), int(T < 2.5)))
        gg = M[1:, 1:].sum(); ev.append((r["d"], mid, "Gol" if gg >= 0.5 else "No gol", max(gg, 1 - gg), int((hg > 0 and ag > 0) == (gg >= 0.5))))
        p1, px = np.tril(M, -1).sum(), np.trace(M); p2 = 1 - p1 - px
        ev.append((r["d"], mid, "1X2 gol", max(p1, p2), int((hg > ag) if p1 >= p2 else (ag > hg))))
    for k in ("c", "s", "st", "f", "o"):
        m = r.get(k); yy = y.get(k)
        if not m or yy is None or yy[0] is None or yy[1] is None: continue
        rt = None if m[2] in (-1, None) else m[2]; rT = float("inf") if m[3] == -1 else m[3]
        P = H.h2h(m[0], m[1], rt, rT, m[4] or 0.0); one = P[0] >= P[2]
        ev.append((r["d"], mid, "1X2 " + k, P[0] if one else P[2], int(yy[0] > yy[1]) if one else int(yy[1] > yy[0])))
E = pd.DataFrame(ev, columns=["date", "mid", "mk", "p", "y"]) if not __import__("os").path.exists(P2 + "/q23_events.pkl") else pd.read_pickle(P2 + "/q23_events.pkl")
print("eventi", len(E), "giorni", E.date.nunique(), flush=True)
E.to_pickle(P2 + "/q23_events.pkl")
# calibrazione dei singoli eventi (tutti) per controllo
E["bin"] = (E.p // 0.05) * 0.05
print(E[E.p >= 0.5].groupby("bin").agg(n=("y", "size"), presi=("y", "mean"), p=("p", "mean")).round(3).to_string())
BANDS = {"Quota 2": (0.45, 0.55), "Quota 3": (0.30, 0.37)}
def pick(day, n, lo, hi):
    """combinazione di n eventi di partite diverse con probabilità congiunta massima dentro [lo, hi]"""
    d = day.sort_values("p", ascending=False)
    if n == 1:
        x = d[(d.p >= lo) & (d.p <= hi)]
        return (x.p.iloc[0], int(x.y.iloc[0]), [x.mk.iloc[0]]) if len(x) else None
    tgt = hi ** (1 / n)
    pool = pd.concat([d.head(40 if n == 2 else 18), d.iloc[(d.p - tgt).abs().argsort()[:40 if n == 2 else 18]]]).drop_duplicates()
    best = None
    for comb in itertools.combinations(pool.itertuples(), n):
        if len({c.mid for c in comb}) < n: continue
        P = math.prod(c.p for c in comb)
        if lo <= P <= hi and (best is None or P > best[0]): best = (P, int(all(c.y for c in comb)), [c.mk for c in comb])
    return best
rows = []
for date, day in E.groupby("date"):
    for q, (lo, hi) in BANDS.items():
        for n in (1, 2, 3):
            b = pick(day, n, lo, hi)
            if b: rows.append(dict(date=date, quota=q, n=n, p=b[0], y=b[1], mk="+".join(b[2])))
R = pd.DataFrame(rows); R.to_pickle(P2 + "/q23_picks.pkl")
print("\nSCELTA DEL GIORNO (massima probabilità nella fascia): dichiarata contro reale")
for (q, n), g in R.groupby(["quota", "n"]):
    se = math.sqrt(g.y.mean() * (1 - g.y.mean()) / len(g))
    print(f"{q} {['', 'singola', 'doppia', 'tripla'][n]:8s}: giorni {len(g):4d}, dichiarata {g.p.mean()*100:5.1f}%, presa {g.y.mean()*100:5.1f}% (±{1.96*se*100:.1f}), differenza {(g.y.mean()-g.p.mean())*100:+5.1f} punti")
# calibrazione walk-forward: rapporto reale/dichiarata stimato sulle sole giornate precedenti (per quota e struttura), poi ricontrollo
print("\nCON CALIBRAZIONE WALK-FORWARD (fattore stimato sulle giornate precedenti, almeno 60)")
for (q, n), g in R.groupby(["quota", "n"]):
    g = g.sort_values("date").reset_index(drop=True); adj = []
    for i in range(len(g)):
        prev = g.iloc[:i]
        if len(prev) < 60: adj.append(np.nan); continue
        k = (prev.y.sum() + 10) / (prev.p.sum() + 10)   # fattore ristretto verso 1
        adj.append(min(0.99, g.p.iloc[i] * k))
    g["pc"] = adj; h = g.dropna()
    for a, b in (("2023-07-01", "2024-06-30"), ("2024-07-01", "2025-06-30"), ("2025-07-01", "2100-01-01")):
        x = h[(h.date >= a) & (h.date <= b)]
        if len(x): print(f"{q} {['', 'singola', 'doppia', 'tripla'][n]:8s} {a[:7]}→: giorni {len(x):4d}, dichiarata calibrata {x.pc.mean()*100:5.1f}%, presa {x.y.mean()*100:5.1f}%")
