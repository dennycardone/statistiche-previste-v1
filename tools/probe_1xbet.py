"""Prova: 1xBet su API-Football. Che mercati dà sulle partite dei prossimi giorni (corner, tiri, falli, cartellini, doppia chance)?
Stampa solo nomi di mercati e conteggi come annotazioni del giro (nessuna quota salvata)."""
import json, os, urllib.request, urllib.parse, datetime, collections, time
KEY = os.environ["APIFOOTBALL_KEY"].strip()
def get(p, **q):
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
    time.sleep(0.3); return d
def note(s): print("::notice title=1xBet::" + s.replace("%", "%25"))
bk = get("odds/bookmakers").get("response", [])
x = [b for b in bk if "1x" in b["name"].lower()]
note("Bookmaker API-Football: " + str(len(bk)) + " · 1xBet: " + json.dumps(x))
if x:
    bid = x[0]["id"]; mk = collections.Counter(); n = 0; ex = {}
    for dd in (0, 1, 2):
        day = (datetime.date.today() + datetime.timedelta(days=dd)).isoformat()
        for page in (1, 2, 3):
            R = get("odds", date=day, bookmaker=bid, page=page)
            for e in R.get("response", []):
                n += 1
                for b in e.get("bookmakers", []):
                    for bet in b.get("bets", []):
                        mk[bet["name"]] += 1
                        if any(w in bet["name"].lower() for w in ("corner", "shot", "foul", "card", "double")) and bet["name"] not in ex:
                            ex[bet["name"]] = [v["value"] + "=" + str(v["odd"]) for v in bet.get("values", [])][:8]
            if R.get("paging", {}).get("current", 1) >= R.get("paging", {}).get("total", 1): break
    note(f"Partite con quote 1xBet (oggi-dopodomani, prime pagine): {n}")
    items = sorted(mk.items(), key=lambda t: -t[1])
    for i in range(0, len(items), 40): note("Mercati: " + " | ".join(f"{a} ({b})" for a, b in items[i:i + 40]))
    for k_, v in ex.items(): note(f"Esempio {k_}: " + ", ".join(v))
