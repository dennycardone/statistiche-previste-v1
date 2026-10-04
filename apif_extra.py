"""Arbitro e cartellini da API-Football (storico + giorno per giorno), per l'app.
- abbina i nomi delle squadre di API-Football ai nostri (partite con stessa data ±1 e stesso risultato);
- per ogni partita, con le sole partite precedenti: fattore arbitro sui falli e sui cartellini (quanto fischia rispetto
  al previsto, ristretto verso 1 con K partite fittizie) e cartellini attesi (modello squadre: media mobile dei cartellini
  propri e provocati, peso 0,95 a partita) corretto per l'arbitro.
Parametri scelti sul 2023 e verificati sul 2024-2026 (backtest): K=20, W=0,95."""
import collections, datetime, difflib, re, unicodedata
K, W, MIN_N = 20, 0.95, 3
def _norm(x):
    x = unicodedata.normalize("NFKD", x or "").encode("ascii", "ignore").decode().lower().replace("'", "")
    x = re.sub(r"[^a-z0-9 ]", " ", x)
    stop = {"fc", "afc", "cf", "sc", "ac", "fk", "sk", "the", "club", "de", "calcio", "cd", "ud", "rc", "sd", "ca", "ss", "as", "us", "1", "sv", "vfl", "vfb", "tsg", "fsv"}
    return " ".join(w for w in x.split() if w not in stop)
def _sim(a, b):
    a, b = _norm(a), _norm(b)
    if a == b: return 1.0
    if a and b and (a in b or b in a): return 0.9
    return difflib.SequenceMatcher(None, a, b).ratio()
MANUAL = {"NOR": {"Ham-Kam": "HamKam"}, "AUT": {"WSG Wattens": "Tirol"}}   # nomi che l'abbinamento automatico non riconosce
def learn_map(api, ours, lg=None):
    """api: [(date, home, away, hg, ag)], ours: [(date, home, away, hg, ag)] di un campionato -> {nome API: nostro nome}"""
    byd = collections.defaultdict(list)
    for o in ours: byd[o[0]].append(o)
    votes = collections.defaultdict(collections.Counter)
    for d, h, a, hg, ag in api:
        if hg is None: continue
        cand = [o for k in (-1, 0, 1) for o in byd.get(d + datetime.timedelta(days=k), []) if o[3] == hg and o[4] == ag]
        sc = sorted(((_sim(h, o[1]) + _sim(a, o[2]), o) for o in cand), key=lambda z: -z[0])
        if sc and sc[0][0] >= 1.2 and (len(sc) == 1 or sc[1][0] < sc[0][0] - 0.3):
            votes[h][sc[0][1][1]] += 1; votes[a][sc[0][1][2]] += 1
    m = {}
    for k, c in votes.items():
        (best, n), = c.most_common(1)
        if n >= 2 and n >= 0.8 * sum(c.values()): m[k] = best
    # più nomi API sulla stessa squadra nostra: ammessi solo se non compaiono mai nella stessa stagione (API-Football cambia
    # a volte la grafia tra una stagione e l'altra, es. "Bayern Munich" / "Bayern München"); altrimenti sono squadre diverse → scartati
    seas = collections.defaultdict(set)
    for d, h, a, hg, ag in api:
        sk = d.year if d.month >= 7 else d.year - 1
        seas[h].add(sk); seas[a].add(sk)
    by_ours = collections.defaultdict(list)
    for k, v in m.items(): by_ours[v].append(k)
    out = {}
    for v, ks in by_ours.items():
        ok = all(not (seas[x] & seas[y]) for i, x in enumerate(ks) for y in ks[i + 1:])
        if ok:
            for k in ks: out[k] = v
    for k, v in MANUAL.get(lg, {}).items():
        out = {x: y for x, y in out.items() if y != v}; out[k] = v
    return out
def refkey(name):   # "Daniele Doveri", "D. Doveri", "Doveri, Italy" → "d doveri" (API-Football non scrive sempre allo stesso modo)
    if not name: return None
    w = _norm(name.split(",")[0]).split()
    if not w: return None
    return (w[0][0] + " " + w[-1]) if len(w) > 1 else w[0]
def compute(rows):
    """rows di un campionato in ordine di data: dict(d, h, a, ref, hc, ac, hf, af) (statistiche None se non giocata).
    Restituisce per ogni riga: ref, n partite dell'arbitro, fattore falli, fattore cartellini, cartellini attesi (None se mancano dati)."""
    team = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0])   # cartellini propri, provocati, falli propri, subiti, peso
    refs = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0])      # cartellini reali, attesi, falli reali, attesi, n
    lg = [0.0, 0.0, 0]                                                   # cartellini, falli, n
    out = []
    for r in rows:
        th, ta = team[r["h"]], team[r["a"]]
        res = {"ref": r.get("ref"), "n": 0, "ff": None, "fc": None, "mu": None, "mu0": None, "mh": None, "ma": None}
        ec = ef = None
        if lg[2] >= 30 and th[4] >= MIN_N and ta[4] >= MIN_N:
            ec = (th[0] / th[4] + ta[1] / ta[4]) / 2 + (ta[0] / ta[4] + th[1] / th[4]) / 2
            ef = (th[2] / th[4] + ta[3] / ta[4]) / 2 + (ta[2] / ta[4] + th[3] / th[4]) / 2
            mc, mf = lg[0] / lg[2], lg[1] / lg[2]
            rk = refkey(r.get("ref")); R = refs.get(rk) if rk else None
            fc = (R[0] + K * mc) / (R[1] + K * mc) if R and R[4] and R[1] + K * mc > 0 else 1.0
            ff = (R[2] + K * mf) / (R[3] + K * mf) if R and R[4] and R[3] + K * mf > 0 else 1.0
            eh = (th[0] / th[4] + ta[1] / ta[4]) / 2; ea = (ta[0] / ta[4] + th[1] / th[4]) / 2   # cartellini attesi per squadra
            res.update(n=R[4] if R else 0, ff=round(ff, 4), fc=round(fc, 4), mu=round(ec * fc, 3), mu0=round(ec, 3), mh=round(eh * fc, 3), ma=round(ea * fc, 3))
        out.append(res)
        if r.get("hc") is None or r.get("ac") is None: continue
        T = r["hc"] + r["ac"]; F = (r["hf"] + r["af"]) if r.get("hf") is not None and r.get("af") is not None else None
        if refkey(r.get("ref")) and ec is not None:
            R = refs[refkey(r["ref"])]; R[0] += T; R[1] += ec; R[4] += 1
            if F is not None: R[2] += F; R[3] += ef
        for t, oc, pc, of, pf in ((r["h"], r["hc"], r["ac"], r.get("hf"), r.get("af")), (r["a"], r["ac"], r["hc"], r.get("af"), r.get("hf"))):
            x = team[t]
            if of is None or pf is None: of, pf = (x[2] / x[4], x[3] / x[4]) if x[4] else (0.0, 0.0)
            x[0] = x[0] * W + oc; x[1] = x[1] * W + pc; x[2] = x[2] * W + of; x[3] = x[3] * W + pf; x[4] = x[4] * W + 1
        lg[0] += T; lg[1] += F if F is not None else lg[1] / max(lg[2], 1); lg[2] += 1
    return out

STAT_COLS = ["HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC"]
API_IDX = {"HS": (7, 0), "AS": (8, 0), "HST": (7, 1), "AST": (8, 1), "HF": (7, 3), "AF": (8, 3), "HC": (7, 2), "AC": (8, 2)}   # (squadra, statistica) nell'archivio
def api_stats_ok(v):
    """Controllo di plausibilità delle statistiche di API-Football (verifica su fonti indipendenti: API-Football è la più
    affidabile, ma a volte ha falli impossibili, es. 23-0 o 4-2). Restituisce per gruppo (tiri, porta, falli, corner) se usarlo."""
    H, A = v[7] if len(v) > 9 else v[6], v[8] if len(v) > 9 else v[7]
    g = lambda t, k: t[k] if t and t[k] is not None else None
    hs, as_, hst, ast, hc, ac, hf, af = g(H, 0), g(A, 0), g(H, 1), g(A, 1), g(H, 2), g(A, 2), g(H, 3), g(A, 3)
    ok = {}
    ok["s"] = hs is not None and as_ is not None and hs + as_ >= 4
    ok["st"] = ok["s"] and hst is not None and ast is not None and hst <= hs and ast <= as_
    ok["f"] = hf is not None and af is not None and hf >= 3 and af >= 3 and hf + af >= 10
    ok["c"] = hc is not None and ac is not None
    return ok
GROUP = {"HS": "s", "AS": "s", "HST": "st", "AST": "st", "HF": "f", "AF": "f", "HC": "c", "AC": "c"}
def fill_stats(rd, lg, api_rows, mp, override=False):
    """rd: righe CSV (intestazione + righe) di un campionato. Riempie SOLO dove mancano: corner, falli, tiri, tiri in porta
    (colonne di football-data) e cartellini per squadra HK/AK (gialli + rossi, sempre da API-Football), con la partita di
    API-Football che ha stesse squadre, giorno ±1 e stesso risultato. Restituisce (righe, quante partite toccate)."""
    hdr = [h.strip() for h in rd[0]]; body = [list(r) for r in rd[1:]]
    new = "HomeTeam" not in hdr
    iD, iH, iA = hdr.index("Date"), hdr.index("Home" if new else "HomeTeam"), hdr.index("Away" if new else "AwayTeam")
    iG1, iG2 = hdr.index("HG" if new else "FTHG"), hdr.index("AG" if new else "FTAG")
    for c in STAT_COLS + ["HK", "AK"]:
        if c not in hdr: hdr.append(c); [r.append("") for r in body]
    idx = {c: hdr.index(c) for c in STAT_COLS + ["HK", "AK"]}
    by = collections.defaultdict(list)
    for v in api_rows:
        h, a = mp.get(v[2]), mp.get(v[3])
        if h and a and v[4] is not None: by[(h, a)].append(v)
    n = 0
    for r in body:
        if len(r) < len(hdr): r.extend([""] * (len(hdr) - len(r)))
        need_s = override or not all(r[idx[c]].strip() for c in STAT_COLS); need_k = override or not (r[idx["HK"]].strip() and r[idx["AK"]].strip())
        if not need_s and not need_k: continue
        try:
            dd = r[iD].strip().split("/"); y = dd[2] if len(dd[2]) == 4 else "20" + dd[2]; d = datetime.date(int(y), int(dd[1]), int(dd[0]))
            g1, g2 = int(r[iG1]), int(r[iG2])
        except Exception: continue
        for v in by.get((r[iH].strip(), r[iA].strip()), []):
            if abs((datetime.date.fromisoformat(v[0][:10]) - d).days) <= 1 and v[4] == g1 and v[5] == g2:
                done = False
                vals = {c: v[t][k] for c, (t, k) in API_IDX.items()}
                ok = api_stats_ok(v)
                if need_s:
                    for c in STAT_COLS:   # API-Football dove plausibile (anche sopra football-data se override), altrimenti resta quello che c'è
                        if ok[GROUP[c]] and vals[c] is not None and (override or not r[idx[c]].strip()):
                            r[idx[c]] = str(int(vals[c])); done = True
                if need_k and v[7][4] is not None and v[8][4] is not None:
                    r[idx["HK"]] = str(int(v[7][4] + (v[7][5] or 0))); r[idx["AK"]] = str(int(v[8][4] + (v[8][5] or 0))); done = True
                n += done; break
    return [hdr] + body, n

def add_results(rd, lg, api_rows, mp, today, tz):
    """Aggiunge le partite giocate che API-Football ha e il nostro file non ancora (dopo l'ultima data del file e se la stessa
    sfida non c'è già entro 3 giorni), con gol, statistiche e cartellini. Formati football-data (HomeTeam…) e "new" (Home…)."""
    hdr = [h.strip() for h in rd[0]]; body = [list(r) for r in rd[1:] if any(x.strip() for x in r)]
    new = "HomeTeam" not in hdr
    for c in STAT_COLS + ["HK", "AK"]:
        if c not in hdr: hdr.append(c); [r.append("") for r in body]
    ix = {h: i for i, h in enumerate(hdr)}
    iD, iH, iA = ix["Date"], ix["Home" if new else "HomeTeam"], ix["Away" if new else "AwayTeam"]
    iG1, iG2 = ix["HG" if new else "FTHG"], ix["AG" if new else "FTAG"]
    def _d(x):
        try:
            dd = x.strip().split("/"); y = dd[2] if len(dd[2]) == 4 else "20" + dd[2]; return datetime.date(int(y), int(dd[1]), int(dd[0]))
        except Exception: return None
    pairs = collections.defaultdict(list)
    for r in body:
        d = _d(r[iD])
        if d: pairs[(r[iH].strip(), r[iA].strip())].append(d)
    dates = [d for v in pairs.values() for d in v]
    if not dates: return [hdr] + body, 0
    last = max(dates); lastrow = max(body, key=lambda r: _d(r[iD]) or datetime.date.min)
    n = 0
    for v in sorted(api_rows, key=lambda v: v[0]):
        if v[9] not in ("FT", "AET", "PEN") or v[4] is None: continue
        h, a = mp.get(v[2]), mp.get(v[3])
        if not h or not a: continue
        loc = datetime.datetime.fromisoformat(v[0] + ":00+00:00").astimezone(tz); d = loc.date()
        if d <= last or d > today or any(abs((x - d).days) <= 3 for x in pairs.get((h, a), [])): continue
        r = [""] * len(hdr)
        r[iD] = d.strftime("%d/%m/%Y"); r[iH], r[iA], r[iG1], r[iG2] = h, a, str(v[4]), str(v[5])
        if "Time" in ix: r[ix["Time"]] = loc.strftime("%H:%M")
        res = "H" if v[4] > v[5] else "A" if v[5] > v[4] else "D"
        if new:
            r[ix.get("Country", 0)] = lg
            if "League" in ix: r[ix["League"]] = lastrow[ix["League"]]
            if "Season" in ix:
                ss = lastrow[ix["Season"]]
                if ss.strip().isdigit() and d.year != int(ss) and d.month <= 6 and int(ss) < d.year: ss = str(d.year)   # campionati per anno solare: nuova stagione
                r[ix["Season"]] = ss
            if "Res" in ix: r[ix["Res"]] = res
        else:
            r[ix.get("Div", 0)] = lg
            if "FTR" in ix: r[ix["FTR"]] = res
        for c, (t, k) in API_IDX.items():
            x = v[t][k] if v[t] else None
            if x is not None: r[ix[c]] = str(int(x))
        if v[7] and v[8] and v[7][4] is not None and v[8][4] is not None:
            r[ix["HK"]] = str(int(v[7][4] + (v[7][5] or 0))); r[ix["AK"]] = str(int(v[8][4] + (v[8][5] or 0)))
        body.append(r); pairs[(h, a)].append(d); n += 1
    return [hdr] + body, n
