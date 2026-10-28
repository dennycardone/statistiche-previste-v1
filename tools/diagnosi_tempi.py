"""Diagnosi (28/10/2026): cosa dà API-Football sul 1° tempo. Solo nomi e conteggi, nessun dato salvato. Richieste dalla riserva per le
prove (tools/af_budget.py): 1 status + 1 statistiche per tempo + 1 richiesta cumulativa di 2 partite.
  1) fixtures/statistics?half=true: quali statistiche ci sono nel 1° e nel 2° tempo (falli, fuorigioco, cartellini?)
  2) fixtures?ids=a-b (fino a 20 partite in una richiesta): ci sono eventi con il minuto (cartellini, gol) e il risultato del 1° tempo?"""
import json, os, sys, urllib.request, urllib.parse, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.excepthook = lambda t, v, tb: print("::error title=Diagnosi tempi::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
import af_budget
KEY = os.environ["APIFOOTBALL_KEY"].strip()
def af(path, **q):
    req = urllib.request.Request("https://v3.football.api-sports.io/" + path + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))
st = af_budget.requests_of(af("status")); free = af_budget.test_budget(st)
if free < 5: note("Diagnosi tempi", f"riserva insufficiente ({free})"); sys.exit(0)
AP = json.load(open("data/apif.json"))["partite"]
done = sorted(((v[0], fid, v[1]) for fid, v in AP.items() if v[9] == "FT" and v[1] in ("I1", "E0", "SP1")), reverse=True)[:2]
fid = done[0][1]
R = af("fixtures/statistics", fixture=fid, half="true").get("response", [])
if R:
    t = R[0]; parts = [k for k in t if k.startswith("statistics")]
    note("Diagnosi tempi · statistiche per tempo", f"partita {done[0][2]} {fid} · parti {parts} · " + " ‖ ".join(f"{k}: " + ", ".join(x['type'] for x in (t.get(k) or [])) for k in parts))
F = af("fixtures", ids="-".join(x[1] for x in done)).get("response", [])
for f in F:
    ev = f.get("events") or []
    tipi = sorted({(e.get("type"), e.get("detail")) for e in ev}, key=str)
    note("Diagnosi tempi · richiesta cumulativa", f"partita {f['fixture']['id']} · chiavi {sorted(f)} · risultato 1° tempo {f.get('score', {}).get('halftime')} · eventi {len(ev)} "
         f"(con minuto {sum(1 for e in ev if (e.get('time') or {}).get('elapsed') is not None)}) · tipi {tipi[:12]} · statistiche {len(f.get('statistics') or [])} · giocatori {len(f.get('players') or [])}")
