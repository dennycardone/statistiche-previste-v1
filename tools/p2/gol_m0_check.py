"""Fase 3, punto 1 (Denny): la replica Python di M0 riproduce l'app? Confronto partita per partita di λ casa, λ ospite e 1X2."""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from gol_lib import *
TA = load_tarea(); out = {}; allr = []
codes = sys.argv[1].split(",") if len(sys.argv) > 1 else sorted(f[:-5] for f in os.listdir(os.path.join(REPO, "ricerca", "gol")))
for c in codes:
    L = League(c, TA); rows = []
    for r in L.ref:
        if r.get("lh") is None: continue
        res = L.m0(day(r["d"]), r["h"], r["a"])
        if res is None: rows.append((r["lh"], r["la"], np.nan, np.nan, *r["p"], np.nan, np.nan, np.nan)); continue
        M = score_matrix(*res); p = p1x2(M)
        rows.append((r["lh"], r["la"], res[0], res[1], *r["p"], *p))
    R = np.array(rows, float); allr.append(R)
    dl = np.abs(np.r_[R[:, 2] - R[:, 0], R[:, 3] - R[:, 1]]); dp = np.abs(R[:, 7:10] - R[:, 4:7])
    print(f"{c:4} n={len(R):5} λ: diff media {np.nanmean(dl):.2e} max {np.nanmax(dl):.2e} · senza replica {np.isnan(R[:,2]).sum()} · 1X2 diff max {np.nanmax(dp):.2e}", flush=True)
R = np.vstack(allr); dl = np.abs(np.r_[R[:, 2] - R[:, 0], R[:, 3] - R[:, 1]]); dp = np.abs(R[:, 7:10] - R[:, 4:7])
print(f"TUTTI n={len(R)} λ diff media {np.nanmean(dl):.2e} · 99° percentile {np.nanpercentile(dl,99):.2e} · max {np.nanmax(dl):.2e} · quota con diff < 1e-4: {np.nanmean(dl<1e-4)*100:.2f}% · 1X2 diff max {np.nanmax(dp):.2e}")
