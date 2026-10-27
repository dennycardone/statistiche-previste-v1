"""Diagnosi (27/10/2026): quali bookmaker passa API-Football e con quali mercati delle statistiche, sulle partite di oggi e domani dei nostri
campionati. Stampa SOLO conteggi e nomi dei mercati, mai le quote. Richieste solo dalla riserva per le prove (tools/af_budget.py), al
massimo 40."""
import json, os, re, sys, datetime, urllib.request, urllib.parse, traceback, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.excepthook = lambda t, v, tb: print("::error title=Diagnosi bookmaker::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
import af_budget
KEY = os.environ["APIFOOTBALL_KEY"].strip(); nreq = 0
def af(path, **q):
    global nreq; nreq += 1
    req = urllib.request.Request("https://v3.football.api-sports.io/" + path + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))
st = af_budget.requests_of(af("status")); free = af_budget.test_budget(st)
if free < 60: note("Diagnosi bookmaker", f"riserva insufficiente ({free})"); sys.exit(0)
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "update_data.py")).read()
m = re.search(r"AF_LEAGUES_X = \{(.*?)\}", src, re.S); IDS = {int(v): k for k, v in re.findall(r'"(\w+)": (\d+)', m.group(1))}
for k in re.findall(r'"(UCL|UEL|CZE)": \((\d+)', src): IDS[int(k[1])] = k[0]
rm = re.search(r"REMOVED = \{(.*?)\}", src); REM = set(re.findall(r'"(\w+)"', rm.group(1))) if rm else set()
IDS = {i: c for i, c in IDS.items() if c not in REM}
MK = {"corner 1X2": r"^corners 1x2$", "falli 1X2": r"^fouls\. 1x2$", "falli totali": r"^fouls\. total$", "tiri 1X2": r"^shots\.1x2$", "tiri in porta 1X2": r"^shotontarget 1x2$",
      "tiri totali": r"^total shots$", "tiri in porta totali": r"^total shotongoal$", "gialli 1X2": r"^yellow cards 1x2$", "cartellini O/U": r"^cards over/under$",
      "gialli O/U": r"^yellow over/under$", "fuorigioco 1X2": r"^offsides 1x2$", "corner O/U": r"^corners over under$"}
fx_tot, books = collections.Counter(), collections.defaultdict(collections.Counter); per_lg = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
nbets = collections.defaultdict(list)
today = datetime.date.today()
for k in (0, 1):
    d = str(today + datetime.timedelta(days=k)); page, pages = 1, 1
    while page <= pages and nreq < 40:
        O = af("odds", date=d, timezone="Europe/Rome", page=page); pages = (O.get("paging") or {}).get("total", 1) or 1; page += 1
        for e in O.get("response", []):
            lg = IDS.get(e["league"]["id"])
            if not lg: continue
            fx_tot[lg] += 1
            for b in e.get("bookmakers", []):
                names = [(bt.get("name") or "").lower() for bt in b.get("bets", [])]
                books[b["name"]]["partite"] += 1; nbets[b["name"]].append(len(names))
                for lab, rx in MK.items():
                    if any(re.match(rx, n) for n in names): books[b["name"]][lab] += 1; per_lg[b["name"]][lg][lab] += 1
N = sum(fx_tot.values())
note("Diagnosi bookmaker · partite", f"oggi e domani, nostri campionati: {N} partite con quote ({nreq} richieste) · per campionato: " + ", ".join(f"{lg} {n}" for lg, n in fx_tot.most_common()))
for bk in sorted(books, key=lambda b: -books[b]["partite"]):
    c = books[bk]; avg = sum(nbets[bk]) / len(nbets[bk]) if nbets[bk] else 0
    note(f"Diagnosi bookmaker · {bk}", f"partite {c['partite']} su {N} · mercati per partita in media {avg:.0f} · " + ", ".join(f"{lab} {c[lab]}" for lab in MK if c[lab]))
for bk in ("Bet365", "1xBet"):
    if bk in per_lg:
        note(f"Diagnosi bookmaker · {bk} per campionato", " ‖ ".join(f"{lg} ({fx_tot[lg]}): " + ", ".join(f"{lab} {n}" for lab, n in per_lg[bk][lg].items()) for lg in sorted(per_lg[bk])))
