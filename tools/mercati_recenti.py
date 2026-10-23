"""Ultimi giorni (24/10/2026): per ogni 1X2 di nicchia, in quali campionati 1xBet lo ha quotato giorno per giorno (archivio privato).
Solo conteggi aggregati, nessuna quota, nessuna richiesta API. Serve a vedere i mercati appena aggiunti o tolti da 1xBet."""
import json, collections, datetime
OH = json.load(open("data/odds_hist.json"))
oggi = datetime.date.today(); giorni = [(oggi - datetime.timedelta(days=k)).isoformat() for k in range(7, -1, -1)]
MK = {"Falli 1X2": "x.f1x2", "Tiri 1X2": "x.s1x2", "Tiri in porta 1X2": "x.st1x2", "Gialli 1X2": "x.y1x2", "Fuorigioco 1X2": "x.off.offsides_1x2"}
tot = collections.Counter(); has = {m: collections.Counter() for m in MK}
for k, v in OH.items():
    lg, d = k.split("|")[:2]
    if d not in giorni: continue
    ks = {q.split(":")[0] for part in ("prima", "ultima") for q in (v.get(part) or {}).get("q", {}) if q.startswith("x.")}
    if not ks: continue
    tot[(lg, d)] += 1
    for m, key in MK.items():
        if key in ks: has[m][(lg, d)] += 1
for m in MK:
    lgs = sorted({lg for lg, d in has[m]})
    parts = []
    for lg in lgs:
        cells = [f"{d[8:]}/{d[5:7]} {has[m][(lg, d)]}/{tot[(lg, d)]}" for d in giorni if tot[(lg, d)]]
        parts.append(f"{lg}: " + " ".join(cells))
    print(f"::notice title={m} · ultimi 8 giorni::" + (" ‖ ".join(parts) or "nessuno"))
