"""Prova (19/10/2026): quote di API-Football per la MLS (perché le partite di Cincinnati & co. non hanno quote 1xBet).
Poche richieste (stato + partite del giorno + quote di 3 partite), solo se avanzano dopo la riserva dell'app (tools/af_budget.py)."""
import json, os, sys, urllib.request, urllib.parse, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import af_budget
KEY = os.environ["APIFOOTBALL_KEY"].strip()
def get(p, **q):
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + "?" + urllib.parse.urlencode(q), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
budget = af_budget.test_budget(af_budget.requests_of(get("status")))
if budget < 10: print("::warning title=MLS::richieste non disponibili ora"); sys.exit(0)
out = []
for k in (0, 1, 3):
    d = (datetime.date.today() + datetime.timedelta(days=k)).isoformat()
    F = [f for f in get("fixtures", league=253, season=2026, date=d).get("response", [])]
    out.append(f"{d}: {len(F)} partite MLS ({', '.join(f['teams']['home']['name'] + '-' + f['teams']['away']['name'] + ' ' + f['fixture']['status']['short'] for f in F[:4])})")
    for f in F[:1]:
        O = get("odds", fixture=f["fixture"]["id"]).get("response", [])
        bk = [b["name"] for e in O for b in e.get("bookmakers", [])]
        x = next((b for e in O for b in e.get("bookmakers", []) if b["name"] == "1xBet"), None)
        out.append(f"  quote {f['teams']['home']['name']}-{f['teams']['away']['name']}: {len(bk)} bookmaker {bk[:12]} · 1xBet: {'sì, ' + str(len(x['bets'])) + ' mercati' if x else 'no'}")
O = get("odds", league=253, season=2026, page=1)
print("::notice title=MLS quote per campionato::" + f"risultati {O.get('results')} pagine {(O.get('paging') or {}).get('total')} errori {O.get('errors')}")
for l in out: print("::notice title=MLS::" + l)
