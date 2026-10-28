"""Prevista 2.0 · fase 1-A: le formazioni migliorano il 1X2 di tiri, tiri in porta, falli, fuorigioco e corner?
Baseline = previsioni dell'app con i soli dati precedenti (base/*.json). Correzione e^(b·x) sui valori attesi di ogni squadra, pesi
stimati mese per mese sulle sole partite precedenti (harness.walk_forward), 1X2 ricalcolato con le stesse distribuzioni dell'app
(harness.h2h). Scelta delle variabili sul periodo "scelta", giudizio su "verifica" e "holdout" (harness.confronta)."""
import os as _os
P2 = _os.environ.get("RICERCA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "ricerca"))   # 28/10/2026: archivio di ricerca (ramo ricerca)
REPO = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
import json, glob, pickle, collections, sys, datetime, numpy as np, pandas as pd
sys.path.insert(0, REPO + "/tools"); import harness as H
FEAT = pickle.load(open(sys.argv[1] if len(sys.argv) > 1 else "feat.pkl", "rb"))
B = []
for fn in glob.glob("base/*.json"):
    lg = fn.split("/")[-1][:-5]
    for r in json.load(open(fn)): r["lg"] = lg; B.append(r)
print("baseline", len(B))
FK = FEAT
def feat_of(r):
    for dd in (0, -1, 1):
        d = (datetime.date.fromisoformat(r["d"]) + datetime.timedelta(days=dd)).isoformat()
        f = FK.get((r["lg"], d, r["h"], r["a"]))
        if f: return f
    return None
MK = {"s": "Tiri", "st": "Tiri in porta", "f": "Falli", "o": "Fuorigioco", "c": "Corner"}
CAND = {k: [["own:xi_nulla", "opp:xi_nulla"], ["own:xi_late", "own:xi_nulla", "opp:xi_nulla"], ["own:xi_gap"]] for k in ("s", "st", "f", "c")}
MK = {"s": "Tiri", "st": "Tiri in porta", "f": "Falli", "c": "Corner"}
rows = []
for r in B:
    f = feat_of(r)
    rows.append((r, f))
print("partite con formazioni abbinate", sum(1 for _, f in rows if f and f.get("h") and f.get("a")), "su", len(rows))
def team_table(k, feats, scen):
    out = []
    for i, (r, f) in enumerate(rows):
        m = r.get(k); y = r["y"].get(k)
        if not m or y is None or y[0] is None or y[1] is None or not f or not f.get("h") or not f.get("a"): continue
        for side, o_, j in (("h", "a", 0), ("a", "h", 1)):
            x = {}
            for nm in feats:
                src, v = nm.split(":"); v = v.replace("xi_", scen + "_")
                x[nm] = f[side if src == "own" else o_].get(v, np.nan)
            out.append(dict(i=i, side=j, date=r["d"], lg=r["lg"], season=r["se"], mu0=m[j], y=y[j], **x))
    return pd.DataFrame(out)
def probs(k, T):
    """1X2 corretto (mu) e dell'app (mu0) per le partite con entrambe le squadre corrette"""
    P = []
    for i, g in T.groupby("i"):
        if len(g) != 2 or g.mu.isna().any(): continue
        r = rows[i][0]; m = r[k]; y = r["y"][k]
        rt = None if m[2] in (-1, None) else m[2]; rT = m[3]
        if rT == -1: rT = float("inf")
        gh, ga = g[g.side == 0].iloc[0], g[g.side == 1].iloc[0]
        ck = (k, i)
        if ck not in POLD: POLD[ck] = H.h2h(m[0], m[1], rt, rT, m[4] or 0.0)
        po = POLD[ck]; pn = H.h2h(gh.mu, ga.mu, rt, rT, m[4] or 0.0)
        P.append(dict(date=r["d"], lg=r["lg"], season=r["se"], y=0 if y[0] > y[1] else 1 if y[0] == y[1] else 2, p_old=po, p_new=pn))
    return pd.DataFrame(P)
REP = {}
POLD = {}
for scen, lab in (("xi", "posta in gioco"),):
    for k, name in MK.items():
        best = None
        for feats in CAND[k]:
            T = team_table(k, feats, scen)
            if not len(T): continue
            rT = rows[T.i.iloc[0]][0][k][3]; rT = None if rT in (-1, None) else rT
            T2, coefs = H.walk_forward(T, feats, r=rT)
            PP = probs(k, T2)
            if not len(PP): continue
            res = H.confronta(PP)
            sc = res.get("scelta", {}).get("diff", 9)
            print(f"[{lab}] {name} {feats}: scelta {sc:+.5f}", flush=True)
            if best is None or sc < best[0]: best = (sc, feats, res, coefs)
        if best:
            last = {kk: [round(float(x), 3) for x in v] for kk, v in list(best[3].items())[-1:]}
            REP[f"{lab} · {name}"] = dict(variabili=best[1], pesi_ultimi=last, **best[2])
            print(H.riepilogo(f"{lab} · {name} · {best[1]}", best[2]), flush=True)
json.dump(REP, open(sys.argv[2] if len(sys.argv) > 2 else "res_1a.json", "w"), indent=1, default=float)
