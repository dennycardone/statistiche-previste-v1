"""Falli · quale tetto per il fattore arbitro? (18/11/2026, Denny: "questo 4% chi l'ha scelto? e se col 5 o 6% va meglio?")
Griglia di tetti verso l'alto (0%, 1%, …, 12%, nessuno) e di pavimenti verso il basso, sul modello di produzione + derby.
Scelta del tetto SOLO nel periodo di sviluppo (fino al 30/6/2024), poi verifica 2024-25 e holdout da luglio 2025, contro il tetto attuale +4%."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lab"))
from comune import boot
from scipy.stats import nbinom
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
P = pd.read_pickle(os.path.join(REPO, "ricerca", "falli", "audit.pkl")); J, db = P["J"], P["db"]
k_nocap = [k for k in P["MODELS"] if "senza tetto" in k][0]; f0 = P["MODELS"][k_nocap][0] / J.l0h.values   # fattore arbitro della produzione senza tetto
dF = np.where(db == 1, np.exp(0.0564), 1.0)
yh, ya = J.yh.values, J.ya.values
def ll(f):
    lh, la = J.l0h.values * f * dF, J.l0a.values * f * dF; lp = lambda y, mu, r: nbinom.logpmf(y, r, r / (r + mu))
    return -(lp(yh, lh, 200) + lp(ya, la, 200)), -lp(yh + ya, lh + la, 150)
per = J.per.values; wk = J.wk.values
caps = [1.0, 1.01, 1.02, 1.03, 1.04, 1.05, 1.06, 1.07, 1.08, 1.10, 1.12, None]
floors = [None, 0.97, 0.96, 0.95, 0.94, 0.92]
res = {}
for c in caps:
    for fl in floors:
        f = f0.copy()
        if c is not None: f = np.minimum(f, c)
        if fl is not None: f = np.maximum(f, fl)
        res[(c, fl)] = ll(f)
ref = res[(1.04, None)]
print("quota di partite in cui il tetto +4% taglia il fattore:", f"{(f0 > 1.04).mean()*100:.1f}%", "· fattore oltre +6%:", f"{(f0 > 1.06).mean()*100:.1f}%", "· sotto −4%:", f"{(f0 < 0.96).mean()*100:.1f}%")
print(f"{'tetto':>7} {'pavim.':>7} | {'sviluppo':>9} {'verifica':>9} {'holdout':>9}   (log-loss falli per squadra, differenza dal tetto +4%; negativo = meglio)")
rows = []
for (c, fl), (lt, lT) in res.items():
    d = [float((lt - ref[0])[per == p].mean()) for p in ("scelta", "verifica", "holdout")]
    rows.append(((c, fl), d))
    if fl is None or c == 1.04: print(f"{('nessuno' if c is None else f'+{round((c-1)*100)}%'):>7} {('nessuno' if fl is None else f'{round((fl-1)*100)}%'):>7} | {d[0]:+9.5f} {d[1]:+9.5f} {d[2]:+9.5f}")
best = min(rows, key=lambda r: r[1][0]); (bc, bf), _ = best
print("\nscelto nel periodo di sviluppo: tetto", bc, "pavimento", bf)
lt = res[(bc, bf)][0]; lT = res[(bc, bf)][1]
for p in ("verifica", "holdout"):
    m = per == p; d = (lt - ref[0])[m]; mu, lo, hi = boot(d, wk[m], q=(2.5, 97.5)); lg = pd.Series(d).groupby(J.lg.values[m]).mean()
    dt = (lT - ref[1])[m]; mt, lot, hit = boot(dt, wk[m], q=(2.5, 97.5))
    print(f"  {p}: per squadra {mu:+.5f} [{lo:+.5f}, {hi:+.5f}] campionati {(lg < 0).sum()}/{len(lg)} · totale {mt:+.5f} [{lot:+.5f}, {hit:+.5f}]")
