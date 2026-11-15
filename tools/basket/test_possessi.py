"""Basket · test del fix dei possessi e dell'esclusione della preseason NBA (15/11/2026, Denny). Harness come modello.py:
log-loss di vittoria, totale (5 linee attorno all'atteso) e handicap per periodo e campionato, sulle stesse partite e linee per tutte le varianti
(partite di stagione regolare e playoff, linee dal modello pubblicato). Varianti: com'è / possessi sistemati / senza preseason / entrambi.
Uso: python tools/basket/test_possessi.py CARTELLA_ARCHIVIO [USCITA.json]"""
import sys, os, json, math, collections
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from bk_lib import load, team_model, per, Phi, rob, ll, SCELTA, NUOVO_FORMATO
DIR = sys.argv[1]; OUT = sys.argv[2] if len(sys.argv) > 2 else "basket_possessi.json"
V = {"com'è": dict(preseason=True, fix=False), "solo filtro": dict(preseason=True, fix=False, filt=True), "solo formato nuovo": dict(preseason=True, fix=True, filt=False), "possessi": dict(preseason=True, fix=True), "senza preseason": dict(preseason=False, fix=False), "entrambi": dict(preseason=False, fix=True)}
M = {}
for nm, kw in V.items():
    rows = team_model(load(DIR, **kw)); M[nm] = {r["id"]: r for r in rows if r["eh"] is not None}
    n = sum(1 for r in rows if r["qph"] and r["qpa"] and r["d"] >= NUOVO_FORMATO); n0 = sum(1 for r in rows if r["d"] >= NUOVO_FORMATO)
    print(nm, "partite con possessi calcolati dal gennaio 2026:", n, "su", n0)
ids = [i for i in M["entrambi"] if all(i in M[v] for v in V) and M["com'è"][i]["nh"] >= 5 and M["com'è"][i]["na"] >= 5 and M["entrambi"][i]["nh"] >= 5 and M["entrambi"][i]["na"] >= 5]
print("partite valutate", len(ids))
def per2(d): return per(d) if d < NUOVO_FORMATO else "dal 8/1/2026"
res = {"partite": len(ids)}
LL = {}
for nm in V:
    m = M[nm]; sig = {}
    for lg in set(m[i]["lg"] for i in ids):
        S = [m[i] for i in ids if m[i]["lg"] == lg and m[i]["d"] <= SCELTA]
        sig[lg] = (rob([r["ph"] - r["pa"] - r["eh"] + r["ea"] for r in S]), rob([r["ph"] + r["pa"] - r["eh"] - r["ea"] for r in S]))
    R = collections.defaultdict(list)
    for i in ids:
        r, r0 = m[i], M["com'è"][i]; ss, st = sig[r["lg"]]
        ms, mt = r["eh"] - r["ea"], r["eh"] + r["ea"]
        for p in {per(r["d"]), per2(r["d"])}:
            R[(p, "vittoria", r["lg"])].append(ll(Phi(ms / ss), 1 if r["ph"] > r["pa"] else 0))
            Lt = round(r0["eh"] + r0["ea"]) + 0.5
            R[(p, "totale", r["lg"])].append(np.mean([ll(1 - Phi((Lt + o - mt) / st), 1 if r["ph"] + r["pa"] > Lt + o else 0) for o in (-10, -5, 0, 5, 10)]))
            Ls = round(r0["eh"] - r0["ea"]) - 0.5
            R[(p, "handicap", r["lg"])].append(ll(1 - Phi((Ls - ms) / ss), 1 if r["ph"] - r["pa"] > Ls else 0))
    LL[nm] = R
    res[f"sigma {nm}"] = {lg: [round(a, 2), round(b, 2)] for lg, (a, b) in sorted(sig.items())}
base = LL["com'è"]
for nm in ("solo filtro", "solo formato nuovo", "possessi", "senza preseason", "entrambi"):
    out = {}
    for p in ("scelta", "verifica", "holdout", "dal 8/1/2026"):
        for mk in ("totale", "handicap", "vittoria"):
            ks = sorted(k for k in base if k[0] == p and k[1] == mk)
            if not ks: continue
            d = np.concatenate([np.array(LL[nm][k]) - np.array(base[k]) for k in ks])
            per_lg = {k[2]: round(float(np.mean(np.array(LL[nm][k]) - np.array(base[k]))), 4) for k in ks}
            se = d.std() / math.sqrt(len(d))
            out[f"{p} · {mk}"] = {"diff": round(float(d.mean()), 5), "z": round(float(d.mean() / se), 2) if se else 0.0, "migliorati": f"{sum(v < 0 for v in per_lg.values())}/{len(per_lg)}", "per_campionato": per_lg}
    res[nm] = out
# errore medio sul totale (punti) per periodo
mae = {}
for nm in V:
    for p in ("verifica", "holdout", "dal 8/1/2026"):
        x = [abs(M[nm][i]["ph"] + M[nm][i]["pa"] - M[nm][i]["eh"] - M[nm][i]["ea"]) for i in ids if p in (per(M[nm][i]["d"]), per2(M[nm][i]["d"]))]
        mae[f"{nm} · {p}"] = round(float(np.mean(x)), 2)
res["errore_medio_totale"] = mae
json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
for nm in ("solo filtro", "solo formato nuovo", "possessi", "senza preseason", "entrambi"):
    for k, v in res[nm].items(): print(nm, "|", k, v["diff"], "z", v["z"], v["migliorati"])
print(json.dumps(mae, ensure_ascii=False))
