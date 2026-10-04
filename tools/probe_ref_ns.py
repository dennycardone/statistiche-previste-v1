"""Quante partite non ancora giocate hanno già l'arbitro indicato (oggi + prossimi 6 giorni, nostri campionati)."""
import json, os, urllib.request, urllib.parse, datetime, collections
KEY = os.environ["APIFOOTBALL_KEY"].strip()
IDS = {135,136,39,40,41,42,43,140,141,61,62,78,79,88,94,179,180,183,184,144,203,197,128,218,71,169,119,244,357,98,262,103,106,283,235,113,207,253}
out = {}
for k in range(7):
    d = str(datetime.date.today() + datetime.timedelta(days=k))
    req = urllib.request.Request("https://v3.football.api-sports.io/fixtures?" + urllib.parse.urlencode({"date": d}), headers={"x-apisports-key": KEY})
    F = json.loads(urllib.request.urlopen(req, timeout=60).read().decode()).get("response", [])
    ns = [f for f in F if f["league"]["id"] in IDS and f["fixture"]["status"]["short"] in ("NS", "TBD")]
    out[d] = {"partite": len(ns), "con_arbitro": sum(1 for f in ns if f["fixture"].get("referee")),
              "esempi": [(f["league"]["name"], f["teams"]["home"]["name"], f["teams"]["away"]["name"], f["fixture"].get("referee")) for f in ns][:12]}
os.makedirs("probe", exist_ok=True); json.dump(out, open("probe/apifootball.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({d: (v["partite"], v["con_arbitro"]) for d, v in out.items()}))
