"""Sonda basket (15/11/2026, Denny): la chiave di API-Football apre anche API-Basketball? Piano, limite giornaliero, campionati, storia,
statistiche di squadra e giocatori, quote. Usa SOLO il servizio basket (limite separato dal calcio): ~10 richieste. Nessun dato salvato."""
import json, os, urllib.request, urllib.parse, datetime
KEY = os.environ["APIFOOTBALL_KEY"].strip(); BASE = "https://v1.basketball.api-sports.io/"; used = 0
def get(p, **q):
    global used; used += 1
    req = urllib.request.Request(BASE + p + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
def note(t, m): print(f"::notice title=Basket · {t}::{m[:3800]}")
st = get("status"); r = st.get("response") or {}
if st.get("errors") or not r:
    note("accesso", f"la chiave NON apre il basket: {json.dumps(st.get('errors'))[:300]}"); raise SystemExit(0)
sub, req_ = r.get("subscription") or {}, r.get("requests") or {}
note("accesso", f"piano {sub.get('plan')} · attivo {sub.get('active')} · scadenza {sub.get('end')} · richieste oggi {req_.get('current')} su {req_.get('limit_day')}")
L = get("leagues").get("response") or []
note("campionati", f"{len(L)} campionati in totale")
want = {"NBA": "USA", "Euroleague": "Europe", "Lega A": "Italy", "ACB": "Spain", "Eurocup": "Europe", "LNB": "France", "BBL": "Germany"}
picked = []
for lg in L:
    nm, cn = lg.get("name"), (lg.get("country") or {}).get("name")
    if nm in want and want[nm] == cn:
        ss = lg.get("seasons") or []
        last = ss[-1] if ss else {}; cov = last.get("coverage") or {}
        ss = sorted(ss, key=lambda z: str(z.get("season"))); last = ss[-1] if ss else {}; cov = last.get("coverage") or {}
        picked.append((lg["id"], nm, cn, [s.get("season") for s in ss][:1] + [s.get("season") for s in ss][-1:], cov))
note("campionati principali", " | ".join(f"{i} {n} ({c}) stagioni {s[0]}→{s[-1]} · copertura ultima: {json.dumps(cov)[:220]}" for i, n, c, s, cov in picked))
nba = next((p for p in picked if p[1] == "NBA"), None)
if nba:
    season = "2026-2027"
    d_ = get("games", league=nba[0], season=season); G = d_.get("response") or []
    if d_.get("errors"): note("NBA errori", json.dumps(d_.get("errors"))[:300])
    fin = [g for g in G if (g.get("status") or {}).get("short") in ("FT", "AOT")]
    note("NBA partite", f"stagione {season}: {len(G)} in calendario, {len(fin)} finite")
    if fin:
        g = fin[-1]; gid = g["id"]
        ts = get("games/statistics/teams", id=gid).get("response") or []
        ps = get("games/statistics/players", id=gid).get("response") or []
        note("NBA statistiche", f"{g['teams']['home']['name']}–{g['teams']['away']['name']} {g['date'][:10]} · squadra: {', '.join(list((ts[0] if ts else {}).keys())[:20])} · giocatori: {len(ps)} righe, campi {', '.join(list((ps[0] if ps else {}).keys())[:20])}")
    up = [g for g in G if (g.get("status") or {}).get("short") == "NS"][:1]
    if up:
        od = get("odds", game=up[0]["id"]).get("response") or []
        bks = od[0].get("bookmakers", []) if od else []
        bets = sorted({b["name"] for bk in bks for b in bk.get("bets", [])})
        note("NBA quote", f"{up[0]['teams']['home']['name']}–{up[0]['teams']['away']['name']}: {len(bks)} bookmaker ({', '.join(bk['name'] for bk in bks[:12])}) · mercati {len(bets)}: {', '.join(bets[:40])}")
ita = next((p for p in picked if p[1] == "Lega A"), None)
if ita:
    d_ = get("games", league=ita[0], season="2026-2027"); G = d_.get("response") or []
    if d_.get("errors"): note("Serie A errori", json.dumps(d_.get("errors"))[:300])
    note("Serie A basket", f"stagione 2026-2027: {len(G)} partite in calendario, finite {sum(1 for g in G if (g.get('status') or {}).get('short') in ('FT','AOT'))}")
note("richieste", f"usate {used} (solo servizio basket)")
