"""Scarica da football-data.co.uk i CSV dei campionati della dashboard nella cartella data/.
Campionati europei: stagione corrente sempre, le 5 precedenti solo se mancano (servono per gli H2H).
"""
import datetime, json, os, urllib.request

LEAGUES = ["I1", "I2", "E0", "SP1", "F1", "D1", "N1", "P1"]
NEW_LEAGUES = []
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

for lg in NEW_LEAGUES:
    name = f"{lg}.csv"
    try:
        txt = get(NEW.format(lg=lg))
        if "Home" in txt:
            save(name, txt)
    except Exception as e:
        print("skip", name, e)
    if os.path.exists(os.path.join(OUT, name)):
        files.append(name)

# prossime giornate: calendario completo da fixturedownload.com (gratuito, senza chiave).
# I nomi delle squadre vengono convertiti in quelli usati da football-data.co.uk.
FD_SLUGS = {"I1": "serie-a", "E0": "epl", "SP1": "la-liga", "F1": "ligue-1", "D1": "bundesliga", "N1": "eredivisie", "P1": "primeira-liga"}
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
rows = ["Div,Date,Time,HomeTeam,AwayTeam,Round"]
unknown = set()
for lg, slug in FD_SLUGS.items():
    try:
        data = json.loads(get(f"https://fixturedownload.com/feed/json/{slug}-{cur}"))
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
        h = ALIAS[lg].get(m["HomeTeam"], m["HomeTeam"]); a = ALIAS[lg].get(m["AwayTeam"], m["AwayTeam"])
        if h == m["HomeTeam"] and h not in ALIAS[lg].values(): unknown.add((lg, h))
        if a == m["AwayTeam"] and a not in ALIAS[lg].values(): unknown.add((lg, a))
        rows.append(",".join([lg, loc.strftime("%d/%m/%Y"), tm, h.replace(",", " "), a.replace(",", " "), str(m.get("RoundNumber", ""))]))
save("next_fixtures.csv", "\n".join(rows))
files.append("next_fixtures.csv")
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
fresh = old.get("v") == 2 and old.get("updated") and (datetime.date.today() - datetime.date.fromisoformat(old["updated"])).days < 7
if token and not fresh:
    crests = {"v": 2, "updated": datetime.date.today().isoformat(), "teams": {}}
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
        out = {}
        for t in sorted(mine):
            if t in CREST_MANUAL: out[t] = CREST_MANUAL[t]; continue
            key = norm(CREST_ALIAS.get(t, t)); best = None; part = []
            for a in api:
                names = [norm(a.get("shortName") or ""), norm(a.get("name") or ""), norm(a.get("tla") or "")]
                if key in names: best = a; break
                if any(re.search(r"\b" + re.escape(key) + r"\b", n) for n in names[:2]): part.append(a)
            if not best and part: best = min(part, key=lambda a: len(a.get("name") or ""))   # il nome più corto che contiene la parola
            if best and best.get("crest"): out[t] = best["crest"]
            else: print("STEMMA NON TROVATO:", lg, t, "| squadre disponibili:", ", ".join(a.get("shortName") or a.get("name") for a in api))
        crests["teams"][lg] = out
    json.dump(crests, open(crest_path, "w"), indent=1)
elif not token:
    print("FD_TOKEN non impostato: stemmi saltati")

# Elo da ClubElo (api.clubelo.com, gratuito, senza chiave) -> data/elo.csv (date,div,team,elo).
# Serve alla Media dinamica dei gol. Istantanee il 1° e il 15 di ogni mese dall'inizio della stagione, più quella di oggi.
# I nomi di ClubElo sono diversi da quelli di football-data.co.uk: il collegamento si fa confrontando i valori ClubElo del 01/06/2025
# (ELO_REF, presi dall'archivio Club-Football-Match-Data, fonte ClubElo) e, per le squadre nuove, con il nome. Esito in data/elo_log.txt.
import csv, io, difflib
ELO_COUNTRY = {"I1": "ITA", "I2": "ITA", "E0": "ENG", "SP1": "ESP", "F1": "FRA", "D1": "GER", "N1": "NED", "P1": "POR"}
ELO_REF = {"GER":{"Augsburg":1618.66,"Bayern Munich":1919.0,"Bochum":1539.74,"Darmstadt":1445.67,"Dortmund":1818.35,"Ein Frankfurt":1745.76,"Elversberg":1501.5,"FC Koln":1552.19,"Fortuna Dusseldorf":1505.92,"Freiburg":1684.34,"Greuther Furth":1404.26,"Hamburg":1554.55,"Heidenheim":1558.73,"Hertha":1454.29,"Hoffenheim":1605.84,"Holstein Kiel":1537.13,"Leverkusen":1848.79,"M'gladbach":1632.48,"Mainz":1706.18,"Paderborn":1491.97,"RB Leipzig":1716.37,"Schalke 04":1408.42,"St Pauli":1577.11,"Stuttgart":1719.31,"Union Berlin":1617.17,"Werder Bremen":1677.45,"Wolfsburg":1645.72},"ENG":{"Arsenal":1993.34,"Aston Villa":1872.84,"Bournemouth":1808.1,"Brentford":1811.27,"Brighton":1827.13,"Burnley":1729.6,"Chelsea":1902.8,"Coventry":1546.33,"Crystal Palace":1835.04,"Everton":1793.98,"Fulham":1781.72,"Hull":1492.23,"Ipswich":1591.07,"Leeds":1722.36,"Leicester":1618.57,"Liverpool":1993.42,"Luton":1498.03,"Man City":1959.94,"Man United":1799.46,"Newcastle":1868.55,"Norwich":1506.63,"Nott'm Forest":1802.87,"Sheffield United":1622.27,"Southampton":1555.24,"Sunderland":1547.1,"Tottenham":1774.01,"Watford":1472.01,"West Brom":1537.86,"West Ham":1750.13,"Wolves":1735.76},"FRA":{"Ajaccio":1396.28,"Amiens":1391.28,"Angers":1538.24,"Auxerre":1629.1,"Brest":1679.1,"Clermont":1418.83,"Le Havre":1553.54,"Lens":1693.22,"Lille":1782.05,"Lorient":1595.59,"Lyon":1744.63,"Marseille":1756.53,"Metz":1575.77,"Monaco":1762.13,"Montpellier":1490.47,"Nantes":1586.95,"Nice":1720.62,"Paris FC":1543.14,"Paris SG":1974.94,"Reims":1589.83,"Rennes":1663.49,"St Etienne":1532.84,"Strasbourg":1707.01,"Toulouse":1653.91,"Troyes":1441.31},"ITA":{"Atalanta":1842.22,"Bologna":1750.82,"Brescia":1424.0,"Cagliari":1602.28,"Como":1648.34,"Cremonese":1532.65,"Empoli":1577.66,"Fiorentina":1756.97,"Frosinone":1470.95,"Genoa":1664.06,"Inter":1933.24,"Juventus":1805.85,"Lazio":1770.41,"Lecce":1583.05,"Milan":1786.91,"Monza":1519.14,"Napoli":1838.37,"Parma":1602.97,"Pisa":1531.47,"Roma":1819.66,"Salernitana":1440.11,"Sampdoria":1436.17,"Sassuolo":1596.91,"Spezia":1532.48,"Torino":1675.24,"Udinese":1620.26,"Venezia":1557.56,"Verona":1595.07,"Bari":1439.38,"Carrarese":1411.26,"Catanzaro":1461.08,"Cesena":1433.63,"Cittadella":1367.74,"Cosenza":1354.6,"Juve Stabia":1452.54,"Mantova":1411.93,"Modena":1422.21,"Palermo":1467.57,"Reggiana":1407.29,"Sudtirol":1444.71},"NED":{"AZ Alkmaar":1626.28,"Ajax":1663.95,"Almere City":1349.17,"Feyenoord":1738.36,"For Sittard":1420.51,"Go Ahead Eagles":1498.69,"Groningen":1410.41,"Heerenveen":1445.41,"Heracles":1409.37,"NAC Breda":1351.14,"Nijmegen":1505.07,"PSV Eindhoven":1797.04,"Sparta Rotterdam":1493.51,"Twente":1576.95,"Utrecht":1584.75,"Waalwijk":1378.19,"Willem II":1324.45,"Zwolle":1462.81},"POR":{"AVS":1353.67,"Arouca":1471.93,"Benfica":1791.48,"Boavista":1345.25,"Casa Pia":1459.93,"Estoril":1470.44,"Famalicao":1511.27,"Farense":1388.83,"Gil Vicente":1432.91,"Guimaraes":1576.28,"Moreirense":1460.37,"Nacional":1410.28,"Porto":1678.2,"Rio Ave":1450.03,"Santa Clara":1484.94,"Sp Braga":1650.65,"Sp Lisbon":1788.6},"ESP":{"Alaves":1644.12,"Almeria":1544.16,"Ath Bilbao":1789.31,"Ath Madrid":1855.35,"Barcelona":1945.43,"Betis":1742.14,"Cadiz":1525.76,"Celta":1689.27,"Eibar":1529.63,"Elche":1569.98,"Espanol":1634.66,"Getafe":1625.76,"Girona":1637.03,"Granada":1537.0,"Huesca":1496.86,"La Coruna":1473.67,"Las Palmas":1563.5,"Leganes":1599.03,"Levante":1605.75,"Malaga":1448.7,"Mallorca":1641.25,"Osasuna":1697.22,"Oviedo":1574.9,"Real Madrid":1936.13,"Santander":1527.51,"Sevilla":1637.12,"Sociedad":1667.32,"Valencia":1679.42,"Valladolid":1467.33,"Vallecano":1658.48,"Villarreal":1785.55}}
ELO_ALIAS = {}   # nome football-data.co.uk -> nome ClubElo, da aggiungere a mano solo se elo_log.txt segnala un errore
def clubelo(day):
    err = None
    for base in ("http://api.clubelo.com/", "https://api.clubelo.com/"):
        try:
            rows = list(csv.DictReader(io.StringIO(get(base + day))))
            if rows and "Elo" in rows[0]: return rows
        except Exception as e:
            err = e
    print("skip Elo", day, err)
    return None
def elo_update():
    elo_path = os.path.join(OUT, "elo.csv"); log = []
    # squadre della stagione in corso (risultati + calendario)
    teams = set()
    for lg in LEAGUES:
        p = os.path.join(OUT, f"{lg}_{code(cur)}.csv")
        if os.path.exists(p):
            rd = list(csv.reader(open(p, encoding="utf-8")))
            if rd:
                h = rd[0]; ih, ia = h.index("HomeTeam") if "HomeTeam" in h else -1, h.index("AwayTeam") if "AwayTeam" in h else -1
                for r in rd[1:]:
                    if ih >= 0 and len(r) > max(ih, ia): teams.update([(lg, r[ih].strip()), (lg, r[ia].strip())])
    p = os.path.join(OUT, "next_fixtures.csv")
    if os.path.exists(p):
        for r in list(csv.reader(open(p, encoding="utf-8")))[1:]:
            if len(r) > 4 and r[0] in ELO_COUNTRY: teams.update([(r[0], r[3].strip()), (r[0], r[4].strip())])
    teams = {t for t in teams if t[1]}
    ref_rows = clubelo("2025-06-01")
    today_rows = clubelo(today.isoformat())
    if not today_rows:
        print("ClubElo non raggiungibile: elo.csv non aggiornato"); return
    names = {}
    for r in (ref_rows or []) + today_rows: names.setdefault(r["Country"], set()).add(r["Club"])
    mapping = {}
    for lg, t in sorted(teams):
        c = ELO_COUNTRY[lg]; cand = sorted(names.get(c, ()))
        if t in ELO_ALIAS: mapping[(lg, t)] = ELO_ALIAS[t]; log.append(f"{lg} {t} -> {ELO_ALIAS[t]} (a mano)"); continue
        v = ELO_REF.get(c, {}).get(t)
        if v is not None and ref_rows:
            hit = [r["Club"] for r in ref_rows if r["Country"] == c and abs(float(r["Elo"]) - v) < 0.01]
            if len(hit) == 1: mapping[(lg, t)] = hit[0]; log.append(f"{lg} {t} -> {hit[0]} (valore Elo 01/06/2025 identico)"); continue
        nt = norm(t); nm = {norm(x): x for x in cand}
        if nt in nm: mapping[(lg, t)] = nm[nt]; log.append(f"{lg} {t} -> {nm[nt]} (stesso nome)"); continue
        part = [x for k, x in nm.items() if re.search(r"\b" + re.escape(nt) + r"\b", k) or re.search(r"\b" + re.escape(k) + r"\b", nt)]
        if len(part) == 1: mapping[(lg, t)] = part[0]; log.append(f"{lg} {t} -> {part[0]} (nome contenuto) DA CONTROLLARE"); continue
        close = difflib.get_close_matches(nt, list(nm), n=2, cutoff=0.8)
        if len(close) == 1 or (len(close) == 2 and difflib.SequenceMatcher(None, nt, close[0]).ratio() - difflib.SequenceMatcher(None, nt, close[1]).ratio() > 0.1):
            mapping[(lg, t)] = nm[close[0]]; log.append(f"{lg} {t} -> {nm[close[0]]} (nome simile) DA CONTROLLARE"); continue
        log.append(f"{lg} {t} -> NON TROVATA (niente Elo: la Media dinamica usa la versione senza Elo)")
    # istantanee: 1 e 15 del mese dall'inizio della stagione + oggi; si scaricano solo quelle mancanti
    start = datetime.date(cur, 7, 1)
    days = []; d = start
    while d <= today:
        if d.day in (1, 15): days.append(d.isoformat())
        d += datetime.timedelta(days=1)
    days.append(today.isoformat())
    have = {}
    if os.path.exists(elo_path):
        for r in list(csv.reader(open(elo_path, encoding="utf-8")))[1:]:
            if len(r) == 4: have.setdefault(r[0], []).append(r)
    out = []
    for day in sorted(set(days)):
        got = {(r[1], r[2]) for r in have.get(day, [])}
        recent = (today - datetime.date.fromisoformat(day)).days <= 20
        if day in have and day != today.isoformat() and (set(mapping) <= got or not recent):
            out += have[day]; continue
        rows = today_rows if day == today.isoformat() else clubelo(day)
        if rows is None:
            out += have.get(day, []); continue
        by = {(r["Country"], r["Club"]): r["Elo"] for r in rows}
        for (lg, t), club in mapping.items():
            e = by.get((ELO_COUNTRY[lg], club))
            if e: out.append([day, lg, t, f"{float(e):.2f}"])
        time.sleep(1)
    with open(elo_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "div", "team", "elo"]); w.writerows(sorted(out))
    open(os.path.join(OUT, "elo_log.txt"), "w", encoding="utf-8").write("\n".join(log) + "\n")
    print("Elo:", len(mapping), "squadre collegate su", len(teams), "|", sum("NON TROVATA" in x for x in log), "non trovate")
try:
    elo_update()
except Exception as e:
    print("skip Elo", e)

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2)))
json.dump({"updated": now.strftime("%d/%m/%Y %H:%M"), "files": files},
          open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
print("ok", len(files), "file")
