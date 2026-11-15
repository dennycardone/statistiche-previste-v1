"""Basket · sonda falli di squadra da fonti gratuite (15/11/2026, Denny: "mi servono solo quelli di squadra").
NBA: ESPN (scoreboard + summary). Eurolega/Eurocup: dati del sito ufficiale (live.euroleague.net / api-live.euroleague.net).
Poche richieste, niente API-Football/API-Basketball. Stampa stato, voci che parlano di falli e quanto indietro arriva lo storico. Nessun dato salvato."""
import json, urllib.request, datetime, re
UA = {"User-Agent": "Mozilla/5.0 (compatible; prevista-sonda/1.0)", "Accept": "application/json"}
def get(url, ua=True):
    try:
        req = urllib.request.Request(url, headers=UA if ua else {})
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, r.read().decode("utf8", "ignore")
    except urllib.error.HTTPError as e: return e.code, ""
    except Exception as e: return str(e)[:80], ""
def note(t, m): print(f"::notice title=Falli · {t}::{m[:3800]}")
def find_fouls(obj, path="", out=None):
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if re.search(r"foul|^pf$|^fc$|^fd$|personal", str(k), re.I) or (isinstance(v, str) and re.search(r"foul", v, re.I) and len(v) < 40): out.append(f"{p}={json.dumps(v)[:60]}")
            find_fouls(v, p, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:3]): find_fouls(v, f"{path}[{i}]", out)
    return out
# ---- NBA da ESPN ----
for day in ("20261114", "20231115", "20191115"):
    st, body = get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={day}")
    ev = (json.loads(body).get("events") or []) if body else []
    note(f"ESPN NBA scoreboard {day}", f"stato {st} · partite {len(ev)}")
    if ev:
        eid = ev[0]["id"]; st2, b2 = get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={eid}")
        if b2:
            J = json.loads(b2); T = (J.get("boxscore") or {}).get("teams") or []
            stats = [(t.get("team", {}).get("abbreviation"), {s.get("name") or s.get("label"): s.get("displayValue") for s in t.get("statistics", [])}) for t in T]
            note(f"ESPN NBA summary {day}", f"stato {st2} · " + " | ".join(f"{a}: " + ", ".join(f"{k}={v}" for k, v in s.items() if re.search(r"foul|turnover|rebound", str(k), re.I)) for a, s in stats))
        else: note(f"ESPN NBA summary {day}", f"stato {st2}")
# ---- Eurolega / Eurocup ----
cands = [("live Boxscore E2025 g1", "https://live.euroleague.net/api/Boxscore?gamecode=1&seasoncode=E2025"),
         ("live Boxscore E2026 g1", "https://live.euroleague.net/api/Boxscore?gamecode=1&seasoncode=E2026"),
         ("live Boxscore E2019 g1", "https://live.euroleague.net/api/Boxscore?gamecode=1&seasoncode=E2019"),
         ("live Boxscore U2026 g1", "https://live.euroleague.net/api/Boxscore?gamecode=1&seasoncode=U2026"),
         ("api-live v1 games E2026", "https://api-live.euroleague.net/v1/games?seasonCode=E2026&gameCode=1"),
         ("api-live v2 stats E2026", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games/1/stats"),
         ("api-live v2 games E2026", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games")]
for lab, url in cands:
    st, body = get(url)
    info = f"stato {st} · {len(body)} caratteri"
    if body:
        try:
            J = json.loads(body); f = find_fouls(J)
            info += " · chiavi " + ", ".join(list(J)[:12] if isinstance(J, dict) else [f"lista di {len(J)}"]) + " · falli: " + "; ".join(f[:10])
        except Exception: info += " · non JSON: " + body[:150].replace("\n", " ")
    note(f"Euroleague {lab}", info)
