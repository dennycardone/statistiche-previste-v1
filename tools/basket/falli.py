"""Basket · archivio falli di squadra (15/11/2026, Denny: "mi servono solo quelli di squadra").
API-Basketball dall'8/1/2026 non passa più falli e rimbalzi offensivi: si prendono da fonti gratuite, senza chiave.
  NBA: ESPN (scoreboard del giorno + riepilogo della partita: falli, rimbalzi offensivi).
  Eurolega / Eurocup: dati del sito ufficiale (live.euroleague.net/api/Boxscore: falli commessi, subiti, rimbalzi offensivi).
Abbinamento alle partite dell'archivio (ramo basket) con data (±1 giorno) e punteggio finale (+ controllo sui nomi in Europa).
Uso leggero: una richiesta al secondo, tetto di richieste per giro; le partite già fatte non si richiedono più.
Uso: python tools/basket/falli.py ARCHIVIO_BASKET CARTELLA_FALLI [MAX_RICHIESTE]
Formato <COD>_<stagione>.json: {"partite": {id_partita: {"h": [falli, rimb_off], "a": [...], "src": id_fonte}}, "fatte": [id fonte o data]}"""
import json, os, sys, time, glob, datetime, urllib.request, re, unicodedata
ARCH, OUT = sys.argv[1], sys.argv[2]
MAXR = int(sys.argv[3]) if len(sys.argv) > 3 else 2500
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (compatible; prevista/1.0)", "Accept": "application/json"}
used = 0
def get(url):
    global used
    for t in range(3):
        used += 1
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                time.sleep(1.0); return json.loads(r.read().decode("utf8", "ignore"))
        except urllib.error.HTTPError as e:
            time.sleep(1.0)
            if e.code in (404, 400): return None
        except Exception:
            time.sleep(5 * (t + 1))
    return None
def can(): return used < MAXR
def asc(s): return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
def tok(s): return {t for t in re.sub(r"[^a-z ]", " ", asc(s)).split() if len(t) >= 4}
def load_out(fn):
    return json.load(open(fn)) if os.path.exists(fn) else {"partite": {}, "fatte": []}
summary = []
for fn in sorted(glob.glob(os.path.join(ARCH, "*.json"))):
    D = json.load(open(fn)); lg, ss = D["lega"], D["stagione"]
    if lg not in ("NBA", "EL", "EC"): continue
    of = os.path.join(OUT, f"{lg}_{ss}.json"); O = load_out(of); fatte = set(map(str, O["fatte"]))
    games = {gid: v for gid, v in D["partite"].items() if v[1] in ("FT", "AOT") and v[4] and v[5] and v[4][5] is not None}
    todo = {gid for gid in games if gid not in O["partite"]}
    if not todo: summary.append(f"{lg} {ss}: completo ({len(O['partite'])})"); continue
    by_score = {}
    for gid, v in games.items(): by_score.setdefault((v[4][5], v[5][5]), []).append((gid, v))
    def match(ph, pa, day, names=None):
        for gid, v in by_score.get((ph, pa), []):
            d0 = datetime.date.fromisoformat(v[0][:10])
            if day and abs((d0 - day).days) > 1: continue
            if names:
                nh, na = D["squadre"].get(str(v[2]), ""), D["squadre"].get(str(v[3]), "")
                if not (tok(nh) & tok(names[0]) or tok(na) & tok(names[1])): continue
            return gid
        return None
    n0 = len(O["partite"])
    if lg == "NBA":
        days = sorted({games[g][0][:10] for g in todo})
        for d in days:
            if not can(): break
            for dd in (d, (datetime.date.fromisoformat(d) - datetime.timedelta(days=1)).isoformat()):   # data UTC contro data USA
                key = "d" + dd
                if key in fatte: continue
                J = get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={dd.replace('-', '')}")
                if J is None: continue
                for ev in J.get("events") or []:
                    if not can(): break
                    comp = (ev.get("competitions") or [{}])[0]; cs = comp.get("competitors") or []
                    if str(ev["id"]) in fatte or len(cs) != 2 or not (((ev.get("status") or {}).get("type") or {}).get("completed")): continue
                    h = next((c for c in cs if c.get("homeAway") == "home"), None); a = next((c for c in cs if c.get("homeAway") == "away"), None)
                    try: ph, pa = int(h["score"]), int(a["score"])
                    except Exception: continue
                    gid = match(ph, pa, datetime.date.fromisoformat(dd))
                    fatte.add(str(ev["id"]))
                    if not gid or gid in O["partite"]: continue
                    S = get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={ev['id']}")
                    if not S: continue
                    out = {}
                    for t in (S.get("boxscore") or {}).get("teams") or []:
                        st = {s.get("name"): s.get("displayValue") for s in t.get("statistics", [])}
                        side = "h" if t.get("homeAway") == "home" else "a"
                        try: out[side] = [int(st.get("fouls")), int(st.get("offensiveRebounds"))]
                        except Exception: pass
                    if "h" in out and "a" in out: out["src"] = "espn:" + str(ev["id"]); O["partite"][gid] = out
                if can(): fatte.add(key)
    else:
        code = ("E" if lg == "EL" else "U") + ss[:4]
        miss = 0; gc = 0
        while can() and miss < 15:
            gc += 1
            if f"g{gc}" in fatte: miss = 0; continue
            J = get(f"https://live.euroleague.net/api/Boxscore?gamecode={gc}&seasoncode={code}")
            st = (J or {}).get("Stats") or []
            if len(st) != 2: miss += 1; continue
            miss = 0
            try:
                th, ta = st[0]["totr"], st[1]["totr"]; ph, pa = int(th["Points"]), int(ta["Points"])
            except Exception: continue
            fatte.add(f"g{gc}")
            n0_, n1_ = st[0].get("Team", ""), st[1].get("Team", "")
            gid = match(ph, pa, None, (n0_, n1_)); sw = False
            if not gid: gid = match(pa, ph, None, (n1_, n0_)); sw = True   # se il primo del tabellino è la squadra in trasferta
            if gid and gid not in O["partite"]:
                x0, x1 = [th.get("FoulsCommited"), th.get("OffensiveRebounds")], [ta.get("FoulsCommited"), ta.get("OffensiveRebounds")]
                O["partite"][gid] = {"h": x1 if sw else x0, "a": x0 if sw else x1, "src": f"{code}:{gc}"}
    O["fatte"] = sorted(fatte); json.dump(O, open(of, "w"), separators=(",", ":"))
    summary.append(f"{lg} {ss}: {len(O['partite'])}/{len(games)} (+{len(O['partite']) - n0})")
    if not can(): break
print(f"::notice title=Basket · falli di squadra::richieste {used} · " + " · ".join(summary)[:3500])
