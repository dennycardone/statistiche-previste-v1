"""Champions League (13/10/2026): previsioni per squadra di gol, corner, tiri, tiri in porta, falli e cartellini.

Dati: solo API-Football. Archivio storico/*.json (ramo storico, stagioni 2022-2025 complete) + stagione 2026 (2026-27, o 2026
per i campionati ad anno solare) aggiornata qui a ogni giro: campionati delle squadre europee e le tre coppe (Champions, Europa League,
Conference League), che collegano i campionati tra loro.

Modelli candidati (ricerca del 12/10/2026, walk-forward 2023-24 / 2024-25 / 2025-26):
  B0  media della Champions (fase principale, casa e trasferta separate)
  B1  storico europeo della squadra, ridotto verso la media
  M2  rating comune: GLM di Poisson su tutte le competizioni, log λ = c_comp + casa_comp + att_squadra + dif_avversario,
      ultimi 730 giorni, pesi nel tempo (τ), ridge (ρ), peso delle partite europee (β): 8 configurazioni
Per ogni statistica si usa il candidato con l'errore medio per squadra più basso sulle previsioni fatte PRIMA delle partite
(ricerca + partite nuove, le più recenti pesano di più): a ogni risultato nuovo il modello si ricalcola e la scelta si aggiorna da sola.
Intervalli: Binomiale Negativa con la dispersione stimata dal modello. Gol: Poisson indipendenti (1X2, Over, Gol/No gol, risultati).

Uscite: storico/{lega}_2026.json (archivio), storico/ucl_log.json (previsioni congelate prima del calcio d'inizio), ucl.json (per l'app)."""
import json, os, glob, math, datetime, time, urllib.request, urllib.parse, sys, collections
import numpy as np, scipy.sparse as sp
from scipy.optimize import minimize
from scipy.stats import nbinom, poisson
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import af_budget

ST, CUR = "storico", int(os.environ.get("UCL_CUR", 2026))   # UCL_CUR / UCL_NOW: solo per le prove in locale
EUR = ("UCL", "UEL", "UECL")
CUPS = {"UCL": ("ucl", "Champions"), "UEL": ("uel", "Europa League")}   # 13/10/2026: anche l'Europa League, stesso metodo
SEED_COMP = os.environ.get("SEED_COMP")   # solo in locale: costruisce tools/<coppa>_seed.json (walk-forward delle stagioni 2023-24 → 2025-26)
LEAGUES = [("I1", 135), ("E0", 39), ("SP1", 140), ("D1", 78), ("F1", 61), ("I2", 136), ("E1", 40), ("N1", 88), ("P1", 94), ("B1", 144), ("T1", 203),
           ("G1", 197), ("SC0", 179), ("SP2", 141), ("F2", 62), ("D2", 79), ("E2", 41), ("E3", 42), ("SC1", 180), ("SC2", 183), ("SC3", 184),
           ("BRA", 71), ("ARG", 128), ("USA", 253), ("MEX", 262), ("CHN", 169), ("JPN", 98), ("AUT", 218), ("DNK", 119), ("NOR", 103), ("SWE", 113),
           ("RUS", 235), ("POL", 106), ("ROU", 283), ("SWZ", 207), ("FIN", 244), ("IRL", 357), ("EC", 43),
           ("SRB", 286), ("CRO", 210), ("HUN", 271), ("CZE", 345), ("UKR", 333), ("ISR", 383), ("BUL", 172), ("CYP", 318), ("SVK", 332), ("BLR", 116),
           ("UCL", 2), ("UEL", 3), ("UECL", 848)]
STATS = {"g": None, "s": 0, "st": 1, "c": 2, "f": 3, "k": None}   # indice nelle statistiche salvate (gol a parte, cartellini = gialli + rossi)
# configurazioni M2 (τ giorni, ridge, peso europeo)
CFGS = {f"M2_t{t}_r{r}_b{b}": (t, float(r), float(b)) for t in (180, 365) for r in (1, 5) for b in (1, 3)}
T0 = datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc)
NOW = datetime.datetime.fromisoformat(os.environ["UCL_NOW"]).replace(tzinfo=datetime.timezone.utc) if os.environ.get("UCL_NOW") else datetime.datetime.now(datetime.timezone.utc)
def tday(s):   # giorni dal 1/1/2022 (data "2026-10-21T19:00" in UTC)
    return (datetime.datetime.fromisoformat(s[:16]).replace(tzinfo=datetime.timezone.utc) - T0).total_seconds() / 86400
TNOW = (NOW - T0).total_seconds() / 86400

# ---------------- 1. dati della stagione in corso da API-Football (solo le richieste che avanzano dopo la riserva dell'app) ----------------
KEY = os.environ.get("APIFOOTBALL_KEY", "").strip()
used = 0
def get(p, **q):
    global used
    used += 1
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
            time.sleep(0.25); return d
        except Exception as e:
            print("retry", p, e); time.sleep(5)
    return {"errors": ["rete"]}
def stat(t, k):
    for s in t.get("statistics", []):
        if s["type"] == k:
            v = s["value"]
            if v is None: return 0 if k in ("Yellow Cards", "Red Cards") else None
            try: return float(str(v).replace("%", ""))
            except Exception: return None
    return None
KS = ["Total Shots", "Shots on Goal", "Corner Kicks", "Fouls", "Yellow Cards", "Red Cards", "expected_goals"]
FIN = ("FT", "AET", "PEN")
budget = af_budget.test_budget(af_budget.requests_of(get("status"))) if KEY else 0
print("richieste disponibili oltre la riserva dell'app:", budget)
os.makedirs(ST, exist_ok=True)
today = NOW.strftime("%Y-%m-%d")
for lg, lid in LEAGUES:
    fn = f"{ST}/{lg}_{CUR}.json"
    D = json.load(open(fn)) if os.path.exists(fn) else {"lega": lg, "stagione": CUR, "partite": {}, "completo": False, "ids": [], "lista": ""}
    # elenco partite: le coppe a ogni giro, i campionati una volta al giorno
    if budget > 40 and (lg in EUR or D.get("lista", "")[:10] != today):
        L = get("fixtures", league=lid, season=CUR); budget -= 1
        if L.get("errors"): print(lg, L["errors"]); continue
        R = L.get("response", [])
        D["ids"] = [f["fixture"]["id"] for f in R if f["fixture"]["status"]["short"] in FIN]
        D["lista"] = NOW.isoformat(timespec="minutes")
        if lg in CUPS:
            D["calendario"] = [[f["fixture"]["id"], f["fixture"]["date"][:16], f["teams"]["home"]["name"], f["teams"]["away"]["name"], f["league"].get("round") or "",
                                f["fixture"]["status"]["short"], f["teams"]["home"].get("logo") or "", f["teams"]["away"].get("logo") or ""] for f in R]
    # partite finite da scaricare: le nuove e quelle recenti ancora senza statistiche (arrivano qualche minuto dopo la fine)
    todo = [i for i in D["ids"] if str(i) not in D["partite"] or (D["partite"][str(i)][6][0] is None and TNOW - tday(D["partite"][str(i)][0]) < 3)]
    for k in range(0, len(todo), 20):
        if budget <= 40: break
        R = get("fixtures", ids="-".join(str(i) for i in todo[k:k + 20])); budget -= 1
        for f in R.get("response", []):
            st_ = {t["team"]["id"]: t for t in f.get("statistics", [])}
            H, A = st_.get(f["teams"]["home"]["id"], {}), st_.get(f["teams"]["away"]["id"], {})
            D["partite"][str(f["fixture"]["id"])] = [f["fixture"]["date"][:16], f["teams"]["home"]["name"], f["teams"]["away"]["name"],
                f["goals"]["home"], f["goals"]["away"], f["fixture"].get("referee"), [stat(H, k_) for k_ in KS], [stat(A, k_) for k_ in KS], f["league"].get("round") or ""]
    json.dump(D, open(fn, "w"), ensure_ascii=False, separators=(",", ":"))
    print(lg, CUR, len(D["partite"]), "/", len(D["ids"]))
print("richieste usate", used, "· avanzano oltre la riserva", budget)

# ---------------- 2. archivio in righe ----------------
def is_qual(rnd): return ("Qualifying" in rnd) or rnd == "Play-offs" or rnd.startswith("Preliminary")
def phase(comp, season, dt, rnd=None):
    if comp not in EUR: return None
    if rnd: return "qual" if is_qual(rnd) else "main"
    y, m = int(dt[:4]), int(dt[5:7])
    return "qual" if (y == season and m in (6, 7, 8)) else "main"
rows = []
for f in sorted(glob.glob(f"{ST}/*_20[0-9][0-9].json")):
    d = json.load(open(f)); comp, s = d["lega"], d["stagione"]
    if s < CUR - (4 if SEED_COMP else 3): continue
    for fid, v in d["partite"].items():
        if v[3] is None: continue
        H, A = v[6], v[7]
        g = lambda x, i: x[i] if x and x[i] is not None else None
        card = lambda x: (x[4] + (x[5] or 0)) if x and x[4] is not None else None
        rows.append(dict(id=fid, comp=comp, dt=v[0], t=tday(v[0]), h=v[1], a=v[2], ph=phase(comp, s, v[0], v[8] if len(v) > 8 else None),
                         g=(v[3], v[4]), s=(g(H, 0), g(A, 0)), st=(g(H, 1), g(A, 1)), c=(g(H, 2), g(A, 2)), f=(g(H, 3), g(A, 3)), k=(card(H), card(A))))
rows.sort(key=lambda r: r["t"])
print("righe archivio", len(rows))

class Data:   # array per una statistica
    def __init__(self, stat):
        O = [r for r in rows if r[stat][0] is not None and r[stat][1] is not None]
        self.O = O
        self.t = np.array([r["t"] for r in O]); self.comp = np.array([r["comp"] for r in O])
        self.hn = [r["h"] for r in O]; self.an = [r["a"] for r in O]
        self.hv = np.array([r[stat][0] for r in O], float); self.av = np.array([r[stat][1] for r in O], float)
        self.eur = np.isin(self.comp, EUR); self.main = {c: np.array([r["comp"] == c and r["ph"] == "main" for r in O]) for c in CUPS}
        names = sorted(set(self.hn) | set(self.an)); self.ti = {n: i for i, n in enumerate(names)}
        self.h = np.array([self.ti[n] for n in self.hn]); self.a = np.array([self.ti[n] for n in self.an])

def b0(D, t, comp, tau=730):
    m = D.main[comp] & (D.t < t); w = np.exp(-(t - D.t[m]) / tau)
    return float((w * D.hv[m]).sum() / w.sum()), float((w * D.av[m]).sum() / w.sum())
def b1(D, t, h, a, comp, k=8, tau=365):
    mh, ma = b0(D, t, comp); m = (mh + ma) / 2; mask = D.eur & (D.t < t)
    def f(team):
        i = D.ti.get(team)
        if i is None: return 1.0, 1.0
        xh = mask & (D.h == i); xa = mask & (D.a == i)
        wh = np.exp(-(t - D.t[xh]) / tau); wa = np.exp(-(t - D.t[xa]) / tau)
        fs = (wh * D.hv[xh]).sum() + (wa * D.av[xa]).sum(); cs = (wh * D.av[xh]).sum() + (wa * D.hv[xa]).sum(); fw = wh.sum() + wa.sum()
        return (fs + k * m) / (fw + k) / m, (cs + k * m) / (fw + k) / m
    (ah, dh), (aa, da) = f(h), f(a)
    return mh * ah * da, ma * aa * dh
def m2_fit(D, t, tau, ridge, beta, window=730):
    m = (D.t < t) & (D.t >= t - window); idx = np.where(m)[0]
    teams = sorted({D.hn[i] for i in idx} | {D.an[i] for i in idx}); comps = sorted(set(D.comp[idx]))
    ti = {x: i for i, x in enumerate(teams)}; ci = {x: i for i, x in enumerate(comps)}; nT, nC = len(teams), len(comps)
    n = len(idx)
    cidx = np.array([ci[c] for c in D.comp[idx]]); hi = np.array([ti[D.hn[i]] for i in idx]); ai = np.array([ti[D.an[i]] for i in idx])
    w1 = np.exp(-(t - D.t[idx]) / tau) * np.where(D.eur[idx], beta, 1.0)
    # righe: 2k casa (c + casa + att casa + dif ospite), 2k+1 ospite (c + att ospite + dif casa)
    r_h, r_a = 2 * np.arange(n), 2 * np.arange(n) + 1
    rr = np.concatenate([r_h, r_h, r_h, r_h, r_a, r_a, r_a])
    cc = np.concatenate([cidx, nC + cidx, 2 * nC + hi, 2 * nC + nT + ai, cidx, 2 * nC + ai, 2 * nC + nT + hi])
    X = sp.csr_matrix((np.ones(len(rr)), (rr, cc)), shape=(2 * n, 2 * nC + 2 * nT))
    y = np.empty(2 * n); y[0::2] = D.hv[idx]; y[1::2] = D.av[idx]
    w = np.repeat(w1, 2)
    P = 2 * nC + 2 * nT; reg = np.zeros(P); reg[2 * nC:] = ridge
    x0 = np.zeros(P); x0[:nC] = math.log(max(1e-3, (w * y).sum() / w.sum()))
    def f(b):
        eta = X @ b; lam = np.exp(np.clip(eta, -20, 20))
        return (w * (lam - y * eta)).sum() + 0.5 * (reg * b * b).sum(), X.T @ (w * (lam - y)) + reg * b
    b = minimize(f, x0, jac=True, method="L-BFGS-B", options={"maxiter": 400}).x
    lam = np.exp(X @ b); alpha = max(float((w * ((y - lam) ** 2 - lam)).sum() / (w * lam ** 2).sum()), 1e-4)
    def pred(h, a, comp="UCL"):
        if comp not in ci: return None
        c, hv = b[ci[comp]], b[nC + ci[comp]]
        att = lambda x: b[2 * nC + ti[x]] if x in ti else 0.0
        dfn = lambda x: b[2 * nC + nT + ti[x]] if x in ti else 0.0
        return math.exp(c + hv + att(h) + dfn(a)), math.exp(c + att(a) + dfn(h))
    return pred, alpha

def predict_all(D, t, games, comp):
    """previsioni di tutti i candidati per le partite `games` (lista di (id, casa, ospite)), con i soli dati prima di t"""
    out = {gid: {"P": {}, "A": {}} for gid, _, _ in games}
    base = b0(D, t, comp)
    for gid, h, a in games:
        out[gid]["P"]["B0"] = [round(base[0], 3), round(base[1], 3)]
        x = b1(D, t, h, a, comp); out[gid]["P"]["B1"] = [round(x[0], 3), round(x[1], 3)]
    for name, (tau, ridge, beta) in CFGS.items():
        pred, alpha = m2_fit(D, t, tau, ridge, beta)
        for gid, h, a in games:
            p = pred(h, a, comp) or base
            out[gid]["P"][name] = [round(p[0], 3), round(p[1], 3)]; out[gid]["A"][name] = round(alpha, 4)
    return out

# ---------------- 3. registro delle previsioni congelate prima del calcio d'inizio ----------------
DATA = {s: Data(s) for s in STATS}
def run_comp(comp):
    key, nome = CUPS[comp]
    SEEDF = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{key}_seed.json")
    SEED = json.load(open(SEEDF)) if os.path.exists(SEEDF) else {}   # ricerca: walk-forward 2023-24 → 2025-26
    if os.environ.get("UCL_NOW"): SEED = {k: v for k, v in SEED.items() if v["dt"] < os.environ.get("UCL_SEED_TO", os.environ["UCL_NOW"][:10])}
    LOGF = f"{ST}/{key}_log.json"
    LOG = json.load(open(LOGF)) if os.path.exists(LOGF) else {}
    U = json.load(open(f"{ST}/{comp}_{CUR}.json")) if os.path.exists(f"{ST}/{comp}_{CUR}.json") else {"partite": {}, "calendario": []}
    CAL = {str(c[0]): c for c in U.get("calendario", [])}
    played = {fid: v for fid, v in U["partite"].items() if v[3] is not None and not is_qual(v[8] if len(v) > 8 else "")}
    upcoming = [c for c in CAL.values() if c[5] in ("NS", "TBD") and not is_qual(c[4]) and 0 <= tday(c[1]) - TNOW <= 16]
    # partite giocate della stagione senza previsione congelata (es. il primo giro): previsione walk-forward con i soli dati precedenti
    retro = sorted([fid for fid in played if fid not in LOG and fid not in SEED], key=lambda f: played[f][0])
    by_day = collections.defaultdict(list)
    for fid in retro: by_day[math.floor(tday(played[fid][0]))].append(fid)
    for d0, ids in by_day.items():
        for s, D in DATA.items():
            P = predict_all(D, d0, [(fid, played[fid][1], played[fid][2]) for fid in ids], comp)
            for fid in ids:
                e = LOG.setdefault(fid, {"dt": played[fid][0], "h": played[fid][1], "a": played[fid][2], "P": {}, "A": {}, "fonte": "a posteriori, dati precedenti"})
                e["P"][s] = P[fid]["P"]; e["A"][s] = P[fid]["A"]
    print("previsioni a posteriori (walk-forward) aggiunte:", len(retro))
    # partite in arrivo: previsione di adesso, sovrascritta a ogni giro fino al calcio d'inizio (poi resta congelata)
    for s, D in DATA.items():
        P = predict_all(D, TNOW, [(str(c[0]), c[2], c[3]) for c in upcoming], comp)
        for c in upcoming:
            fid = str(c[0]); e = LOG.setdefault(fid, {"P": {}, "A": {}})
            e.update(dt=c[1], h=c[2], a=c[3], fonte="prima del calcio d'inizio", calcolata=NOW.isoformat(timespec="minutes"))
            e["P"][s] = P[fid]["P"]; e["A"][s] = P[fid]["A"]
    json.dump(LOG, open(LOGF, "w"), ensure_ascii=False, separators=(",", ":"))

    # ---------------- 4. scelta del modello per statistica: errore medio per squadra, pesato verso le partite recenti ----------------
    def actual(fid, s):
        if fid in SEED: return SEED[fid]["y"].get(s)
        v = played.get(fid)
        if not v: return None
        if s == "g": return [v[3], v[4]]
        H, A = v[6], v[7]
        if s == "k": return [H[4] + (H[5] or 0), A[4] + (A[5] or 0)] if H[4] is not None and A[4] is not None else None
        i = STATS[s]; return [H[i], A[i]] if H[i] is not None and A[i] is not None else None
    CHOICE, SCORES = {}, {}
    for s in STATS:
        err, wsum = collections.defaultdict(float), 0.0
        for src in (SEED, LOG):
            for fid, e in src.items():
                y = actual(fid, s); P = e["P"].get(s)
                if not y or not P or (src is LOG and fid in SEED): continue
                w = math.exp(-(TNOW - tday(e["dt"])) / 365); wsum += 2 * w
                for name, p in P.items():
                    if name in ("B0", "B1") or name in CFGS: err[name] += w * (abs(p[0] - y[0]) + abs(p[1] - y[1]))
        SCORES[s] = {k: round(v / wsum, 4) for k, v in err.items()}
        CHOICE[s] = min(SCORES[s], key=SCORES[s].get)
        print(s, "modello scelto", CHOICE[s], "errore medio per squadra", SCORES[s][CHOICE[s]], "(B0", SCORES[s]["B0"], ")")
        print(f"::notice title={nome} {s}::{CHOICE[s]} errore {SCORES[s][CHOICE[s]]} · media semplice {SCORES[s]['B0']}")

    # ---------------- 5. uscita per l'app ----------------
    def pmf(mu, alpha, K):
        if alpha < 1e-3: return poisson.pmf(np.arange(K), mu)
        r = 1 / alpha; return nbinom.pmf(np.arange(K), r, r / (r + mu))
    def interval(p, lo=0.10, hi=0.90):
        c = np.cumsum(p / p.sum()); return [int(np.searchsorted(c, lo)), int(np.searchsorted(c, hi))]
    def alpha_for(e, s):
        A = e["A"].get(s, {}); ch = CHOICE[s]
        if ch in A: return A[ch]
        best = min((k for k in A if k in SCORES[s]), key=lambda k: SCORES[s][k], default=None)
        return A[best] if best else 0.0
    def block(e, s):
        P = e["P"].get(s)
        if not P or CHOICE[s] not in P: return None
        ph, pa = P[CHOICE[s]]; al = 0.0 if s == "g" else alpha_for(e, s); K = 80 if s in ("s", "f") else 40
        a, b = pmf(ph, al, K), pmf(pa, al, K); t = np.convolve(a, b)[:K]
        return [round(ph, 2), round(pa, 2), interval(a), interval(b), interval(t), round(al, 4)]   # ultima: dispersione (Binomiale Negativa) per le probabilità dell app
    def goals(e):
        P = e["P"].get("g")
        if not P or CHOICE["g"] not in P: return None
        ph, pa = P[CHOICE["g"]]
        M = np.outer(poisson.pmf(np.arange(11), ph), poisson.pmf(np.arange(11), pa)); M /= M.sum()
        p1, px = float(np.tril(M, -1).sum()), float(np.trace(M))
        tot = np.array([[i + j for j in range(11)] for i in range(11)])
        ov = [float(M[tot > L].sum()) for L in (1.5, 2.5, 3.5)]
        gg = float(M[1:, 1:].sum())
        top = sorted(((float(M[i, j]), f"{i}-{j}") for i in range(7) for j in range(7)), reverse=True)[:5]
        r = lambda x: round(x, 3)
        return {"1": r(p1), "X": r(px), "2": r(1 - p1 - px), "ov": [r(x) for x in ov], "gg": r(gg), "top": [[k, r(p)] for p, k in top]}
    OUT = []
    for fid, e in LOG.items():
        dd = tday(e["dt"]) - TNOW
        if dd < -31 or dd > 16: continue
        c = CAL.get(fid); v = played.get(fid)
        if c and c[5] in ("CANC", "ABD", "AWD", "WO"): continue
        res = None
        if v: res = {s: (lambda y: [int(y[0]), int(y[1])] if y else None)(actual(fid, s)) for s in STATS}
        OUT.append({"id": fid, "dt": e["dt"], "h": e["h"], "a": e["a"], "round": (c[4] if c else (v[8] if v and len(v) > 8 else "")),
                    "lh": c[6] if c else "", "la": c[7] if c else "", "stato": c[5] if c else ("FT" if v else ""),
                    "p": {s: block(e, s) for s in STATS}, "gol": goals(e), "ris": res, "fonte": e.get("fonte", "")})
    OUT.sort(key=lambda x: (x["dt"], x["h"]))
    json.dump({"updated": NOW.isoformat(timespec="minutes"), "modelli": CHOICE, "errori": SCORES, "partite": OUT}, open(f"{key}.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"{key}.json:", len(OUT), "partite ·", sum(1 for x in OUT if x["ris"]), "giocate")

if SEED_COMP:   # costruzione del seed (in locale): walk-forward sulle stagioni 2023-24 → 2025-26, fase principale, giorno per giorno
    comp = SEED_COMP; key = CUPS[comp][0]; SEED = {}
    G = sorted([r for r in rows if r["comp"] == comp and r["ph"] == "main" and r["dt"] >= "2023-07-01" and r["dt"] < "2026-07-01"], key=lambda r: r["t"])
    by = collections.defaultdict(list)
    for r in G: by[math.floor(r["t"])].append(r)
    for j, (d0, rs) in enumerate(sorted(by.items())):
        for s_, D in DATA.items():
            ok = [r for r in rs if r[s_][0] is not None and r[s_][1] is not None]
            if not ok: continue
            P = predict_all(D, d0, [(r["id"], r["h"], r["a"]) for r in ok], comp)
            for r in ok:
                e = SEED.setdefault(r["id"], {"dt": r["dt"], "h": r["h"], "a": r["a"], "y": {}, "P": {}, "A": {}})
                e["y"][s_] = [r[s_][0], r[s_][1]]; e["P"][s_] = P[r["id"]]["P"]; e["A"][s_] = P[r["id"]]["A"]
        print("seed", comp, j + 1, "/", len(by), flush=True)
    json.dump(SEED, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{key}_seed.json"), "w"), separators=(",", ":"))
else:
    for comp in CUPS: run_comp(comp)
