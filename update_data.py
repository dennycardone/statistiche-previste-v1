"""Scarica da football-data.co.uk i CSV dei campionati della dashboard nella cartella data/.
Campionati europei: stagione corrente sempre, le 5 precedenti solo se mancano (servono per gli H2H).
"""
import datetime, json, os, urllib.request, urllib.parse, math, re

LEAGUES = ["I1", "I2", "E0", "SP1", "F1", "D1", "N1", "P1",
           "E1", "E2", "E3", "EC", "SC0", "SC1", "SC2", "SC3", "D2", "F2", "SP2", "B1", "T1", "G1"]
# campionati "extra" di football-data.co.uk (un file con tutte le stagioni, solo risultati e quote)
NEW_LEAGUES = ["ARG", "AUT", "BRA", "CHN", "DNK", "FIN", "IRL", "JPN", "MEX", "NOR", "POL", "ROU", "RUS", "SWE", "SWZ", "USA"]
# campionati solo su API-Football (ottobre 2026, squadre delle coppe europee): codice → (id API-Football, nome, stagione per anno solare).
# Statistiche partita nello storico 2024-2026: Serbia, Croazia, Cechia oltre il 95% delle partite; Ungheria,
# Israele, Bulgaria circa la metà (le partite senza statistiche restano vuote: niente stime).
API_ONLY = {"SRB": (286, "Super Liga", False), "CRO": (210, "HNL", False), "CZE": (345, "Czech Liga", False),
            "ISR": (383, "Ligat Ha'al", False),
            # 13/10/2026: Champions League come un campionato per la scheda partita (precedenti, classifica, rendimento, quote 1xBet);
            # solo fase principale (le qualificazioni di giugno-agosto restano fuori). Le previsioni vengono da data/ucl.json (tools/ucl_model.py).
            "UCL": (2, "Champions League", False), "UEL": (3, "Europa League", False)}   # 13/10/2026: anche l'Europa League
# esclusi (verifica 6/10/2026 sullo storico): Cipro (statistiche solo sul 22-35% delle partite 2024-2026), Bielorussia (nessuna statistica);
# Slovacchia e Ucraina tolte su richiesta (stagione 2026/27 quasi senza statistiche): i loro file vengono cancellati
# 26/10/2026: tolte anche Bulgaria (falli mancanti su tutte le partite lug-ott 2026, fuorigioco 0-0 sospetti) e Ungheria, su richiesta
# 26/10/2026 sera (Denny): tolti anche Israele, Scozia Championship e League One, Finlandia, Polonia, Romania, Serbia, Cina, Croazia.
# Un solo elenco: niente download, niente richieste API, niente quote; i loro file e le loro partite vengono cancellati.
REMOVED = {"SVK", "UKR", "BUL", "HUN", "ISR", "SC1", "SC2", "FIN", "POL", "ROU", "SRB", "CHN", "CRO"}
LEAGUES = [l for l in LEAGUES if l not in REMOVED]
NEW_LEAGUES = [l for l in NEW_LEAGUES if l not in REMOVED]
API_ONLY = {k: v for k, v in API_ONLY.items() if k not in REMOVED}
import glob as _g0
for _c in REMOVED:
    for _f in _g0.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", _c + ".csv")) + _g0.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", _c + "_*.csv")):
        try: os.remove(_f)
        except OSError: pass
BASE = "https://www.football-data.co.uk/mmz4281/{code}/{lg}.csv"
NEW = "https://www.football-data.co.uk/new/{lg}.csv"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)


def code(y):
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


_FD_FAIL = {}


def get(url):
    """24/10/2026: un giro del 22/10 è durato 48 minuti per i download lenti di football-data. Attesa massima 25 s per file e,
    dopo 4 errori di fila, il giro smette di scaricare e usa i file già salvati (rimane l'ultima versione buona, niente stime)."""
    host = urllib.parse.urlsplit(url).netloc
    if _FD_FAIL.get(host, 0) >= 4: raise RuntimeError(host + " non risponde in questo giro: tengo i file salvati")
    req = urllib.request.Request(url, headers={"User-Agent": "statistiche-previste/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            txt = r.read().decode("utf-8-sig", errors="replace")
    except Exception:
        _FD_FAIL[host] = _FD_FAIL.get(host, 0) + 1
        if _FD_FAIL[host] == 4: print("::warning title=Download lenti::" + host + ": 4 download falliti di fila, il giro usa i file già salvati")
        raise
    _FD_FAIL[host] = 0
    return txt


def save(name, txt):
    open(os.path.join(OUT, name), "w", encoding="utf-8").write(txt)


def jdump(obj, path):
    """19/10/2026: scrittura sicura degli archivi: prima un file temporaneo, poi lo scambio (un giro interrotto non lascia un file a metà)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh: json.dump(obj, fh, separators=(",", ":"), ensure_ascii=False)
    os.replace(tmp, path)


def jload_archive(path):
    """Archivio privato che non deve mai ripartire da vuoto: se manca → {} (primo giro); se c'è ma non si legge → il giro si ferma."""
    if not os.path.exists(path): return {}
    try: return json.load(open(path))
    except Exception as e:
        print(f"::error title=Archivio illeggibile::{os.path.basename(path)}: {e} — giro fermato, l'archivio non viene sovrascritto")
        raise SystemExit(1)


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
FD_RENAME = {"ROU": {"Din. Bucuresti": "Dinamo Bucuresti"}}
for lg in NEW_LEAGUES:
    name = f"{lg}.csv"
    try:
        txt = get(NEW.format(lg=lg))
        if "Home" in txt:
            rd = list(csv.reader(io.StringIO(txt)))
            hdr, body = rd[0], [r for r in rd[1:] if r]
            # 19/10/2026: football-data a volte cambia la grafia di una squadra a metà stagione (Romania, 9/10/2026: "Dinamo Bucuresti"
            # → "Din. Bucuresti"): la squadra si spezzava in due e la stessa partita compariva due volte. Un solo nome per squadra.
            ren = FD_RENAME.get(lg, {})
            if ren and "Home" in hdr and "Away" in hdr:
                iH_, iA_ = hdr.index("Home"), hdr.index("Away")
                for r in body:
                    if len(r) > max(iH_, iA_): r[iH_] = ren.get(r[iH_].strip(), r[iH_]); r[iA_] = ren.get(r[iA_].strip(), r[iA_])
            iS = hdr.index("Season") if "Season" in hdr else -1
            keep, seen_ = [], set()
            iD_ = hdr.index("Date") if "Date" in hdr else -1
            for r in body:
                try: y = int(str(r[iS]).strip()[:4]) if iS >= 0 else None
                except Exception: y = None
                if y is None or y >= today.year - 6:        # ultime stagioni, come per gli altri campionati
                    r[0] = lg                                # colonna Country = codice del campionato (l'app lo riconosce)
                    if ren and iD_ >= 0:                     # dopo il cambio di nome: la stessa partita una volta sola
                        kd_ = (r[iD_].strip(), r[iH_].strip(), r[iA_].strip())
                        if kd_ in seen_: continue
                        seen_.add(kd_)
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
    # richieste del giorno finite (o API momentaneamente giù): il piano resta a pagamento. Senza questo il giro cadeva sulle fonti
    # gratuite e toglieva dal calendario le partite di API-Football (8/10/2026). Calendario, risultati e statistiche si rifanno
    # dall'archivio già scaricato (data/apif.json), senza nuove richieste.
    if not AF_PRO:
        try:
            _od = json.load(open(os.path.join(OUT, "odds.json")))
            if _od.get("pro"): AF_PRO = True; print("API-Football: richieste non disponibili ora, uso l'archivio (piano a pagamento)")
        except Exception: pass
print("API-Football a pagamento:", AF_PRO)
print("::notice title=API-Football::a pagamento " + str(AF_PRO))
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
ESPN = {k: v for k, v in ESPN.items() if k not in REMOVED}
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
ESPN_STATS = {k: v for k, v in ESPN_STATS.items() if k not in REMOVED}
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
ESPN_RES = {k: v for k, v in ESPN_RES.items() if k not in REMOVED}
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
# Backtest 2024-2026: falli +1,5% di precisione con l'arbitro (tetto +4% nell'app dal 7/10/2026), cartellini +2,9% sulla media del campionato (probabilità di Poisson tarate).
AF_LEAGUES_X = {"I1": 135, "I2": 136, "E0": 39, "E1": 40, "E2": 41, "E3": 42, "EC": 43, "SP1": 140, "SP2": 141, "F1": 61, "F2": 62, "D1": 78, "D2": 79,
                "N1": 88, "P1": 94, "SC0": 179, "SC1": 180, "SC2": 183, "SC3": 184, "B1": 144, "T1": 203, "G1": 197, "ARG": 128, "AUT": 218, "BRA": 71,
                "CHN": 169, "DNK": 119, "FIN": 244, "IRL": 357, "JPN": 98, "MEX": 262, "NOR": 103, "POL": 106, "ROU": 283, "RUS": 235, "SWE": 113,
                "SWZ": 207, "USA": 253}
AF_LEAGUES_X.update({k: v[0] for k, v in API_ONLY.items()})
AF_LEAGUES_X = {k: v for k, v in AF_LEAGUES_X.items() if k not in REMOVED}
try:
    import apif_extra, glob as _glob, urllib.parse as _up
    _key = os.environ.get("APIFOOTBALL_KEY", "").strip()
    ap_path = os.path.join(OUT, "apif.json")
    AP = jload_archive(ap_path)
    AP.setdefault("partite", {}); AP.setdefault("agg", "")
    # storico dal ramo storico (scaricato dal workflow in storico/): al primo giro, poi per i campionati nuovi che l'archivio non ha
    _have = {v[1] for v in AP["partite"].values()}; _n0 = len(AP["partite"])
    for fn in _glob.glob(os.path.join(os.path.dirname(OUT), "storico", "*.json")):
        D = json.load(open(fn))
        if not isinstance(D, dict) or "lega" not in D or "partite" not in D: continue   # ucl_log.json e altri file non di archivio
        if D["lega"] in _have or D["lega"] not in AF_LEAGUES_X: continue   # coppe europee: solo per i backtest
        for fid, v in D["partite"].items(): AP["partite"].setdefault(fid, [v[0], D["lega"], v[1], v[2], v[3], v[4], v[5], v[6], v[7], "FT"])
    # 19/10/2026: Giappone, stagione speciale febbraio–giugno 2026 (J1 100 Year Vision League) assente nel file di football-data:
    # le partite arrivano dal ramo storico (API-Football) e add_results le aggiunge. Stagione "2025" nel file: è una mezza stagione a sé,
    # così non si mescola con la 2026-27 (classifica, partite in stagione); i modelli usano le date, non la stagione.
    GAP_FILL = {"JPN": (datetime.date(2026, 1, 1), datetime.date(2026, 7, 15), "2025")}
    for _lg in GAP_FILL:
        for fn in _glob.glob(os.path.join(os.path.dirname(OUT), "storico", _lg + "_*.json")):
            try: D = json.load(open(fn))
            except Exception: continue
            if not isinstance(D, dict) or D.get("lega") != _lg: continue
            for fid, v in D.get("partite", {}).items():
                if GAP_FILL[_lg][0].isoformat() <= v[0][:10] <= GAP_FILL[_lg][1].isoformat():
                    AP["partite"].setdefault(fid, [v[0], _lg, v[1], v[2], v[3], v[4], v[5], v[6], v[7], "FT" if v[3] is not None else "NS"])
    if len(AP["partite"]) > _n0: print("arbitri: dallo storico", len(AP["partite"]) - _n0, "partite")
    # 14/10/2026: in coda (indici 7-12) anche tiri in area/fuori area, bloccati, fuori porta, possesso e parate: arrivano nella stessa
    # risposta (nessuna richiesta in più), solo archivio per i test futuri. Le posizioni 0-6 non cambiano.
    KS_ = ["Total Shots", "Shots on Goal", "Corner Kicks", "Fouls", "Yellow Cards", "Red Cards", "expected_goals",
           "Shots insidebox", "Shots outsidebox", "Blocked Shots", "Shots off Goal", "Ball Possession", "Goalkeeper Saves", "Offsides"]   # 17/10: fuorigioco (indice 13)
    def _af(path, **q):
        req = urllib.request.Request("https://v3.football.api-sports.io/" + path + ("?" + _up.urlencode(q) if q else ""), headers={"x-apisports-key": _key})
        with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
        time.sleep(0.25); return d
    _now = datetime.datetime.now(ROME)
    try: _due = not AP["agg"] or (_now - datetime.datetime.strptime(AP["agg"], "%Y-%m-%d %H:%M").replace(tzinfo=ROME)).total_seconds() >= 50 * 60   # ogni giro (circa ogni ora)
    except Exception: _due = True
    if _key and (_due or os.environ.get("APIF_FORCE")):
        _sr = _af("status").get("response"); st_ = (_sr.get("requests") or {}) if isinstance(_sr, dict) else {}   # richieste finite: "response" è una lista vuota
        print("::notice title=API-Football richieste::" + (f"{st_.get('current')} su {st_.get('limit_day')} oggi" if st_ else "stato non disponibile (richieste finite?)"))
        if int(st_.get("limit_day", 100)) > 100:   # serve il piano a pagamento
            # 19/10/2026: meno richieste (prima ~80 a ogni aggiornamento, ~1.600 al giorno). Calendario completo di ogni campionato
            # (46 richieste) solo una volta al giorno; negli altri giri le partite per data (ieri, oggi, domani, dopodomani in UTC: 4 richieste,
            # tutti i campionati insieme). Statistiche di una partita finita: appena finita (ritentate fino a 3 giorni se API-Football non le ha
            # ancora), poi una volta 12 ore e una volta 36 ore dopo il calcio d'inizio (correzioni dei dati); le partite vecchie senza
            # statistiche non vengono più richieste ogni ora.
            _utc = datetime.datetime.now(datetime.timezone.utc)
            full = AP.get("agg_full", "")[:10] != _now.strftime("%Y-%m-%d") or not AP.get("stagioni") or bool(os.environ.get("APIF_FORCE"))
            ID2LG = {v: k for k, v in AF_LEAGUES_X.items()}
            need, n_new, n_req0 = [], 0, 0
            def _take(f, lg):
                fid = str(f["fixture"]["id"]); stt = f["fixture"]["status"]["short"]; old = AP["partite"].get(fid)
                base = [f["fixture"]["date"][:16], lg, f["teams"]["home"]["name"], f["teams"]["away"]["name"], f["goals"]["home"], f["goals"]["away"],
                        f["fixture"].get("referee") or (old[6] if old else None), old[7] if old else [None] * 7, old[8] if old else [None] * 7, stt]
                AP["partite"][fid] = base
                # 26/10/2026 (fase 0, dati "as-of"): quando abbiamo visto per la prima volta l'arbitro (prima della partita o dopo)
                if base[6] and not AP.setdefault("visto", {}).setdefault(fid, {}).get("ref"):
                    AP["visto"][fid]["ref"] = _utc.strftime("%Y-%m-%dT%H:%M"); AP["visto"][fid]["ko"] = base[0]
                for side_ in ("home", "away"):   # loghi delle squadre (immagini gratuite di API-Football, non consumano richieste)
                    if f["teams"][side_].get("logo"): AP.setdefault("loghi", {}).setdefault(lg, {})[f["teams"][side_]["name"]] = f["teams"][side_]["logo"]
                if stt not in ("FT", "AET", "PEN"): return
                ko = datetime.datetime.fromisoformat(base[0] + ":00+00:00"); age = (_utc - ko).total_seconds() / 3600
                last = AP.setdefault("stats_at", {}).get(fid)
                if base[7][4] is None: due = age <= 72                       # statistiche non ancora arrivate
                else: due = any(age >= m and (not last or last < (ko + datetime.timedelta(hours=m)).strftime("%Y-%m-%dT%H:%M")) for m in (12, 36) if age <= m + 24)
                if due: need.append(fid)
            if full:
                cur_season = {}
                for x in _af("leagues", current="true").get("response", []):
                    for ss in x.get("seasons", []):
                        if ss.get("current"): cur_season[x["league"]["id"]] = ss["year"]
                n_req0 += 1
                for lg, lid in AF_LEAGUES_X.items():
                    sy = cur_season.get(lid)
                    if not sy: continue
                    for f in _af("fixtures", league=lid, season=sy).get("response", []): _take(f, lg)
                    n_req0 += 1
                AP["stagioni"] = {str(k): v for k, v in cur_season.items()}; AP["agg_full"] = _now.strftime("%Y-%m-%d %H:%M")
            else:
                SY = {int(k): v for k, v in AP["stagioni"].items()}
                for k in (-1, 0, 1, 2):
                    for f in _af("fixtures", date=(_utc.date() + datetime.timedelta(days=k)).isoformat()).get("response", []):
                        lid = f["league"]["id"]
                        if lid in ID2LG and f["league"].get("season") == SY.get(lid): _take(f, ID2LG[lid])
                    n_req0 += 1
            def _stat(t, k):
                for s_ in t.get("statistics", []):
                    if s_["type"] == k:
                        v = s_["value"]
                        if v is None: return 0 if k in ("Yellow Cards", "Red Cards") else None
                        try: return float(str(v).replace("%", ""))
                        except Exception: return None
                return None
            n_req1 = 0
            for i in range(0, min(len(need), 2000), 20):
                n_req1 += 1
                for f in _af("fixtures", ids="-".join(need[i:i + 20])).get("response", []):
                    fid = str(f["fixture"]["id"]); stt_ = {t["team"]["id"]: t for t in f.get("statistics", [])}
                    H, A = stt_.get(f["teams"]["home"]["id"], {}), stt_.get(f["teams"]["away"]["id"], {})
                    x = AP["partite"].get(fid)
                    if x and H and A:   # risposta senza statistiche: restano quelle che c'erano (non si cancellano)
                        x[7] = [_stat(H, k) for k in KS_]; x[8] = [_stat(A, k) for k in KS_]; n_new += 1
                        AP["stats_at"][fid] = _utc.strftime("%Y-%m-%dT%H:%M")
                        AP.setdefault("visto", {}).setdefault(fid, {}).setdefault("st", _utc.strftime("%Y-%m-%dT%H:%M"))
            _old = (_utc - datetime.timedelta(days=10)).strftime("%Y-%m-%dT%H:%M")
            AP["stats_at"] = {k: v for k, v in AP.get("stats_at", {}).items() if v >= _old}
            print(f"::notice title=API-Football · aggiornamento partite::{'calendario completo' if full else 'partite per data'}: {n_req0} richieste · statistiche: {len(need)} partite, {n_req1} richieste")
            AP["agg"] = _now.strftime("%Y-%m-%d %H:%M")
            print("arbitri: aggiornate", n_new, "statistiche,", len(AP["partite"]), "partite in archivio")
            _nx = sum(1 for v in AP["partite"].values() if v[7] and len(v[7]) > 7 and v[7][7] is not None)
            print(f"::notice title=Statistiche in più (tiri in area, bloccati, possesso)::{_nx} partite in archivio")
        for _k in [k for k, v in AP["partite"].items() if v[1] in REMOVED]: del AP["partite"][_k]   # campionati tolti
        jdump(AP, ap_path)
    # conteggio delle partite con le statistiche in più (tiri in area, bloccati, possesso, parate) a ogni giro: solo il numero, per verificare i nomi dei campi
    QUAL["stat_extra"] = {"partite": sum(1 for v in AP["partite"].values() if v[7] and len(v[7]) > 7 and v[7][7] is not None),
                          "fuorigioco": sum(1 for v in AP["partite"].values() if v[7] and len(v[7]) > 13 and v[7][13] is not None and v[8] and len(v[8]) > 13 and v[8][13] is not None), "archivio": AP.get("agg")}
    # campionati solo su API-Football: file dell'app costruito dall'archivio (stesse colonne dei file "new" di football-data)
    for lg_, (lid_, nm_, cal_) in API_ONLY.items():
        try:
            _src = AP["partite"].values() if lg_ not in ("UCL", "UEL") else [v for v in AP["partite"].values() if v[1] == lg_ and v[0][5:7] not in ("06", "07", "08")]   # coppe: senza qualificazioni
            rows_ = apif_extra.build_csv(lg_, nm_, _src, cal_, ROME, today.year - 6)
            if len(rows_) > 1:
                buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(rows_); save(f"{lg_}.csv", buf.getvalue())
                if f"{lg_}.csv" not in files: files.append(f"{lg_}.csv")
                print("campionato API-Football", lg_, len(rows_) - 1, "partite")
        except Exception as e_: print("campionato API-Football", lg_, e_)
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
    # campionati tolti (Slovacchia, Ucraina): fuori dall'archivio, così non tornano nel calendario e nel controllo qualità
    for _k in [k for k, v in AP["partite"].items() if v[1] in REMOVED]: del AP["partite"][_k]
    by_lg = collections.defaultdict(list)
    for v in AP["partite"].values():
        if v[1] in AF_LEAGUES_X: by_lg[v[1]].append(v)   # solo i campionati dell'app
    MAPS = {}
    for lg, L in by_lg.items():
        L.sort(key=lambda v: v[0])
        MAPS[lg] = apif_extra.learn_map([(datetime.date.fromisoformat(v[0][:10]), v[2], v[3], v[4], v[5]) for v in L if v[9] in ("FT", "AET", "PEN")], ours.get(lg, []), lg)
        # 13/10/2026: campionati solo API-Football (e coppe): i nostri nomi SONO quelli di API-Football. Una squadra con meno di 2 partite
        # già abbinate (es. esordienti in Champions: Sabah, Viking, Como…) restava senza nome → partita fuori dal calendario e senza quote
        if lg in API_ONLY:
            for v in L: MAPS[lg].setdefault(v[2], v[2]); MAPS[lg].setdefault(v[3], v[3])
    # 25/10/2026 · Prevista 2.0, fase 1-B: formazioni ufficiali → correzione dei falli attesi. Test walk-forward (tools/p2/test1a.py,
    # 44.000 partite dal 2023): 1X2 falli −0,0053 di log-loss nella verifica (lug 2024 – giu 2025) e −0,0057 nell'holdout (da lug 2025),
    # migliori in 35/42 e 39/44 campionati. Per ogni squadra: falli attesi × e^(0,368·falli fatti dei suoi titolari + 0,377·falli subiti
    # dei titolari avversari − 0,030·cartellini dei suoi titolari), ognuno come log(somma dei valori dei titolari di oggi / somma abituale
    # della squadra). Valori dei giocatori: ramo valori (tools/valori_giocatori.py, ogni sera). Formazioni: fixtures/lineups di API-Football
    # per le partite che iniziano entro 80 minuti (una richiesta a partita, ritentata al giro dopo se non sono ancora uscite).
    try:
        import xi_corr
        _VP = os.path.join(os.path.dirname(OUT), "valori", "valori.json"); _XP = os.path.join(OUT, "xi.json")
        XI = json.load(open(_XP)) if os.path.exists(_XP) else {}
        # 26/10/2026: formazioni prese dal micro-processo (formazioni_live.yml, ogni 10 minuti, ramo xi): si uniscono a quelle di questo giro
        _XL = os.path.join(os.path.dirname(OUT), "xi_live", "xi.json")
        if os.path.exists(_XL):
            try:
                for fid, x in json.load(open(_XL)).get("xi", {}).items(): XI.setdefault(fid, {k: x[k] for k in ("t", "hid", "aid", "h", "a")})
            except Exception as e_: print("::warning title=Formazioni ufficiali::ramo xi non letto: " + str(e_)[:120])
        FORMZ, W_XI, _nxi, _DX, _KO, _NEXT = {}, xi_corr.W_XI, 0, [], {}, []   # _DX: esito di ogni tentativo (diagnosi nell'avviso)
        _nowu = datetime.datetime.now(datetime.timezone.utc)
        if os.path.exists(_VP):
            _V = json.load(open(_VP))
            for fid, v in AP["partite"].items():
                if v[1] not in AF_LEAGUES_X: continue
                ko = datetime.datetime.fromisoformat(v[0] + ":00+00:00"); mins = (ko - _nowu).total_seconds() / 60
                h, a = MAPS.get(v[1], {}).get(v[2]), MAPS.get(v[1], {}).get(v[3])
                d_ = ko.astimezone(ROME).date().isoformat()
                # elenco per il micro-processo: partite non iniziate delle prossime 36 ore con i nostri nomi (id API-Football, nessuna quota)
                if v[9] == "NS" and -10 < mins <= 36 * 60 and h and a and v[1] != "EC":   # 28/10/2026: National League senza statistiche né formazioni
                    _NEXT.append({"fid": fid, "lg": v[1], "ko": ko.strftime("%Y-%m-%dT%H:%M"), "d": d_, "h": h, "a": a, "ha": v[2], "aa": v[3]})
                # riserva: il micro-processo di solito le prende prima; qui solo da 50 minuti prima del fischio
                if fid not in XI and v[9] == "NS" and -10 < mins <= 50 and _key and _nxi < 80 and v[1] != "EC":
                    try:
                        R = _af("fixtures/lineups", fixture=fid).get("response") or []; _nxi += 1
                        got, why = xi_corr.parse_lineups(R, v[2], v[3])
                        if got:
                            XI[fid] = {"t": _nowu.strftime("%Y-%m-%d %H:%M"), "hid": got[0], "aid": got[1], "h": got[2], "a": got[3]}
                            _DX.append(f"{v[2]}–{v[3]} ({mins:.0f}′ prima): presa")
                        else: _DX.append(f"{v[2]}–{v[3]} ({mins:.0f}′ prima): {why}")
                    except Exception as e_: _DX.append(f"{v[2]}–{v[3]}: errore {str(e_)[:80]}")
                x = XI.get(fid)
                if not x or mins < -180: continue
                if not h or not a: _DX.append(f"{v[2]}–{v[3]}: nomi non abbinati ai nostri"); continue
                c_, why = xi_corr.corr(x, _V)
                if not c_: _DX.append(f"{v[2]}–{v[3]}: {why}"); continue
                k_ = f"{v[1]}|{d_}|{h}|{a}"; _KO[k_] = ko.strftime("%Y-%m-%d %H:%M")
                FORMZ[k_] = {"fh": c_[0], "fa": c_[1], "ora": x["t"], "xi": xi_corr.entry(x)}
            # 27/10/2026: rapporto delle ultime 24 ore. Per ogni partita iniziata dei nostri campionati: formazione presa prima del fischio
            # (con quanti minuti di anticipo) o mancata. Avviso se ne manca più di 1 su 10.
            _pres, _mis = [], []
            for fid, v in AP["partite"].items():
                if v[1] not in AF_LEAGUES_X or v[1] in ("UCL", "UEL", "EC"): continue   # EC: API-Football non dà le formazioni della National League
                ko = datetime.datetime.fromisoformat(v[0] + ":00+00:00"); ago = (_nowu - ko).total_seconds() / 60
                if not (10 <= ago <= 24 * 60) or v[9] in ("NS", "TBD", "PST", "CANC", "ABD", "AWD", "WO"): continue
                x = XI.get(fid); nm_ = f"{v[1]} {v[2]}–{v[3]}"
                if x and x["t"] < ko.strftime("%Y-%m-%d %H:%M"): _pres.append((ko - datetime.datetime.strptime(x["t"], "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc)).total_seconds() / 60)
                else: _mis.append(nm_ + (" (presa dopo il fischio)" if x else ""))
            _nt = len(_pres) + len(_mis)
            QUAL["formazioni"] = {"partite_24h": _nt, "prese_prima": len(_pres), "anticipo_medio_min": round(sum(_pres) / len(_pres)) if _pres else None, "mancate": _mis[:30]}
            if _nt: print(f"::{'warning' if len(_mis) > 0.1 * _nt else 'notice'} title=Formazioni · ultime 24 ore::prese prima del fischio {len(_pres)} su {_nt}"
                          + (f" (in media {round(sum(_pres) / len(_pres))} minuti prima)" if _pres else "") + (" · mancate: " + "; ".join(_mis[:12]) if _mis else ""))
            for k_ in [k_ for k_, x in XI.items() if (_nowu - datetime.datetime.strptime(x["t"], "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc)).days > 3]: del XI[k_]
        jdump(sorted(_NEXT, key=lambda r: r["ko"]), os.path.join(OUT, "prossime.json"))
        jdump(XI, _XP)
        jdump({"pesi": W_XI, "partite": FORMZ}, os.path.join(OUT, "formazioni.json"))
        # archivio privato delle correzioni (mai pubblicato, mai sfoltito): serve allo studio Quota 2 / Quota 3 "statistiche + formazioni"
        _HP = os.path.join(OUT, "formazioni_hist.json"); _FH = json.load(open(_HP)) if os.path.exists(_HP) else {}
        for k_, x in FORMZ.items():   # solo formazioni prese prima del fischio (dati noti prima della partita)
            if x["ora"] < _KO.get(k_, ""): _FH[k_] = {"fh": x["fh"], "fa": x["fa"], "ora": x["ora"]}
        jdump(_FH, _HP)
        print("::notice title=Formazioni ufficiali::" + f"{len(FORMZ)} partite con la correzione dei falli, {_nxi} richieste" + ("" if os.path.exists(_VP) else " (valori dei giocatori non disponibili)")
              + (" · " + " · ".join(_DX[:12]) if _DX else ""))
    except Exception as e_: print("::warning title=Formazioni ufficiali::" + str(e_))
    # 28/10/2026 (Denny): archivio privato di infortunati e squalificati (API-Football "injuries"), con l'ORA in cui li vediamo. Serve a
    # testarli tra qualche mese come qualsiasi variabile (solo informazioni note prima del fischio: per ogni giocatore la prima e l'ultima
    # volta vista). Ogni 3 ore, partite di oggi e domani dei nostri campionati: 2-4 richieste. Mai pubblicato; nella copia cifrata.
    try:
        _IP = os.path.join(OUT, "infortuni_hist.json"); INJ = json.load(open(_IP)) if os.path.exists(_IP) else {"agg": "", "partite": {}}
        _nowu2 = datetime.datetime.now(datetime.timezone.utc); _ts2 = _nowu2.strftime("%Y-%m-%d %H:%M")
        _due2 = not INJ.get("agg") or (_nowu2 - datetime.datetime.strptime(INJ["agg"], "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc)).total_seconds() >= 3 * 3600 - 300
        if _key and _due2:
            _ids2 = {v: k for k, v in AF_LEAGUES_X.items() if k != "EC"}; _nr2 = _np2 = _ng2 = 0
            for _k2 in (0, 1):
                _d2 = (datetime.datetime.now(ROME).date() + datetime.timedelta(days=_k2)).isoformat(); _pg, _pgs = 1, 1
                while _pg <= _pgs and _nr2 < 8:
                    R_ = _af("injuries", date=_d2, page=_pg) if _pg > 1 else _af("injuries", date=_d2); _nr2 += 1
                    _pgs = (R_.get("paging") or {}).get("total", 1) or 1; _pg += 1
                    for it in R_.get("response") or []:
                        lg_ = _ids2.get((it.get("league") or {}).get("id")); fx_ = (it.get("fixture") or {}).get("id"); pl_ = it.get("player") or {}
                        if not lg_ or not fx_ or not pl_.get("id"): continue
                        P_ = INJ["partite"].setdefault(str(fx_), {"lg": lg_, "ko": ((it.get("fixture") or {}).get("date") or "")[:16], "g": {}})
                        g_ = P_["g"].get(str(pl_["id"]))
                        if not g_:
                            P_["g"][str(pl_["id"])] = {"n": pl_.get("name"), "sq": (it.get("team") or {}).get("id"), "tipo": pl_.get("type"), "motivo": pl_.get("reason"), "prima": _ts2, "ultima": _ts2}; _ng2 += 1
                        else: g_["ultima"] = _ts2; g_["tipo"] = pl_.get("type") or g_.get("tipo")
                        _np2 += 1
            INJ["agg"] = _ts2
            _lim2 = (_nowu2 - datetime.timedelta(days=400)).strftime("%Y-%m-%d")
            INJ["partite"] = {k: v for k, v in INJ["partite"].items() if (v.get("ko") or "9")[:10] >= _lim2}
            jdump(INJ, _IP)
            print("::notice title=Infortunati e squalificati::" + f"{_nr2} richieste · {_np2} segnalazioni nei nostri campionati (nuove {_ng2}) · archivio {len(INJ['partite'])} partite")
    except Exception as e_: print("::warning title=Infortunati e squalificati::" + str(e_)[:200])
    try:   # 26/10/2026 (fase 0): fiducia degli abbinamenti dei nomi API-Football → nostri
        _low = [f"{lg_} {k}→{x['nostro']} ({x['voti']} voti)" for lg_, D_ in apif_extra.CONF.items() for k, x in D_["abbinati"].items() if x["fiducia"] == "bassa"]
        _un = [f"{lg_} {k} ({x['partite']} partite): {x['diagnosi']}" for lg_, D_ in apif_extra.CONF.items() for k, x in D_["non_abbinati"].items() if x.get("recenti")]   # solo squadre con partite negli ultimi 200 giorni
        QUAL["nomi"] = {"fiducia_bassa": _low[:40], "non_abbinati": _un[:40],
                        "abbinati": sum(len(D_["abbinati"]) for D_ in apif_extra.CONF.values())}
        print("::notice title=Abbinamento nomi::" + f"{QUAL['nomi']['abbinati']} nomi abbinati · fiducia bassa {len(_low)} · non abbinati {len(_un)}" + (": " + "; ".join(_un[:12]) if _un else ""))
    except Exception as e_: print("::warning title=Abbinamento nomi::" + str(e_))
    # 18/10/2026: fuorigioco per squadra (data/fuorigioco.json, per il modello fuorigioco dell'app). Fonti: ramo statextra (storico dal 2022,
    # recuperato da tools/extra_stats_apifootball.py) e archivio giornaliero (indice 13). API-Football registra lo 0-0 di fuorigioco come null per
    # entrambe le squadre: un doppio null diventa 0-0 SOLO se (a) nella partita ci sono tiri in area o possesso, (b) nelle ultime 20 partite del
    # campionato con statistiche avanzate dei giorni precedenti i fuorigioco erano valorizzati in almeno 15, (c) nelle ultime 200 partite valorizzate
    # dei giorni precedenti lo 0-0 scritto in chiaro è sotto l'1% (altrimenti il doppio null è un dato mancante). Solo dati passati.
    try:
        _SX = {}
        for _fn in _glob.glob(os.path.join(os.path.dirname(OUT), "statextra", "*.json")):
            _lgx = os.path.basename(_fn)[:-5]
            for _fid, _r in json.load(open(_fn)).items():
                if _r[3] and _r[4] and len(_r[3]) > 13: _SX[_fid] = (_lgx, _r[0], _r[1], _r[2], _r[3], _r[4])
        for _fid, _v in AP["partite"].items():
            if _v[9] in ("FT", "AET", "PEN") and _v[7] and _v[8] and len(_v[7]) > 13 and len(_v[8]) > 13: _SX[_fid] = (_v[1], _v[0], _v[2], _v[3], _v[7], _v[8])
        _OFF = collections.defaultdict(list); _nd = collections.Counter()
        _bylg = collections.defaultdict(list)
        for _x in _SX.values(): _bylg[_x[0]].append(_x)
        for _lg, _L in _bylg.items():
            if _lg not in MAPS or _lg in ("UCL", "UEL", "UECL"): continue
            _mp = MAPS[_lg]; _L.sort(key=lambda z: z[1]); _l20 = collections.deque(maxlen=20); _l200 = collections.deque(maxlen=200); _i = 0
            while _i < len(_L):
                _j = _i
                while _j < len(_L) and _L[_j][1][:10] == _L[_i][1][:10]: _j += 1
                _upd = []
                for _x in _L[_i:_j]:
                    _H, _A = _x[4], _x[5]; _adv = _H[7] is not None or _H[11] is not None; _oh, _oa = _H[13], _A[13]
                    if _oh is None and _oa is None and _adv:
                        _cov = len(_l20) >= 15 and sum(_l20) >= 15; _expl = len(_l200) >= 50 and sum(_l200) / len(_l200) >= 0.01
                        if _cov and not _expl: _oh, _oa = 0.0, 0.0; _nd["0-0 da doppio null"] += 1
                    if _oh is not None and _oa is not None and _x[1][:10] >= "2023-07-01":
                        _h, _a = _mp.get(_x[2]), _mp.get(_x[3])
                        if _h and _a:
                            _loc = datetime.datetime.fromisoformat(_x[1][:16] + ":00+00:00").astimezone(ROME).strftime("%Y-%m-%d")
                            _OFF[_lg].append([_loc, _h, _a, int(_oh), int(_oa)])
                    if _adv: _upd.append((_H[13] is not None and _A[13] is not None, _H[13] == 0 and _A[13] == 0))
                for _has, _z in _upd:
                    _l20.append(1 if _has else 0)
                    if _has: _l200.append(1 if _z else 0)
                _i = _j
        json.dump({"campionati": _OFF}, open(os.path.join(OUT, "fuorigioco.json"), "w"), separators=(",", ":"), ensure_ascii=False)
        # 18/10/2026: tiri in area e tiri in porta per squadra (data/tiri_area.json) per la qualità dei tiri nel modello gol: solo valori reali
        # di entrambe le squadre (nessuna regola sui null), dalla stagione 2023-24
        _TA = collections.defaultdict(list)
        for _lg, _L in _bylg.items():
            if _lg not in MAPS or _lg in ("UCL", "UEL", "UECL"): continue
            for _x in _L:
                _H, _A = _x[4], _x[5]
                if _x[1][:10] < "2023-07-01" or None in (_H[7], _A[7], _H[1], _A[1]): continue
                _h, _a = MAPS[_lg].get(_x[2]), MAPS[_lg].get(_x[3])
                if _h and _a:
                    _loc = datetime.datetime.fromisoformat(_x[1][:16] + ":00+00:00").astimezone(ROME).strftime("%Y-%m-%d")
                    _TA[_lg].append([_loc, _h, _a, int(_H[7]), int(_A[7]), int(_H[1]), int(_A[1])])
        json.dump({"campionati": _TA}, open(os.path.join(OUT, "tiri_area.json"), "w"), separators=(",", ":"), ensure_ascii=False)
        print("tiri_area.json:", len(_TA), "campionati,", sum(len(v) for v in _TA.values()), "partite")
        QUAL["fuorigioco"] = {"campionati": len(_OFF), "partite": sum(len(v) for v in _OFF.values()), "da_doppio_null": _nd["0-0 da doppio null"]}
        print("fuorigioco.json:", len(_OFF), "campionati,", sum(len(v) for v in _OFF.values()), "partite")
    except Exception as e_:
        import traceback; traceback.print_exc(); print("::warning title=Fuorigioco::non calcolati: " + str(e_))
    # loghi con i nostri nomi di squadra (data/loghi.json): prima API-Football, poi gli stemmi di football-data.org
    try:
        _cr = json.load(open(os.path.join(OUT, "crests.json"))).get("teams", {}) if os.path.exists(os.path.join(OUT, "crests.json")) else {}
        LOGHI = {}
        for lg_, dd_ in AP.get("loghi", {}).items():
            mp_ = MAPS.get(lg_, {}); our_ = {t for v in ours.get(lg_, []) for t in (v[1], v[2])}
            for nm_, url_ in dd_.items():
                t_ = mp_.get(nm_) or (nm_ if nm_ in our_ else None)
                if t_: LOGHI.setdefault(lg_, {})[t_] = url_
        for lg_, dd_ in _cr.items():
            for t_, url_ in dd_.items(): LOGHI.setdefault(lg_, {}).setdefault(t_, url_)
        json.dump(LOGHI, open(os.path.join(OUT, "loghi.json"), "w"), separators=(",", ":"), ensure_ascii=False)
        print("loghi:", sum(len(v) for v in LOGHI.values()), "squadre in", len(LOGHI), "campionati")
    except Exception as e_: print("loghi saltati:", e_)
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
    if apif_extra.FIXED:
        print("risultati corretti con API-Football:", apif_extra.FIXED)
        QUAL["risultati_corretti"] = apif_extra.FIXED[:50]
    if AF_PRO:
        # risultati: partite giocate che API-Football ha e i nostri file non ancora (fonte principale per i risultati del giorno)
        n_res = 0
        for lg in by_lg:
            fn = f"{lg}_{code(cur)}.csv" if lg in LEAGUES else f"{lg}.csv"
            if fn not in files: continue
            try:
                rd = list(csv.reader(io.StringIO(open(os.path.join(OUT, fn), encoding="utf-8-sig").read())))
                rd2, k = apif_extra.add_results(rd, lg, by_lg[lg], MAPS[lg], _now.date(), ROME, gap=GAP_FILL.get(lg))
                if k:
                    buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(rd2); save(fn, buf.getvalue()); n_res += k
            except Exception as e:
                print("risultati API", fn, e)
        print("risultati da API-Football:", n_res, "partite aggiunte")
        # partite giocate solo come le dà API-Football: data e ora italiane, niente partite che API-Football non ha
        for lg in by_lg:
            fn = f"{lg}_{code(cur)}.csv" if lg in LEAGUES else f"{lg}.csv"
            if fn not in files: continue
            try:
                rd = list(csv.reader(io.StringIO(open(os.path.join(OUT, fn), encoding="utf-8-sig").read())))
                rd2, k = apif_extra.align_api(rd, lg, by_lg[lg], MAPS[lg], _now.date(), ROME)
                if k:
                    buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(rd2); save(fn, buf.getvalue())
                    hdr_ = [h.strip() for h in rd2[0]]; new_ = "HomeTeam" not in hdr_
                    for r in rd2[1:]:   # date nuove anche per gli abbinamenti successivi (cartellini, quote)
                        try: pairs[(lg, r[hdr_.index("Home" if new_ else "HomeTeam")].strip(), r[hdr_.index("Away" if new_ else "AwayTeam")].strip())].append(datetime.datetime.strptime(r[hdr_.index("Date")].strip(), "%d/%m/%Y").date())
                        except Exception: pass
            except Exception as e:
                print("allineamento API", fn, e)
        print("::notice title=Allineamento API-Football::date corrette " + str(apif_extra.ALIGNED["date"]) + ", partite tolte (non su API-Football) " + str(len(apif_extra.ALIGNED["tolte"])) + (": " + "; ".join(apif_extra.ALIGNED["tolte"][:20]) if apif_extra.ALIGNED["tolte"] else ""))
        QUAL["partite_non_api"] = apif_extra.ALIGNED["tolte"][:50]
        # controllo: ogni partita finita negli ultimi 14 giorni (API-Football) deve essere nei nostri risultati; altrimenti avviso
        try:
            _pl = collections.defaultdict(list)
            for fn in files:
                if "fixtures" in fn or not fn.endswith(".csv"): continue
                lgf = fn.split("_")[0].split(".")[0]
                for r in csv.DictReader(io.StringIO(open(os.path.join(OUT, fn), encoding="utf-8-sig").read())):
                    h, a = (r.get("HomeTeam") or r.get("Home") or "").strip(), (r.get("AwayTeam") or r.get("Away") or "").strip()
                    g1 = (r.get("FTHG") or r.get("HG") or "").strip()
                    try: dd = r["Date"].strip().split("/"); y = dd[2] if len(dd[2]) == 4 else "20" + dd[2]; d = datetime.date(int(y), int(dd[1]), int(dd[0]))
                    except Exception: continue
                    if g1.isdigit(): _pl[(lgf, h, a)].append(d)
            _miss = []
            for lg, L in by_lg.items():
                for v in L:
                    if v[9] not in ("FT", "AET", "PEN") or (lg in ("UCL", "UEL") and v[0][5:7] in ("06", "07", "08")): continue
                    d = datetime.datetime.fromisoformat(v[0] + ":00+00:00").astimezone(ROME).date()
                    if not (_now.date() - datetime.timedelta(days=14) <= d <= _now.date()): continue
                    h, a = MAPS[lg].get(v[2]), MAPS[lg].get(v[3])
                    if not h or not a:
                        _U = apif_extra.CONF.get(lg, {}).get("non_abbinati", {})
                        if any(str((_U.get(x) or {}).get("diagnosi", "")).startswith("squadra di passaggio") for x in (v[2], v[3]) if not MAPS[lg].get(x)): continue   # 26/10/2026: spareggi con squadre di un'altra serie (es. PK-35): non sono partite del campionato
                        _miss.append(f"{lg} {d:%d/%m} {v[2]}-{v[3]} (nomi non abbinati)"); continue
                    if not any(abs((x - d).days) <= 3 for x in _pl.get((lg, h, a), [])): _miss.append(f"{lg} {d:%d/%m} {h}-{a}")
            QUAL["giocate_mancanti"] = _miss
            print("::" + ("warning" if _miss else "notice") + " title=Partite giocate mancanti::" + (str(len(_miss)) + ": " + "; ".join(_miss[:25]) if _miss else "nessuna"))
        except Exception as e_: print("::warning title=Partite giocate mancanti::controllo saltato: " + str(e_))
        # calendario: prossime 3 settimane da API-Football (data e ora italiane); squadre non riconosciute → partita scartata
        LIVE_ST = ("1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP")   # in corso o sospese
        cal, unk = [["Div", "Date", "Time", "HomeTeam", "AwayTeam", "Round"]], set()
        for lg, L in by_lg.items():
            for v in L:
                # anche le partite in corso (1H, HT, 2H…): prima sparivano dalla lista finché non finivano
                if v[9] not in ("NS", "TBD") + LIVE_ST or (lg in ("UCL", "UEL") and v[0][5:7] in ("06", "07", "08")): continue   # coppe: senza qualificazioni
                loc = datetime.datetime.fromisoformat(v[0] + ":00+00:00").astimezone(ROME)
                if not (_now.date() <= loc.date() <= _now.date() + datetime.timedelta(days=21)): continue
                h, a = MAPS[lg].get(v[2]), MAPS[lg].get(v[3])
                if not h or not a: unk.update(x for x, y in ((v[2], h), (v[3], a)) if not y); continue
                cal.append([lg, loc.strftime("%d/%m/%Y"), "" if v[9] == "TBD" else loc.strftime("%H:%M"), h, a, ""])
        # rete di sicurezza: una partita del calendario del giro prima (oggi o dopo) che ora manca torna dentro, a meno che
        # API-Football la dia giocata, rinviata o annullata, o spostata a un'altra data; avviso con l'elenco per capire la causa
        try:
            _mem_p = os.path.join(OUT, "cal_prev.json")
            _prev = json.load(open(_mem_p)) if os.path.exists(_mem_p) else []
            _now_k = {(r[0], r[3], r[4]) for r in cal[1:]}
            _gone = set()
            for lg, L in by_lg.items():
                for v in L:
                    h, a = MAPS[lg].get(v[2]), MAPS[lg].get(v[3])
                    if h and a and v[9] not in ("NS", "TBD") + LIVE_ST: _gone.add((lg, h, a, v[0][:10]))
            _back = []
            for r in _prev:
                try: d_ = datetime.datetime.strptime(r[1], "%d/%m/%Y").date()
                except Exception: continue
                ren_ = FD_RENAME.get(r[0], {}); r = list(r); r[3] = ren_.get(r[3], r[3]); r[4] = ren_.get(r[4], r[4])   # squadra rinominata (19/10/2026)
                if d_ < _now.date() or (r[0], r[3], r[4]) in _now_k or r[0] in REMOVED: continue   # campionati tolti
                _cur_t = set(MAPS.get(r[0], {}).values())
                if _cur_t and (r[3] not in _cur_t or r[4] not in _cur_t): continue   # nome che il campionato non usa più: non rimetterla
                if any(g[:3] == (r[0], r[3], r[4]) and abs((datetime.date.fromisoformat(g[3]) - d_).days) <= 2 for g in _gone): continue
                if any(o[1] == r[3] and o[2] == r[4] and abs((o[0] - d_).days) <= 3 for o in ours.get(r[0], [])): continue   # già giocata
                cal.append(r); _back.append(f"{r[0]} {r[1]} {r[3]}-{r[4]}")
            if _back: print("::warning title=Calendario::rimesse " + str(len(_back)) + " partite sparite: " + "; ".join(_back[:15]))
            json.dump(cal[1:], open(_mem_p, "w"), ensure_ascii=False)
        except Exception as e_: print("::warning title=Calendario::rete di sicurezza saltata: " + str(e_))
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
            # 9/10/2026: calendario SOLO da API-Football per tutti i campionati che API-Football copre (niente ESPN né football-data)
            keep = [rd[0]] + [r for r in rd[1:] if len(r) > 4 and r[0] not in by_lg and r[0] not in api_lg]
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
    # cartellini: modello v2 (cards_model.py) su tutti i campionati insieme (gli arbitri dirigono in più campionati dello stesso paese);
    # pesi stimati mese per mese con le sole partite precedenti, conservati in data/cards_model.json
    CMP = {}
    try:
        import cards_model
        _cm_path = os.path.join(OUT, "cards_model.json")
        try: _cm = json.load(open(_cm_path))
        except Exception: _cm = {}
        _ms, _keys = [], []
        for lg, L in by_lg.items():
            for v in L:
                H, A = v[7], v[8]; played = v[9] in ("FT", "AET", "PEN") and H[4] is not None and A[4] is not None
                _ms.append(dict(lg=lg, d=v[0], h=v[2], a=v[3], ref=v[6], hc=(H[4] + (H[5] or 0)) if played else None, ac=(A[4] + (A[5] or 0)) if played else None,
                                hf=H[3] if played else None, af=A[3] if played else None)); _keys.append((lg, v[0], v[2], v[3]))
        _pr, _alpha, _coef = cards_model.run(_ms, _cm, _now.date(), lim, fit_exclude=set(API_ONLY))
        # 19/10/2026: possesso palla nella ripartizione casa/ospite (totale invariato): possesso delle partite giocate da statextra
        # e dall'archivio giornaliero (indice 11), stesse chiavi (campionato, data, squadre API-Football)
        _pv = {(x_[0], x_[1], x_[2], x_[3]): (x_[4][11], x_[5][11]) for x_ in (globals().get("_SX") or {}).values()
               if len(x_[4]) > 11 and len(x_[5]) > 11 and x_[4][11] is not None and x_[5][11] is not None}
        _np = 0
        for p_, xx_ in zip(_pr, cards_model.possession_x(_ms, _pv)):
            if p_ and xx_ is not None: p_["mh"], p_["ma"] = cards_model.split_possession(p_, xx_); p_["poss"] = round(50 + 10 * xx_, 1); _np += 1
        print("cartellini: ripartizione col possesso su", _np, "partite (possesso di", len(_pv), "partite giocate)")
        CMP = {k: p for k, p in zip(_keys, _pr) if p}
        _cm["attuale"] = {"pesi": dict(zip(["b0"] + cards_model.FEATS, _coef)), "alpha": _alpha}
        json.dump(_cm, open(_cm_path, "w"), separators=(",", ":"))
        print("cartellini v2:", len(CMP), "previsioni · alpha %.4f" % _alpha, "· mesi stimati", len(_cm.get("mesi", {})))
    except Exception as e_:
        import traceback; traceback.print_exc(); print("cartellini v2 non disponibile, resta il modello precedente:", e_); _alpha = None
    # range della media per squadra (gol e cartellini): team_ranges.py, settimane passate conservate in data/team_ranges.json
    TR = {}
    try:
        import team_ranges
        _tr_path = os.path.join(OUT, "team_ranges.json")
        try: _trc = json.load(open(_tr_path))
        except Exception: _trc = {}
        TR = team_ranges.run(by_lg, apif_extra.refkey, _now.date(), lim, _trc)
        json.dump(_trc, open(_tr_path, "w"), separators=(",", ":"))
        print("range per squadra:", len(TR), "partite")
    except Exception as e_:
        import traceback; traceback.print_exc(); print("range per squadra non disponibili:", e_)
    # 10/10/2026: date delle partite rilette dai file definitivi (risultati aggiunti e date allineate a API-Football in questo giro):
    # prima una partita appena finita perdeva arbitro e cartellini perché la sua riga nuova non era tra le date note
    for fn in files:
        if not fn.endswith(".csv"): continue
        try:
            for r in csv.DictReader(io.StringIO(open(os.path.join(OUT, fn), encoding="utf-8-sig").read())):
                lgf = (r.get("Div") or "").strip() or fn.split("_")[0].split(".")[0]
                h, a = (r.get("HomeTeam") or r.get("Home") or "").strip(), (r.get("AwayTeam") or r.get("Away") or "").strip()
                try: dd = r["Date"].strip().split("/"); y = dd[2] if len(dd[2]) == 4 else "20" + dd[2]; pairs[(lgf, h, a)].append(datetime.date(int(y), int(dd[1]), int(dd[0])))
                except Exception: pass
        except Exception: pass
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
            ds = sorted({z for z in pairs.get((lg, h, a), []) if abs((z - d).days) <= 1}, key=lambda z: abs((z - d).days))
            if not ds: continue   # la stessa partita può comparire con date diverse di un giorno nei file (fuso orario, rinvii): la scrivo per ognuna
            real = (r["hc"] + r["ac"]) if r["hc"] is not None and r["ac"] is not None else None
            p = CMP.get((lg, v[0], v[2], v[3]))
            if p:   # [arbitro, sue partite, fattore falli, effetto arbitro sui cartellini, cartellini attesi, reali, casa, ospite, fattori]
                ent = [x["ref"], p["rN"], x["ff"], round(p["ref"], 4), round(p["mu"], 3), real, round(p["mh"], 3), round(p["ma"], 3),
                       [round(p["team"], 3), round(p["ref"], 3), round(p["fouls"], 3), round(p["h2h"], 3), round(p["early"], 3), round(p["derby"], 3)]]
            elif not CMP: ent = [x["ref"], x["n"], x["ff"], x["fc"], x["mu"], real, x["mh"], x["ma"], None]
            else: ent = [x["ref"], x["n"], x["ff"], None, None, real, None, None, None]
            ent.append(TR.get((lg, v[0], v[2], v[3])))   # [9] errori standard per il range: gol casa, gol ospite, cartellini casa, cartellini ospite
            for z in ds: EX[f"{lg}|{z}|{h}|{a}"] = ent
    json.dump({"partite": EX, "alpha": _alpha if CMP else None, "modello": cards_model.VERSION if CMP else "cartellini-v1"},
              open(os.path.join(OUT, "extra.json"), "w"), separators=(",", ":"), ensure_ascii=False)
    print("arbitri e cartellini:", len(EX), "partite abbinate")
except Exception as e:
    import traceback; traceback.print_exc(); print("arbitri e cartellini:", e)
    print("::warning title=API-Football archivio::" + " | ".join(traceback.format_exc().strip().split("\n")[-4:]).replace("%", "%25"))

# Quote dei bookmaker da API-Football (segreto APIFOOTBALL_KEY; piano gratuito: 100 richieste al giorno, 10 al minuto).
# Una volta al giorno (dalle 7 italiane): partite di oggi e domani dei nostri campionati, quota mediana tra i bookmaker
# per Over/Under gol, Gol/No gol, 1X2 e 1X2 corner. Servono solo da mostrare accanto alle nostre probabilità: non entrano
# nei modelli né nel Confidence Score (che usa le quote di football-data, con cui sono stati stimati i pesi).
# Una partita riceve le quote solo se le due squadre corrispondono a una sfida del nostro calendario nello stesso campionato (±1 giorno).
AF_LEAGUES = {"I1": 135, "I2": 136, "E0": 39, "E1": 40, "E2": 41, "E3": 42, "EC": 43, "SP1": 140, "SP2": 141, "F1": 61, "F2": 62, "D1": 78, "D2": 79,
              "N1": 88, "P1": 94, "SC0": 179, "SC1": 180, "SC2": 183, "SC3": 184, "B1": 144, "T1": 203, "G1": 197, "ARG": 128, "AUT": 218, "BRA": 71,
              "CHN": 169, "DNK": 119, "FIN": 244, "IRL": 357, "JPN": 98, "MEX": 262, "NOR": 103, "POL": 106, "ROU": 283, "RUS": 235, "SWE": 113,
              "SWZ": 207, "USA": 253}
AF_LEAGUES.update({k: v[0] for k, v in API_ONLY.items()})
AF_LEAGUES = {k: v for k, v in AF_LEAGUES.items() if k not in REMOVED}
AF_KEY = os.environ.get("APIFOOTBALL_KEY", "").strip()
odds_path = os.path.join(OUT, "odds.json")
try: OD = json.load(open(odds_path))
except Exception: OD = {}
rome_now = datetime.datetime.now(ROME)
# 11/10/2026: quote a fasce (piano a pagamento), a ogni giro dell'app (circa ogni 30 minuti):
#   oggi (e domani dopo le 18, per le partite della notte) a ogni giro · domani ogni 2 ore · da dopodomani a +6 giorni ogni 6 ore.
#   Conti (giornata piena, sabato 10/10): ~25-40 richieste per giorno di quote → ~2.400 al giorno, più ~1.500 del resto dell'app,
#   ben sotto 7.500 meno la riserva per le prove (tools/af_budget.py).
def _tier_due(name, hours):
    try: return (rome_now - datetime.datetime.strptime(OD.get("fasce", {})[name], "%d/%m/%Y %H:%M").replace(tzinfo=ROME)).total_seconds() >= hours * 3600 - 300
    except Exception: return True
ODDS_DAYS = []
if AF_KEY and (OD.get("pro") or not OD):
    ODDS_DAYS.append(0)
    if rome_now.hour >= 18 or _tier_due("domani", 2): ODDS_DAYS.append(1)
    if _tier_due("settimana", 6): ODDS_DAYS += [2, 3, 4, 5, 6]
elif AF_KEY and (OD.get("giorno") != rome_now.strftime("%Y-%m-%d") and rome_now.hour >= 7 or os.environ.get("ODDS_FORCE")):
    ODDS_DAYS = [0, 1]   # piano gratuito: una volta al giorno, oggi e domani
ODDS_FULL = bool(ODDS_DAYS); ODDS_NEAR = False
if ODDS_FULL or ODDS_NEAR:
    af_used = [0]
    def af(path, **q):
        af_used[0] += 1
        req = urllib.request.Request("https://v3.football.api-sports.io/" + path + "?" + urllib.parse.urlencode(q), headers={"x-apisports-key": AF_KEY})
        with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
        time.sleep(0.25)   # 19/10/2026: era 6,5 s (limite del piano gratuito, 10 al minuto); il piano Pro ne ammette 300 al minuto
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
            if (globals().get("MAPS") or {}).get(lg, {}).get(api) == mine: return 1.0   # nomi API → nostri, imparati dai risultati (es. "Heart Of Midlothian" → "Hearts")
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
             "Home Total ShotOnGoal": "hsot", "Away Total ShotOnGoal": "asot", "Asian Handicap": "ah", "Double Chance": "dc",
             "Goals Over/Under": "gou", "Total - Home": "hgou", "Total - Away": "agou",
             "Total Shots": "sou", "Fouls. Total": "fou", "Fouls. Home Total": "hfou", "Fouls. Away Total": "afou"}
    NICHE = {"Corners 1x2": "c1x2", "Corners. Double Chance": "cdc", "Shots.1x2": "s1x2", "ShotOnTarget 1x2": "st1x2", "Fouls. 1x2": "f1x2",
             "Fouls. Double Chance": "fdc", "Yellow Cards 1x2": "y1x2", "Yellow Double Chance": "ydc", "Corners Over Under": "cou",
             "Home Corners Over/Under": "hcou", "Away Corners Over/Under": "acou", "Total Shots": "sou", "Total ShotOnGoal": "sot", "Fouls. Total": "fou",
             "Corners Asian Handicap": "cah", "Cards Asian Handicap": "kah", "Cards Over/Under": "kou"}
    BOOK_TAG = {"1xBet": "x.", "Pinnacle": "p."}
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
                    if nm in XBETS: xacc.setdefault(XBETS[nm] + ":" + val, {})[b["name"]] = o   # mercati secondari: solo archivio (mediana, per le analisi)
                    if nm in XBETS and b["name"] == "1xBet": xacc.setdefault("x." + XBETS[nm] + ":" + val, {})[b["name"]] = o   # 1xBet: linee dell'app
                    # 11/10/2026: mercati del primo tempo di 1xBet (corner, tiri, falli, cartellini…): solo archivio, per studiarli (nessuna richiesta in più)
                    if b["name"] == "1xBet" and re.search(r"1st half|first half|half time", nm, re.I) and re.search(r"corner|shot|foul|card|booking", nm, re.I):
                        xacc.setdefault("x.h1." + re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_") + ":" + val, {})[b["name"]] = o
                    # 1X2 e doppia chance dei mercati di nicchia: quote di 1xBet (il book usato da Denny) e Pinnacle (riferimento), solo archivio
                    # 17/10/2026: mercati sui fuorigioco di 1xBet (se l'API li dà): solo archivio privato, per misurarne la copertura (nessuna richiesta in più)
                    if b["name"] == "1xBet" and re.search(r"offside", nm, re.I):
                        xacc.setdefault("x.off." + re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_") + ":" + val, {})[b["name"]] = o
                    if nm in NICHE and b["name"] in BOOK_TAG:
                        xacc.setdefault(BOOK_TAG[b["name"]] + NICHE[nm] + ":" + val, {})[b["name"]] = o
                    if nm == "Match Winner": key = "1x2:" + {"Home": "1", "Draw": "X", "Away": "2"}.get(val, "")
                    elif nm == "Goals Over/Under" and val.split(" ")[-1] in ("1.5", "2.5", "3.5"): key = "ou" + val.split(" ")[-1] + ":" + val.split(" ")[0][0]
                    elif nm == "Both Teams Score": key = "gg:" + {"Yes": "S", "No": "N"}.get(val, "")
                    elif nm == "Corners 1x2": key = "c1x2:" + {"Home": "1", "Draw": "X", "Away": "2", "1": "1", "X": "X", "2": "2"}.get(val, "")
                    else: continue
                    if key.endswith(":"): continue
                    if b["name"] != "1xBet": continue   # 10/10/2026: quote dell'app solo da 1xBet (riferimento unico)
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
        with urllib.request.urlopen(req, timeout=60) as r: _sr = json.loads(r.read().decode()).get("response"); stt = (_sr.get("requests") or {}) if isinstance(_sr, dict) else {}
        budget = int(stt.get("limit_day", 100)) - int(stt.get("current", 0)) - 5
        paid = int(stt.get("limit_day", 100)) > 100
        # Il piano gratuito non accetta la stagione in corso come parametro: quote chieste per data (tutte le partite, 10 per pagina)
        # oppure per singola partita, scegliendo la via con meno richieste.
        for k in ODDS_DAYS:
            if budget < 30: break   # margine per il resto della giornata
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
    if ODDS_NEAR:   # giro leggero: aggiorno solo le partite vicine, senza toccare l'ora dell'aggiornamento completo
        if res: OD.setdefault("partite", {}).update(res); jdump(OD, odds_path)
    elif res:   # senza quote (errore o richieste del giorno finite): il file precedente resta, si riprova al giro dopo
        _t0 = rome_now.strftime("%Y-%m-%d"); ts_ = rome_now.strftime("%d/%m/%Y %H:%M")
        keep_ = {kk: v for kk, v in (OD.get("partite") or {}).items() if kk.split("|")[1] >= _t0}   # le partite dei giorni non riscaricati restano
        keep_.update(res)
        fas = dict(OD.get("fasce") or {}); fas["oggi"] = ts_
        if 1 in ODDS_DAYS: fas["domani"] = ts_
        if 2 in ODDS_DAYS: fas["settimana"] = ts_
        OD = {"giorno": _t0, "aggiornate": ts_, "fonte": "1xBet (via API-Football)", "fasce": fas,
              "richieste": af_used[0], "errore": err, "non_abbinate": nomatch[:80], "pro": bool(locals().get("paid")), "partite": keep_}
        jdump(OD, odds_path)
    # Archivio per verificare in futuro i mercati (corner, cartellini, tiri in porta…): per ogni partita la prima quota vista e l'ultima
    # prima del calcio d'inizio, con l'ora. Non si cancella mai: serve proprio a misurare a posteriori.
    MOV_KEYS = {"1x2", "ou1.5", "ou2.5", "ou3.5", "gg", "x.c1x2", "x.cdc", "x.s1x2", "x.st1x2", "x.f1x2", "x.fdc", "x.y1x2", "x.ydc", "x.off.offsides_1x2"}
    if allq:
        hp = os.path.join(OUT, "odds_hist.json")
        OH = jload_archive(hp)
        ts = rome_now.strftime("%Y-%m-%d %H:%M")
        # 27/10/2026: partita spostata di data (es. PSG–Lyon dal 25 al 26/10): la stessa sfida dello stesso campionato entro 4 giorni è UNA
        # partita; l'archivio della data vecchia si unisce a quello nuovo (prima quota vista, mercati, serie dei movimenti), così la storia
        # non si spezza in due e i mercati visti prima dello spostamento restano registrati con la loro ora.
        def _merge_old(new_k, old_k):
            o_, n_ = OH.pop(old_k), OH.get(new_k, {})
            m_ = {"prima": o_.get("prima") or n_.get("prima")}
            if n_.get("prima"):
                for qk, qv in n_["prima"].get("q", {}).items():
                    if qk not in m_["prima"]["q"]: m_["prima"]["q"][qk] = qv; m_["prima"].setdefault("ore", {})[qk] = n_["prima"].get("ore", {}).get(qk, n_["prima"]["ora"])
            if o_.get("ultima") or n_.get("ultima"):
                m_["ultima"] = {"ora": (n_.get("ultima") or o_.get("ultima"))["ora"], "q": {**(o_.get("ultima") or {}).get("q", {}), **(n_.get("ultima") or {}).get("q", {})}}
            m_["serie"] = ((o_.get("serie") or []) + (n_.get("serie") or []))[-60:]
            m_["spostata_da"] = old_k.split("|")[1]
            m_ = {k_: v_ for k_, v_ in m_.items() if v_}
            OH[new_k] = m_; _moved.append(f"{old_k} → {new_k.split('|')[1]}")
        _moved, _byp = [], collections.defaultdict(list)
        for kk in list(OH): _l, _d, _h, _a = kk.split("|"); _byp[(_l, _h, _a)].append(_d)
        for kk in allq:   # sfida vista oggi con una data che l'archivio non ha: c'è la stessa sfida pochi giorni prima o dopo?
            _l, _d, _h, _a = kk.split("|")
            if kk in OH: continue
            for _od in _byp.get((_l, _h, _a), []):
                ok_ = f"{_l}|{_od}|{_h}|{_a}"
                if ok_ in OH and ok_ not in allq and abs((datetime.date.fromisoformat(_od) - datetime.date.fromisoformat(_d)).days) <= 4: _merge_old(kk, ok_); break
        for (_l, _h, _a), L_ in _byp.items():   # coppie già spezzate (prima di oggi): la data vecchia smette di essere vista prima della nuova
            if len(L_) < 2: continue
            L_ = sorted(L_)
            for i_ in range(len(L_) - 1):
                k0, k1 = f"{_l}|{L_[i_]}|{_h}|{_a}", f"{_l}|{L_[i_ + 1]}|{_h}|{_a}"
                if k0 in OH and k1 in OH and (datetime.date.fromisoformat(L_[i_ + 1]) - datetime.date.fromisoformat(L_[i_])).days <= 4 \
                        and (OH[k0].get("ultima") or {}).get("ora", "") <= (OH[k1].get("prima") or {}).get("ora", "~"):
                    _merge_old(k1, k0)
        if _moved: print("::notice title=Quote · partite spostate::archivio unito per " + str(len(_moved)) + ": " + "; ".join(_moved[:10]))
        for kk, q in allq.items():
            x = OH.setdefault(kk, {})
            if "prima" not in x: x["prima"] = {"ora": ts, "q": dict(q)}
            else:   # mercati comparsi dopo (es. 1X2 tiri di 1xBet poche ore prima): la loro prima quota, con l'ora
                for qk, qv in q.items():
                    if qk not in x["prima"]["q"]: x["prima"]["q"][qk] = qv; x["prima"].setdefault("ore", {})[qk] = ts
            x["ultima"] = {"ora": ts, "q": {**x.get("ultima", {}).get("q", {}), **q}}
            # movimento delle quote 1xBet (sezione "Quote 1xBet" della Lettura): una tappa per ogni giro in cui qualcosa cambia
            snap = {qk: qv[0] for qk, qv in q.items() if qk.split(":")[0] in MOV_KEYS}
            if snap:
                ser = x.setdefault("serie", [])
                if not ser or ser[-1][1] != snap: ser.append([ts, snap]); del ser[:-60]
        jdump(OH, hp)
        print("archivio quote:", len(OH), "partite")
        # 19/10/2026: dove 1xBet quota gli 1X2 dei mercati di nicchia (data/mercati.json, solo nomi di campionato, nessuna quota).
        # 24/10/2026: conta le ULTIME 10 partite di ogni campionato (fino a ieri, più quelle di oggi che hanno già la quota: falli, tiri e
        # tiri in porta arrivano poche ore prima), non tutto l'archivio: un mercato che 1xBet aggiunge (es. falli di Championship, Segunda,
        # 2. Bundesliga dal 23/10) entra in pochi giorni, uno che toglie esce. "Giocabile" = almeno 5 delle ultime 10 (minimo 4 partite).
        # Radar, Segnali e pallini della home mostrano gli 1X2 di nicchia solo dove sono giocabili; la scheda partita li mostra sempre.
        try:
            _MK = {"c": "x.c1x2", "s": "x.s1x2", "st": "x.st1x2", "f": "x.f1x2", "y": "x.y1x2", "c1": "x.h1.corners_1x2_1st_half", "y1": "x.h1.yellow_cards_1x2_1st_half", "o": "x.off.offsides_1x2"}
            _t0 = rome_now.strftime("%Y-%m-%d"); _byl = collections.defaultdict(list)
            for kk, x in OH.items():
                lg_, d_ = kk.split("|")[:2]
                if d_ > _t0: continue
                ks = {q.split(":")[0] for part in ("prima", "ultima") for q in (x.get(part) or {}).get("q", {}) if q.startswith("x.")}
                if ks: _byl[lg_].append((d_, ks))
            # 27/10/2026: regola delle ultime 10 valutata su ognuno degli ultimi 21 giorni: un campionato resta giocabile per 21 giorni
            # dall'ultima volta che la superava. Motivo: dal 24/10 API-Football ha smesso di passare quasi tutti i mercati 1xBet di falli,
            # gialli e fuorigioco (e in parte i tiri) anche dove 1xBet li offre: senza margine, Radar e Segnali avrebbero tolto quei mercati
            # da campionati dove sono giocabili. Un mercato che 1xBet toglie davvero esce comunque dopo 21 giorni.
            def _ok_at(day_):
                out_ = collections.defaultdict(set)
                for lg_, L_ in _byl.items():
                    for m_, key_ in _MK.items():
                        win = [ks for d_, ks in L_ if d_ < day_ or (d_ == day_ and key_ in ks)][-10:]
                        if len(win) >= 4 and sum(1 for ks in win if key_ in ks) / len(win) >= 0.5: out_[m_].add(lg_)
                return out_
            for L_ in _byl.values(): L_.sort(key=lambda z: z[0])
            _d0 = datetime.date.fromisoformat(_t0); _now_ok = _ok_at(_t0); _mer = {m_: set(_now_ok[m_]) for m_ in _MK}; _grace = collections.defaultdict(list)
            for back_ in range(1, 22):
                for m_, S_ in _ok_at((_d0 - datetime.timedelta(days=back_)).isoformat()).items():
                    for lg_ in S_ - _mer[m_]: _mer[m_].add(lg_); _grace[m_].append(lg_)
            _mer = {m_: sorted(v_ - REMOVED) for m_, v_ in _mer.items()}   # campionati tolti dall'app: fuori anche da qui
            # controllo della fonte: partite degli ultimi 3 giorni con il mercato, contro i 14 giorni prima, solo nei campionati giocabili
            _src = {}
            for m_, key_ in _MK.items():
                if m_ in ("c",): continue
                rec_ = [key_ in ks for lg_ in _mer[m_] for d_, ks in _byl.get(lg_, []) if (_d0 - datetime.date.fromisoformat(d_)).days in (0, 1, 2)]
                old_ = [key_ in ks for lg_ in _mer[m_] for d_, ks in _byl.get(lg_, []) if 3 <= (_d0 - datetime.date.fromisoformat(d_)).days <= 16]
                if len(rec_) >= 8 and len(old_) >= 20:
                    r1, r0 = sum(rec_) / len(rec_), sum(old_) / len(old_)
                    if r0 >= 0.3 and r1 < 0.5 * r0: _src[m_] = f"{round(r1 * 100)}% delle partite negli ultimi 3 giorni contro {round(r0 * 100)}% prima"
            _MKN = {"s": "1X2 tiri", "st": "1X2 tiri in porta", "f": "1X2 falli", "y": "1X2 gialli", "c1": "1X2 corner 1° tempo", "y1": "1X2 gialli 1° tempo", "o": "1X2 fuorigioco"}
            if _src:
                print("::warning title=Quote 1xBet · fonte ridotta::" + " · ".join(f"{_MKN.get(m_, m_)}: {v_}" for m_, v_ in _src.items())
                      + " · API-Football non passa la quota anche dove 1xBet offre il mercato: nell'app compare N.D. con la spiegazione; Radar e Segnali tengono il mercato (margine di 21 giorni)")
            QUAL_SRC = _src
            # 24/10/2026: falli 1X2 di Championship, Segunda e 2. Bundesliga visti da Denny su 1xBet dal 23/10 (archivio: E1 1/1, SP2 1/1,
            # D2 2/2 il 23/10). Inseriti subito fino al 2/11, poi decide solo la regola delle ultime 10 (a quel punto hanno le partite).
            if _t0 <= "2026-11-02":
                for lg_ in ("E1", "SP2", "D2"):
                    if lg_ not in _mer["f"]: _mer["f"] = sorted(_mer["f"] + [lg_])
            # 1X2 del 1° tempo di tiri, tiri in porta e falli: 1xBet li offre dove offre quello della partita intera (verifica di Denny,
            # 19/10/2026), ma API-Football non li passa: stessi campionati della partita intera, segnati come presunti
            for m_ in ("s", "st", "f"): _mer[m_ + "1"] = list(_mer[m_])
            jdump({"soglia": "almeno 5 delle ultime 10 partite, in un giorno qualsiasi degli ultimi 21", "giocabili": _mer,
                   "presunti": ["s1", "st1", "f1"], "fonte_ridotta": {m_: v_ for m_, v_ in _src.items()},
                   "margine": {m_: sorted(set(v_)) for m_, v_ in _grace.items() if v_}}, os.path.join(OUT, "mercati.json"))
            print("mercati 1X2 giocabili:", {m_: len(v_) for m_, v_ in _mer.items()})
        except Exception as e_: print("::warning title=Mercati giocabili::" + str(e_))
    print("quote:", len(res), "partite,", af_used[0], "richieste,", len(nomatch), "non abbinate")
elif not AF_KEY:
    print("APIFOOTBALL_KEY non impostata: quote saltate")
# Linee principali dei bookmaker per la scheda match e il Radar (data/linee.json), dall'archivio: per ogni partita e mercato la linea
# x,5 con quote Over e Under entrambe presenti e più equilibrate (quella su cui il book è vicino al 50%), con l'ultima quota vista
# prima del calcio d'inizio. Solo quote reali; dove la linea non c'è, la partita o il mercato mancano (nell'app: N.D.).
try:
    try: OH
    except NameError: OH = json.load(open(os.path.join(OUT, "odds_hist.json")))
    LMK = {"g": "gou", "hg": "hgou", "ag": "agou", "c": "cou", "hc": "hcou", "ac": "acou", "k": "kou", "hk": "hk", "ak": "ak", "st": "sot", "hst": "hsot", "ast": "asot",
           "s": "sou", "f": "fou", "hf": "hfou", "af": "afou"}
    LMK = {k: "x." + v for k, v in LMK.items()}   # 10/10/2026: linee solo di 1xBet
    LMK.update({"o": "x.off.offsides_total", "ho": "x.off.offsides_home_total", "ao": "x.off.offsides_away_total"})   # 18/10/2026: fuorigioco
    LN = {}
    for kk, x in OH.items():
        q = x.get("ultima", {}).get("q", {}); ent = {}
        for short, mk in LMK.items():
            lines = {}
            for k2, v in q.items():
                if not k2.startswith(mk + ":"): continue
                try: side, ln = k2.split(":", 1)[1].split(" "); ln = float(ln)
                except Exception: continue
                if abs(ln * 2 - round(ln * 2)) > 1e-9 or abs(ln - math.floor(ln) - 0.5) > 1e-9: continue   # solo linee x,5 (niente rimborso)
                lines.setdefault(ln, {})[side[0]] = v
            if short == "g":   # gol totali: anche le linee 1,5 · 2,5 · 3,5 delle quote principali
                for ln in (1.5, 2.5, 3.5):
                    for sd in ("O", "U"):
                        v = q.get(f"x.gou:{'Over' if sd == 'O' else 'Under'} {ln}")
                        if v and sd not in lines.get(ln, {}): lines.setdefault(ln, {})[sd] = v
            best = None
            for ln, o in lines.items():
                if "O" in o and "U" in o and o["O"][0] > 1 and o["U"][0] > 1:
                    d = abs(1 / o["O"][0] - 1 / o["U"][0])
                    if best is None or d < best[0] - 1e-9 or (abs(d - best[0]) < 1e-9 and min(o["O"][1], o["U"][1]) > best[4]):
                        best = (d, ln, o["O"][0], o["U"][0], min(o["O"][1], o["U"][1]))
            if best: ent[short] = [best[1], best[2], best[3], best[4]]
        _o3 = [q.get("x.off.offsides_1x2:" + s_, [None])[0] for s_ in ("Home", "Draw", "Away")]   # fuorigioco 1X2 (1xBet)
        if all(v_ and v_ > 1 for v_ in _o3): ent["o1x2"] = _o3
        if ent: ent["t"] = x["ultima"].get("ora", ""); LN[kk] = ent
    json.dump({"aggiornate": rome_now.strftime("%d/%m/%Y %H:%M"), "fonte": "1xBet (via API-Football): ultima quota vista prima del calcio d'inizio", "partite": LN},
              open(os.path.join(OUT, "linee.json"), "w"), separators=(",", ":"), ensure_ascii=False)
    print("linee bookmaker:", len(LN), "partite")
    # movimento delle quote 1xBet delle partite da oggi in avanti (data/quote_mov.json, pubblico: solo partite non ancora giocate)
    _t0 = rome_now.strftime("%Y-%m-%d"); QM = {}
    for kk, x in OH.items():
        if kk.split("|")[1] >= _t0 and x.get("serie"): QM[kk] = x["serie"]
    json.dump({"aggiornate": rome_now.strftime("%d/%m/%Y %H:%M"), "fonte": "1xBet (via API-Football)", "partite": QM},
              open(os.path.join(OUT, "quote_mov.json"), "w"), separators=(",", ":"), ensure_ascii=False)
    print("movimento quote:", len(QM), "partite")
except Exception as e:
    print("linee bookmaker:", e)

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
# 27/10/2026: quote 1xBet che la fonte non passa più e formazioni mancate (rigore sul riporto, richiesta di Denny)
try:
    _fr = json.load(open(os.path.join(OUT, "mercati.json"))).get("fonte_ridotta") or {}
    _MKN = {"s": "1X2 tiri", "st": "1X2 tiri in porta", "f": "1X2 falli", "y": "1X2 gialli", "c1": "1X2 corner 1° tempo", "y1": "1X2 gialli 1° tempo", "o": "1X2 fuorigioco"}
    if _fr: _av.append("Quote 1xBet ridotte dalla fonte (API-Football): " + "; ".join(f"{_MKN.get(k, k)} {v}" for k, v in _fr.items()) + ". Dove manca la quota, controllare su 1xBet")
    QUAL["quote_fonte_ridotta"] = _fr
except Exception: pass
_fz = QUAL.get("formazioni") or {}
if _fz.get("partite_24h") and len(_fz.get("mancate") or []) > 0.1 * _fz["partite_24h"]:
    _av.append(f"Formazioni ufficiali: mancate {len(_fz['mancate'])} su {_fz['partite_24h']} partite nelle ultime 24 ore")
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
# 19/10/2026: due file. bundle_storico.json = righe prima del 1° gennaio dell'anno di inizio della stagione in corso (stagioni chiuse:
# cambia una volta l'anno, il telefono lo scarica una volta sola); bundle.json = il resto (stagione in corso e calendario). Nessuna
# ora del giro dentro i file: l'ora e le impronte dei file stanno in data/stato.json (scritto alla pubblicazione).
CUT_ST = datetime.date(cur, 1, 1)
def _rowdate(x):
    try: dd = x.strip().split("/"); y = dd[2] if len(dd[2]) == 4 else "20" + dd[2]; return datetime.date(int(y), int(dd[1]), int(dd[0]))
    except Exception: return None
bundle, bundle_st = [], []
for f in files:
    try:
        rd = list(csv.reader(io.StringIO(open(os.path.join(OUT, f), encoding="utf-8-sig").read())))
        if not rd: continue
        hdr = [h.strip() for h in rd[0]]; idx = [i for i, h in enumerate(hdr) if h in KEEP]; iD = hdr.index("Date") if "Date" in hdr else -1
        parts = {"st": io.StringIO(), "cur": io.StringIO()}; ws = {k: csv.writer(v, lineterminator="\n") for k, v in parts.items()}; n = {"st": 0, "cur": 0}
        for w in ws.values(): w.writerow([hdr[i] for i in idx])
        for r in rd[1:]:
            if not any(x.strip() for x in r): continue
            d = _rowdate(r[iD]) if iD >= 0 and iD < len(r) else None
            k = "st" if d and d < CUT_ST and "fixtures" not in f else "cur"
            ws[k].writerow([r[i] if i < len(r) else "" for i in idx]); n[k] += 1
        if n["st"]: bundle_st.append({"name": f, "text": parts["st"].getvalue()})
        if n["cur"] or not n["st"]: bundle.append({"name": f, "text": parts["cur"].getvalue()})
    except Exception as e:
        print("bundle: salto", f, e)
json.dump({"files": bundle_st}, open(os.path.join(OUT, "bundle_storico.json"), "w"), separators=(",", ":"))
json.dump({"files": bundle}, open(os.path.join(OUT, "bundle.json"), "w"), separators=(",", ":"))
print("ok", len(files), "file")
