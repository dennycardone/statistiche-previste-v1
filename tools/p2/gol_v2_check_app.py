"""Fase 4 (Denny): l'app con la V2 riproduce la V2 congelata di Python? λ casa/ospite, rho, 1X2, Over 2,5, Gol/No gol; e M0 resta identico."""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__)); from gol_v2 import *; from gol_eval import matrices, TOT
df = pd.read_pickle(os.path.join(REPO, "ricerca", "gol", "feat.pkl"))
lh, la = v2(df); T = json.load(open(os.path.join(os.path.dirname(__file__), "gol_v2_congelata.json")))["rho_per_mese"]
df = df.assign(l2h=lh, l2a=la, rho=df.date.dt.to_period("M").astype(str).map(T), ds=df.date.dt.strftime("%Y-%m-%d")).set_index(["lg", "ds", "h", "a"])
rows = []
for f in sorted(os.listdir(os.path.join(REPO, "ricerca", "gol"))):
    if not f.endswith(".json") or len(f) > 8: continue
    lg = f[:-5]
    for r in json.load(open(os.path.join(REPO, "ricerca", "gol", f)))["ref"]:
        k = (lg, r["d"], r["h"], r["a"])
        if k not in df.index or r.get("lh") is None: continue
        x = df.loc[k]
        if isinstance(x, pd.DataFrame): x = x.iloc[0]
        rows.append((r["lh"], r["la"], x.l2h, x.l2a, r.get("rho"), x.rho, *r["p"], *(r.get("m0") or [np.nan, np.nan]), x.lh0, x.la0))
R = np.array(rows, float)
M = matrices(R[:, 2], R[:, 3], R[:, 5]); p1 = np.tril(M, -1).sum((1, 2)); px = np.trace(M, axis1=1, axis2=2); p2 = np.triu(M, 1).sum((1, 2))
print("partite confrontate", len(R))
print("λ V2 app − Python: max", np.abs(R[:, 0] - R[:, 2]).max(), np.abs(R[:, 1] - R[:, 3]).max())
print("rho app − Python: max", np.nanmax(np.abs(R[:, 4] - R[:, 5])))
print("1X2 app − Python (Dixon-Coles): max", np.abs(R[:, 6] - p1).max(), np.abs(R[:, 7] - px).max(), np.abs(R[:, 8] - p2).max())
print("M0 dentro l'app (λ prima della forma) − M0 Python: max", np.nanmax(np.abs(R[:, 9] - R[:, 11])), np.nanmax(np.abs(R[:, 10] - R[:, 12])))
