"""Basket · file del sito data/basket.json (15/11/2026). Stesso modello di tools/basket/modello.py (parametri scelti nel periodo scelta:
DP 0,97, K 6; σ robuste per campionato dal periodo scelta), calcolato point-in-time su tutto l'archivio.
Contenuto: partite degli ultimi 10 giorni (con la previsione fatta prima) e dei prossimi 7, linee del giorno dei book (dalla lettura più recente
dell'archivio quote: SOLO le linee in corso, nessuno storico), tabelle del Grado (quante volte previsioni simili sono uscite, verifica + holdout),
classifiche, ultime partite, precedenti, tendenze dei campionati e serie aperte delle squadre.
Uso: python tools/basket/pubblica.py ARCHIVIO_DIR QUOTE.json USCITA.json"""
import json, glob, os, sys, math, collections, datetime, re
DIR, QF, OUT = (sys.argv[1:4] + ["basket", "quote_basket.json", "basket.json"][len(sys.argv) - 1:])[:3]
FDIR = sys.argv[4] if len(sys.argv) > 4 else None   # 15/11/2026: archivio falli (ramo basket-falli: ESPN per NBA, sito Eurolega per EL/EC)
DP, K = 0.97, 6.0
SCELTA, VERIFICA = "2024-06-30", "2025-06-30"
NOMI = {"NBA": ("NBA", "USA"), "EL": ("Eurolega", "Europa"), "EC": ("Eurocup", "Europa"), "ITA": ("Serie A", "Italia"), "ACB": ("Liga ACB", "Spagna"),
        "BBL": ("BBL", "Germania"), "LNB": ("LNB Élite", "Francia")}
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
now = datetime.datetime.now(datetime.timezone.utc); today = now.strftime("%Y-%m-%d")

files = {}
for fn in sorted(glob.glob(os.path.join(DIR, "*.json"))):
    D = json.load(open(fn)); files[(D["lega"], D["stagione"])] = D
cur = {}   # stagione in corso per campionato = l'ultima
for (lg, s) in files:
    if lg not in cur or s > cur[lg]: cur[lg] = s
squadre, loghi = collections.defaultdict(dict), collections.defaultdict(dict)
G = []   # tutte le partite (finite e no)
for (lg, s), D in files.items():
    for k, v in D.get("squadre", {}).items(): squadre[lg][k] = v
    for k, v in D.get("loghi", {}).items(): loghi[lg][k] = v
    for gid, v in D["partite"].items():
        G.append({"id": gid, "lg": lg, "s": s, "d": v[0], "st": v[1], "h": str(v[2]), "a": str(v[3]), "sh": v[4], "sa": v[5], "stat": D["stat"].get(gid)})
G.sort(key=lambda g: (g["d"], g["id"]))
fin = lambda g: g["st"] in ("FT", "AOT") and g["sh"] and g["sa"] and g["sh"][5] is not None and g["sa"][5] is not None
cnt = collections.Counter()
for g in G:
    if fin(g): cnt[(g["lg"], g["s"], g["h"])] += 1; cnt[(g["lg"], g["s"], g["a"])] += 1
# soglia All-Star: metà della mediana delle partite giocate dalle squadre in quella stagione (max 15). Con 15 fisso la stagione in corso
# dei campionati europei (6-9 partite a squadra) restava fuori dal modello (15/11/2026)
_med = collections.defaultdict(list)
for (l_, s_, t_), n_ in cnt.items(): _med[(l_, s_)].append(n_)
THR = {k: min(15, max(2, sorted(v)[len(v) // 2] / 2)) for k, v in _med.items()}
def valid(g):   # come nel test: fuori All-Star, interrotte, a tavolino
    t = THR.get((g["lg"], g["s"]), 15)
    return fin(g) and g["sh"][5] + g["sa"][5] >= 100 and g["sh"][0] is not None and cnt[(g["lg"], g["s"], g["h"])] >= t and cnt[(g["lg"], g["s"], g["a"])] >= t
# 15/11/2026 (Denny, harness tools/basket/test_possessi.py): possessi = FGA − OREB + TOV + 0,44·FTA con
#  - formato nuovo di API-Basketball (dall'8/1/2026): FGA = tiri da 2 + tiri da 3; rimbalzi offensivi assenti → rimbalzi totali × quota offensiva
#    del campionato (media mobile delle partite che li avevano);
#  - statistiche rotte scartate (punti ogni 100 possessi fuori da 70-160 o possessi delle due squadre diversi oltre il 12%) → calcolo di riserva.
#  Errore medio sul totale in verifica da 15,03 a 14,41 punti (Serie A ed Eurocup soprattutto). La preseason NBA resta: toglierla peggiora.
NUOVO_FORMATO = "2026-01-05"
QOR = collections.defaultdict(lambda: [0.0, 0.0])
def poss_game(g):
    S = g["stat"] or {}; q = QOR[g["lg"]]; out = []
    for x, pts in ((S.get("h"), g["sh"][5]), (S.get("a"), g["sa"][5])):
        v = None
        if x and None not in (x[1], x[12], x[5]):
            if x[7] is not None:
                v = x[1] - x[7] + x[12] + 0.44 * x[5]
                if x[6]: q[0] = q[0] * 0.998 + 1; q[1] = q[1] * 0.998 + x[7] / x[6]
            elif x[6] and q[0] > 20:
                fga = x[1] + (x[3] or 0) if g["d"][:10] >= NUOVO_FORMATO else x[1]
                v = fga - q[1] / q[0] * x[6] + x[12] + 0.44 * x[5]
        out.append(v)
    qh, qa = out
    if qh and qa:
        m_ = (qh + qa) / 2
        if not (70 < 100 * g["sh"][5] / qh < 160 and 70 < 100 * g["sa"][5] / qa < 160) or abs(qh - qa) / m_ > 0.12: return None, None
    return qh, qa
# falli di squadra attesi (informativi, Lettura; test tools/basket/test_falli.py: falli totali z −22 verifica, −14 holdout, 7/7 campionati):
# falli commessi = media di (falli che la squadra commette di solito, falli che l'avversaria subisce di solito), media mobile DP 0,90, K 0,5 partite,
# ± metà della differenza casa/trasferta del campionato. Solo se entrambe le squadre hanno falli negli ultimi 45 giorni (API-Basketball non li passa più
# dall'8/1/2026: restano NBA, Eurolega ed Eurocup dalle fonti gratuite).
EXTF = {}
if FDIR and os.path.isdir(FDIR):
    for fn in glob.glob(os.path.join(FDIR, "*.json")):
        try:
            for gid_, v in json.load(open(fn))["partite"].items():
                if v["h"][0] is not None and v["a"][0] is not None: EXTF[gid_] = (v["h"][0], v["a"][0])
        except Exception: pass
FT = collections.defaultdict(lambda: [0.0, 0.0, 0.0, None]); LF = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
def fouls_of(g):
    if g["id"] in EXTF: return EXTF[g["id"]]
    S = g["stat"] or {}
    if S.get("h") and S.get("a") and S["h"][13] is not None and S["a"][13] is not None and S["h"][13] > 5 and S["a"][13] > 5: return (S["h"][13], S["a"][13])
    return None
# rimbalzi attesi (informativi, Lettura): rimbalzi presi e concessi ogni 100 possessi (media mobile DP, ristretti con K partite verso il campionato)
RB = collections.defaultdict(lambda: [0.0, 0.0, 0.0]); LRB = collections.defaultdict(lambda: [0.0, 0.0])

T = collections.defaultdict(lambda: {"n": 0.0, "pace": 0.0, "off": 0.0, "dfn": 0.0, "pts": 0.0, "g": 0})
L = collections.defaultdict(lambda: {"n": 0.0, "pace": 0.0, "rtg": 0.0, "hca": 0.0, "h1": 0.0, "h1n": 0.0})
def predict(lg, h, a, day=None):
    Lg = L[lg]
    if Lg["n"] < 30: return None
    lp, lr, hca = Lg["pace"] / Lg["n"], Lg["rtg"] / Lg["n"], Lg["hca"] / Lg["n"]
    th, ta = T[(lg, h)], T[(lg, a)]
    sh = lambda t, k, b: (t[k] + K * b) / (t["n"] + K)
    pace = sh(th, "pace", lp) * sh(ta, "pace", lp) / lp
    eh = pace * sh(th, "off", lr) * sh(ta, "dfn", lr) / lr / 100 + hca / 2
    ea = pace * sh(ta, "off", lr) * sh(th, "dfn", lr) / lr / 100 - hca / 2
    h1 = Lg["h1"] / Lg["h1n"] if Lg["h1n"] else 0.5
    out = {"eh": round(eh, 2), "ea": round(ea, 2), "pace": round(pace, 1), "h1": round(h1, 4), "nh": th["g"], "na": ta["g"],
           "habh": round(sh(th, "pts", lp * lr / 100), 2), "haba": round(sh(ta, "pts", lp * lr / 100), 2), "pch": round(sh(th, "pace", lp), 2), "pca": round(sh(ta, "pace", lp), 2)}
    lr_ = LRB[lg]
    if lr_[0] > 30:
        lrate = lr_[1] / lr_[0]
        def g_(t, i): x = RB[(lg, t)]; return (x[i] + K * lrate) / (x[0] + K)
        out["rh"] = round(pace * (g_(h, 1) + g_(a, 2)) / 2 / 100, 1); out["ra"] = round(pace * (g_(a, 1) + g_(h, 2)) / 2 / 100, 1)
    lf_ = LF[lg]; fh_, fa_ = FT[(lg, h)], FT[(lg, a)]
    if lf_[0] > 30 and fh_[0] >= 3 and fa_[0] >= 3 and day and all(x[3] and (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(x[3])).days <= 45 for x in (fh_, fa_)):
        lfm, lhd = lf_[1] / lf_[0], lf_[2] / lf_[0]
        def f_(x, i): return (x[i] + 0.5 * lfm) / (x[0] + 0.5)
        out["fh"] = round((f_(fh_, 1) + f_(fa_, 2)) / 2 + lhd / 2, 1); out["fa"] = round((f_(fa_, 1) + f_(fh_, 2)) / 2 - lhd / 2, 1)
    return out
hist = []   # (lega, data, previsione, punti casa, punti ospite) per σ e Grado
PRE = {}
for g in G:
    lg = g["lg"]
    if g["d"][:10] >= (now - datetime.timedelta(days=10)).strftime("%Y-%m-%d") or not fin(g):
        p = predict(lg, g["h"], g["a"], g["d"][:10])
        if p: PRE[g["id"]] = p
    if not valid(g): continue
    p = predict(lg, g["h"], g["a"])
    ph, pa = g["sh"][5], g["sa"][5]
    if p and p["nh"] >= 5 and p["na"] >= 5: hist.append((lg, g["d"][:10], p, ph, pa))
    S = g["stat"] or {}; qh, qa = poss_game(g); Lg = L[lg]
    P = (qh + qa) / 2 if qh and qa else ((ph + pa) / 2 / (Lg["rtg"] / Lg["n"] / 100) if Lg["n"] > 0 else (ph + pa) / 2 / 1.1)
    if S.get("h") and S.get("a") and S["h"][6] and S["a"][6]:
        for t, f_, a_ in ((g["h"], S["h"][6], S["a"][6]), (g["a"], S["a"][6], S["h"][6])):
            x = RB[(lg, t)]; x[0] = x[0] * DP + 1; x[1] = x[1] * DP + 100 * f_ / P; x[2] = x[2] * DP + 100 * a_ / P
        x = LRB[lg]; x[0] = x[0] * 0.998 + 2; x[1] = x[1] * 0.998 + 100 * (S["h"][6] + S["a"][6]) / P
    f = fouls_of(g)
    if f:
        for t, fc, fd in ((g["h"], f[0], f[1]), (g["a"], f[1], f[0])):
            x = FT[(lg, t)]; x[0] = x[0] * 0.9 + 1; x[1] = x[1] * 0.9 + fc; x[2] = x[2] * 0.9 + fd; x[3] = g["d"][:10]
        x = LF[lg]; x[0] = x[0] * 0.998 + 1; x[1] = x[1] * 0.998 + (f[0] + f[1]) / 2; x[2] = x[2] * 0.998 + f[0] - f[1]
    for t, pf, pa_ in ((T[(lg, g["h"])], ph, pa), (T[(lg, g["a"])], pa, ph)):
        for k in ("n", "pace", "off", "dfn", "pts"): t[k] *= DP
        t["n"] += 1; t["pace"] += P; t["off"] += 100 * pf / P; t["dfn"] += 100 * pa_ / P; t["pts"] += pf; t["g"] += 1
    for k in ("n", "pace", "rtg", "hca", "h1", "h1n"): Lg[k] *= 0.998
    Lg["n"] += 1; Lg["pace"] += P; Lg["rtg"] += 100 * (ph + pa) / 2 / P; Lg["hca"] += ph - pa
    if g["sh"][1] is not None and g["sa"][1] is not None:
        Lg["h1"] += (g["sh"][0] + g["sh"][1] + g["sa"][0] + g["sa"][1]) / (ph + pa); Lg["h1n"] += 1
# σ robuste dal periodo scelta (come il test)
import statistics
def rob(x): m = statistics.median(x); return 1.4826 * statistics.median([abs(z - m) for z in x])
SIG = {}
for lg in NOMI:
    s = [(ph - pa) - (p["eh"] - p["ea"]) for l, d, p, ph, pa in hist if l == lg and d <= SCELTA]
    t = [(ph + pa) - (p["eh"] + p["ea"]) for l, d, p, ph, pa in hist if l == lg and d <= SCELTA]
    if len(s) > 100: SIG[lg] = [round(rob(s), 2), round(rob(t), 2)]
# Grado: per mercato e probabilità della lettura (fasce di 5 punti), quante volte è uscita (verifica + holdout)
grado = {m: collections.defaultdict(lambda: [0, 0]) for m in ("vittoria", "totale", "handicap")}
for lg, d, p, ph, pa in hist:
    if d <= SCELTA or lg not in SIG: continue
    ss, st = SIG[lg]; ms, mt = p["eh"] - p["ea"], p["eh"] + p["ea"]
    pw = Phi(ms / ss); q = max(pw, 1 - pw); y = (ph > pa) == (pw >= 0.5)
    b = grado["vittoria"][int(q * 20)]; b[0] += 1; b[1] += y
    for off in (-12, -8, -4, 0, 4, 8, 12):
        Lt = round(mt) + 0.5 + off; po = 1 - Phi((Lt - mt) / st); q = max(po, 1 - po); y = (ph + pa > Lt) == (po >= 0.5)
        b = grado["totale"][int(q * 20)]; b[0] += 1; b[1] += y
        Ls = round(ms) + 0.5 + off / 2; pc = 1 - Phi((Ls - ms) / ss); q = max(pc, 1 - pc); y = (ph - pa > Ls) == (pc >= 0.5)
        b = grado["handicap"][int(q * 20)]; b[0] += 1; b[1] += y
GRADO = {m: {str(k): [v[0], round(v[1] / v[0], 4)] for k, v in sorted(t.items()) if v[0] >= 30} for m, t in grado.items()}

# linee del giorno dalla lettura più recente dell'archivio quote
LINEE = {}
try: QA = json.load(open(QF)).get("partite", {})
except Exception: QA = {}
def best(d): return max(d.items(), key=lambda z: z[1]) if d else (None, None)
def avg(d): return round(sum(d.values()) / len(d), 3) if d else None
for gid, e in QA.items():
    if not e.get("c") or e.get("d", "")[:10] < today: continue
    Q = e["c"][1]; out = {"ora": e["c"][0]}
    ml = Q.get("Home/Away") or {}
    if ml.get("Home") and ml.get("Away"):
        bh, ba = best(ml["Home"]), best(ml["Away"]); out["ml"] = [bh[1], bh[0], ba[1], ba[0], avg(ml["Home"]), avg(ml["Away"]), ml["Home"].get("Pinnacle"), ml["Away"].get("Pinnacle")]
    def pairs(m, a_, b_):
        R = {}
        for k, v in (Q.get(m) or {}).items():
            mm = re.match(r"^(\w+)\s+([+-]?\d+(?:\.\d+)?)$", k)
            if mm: R.setdefault(float(mm.group(2)), {})[mm.group(1)] = v
        return {x: y for x, y in R.items() if a_ in y and b_ in y}
    for key, m, A_, B_ in (("tot", "Over/Under", "Over", "Under"), ("hcp", "Asian Handicap", "Home", "Away"), ("tot1", "Over/Under 1st Half", "Over", "Under")):
        R = pairs(m, A_, B_)
        if not R: continue
        # linea principale: quella con più book e quote più vicine tra loro (Pinnacle se c'è)
        def bal(x): y = R[x]; a_, b_ = avg(y[A_]), avg(y[B_]); return (-min(len(y[A_]), len(y[B_])), abs(a_ - b_))
        Lx = min(R, key=bal); y = R[Lx]; ba_, bb_ = best(y[A_]), best(y[B_])
        out[key] = [Lx, ba_[1], ba_[0], bb_[1], bb_[0], avg(y[A_]), avg(y[B_]), y[A_].get("Pinnacle"), y[B_].get("Pinnacle"), min(len(y[A_]), len(y[B_]))]
    LINEE[gid] = out

# partite pubblicate: ultimi 10 giorni e prossimi 7
lo, hi = (now - datetime.timedelta(days=10)).strftime("%Y-%m-%d"), (now + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
PART = []
for g in G:
    if not (lo <= g["d"][:10] <= hi) or g["st"] in ("CANC", "POST", "ABD"): continue
    p = PRE.get(g["id"])
    if not p and not fin(g): continue
    PART.append({"id": g["id"], "lg": g["lg"], "d": g["d"], "st": g["st"], "h": g["h"], "a": g["a"], "sh": g["sh"] if fin(g) else None, "sa": g["sa"] if fin(g) else None, "p": p,
                 "stat": g["stat"] if fin(g) else None, "fl": fouls_of(g) if fin(g) else None})
# classifiche, ultime partite, precedenti, tendenze, serie aperte (stagione in corso, solo partite valide)
# 15/11/2026 (Denny: Precedenti e Rendimento come il calcio): statistiche della partita dal lato della squadra
# [rimbalzi fatti, subiti, assist f, s, triple f, s, palle perse f, s, falli f, s, 1° tempo f, s] (None se mancano)
def gstats(g, home):
    S = g["stat"] or {}; a, b = (S.get("h"), S.get("a")) if home else (S.get("a"), S.get("h")); f = fouls_of(g)
    if f and not home: f = (f[1], f[0])
    out = []
    for i in (6, 9, 2, 12):
        out += [a[i] if a else None, b[i] if b else None]
    out += [f[0], f[1]] if f else [None, None]
    sh, sa = (g["sh"], g["sa"]) if home else (g["sa"], g["sh"])
    out += [sh[0] + sh[1], sa[0] + sa[1]] if sh[1] is not None and sa[1] is not None else [None, None]
    return out
REND = {}
CLA, ULT, TEN, SER = {}, collections.defaultdict(list), {}, {}
for lg, s in cur.items():
    rows = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    gs = [g for g in G if g["lg"] == lg and g["s"] == s and valid(g)]
    for g in gs:
        ph, pa = g["sh"][5], g["sa"][5]
        for t, pf, pa_, w in ((g["h"], ph, pa, ph > pa), (g["a"], pa, ph, pa > ph)):
            r = rows[t]; r[0] += 1; r[1] += w; r[2] += 1 - w; r[3] += pf; r[4] += pa_
    RD = collections.defaultdict(lambda: {"home": collections.defaultdict(lambda: [0, 0, 0, 0]), "away": collections.defaultdict(lambda: [0, 0, 0, 0])})
    for g in gs:
        for t, home in ((g["h"], 1), (g["a"], 0)):
            st = gstats(g, home); pf, pa = (g["sh"][5], g["sa"][5]) if home else (g["sa"][5], g["sh"][5])
            for k, (x, y) in (("pts", (pf, pa)), ("reb", st[0:2]), ("ast", st[2:4]), ("tre", st[4:6]), ("pp", st[6:8]), ("fl", st[8:10]), ("h1", st[10:12])):
                if x is None or y is None: continue
                c = RD[t]["home" if home else "away"][k]; c[0] += x; c[1] += y; c[2] += x > y; c[3] += 1
    REND[lg] = {t: {v: dict(d) for v, d in x.items()} for t, x in RD.items()}
    CLA[lg] = sorted([[t] + r for t, r in rows.items()], key=lambda r: (-(r[2] / r[1] if r[1] else 0), -(r[4] - r[5])))
    if gs:
        tot = [g["sh"][5] + g["sa"][5] for g in gs]
        TEN[lg] = {"partite": len(gs), "media_punti": round(sum(tot) / len(gs), 1), "casa_vince": round(sum(g["sh"][5] > g["sa"][5] for g in gs) / len(gs), 3),
                   "supplementari": round(sum(1 for g in gs if (g["sh"][4] or 0) + (g["sa"][4] or 0) > 0) / len(gs), 3),
                   "scarto_medio": round(sum(abs(g["sh"][5] - g["sa"][5]) for g in gs) / len(gs), 1), "max_punti": max(tot), "min_punti": min(tot)}
for g in G:
    if not valid(g) or g["d"][:10] < (now - datetime.timedelta(days=400)).strftime("%Y-%m-%d"): continue
    for t, o, home, pf, pa in ((g["h"], g["a"], 1, g["sh"][5], g["sa"][5]), (g["a"], g["h"], 0, g["sa"][5], g["sh"][5])):
        ULT[(g["lg"], t)].append([g["d"][:10], o, home, pf, pa] + gstats(g, home))
ULTP = {f"{lg}|{t}": v[-10:] for (lg, t), v in ULT.items() if lg in cur}
for (lg, t), v in ULT.items():
    if lg not in cur or not v: continue
    def streak(f):
        n = 0
        for r in reversed(v):
            if f(r) is None: continue
            if f(r): n += 1
            else: break
        return n
    SER[f"{lg}|{t}"] = {"vittorie": streak(lambda r: r[3] > r[4]), "sconfitte": streak(lambda r: r[3] < r[4]),
                        "vittorie_casa": streak(lambda r: (r[3] > r[4]) if r[2] else None), "sconfitte_trasferta": streak(lambda r: (r[3] < r[4]) if not r[2] else None),
                        "sopra_media": streak(lambda r: (r[3] + r[4]) > TEN.get(lg, {}).get("media_punti", 999)), "sotto_media": streak(lambda r: (r[3] + r[4]) < TEN.get(lg, {}).get("media_punti", 0))}
PREC = {}
for g in PART:
    if g["sh"] is not None: continue
    pr = [[x["d"][:10], x["h"], x["a"], x["sh"][5], x["sa"][5]] + gstats(x, 1) for x in G if valid(x) and x["lg"] == g["lg"] and {x["h"], x["a"]} == {g["h"], g["a"]}]
    PREC[g["id"]] = pr[-8:]
RITMO = {lg: round(L[lg]["pace"] / L[lg]["n"], 1) for lg in NOMI if L[lg]["n"]}
# 15/11/2026: giocatori (punti, rimbalzi, assist, punti+assist, doppia/tripla doppia) per le partite dei prossimi 3 giorni
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import giocatori_pub
hi3 = (now + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
GIOC = giocatori_pub.build(files, [g for g in PART if g["sh"] is None and g["d"][:10] <= hi3 and g["st"] == "NS"], PRE, QA, valid, today)
J = {"agg": now.strftime("%Y-%m-%d %H:%M"), "ritmo": RITMO, "leghe": {k: list(v) for k, v in NOMI.items()}, "stagioni": cur, "sigma": SIG, "grado": GRADO,
     "squadre": {lg: {k: [v, loghi[lg].get(k, "")] for k, v in d.items()} for lg, d in squadre.items()},
     "partite": PART, "linee": LINEE, "classifica": CLA, "ultime": ULTP, "precedenti": PREC, "tendenze": TEN, "serie": SER, "giocatori": GIOC, "rendimento": REND}
json.dump(J, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
fut = [g for g in PART if g["sh"] is None]
chk = []
for g in fut:
    l = LINEE.get(g["id"], {})
    if "hcp" in l and g["p"]: chk.append(f"{squadre[g['lg']].get(g['h'])}: atteso {g['p']['eh'] - g['p']['ea']:+.1f}, linea Home {l['hcp'][0]:+g}")
print(f"::notice title=Basket · sito::partite {len(PART)} (in programma {len(fut)}, con linee {sum(1 for g in fut if g['id'] in LINEE)}) · σ {SIG} · dimensione {os.path.getsize(OUT) // 1024} KB")
if chk: print("::notice title=Basket · verso dell'handicap::" + " | ".join(chk[:8]))
