"""Quota 2 / Quota 3 · inventario dell'archivio privato delle quote 1xBet (data/odds_hist.json), 25/10/2026.
Solo numeri aggregati: da quando c'è l'archivio, quante partite già giocate hanno quote per ogni mercato (prima vista e ultima vista
prima del fischio), quante per giorno. Serve a sapere su quanti giorni si può validare la scelta di Quota 2 e Quota 3."""
import json, collections, datetime
OH = json.load(open("data/odds_hist.json"))
today = datetime.date.today().isoformat()
MK = {"1X2": "1x2:", "Over/Under 1,5": "ou1.5:", "Over/Under 2,5": "ou2.5:", "Over/Under 3,5": "ou3.5:", "Gol/No gol": "gg:",
      "Corner 1X2": "x.c1x2:", "Tiri 1X2": "x.s1x2:", "Tiri in porta 1X2": "x.st1x2:", "Falli 1X2": "x.f1x2:", "Gialli 1X2": "x.y1x2:", "Fuorigioco 1X2": "x.off.offsides_1x2:"}
days, cnt, lgs = collections.Counter(), collections.Counter(), collections.Counter()
first = last = None; keys = collections.Counter()
for k, v in OH.items():
    lg, d = k.split("|")[:2]
    if d >= today: continue
    days[d] += 1; lgs[lg] += 1; first = min(first or d, d); last = max(last or d, d)
    q = {**((v.get("prima") or {}).get("q") or {}), **((v.get("ultima") or {}).get("q") or {})}
    for kk in q: keys[kk.split(":")[0]] += 1
    for name, pre in MK.items():
        if any(x.startswith(pre) for x in q): cnt[name] += 1
n = sum(days.values())
msg = [f"partite giocate nell'archivio {n}, dal {first} al {last}, giorni con partite {len(days)}, campionati {len(lgs)}",
       "per mercato: " + " · ".join(f"{m} {cnt[m]}" for m in MK),
       "partite per giorno (min/mediana/max): %d / %d / %d" % (min(days.values()), sorted(days.values())[len(days) // 2], max(days.values())),
       "chiavi più frequenti: " + ", ".join(f"{k} {c}" for k, c in keys.most_common(40)),
       "struttura di una voce: " + json.dumps({k: (list(v.keys()) if isinstance(v, dict) else type(v).__name__) for k, v in next(iter(OH.values())).items()})]
for m in msg: print("::notice title=Inventario quote::" + m.replace("%", "%25"))
