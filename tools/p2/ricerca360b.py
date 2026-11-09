"""Ricerca 360 · verifica dei due segnali forti (9/11/2026): handicap asiatico corner 1xBet contro Pinnacle e Over/Under cartellini 1xBet
contro Pinnacle. Controlli: grandezza dei vantaggi (vantaggi enormi = linee diverse o regole diverse, non errori di prezzo), tipo di linea,
lato, una sola giocata per partita, campionati, due metà, e per i cartellini il conteggio dei rossi (rosso = 1 o 2 cartellini)."""
import json, os, sys, math, collections, datetime, csv, io, traceback
import numpy as np
sys.excepthook = lambda t, v, tb: print("::error title=360b::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
note = lambda t, m: print(f"::notice title=360b · {t}::" + m.replace("%", "%25").replace("\n", " "))
OH = json.load(open("data/odds_hist.json")); RM = json.load(open("rm_all.json")); AP = json.load(open("data/apif.json"))["partite"]
REAL = {(r["key"], r["k"]): r.get("real") for r in RM}
DAYS = sorted({k.split("|")[1] for k in OH}); half = DAYS[len(DAYS) // 2]
val = lambda v: v[0] if isinstance(v, list) else v
# gialli e rossi separati: abbinamento AP → chiave (campionato, data ±1, nomi via risultato) come in ricerca360
RES = collections.defaultdict(list)
for bf in ("pub/bundle_storico.json", "pub/bundle.json"):
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
YR = {}
for fid, v in AP.items():
    h, a = MAP.get((v[1], v[2])), MAP.get((v[1], v[3]))
    if not h or not a or v[7][4] is None or v[8][4] is None: continue
    dl = datetime.datetime.fromisoformat(v[0] + ":00+00:00").astimezone(datetime.timezone(datetime.timedelta(hours=1))).date()
    for dd in (0, -1, 1): YR[(v[1], (dl + datetime.timedelta(days=dd)).isoformat(), h, a)] = (v[7][4] + v[8][4], (v[7][5] or 0) + (v[8][5] or 0))
def stats(B):
    B = [b for b in B if b["y"] is not None]
    if not B: return "nessuna"
    pl = np.array([0.0 if b["y"] == "R" else (b["o"] - 1 if b["y"] else -1.0) for b in B]); roi = pl.mean()
    g = collections.defaultdict(float)
    for b, v in zip(B, pl): g[b["key"]] += v - roi
    ci = 1.96 * math.sqrt(sum(v * v for v in g.values())) / len(B)
    h1 = [v for b, v in zip(B, pl) if b["d"] < half]; h2 = [v for b, v in zip(B, pl) if b["d"] >= half]
    w = sum(1 for b in B if b["y"] == 1); dcs = sum(1 for b in B if b["y"] != "R")
    return f"{len(B)} · presa {100 * w / max(1, dcs):.0f}% · quota {np.mean([b['o'] for b in B]):.2f} · {100 * roi:+.1f}% ±{100 * ci:.0f} · metà {100 * np.mean(h1) if h1 else 0:+.0f}%/{100 * np.mean(h2) if h2 else 0:+.0f}%"
# ---------- handicap asiatico corner ----------
def ah(q, mk):
    L = {}
    for k, v in q.items():
        if not k.startswith(mk + ":"): continue
        p_ = k.split(":", 1)[1].split(" ")
        if len(p_) != 2 or p_[0] not in ("Home", "Away"): continue
        try: L[(p_[0], float(p_[1]))] = val(v)
        except Exception: pass
    return L
ex = collections.Counter(); B = []
for key, x in OH.items():
    q = (x.get("ultima") or {}).get("q") or {}; lg, d = key.split("|")[:2]
    P, X = ah(q, "p.cah"), ah(q, "x.cah")
    if len(ex) < 6:
        for kk in list(X)[:3]: ex[f"x {kk}"] += 1
        for kk in list(P)[:3]: ex[f"p {kk}"] += 1
    h, a = REAL.get((key, "hc")), REAL.get((key, "ac"))
    xl = sorted({ln for s, ln in X if s == "Home"}); pl_ = sorted({ln for s, ln in P if s == "Home"})
    for (side, ln), o in X.items():
        oth = ("Away" if side == "Home" else "Home", -ln)
        if (side, ln) not in P or oth not in P or not o: continue
        pf = (1 / P[(side, ln)]) / (1 / P[(side, ln)] + 1 / P[oth]); ev = pf * o - 1
        xo = X.get(oth); xm = (1 / o + 1 / xo - 1) if xo else None
        y = None
        if h is not None and a is not None:
            m = (h - a if side == "Home" else a - h) + ln; y = "R" if abs(m) < 1e-9 else (1 if m > 0 else 0)
        B.append(dict(key=key, d=d, lg=lg, o=o, y=y, ev=ev, side=side, ln=ln, typ="intera" if ln == round(ln) else "x,5", xm=xm, po=P[(side, ln)], pf=pf))
note("asiatico · esempi di linee", f"1xBet: {[k for k in ex if k.startswith('x')][:6]} · Pinnacle: {[k for k in ex if k.startswith('p')][:6]}")
E = np.array([b["ev"] for b in B]); V = [b for b in B if b["ev"] > 0]
note("asiatico · quanto sono grandi i vantaggi", f"{len(B)} quote confrontabili · vantaggio contro Pinnacle: mediana {100 * np.median(E):+.1f}% · 75° {100 * np.percentile(E, 75):+.1f}% · 95° {100 * np.percentile(E, 95):+.1f}% · "
     f"margine di 1xBet sulle due quote della stessa linea: mediana {100 * np.median([b['xm'] for b in B if b['xm'] is not None]):.1f}% · quota Pinnacle media delle giocate a valore {np.mean([b['po'] for b in V]):.2f} contro 1xBet {np.mean([b['o'] for b in V]):.2f}")
out = []
for lab, f in (("vantaggio 0-3%", lambda b: 0 < b["ev"] <= 0.03), ("3-10%", lambda b: 0.03 < b["ev"] <= 0.10), ("10-25%", lambda b: 0.10 < b["ev"] <= 0.25), ("oltre 25%", lambda b: b["ev"] > 0.25),
               ("a valore · linee intere", lambda b: b["ev"] > 0 and b["typ"] == "intera"), ("a valore · linee x,5", lambda b: b["ev"] > 0 and b["typ"] == "x,5"),
               ("a valore · casa", lambda b: b["ev"] > 0 and b["side"] == "Home"), ("a valore · ospite", lambda b: b["ev"] > 0 and b["side"] == "Away"),
               ("a valore · favorita (handicap negativo)", lambda b: b["ev"] > 0 and b["ln"] < 0), ("a valore · sfavorita (handicap positivo)", lambda b: b["ev"] > 0 and b["ln"] > 0)):
    out.append(f"{lab}: {stats([b for b in B if f(b)])}")
note("asiatico · per fascia, linea e lato", " ‖ ".join(out))
best = {}
for b in V:
    if b["key"] not in best or b["ev"] > best[b["key"]]["ev"]: best[b["key"]] = b
two = collections.Counter(b["key"] for b in V); both = sum(1 for k in two if len({(b['side']) for b in V if b['key'] == k}) > 1)
lgc = collections.defaultdict(list)
for b in best.values(): lgc[b["lg"]].append(b)
pos = sum(1 for L in lgc.values() if len(L) >= 5 and np.mean([0 if b["y"] in ("R", None) else (b["o"] - 1 if b["y"] else -1) for b in L]) > 0)
note("asiatico · una sola giocata per partita (vantaggio più alto)", f"{stats(list(best.values()))} · partite con giocate su entrambi i lati: {both} su {len(two)} · campionati positivi {pos} su {sum(1 for L in lgc.values() if len(L) >= 5)} (con almeno 5 giocate)")
# controllo: 1xBet confrontato con se stesso (linea asiatica contro O/U corner di 1xBet) non serve; Pinnacle calibrato sulle linee x,5?
cal = [(b["pf"], b["y"]) for b in B if b["typ"] == "x,5" and b["y"] in (0, 1)]
if cal: note("asiatico · Pinnacle è calibrato?", f"linee x,5: probabilità media di Pinnacle {100 * np.mean([c[0] for c in cal]):.1f}% · riuscita reale {100 * np.mean([c[1] for c in cal]):.1f}% ({len(cal)}) · per fasce: " +
             " · ".join(f"{lo:.1f}-{hi:.1f}: {100 * np.mean([c[1] for c in cal if lo <= c[0] < hi]):.0f}% ({sum(1 for c in cal if lo <= c[0] < hi)})" for lo, hi in ((0, .4), (.4, .5), (.5, .6), (.6, 1.01))))
# ---------- cartellini 1xBet contro Pinnacle, con i rossi contati 1 o 2 ----------
def ou(q, mk):
    L = {}
    for k, v in q.items():
        if not k.startswith(mk + ":"): continue
        p_ = k.split(":", 1)[1].split(" ")
        if len(p_) != 2 or p_[0] not in ("Over", "Under"): continue
        try: L.setdefault(float(p_[1]), {})[p_[0][0]] = val(v)
        except Exception: pass
    return L
C = []
for key, x in OH.items():
    q = (x.get("ultima") or {}).get("q") or {}; lg, d, h, a = key.split("|")
    P, X = ou(q, "p.kou"), ou(q, "x.kou"); yr = YR.get((lg, d, h, a))
    for ln, xo in X.items():
        po = P.get(ln)
        if not po or "O" not in po or "U" not in po: continue
        fo = (1 / po["O"]) / (1 / po["O"] + 1 / po["U"])
        for side in ("O", "U"):
            if side not in xo: continue
            pf = fo if side == "O" else 1 - fo; ev = pf * xo[side] - 1
            def gy(tot): return None if tot is None else ("R" if abs(tot - ln) < 1e-9 else (1 if (tot > ln) == (side == "O") else 0))
            C.append(dict(key=key, d=d, lg=lg, o=xo[side], ev=ev, side=side, ln=ln, y1=gy(None if not yr else yr[0] + yr[1]), y2=gy(None if not yr else yr[0] + 2 * yr[1]),
                          yg=gy(None if not yr else yr[0]), red=None if not yr else yr[1]))
for lab, yk in (("rosso = 1 cartellino (come Prevista)", "y1"), ("rosso = 2 cartellini", "y2"), ("solo gialli", "yg")):
    out = []
    for f_lab, f in (("alla cieca", lambda b: True), ("valore > 0", lambda b: b["ev"] > 0), ("> 3%", lambda b: b["ev"] > 0.03), ("> 3% Under", lambda b: b["ev"] > 0.03 and b["side"] == "U"), ("> 3% Over", lambda b: b["ev"] > 0.03 and b["side"] == "O")):
        out.append(f"{f_lab}: {stats([dict(b, y=b[yk]) for b in C if f(b)])}")
    note(f"cartellini 1xBet contro Pinnacle · {lab}", " ‖ ".join(out))
E2 = np.array([b["ev"] for b in C])
note("cartellini · grandezza dei vantaggi e rossi", f"{len(C)} quote · vantaggio mediana {100 * np.median(E2):+.1f}% · 95° {100 * np.percentile(E2, 95):+.1f}% · partite con almeno un rosso tra quelle a valore > 3%: "
     f"{100 * np.mean([b['red'] > 0 for b in C if b['ev'] > 0.03 and b['red'] is not None]):.0f}% contro {100 * np.mean([b['red'] > 0 for b in C if b['red'] is not None]):.0f}% di tutte")
# Prevista Under cartellini (regola del sistema) con i rossi contati 2
U = []
for r in RM:
    if r["k"] != "k": continue
    lg, d, h, a = r["key"].split("|"); yr = YR.get((lg, d, h, a))
    if not yr: continue
    p = 1 - r["po"]
    if p * r["u"] > 1:
        for lab, tot in (("rosso 1", yr[0] + yr[1]), ("rosso 2", yr[0] + 2 * yr[1])):
            U.append(dict(key=r["key"], d=d, o=r["u"], lab=lab, y="R" if abs(tot - r["L"]) < 1e-9 else (1 if tot < r["L"] else 0)))
note("Under cartellini di Prevista (valore > 0) · sensibilità ai rossi", " ‖ ".join(f"{lab}: {stats([b for b in U if b['lab'] == lab])}" for lab in ("rosso 1", "rosso 2")))
