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
def learn_map(api, ours):
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
    taken = collections.Counter(m.values())
    return {k: v for k, v in m.items() if taken[v] == 1}   # due nomi API sulla stessa squadra nostra: scartati
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
        res = {"ref": r.get("ref"), "n": 0, "ff": None, "fc": None, "mu": None, "mu0": None}
        ec = ef = None
        if lg[2] >= 30 and th[4] >= MIN_N and ta[4] >= MIN_N:
            ec = (th[0] / th[4] + ta[1] / ta[4]) / 2 + (ta[0] / ta[4] + th[1] / th[4]) / 2
            ef = (th[2] / th[4] + ta[3] / ta[4]) / 2 + (ta[2] / ta[4] + th[3] / th[4]) / 2
            mc, mf = lg[0] / lg[2], lg[1] / lg[2]
            rk = refkey(r.get("ref")); R = refs.get(rk) if rk else None
            fc = (R[0] + K * mc) / (R[1] + K * mc) if R and R[4] and R[1] + K * mc > 0 else 1.0
            ff = (R[2] + K * mf) / (R[3] + K * mf) if R and R[4] and R[3] + K * mf > 0 else 1.0
            res.update(n=R[4] if R else 0, ff=round(ff, 4), fc=round(fc, 4), mu=round(ec * fc, 3), mu0=round(ec, 3))
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
def fill_stats(rd, lg, api_rows, mp):
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
        need_s = not all(r[idx[c]].strip() for c in STAT_COLS); need_k = not (r[idx["HK"]].strip() and r[idx["AK"]].strip())
        if not need_s and not need_k: continue
        try:
            dd = r[iD].strip().split("/"); y = dd[2] if len(dd[2]) == 4 else "20" + dd[2]; d = datetime.date(int(y), int(dd[1]), int(dd[0]))
            g1, g2 = int(r[iG1]), int(r[iG2])
        except Exception: continue
        for v in by.get((r[iH].strip(), r[iA].strip()), []):
            if abs((datetime.date.fromisoformat(v[0][:10]) - d).days) <= 1 and v[4] == g1 and v[5] == g2:
                done = False
                vals = {c: v[t][k] for c, (t, k) in API_IDX.items()}
                if need_s and not any(x is None for x in vals.values()):
                    for c in STAT_COLS:
                        if not r[idx[c]].strip(): r[idx[c]] = str(int(vals[c]))
                    done = True
                if need_k and v[7][4] is not None and v[8][4] is not None:
                    r[idx["HK"]] = str(int(v[7][4] + (v[7][5] or 0))); r[idx["AK"]] = str(int(v[8][4] + (v[8][5] or 0))); done = True
                n += done; break
    return [hdr] + body, n
