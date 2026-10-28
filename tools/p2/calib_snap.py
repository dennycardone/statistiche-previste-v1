"""Fase 0 · fotografia della calibrazione per mercato e campionato (previsioni walk-forward dell'app, base/*.json + eventi q23).
Per ogni mercato (lato favorito dei 1X2 delle statistiche, Over/Under e Gol/No gol, 1X2 gol) e campionato, sulle partite da luglio 2025
(stagione in corso e fine della precedente): dichiarata media contro uscita reale, scarto con intervallo al 95%, ECE (errore medio di
calibrazione per fasce) e log-loss contro il riferimento "sempre la frequenza del campionato nelle partite precedenti"."""
import os as _os
P2 = _os.environ.get("RICERCA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "ricerca"))   # 28/10/2026: archivio di ricerca (ramo ricerca)
REPO = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
import pandas as pd, numpy as np, math
E = pd.read_pickle(P2 + "/q23_events.pkl")   # date, mid, mk, p, y (lato favorito / esito scelto)
import json, glob
lgof = {}
mid = 0
for fn in glob.glob(P2 + "/base/*.json"):
    pass
# ricostruisco campionato per mid con lo stesso ordine di lettura di q23_curse.py
B = []
for fn in glob.glob(P2 + "/base/*.json"):
    lg = fn.split("/")[-1][:-5]
    for r in json.load(open(fn)): B.append(lg)
E["lg"] = E.mid.map(lambda i: B[i])
E = E[E.date >= "2025-07-01"]
MKN = {"1X2 c": "Corner 1X2", "1X2 s": "Tiri 1X2", "1X2 st": "Tiri in porta 1X2", "1X2 f": "Falli 1X2", "1X2 o": "Fuorigioco 1X2",
       "Over 1.5": "Over 1,5", "Over 2.5": "Over 2,5", "Over 3.5": "Over 3,5", "Under 2.5": "Under 2,5", "Gol": "Gol/No gol", "No gol": "Gol/No gol", "1X2 gol": "1X2 gol"}
E["m"] = E.mk.map(MKN)
def ece(g):
    b = (g.p * 10).astype(int).clip(0, 9); t = 0
    for _, x in g.groupby(b): t += len(x) * abs(x.y.mean() - x.p.mean())
    return t / len(g)
rows = []
for (m, lg), g in E.groupby(["m", "lg"]):
    if len(g) < 60: continue
    d = g.y.mean() - g.p.mean(); se = math.sqrt(g.y.var() / len(g))
    rows.append(dict(m=m, lg=lg, n=len(g), dich=g.p.mean(), presa=g.y.mean(), scarto=d, z=d / se if se else 0, ece=ece(g)))
R = pd.DataFrame(rows)
print("=== per mercato (tutti i campionati, da luglio 2025)")
for m, g in E.groupby("m"):
    d = g.y.mean() - g.p.mean(); se = math.sqrt(g.y.var() / len(g))
    print(f"{m:18s} n={len(g):6d} dichiarata {g.p.mean()*100:5.1f}% presa {g.y.mean()*100:5.1f}% scarto {d*100:+5.1f} ±{1.96*se*100:.1f} · ECE {ece(g)*100:.1f} punti")
print("\n=== campionati che scivolano (|scarto| oltre 2 errori standard e oltre 4 punti)")
F = R[(R.z.abs() > 2) & (R.scarto.abs() > 0.04)].sort_values("scarto")
for r in F.itertuples(): print(f"{r.m:18s} {r.lg:4s} n={r.n:5d} dichiarata {r.dich*100:5.1f}% presa {r.presa*100:5.1f}% scarto {r.scarto*100:+5.1f} (z {r.z:+.1f}) ECE {r.ece*100:.1f}")
print("\n=== quante combinazioni campionato×mercato scivolano:", len(F), "su", len(R), "(atteso per caso con |z|>2: circa", round(len(R) * 0.046), ")")
print("\n=== peggior ECE per mercato (campionati con almeno 150 previsioni)")
for m, g in R[R.n >= 150].groupby("m"):
    w = g.sort_values("ece", ascending=False).head(3)
    print(f"{m:18s} " + " · ".join(f"{r.lg} {r.ece*100:.1f}" for r in w.itertuples()))
R.to_csv(P2 + "/calib_snap.csv", index=False)
