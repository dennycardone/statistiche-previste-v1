"""Basket · giocatori per il sito (15/11/2026, Denny). Versione automatica validata sull'harness (tools/basket/test_giocatori.py, IPOTESI.md 15/11):
  media al minuto del giocatore (media mobile DP 0,97, ristretta verso la media del suo ruolo con 120 minuti fittizi) × minuti medi (quintetto non noto);
  ancoraggio alla partita di Prevista: × (punti attesi della squadra / punti abituali)^α per punti e assist, × (ritmo atteso / ritmo abituale)^α per i rimbalzi;
  assenze automatiche: abituali (≥15 minuti di media) che mancavano all'ultima partita della squadra, + (NBA) uno dei primi 2 realizzatori non quotato
  dai book del feed mentre i compagni lo sono → assente; i presenti salgono di (1 + β · quota mancante).
  Distribuzioni (scelte sulle soglie fisse nel periodo scelta): punti e punti+assist binomiale negativa varianza 3·media; rimbalzi e assist
  binomiale negativa con r = 13 (coda bassa corretta). Doppia/tripla doppia: tre voci indipendenti, poi ricalibrate (logit a + b·logit).
Python puro (il runner di GitHub non ha numpy). Le probabilità si calcolano nell'app con gli stessi parametri (gpar)."""
import json, glob, os, re, collections, datetime, unicodedata
DP, KMIN = 0.97, 120.0
ALPHA = {"pts": 0.75, "reb": 1.25, "ast": 1.5}
BETA = {"pts": 0.2, "reb": 0.1, "ast": 0.3}
GPAR = {"pts": ["nb1", 3.0], "reb": ["nb2", 13.0], "ast": ["nb2", 13.0], "pa": ["nb1", 3.0], "dd": [-0.1, 0.8], "td": [0.1, 0.9], "beta": BETA}
ST = ("pts", "reb", "ast")
TRANS = str.maketrans({"ø": "o", "Ø": "o", "đ": "d", "Đ": "d", "ł": "l", "Ł": "l", "ß": "ss", "æ": "ae", "Æ": "ae", "œ": "oe", "ı": "i", "þ": "th", "ð": "d"})
def asc(s): return unicodedata.normalize("NFKD", (s or "").translate(TRANS)).encode("ascii", "ignore").decode().lower()   # č/ć → c, ö → o, ø → o ...
def norm(s): return frozenset(t for t in re.sub(r"[^a-z ]", " ", asc(s)).split() if t not in ("jr", "sr", "ii", "iii", "iv"))
SUF = {"jr", "sr", "ii", "iii", "iv"}
def toks(s): return [t for t in re.sub(r"[^a-z. ]", " ", asc(s)).replace(".", ". ").split() if t.strip(".") and t.strip(".") not in SUF]
def key_arch(n):   # archivio: "Cognome Nome" oppure "N. Cognome" → (cognome, iniziale)
    t = toks(n)
    if len(t) < 2: return None
    if t[0].endswith("."): return (" ".join(x.strip(".") for x in t[1:]), t[0][0])
    return (" ".join(x.strip(".") for x in t[:-1]), t[-1][0])
def key_book(n):   # book: "Nome Cognome" → (cognome, iniziale)
    t = toks(n)
    return (" ".join(x.strip(".") for x in t[1:]), t[0][0]) if len(t) >= 2 else None
def show_name(n):   # API: "Cognome Nome" → "Nome Cognome"
    t = (n or "").split()
    if len(t) < 2 or t[0].endswith("."): return n or ""   # già "N. Cognome"
    if t[-1].rstrip(".").upper() in ("JR", "SR", "II", "III", "IV") and len(t) >= 3: return " ".join([t[-2]] + t[:-2] + [t[-1]])   # "Oubre Kelly Jr." → "Kelly Oubre Jr."
    return " ".join(t[-1:] + t[:-1])

def build(files, upcoming, pre, quotes, valid, today):
    """files: {(lega, stagione): file archivio}; upcoming: partite da giocare [{id, lg, h, a, d}]; pre: {id: previsione con eh, ea, pace, habh, haba, pch, pca};
    quotes: archivio quote {id: {"c": [ora, Q]}}; valid(g): partita valida per il modello. Restituisce {"gpar":..., "partite": {id: {...}}}"""
    NOMI = {}
    games = []
    for (lg, s), D in files.items():
        for k, v in (D.get("nomi") or {}).items(): NOMI[str(k)] = v
        for gid, v in D["partite"].items():
            gi = (D.get("gioc") or {}).get(gid)
            if gi and v[1] in ("FT", "AOT"): games.append((v[0], gid, lg, str(v[2]), str(v[3]), gi))
    games.sort()
    P = {}; LR = collections.defaultdict(lambda: {"m": 0.0, "pts": 0.0, "reb": 0.0, "ast": 0.0})
    ROST = collections.defaultdict(set); LASTP = {}
    for t, gid, lg, h, a, gi in games:
        d = t[:10]
        ok = [p for p in gi if p[3] and p[3] > 0 and None not in (p[4], p[11], p[12])]
        for side in (0, 1):
            pres = {str(p[0]) for p in ok if p[1] == side}
            if len(pres) >= 5: LASTP[(lg, h if side == 0 else a)] = (d, pres)
        for p in ok:
            key = (lg, str(p[0])); s = P.get(key)
            if s is None: s = P[key] = {"w": 0.0, "m": 0.0, "pts": 0.0, "reb": 0.0, "ast": 0.0, "ws": 0.0, "wb": 0.0, "team": None, "last": None}
            for k in ("w", "m", "pts", "reb", "ast", "ws", "wb"): s[k] *= DP
            s["w"] += 1; s["m"] += p[3]; s["pts"] += p[4]; s["reb"] += p[11]; s["ast"] += p[12]
            s["ws" if p[2] else "wb"] += 1
            team = h if p[1] == 0 else a; s["team"] = team; s["last"] = d; ROST[(lg, team)].add(str(p[0]))
            L = LR[(lg, 1 if p[2] else 0)]
            for k in ("m", "pts", "reb", "ast"): L[k] *= 0.999
            L["m"] += p[3]; L["pts"] += p[4]; L["reb"] += p[11]; L["ast"] += p[12]
    # quote giocatori del feed (NBA) per partita: soglie punti e punti+assist
    def qplayers(gid):
        e = quotes.get(gid) or {}
        Q = (e.get("c") or [None, {}])[1]; out = collections.defaultdict(dict)
        for v, bk in (Q.get("Player Points Milestones") or {}).items():
            mm = re.match(r"^(.*?)\s*-\s*(\d+)$", v)
            if mm and bk:
                b = max(bk.items(), key=lambda z: z[1]); out[mm.group(1)].setdefault("pt", {})[mm.group(2)] = [b[1], b[0]]
        for mk, code in (("Player Points and Assists", "pa"), ("Player Runs", "rb")):   # Player Runs = rimbalzi (sonda_runs.py 15/11: corr 0,96, scarto 0,6)
            for v, bk in (Q.get(mk) or {}).items():
                mm = re.match(r"^(.*?)\s*-\s*(Over|Under)\s+(\d+(?:\.\d+)?)$", v)
                if mm and bk:
                    b = max(bk.items(), key=lambda z: z[1]); out[mm.group(1)].setdefault(code, {}).setdefault(mm.group(3), {})[mm.group(2)[0]] = [b[1], b[0]]
        idx = {}
        sur = collections.Counter(key_book(nm)[0] for nm in out if key_book(nm))
        for nm, q in out.items():
            t0 = toks(nm); q["_i"] = t0[0][0] if t0 else None
            idx[norm(nm)] = q; k2 = key_book(nm); idx.setdefault(k2, q)
            if k2 and sur[k2[0]] == 1: idx[("cognome", k2[0])] = q   # ripiego: cognome unico nella partita
            t = toks(nm)
            if t and len(t[-1]) >= 4 and sum(1 for x in out if toks(x)[-1:] == t[-1:]) == 1: idx[("ult", t[-1])] = q   # "VJ Edgecombe" / "Edgecombe V. J."
        return idx
    OUT = {}
    for g in upcoming:
        p_ = pre.get(g["id"])
        if not p_ or "habh" not in p_: continue
        lg, d = g["lg"], g["d"][:10]
        QP = qplayers(g["id"])
        # 16/11/2026: prima gli abbinamenti sicuri (nome intero, cognome + iniziale), poi i ripieghi solo sulle voci del book rimaste libere e con
        # l'iniziale compatibile (le linee di Jaylen Brown, 76ers, finivano anche su M. J. Brown dei Nets col ripiego sul solo cognome)
        QM, used = {}, set()
        allp = list(ROST[(lg, g["h"])]) + list(ROST[(lg, g["a"])])
        for pid in allp:
            n = NOMI.get(pid, ""); hit = QP.get(norm(n)) or QP.get(key_arch(n))
            if hit: QM[pid] = hit; used.add(id(hit))
        for pid in allp:
            if pid in QM: continue
            n = NOMI.get(pid, ""); k = key_arch(n); ini = {t[0] for t in toks(n) if t}
            c = [QP.get(("cognome", k[0])) if k else None] + [QP.get(("ult", t)) for t in toks(n) if len(t) >= 4]
            for hit in c:
                if hit and id(hit) not in used and (not hit.get("_i") or hit["_i"] in ini): QM[pid] = hit; used.add(id(hit)); break
        def qof(pid):
            q = QM.get(pid)
            return {k: v for k, v in q.items() if k != "_i"} if q else None
        res = {}
        for side, team in (("h", g["h"]), ("a", g["a"])):
            regs = []
            for pid in ROST[(lg, team)]:
                s = P[(lg, pid)]
                if s["team"] != team or s["w"] < 2 or not s["last"] or (datetime.date.fromisoformat(d) - datetime.date.fromisoformat(s["last"])).days > 30: continue
                am = s["m"] / s["w"]
                if am < 12: continue
                L = LR[(lg, 1 if s["ws"] >= s["wb"] else 0)]
                if L["m"] < 500: continue
                mu = {k: (s[k] + KMIN * L[k] / L["m"]) / (s["m"] + KMIN) * am for k in ST}
                regs.append([pid, am, mu])
            if len(regs) < 5: continue
            lp = LASTP.get((lg, team))
            tot = {k: sum(r[2][k] for r in regs if r[1] >= 15) or 1 for k in ST}
            top2 = [r[0] for r in sorted(regs, key=lambda r: -r[2]["pts"])[:2]]
            nq = sum(1 for r in regs if qof(r[0]))
            for r in regs:
                why = 0
                if lp and r[0] not in lp[1] and r[1] >= 15: why = 1                       # mancava all'ultima partita
                elif QP and nq >= 4 and r[0] in top2 and not qof(r[0]): why = 2   # NBA: non quotato dai book
                r.append(why)
            miss = {k: sum(r[2][k] for r in regs if r[3] and r[1] >= 15) / tot[k] for k in ST}
            eh, hab, pc = (p_["eh"], p_["habh"], p_["pch"]) if side == "h" else (p_["ea"], p_["haba"], p_["pca"])
            rows = []
            for pid, am, mu, why in sorted(regs, key=lambda r: -r[1]):
                m2 = {}
                for k in ST:
                    sc = (eh / hab) if k != "reb" else (p_["pace"] / pc)
                    m2[k] = round(mu[k] * sc ** ALPHA[k] * (1 + (0 if why else BETA[k] * miss[k])), 2)
                q = qof(pid) or {}
                rows.append([show_name(NOMI.get(pid, pid)), pid, round(am, 1), m2["pts"], m2["reb"], m2["ast"], why, q or None])
            res[side] = {"g": rows[:10], "miss": {k: round(v, 3) for k, v in miss.items()}, "ultima": lp[0] if lp else None}
        if res: OUT[g["id"]] = res
    return {"gpar": GPAR, "partite": OUT}
