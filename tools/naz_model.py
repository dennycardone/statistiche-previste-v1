"""Nazionali (8/11/2026, richiesta di Denny): previsioni per squadra di gol, corner, tiri, tiri in porta, falli e cartellini per le partite
ufficiali delle nazionali (Mondiale, Europeo, Nations League, Copa América, Coppa d'Africa e qualificazioni). Amichevoli escluse.
Fuorigioco esclusi (la prova di fattibilità non li ha passati).

Prova di fattibilità (tools/p2/nazionali.py, IPOTESI.md 8/11/2026), walk-forward con i periodi del banco di prova: il modello per squadra
batte la media su "chi ne fa di più" in corner, tiri, tiri in porta, falli e cartellini, e sul totale di tiri, tiri in porta e falli.
Totale dei corner come la media; totale dei cartellini peggio della media in holdout (mostrato su richiesta di Denny, con l'avviso).

Modello (lo stesso della prova): per ogni squadra fatti e subiti con decadimento nel tempo (metà peso ogni 540 giorni), ritirati verso la
media con 4 partite fittizie; atteso casa = fatti casa × subiti ospite / media (e viceversa). Media = ultime 400 partite. Dispersione
(Binomiale Negativa) stimata dagli errori delle previsioni walk-forward recenti.

Dati: solo API-Football, richieste oltre la riserva dell'app (tools/af_budget.py). Archivio e previsioni sul ramo "nazionali":
  NAZ.json (archivio partite + statistiche), naz_log.json (previsioni congelate prima del calcio d'inizio), naz.json (per l'app,
  stesso formato di ucl.json)."""
import json, os, math, datetime, time, urllib.request, urllib.parse, sys, collections, traceback
import numpy as np
from scipy.stats import nbinom, poisson
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.excepthook = lambda t, v, tb: print("::error title=Nazionali::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
import af_budget
from naz_nomi import it as IT_   # 8/11/2026: nomi in italiano nell'uscita per l'app

DIR = os.environ.get("NAZ_DIR", "nazionali"); os.makedirs(DIR, exist_ok=True)
COMP = {1: "Mondiale", 4: "Europeo", 5: "Nations League", 960: "Qualificazioni Europeo", 32: "Qualificazioni Mondiale UEFA", 34: "Qualificazioni Mondiale CONMEBOL",
        31: "Qualificazioni Mondiale CONCACAF", 30: "Qualificazioni Mondiale AFC", 29: "Qualificazioni Mondiale CAF", 9: "Copa América", 6: "Coppa d'Africa"}
KS = ["Total Shots", "Shots on Goal", "Corner Kicks", "Fouls", "Yellow Cards", "Red Cards", "expected_goals"]   # come update_data.py (indici 0-6)
FIN = ("FT", "AET", "PEN")
STATS = {"g": None, "s": 0, "st": 1, "c": 2, "f": 3, "k": None}
HL, PRIOR, NMU = 540.0, 4.0, 400
NOW = datetime.datetime.now(datetime.timezone.utc)
T0 = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
tday = lambda s: (datetime.datetime.fromisoformat(s[:16]).replace(tzinfo=datetime.timezone.utc) - T0).total_seconds() / 86400
TNOW = (NOW - T0).total_seconds() / 86400
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))

# ---------------- 1. archivio da API-Football ----------------
KEY = os.environ.get("APIFOOTBALL_KEY", "").strip(); used = 0
def get(p, **q):
    global used; used += 1
    req = urllib.request.Request("https://v3.football.api-sports.io/" + p + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read().decode())
            time.sleep(0.25); return d
        except Exception as e: print("retry", p, e); time.sleep(5)
    return {"errors": ["rete"]}
def stat(t, k):
    for s in t.get("statistics", []):
        if s["type"] == k:
            v = s["value"]
            if v is None: return 0 if k in ("Yellow Cards", "Red Cards") else None
            try: return float(str(v).replace("%", ""))
            except Exception: return None
    return None
AF = os.path.join(DIR, "NAZ.json")
A = json.load(open(AF)) if os.path.exists(AF) else {"partite": {}, "stagioni": {}, "liste": {}, "agg": ""}
budget = af_budget.test_budget(af_budget.requests_of(get("status"))) if KEY else 0
print("richieste disponibili oltre la riserva dell'app:", budget)
today = NOW.strftime("%Y-%m-%d")
def take(f):
    fid = str(f["fixture"]["id"]); old = A["partite"].get(fid)
    A["partite"][fid] = [f["fixture"]["date"][:16], f["league"]["id"], f["teams"]["home"]["name"], f["teams"]["away"]["name"], f["goals"]["home"], f["goals"]["away"],
                         f["fixture"].get("referee") or (old[6] if old else None), old[7] if old else [None] * 7, old[8] if old else [None] * 7,
                         f["fixture"]["status"]["short"], f["league"].get("round") or "", f["teams"]["home"].get("logo") or "", f["teams"]["away"].get("logo") or ""]
if budget > 60:
    # stagioni: tutte dal 2020 al primo giro, poi una volta al giorno la lista delle stagioni (la nuova edizione di una competizione)
    if A.get("stagioni_agg", "")[:10] != today:
        for lid in COMP:
            r = get("leagues", id=lid).get("response", []); budget -= 1
            if r: A["stagioni"][str(lid)] = sorted(s["year"] for s in r[0]["seasons"] if s["year"] >= 2020 and s.get("coverage", {}).get("fixtures", {}).get("statistics_fixtures"))
        A["stagioni_agg"] = NOW.isoformat(timespec="minutes")
    # partite: ogni stagione una volta (archivio); le stagioni con partite da ieri a +16 giorni a ogni giro, le altre recenti una volta al giorno
    for lid, ys in A["stagioni"].items():
        for y in ys:
            k = f"{lid}|{y}"; last = A["liste"].get(k, "")
            mine = [v for v in A["partite"].values() if str(v[1]) == lid and v[0][:4] in (str(y), str(y + 1))]
            live = any(-1 <= tday(v[0]) - TNOW <= 16 and v[9] not in FIN for v in mine) or any(0 <= TNOW - tday(v[0]) <= 2 for v in mine)
            recent = y >= NOW.year - 1
            if budget <= 45: break
            if not last or live or (recent and last[:10] != today):
                R = get("fixtures", league=lid, season=y); budget -= 1
                if R.get("errors"): print(k, R["errors"]); continue
                for f in R.get("response", []): take(f)
                A["liste"][k] = NOW.isoformat(timespec="minutes")
    # statistiche delle partite finite: mancanti (le nuove, ritentate fino a 3 giorni) e una correzione a 36 ore
    todo = [fid for fid, v in A["partite"].items() if v[9] in FIN and (v[7][2] is None and (TNOW - tday(v[0]) < 3 or not A.get("tentato", {}).get(fid))
            or (1.5 <= TNOW - tday(v[0]) <= 3 and not A.get("corretto", {}).get(fid)))]
    for i in range(0, len(todo), 20):
        if budget <= 40: break
        R = get("fixtures", ids="-".join(todo[i:i + 20])); budget -= 1
        for f in R.get("response", []):
            fid = str(f["fixture"]["id"]); take(f); A.setdefault("tentato", {})[fid] = 1
            if TNOW - tday(f["fixture"]["date"]) >= 1.5: A.setdefault("corretto", {})[fid] = 1
            st_ = {t["team"]["id"]: t for t in f.get("statistics", [])}
            H, W = st_.get(f["teams"]["home"]["id"]), st_.get(f["teams"]["away"]["id"])
            if H and W:
                A["partite"][fid][7] = [stat(H, k) for k in KS]; A["partite"][fid][8] = [stat(W, k) for k in KS]
                ev = {f["teams"]["home"]["id"]: [0, 0], f["teams"]["away"]["id"]: [0, 0]}   # cartellini anche dagli eventi (il valore più alto)
                for e in f.get("events") or []:
                    t_ = (e.get("team") or {}).get("id"); d_ = e.get("detail") or ""
                    if e.get("type") == "Card" and t_ in ev and (e.get("player") or {}).get("id"): ev[t_][1 if ("Red" in d_ or "Second" in d_) else 0] += 1
                for j, tid in ((7, f["teams"]["home"]["id"]), (8, f["teams"]["away"]["id"])):
                    x = A["partite"][fid][j]
                    if x[4] is not None: x[4] = max(x[4], ev[tid][0]); x[5] = max(x[5] or 0, ev[tid][1])
    A["agg"] = NOW.isoformat(timespec="minutes")
    json.dump(A, open(AF, "w"), ensure_ascii=False, separators=(",", ":"))
print("archivio:", len(A["partite"]), "partite ·", sum(1 for v in A["partite"].values() if v[9] in FIN and v[7][2] is not None), "con statistiche · richieste", used)

# ---------------- 2. modello ----------------
def val(v, s):
    if s == "g": return (v[4], v[5]) if v[4] is not None and v[5] is not None else None
    H, W = v[7], v[8]
    if s == "k": return (H[4] + (H[5] or 0), W[4] + (W[5] or 0)) if H[4] is not None and W[4] is not None else None
    i = STATS[s]; return (H[i], W[i]) if H[i] is not None and W[i] is not None else None
played = sorted([(fid, v) for fid, v in A["partite"].items() if v[9] in FIN], key=lambda x: x[1][0])
class Model:
    def __init__(self, s):
        self.s = s; self.rows = [(tday(v[0]), v[2], v[3]) + val(v, s) for fid, v in played if val(v, s)]
    def predict(self, t, pairs):   # pairs: [(casa, ospite)] con i soli dati prima di t (giorni)
        R = [r for r in self.rows if r[0] < t - 1e-6]
        if len(R) < 100: return [None for _ in pairs]
        mu = sum(r[3] + r[4] for r in R[-NMU:]) / len(R[-NMU:]) / 2
        H = collections.defaultdict(list)
        for d0, h, a, x, y in R: H[h].append((d0, x, y)); H[a].append((d0, y, x))
        def rate(team, side):
            ws, sm = PRIOR, PRIOR * mu
            for d0, f_, a_ in H.get(team, ()):
                w = 0.5 ** ((t - d0) / HL); ws += w; sm += w * (f_ if side == 0 else a_)
            return sm / ws
        out = []
        for h, a in pairs:
            fh, ah, fa, aa = rate(h, 0), rate(h, 1), rate(a, 0), rate(a, 1)
            out.append((fh * aa / mu, fa * ah / mu, min(len(H.get(h, ())), len(H.get(a, ())))))
        return out
MODELS = {s: Model(s) for s in STATS}

# previsioni walk-forward delle ultime 400 partite giocate: dispersione e controllo (errore contro la media)
ALPHA, CHECK = {}, {}
for s, M in MODELS.items():
    last = M.rows[-400:]; byd = collections.defaultdict(list)
    for r in last: byd[math.floor(r[0])].append(r)
    se, ml, ml2, em, eb = [], [], [], [], []
    for d0, rs in byd.items():
        P = M.predict(d0, [(r[1], r[2]) for r in rs])
        R0 = [r for r in M.rows if r[0] < d0]; mu = sum(r[3] + r[4] for r in R0[-NMU:]) / max(1, len(R0[-NMU:])) / 2
        for r, p in zip(rs, P):
            if not p: continue
            for y, l in ((r[3], p[0]), (r[4], p[1])): se.append((y - l) ** 2); ml.append(l); ml2.append(l * l)
            em.append(abs(r[3] + r[4] - p[0] - p[1])); eb.append(abs(r[3] + r[4] - 2 * mu))
    ALPHA[s] = 0.0 if s == "g" or not ml else max(0.0, (np.mean(se) - np.mean(ml)) / np.mean(ml2))
    CHECK[s] = {"errore_modello": round(float(np.mean(em)), 3) if em else None, "errore_media": round(float(np.mean(eb)), 3) if eb else None, "partite": len(em)}
note("Nazionali · modello", " · ".join(f"{s}: errore totale {CHECK[s]['errore_modello']} contro media {CHECK[s]['errore_media']} (α {ALPHA[s]:.3f})" for s in STATS))

# ---------------- 3. previsioni: congelate prima del calcio d'inizio, a posteriori per le giocate senza previsione ----------------
LOGF = os.path.join(DIR, "naz_log.json"); LOG = json.load(open(LOGF)) if os.path.exists(LOGF) else {}
upcoming = [(fid, v) for fid, v in A["partite"].items() if v[9] in ("NS", "TBD") and 0 <= tday(v[0]) - TNOW <= 16]
recent = [(fid, v) for fid, v in played if TNOW - tday(v[0]) <= 31 and fid not in LOG]
byd = collections.defaultdict(list)
for fid, v in recent: byd[math.floor(tday(v[0]))].append((fid, v))
for d0, L in byd.items():
    for s, M in MODELS.items():
        P = M.predict(d0, [(v[2], v[3]) for _, v in L])
        for (fid, v), p in zip(L, P):
            e = LOG.setdefault(fid, {"dt": v[0], "h": v[2], "a": v[3], "P": {}, "fonte": "a posteriori, dati precedenti"})
            e["P"][s] = p and [round(p[0], 3), round(p[1], 3), p[2]]
for s, M in MODELS.items():
    P = M.predict(TNOW, [(v[2], v[3]) for _, v in upcoming])
    for (fid, v), p in zip(upcoming, P):
        e = LOG.setdefault(fid, {"P": {}}); e.update(dt=v[0], h=v[2], a=v[3], fonte="prima del calcio d'inizio", calcolata=NOW.isoformat(timespec="minutes"))
        e["P"][s] = p and [round(p[0], 3), round(p[1], 3), p[2]]
LOG = {k: e for k, e in LOG.items() if TNOW - tday(e["dt"]) <= 400}
json.dump(LOG, open(LOGF, "w"), ensure_ascii=False, separators=(",", ":"))

# ---------------- 4. uscita per l'app (stesso formato di ucl.json) ----------------
def pmf(mu, al, K):
    if al < 1e-3: return poisson.pmf(np.arange(K), mu)
    r = 1 / al; return nbinom.pmf(np.arange(K), r, r / (r + mu))
def interval(p, lo=0.10, hi=0.90):
    c = np.cumsum(p / p.sum()); return [int(np.searchsorted(c, lo)), int(np.searchsorted(c, hi))]
def block(e, s):
    p = e["P"].get(s)
    if not p: return None
    ph, pa = p[0], p[1]; al = ALPHA[s]; K = 80 if s in ("s", "f") else 40
    a, b = pmf(ph, al, K), pmf(pa, al, K); t = np.convolve(a, b)[:K]
    return [round(ph, 2), round(pa, 2), interval(a), interval(b), interval(t), round(al, 4)]
def goals(e):
    p = e["P"].get("g")
    if not p: return None
    M = np.outer(poisson.pmf(np.arange(11), p[0]), poisson.pmf(np.arange(11), p[1])); M /= M.sum()
    p1, px = float(np.tril(M, -1).sum()), float(np.trace(M)); tot = np.add.outer(np.arange(11), np.arange(11))
    r = lambda x: round(x, 3)
    top = sorted(((float(M[i, j]), f"{i}-{j}") for i in range(7) for j in range(7)), reverse=True)[:5]
    return {"1": r(p1), "X": r(px), "2": r(1 - p1 - px), "ov": [r(float(M[tot > L].sum())) for L in (1.5, 2.5, 3.5)], "gg": r(float(M[1:, 1:].sum())), "top": [[k, r(q)] for q, k in top]}
# gironi (8/11/2026, Denny: classifica come i club): squadre collegate dalle partite della stessa competizione e stagione con turno di girone
# ("League A - 5", "Group B - 3", "Group Stage - 2"…); niente richieste in più. Per la classifica dell'app: elenco delle partite del girone.
import re as _re
def _loc(dt):   # data locale italiana (come gli id dell'app)
    return (datetime.datetime.fromisoformat(dt[:16]).replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=1 if not (3 < int(dt[5:7]) < 10) else 2)))).date().isoformat()
def _phase(rnd): m = _re.match(r"^(League [A-D]|Group [A-L]|Group Stage|Regular Season|1st Round|2nd Round|3rd Round)", rnd or ""); return m.group(1) if m else None
GRP, G_OF = [], {}
byc = collections.defaultdict(list)
for fid, v in A["partite"].items():
    ph = _phase(v[10])
    if ph: byc[(v[1], ph, min(int(v[0][:4]), 9999))].append((fid, v))
# stessa edizione: partite della stessa competizione e fase entro 400 giorni l'una dall'altra, unite per squadre in comune
for (lid, ph, _y), L in byc.items(): pass
byk = collections.defaultdict(list)
for (lid, ph, y), L in byc.items(): byk[(lid, ph)].extend(L)
for (lid, ph), L in byk.items():
    L.sort(key=lambda x: x[1][0]); par = {}
    def find(x):
        while par.setdefault(x, x) != x: par[x] = par[par[x]]; x = par[x]
        return x
    # edizione = finestra di date (nuova edizione se passano più di 300 giorni dalla partita precedente della stessa competizione)
    ed, last, eds = 0, None, {}
    for fid, v in L:
        t = tday(v[0])
        if last is not None and t - last > 300: ed += 1
        last = t; eds[fid] = ed
        a_, b_ = f"{ed}|{v[2]}", f"{ed}|{v[3]}"; par[find(a_)] = find(b_)
    comp = collections.defaultdict(list)
    for fid, v in L: comp[find(f"{eds[fid]}|{v[2]}")].append((fid, v))
    for root, M_ in comp.items():
        teams = sorted({v[2] for _, v in M_} | {v[3] for _, v in M_})
        if len(teams) < 3 or len(teams) > 12: continue
        gi = len(GRP); GRP.append({"nome": f"{COMP.get(lid, '')} · {ph.replace('League ', 'Lega ').replace('Group Stage', 'Fase a gironi').replace('Group ', 'Girone ').replace('Regular Season', 'Girone unico')}",
                                   "squadre": [IT_(t) for t in teams], "partite": [[_loc(v[0]), IT_(v[2]), IT_(v[3])] for _, v in sorted(M_, key=lambda x: x[1][0])]})
        for fid, _ in M_: G_OF[fid] = gi
LOGHI = {}
for v in A["partite"].values():
    if v[11]: LOGHI[IT_(v[2])] = v[11]
    if v[12]: LOGHI[IT_(v[3])] = v[12]
OUT = []
for fid, e in LOG.items():
    dd = tday(e["dt"]) - TNOW
    if dd < -31 or dd > 16: continue
    v = A["partite"].get(fid)
    if not v or v[9] in ("CANC", "ABD", "AWD", "WO", "PST"): continue
    res = {s: (lambda y: [int(y[0]), int(y[1])] if y else None)(val(v, s)) for s in STATS} if v[9] in FIN else None
    pre = min((p[2] for p in e["P"].values() if p), default=0)
    OUT.append({"id": fid, "dt": e["dt"], "h": IT_(e["h"]), "a": IT_(e["a"]), "round": f"{COMP.get(v[1], '')} · {v[10]}".strip(" ·"), "comp": COMP.get(v[1], ""),
                "lh": v[11], "la": v[12], "stato": v[9], "gruppo": G_OF.get(fid), "p": {s: block(e, s) for s in STATS}, "gol": goals(e), "ris": res, "fonte": e.get("fonte", ""), "prec": pre})
OUT.sort(key=lambda x: (x["dt"], x["h"]))
_used = sorted({x["gruppo"] for x in OUT if x.get("gruppo") is not None}); _ren = {g: i for i, g in enumerate(_used)}
for x in OUT: x["gruppo"] = _ren.get(x.get("gruppo"))
json.dump({"updated": NOW.isoformat(timespec="minutes"), "controllo": CHECK, "dispersione": {s: round(a, 4) for s, a in ALPHA.items()}, "partite": OUT,
           "gruppi": [GRP[g] for g in _used], "loghi": LOGHI},
          open(os.path.join(DIR, "naz.json"), "w"), ensure_ascii=False, separators=(",", ":"))
note("Nazionali · uscita", f"naz.json: {len(OUT)} partite ({sum(1 for x in OUT if x['ris'])} giocate, {sum(1 for x in OUT if not x['ris'])} in arrivo) · richieste usate {used}")
