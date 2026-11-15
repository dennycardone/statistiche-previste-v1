"""Basket · che cosa è "Player Runs" di Betano? (15/11/2026, Denny). Confronta la linea (Over x,5) di ogni giocatore con le sue medie in archivio
(rimbalzi, assist, punti, triple segnate) nelle ultime 2 stagioni NBA: la voce con correlazione più alta e scarto medio più piccolo è quella giusta.
Come controllo, lo stesso su "Player Points and Assists" (deve corrispondere a punti + assist). Solo numeri aggregati, nessuna quota.
Uso: python tools/basket/sonda_runs.py CARTELLA_ARCHIVIO QUOTE.json"""
import json, glob, os, sys, re, collections, unicodedata
import numpy as np
DIR, QF = sys.argv[1], sys.argv[2]
def norm(s): return frozenset(re.sub(r"[^a-z ]", " ", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()).split())
NAME, ST = {}, collections.defaultdict(lambda: np.zeros(6))
for fn in sorted(glob.glob(os.path.join(DIR, "NBA_*.json")))[-2:]:
    D = json.load(open(fn))
    for k, v in (D.get("nomi") or {}).items(): NAME[norm(v)] = k
    for gid, ps in (D.get("gioc") or {}).items():
        for p in ps:
            if not p[3] or None in (p[4], p[11], p[12]): continue
            ST[str(p[0])] += [1, p[4], p[11], p[12], p[7] or 0, p[3]]
Q = json.load(open(QF)).get("partite", {})
lines = collections.defaultdict(lambda: collections.defaultdict(list))
for e in Q.values():
    for m, vals in (e.get("c") or [None, {}])[1].items():
        if not m.lower().startswith("player "): continue
        for v in vals:
            mm = re.match(r"^(.*?)\s*-\s*(?:Over\s+)?(\d+(?:\.\d+)?)$", v)
            if mm and ("Over" in v or m == "Player Points Milestones"): lines[m][mm.group(1)].append(float(mm.group(2)))
out = []
for m, pl in lines.items():
    X = []
    nomatch = 0
    for nm, ls in pl.items():
        pid = NAME.get(norm(nm))
        if not pid or ST[pid][0] < 5: nomatch += 1; continue
        s = ST[pid]; n = s[0]
        X.append((float(np.median(ls)), s[1] / n, s[2] / n, s[3] / n, s[4] / n, (s[1] + s[3]) / n, (s[2] + s[3]) / n))
    if len(X) < 5: out.append(f"{m}: {len(X)} giocatori abbinati (pochi), non abbinati {nomatch}"); continue
    X = np.array(X); res = []
    for i, lab in ((1, "punti"), (2, "rimbalzi"), (3, "assist"), (4, "triple"), (5, "punti+assist"), (6, "rimbalzi+assist")):
        res.append((float(np.corrcoef(X[:, 0], X[:, i])[0, 1]), float(np.mean(np.abs(X[:, 0] - X[:, i]))), lab))
    res.sort(reverse=True)
    out.append(f"{m} ({len(X)} giocatori, non abbinati {nomatch}): " + " · ".join(f"{lab} corr {c:.2f} scarto {d:.1f}" for c, d, lab in res))
print("::notice title=Basket · che cosa sono i mercati giocatori::" + " | ".join(out)[:3800])
