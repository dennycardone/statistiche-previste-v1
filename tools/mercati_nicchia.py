"""Quali campionati hanno i mercati di nicchia su 1xBet (archivio quote privato data/odds_hist.json).
Gira solo in GitHub Actions; stampa solo conteggi aggregati come annotazioni (nessuna quota)."""
import json, collections, sys
OH = json.load(open("data/odds_hist.json"))
NAMES = {"c1x2": "Corner 1X2", "cdc": "Corner doppia chance", "s1x2": "Tiri 1X2", "st1x2": "Tiri in porta 1X2", "f1x2": "Falli 1X2",
         "fdc": "Falli doppia chance", "y1x2": "Gialli 1X2", "ydc": "Gialli doppia chance", "cou": "Corner O/U", "hcou": "Corner casa O/U",
         "acou": "Corner ospite O/U", "sou": "Tiri O/U", "sot": "Tiri in porta O/U", "fou": "Falli O/U", "kou": "Cartellini O/U", "cah": "Corner handicap", "kah": "Cartellini handicap"}
tot = collections.Counter(); has = collections.defaultdict(collections.Counter); since = None
for k, v in OH.items():
    lg, d = k.split("|")[:2]
    keys = set()
    for part in ("prima", "ultima"):
        for q in (v.get(part) or {}).get("q", {}):
            if q.startswith("x."): keys.add(q[2:].split(":")[0])
    if not keys: continue
    tot[lg] += 1; since = min(since or d, d)
    for m in keys: has[m][lg] += 1
lines = []
for m, nm in NAMES.items():
    c = has.get(m, {})
    lst = sorted(((lg, n, tot[lg]) for lg, n in c.items()), key=lambda x: -x[1] / x[2])
    good = [f"{lg} {round(100*n/t)}%" for lg, n, t in lst if n / t >= 0.5]
    weak = [f"{lg} {round(100*n/t)}%" for lg, n, t in lst if n / t < 0.5]
    lines.append(f"{nm}: {len(good)} campionati ≥50% → " + (", ".join(good) or "nessuno") + (" | sotto 50%: " + ", ".join(weak) if weak else ""))
# mercati del primo tempo (x.h1.*) e dei fuorigioco (x.off.*, dal 17/10/2026): nomi come arrivano da API-Football
for m in sorted(k for k in has if k.startswith(("h1.", "off."))):
    c = has[m]; lst = sorted(((lg, n, tot[lg]) for lg, n in c.items()), key=lambda x: -x[1] / x[2])
    good = [f"{lg} {round(100*n/t)}%" for lg, n, t in lst if n / t >= 0.5]
    lines.append(f"{m}: {len(good)} campionati ≥50% → " + (", ".join(good) or "nessuno") + f" | presenti in {len(lst)} campionati")
print(f"::notice title=Base::partite con quote 1xBet dal {since}: {sum(tot.values())} in {len(tot)} campionati: " + ", ".join(f"{lg} {n}" for lg, n in tot.most_common()))
for i in range(0, len(lines), 2):
    print("::notice title=Mercati " + str(i // 2 + 1) + "::" + " ‖ ".join(lines[i:i + 2]))
