"""Ricerca a 360 gradi (9/11/2026, richiesta di Denny): qualsiasi vantaggio verificabile contro i bookmaker sui nostri archivi.
Gira nel runner sull'archivio privato (data/odds_hist.json, data/apif.json, ramo tempi) più rm_all.json e q23_candidati.json prodotti nello
stesso runner con i soli dati precedenti a ogni partita. Stampa SOLO numeri aggregati.
Filoni:
  1  sharp contro soft: Pinnacle senza margine (p.*) come probabilità "vera"; si gioca la quota di 1xBet (x.*) o la più alta tra i book
     (m.*, dal 6/11) quando batte la quota equa di Pinnacle; con e senza l'accordo di Prevista.
  2  struttura delle linee: linee intere (rimborso) contro linee x,5; Over contro Under per mercato e per linea; handicap asiatici.
  3  1° tempo contro partita: corner del 1° tempo di 1xBet contro la frazione reale (ramo tempi) applicata alla linea della partita.
  4  formazioni ufficiali: quota di 1xBet subito dopo le formazioni (prima tappa dopo -60') contro la quota finale, sui falli 1X2 dove
     Prevista con le formazioni si sposta.
  5  cassa: puntata fissa, Kelly frazionale, proporzionale al vantaggio, su ciascuna strategia rimasta; Monte Carlo per giorni.
Rimborso: linea intera con valore uguale → puntata restituita (profitto 0). Rendimento = profitto / puntato. IC 95% bootstrap per partita.
Molti test insieme: per ogni regola si riportano le due metà dei giorni e il p-value; con 100+ test un p < 0,01 isolato può essere caso."""
import json, os, sys, glob, math, csv, io, collections, datetime, traceback
import numpy as np
from scipy.special import gammaln
sys.excepthook = lambda t, v, tb: print("::error title=360::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
note = lambda t, m: print(f"::notice title=360 · {t}::" + m.replace("%", "%25").replace("\n", " "))
rng = np.random.default_rng(7)
OH = json.load(open("data/odds_hist.json"))
RM = json.load(open("rm_all.json")) if os.path.exists("rm_all.json") else []
REAL, PO = {}, {}
for r in RM:
    REAL[(r["key"], r["k"])] = r.get("real")
    PO[(r["key"], r["k"], r["L"])] = (r["po"], r.get("mu"))
DAYS = sorted({k.split("|")[1] for k in OH})
note("archivi", f"quote: {len(OH)} partite, {DAYS[0] if DAYS else '-'} → {DAYS[-1] if DAYS else '-'} · statistiche reali abbinate (corner, cartellini, tiri, falli): {len({k for k, _ in REAL})} partite")

def val(v): return v[0] if isinstance(v, list) else v
def lines(q, mk, want_max=False):
    """{linea: {"O": quota, "U": quota}} per il mercato mk (es. "p.cou"); con want_max per le chiavi m.: quota massima e book"""
    L = {}
    for k, v in q.items():
        if not k.startswith(mk + ":"): continue
        parts = k.split(":", 1)[1].split(" ")
        if len(parts) != 2 or parts[0] not in ("Over", "Under"): continue
        try: ln = float(parts[1])
        except Exception: continue
        if want_max:
            if not isinstance(v, list) or len(v) < 4 or v[3] == "Pinnacle": continue
            L.setdefault(ln, {})[parts[0][0]] = (v[2], v[3])
        else:
            o = val(v)
            if o and o > 1: L.setdefault(ln, {})[parts[0][0]] = o
    return L
def settle(side, L, real):   # profitto per 1 unità alla quota o: restituisce (esito 1/0/None rimborso)
    if real is None: return None
    if abs(real - L) < 1e-9: return "R"
    return 1 if (real > L) == (side == "O") else 0
def stats(B, label=""):
    """B: lista di dict con key, d, o, y ("R" = rimborso)"""
    B = [b for b in B if b["y"] is not None]
    if not B: return "nessuna", None
    pl = np.array([0.0 if b["y"] == "R" else (b["o"] - 1 if b["y"] else -1.0) for b in B]); roi = pl.mean()
    g = collections.defaultdict(float)
    for b, v in zip(B, pl): g[b["key"]] += v - roi
    ci = 1.96 * math.sqrt(sum(v * v for v in g.values())) / len(B)
    se = ci / 1.96 if ci > 0 else 1e-9; z = roi / se; pv = math.erfc(abs(z) / math.sqrt(2))
    half = DAYS[len(DAYS) // 2] if DAYS else ""
    h1 = [v for b, v in zip(B, pl) if b["d"] < half]; h2 = [v for b, v in zip(B, pl) if b["d"] >= half]
    won = sum(1 for b in B if b["y"] == 1); dec = sum(1 for b in B if b["y"] != "R")
    s = (f"{len(B)} · presa {100 * won / max(1, dec):.0f}% · quota {np.mean([b['o'] for b in B]):.2f} · rendimento {100 * roi:+.1f}% ±{100 * ci:.0f} (p {pv:.3f})"
         f" · metà {100 * np.mean(h1) if h1 else float('nan'):+.0f}% / {100 * np.mean(h2) if h2 else float('nan'):+.0f}%")
    return s, dict(n=len(B), roi=roi, ci=ci, p=pv, h1=np.mean(h1) if h1 else None, h2=np.mean(h2) if h2 else None, B=B, pl=pl)
RULES = {}   # nome → risultato (per il filone 5)
def keep(name, res):
    if res and res["n"] >= 30: RULES[name] = res

# ================= 1 · SHARP (Pinnacle) contro SOFT =================
MK = {"cou": "c", "hcou": "hc", "acou": "ac", "kou": "k", "sou": "s", "sot": "st", "fou": "f"}
NAME = {"cou": "corner totali", "hcou": "corner casa", "acou": "corner ospite", "kou": "cartellini", "sou": "tiri", "sot": "tiri in porta", "fou": "falli"}
cov = collections.Counter(); B1 = collections.defaultdict(list); CAL = collections.defaultdict(lambda: [[], [], []])
for key, x in OH.items():
    q = (x.get("ultima") or {}).get("q") or {}; d = key.split("|")[1]
    for mk, k in MK.items():
        P = lines(q, "p." + mk)
        if not P: continue
        cov[mk] += 1
        X, M = lines(q, "x." + mk), lines(q, "m." + mk, True)
        real = REAL.get((key, k))
        for L, po in P.items():
            if "O" not in po or "U" not in po: continue
            fo = (1 / po["O"]) / (1 / po["O"] + 1 / po["U"])
            if real is not None and abs(real - L) > 1e-9 and abs(L - round(L)) > 0.1:   # calibrazione su linee x,5
                CAL[mk][0].append(fo); CAL[mk][1].append(1 if real > L else 0)
                xo = X.get(L)
                if xo and "O" in xo and "U" in xo: CAL[mk][2].append(((1 / xo["O"]) / (1 / xo["O"] + 1 / xo["U"]), fo, 1 if real > L else 0))
            for side in ("O", "U"):
                pf = fo if side == "O" else 1 - fo
                pp = PO.get((key, k, L)); pv = None if pp is None else (pp[0] if side == "O" else 1 - pp[0])
                for src, D in (("1xBet", X), ("max", M)):
                    o = D.get(L, {}).get(side)
                    if not o: continue
                    bk = None
                    if src == "max": o, bk = o
                    ev = pf * o - 1
                    B1[(mk, src)].append(dict(key=key, d=d, o=o, y=settle(side, L, real), ev=ev, pv=pv, pf=pf, side=side, L=L, bk=bk))
note("1 · copertura Pinnacle", " · ".join(f"{NAME[m]} {n} partite" for m, n in cov.items()) or "nessuna quota Pinnacle in archivio")
cal_txt = []
for mk, (F, Y, XP) in CAL.items():
    if len(Y) < 50: continue
    F, Y = np.array(F), np.array(Y)
    br = np.mean((F - Y) ** 2)
    xb = np.mean([(a - y) ** 2 for a, b, y in XP]) if XP else float("nan"); pb = np.mean([(b - y) ** 2 for a, b, y in XP]) if XP else float("nan")
    cal_txt.append(f"{NAME[mk]}: Brier Pinnacle {br:.4f} su {len(Y)} linee · sulle stesse linee 1xBet {xb:.4f} contro Pinnacle {pb:.4f} ({len(XP)})")
note("1 · Pinnacle più preciso di 1xBet? (Brier, più basso = meglio)", " ‖ ".join(cal_txt) or "pochi dati")
for (mk, src), L in sorted(B1.items()):
    if len([b for b in L if b["y"] is not None]) < 20: continue
    out = []
    for lab, f in (("tutte le quote (alla cieca)", lambda b: True), ("valore contro Pinnacle > 0", lambda b: b["ev"] > 0), ("> +3%", lambda b: b["ev"] > 0.03),
                   ("> +6%", lambda b: b["ev"] > 0.06), ("> 0 e Prevista d'accordo", lambda b: b["ev"] > 0 and b["pv"] is not None and b["pv"] * b["o"] > 1),
                   ("> 0 ma Prevista contro", lambda b: b["ev"] > 0 and b["pv"] is not None and b["pv"] * b["o"] <= 1)):
        s, r = stats([b for b in L if f(b)]); out.append(f"{lab}: {s}")
        if lab != "tutte le quote (alla cieca)": keep(f"Sharp · {NAME[mk]} · {src} · {lab}", r)
    note(f"1 · {NAME[mk]} · quota {'di 1xBet' if src == '1xBet' else 'più alta tra i book (dal 6/11)'} contro la equa di Pinnacle", " ‖ ".join(out))
# tutti i mercati insieme, 1xBet e massimo
for src in ("1xBet", "max"):
    A_ = [b for (mk, s_), L in B1.items() if s_ == src for b in L]
    out = []
    for th in (0, 0.02, 0.04, 0.06, 0.10):
        s, r = stats([b for b in A_ if b["ev"] > th]); out.append(f"valore > {100 * th:.0f}%: {s}"); keep(f"Sharp · tutti i mercati · {src} · valore > {100 * th:.0f}%", r)
    note(f"1 · tutti i mercati O/U · quota {'1xBet' if src == '1xBet' else 'più alta'} contro Pinnacle", " ‖ ".join(out))
# 1X2 corner: Pinnacle (p.c1x2) contro 1xBet (x.c1x2) e massimo (m.c1x2)
B1x = collections.defaultdict(list)
for key, x in OH.items():
    q = (x.get("ultima") or {}).get("q") or {}; d = key.split("|")[1]
    P = [val(q.get("p.c1x2:" + s)) for s in ("Home", "Draw", "Away")]
    if not all(v and v > 1 for v in P): continue
    hc, ac = REAL.get((key, "hc")), REAL.get((key, "ac"))
    res = None if hc is None or ac is None else ("Home" if hc > ac else "Draw" if hc == ac else "Away")
    inv = [1 / v for v in P]; t = sum(inv); fair = dict(zip(("Home", "Draw", "Away"), [v / t for v in inv]))
    for s in ("Home", "Draw", "Away"):
        for src, kk in (("1xBet", "x.c1x2:"), ("max", "m.c1x2:")):
            v = q.get(kk + s)
            if not v: continue
            if src == "max":
                if not isinstance(v, list) or len(v) < 4 or v[3] == "Pinnacle": continue
                o = v[2]
            else: o = val(v)
            B1x[src].append(dict(key=key, d=d, o=o, y=None if res is None else (1 if res == s else 0), ev=fair[s] * o - 1))
for src, L in B1x.items():
    out = []
    for th in (0, 0.03, 0.06):
        s, r = stats([b for b in L if b["ev"] > th]); out.append(f"valore > {100 * th:.0f}%: {s}"); keep(f"Sharp · 1X2 corner · {src} · valore > {100 * th:.0f}%", r)
    note(f"1 · 1X2 corner · quota {'1xBet' if src == '1xBet' else 'più alta'} contro Pinnacle", " ‖ ".join(out))

# ================= 2 · STRUTTURA DELLE LINEE =================
B2 = collections.defaultdict(list)
for key, x in OH.items():
    q = (x.get("ultima") or {}).get("q") or {}; d = key.split("|")[1]
    for mk, k in MK.items():
        real = REAL.get((key, k))
        if real is None: continue
        X = lines(q, "x." + mk); P = lines(q, "p." + mk)
        for L, xo in X.items():
            typ = "intera" if abs(L - round(L)) < 1e-9 else "x,5" if abs(L - math.floor(L) - 0.5) < 1e-9 else "quarto"
            for side in ("O", "U"):
                if side not in xo: continue
                pp = PO.get((key, k, L)); pv = None if pp is None else (pp[0] if side == "O" else 1 - pp[0])
                B2[(mk, typ, side)].append(dict(key=key, d=d, o=xo[side], y=settle(side, L, real), L=L, pv=pv))
out = []
for mk in MK:
    for typ in ("intera", "x,5", "quarto"):
        for side in ("O", "U"):
            L = B2.get((mk, typ, side), [])
            if len([b for b in L if b["y"] is not None]) < 40: continue
            s, r = stats(L); out.append(f"{NAME[mk]} {typ} {'Over' if side == 'O' else 'Under'}: {s}")
note("2 · 1xBet alla cieca per tipo di linea (tutte le linee proposte)", " ‖ ".join(out[:14]))
if len(out) > 14: note("2 · 1xBet alla cieca per tipo di linea (segue)", " ‖ ".join(out[14:]))
# Prevista sulla linea più equilibrata: per mercato, lato e valore della linea (dove si concentra il vantaggio)
out = []
for k_, nm in (("k", "cartellini"), ("c", "corner totali"), ("s", "tiri"), ("st", "tiri in porta"), ("f", "falli")):
    R_ = [r for r in RM if r["k"] == k_]
    byL = collections.defaultdict(list)
    for r in R_:
        for side in ("O", "U"):
            p = r["po"] if side == "O" else 1 - r["po"]; o = r["o"] if side == "O" else r["u"]
            if p * o > 1: byL[(side, r["L"])].append(dict(key=r["key"], d=r["d"], o=o, y=settle(side, r["L"], r.get("real"))))
    for (side, L), Bs in sorted(byL.items()):
        if len(Bs) < 25: continue
        s, r = stats(Bs); out.append(f"{nm} {'Over' if side == 'O' else 'Under'} {L}: {s}"); keep(f"Prevista · {nm} {'Over' if side == 'O' else 'Under'} {L} · valore > 0", r)
note("2 · Prevista (valore > 0) per linea · 1xBet", " ‖ ".join(out[:16]))
if len(out) > 16: note("2 · Prevista (valore > 0) per linea · segue", " ‖ ".join(out[16:32]))
# handicap asiatici (corner e cartellini): 1xBet contro Pinnacle sulla stessa linea
def ah_lines(q, mk):
    L = {}
    for k, v in q.items():
        if not k.startswith(mk + ":"): continue
        parts = k.split(":", 1)[1].split(" ")
        if len(parts) != 2 or parts[0] not in ("Home", "Away"): continue
        try: ln = float(parts[1])
        except Exception: continue
        o = val(v)
        if o and o > 1: L.setdefault((parts[0], ln), o)
    return L
B2a = collections.defaultdict(list)
for key, x in OH.items():
    q = (x.get("ultima") or {}).get("q") or {}; d = key.split("|")[1]
    for mk, (kh, ka) in (("cah", ("hc", "ac")), ("kah", ("hk", "ak"))):
        P, X = ah_lines(q, "p." + mk), ah_lines(q, "x." + mk)
        h, a = REAL.get((key, kh)), REAL.get((key, ka))
        for (side, ln), o in X.items():
            other = ("Away" if side == "Home" else "Home", -ln)
            if (side, ln) not in P or other not in P or abs(ln * 2 - round(ln * 2)) > 1e-9: continue
            pf = (1 / P[(side, ln)]) / (1 / P[(side, ln)] + 1 / P[other])
            y = None
            if h is not None and a is not None:
                m = (h - a if side == "Home" else a - h) + ln
                y = "R" if abs(m) < 1e-9 else (1 if m > 0 else 0)
            B2a[mk].append(dict(key=key, d=d, o=o, y=y, ev=pf * o - 1))
for mk, L in B2a.items():
    out = []
    for lab, f in (("alla cieca", lambda b: True), ("valore contro Pinnacle > 0", lambda b: b["ev"] > 0), ("> +4%", lambda b: b["ev"] > 0.04)):
        s, r = stats([b for b in L if f(b)]); out.append(f"{lab}: {s}")
        if lab != "alla cieca": keep(f"Asiatico · {mk} · {lab}", r)
    note(f"2 · handicap asiatico {'corner' if mk == 'cah' else 'cartellini'} · 1xBet", " ‖ ".join(out))

# ================= 3 · 1° TEMPO contro PARTITA (corner) =================
def nb_over(mu, r, L):
    kk = np.arange(0, int(math.floor(L)) + 1); qq = r / (r + mu)
    p = np.exp(gammaln(kk + r) - gammaln(r) - gammaln(kk + 1) + r * np.log(qq) + kk * np.log1p(-qq)); return 1 - p.sum()
def implied_mu(Ld, r):
    best = None
    for ln, o in Ld.items():
        if "O" in o and "U" in o and abs(ln - math.floor(ln) - 0.5) < 1e-9:
            dd = abs(1 / o["O"] - 1 / o["U"])
            if best is None or dd < best[0]: best = (dd, ln, (1 / o["O"]) / (1 / o["O"] + 1 / o["U"]))
    if not best: return None
    _, ln, p = best; lo, hi = 0.05, 40.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if nb_over(mid, r, ln) < p: lo = mid
        else: hi = mid
    return (lo + hi) / 2
AP = json.load(open("data/apif.json"))["partite"] if os.path.exists("data/apif.json") else {}
RES = collections.defaultdict(list)
for bf in ("pub/bundle_storico.json", "pub/bundle.json"):
    if not os.path.exists(bf): continue
    for f in json.load(open(bf))["files"]:
        for r in csv.DictReader(io.StringIO(f["text"])):
            try: d = datetime.datetime.strptime(r["Date"], "%d/%m/%Y").date(); RES[(r["Div"], int(r["FTHG"]), int(r["FTAG"]))].append((d, r["HomeTeam"], r["AwayTeam"]))
            except Exception: pass
votes = collections.defaultdict(collections.Counter)
for fid, v in AP.items():
    try: d0 = datetime.date.fromisoformat(v[0][:10]); hg, ag = int(v[4]), int(v[5])
    except Exception: continue
    for d, h, a in RES.get((v[1], hg, ag), []):
        if abs((d - d0).days) <= 1: votes[(v[1], v[2])][h] += 1; votes[(v[1], v[3])][a] += 1
MAP = {k: c.most_common(1)[0][0] for k, c in votes.items() if c.most_common(1)[0][1] >= 3}
H1, FR = {}, {}
rows = []
for fn in glob.glob("tempi/*.json"):
    lg = os.path.basename(fn)[:-5]
    for fid, v in json.load(open(fn)).items():
        try:
            if v[3] and v[4] and v[5] and v[6] and None not in (v[3][0], v[4][0], v[5][0], v[6][0]):
                rows.append((v[0][:10], lg, v[1], v[2], v[3][0] + v[4][0], v[3][0] + v[4][0] + v[5][0] + v[6][0]))
        except Exception: pass
rows.sort(); lgS = collections.defaultdict(lambda: [1e-9, 1e-9])
for d, lg, h, a, c1, ct in rows:
    L_ = lgS[lg]
    hh, aa = MAP.get((lg, h)), MAP.get((lg, a))
    if hh and aa: H1[(lg, d, hh, aa)] = c1; FR[(lg, d, hh, aa)] = L_[0] / L_[1] if L_[1] > 300 else None
    L_[0] = L_[0] * 0.999 + c1; L_[1] = L_[1] * 0.999 + ct
def look(D, lg, d, h, a):
    for dd in (0, -1, 1):
        x_ = D.get((lg, (datetime.date.fromisoformat(d) + datetime.timedelta(days=dd)).isoformat(), h, a))
        if x_ is not None: return x_
    return None
B3 = collections.defaultdict(list); RAT = []
for key, x in OH.items():
    q = (x.get("ultima") or {}).get("q") or {}; lg, d, h, a = key.split("|")
    X1 = lines(q, "x.h1.total_corners_1st_half")
    if not X1: continue
    m90 = implied_mu(lines(q, "p.cou"), 60.0) or implied_mu(lines(q, "x.cou"), 60.0)
    if not m90: continue
    fr = look(FR, lg, d, h, a); c1 = look(H1, lg, d, h, a); m1x = implied_mu(X1, 8.8)
    if m1x: RAT.append(m1x / m90)
    if not fr: continue
    mu1 = m90 * fr
    for L, xo in X1.items():
        for side in ("O", "U"):
            if side not in xo: continue
            po = nb_over(mu1, 8.8, L); p = po if side == "O" else 1 - po; ev = p * xo[side] - 1
            B3["tutte"].append(dict(key=key, d=d, o=xo[side], y=settle(side, L, c1), ev=ev, side=side))
out = [f"rapporto 1° tempo / partita di 1xBet: media {np.mean(RAT):.3f}, dev. {np.std(RAT):.3f} ({len(RAT)})" if RAT else "nessun rapporto"]
for lab, f in (("alla cieca", lambda b: True), ("valore > 0 (frazione reale del campionato × partita)", lambda b: b["ev"] > 0), ("> +5%", lambda b: b["ev"] > 0.05),
               ("> +5% solo Over", lambda b: b["ev"] > 0.05 and b["side"] == "O"), ("> +5% solo Under", lambda b: b["ev"] > 0.05 and b["side"] == "U")):
    s, r = stats([b for b in B3["tutte"] if f(b)]); out.append(f"{lab}: {s}")
    if lab != "alla cieca": keep(f"1° tempo corner · {lab}", r)
note("3 · corner 1° tempo · 1xBet contro frazione reale × linea della partita", " ‖ ".join(out))

# ================= 4 · FORMAZIONI UFFICIALI: quota subito dopo contro quota finale =================
C = json.load(open("q23_candidati.json")) if os.path.exists("q23_candidati.json") else []
cand = {(c["key"], c["side"]): c for c in C if c["mk"] == "1X2 falli" and c.get("pxi") is not None}
B4 = collections.defaultdict(list); mv = []
SEL = {"1": "Home", "X": "Draw", "2": "Away"}
for (key, side), c in cand.items():
    ser = (OH.get(key) or {}).get("serie") or []
    if not ser or not c.get("t"): continue
    try:
        ko = datetime.datetime.fromisoformat(f"{c['d']}T{c['t']}")
    except Exception: continue
    pts = []
    for ts, q in ser:
        try: t_ = datetime.datetime.fromisoformat(ts[:16])
        except Exception: continue
        o = val(q.get("x.f1x2:" + SEL[side])) if q.get("x.f1x2:" + SEL[side]) else None
        if o: pts.append(((ko - t_).total_seconds() / 60, o))
    pre = [o for m, o in pts if m > 65]; post = [(m, o) for m, o in pts if 0 < m <= 60]
    if not pre or not post: continue
    o_pre, o_after, o_close = pre[-1], max(post, key=lambda z: z[0])[1], min(post, key=lambda z: z[0])[1]
    dlt = c["pxi"] - c["p"]
    if abs(dlt) >= 0.04: mv.append((dlt, 1 / o_after - 1 / o_pre, 1 / o_close - 1 / o_after))
    for lab, o in (("subito dopo le formazioni", o_after), ("quota finale", o_close)):
        if c["pxi"] * o > 1 and dlt >= 0.03: B4[lab].append(dict(key=key, d=c["d"], o=o, y=c["y"]))
if mv:
    up = [m for m in mv if m[0] > 0]
    note("4 · formazioni · il mercato segue Prevista?", f"partite con spostamento di Prevista ≥ 4 punti: {len(mv)} · quando Prevista sale ({len(up)}): probabilità di 1xBet "
         f"da prima delle formazioni a subito dopo {100 * np.mean([m[1] for m in up]) if up else 0:+.1f} punti, da subito dopo alla fine {100 * np.mean([m[2] for m in up]) if up else 0:+.1f} punti")
out = []
for lab in ("subito dopo le formazioni", "quota finale"):
    s, r = stats(B4.get(lab, [])); out.append(f"{lab}: {s}"); keep(f"Formazioni falli · {lab}", r)
note("4 · falli 1X2 con Prevista spostata dalle formazioni (≥ +3 punti, valore > 0)", " ‖ ".join(out) + " · (1xBet non quota i falli 1X2 dal 24/10: campione fermo a ottobre)")

# ================= 5 · CASSA =================
def sim(res, mode, n_sims=4000, days=None):
    B = res["B"]; byd = collections.defaultdict(list)
    for b in B:
        if b["y"] is None: continue
        byd[b["d"]].append(b)
    D = list(byd.values()); nd = days or len(D)
    if nd < 5: return None
    fin, dd_, ruin = [], [], 0
    for _ in range(n_sims):
        bank, peak, mdd = 100.0, 100.0, 0.0
        for i in rng.integers(0, len(D), nd):
            day = D[i]; st_tot = 0; stakes = []
            for b in day:
                p = b.get("pf") or b.get("pv") or (1 / b["o"]) * 1.03
                edge = p * b["o"] - 1
                if mode == "fissa 1%": s = 0.01 * bank
                elif mode == "fissa 2%": s = 0.02 * bank
                elif mode.startswith("Kelly"):
                    fr = {"Kelly 1/4": 0.25, "Kelly 1/8": 0.125}[mode]; s = max(0.0, fr * edge / (b["o"] - 1)) * bank
                else: s = max(0.0, min(0.03, 0.5 * edge)) * bank   # proporzionale al vantaggio (metà del vantaggio, tetto 3%)
                s = min(s, 0.03 * bank); stakes.append(s)
            tot = sum(stakes)
            if tot > 0.10 * bank: stakes = [s * 0.10 * bank / tot for s in stakes]
            for b, s in zip(day, stakes):
                bank += 0 if b["y"] == "R" else (s * (b["o"] - 1) if b["y"] else -s)
            peak = max(peak, bank); mdd = max(mdd, 1 - bank / peak)
        fin.append(bank); dd_.append(mdd); ruin += bank < 50
    fin = np.array(fin)
    return f"cassa finale mediana {np.median(fin):.0f} (5°-95°: {np.percentile(fin, 5):.0f}-{np.percentile(fin, 95):.0f}) · profitto nel {100 * np.mean(fin > 100):.0f}% · calo massimo 95° {100 * np.percentile(dd_, 95):.0f}% · sotto metà cassa {100 * ruin / n_sims:.1f}%"
cands = sorted([(n, r) for n, r in RULES.items() if r["roi"] > 0 and r["h1"] is not None and r["h2"] is not None and r["h1"] > 0 and r["h2"] > 0],
               key=lambda x: x[1]["p"])
note("5 · regole positive in entrambe le metà", f"{len(cands)} su {len(RULES)} regole provate (con almeno 30 giocate) · " +
     " ‖ ".join(f"{n}: {r['n']} · {100 * r['roi']:+.1f}% ±{100 * r['ci']:.0f} (p {r['p']:.3f})" for n, r in cands[:12]))
for n, r in cands[:4]:
    out = []
    for mode in ("fissa 1%", "fissa 2%", "Kelly 1/8", "Kelly 1/4", "proporzionale"):
        s = sim(r, mode); out.append(f"{mode}: {s}")
    note(f"5 · cassa · {n} (giorni ricampionati, stessa durata dell'archivio)", " ‖ ".join(out))
# calo massimo e serie storiche reali (ordine vero) per le prime 3
for n, r in cands[:3]:
    B = sorted([b for b in r["B"] if b["y"] is not None], key=lambda b: b["d"]); bank, peak, mdd, lose, worst = 100.0, 100.0, 0.0, 0, 0
    for b in B:
        s = 0.01 * bank; bank += 0 if b["y"] == "R" else (s * (b["o"] - 1) if b["y"] else -s)
        peak = max(peak, bank); mdd = max(mdd, 1 - bank / peak); lose = lose + 1 if b["y"] == 0 else 0; worst = max(worst, lose)
    note(f"5 · storico reale · {n}", f"puntata 1% della cassa: 100 → {bank:.1f} · calo massimo {100 * mdd:.1f}% · serie peggiore {worst} perse di fila · giocate {len(B)} in {len({b['d'] for b in B})} giorni")
