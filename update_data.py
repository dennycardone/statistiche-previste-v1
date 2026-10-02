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

import csv, io
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
ESPN_ALIAS = {"DNK": {"AGF": "Aarhus", "F.C. København": "FC Copenhagen"}, "NOR": {"Hamarkameratene": "HamKam"}}
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
if os.path.exists(espn_path): files.append("espn_fixtures.csv")

# Corner, falli, tiri e tiri in porta per i campionati che football-data dà solo con risultati: dalle statistiche partita di ESPN.
# Verificato (ottobre 2026) su 73 partite di Serie A e Premier: stessi numeri di football-data (stesso fornitore).
# Cache in data/espn_stats.json; a ogni giro al massimo ESPN_BUDGET partite nuove (il passato si riempie in pochi giri).
# Una partita riceve le statistiche solo se squadre, giorno (±1) e risultato coincidono con la riga di football-data.
ESPN_STATS = {"BRA": "bra.1", "ARG": "arg.1"}
ESPN_BUDGET = 700
STAT_COLS = ["HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC"]
cache_path = os.path.join(OUT, "espn_stats.json")
try: SC = json.load(open(cache_path))
except Exception: SC = {}
SC.setdefault("v", 1); SC.setdefault("months", {}); SC.setdefault("ev", {})
budget = ESPN_BUDGET
def _tn(t): return [t.get("displayName"), t.get("shortDisplayName"), t.get("name"), t.get("abbreviation"), t.get("location")]
for lg, code_ in ESPN_STATS.items():
    done = set(SC["months"].setdefault(lg, [])); EV = SC["ev"].setdefault(lg, {})
    months, y, m = [], today.year - 5, 1
    while (y, m) <= (today.year, today.month):
        months.append(f"{y}{m:02d}"); m += 1
        if m > 12: y, m = y + 1, 1
    recent = set(months[-2:])
    for ym in months:
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
                EV[eid] = [ev["date"], _tn(side["home"]["team"]), _tn(side["away"]["team"]), int(float(side["home"].get("score", -1))),
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
    nmap, used = {}, {}
    for e in SC["ev"].get(lg, {}).values():
        for names in (e[1], e[2]):
            k = names[0]
            if k in nmap: continue
            t = espn_match(lg, names, pool); nmap[k] = t
            if t: used.setdefault(t, set()).add(k)
    dup = {t for t, v in used.items() if len(v) > 1}
    idx = {}
    for e in SC["ev"].get(lg, {}).values():
        if e[5] is None: continue
        h, a = nmap.get(e[1][0]), nmap.get(e[2][0])
        if not h or not a or h in dup or a in dup: continue
        d = datetime.datetime.strptime(e[0], "%Y-%m-%dT%H:%MZ").date()
        idx.setdefault((h, a), []).append((d, e[3], e[4], e[5]))
    n_ok = 0
    out = [hdr + STAT_COLS]
    for r in body:
        add = [""] * 8
        try:
            d = datetime.datetime.strptime(r[iD].strip(), "%d/%m/%Y").date()
            for (ed, g1, g2, vals) in idx.get((r[iH].strip(), r[iA].strip()), []):
                if abs((ed - d).days) <= 1 and str(g1) == r[iG1].strip() and str(g2) == r[iG2].strip():
                    add = [str(v) for v in vals]; n_ok += 1; break
        except Exception:
            pass
        out.append(r + add)
    buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(out); save(f"{lg}.csv", buf.getvalue())
    espn_stats_check[lg] = {"partite_con_statistiche": n_ok, "partite_totali": len(body), "squadre_doppie": sorted(dup),
                            "nomi_non_riconosciuti": sorted(k for k, v in nmap.items() if v is None)}
try:
    J = json.load(open(os.path.join(OUT, "espn_check.json")))
except Exception:
    J = {}
J["statistiche"] = espn_stats_check; J["statistiche_aggiornate"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
json.dump(J, open(os.path.join(OUT, "espn_check.json"), "w"), indent=1, ensure_ascii=False)
if unknown:
    print("Nomi non convertiti (verificare ALIAS se non coincidono con football-data):", sorted(unknown))

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


now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2)))
json.dump({"updated": now.strftime("%d/%m/%Y %H:%M"), "files": files},
          open(os.path.join(OUT, "manifest.json"), "w"), indent=1)

# bundle.json: tutti i dati in un solo file, con solo le colonne che usa l'app (l'app si apre più in fretta)
KEEP = {"Div", "Date", "Time", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "HTHG", "HTAG", "HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC", "HxG", "AxG", "Round",
        "AvgH", "AvgD", "AvgA", "B365H", "B365D", "B365A", "Avg>2.5", "Avg<2.5", "B365>2.5", "B365<2.5",
        "Country", "League", "Season", "Home", "Away", "HG", "AG", "AvgCH", "AvgCD", "AvgCA", "PSCH", "PSCD", "PSCA", "AvgC>2.5", "AvgC<2.5"}
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
