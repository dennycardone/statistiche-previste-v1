"""Prevista 2.0 · fase 1-B: valori dei giocatori per la correzione dei falli con la formazione ufficiale (25/10/2026).
Dall'archivio delle formazioni (ramo formazioni, API-Football) calcola, con lo stesso metodo del test walk-forward (tools/p2/players.py):
  - per ogni giocatore: falli fatti, falli subiti e cartellini ogni 90 minuti (media mobile per presenza, peso 0,97), ristretti verso la
    media del suo ruolo con 5 partite fittizie;
  - per ogni squadra: la somma "abituale" dei titolari (media mobile delle ultime partite, peso 0,85 a partita);
  - la media per ruolo (giocatori senza storia).
Scrive formazioni/valori.json, letto da update_data.py quando escono le formazioni (circa un'ora prima della partita)."""
import json, glob, sys, datetime, numpy as np
FORM = sys.argv[1] if len(sys.argv) > 1 else "formazioni"
DP, DT, K = 0.97, 0.85, 5.0
POS = {"G": 0, "D": 1, "M": 2, "F": 3}
FX = []
for fn in glob.glob(FORM + "/*.json"):
    if fn.endswith("valori.json"): continue
    try: D = json.load(open(fn))
    except Exception: continue
    if not isinstance(D, dict) or "partite" not in D: continue
    for fid, v in D["partite"].items(): FX.append((v[0], fid, v))
FX.sort()
pl, role = {}, {}
G = np.zeros((4, 6)); G[:, :3] = 1e-9                  # per ruolo: minuti (3), somme (3): falli fatti, falli subiti, cartellini
def rates(pid):
    r = POS.get(role.get(pid, "M"), 2); g = G[r, 3:] / np.maximum(G[r, :3], 1e-9) * 90
    p = pl.get(pid)
    return g if p is None else (p[3:] + K * g) / (p[:3] / 90 + K)
team = {}
for d, fid, v in FX:
    _, hid, aid, hn, an, hg, ag, xh, xa, P = v
    for tid, xi in ((hid, xh), (aid, xa)):
        if len(xi) >= 10:
            agg = np.sum([rates(p) for p in xi], axis=0); T = team.setdefault(str(tid), np.zeros(4)); T[:3] = T[:3] * DT + agg; T[3] = T[3] * DT + 1
    for r in P:
        pid = r[0]; mi = r[2]
        if r[11]: role[pid] = r[11]
        x = np.array([r[7], r[8], r[5] + r[6]], float)
        a = pl.setdefault(pid, np.zeros(6)); a *= DP; a[:3] += mi; a[3:] += x
        rr = POS.get(role.get(pid, "M"), 2); G[rr] *= 0.9999; G[rr, :3] += mi; G[rr, 3:] += x
out = {"agg": datetime.date.today().isoformat(), "partite": len(FX), "ultima": FX[-1][0] if FX else None,
       "colonne": ["falli fatti", "falli subiti", "cartellini"],
       "ruoli": {k: [round(float(x), 4) for x in (G[i, 3:] / np.maximum(G[i, :3], 1e-9) * 90)] for k, i in POS.items()},
       "giocatori": {str(p): [round(float(x), 4) for x in rates(p)] + [role.get(p, "")] for p in pl},
       "squadre": {t: [round(float(x), 4) for x in (T[:3] / T[3])] for t, T in team.items() if T[3] >= 3}}
json.dump(out, open(FORM + "/valori.json", "w"), separators=(",", ":"))
print("valori:", len(out["giocatori"]), "giocatori,", len(out["squadre"]), "squadre, ultima partita", out["ultima"])
