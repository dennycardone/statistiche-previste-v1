"""Scarica da football-data.co.uk i CSV dei campionati della dashboard nella cartella data/.
Campionati europei: stagione corrente sempre, le 5 precedenti solo se mancano (servono per gli H2H).
"""
import datetime, json, os, urllib.request

LEAGUES = ["I1", "I2", "E0", "SP1", "F1", "D1", "N1", "P1",
           "E1", "E2", "E3", "EC", "SC0", "SC1", "SC2", "SC3", "D2", "F2", "SP2", "B1", "T1", "G1"]
# campionati "extra" di football-data.co.uk (un file con tutte le stagioni, solo risultati e quote)
NEW_LEAGUES = ["ARG", "AUT", "BRA", "CHN", "DNK", "FIN", "IRL", "JPN", "MEX", "NOR", "POL", "ROU", "RUS", "SWE", "SWZ", "USA"]
BASE = "https://www.football-data.co.uk/mmz4281/{code}/{lg}.csv"
NEW = "https://www.football-data.co.uk/new/{lg}.csv"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)


def code(y):
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "statistiche-previste/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8-sig", errors="replace")


def save(name, txt):
    open(os.path.join(OUT, name), "w", encoding="utf-8").write(txt)


today = datetime.date.today()
cur = today.year if today.month >= 7 else today.year - 1
files = []

for lg in LEAGUES:
    for y in range(cur, cur - 6, -1):
        name = f"{lg}_{code(y)}.csv"
        path = os.path.join(OUT, name)
        if y == cur or not os.path.exists(path):
            try:
                txt = get(BASE.format(code=code(y), lg=lg))
                if "HomeTeam" in txt:
                    save(name, txt)
            except Exception as e:
                print("skip", name, e)
        if os.path.exists(path):
            files.append(name)

import csv, io, collections
for lg in NEW_LEAGUES:
    name = f"{lg}.csv"
    try:
        txt = get(NEW.format(lg=lg))
        if "Home" in txt:
            rd = list(csv.reader(io.StringIO(txt)))
            hdr, body = rd[0], [r for r in rd[1:] if r]
            iS = hdr.index("Season") if "Season" in hdr else -1
            keep = []
            for r in body:
                try: y = int(str(r[iS]).strip()[:4]) if iS >= 0 else None
                except Exception: y = None
                if y is None or y >= today.year - 6:        # ultime stagioni, come per gli altri campionati
                    r[0] = lg                                # colonna Country = codice del campionato (l'app lo riconosce)
                    keep.append(r)
            buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows([hdr] + keep)
            save(name, buf.getvalue())
    except Exception as e:
        print("skip", name, e)
    if os.path.exists(os.path.join(OUT, name)):
        files.append(name)

# API-Football a pagamento? Se sì è la fonte principale per TUTTO: calendario, risultati, statistiche, arbitri e cartellini.
# Verifica su fonti indipendenti (sito LaLiga, FBref, FotMob…, 12 partite dove i due fornitori differivano): API-Football giusto
# ~26 volte, football-data 3 (football-data conta meno tiri e ha scambiato partite). football-data resta solo dove il dato di
# API-Football è impossibile (es. falli 23-0) o manca, e per le quote storiche; ESPN come riserva del calendario.
AF_PRO = False
if os.environ.get("APIFOOTBALL_KEY", "").strip():
    try:
        _rq = urllib.request.Request("https://v3.football.api-sports.io/status", headers={"x-apisports-key": os.environ["APIFOOTBALL_KEY"].strip()})
        with urllib.request.urlopen(_rq, timeout=30) as _r:
            AF_PRO = int(json.loads(_r.read().decode()).get("response", {}).get("requests", {}).get("limit_day", 100)) > 100
    except Exception as e:
        print("API-Football non raggiungibile:", e)
print("API-Football a pagamento:", AF_PRO)
QUAL = {}   # controllo qualità dei dati di questo giro → data/qualita.json (mostrato nell'app)

# prossime giornate: calendario completo da fixturedownload.com (gratuito, senza chiave).
# I nomi delle squadre vengono convertiti in quelli usati da football-data.co.uk.
FD_SLUGS = {"I1": "serie-a", "E0": "epl", "SP1": "la-liga", "F1": "ligue-1", "D1": "bundesliga", "N1": "eredivisie", "P1": "primeira-liga",
            "E1": "championship", "E2": "efl-league-one", "E3": "efl-league-two", "T1": "super-lig", "USA": "mls"}
CAL_YEAR = {"USA"}   # campionati con stagione per anno solare: il file del calendario ha l'anno in corso
ALIAS = {
    "I1": {"Internazionale": "Inter"},
    "E0": {"Man Utd": "Man United", "Spurs": "Tottenham"},
    "SP1": {"Atlético de Madrid": "Ath Madrid", "Athletic Club": "Ath Bilbao", "CA Osasuna": "Osasuna", "Deportivo Alavés": "Alaves",
            "Elche CF": "Elche", "FC Barcelona": "Barcelona", "Getafe CF": "Getafe", "Levante UD": "Levante", "Málaga CF": "Malaga",
            "R. Racing Club": "Santander", "Rayo Vallecano": "Vallecano", "RC Deportivo": "La Coruna", "RCD Espanyol de Barcelona": "Espanol",
            "Real Betis": "Betis", "Real Sociedad": "Sociedad", "Sevilla FC": "Sevilla", "Valencia CF": "Valencia", "Villarreal CF": "Villarreal",
            "RCD Mallorca": "Mallorca", "Girona FC": "Girona", "UD Las Palmas": "Las Palmas", "Real Valladolid CF": "Valladolid", "RC Celta": "Celta",
            "Real Oviedo": "Oviedo", "SD Eibar": "Eibar", "CD Leganés": "Leganes"},
    "D1": {"FC Bayern München": "Bayern Munich", "VfB Stuttgart": "Stuttgart", "SV Elversberg": "Elversberg", "1. FC Köln": "FC Koln",
           "1. FC Union Berlin": "Union Berlin", "1. FSV Mainz 05": "Mainz", "FC Augsburg": "Augsburg", "Sport-Club Freiburg": "Freiburg",
           "TSG Hoffenheim": "Hoffenheim", "Borussia Dortmund": "Dortmund", "Bayer 04 Leverkusen": "Leverkusen", "SV Werder Bremen": "Werder Bremen",
           "Hamburger SV": "Hamburg", "Borussia Mönchengladbach": "M'gladbach", "Eintracht Frankfurt": "Ein Frankfurt", "FC Schalke 04": "Schalke 04",
           "SC Paderborn 07": "Paderborn", "VfL Wolfsburg": "Wolfsburg", "1. FC Heidenheim 1846": "Heidenheim", "FC St. Pauli": "St Pauli", "VfL Bochum 1848": "Bochum"},
    "F1": {"Olympique de Marseille": "Marseille", "RC Strasbourg Alsace": "Strasbourg", "RC Lens": "Lens", "AJ Auxerre": "Auxerre", "Le Mans FC": "Le Mans",
           "Stade Brestois 29": "Brest", "OGC Nice": "Nice", "Toulouse FC": "Toulouse", "Estac Troyes": "Troyes", "Angers SCO": "Angers",
           "Havre Athletic Club": "Le Havre", "LOSC Lille": "Lille", "Stade Rennais FC": "Rennes", "FC Lorient": "Lorient", "Olympique Lyonnais": "Lyon",
           "AS Monaco": "Monaco", "Paris Saint-Germain": "Paris SG", "FC Nantes": "Nantes", "FC Metz": "Metz", "AS Saint-Étienne": "St Etienne"},
    "N1": {"SC Cambuur": "Cambuur", "N.E.C. Nijmegen": "Nijmegen", "PSV": "PSV Eindhoven", "AZ": "AZ Alkmaar", "PEC Zwolle": "Zwolle", "FC Groningen": "Groningen",
           "sc Heerenveen": "Heerenveen", "FC Utrecht": "Utrecht", "Excelsior Rotterdam": "Excelsior", "ADO Den Haag": "Den Haag", "Fortuna Sittard": "For Sittard",
           "FC Twente": "Twente", "NAC Breda": "NAC Breda", "Heracles Almelo": "Heracles", "FC Volendam": "Volendam"},
    "P1": {"Académico": "Academico Viseu", "Casa Pia AC": "Casa Pia", "CD Nacional": "Nacional", "Estoril Praia": "Estoril", "Estrela Amadora": "Estrela",
           "FC Alverca": "Alverca", "FC Arouca": "Arouca", "FC Famalicão": "Famalicao", "FC Porto": "Porto", "Gil Vicente FC": "Gil Vicente",
           "Marítimo M.": "Maritimo", "Moreirense FC": "Moreirense", "Rio Ave FC": "Rio Ave", "SC Braga": "Sp Braga", "SL Benfica": "Benfica",
           "Sporting CP": "Sp Lisbon", "Vitória SC": "Guimaraes"},
}
try:
    from zoneinfo import ZoneInfo
    ROME = ZoneInfo("Europe/Rome")
except Exception:
    ROME = datetime.timezone(datetime.timedelta(hours=2))
import difflib, unicodedata as _ud, re as _re
def _norm(x):
    x = _ud.normalize("NFKD", x).encode("ascii", "ignore").decode().lower().replace("'", "")
    x = _re.sub(r"[^a-z0-9 ]", " ", x)
    stop = {"fc", "afc", "cf", "sc", "ac", "fk", "sk", "the", "club", "de", "calcio", "cd", "ud", "rc", "sd", "ca", "ss", "as", "us", "1", "sv", "vfl", "vfb", "tsg", "fsv"}
    return " ".join(w for w in x.split() if w not in stop)
def fd_teams(lg):
    names = set()
    for f in files:
        if not (f.startswith(lg + "_") or f == lg + ".csv"): continue
        try:
            rd = list(csv.reader(io.StringIO(open(os.path.join(OUT, f), encoding="utf-8").read())))
            h = rd[0]; ih = h.index("HomeTeam") if "HomeTeam" in h else h.index("Home"); ia = h.index("AwayTeam") if "AwayTeam" in h else h.index("Away")
            for r in rd[1:]:
                if len(r) > max(ih, ia): names.update([r[ih].strip(), r[ia].strip()])
        except Exception: pass
    names.discard(""); return names
FIX_ALIAS = {"Sheffield Wednesday": "Sheffield Weds", "Queens Park Rangers": "QPR", "West Bromwich Albion": "West Brom", "Wolverhampton Wanderers": "Wolves",
             "Nottingham Forest": "Nott'm Forest", "Milton Keynes Dons": "MK Dons", "Peterborough United": "Peterboro", "Oxford United": "Oxford",
             "Manchester City": "Man City", "Manchester United": "Man United", "Sheffield United": "Sheffield United", "Newcastle United": "Newcastle"}
def to_fd(lg, name, pool):
    if name in pool: return name
    a = ALIAS.get(lg, {}).get(name) or FIX_ALIAS.get(name)
    if a: return a
    n = _norm(name); byn = {_norm(t): t for t in pool}
    if n in byn: return byn[n]
    cand = [t for k, t in byn.items() if k and (k in n or n in k)]
    if len(cand) == 1: return cand[0]
    m = difflib.get_close_matches(n, list(byn), n=1, cutoff=0.6)
    return byn[m[0]] if m else None
rows = ["Div,Date,Time,HomeTeam,AwayTeam,Round"]
unknown = set()
for lg, slug in FD_SLUGS.items():
    pool = fd_teams(lg)
    try:
        data = json.loads(get(f"https://fixturedownload.com/feed/json/{slug}-{today.year if lg in CAL_YEAR else cur}"))
    except Exception as e:
        print("skip calendario", lg, e)
        continue
    for m in data:
        if m.get("HomeTeamScore") is not None:
            continue
        try:
            dt = datetime.datetime.strptime(m["DateUtc"], "%Y-%m-%d %H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        except Exception:
            continue
        loc = dt.astimezone(ROME)
        # 00:00Z o 23:00Z = solo data, orario non ancora ufficiale
        tm = "" if dt.strftime("%H:%M") in ("00:00", "23:00") else loc.strftime("%H:%M")
        h = to_fd(lg, m["HomeTeam"], pool); a = to_fd(lg, m["AwayTeam"], pool)
        if h is None: unknown.add((lg, m["HomeTeam"])); h = m["HomeTeam"]
        if a is None: unknown.add((lg, m["AwayTeam"])); a = m["AwayTeam"]
        rows.append(",".join([lg, loc.strftime("%d/%m/%Y"), tm, h.replace(",", " "), a.replace(",", " "), str(m.get("RoundNumber", ""))]))
save("next_fixtures.csv", "\n".join(rows))
files.append("next_fixtures.csv")

# Calendario degli altri campionati: ESPN (gratuito, senza chiave; interfaccia pubblica ma non ufficiale).
# Solo i campionati che ESPN tiene aggiornati (verificato a ottobre 2026). Una richiesta per giorno e campionato,
# prossimi 14 giorni; si riscarica ogni 3 ore (negli altri giri resta il file precedente). Partite già giocate, rinviate
# o con una squadra non riconosciuta vengono scartate: mai abbinamenti incerti.
ESPN = {"I2": "ita.2", "SC0": "sco.1", "SC1": "sco.2", "D2": "ger.2", "F2": "fra.2", "SP2": "esp.2", "B1": "bel.1", "G1": "gre.1",
        "EC": "eng.5", "ARG": "arg.1", "AUT": "aut.1", "BRA": "bra.1", "CHN": "chn.1", "DNK": "den.1", "JPN": "jpn.1", "MEX": "mex.1",
        "NOR": "nor.1", "RUS": "rus.1", "SWE": "swe.1"}
ESPN_ALIAS = {"DNK": {"AGF": "Aarhus", "F.C. København": "FC Copenhagen"}, "NOR": {"Hamarkameratene": "HamKam"}, "RUS": {"Nizhny Novgorod": "Pari NN"},
              "USA": {"LAFC": "Los Angeles FC", "Red Bull New York": "New York Red Bulls"},
              "SP1": {"Deportivo": "La Coruna"}, "D1": {"FC Cologne": "FC Koln"}, "T1": {"Istanbul Basaksehir": "Buyuksehyr"}}
import time
def espn_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (statistiche-previste)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")
def cur_teams(lg):   # squadre della stagione in corso nei nostri file (se il file è vuoto: tutte)
    fs = sorted(f for f in files if f.startswith(lg + "_"))
    try:
        if fs:
            rd = list(csv.reader(io.StringIO(open(os.path.join(OUT, fs[-1]), encoding="utf-8").read()))); h = rd[0]
            ih, ia = h.index("HomeTeam"), h.index("AwayTeam"); P = {x.strip() for r in rd[1:] if len(r) > ia for x in (r[ih], r[ia])}
        else:
            rd = list(csv.reader(io.StringIO(open(os.path.join(OUT, lg + ".csv"), encoding="utf-8").read()))); h = rd[0]
            iS, ih, ia = h.index("Season"), h.index("Home"), h.index("Away"); ss = max(r[iS] for r in rd[1:] if len(r) > iS)
            P = {x.strip() for r in rd[1:] if len(r) > ia and r[iS] == ss for x in (r[ih], r[ia])}
        P.discard("")
        return P or fd_teams(lg)
    except Exception:
        return fd_teams(lg)
def espn_match(lg, names, pool):
    names = [n for n in names if n]
    for n in names:
        a = ESPN_ALIAS.get(lg, {}).get(n)
        if a and a in pool: return a
    byn = {_norm(t): t for t in pool}
    for n in names:
        if n in pool: return n
        if _norm(n) in byn: return byn[_norm(n)]
    for n in names:
        k = _norm(n); cand = [t for kk, t in byn.items() if kk and k and (kk in k or k in kk)]
        if len(cand) == 1: return cand[0]
    for n in names[:3]:
        m = difflib.get_close_matches(_norm(n), list(byn), n=1, cutoff=0.6)
        if m: return byn[m[0]]
    return None
espn_path = os.path.join(OUT, "espn_fixtures.csv")
espn_old = os.path.exists(espn_path)
if not espn_old or datetime.datetime.utcnow().hour % 3 == 2 or os.environ.get("ESPN_FORCE"):
    erows, check = ["Div,Date,Time,HomeTeam,AwayTeam,Round"], {}
    for lg, code_ in ESPN.items():
        pool, seen, maps, evs = cur_teams(lg), set(), {}, []
        for k in range(14):
            d = today + datetime.timedelta(days=k)
            try:
                evs += json.loads(espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code_}/scoreboard?dates={d:%Y%m%d}")).get("events", [])
            except Exception as e:
                print("ESPN", lg, d, e)
            time.sleep(0.2)
        out_lg, bad = [], set()
        for ev in evs:
            try:
                comp = ev["competitions"][0]; st = ev.get("status", {}).get("type", {})
                if st.get("completed") or st.get("name") in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_ABANDONED"): continue
                side = {c["homeAway"]: c["team"] for c in comp["competitors"]}
                tm = {}
                for hw in ("home", "away"):
                    t = side[hw]; nm = [t.get("displayName"), t.get("shortDisplayName"), t.get("name"), t.get("abbreviation"), t.get("location")]
                    tm[hw] = espn_match(lg, nm, pool)
                    if tm[hw] is None: bad.add(nm[0])
                    else: maps.setdefault(tm[hw], set()).add(nm[0])
                if None in tm.values(): continue
                dt = datetime.datetime.strptime(ev["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=datetime.timezone.utc).astimezone(ROME)
                out_lg.append((tm["home"], tm["away"], dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M") if comp.get("timeValid", True) else ""))
            except Exception as e:
                print("ESPN evento", lg, e)
        dup = {t for t, v in maps.items() if len(v) > 1}   # due squadre ESPN sulla stessa nostra: scarto quelle partite
        for h, a, dd, tt in out_lg:
            if h in dup or a in dup or (h, a, dd) in seen: continue
            seen.add((h, a, dd)); erows.append(",".join([lg, dd, tt, h.replace(",", " "), a.replace(",", " "), ""]))
        check[lg] = {"partite": len(seen), "non_riconosciute": sorted(bad), "doppi": sorted(dup)}
    save("espn_fixtures.csv", "\n".join(erows))
    json.dump({"aggiornato": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), "campionati": check}, open(os.path.join(OUT, "espn_check.json"), "w"), indent=1, ensure_ascii=False)
if os.path.exists(espn_path): files.append("espn_fixtures.csv")   # con API-Football: solo per le partite che API-Football non ha (vedi sotto)

# Corner, falli, tiri e tiri in porta per i campionati che football-data dà solo con risultati: dalle statistiche partita di ESPN.
# Verificato (ottobre 2026) su 73 partite di Serie A e Premier: stessi numeri di football-data (stesso fornitore).
# Cache in data/espn_stats.json; a ogni giro al massimo ESPN_BUDGET partite nuove (il passato si riempie in pochi giri).
# Una partita riceve le statistiche solo se squadre, giorno (±1) e risultato coincidono con la riga di football-data.
ESPN_STATS = {"BRA": "bra.1", "ARG": "arg.1", "USA": "usa.1", "MEX": "mex.1", "JPN": "jpn.1", "CHN": "chn.1", "AUT": "aut.1",
              "DNK": "den.1", "NOR": "nor.1", "SWE": "swe.1", "RUS": "rus.1"}
ESPN_BUDGET = 2000
if AF_PRO: ESPN_STATS = {}   # statistiche e risultati di questi campionati da API-Football
STAT_COLS = ["HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC"]
cache_path = os.path.join(OUT, "espn_stats.json")
try: SC = json.load(open(cache_path))
except Exception: SC = {}
SC.setdefault("v", 1); SC.setdefault("months", {}); SC.setdefault("ev", {}); SC.setdefault("teams", {})
budget = ESPN_BUDGET
def _tn(t): return [t.get("displayName"), t.get("shortDisplayName"), t.get("name"), t.get("abbreviation"), t.get("location")]
for lg, code_ in ESPN_STATS.items():
    done = set(SC["months"].setdefault(lg, [])); EV = SC["ev"].setdefault(lg, {}); TM = SC["teams"].setdefault(lg, {})
    months, y, m = [], today.year - 5, 1
    while (y, m) <= (today.year, today.month):
        months.append(f"{y}{m:02d}"); m += 1
        if m > 12: y, m = y + 1, 1
    recent = set(months[-2:])
    for ym in reversed(months):   # dal più recente: i risultati nuovi hanno la precedenza sul recupero del passato
        if ym in done and ym not in recent: continue
        try:
            evs = json.loads(espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code_}/scoreboard?dates={ym}&limit=300")).get("events", [])
        except Exception as e:
            print("ESPN stats mese", lg, ym, e); continue
        time.sleep(0.2)
        ok = True
        for ev in evs:
            if not ev.get("status", {}).get("type", {}).get("completed"): continue
            eid = ev["id"]; old = EV.get(eid)
            if old and (old[5] is not None or ev["date"][:10] < str(today - datetime.timedelta(days=7))): continue
            if budget <= 0: ok = False; break
            budget -= 1
            try:
                sm = json.loads(espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code_}/summary?event={eid}"))
                comp = ev["competitions"][0]; side = {c["homeAway"]: c for c in comp["competitors"]}
                st = {t["team"]["id"]: {x["name"]: x.get("displayValue") for x in t.get("statistics", [])} for t in sm.get("boxscore", {}).get("teams", [])}
                H, A = st.get(side["home"]["team"]["id"], {}), st.get(side["away"]["team"]["id"], {})
                def num(d, k):
                    try: return int(float(d.get(k)))
                    except Exception: return None
                vals = [num(H, "totalShots"), num(A, "totalShots"), num(H, "shotsOnTarget"), num(A, "shotsOnTarget"),
                        num(H, "foulsCommitted"), num(A, "foulsCommitted"), num(H, "wonCorners"), num(A, "wonCorners")]
                if None in vals or sum(vals) == 0: vals = None   # statistiche mancanti (ESPN a volte mette tutti zeri)
                for hw in ("home", "away"): TM[side[hw]["team"]["id"]] = _tn(side[hw]["team"])
                EV[eid] = [ev["date"], side["home"]["team"]["id"], side["away"]["team"]["id"], int(float(side["home"].get("score", -1))),
                           int(float(side["away"].get("score", -1))), vals]
            except Exception as e:
                print("ESPN stats partita", lg, eid, e)
            time.sleep(0.2)
        if ok and ym not in recent: done.add(ym)
    SC["months"][lg] = sorted(done)
json.dump(SC, open(cache_path, "w"), separators=(",", ":"), ensure_ascii=False)
# unione con i file di football-data
espn_stats_check = {}
for lg in ESPN_STATS:
    path = os.path.join(OUT, f"{lg}.csv")
    if not os.path.exists(path): continue
    rd = list(csv.reader(io.StringIO(open(path, encoding="utf-8").read())))
    hdr, body = rd[0], rd[1:]
    if "HS" in hdr: continue
    iD, iH, iA, iG1, iG2 = hdr.index("Date"), hdr.index("Home"), hdr.index("Away"), hdr.index("HG"), hdr.index("AG")
    pool = {x for r in body if len(r) > iA for x in (r[iH].strip(), r[iA].strip())} - {""}
    TMl = SC["teams"].get(lg, {})
    def names_of(x): return x if isinstance(x, list) else TMl.get(x, [None])
    for e in SC["ev"].get(lg, {}).values():
        e[1], e[2] = names_of(e[1]), names_of(e[2])
    nmap, used = {}, {}
    for e in SC["ev"].get(lg, {}).values():
        for names in (e[1], e[2]):
            k = names[0]
            if not k: continue
            if k in nmap: continue
            t = espn_match(lg, names, pool); nmap[k] = t
            if t: used.setdefault(t, set()).add(k)
    dup = {t for t, v in used.items() if len(v) > 1}
    idx, allev = {}, []
    for e in SC["ev"].get(lg, {}).values():
        h, a = nmap.get(e[1][0]), nmap.get(e[2][0])
        if not h or not a or h in dup or a in dup or e[3] < 0 or e[4] < 0: continue
        dt = datetime.datetime.strptime(e[0], "%Y-%m-%dT%H:%MZ").replace(tzinfo=datetime.timezone.utc)
        allev.append((dt, h, a, e[3], e[4], e[5]))
        if e[5] is not None: idx.setdefault((h, a), []).append((dt.date(), e[3], e[4], e[5]))
    n_ok = 0
    out = [hdr + STAT_COLS]
    fd_dates, pairs = [], {}
    for r in body:
        add = [""] * 8
        try:
            d = datetime.datetime.strptime(r[iD].strip(), "%d/%m/%Y").date(); fd_dates.append(d)
            pairs.setdefault((r[iH].strip(), r[iA].strip()), []).append(d)
            for (ed, g1, g2, vals) in idx.get((r[iH].strip(), r[iA].strip()), []):
                if abs((ed - d).days) <= 1 and str(g1) == r[iG1].strip() and str(g2) == r[iG2].strip():
                    add = [str(v) for v in vals]; n_ok += 1; break
        except Exception:
            pass
        out.append(r + add)
    # partite giocate che football-data non ha ancora pubblicato: risultato (e statistiche) da ESPN.
    # Solo dopo l'ultima partita presente nel file di football-data e se la stessa sfida non c'è già entro 3 giorni.
    n_add = 0
    if fd_dates and body:
        last = max(fd_dates)
        iS, iT, iR = hdr.index("Season"), (hdr.index("Time") if "Time" in hdr else -1), (hdr.index("Res") if "Res" in hdr else -1)
        lastrow = max(body, key=lambda r: datetime.datetime.strptime(r[iD].strip(), "%d/%m/%Y").date() if r[iD].strip() else datetime.date.min)
        try: UK = ZoneInfo("Europe/London")
        except Exception: UK = datetime.timezone.utc
        for (dt, h, a, g1, g2, vals) in sorted(allev):
            loc = dt.astimezone(UK); d = loc.date()
            if d <= last or d > today: continue
            if any(abs((x - d).days) <= 3 for x in pairs.get((h, a), [])): continue
            r = [""] * len(hdr)
            r[0] = lg; r[1] = lastrow[1]; season = lastrow[iS]
            if season.strip().isdigit() and loc.year != int(season): season = str(loc.year)   # campionati per anno solare: nuova stagione
            r[iS] = season; r[iD] = loc.strftime("%d/%m/%Y")
            if iT >= 0: r[iT] = loc.strftime("%H:%M")
            r[iH], r[iA], r[iG1], r[iG2] = h, a, str(g1), str(g2)
            if iR >= 0: r[iR] = "H" if g1 > g2 else "A" if g2 > g1 else "D"
            out.append(r + ([str(v) for v in vals] if vals else [""] * 8)); pairs.setdefault((h, a), []).append(d); n_add += 1
    buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(out); save(f"{lg}.csv", buf.getvalue())
    espn_stats_check[lg] = {"partite_con_statistiche": n_ok, "partite_totali": len(body), "partite_aggiunte_da_espn": n_add, "squadre_doppie": sorted(dup),
                            "nomi_non_riconosciuti": sorted(k for k, v in nmap.items() if v is None)}
try:
    J = json.load(open(os.path.join(OUT, "espn_check.json")))
except Exception:
    J = {}
J["statistiche"] = espn_stats_check; J["statistiche_aggiornate"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
json.dump(J, open(os.path.join(OUT, "espn_check.json"), "w"), indent=1, ensure_ascii=False)
if unknown:
    print("Nomi non convertiti (verificare ALIAS se non coincidono con football-data):", sorted(unknown))

# Risultati del giorno per i campionati europei: football-data.co.uk li pubblica solo un paio di volte a settimana.
# Nel frattempo il risultato finale arriva da ESPN (solo gol: corner, falli, tiri e xG restano vuoti finché football-data
# non pubblica la sua riga, che poi prende il posto di quella di ESPN). Si aggiungono solo partite finite, giocate dopo
# l'ultima data presente nel file di football-data, con entrambe le squadre riconosciute e senza la stessa sfida entro 3 giorni.
# Cache in data/espn_results.json: un giorno già concluso da più di 2 giorni non si riscarica.
ESPN_RES = {"I1": "ita.1", "I2": "ita.2", "E0": "eng.1", "E1": "eng.2", "E2": "eng.3", "E3": "eng.4", "EC": "eng.5",
            "SP1": "esp.1", "SP2": "esp.2", "F1": "fra.1", "F2": "fra.2", "D1": "ger.1", "D2": "ger.2", "N1": "ned.1",   # (Scozia League One e Two: ESPN non le copre)
            "P1": "por.1", "SC0": "sco.1", "SC1": "sco.2", "B1": "bel.1", "T1": "tur.1", "G1": "gre.1"}
if AF_PRO: ESPN_RES = {}   # risultati del giorno da API-Football
res_path = os.path.join(OUT, "espn_results.json")
try: RC = json.load(open(res_path))
except Exception: RC = {}
if RC.get("v") != 1: RC = {"v": 1, "days": {}, "ev": {}}
try: UKZ = ZoneInfo("Europe/London")
except Exception: UKZ = datetime.timezone.utc
res_check = {}
for lg, code_ in ESPN_RES.items():
    name = f"{lg}_{code(cur)}.csv"; path = os.path.join(OUT, name)
    if not os.path.exists(path): continue
    try:
        rd = list(csv.reader(io.StringIO(open(path, encoding="utf-8").read())))
        hdr, body = rd[0], [r for r in rd[1:] if any(x.strip() for x in r)]
        iD, iH, iA = hdr.index("Date"), hdr.index("HomeTeam"), hdr.index("AwayTeam")
        iG1, iG2 = hdr.index("FTHG"), hdr.index("FTAG")
        iR = hdr.index("FTR") if "FTR" in hdr else -1; iT = hdr.index("Time") if "Time" in hdr else -1
    except Exception as e:
        print("risultati ESPN: file", name, e); continue
    def _d(x):
        x = x.strip()
        for f in ("%d/%m/%Y", "%d/%m/%y"):
            try: return datetime.datetime.strptime(x, f).date()
            except Exception: pass
        return None
    pairs, scores = {}, {}
    for r in body:
        if len(r) > iA and _d(r[iD]):
            pr = (r[iH].strip(), r[iA].strip()); pairs.setdefault(pr, []).append(_d(r[iD]))
            scores.setdefault(pr, []).append((_d(r[iD]), r[iG1].strip(), r[iG2].strip()))
    dates = [d for v in pairs.values() for d in v]
    last = max(dates) if dates else today - datetime.timedelta(days=21)
    start = today - datetime.timedelta(days=21)   # 3 settimane: servono anche partite già in football-data per confermare i nomi
    days = RC["days"].setdefault(lg, []); EVR = RC["ev"].setdefault(lg, {})
    d = start
    while d <= today:
        ds = d.strftime("%Y%m%d")
        if ds not in days or d >= today - datetime.timedelta(days=2):
            try:
                for ev in json.loads(espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code_}/scoreboard?dates={ds}")).get("events", []):
                    st = ev.get("status", {}).get("type", {})
                    if not st.get("completed") or st.get("name") in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_ABANDONED", "STATUS_SUSPENDED"): continue
                    comp = ev["competitions"][0]; side = {c["homeAway"]: c for c in comp["competitors"]}
                    EVR[ev["id"]] = [ev["date"], _tn(side["home"]["team"]), _tn(side["away"]["team"]),
                                     int(float(side["home"].get("score"))), int(float(side["away"].get("score")))]
                if ds not in days and d < today - datetime.timedelta(days=2): days.append(ds)
            except Exception as e:
                print("risultati ESPN", lg, ds, e)
            time.sleep(0.2)
        d += datetime.timedelta(days=1)
    # pulizia: solo le ultime 3 settimane
    lim = str(today - datetime.timedelta(days=21))
    for k in [k for k, v in EVR.items() if v[0][:10] < lim]: del EVR[k]
    RC["days"][lg] = sorted(x for x in days if x >= lim.replace("-", ""))
    pool = {t for pr in pairs for t in pr} or cur_teams(lg)
    def _m(names):
        for n in names:
            a_ = ALIAS.get(lg, {}).get(n) or FIX_ALIAS.get(n)
            if n in pool: return n
            if a_ in pool: return a_
        return espn_match(lg, names, pool)
    nmap, used, bad = {}, {}, set()
    for v in EVR.values():
        for names in (v[1], v[2]):
            k = names[0]
            if not k or k in nmap: continue
            t = _m(names); nmap[k] = t
            if t: used.setdefault(t, set()).add(k)
            else: bad.add(k)
    dup = {t for t, v in used.items() if len(v) > 1}
    evs_ = []
    for v in sorted(EVR.values(), key=lambda v: v[0]):
        loc = datetime.datetime.strptime(v[0], "%Y-%m-%dT%H:%MZ").replace(tzinfo=datetime.timezone.utc).astimezone(UKZ)
        evs_.append((loc, loc.date(), v[1][0], v[2][0], nmap.get(v[1][0]), nmap.get(v[2][0]), v[3], v[4]))
    # nome ESPN confermato = almeno una sua partita coincide con football-data (stesse squadre, giorno ±1, stesso risultato)
    ok_names = set()
    for loc, dd, kh, ka, h, a, g1, g2 in evs_:
        if h and a and any(abs((x - dd).days) <= 1 and s1 == str(g1) and s2 == str(g2) for x, s1, s2 in scores.get((h, a), [])):
            ok_names.update([kh, ka])
    add, unconf = [], set()
    for loc, dd, kh, ka, h, a, g1, g2 in evs_:
        v = [None, None, None, g1, g2]
        if not h or not a or h in dup or a in dup or h == a: continue
        if dd <= last or dd > today: continue
        if kh not in ok_names or ka not in ok_names: unconf.update(x for x in (kh, ka) if x not in ok_names); continue
        if any(abs((x - dd).days) <= 3 for x in pairs.get((h, a), [])): continue
        r = [""] * len(hdr)
        r[0] = lg; r[iD] = dd.strftime("%d/%m/%Y"); r[iH], r[iA], r[iG1], r[iG2] = h, a, str(v[3]), str(v[4])
        if iT >= 0: r[iT] = loc.strftime("%H:%M")
        if iR >= 0: r[iR] = "H" if v[3] > v[4] else "A" if v[4] > v[3] else "D"
        add.append(r); pairs.setdefault((h, a), []).append(dd)
    if add:
        buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows([hdr] + body + add); save(name, buf.getvalue())
    res_check[lg] = {"ultima_data_football_data": str(last), "risultati_aggiunti_da_espn": len(add),
                     "nomi_non_riconosciuti": sorted(bad), "nomi_non_confermati": sorted(unconf), "squadre_doppie": sorted(dup)}
json.dump(RC, open(res_path, "w"), separators=(",", ":"), ensure_ascii=False)
try: J = json.load(open(os.path.join(OUT, "espn_check.json")))
except Exception: J = {}
J["risultati"] = res_check; J["risultati_aggiornati"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
json.dump(J, open(os.path.join(OUT, "espn_check.json"), "w"), indent=1, ensure_ascii=False)

# calendario: solo i campionati della dashboard
try:
    fx = get("https://www.football-data.co.uk/fixtures.csv").splitlines()
    keep = [fx[0]] + [l for l in fx[1:] if l.split(",")[0] in LEAGUES]
    save("fixtures.csv", "\n".join(keep))
    files.append("fixtures.csv")
except Exception as e:
    print("skip fixtures", e)

# stemmi ufficiali: link alle immagini di football-data.org (serve il token gratuito, segreto FD_TOKEN su GitHub).
# Si aggiornano una volta a settimana. Serie B non è nel piano gratuito di football-data.org: niente stemmi.
import unicodedata, re, time
FD_COMP = {"I1": "SA", "E0": "PL", "SP1": "PD", "F1": "FL1", "D1": "BL1", "N1": "DED", "P1": "PPL"}
CREST_ALIAS = {  # nome football-data.co.uk -> parola chiave nel nome ufficiale
    "Inter": "internazionale", "Milan": "ac milan", "Man United": "manchester united", "Man City": "manchester city",
    "Nott'm Forest": "nottingham", "Wolves": "wolverhampton", "Newcastle": "newcastle", "Tottenham": "tottenham",
    "Ath Madrid": "atletico", "Ath Bilbao": "athletic", "Sociedad": "real sociedad", "Vallecano": "rayo", "Espanol": "espanyol",
    "Betis": "betis", "La Coruna": "coruna", "Santander": "racing", "Celta": "celta", "Alaves": "alaves",
    "Paris SG": "paris saint", "St Etienne": "etienne", "Ein Frankfurt": "eintracht frankfurt", "M'gladbach": "monchengladbach",
    "FC Koln": "koln", "Bayern Munich": "bayern", "Sp Lisbon": "sporting clube de portugal", "Sp Braga": "braga",
    "Guimaraes": "vitoria", "For Sittard": "fortuna", "PSV Eindhoven": "psv", "Verona": "verona", "Leverkusen": "leverkusen",
    "Rennes": "rennais", "Hamburg": "hamburger", "Nijmegen": "nec", "AZ Alkmaar": "az", "Academico Viseu": "viseu",
    "West Brom": "west bromwich", "Sheffield Weds": "sheffield wednesday", "Werder Bremen": "werder", "Union Berlin": "union berlin",
    "Espanol": "espanyol", "Estrela": "estrela", "Waalwijk": "rkc", "Go Ahead Eagles": "go ahead",
}
# nomi aggiunti a mano (nome football-data.co.uk -> link diretto allo stemma), se il riconoscimento automatico sbaglia
CREST_MANUAL = {}
def norm(x):
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower().replace("'", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", x)).strip()
crest_path = os.path.join(OUT, "crests.json")
token = os.environ.get("FD_TOKEN", "").strip()
old = {}
if os.path.exists(crest_path):
    try: old = json.load(open(crest_path))
    except Exception: old = {}
fresh = old.get("v") == 3 and old.get("updated") and (datetime.date.today() - datetime.date.fromisoformat(old["updated"])).days < 7
if token and not fresh:
    crests = {"v": 3, "updated": datetime.date.today().isoformat(), "teams": {}, "colors": {}}
    for lg, comp in FD_COMP.items():
        try:
            req = urllib.request.Request(f"https://api.football-data.org/v4/competitions/{comp}/teams", headers={"X-Auth-Token": token})
            api = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))["teams"]
        except Exception as e:
            print("skip stemmi", lg, e); continue
        time.sleep(7)   # piano gratuito: 10 richieste al minuto
        # squadre della stagione in corso nei CSV
        mine = set()
        cur_file = os.path.join(OUT, f"{lg}_{code(cur)}.csv")
        if os.path.exists(cur_file):
            for line in open(cur_file, encoding="utf-8").read().splitlines()[1:]:
                c = line.split(",")
                if len(c) > 4: mine.update([c[3] if ":" in c[2] else c[2], c[4] if ":" in c[2] else c[3]])
        mine.discard("")
        out = {}; cols = {}
        for t in sorted(mine):
            if t in CREST_MANUAL: out[t] = CREST_MANUAL[t]; continue
            key = norm(CREST_ALIAS.get(t, t)); best = None; part = []
            for a in api:
                names = [norm(a.get("shortName") or ""), norm(a.get("name") or ""), norm(a.get("tla") or "")]
                if key in names: best = a; break
                if any(re.search(r"\b" + re.escape(key) + r"\b", n) for n in names[:2]): part.append(a)
            if not best and part: best = min(part, key=lambda a: len(a.get("name") or ""))   # il nome più corto che contiene la parola
            if best and best.get("clubColors"): cols[t] = best["clubColors"]   # colori sociali, es. "Red / Black"
            if best and best.get("crest"): out[t] = best["crest"]
            else: print("STEMMA NON TROVATO:", lg, t, "| squadre disponibili:", ", ".join(a.get("shortName") or a.get("name") for a in api))
        crests["teams"][lg] = out; crests["colors"][lg] = cols
    json.dump(crests, open(crest_path, "w"), indent=1)
elif not token:
    print("FD_TOKEN non impostato: stemmi saltati")


# Pulizia dei calendari: niente partite con data passata (rinviate o mai giocate: in app sembrerebbero "da giocare" nei giorni scorsi)
# e, se ESPN (aggiornato ogni 3 ore) dà la stessa sfida in un altro giorno vicino, vale la data di ESPN (partita spostata).
try:
    _today = datetime.datetime.now(ROME).date()
    def _rd(fn):
        try: return list(csv.reader(io.StringIO(open(os.path.join(OUT, fn), encoding="utf-8").read())))
        except Exception: return []
    def _d(x):
        try: return datetime.datetime.strptime(x.strip(), "%d/%m/%Y").date()
        except Exception: return None
    E_ = _rd("espn_fixtures.csv"); espn_dates = {}
    for r in E_[1:]:
        if len(r) > 4 and _d(r[1]): espn_dates.setdefault((r[0], r[3].strip(), r[4].strip()), []).append(_d(r[1]))
    for fn in ("fixtures.csv", "next_fixtures.csv", "espn_fixtures.csv"):
        rd = _rd(fn)
        if not rd: continue
        keep, drop = [rd[0]], 0
        for r in rd[1:]:
            d = _d(r[1]) if len(r) > 4 else None
            if d is None: keep.append(r); continue
            if d < _today: drop += 1; continue
            ed = espn_dates.get((r[0], r[3].strip(), r[4].strip()))
            if fn != "espn_fixtures.csv" and ed and d not in ed and any(abs((x - d).days) <= 10 for x in ed): drop += 1; continue
            keep.append(r)
        buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(keep); save(fn, buf.getvalue())
        print("calendario", fn, "tolte", drop)
except Exception as e:
    print("pulizia calendari:", e)

# Arbitro e cartellini (API-Football, piano a pagamento): archivio partite in data/apif.json (all'inizio dallo storico 2022-2025
# del ramo storico), aggiornato ogni 3 ore con le stagioni in corso (anche le partite future: lì c'è l'arbitro, di solito 1-2 giorni prima).
# Per ogni partita (con le sole partite precedenti): fattore arbitro su falli e cartellini e cartellini attesi → data/extra.json.
# Backtest 2024-2026: falli +1,5% di precisione con l'arbitro, cartellini +2,9% sulla media del campionato (probabilità di Poisson tarate).
AF_LEAGUES_X = {"I1": 135, "I2": 136, "E0": 39, "E1": 40, "E2": 41, "E3": 42, "EC": 43, "SP1": 140, "SP2": 141, "F1": 61, "F2": 62, "D1": 78, "D2": 79,
                "N1": 88, "P1": 94, "SC0": 179, "SC1": 180, "SC2": 183, "SC3": 184, "B1": 144, "T1": 203, "G1": 197, "ARG": 128, "AUT": 218, "BRA": 71,
                "CHN": 169, "DNK": 119, "FIN": 244, "IRL": 357, "JPN": 98, "MEX": 262, "NOR": 103, "POL": 106, "ROU": 283, "RUS": 235, "SWE": 113,
                "SWZ": 207, "USA": 253}
try:
    import apif_extra, glob as _glob, urllib.parse as _up
    _key = os.environ.get("APIFOOTBALL_KEY", "").strip()
    ap_path = os.path.join(OUT, "apif.json")
    try: AP = json.load(open(ap_path))
    except Exception: AP = {}
    AP.setdefault("partite", {}); AP.setdefault("agg", "")
    if not AP["partite"]:   # primo giro: storico dal ramo storico (scaricato dal workflow in storico/)
        for fn in _glob.glob(os.path.join(os.path.dirname(OUT), "storico", "*.json")):
            D = json.load(open(fn))
            for fid, v in D["partite"].items(): AP["partite"][fid] = [v[0], D["lega"], v[1], v[2], v[3], v[4], v[5], v[6], v[7], "FT"]
        print("arbitri: storico iniziale", len(AP["partite"]), "partite")
    KS_ = ["Total Shots", "Shots on Goal", "Corner Kicks", "Fouls", "Yellow Cards", "Red Cards", "expected_goals"]
    def _af(path, **q):
        req = urllib.request.Request("https://v3.football.api-sports.io/" + path + ("?" + _up.urlencode(q) if q else ""), headers={"x-apisports-key": _key})
        with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
        time.sleep(0.25); return d
    _now = datetime.datetime.now(ROME)
    try: _due = not AP["agg"] or (_now - datetime.datetime.strptime(AP["agg"], "%Y-%m-%d %H:%M").replace(tzinfo=ROME)).total_seconds() >= 50 * 60   # ogni giro (circa ogni ora)
    except Exception: _due = True
    if _key and (_due or os.environ.get("APIF_FORCE")):
        st_ = _af("status").get("response", {}).get("requests", {})
        if int(st_.get("limit_day", 100)) > 100:   # serve il piano a pagamento
            cur_season = {}
            for x in _af("leagues", current="true").get("response", []):
                for ss in x.get("seasons", []):
                    if ss.get("current"): cur_season[x["league"]["id"]] = ss["year"]
            need, n_new = [], 0
            for lg, lid in AF_LEAGUES_X.items():
                sy = cur_season.get(lid)
                if not sy: continue
                for f in _af("fixtures", league=lid, season=sy).get("response", []):
                    fid = str(f["fixture"]["id"]); stt = f["fixture"]["status"]["short"]; old = AP["partite"].get(fid)
                    base = [f["fixture"]["date"][:16], lg, f["teams"]["home"]["name"], f["teams"]["away"]["name"], f["goals"]["home"], f["goals"]["away"],
                            f["fixture"].get("referee"), old[7] if old else [None] * 7, old[8] if old else [None] * 7, stt]
                    AP["partite"][fid] = base
                    if stt in ("FT", "AET", "PEN") and (base[7][4] is None or (_now.date() - datetime.date.fromisoformat(base[0][:10])).days <= 2): need.append(fid)
            def _stat(t, k):
                for s_ in t.get("statistics", []):
                    if s_["type"] == k:
                        v = s_["value"]
                        if v is None: return 0 if k in ("Yellow Cards", "Red Cards") else None
                        try: return float(str(v).replace("%", ""))
                        except Exception: return None
                return None
            for i in range(0, min(len(need), 2000), 20):
                for f in _af("fixtures", ids="-".join(need[i:i + 20])).get("response", []):
                    stt_ = {t["team"]["id"]: t for t in f.get("statistics", [])}
                    H, A = stt_.get(f["teams"]["home"]["id"], {}), stt_.get(f["teams"]["away"]["id"], {})
                    x = AP["partite"].get(str(f["fixture"]["id"]))
                    if x: x[7] = [_stat(H, k) for k in KS_]; x[8] = [_stat(A, k) for k in KS_]; n_new += 1
            AP["agg"] = _now.strftime("%Y-%m-%d %H:%M")
            print("arbitri: aggiornate", n_new, "statistiche,", len(AP["partite"]), "partite in archivio")
        json.dump(AP, open(ap_path, "w"), separators=(",", ":"), ensure_ascii=False)
    # nostre partite (giocate e in calendario) per abbinare i nomi e le date
    ours, pairs = collections.defaultdict(list), collections.defaultdict(list)
    for fn in files:
        try:
            rd = list(csv.DictReader(io.StringIO(open(os.path.join(OUT, fn), encoding="utf-8-sig").read())))
        except Exception: continue
        for r in rd:
            lg = (r.get("Div") or r.get("Country") or "").strip()
            h, a = (r.get("HomeTeam") or r.get("Home") or "").strip(), (r.get("AwayTeam") or r.get("Away") or "").strip()
            try:
                dd = r["Date"].strip().split("/"); y = dd[2] if len(dd[2]) == 4 else "20" + dd[2]; d = datetime.date(int(y), int(dd[1]), int(dd[0]))
            except Exception: continue
            g1, g2 = (r.get("FTHG") or r.get("HG") or "").strip(), (r.get("FTAG") or r.get("AG") or "").strip()
            pairs[(lg, h, a)].append(d)
            if g1.isdigit() and g2.isdigit(): ours[lg].append((d, h, a, int(g1), int(g2)))
    by_lg = collections.defaultdict(list)
    for v in AP["partite"].values(): by_lg[v[1]].append(v)
    MAPS = {}
    for lg, L in by_lg.items():
        L.sort(key=lambda v: v[0])
        MAPS[lg] = apif_extra.learn_map([(datetime.date.fromisoformat(v[0][:10]), v[2], v[3], v[4], v[5]) for v in L if v[9] in ("FT", "AET", "PEN")], ours.get(lg, []), lg)
    # Statistiche da API-Football su tutte le partite che ha (dal 2022), se plausibili (apif_extra.api_stats_ok); altrimenti
    # quelle di football-data. Anche i campionati senza statistiche su football-data (Polonia, Romania, Svizzera, Finlandia, Irlanda).
    n_fill = 0
    for fn in files:
        lg = fn.split("_")[0].split(".")[0]
        if lg not in by_lg or not fn.endswith(".csv") or "fixtures" in fn: continue
        try:
            rd = list(csv.reader(io.StringIO(open(os.path.join(OUT, fn), encoding="utf-8-sig").read())))
            if not rd: continue
            rd2, k = apif_extra.fill_stats(rd, lg, [v for v in by_lg[lg] if v[9] in ("FT", "AET", "PEN")], MAPS[lg], override=AF_PRO)
            if k:
                buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(rd2); save(fn, buf.getvalue()); n_fill += k
        except Exception as e:
            print("statistiche API", fn, e)
    print("statistiche da API-Football:", n_fill, "partite riempite")
    if AF_PRO:
        # risultati: partite giocate che API-Football ha e i nostri file non ancora (fonte principale per i risultati del giorno)
        n_res = 0
        for lg in by_lg:
            fn = f"{lg}_{code(cur)}.csv" if lg in LEAGUES else f"{lg}.csv"
            if fn not in files: continue
            try:
                rd = list(csv.reader(io.StringIO(open(os.path.join(OUT, fn), encoding="utf-8-sig").read())))
                rd2, k = apif_extra.add_results(rd, lg, by_lg[lg], MAPS[lg], _now.date(), ROME)
                if k:
                    buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(rd2); save(fn, buf.getvalue()); n_res += k
            except Exception as e:
                print("risultati API", fn, e)
        print("risultati da API-Football:", n_res, "partite aggiunte")
        # calendario: prossime 3 settimane da API-Football (data e ora italiane); squadre non riconosciute → partita scartata
        cal, unk = [["Div", "Date", "Time", "HomeTeam", "AwayTeam", "Round"]], set()
        for lg, L in by_lg.items():
            for v in L:
                if v[9] not in ("NS", "TBD"): continue
                loc = datetime.datetime.fromisoformat(v[0] + ":00+00:00").astimezone(ROME)
                if not (_now.date() <= loc.date() <= _now.date() + datetime.timedelta(days=21)): continue
                h, a = MAPS[lg].get(v[2]), MAPS[lg].get(v[3])
                if not h or not a: unk.update(x for x, y in ((v[2], h), (v[3], a)) if not y); continue
                cal.append([lg, loc.strftime("%d/%m/%Y"), "" if v[9] == "TBD" else loc.strftime("%H:%M"), h, a, ""])
        api_lg = {r[0] for r in cal[1:]}
        buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(cal); save("api_fixtures.csv", buf.getvalue())
        if "api_fixtures.csv" not in files: files.append("api_fixtures.csv")
        # le altre fonti di calendario restano solo per i campionati che API-Football non copre; da football-data teniamo le
        # righe con la stessa data (portano le quote), non quelle con la data vecchia
        api_dates = collections.defaultdict(set)
        for r in cal[1:]: api_dates[(r[0], r[3], r[4])].add(r[1])
        api_time = {(r[0], r[1], r[3], r[4]): r[2] for r in cal[1:]}
        for fn in ("next_fixtures.csv", "fixtures.csv", "espn_fixtures.csv"):
            try: rd = list(csv.reader(io.StringIO(open(os.path.join(OUT, fn), encoding="utf-8").read())))
            except Exception: continue
            if fn == "espn_fixtures.csv":
                # ESPN (aggiornato ogni 3 ore) solo per le sfide che API-Football non mette nelle prossime 3 settimane
                # (es. partita spostata che API-Football ha ancora alla data vecchia)
                keep = [rd[0]] + [r for r in rd[1:] if len(r) > 4 and not api_dates.get((r[0], r[3].strip(), r[4].strip()))]
            else:
                keep = [rd[0]] + [r for r in rd[1:] if len(r) > 4 and (r[0] not in api_lg or (fn == "fixtures.csv" and r[1] in api_dates.get((r[0], r[3].strip(), r[4].strip()), ())))]
                for r in keep[1:]:   # stessa partita di API-Football: vale l'ora italiana di API-Football
                    t = api_time.get((r[0], r[1], r[3].strip(), r[4].strip()))
                    if t is not None and len(r) > 2: r[2] = t
            buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(keep); save(fn, buf.getvalue())
        for r in cal[1:]:
            try: pairs[(r[0], r[3], r[4])].append(datetime.datetime.strptime(r[1], "%d/%m/%Y").date())
            except Exception: pass
        print("calendario da API-Football:", len(cal) - 1, "partite,", len(api_lg), "campionati; squadre non riconosciute:", sorted(unk)[:30])
        # controllo qualità: squadre non riconosciute, partite scadute (non giocate con data passata), statistiche scartate, calendario da ESPN
        QUAL["squadre_non_riconosciute"] = sorted(unk)
        stale, bad = [], []
        for lg, L in by_lg.items():
            for v in L:
                d = datetime.date.fromisoformat(v[0][:10])
                if v[9] in ("NS", "TBD") and _now.date() - datetime.timedelta(days=14) <= d < _now.date():
                    stale.append(f"{lg} {d:%d/%m} {v[2]} - {v[3]}")
                if v[9] in ("FT", "AET", "PEN") and d >= _now.date() - datetime.timedelta(days=14) and v[7][0] is not None:
                    ok = apif_extra.api_stats_ok(v)
                    no = [n for n, k in (("tiri", "s"), ("tiri in porta", "st"), ("falli", "f"), ("corner", "c")) if not ok[k]]
                    if no: bad.append(f"{lg} {d:%d/%m} {v[2]} - {v[3]}: {', '.join(no)}")
        QUAL["partite_scadute"] = stale; QUAL["statistiche_scartate"] = bad
        try: QUAL["calendario_da_espn"] = [" ".join([r[0], r[1], r[3], "-", r[4]]) for r in list(csv.reader(open(os.path.join(OUT, "espn_fixtures.csv"), encoding="utf-8")))[1:] if len(r) > 4]
        except Exception: QUAL["calendario_da_espn"] = []
    EX, lim = {}, _now.date() - datetime.timedelta(days=400)
    for lg, L in by_lg.items():
        mp = MAPS[lg]
        rows = []
        for v in L:
            H, A = v[7], v[8]; played = v[9] in ("FT", "AET", "PEN")
            rows.append(dict(h=v[2], a=v[3], ref=(v[6] or "").split(",")[0].strip() or None,
                             hc=(H[4] + (H[5] or 0)) if played and H[4] is not None else None, ac=(A[4] + (A[5] or 0)) if played and A[4] is not None else None,
                             hf=H[3] if played else None, af=A[3] if played else None))
        for v, r, x in zip(L, rows, apif_extra.compute(rows)):
            h, a = mp.get(v[2]), mp.get(v[3]); d = datetime.date.fromisoformat(v[0][:10])
            if not h or not a or d < lim: continue
            ds = [z for z in pairs.get((lg, h, a), []) if abs((z - d).days) <= 1]
            if not ds: continue
            EX[f"{lg}|{ds[0]}|{h}|{a}"] = [x["ref"], x["n"], x["ff"], x["fc"], x["mu"], (r["hc"] + r["ac"]) if r["hc"] is not None and r["ac"] is not None else None, x["mh"], x["ma"]]
    json.dump({"agg": _now.strftime("%d/%m/%Y %H:%M"), "partite": EX}, open(os.path.join(OUT, "extra.json"), "w"), separators=(",", ":"), ensure_ascii=False)
    print("arbitri e cartellini:", len(EX), "partite abbinate")
except Exception as e:
    import traceback; traceback.print_exc(); print("arbitri e cartellini:", e)

# Quote dei bookmaker da API-Football (segreto APIFOOTBALL_KEY; piano gratuito: 100 richieste al giorno, 10 al minuto).
# Una volta al giorno (dalle 7 italiane): partite di oggi e domani dei nostri campionati, quota mediana tra i bookmaker
# per Over/Under gol, Gol/No gol, 1X2 e 1X2 corner. Servono solo da mostrare accanto alle nostre probabilità: non entrano
# nei modelli né nel Confidence Score (che usa le quote di football-data, con cui sono stati stimati i pesi).
# Una partita riceve le quote solo se le due squadre corrispondono a una sfida del nostro calendario nello stesso campionato (±1 giorno).
AF_LEAGUES = {"I1": 135, "I2": 136, "E0": 39, "E1": 40, "E2": 41, "E3": 42, "EC": 43, "SP1": 140, "SP2": 141, "F1": 61, "F2": 62, "D1": 78, "D2": 79,
              "N1": 88, "P1": 94, "SC0": 179, "SC1": 180, "SC2": 183, "SC3": 184, "B1": 144, "T1": 203, "G1": 197, "ARG": 128, "AUT": 218, "BRA": 71,
              "CHN": 169, "DNK": 119, "FIN": 244, "IRL": 357, "JPN": 98, "MEX": 262, "NOR": 103, "POL": 106, "ROU": 283, "RUS": 235, "SWE": 113,
              "SWZ": 207, "USA": 253}
AF_KEY = os.environ.get("APIFOOTBALL_KEY", "").strip()
odds_path = os.path.join(OUT, "odds.json")
try: OD = json.load(open(odds_path))
except Exception: OD = {}
rome_now = datetime.datetime.now(ROME)
def _odds_due():   # gratis: una volta al giorno dalle 7; a pagamento (OD["pro"]): ogni 3 ore
    if OD.get("errore") and not OD.get("partite"): return True
    if OD.get("giorno") != rome_now.strftime("%Y-%m-%d"): return rome_now.hour >= 7
    if OD.get("pro"):
        try: return (rome_now - datetime.datetime.strptime(OD["aggiornate"], "%d/%m/%Y %H:%M").replace(tzinfo=ROME)).total_seconds() >= 3 * 3600
        except Exception: return True
    return False
if AF_KEY and (_odds_due() or os.environ.get("ODDS_FORCE")):
    af_used = [0]
    def af(path, **q):
        af_used[0] += 1
        req = urllib.request.Request("https://v3.football.api-sports.io/" + path + "?" + urllib.parse.urlencode(q), headers={"x-apisports-key": AF_KEY})
        with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
        time.sleep(6.5)
        if d.get("errors"): raise RuntimeError(str(d["errors"]))
        return d
    import urllib.parse, statistics
    BY_ID = {v: k for k, v in AF_LEAGUES.items()}
    # il nostro calendario (prossimi giorni), per abbinare le squadre
    ours = {}
    for fn in ("api_fixtures.csv", "next_fixtures.csv", "espn_fixtures.csv", "fixtures.csv"):   # api_fixtures: calendario principale
        try:
            for r in csv.DictReader(io.StringIO(open(os.path.join(OUT, fn), encoding="utf-8").read())):
                try: dd = datetime.datetime.strptime(r["Date"].strip(), "%d/%m/%Y").date()
                except Exception: continue
                ours.setdefault(r["Div"].strip(), set()).add((dd, r["HomeTeam"].strip(), r["AwayTeam"].strip()))
        except Exception as e:
            print("quote: calendario", fn, e)
    def pick(lg, dd, h, a):   # sfida del nostro calendario che corrisponde (stesso campionato, ±1 giorno), altrimenti None
        cand = [(d, x, y) for d, x, y in ours.get(lg, ()) if abs((d - dd).days) <= 1]
        if not cand: return None
        def sc(api, mine):
            al = ESPN_ALIAS.get(lg, {}).get(api) or ALIAS.get(lg, {}).get(api) or FIX_ALIAS.get(api)
            if al == mine or api == mine: return 1.0
            a1, m1 = _norm(api), _norm(mine)
            if a1 == m1: return 1.0
            if a1 and m1 and (a1 in m1 or m1 in a1): return 0.9
            return difflib.SequenceMatcher(None, a1, m1).ratio()
        best = sorted(((sc(h, x) + sc(a, y), sc(h, x), sc(a, y), (d, x, y)) for d, x, y in cand), reverse=True)
        top = best[0]
        if top[1] < 0.6 or top[2] < 0.6: return None
        if len(best) > 1 and best[1][0] >= top[0] - 0.15: return None   # ambiguo: due sfide quasi uguali
        return top[3]
    def med(xs):
        xs = [x for x in xs if x and x > 1]
        return round(statistics.median(xs), 2) if xs else None
    res, nomatch, err, allq = {}, [], None, {}
    XBETS = {"Corners Over Under": "cou", "Home Corners Over/Under": "hcou", "Away Corners Over/Under": "acou", "Corners Asian Handicap": "cah",
             "Cards Over/Under": "kou", "Home Team Total Cards": "hk", "Away Team Total Cards": "ak", "Total ShotOnGoal": "sot",
             "Home Total ShotOnGoal": "hsot", "Away Total ShotOnGoal": "asot", "Asian Handicap": "ah", "Double Chance": "dc"}
    def take(e, f):   # quote mediane di una partita
        lg = BY_ID[f["league"]["id"]]; fdd = datetime.date.fromisoformat(f["fixture"]["date"][:10])
        m = pick(lg, fdd, f["teams"]["home"]["name"], f["teams"]["away"]["name"])
        if not m: nomatch.append(f"{lg} {f['teams']['home']['name']} - {f['teams']['away']['name']}"); return
        acc, xacc = {}, {}
        for b in e.get("bookmakers", []):
            for bet in b.get("bets", []):
                for v in bet.get("values", []):
                    try: o = float(v["odd"])
                    except Exception: continue
                    nm, val = bet["name"], str(v["value"])
                    if nm in XBETS: xacc.setdefault(XBETS[nm] + ":" + val, {})[b["name"]] = o   # mercati secondari: solo archivio
                    if nm == "Match Winner": key = "1x2:" + {"Home": "1", "Draw": "X", "Away": "2"}.get(val, "")
                    elif nm == "Goals Over/Under" and val.split(" ")[-1] in ("1.5", "2.5", "3.5"): key = "ou" + val.split(" ")[-1] + ":" + val.split(" ")[0][0]
                    elif nm == "Both Teams Score": key = "gg:" + {"Yes": "S", "No": "N"}.get(val, "")
                    elif nm == "Corners 1x2": key = "c1x2:" + {"Home": "1", "Draw": "X", "Away": "2", "1": "1", "X": "X", "2": "2"}.get(val, "")
                    else: continue
                    if key.endswith(":"): continue
                    acc.setdefault(key, {})[b["name"]] = o
        q = {kk: [med(list(v.values())), len(v)] for kk, v in acc.items()}
        q = {kk: v for kk, v in q.items() if v[0]}
        if q: res[f"{lg}|{m[0]}|{m[1]}|{m[2]}"] = {"q": q, "nb": len(e.get("bookmakers", [])), "agg": e.get("update", "")[:16]}
        xq = {kk: [med(list(v.values())), len(v)] for kk, v in xacc.items()}
        xq = {kk: v for kk, v in xq.items() if v[0]}
        if q or xq: allq[f"{lg}|{m[0]}|{m[1]}|{m[2]}"] = {**q, **xq}
    try:
        # richieste rimaste oggi (la chiamata status non conta); ne lascio 5 di margine
        req = urllib.request.Request("https://v3.football.api-sports.io/status", headers={"x-apisports-key": AF_KEY})
        with urllib.request.urlopen(req, timeout=60) as r: stt = json.loads(r.read().decode()).get("response", {}).get("requests", {})
        budget = int(stt.get("limit_day", 100)) - int(stt.get("current", 0)) - 5
        paid = int(stt.get("limit_day", 100)) > 100
        # Il piano gratuito non accetta la stagione in corso come parametro: quote chieste per data (tutte le partite, 10 per pagina)
        # oppure per singola partita, scegliendo la via con meno richieste.
        for k in range(7 if paid else 2):   # piano gratuito: quote solo da ieri a domani → oggi e domani; a pagamento: 7 giorni
            if budget < 2: break
            dd = rome_now.date() + datetime.timedelta(days=k)
            F = af("fixtures", date=str(dd), timezone="Europe/Rome").get("response", []); budget -= 1
            fx = {f["fixture"]["id"]: f for f in F if f["league"]["id"] in BY_ID and f["fixture"]["status"]["short"] in ("NS", "TBD")}
            if not fx: continue
            O = af("odds", date=str(dd), timezone="Europe/Rome", page=1); budget -= 1
            pages, seen = (O.get("paging") or {}).get("total", 1) or 1, set()
            for e in O.get("response", []):
                if e["fixture"]["id"] in fx: take(e, fx[e["fixture"]["id"]]); seen.add(e["fixture"]["id"])
            todo = [i for i in fx if i not in seen]
            if len(todo) <= pages - 1:
                for i in todo:
                    if budget < 1: break
                    for e in af("odds", fixture=i).get("response", []): take(e, fx[i])
                    budget -= 1
            else:
                for pg in range(2, pages + 1):
                    if budget < 1: break
                    for e in af("odds", date=str(dd), timezone="Europe/Rome", page=pg).get("response", []):
                        if e["fixture"]["id"] in fx: take(e, fx[e["fixture"]["id"]])
                    budget -= 1
    except Exception as e:
        err = str(e); print("quote API-Football:", e)
    if res or not err:   # con un errore e nessuna quota: si riprova al giro dopo (il file precedente resta)
        OD = {"giorno": rome_now.strftime("%Y-%m-%d"), "aggiornate": rome_now.strftime("%d/%m/%Y %H:%M"), "fonte": "API-Football (quota mediana tra i bookmaker)",
              "richieste": af_used[0], "errore": err, "non_abbinate": nomatch[:80], "pro": bool(locals().get("paid")), "partite": res}
        json.dump(OD, open(odds_path, "w"), separators=(",", ":"), ensure_ascii=False)
    # Archivio per verificare in futuro i mercati (corner, cartellini, tiri in porta…): per ogni partita la prima quota vista e l'ultima
    # prima del calcio d'inizio, con l'ora. Non si cancella mai: serve proprio a misurare a posteriori.
    if allq:
        hp = os.path.join(OUT, "odds_hist.json")
        try: OH = json.load(open(hp))
        except Exception: OH = {}
        ts = rome_now.strftime("%Y-%m-%d %H:%M")
        for kk, q in allq.items():
            x = OH.setdefault(kk, {})
            if "prima" not in x: x["prima"] = {"ora": ts, "q": q}
            x["ultima"] = {"ora": ts, "q": q}
        json.dump(OH, open(hp, "w"), separators=(",", ":"), ensure_ascii=False)
        print("archivio quote:", len(OH), "partite")
    print("quote:", len(res), "partite,", af_used[0], "richieste,", len(nomatch), "non abbinate")
elif not AF_KEY:
    print("APIFOOTBALL_KEY non impostata: quote saltate")

# controllo qualità: riepilogo del giro (aggiornato a ogni giro, anche se API-Football non ha risposto)
try:
    _od = json.load(open(os.path.join(OUT, "odds.json")))
    na, ab = len(_od.get("non_abbinate", [])), len(_od.get("partite", {}))
    QUAL["quote"] = {"aggiornate": _od.get("aggiornate"), "abbinate": ab, "non_abbinate": na, "esempi_non_abbinate": _od.get("non_abbinate", [])[:10]}
except Exception: QUAL["quote"] = None
try: QUAL["api_aggiornata"] = json.load(open(os.path.join(OUT, "apif.json"))).get("agg")
except Exception: QUAL["api_aggiornata"] = None
_av = []
if QUAL.get("quote") and QUAL["quote"]["abbinate"] + QUAL["quote"]["non_abbinate"] >= 10 and QUAL["quote"]["non_abbinate"] > QUAL["quote"]["abbinate"] * 0.25:
    _av.append(f"Quote: {QUAL['quote']['non_abbinate']} partite non abbinate su {QUAL['quote']['abbinate'] + QUAL['quote']['non_abbinate']}")
if QUAL.get("squadre_non_riconosciute"): _av.append(f"{len(QUAL['squadre_non_riconosciute'])} squadre di API-Football non riconosciute")
if QUAL.get("partite_scadute"): _av.append(f"{len(QUAL['partite_scadute'])} partite non giocate con data passata (rinviate o calendario non aggiornato)")
if QUAL.get("statistiche_scartate"): _av.append(f"{len(QUAL['statistiche_scartate'])} partite con statistiche API impossibili (usato football-data o vuoto)")
try:
    if not AF_PRO: _av.append("API-Football non disponibile: dati dalle fonti gratuite")
    elif QUAL.get("api_aggiornata") and (datetime.datetime.now(ROME) - datetime.datetime.strptime(QUAL["api_aggiornata"], "%Y-%m-%d %H:%M").replace(tzinfo=ROME)).total_seconds() > 3 * 3600:
        _av.append("Archivio API-Football non aggiornato da più di 3 ore")
except Exception: pass
QUAL["avvisi"] = _av; QUAL["stato"] = "ok" if not _av else "da controllare"; QUAL["giro"] = datetime.datetime.now(ROME).strftime("%d/%m/%Y %H:%M")
json.dump(QUAL, open(os.path.join(OUT, "qualita.json"), "w"), ensure_ascii=False, indent=1)
print("controllo qualità:", QUAL["stato"], _av)

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2)))
json.dump({"updated": now.strftime("%d/%m/%Y %H:%M"), "files": files},
          open(os.path.join(OUT, "manifest.json"), "w"), indent=1)

# bundle.json: tutti i dati in un solo file, con solo le colonne che usa l'app (l'app si apre più in fretta)
KEEP = {"Div", "Date", "Time", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "HTHG", "HTAG", "HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC", "HxG", "AxG", "Round",
        "AvgH", "AvgD", "AvgA", "B365H", "B365D", "B365A", "Avg>2.5", "Avg<2.5", "B365>2.5", "B365<2.5",
        "Country", "League", "Season", "Home", "Away", "HG", "AG", "HK", "AK", "AvgCH", "AvgCD", "AvgCA", "PSCH", "PSCD", "PSCA", "AvgC>2.5", "AvgC<2.5"}
bundle = []
for f in files:
    try:
        rd = list(csv.reader(io.StringIO(open(os.path.join(OUT, f), encoding="utf-8-sig").read())))
        if not rd: continue
        hdr = [h.strip() for h in rd[0]]; idx = [i for i, h in enumerate(hdr) if h in KEEP]
        buf = io.StringIO(); w = csv.writer(buf, lineterminator="\n")
        w.writerow([hdr[i] for i in idx])
        for r in rd[1:]:
            if any(x.strip() for x in r): w.writerow([r[i] if i < len(r) else "" for i in idx])
        bundle.append({"name": f, "text": buf.getvalue()})
    except Exception as e:
        print("bundle: salto", f, e)
json.dump({"updated": now.strftime("%d/%m/%Y %H:%M"), "files": bundle}, open(os.path.join(OUT, "bundle.json"), "w"), separators=(",", ":"))
print("ok", len(files), "file")
