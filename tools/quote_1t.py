"""1xBet prezza il 1° tempo come frazione fissa del totale? (28/10/2026, richiesta di Denny). Gira nel runner sull'archivio privato delle
quote (data/odds_hist.json); stampa SOLO numeri aggregati.
Per ogni partita con le linee Over/Under corner di 1xBet sia della partita (x.cou) sia del 1° tempo (x.h1.total_corners_1st_half),
ultima quota vista prima del fischio: linea più equilibrata, probabilità senza margine, corner attesi impliciti (Binomiale Negativa con la
dispersione dell'app: partita r = 60, 1° tempo r = 8,8) → rapporto di 1xBet = attesi 1° tempo / attesi partita.
Confronti:
  - quanto varia il rapporto di 1xBet tra le partite (in tutto e dentro lo stesso campionato) e la sua media per campionato
  - indice di 1° tempo delle due squadre (con le sole partite precedenti: quota di 1° tempo dei corner nelle loro partite, ristretta verso
    il campionato con 10 partite fittizie, ramo tempi) → correlazione con il rapporto di 1xBet e con la quota reale della partita.
  Se 1xBet usa una frazione fissa, il suo rapporto non segue l'indice delle squadre; la quota reale invece sì (se l'indice dice qualcosa)."""
import json, os, sys, glob, math, collections, datetime, csv, io, traceback
import numpy as np
from scipy.special import gammaln
sys.excepthook = lambda t, v, tb: print("::error title=Quote 1° tempo::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))
OH = json.load(open("data/odds_hist.json")); AP = json.load(open("data/apif.json"))["partite"]
def nb_over(mu, r, L):
    k = np.arange(0, int(L) + 1); q = r / (r + mu)
    p = np.exp(gammaln(k + r) - gammaln(r) - gammaln(k + 1) + r * np.log(q) + k * np.log1p(-q)); return 1 - p.sum()
LAST = {}
def implied(q, mk, r):
    L = {}
    for k, v in q.items():
        if not k.startswith(mk + ":"): continue
        parts = k.split(":", 1)[1].split(" ")
        if len(parts) != 2: continue
        try: ln = float(parts[1])
        except Exception: continue
        if abs(ln - math.floor(ln) - 0.5) > 1e-9: continue
        L.setdefault(ln, {})[parts[0][0]] = v[0] if isinstance(v, list) else v
    best = None
    for ln, o in L.items():
        if o.get("O", 0) > 1 and o.get("U", 0) > 1:
            d = abs(1 / o["O"] - 1 / o["U"])
            if best is None or d < best[0]: best = (d, ln, o["O"], o["U"])
    if not best: return None
    _, ln, oo, uu = best; p = (1 / oo) / (1 / oo + 1 / uu); LAST[mk] = (ln, p)
    lo, hi = 0.01, 40.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if nb_over(mid, r, ln) < p: lo = mid
        else: hi = mid
    return (lo + hi) / 2
# nomi API-Football → nostri (stessa data ±1 e stesso risultato, voto a maggioranza) dai risultati pubblicati
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
# indice di 1° tempo delle squadre (con le sole partite precedenti) e quota reale, dal ramo tempi
IDX, REAL = {}, {}
K, DEC = 10.0, 0.97
rows = []
for fn in glob.glob("tempi/*.json"):
    lg = os.path.basename(fn)[:-5]
    for fid, v in json.load(open(fn)).items():
        if v[3] and v[4] and v[5] and v[6] and None not in (v[3][0], v[4][0], v[5][0], v[6][0]):
            rows.append((v[0][:10], lg, v[1], v[2], v[3][0] + v[4][0], v[3][0] + v[4][0] + v[5][0] + v[6][0]))
rows.sort()
lgS = collections.defaultdict(lambda: [1e-9, 1e-9]); tm = collections.defaultdict(lambda: [0.0, 0.0])
for d, lg, h, a, c1, ct in rows:
    L = lgS[lg]; s_lg = L[0] / L[1]; avg = 10.0
    if L[1] > 500 and ct > 0:
        sh = lambda S: (S[0] + K * avg * s_lg) / (S[1] + K * avg)
        hh, aa = MAP.get((lg, h)), MAP.get((lg, a))
        if hh and aa:
            IDX[(lg, d, hh, aa)] = math.log(sh(tm[(lg, h)]) / s_lg) + math.log(sh(tm[(lg, a)]) / s_lg)
            REAL[(lg, d, hh, aa)] = (c1 / ct, s_lg, c1, ct)
    L[0] = L[0] * 0.999 + c1; L[1] = L[1] * 0.999 + ct
    for t in (h, a): S = tm[(lg, t)]; S[0] = S[0] * DEC + c1; S[1] = S[1] * DEC + ct
def look(D, lg, d, h, a):
    for dd in (0, -1, 1):
        x = D.get((lg, (datetime.date.fromisoformat(d) + datetime.timedelta(days=dd)).isoformat(), h, a))
        if x is not None: return x
    return None
out = []
for k, x in OH.items():
    q = (x.get("ultima") or {}).get("q") or {}
    m90, m1 = implied(q, "x.cou", 60.0), implied(q, "x.h1.total_corners_1st_half", 8.8)
    if not m90 or not m1: continue
    lg, d, h, a = k.split("|")
    out.append(dict(lg=lg, ratio=m1 / m90, idx=look(IDX, lg, d, h, a), real=look(REAL, lg, d, h, a), l1=LAST["x.h1.total_corners_1st_half"], l90=LAST["x.cou"]))
R = np.array([o["ratio"] for o in out])
if not len(R): note("Quote 1° tempo · corner", "nessuna partita con entrambe le linee"); sys.exit(0)
by = collections.defaultdict(list)
for o in out: by[o["lg"]].append(o["ratio"])
within = np.sqrt(np.mean([np.var(v) for v in by.values() if len(v) >= 10])) if by else float("nan")
note("Quote 1° tempo · corner · rapporto di 1xBet", f"partite {len(R)} · rapporto medio {R.mean():.3f} · deviazione standard tra le partite {R.std():.3f} · dentro lo stesso campionato {within:.3f} · "
     f"percentili 10-50-90 {np.percentile(R, 10):.3f} / {np.percentile(R, 50):.3f} / {np.percentile(R, 90):.3f} ‖ per campionato: " +
     ", ".join(f"{lg} {np.mean(v):.3f} (±{np.std(v):.3f}, {len(v)})" for lg, v in sorted(by.items(), key=lambda z: -len(z[1])) if len(v) >= 10))
J = [o for o in out if o["idx"] is not None and o["real"] is not None]
if len(J) >= 30:
    ix = np.array([o["idx"] for o in J]); bk = np.array([o["ratio"] for o in J]); re_ = np.array([o["real"][0] for o in J]); sl = np.array([o["real"][1] for o in J])
    c = lambda x, y: float(np.corrcoef(x, y)[0, 1])
    note("Quote 1° tempo · corner · segue le squadre?", f"partite abbinate {len(J)} · correlazione indice delle squadre ↔ rapporto 1xBet {c(ix, bk):+.3f} · indice ↔ quota reale {c(ix, re_):+.3f} · "
         f"rapporto 1xBet ↔ quota reale {c(bk, re_):+.3f} · quota reale media {re_.mean():.3f} contro rapporto 1xBet {bk.mean():.3f} e quota del campionato {sl.mean():.3f}")
else: note("Quote 1° tempo · corner · segue le squadre?", f"partite abbinate all'archivio per tempo: {len(J)} (troppo poche)")
# calibrazione diretta (senza ipotesi sulla dispersione): probabilità Over senza margine di 1xBet contro quanto è successo
if len(J) >= 30:
    for lab, key, col in (("1° tempo", "l1", 2), ("partita (controllo)", "l90", 3)):
        P = np.array([o[key][1] for o in J]); Y = np.array([1.0 if o["real"][col] > o[key][0] else 0.0 for o in J])
        se = math.sqrt(P.mean() * (1 - P.mean()) / len(P))
        note(f"Quote 1° tempo · corner · calibrazione Over {lab}", f"partite {len(J)} · Over senza margine di 1xBet {100 * P.mean():.1f} · realizzato {100 * Y.mean():.1f} · differenza {100 * (Y.mean() - P.mean()):+.1f} punti (±{196 * se:.1f})")
