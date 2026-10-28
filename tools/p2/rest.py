"""Agente di ricerca · ipotesi 1: giorni di riposo e stanchezza. Per ogni partita e squadra (campionato + coppe europee dell'archivio
formazioni, stesso id squadra API-Football): giorni dall'ultima partita (tetto 14), partite negli ultimi 14 giorni, coppa europea negli
ultimi 4 giorni. Uscita feat_rest.pkl con le stesse chiavi di feat.pkl (campionato, data, casa, ospite, gol), così test1a.py lo usa."""
import os as _os
P2 = _os.environ.get("RICERCA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "ricerca"))   # 28/10/2026: archivio di ricerca (ramo ricerca)
REPO = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
import json, glob, pickle, datetime, collections, bisect
FX = []
for fn in glob.glob(P2 + "/form2/*.json"):
    D = json.load(open(fn))
    if not isinstance(D.get("partite"), dict) or "lega" not in D: continue   # 28/10/2026: valori.json e altri file non di campionato
    for fid, v in D["partite"].items(): FX.append((v[0][:10], D["lega"], v))
sched = collections.defaultdict(list)
for d, lg, v in FX:
    for t in (v[1], v[2]): sched[t].append((d, lg in ("UCL", "UEL", "UECL")))
for t in sched: sched[t].sort()
F = {}
for d, lg, v in FX:
    if lg in ("UCL", "UEL", "UECL"): continue
    d0 = datetime.date.fromisoformat(d); f = {}
    for side, t in (("h", v[1]), ("a", v[2])):
        L = sched[t]; i = bisect.bisect_left(L, (d, False))
        prev = [x for x in L[max(0, i - 10):i] if x[0] < d]
        if not prev: f[side] = None; continue
        last = datetime.date.fromisoformat(prev[-1][0]); rest = min(14, (d0 - last).days)
        n14 = sum(1 for x in prev if (d0 - datetime.date.fromisoformat(x[0])).days <= 14)
        eu = int(any(x[1] and (d0 - datetime.date.fromisoformat(x[0])).days <= 4 for x in prev))
        f[side] = {"xi_rest": rest, "xi_rest3": int(rest <= 3), "xi_n14": n14, "xi_eu": eu}
    F[(lg, d, v[3], v[4], v[5], v[6])] = f
pickle.dump(F, open(P2 + "/feat_rest.pkl", "wb"))
print("partite", len(F), "· con riposo ≤3 giorni:", sum(1 for f in F.values() for s in ("h", "a") if f.get(s) and f[s]["xi_rest3"]))
