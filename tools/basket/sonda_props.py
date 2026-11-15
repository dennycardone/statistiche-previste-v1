"""Basket · sonda giocatori e mercati (15/11/2026, Denny: modulo Giocatori e Lettura arricchita).
Cosa passa API-Basketball: (1) voci esatte di /games/statistics/players e /teams su una partita finita di NBA, Eurolega, Serie A;
(2) elenco di tutti i tipi di scommessa (/odds/bets); (3) per una partita in programma di NBA, Eurolega e Serie A, quali book e quali
mercati (nomi, mai quote salvate). ~12 richieste sul limite del basket. Nessun dato salvato."""
import json, os, urllib.request, urllib.parse, datetime, collections
KEY = os.environ["APIFOOTBALL_KEY"].strip(); BASE = "https://v1.basketball.api-sports.io/"; used = 0
def get(p, **q):
    global used; used += 1
    req = urllib.request.Request(BASE + p + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
def note(t, m):
    for i in range(0, len(m), 3800): print(f"::notice title=Basket sonda · {t}{' (seg.)' if i else ''}::{m[i:i+3800]}")
st = (get("status").get("response") or {}).get("requests") or {}
note("budget", f"richieste oggi {st.get('current')} su {st.get('limit_day')}")
B = get("odds/bets").get("response") or []
note("tipi di scommessa", f"{len(B)} tipi: " + " | ".join(f"{b['id']} {b['name']}" for b in B))
LG = {"NBA": (12, "2026-2027"), "EL": (120, "2026"), "ITA": (52, "2026-2027")}
today = datetime.datetime.now(datetime.timezone.utc).date()
for cod, (lid, ss) in LG.items():
    G = get("games", league=lid, season=ss).get("response") or []
    fin = [g for g in G if (g.get("status") or {}).get("short") in ("FT", "AOT")]
    nxt = sorted([g for g in G if (g.get("status") or {}).get("short") == "NS" and g["date"][:10] >= str(today)], key=lambda g: g["date"])
    if fin:
        g = fin[-1]; P = get("games/statistics/players", id=g["id"]).get("response") or []
        if P: note(f"{cod} giocatore (voci)", json.dumps(P[0], ensure_ascii=False)[:1500])
        T = get("games/statistics/teams", id=g["id"]).get("response") or []
        if T: note(f"{cod} squadra (voci)", json.dumps(T[0], ensure_ascii=False)[:1500])
    for g in nxt[:1]:
        O = get("odds", game=g["id"]).get("response") or []
        books = collections.OrderedDict()
        for o in O:
            for bk in o.get("bookmakers") or []:
                books[bk["name"]] = [b["name"] for b in bk.get("bets") or []]
        allb = collections.Counter(n for v in books.values() for n in v)
        note(f"{cod} quote {g['date'][:10]} {g['teams']['home']['name']}–{g['teams']['away']['name']}",
             f"{len(books)} book: " + ", ".join(f"{k} ({len(v)})" for k, v in books.items()) + " · mercati (quanti book): " + " | ".join(f"{n} ({c})" for n, c in allb.most_common()))
note("richieste usate", str(used))
