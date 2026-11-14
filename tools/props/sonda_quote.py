"""Player props · punto 2 (14/11/2026, Denny): API-Football passa mercati sui giocatori? Solo nomi dei mercati, bookmaker e numero di
giocatori quotati, mai le quote. Prende le prossime partite di Serie A, Premier, Liga, Bundesliga, Ligue 1 e Champions e il catalogo
dei mercati (odds/bets). Usa solo richieste fuori dalla riserva dell'app (af_budget), al massimo ~16."""
import json, os, sys, urllib.request, urllib.parse, collections, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..")); import af_budget
KEY = os.environ["APIFOOTBALL_KEY"].strip(); used = 0
def get(p, **q):
    global used; used += 1
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
B = af_budget.test_budget(af_budget.requests_of(get("status")))
print(f"::notice title=Props · budget::richieste per le prove adesso: {B}")
if B < 16: print("::warning title=Props::budget insufficiente, riprovare più tardi"); sys.exit(0)
PL = re.compile(r"player|scorer|booked|card.*player|shots.*player|anytime|first goal|last goal|assist", re.I)
cat = get("odds/bets").get("response") or []
pm = [b for b in cat if PL.search(b.get("name") or "")]
print(f"::notice title=Props · catalogo::{len(cat)} mercati nel catalogo; sui giocatori {len(pm)}: " + " | ".join(f"{b['id']} {b['name']}" for b in pm)[:3500])
LG = {"Serie A": 135, "Premier League": 39, "La Liga": 140, "Bundesliga": 78, "Ligue 1": 61, "Champions League": 2}
tot = collections.defaultdict(set); nfx = 0
for name, lid in LG.items():
    fx = (get("fixtures", league=lid, season=2026, next=2).get("response") or [])[:1]
    for f in fx:
        fid = f["fixture"]["id"]; lab = f"{name}: {f['teams']['home']['name']}–{f['teams']['away']['name']} {f['fixture']['date'][:10]}"
        page, seen = 1, collections.defaultdict(lambda: collections.defaultdict(set))
        while True:
            d = get("odds", fixture=fid, page=page)
            for r in d.get("response") or []:
                for bk in r.get("bookmakers") or []:
                    for bet in bk.get("bets") or []:
                        if PL.search(bet.get("name") or ""):
                            for v in bet.get("values") or []: seen[bet["name"]][bk["name"]].add(str(v.get("value"))[:40])
            pg = d.get("paging") or {}
            if page >= int(pg.get("total") or 1) or page >= 3: break
            page += 1
        nfx += 1
        if not seen: print(f"::notice title=Props · {name}::{lab} · nessun mercato giocatore"); continue
        txt = " | ".join(f"{m}: " + ", ".join(f"{b} ({len(vs)} voci)" for b, vs in sorted(bk_.items())) for m, bk_ in sorted(seen.items()))
        ex = next(iter(next(iter(seen.values())).values()))
        print(f"::notice title=Props · {name}::{lab} · {txt[:3000]} · esempio voci: {', '.join(sorted(ex)[:6])}")
        for m, bk_ in seen.items():
            for b in bk_: tot[m].add(b)
print(f"::notice title=Props · riepilogo::{nfx} partite · " + (" | ".join(f"{m}: {', '.join(sorted(b))}" for m, b in sorted(tot.items())) or "nessun mercato giocatore") + f" · richieste usate {used}")
