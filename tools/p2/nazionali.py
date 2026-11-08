"""Fattibilità NAZIONALI (8/11/2026, richiesta di Denny). Richieste solo dalla riserva per le prove (tools/af_budget.py). Stampa SOLO numeri
aggregati. Tre domande:
  1. Quante partite di nazionali con statistiche complete ha API-Football (2021 → oggi), per competizione.
  2. Un modello per squadra (corner, falli, tiri, tiri in porta, cartellini, fuorigioco: forza fatta/subita con decadimento, ritirata verso la
     media) batte la media semplice? Walk-forward, periodi del banco di prova: scelta ≤ 30/06/2024 · verifica 07/2024-06/2025 · holdout ≥ 07/2025.
     Misure: errore medio assoluto del totale contro la media di tutte le partite precedenti; Brier di "chi ne fa di più" contro il 50/50 del
     modello senza squadre (pari tolti). IC 95% bootstrap per partita.
  3. Quante quote passano i book via API-Football sulle partite di nazionali dei prossimi giorni (corner, cartellini)."""
import json, os, sys, math, random, datetime, urllib.request, urllib.parse, collections, traceback
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.excepthook = lambda t, v, tb: print("::error title=Nazionali::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
import af_budget
KEY = os.environ["APIFOOTBALL_KEY"].strip(); nreq = 0
def af(path, **q):
    global nreq; nreq += 1
    req = urllib.request.Request("https://v3.football.api-sports.io/" + path + ("?" + urllib.parse.urlencode(q) if q else ""), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))
free = af_budget.test_budget(af_budget.requests_of(af("status")))
MAXR = min(400, free - 20)
if MAXR < 120: note("Nazionali", f"riserva per le prove insufficiente ({free}): riprovare più tardi"); sys.exit(0)
COMP = {1: "Mondiale", 4: "Europeo", 5: "Nations League", 960: "Qualificazioni Europeo", 32: "Qualificazioni Mondiale UEFA", 34: "Qualificazioni Mondiale CONMEBOL",
        31: "Qualificazioni Mondiale CONCACAF", 30: "Qualificazioni Mondiale AFC", 29: "Qualificazioni Mondiale CAF", 9: "Copa América", 6: "Coppa d'Africa", 10: "Amichevoli"}
# 1 · copertura
cov = {}
for lid in COMP:
    r = af("leagues", id=lid).get("response", [])
    for s in (r[0]["seasons"] if r else []):
        if s["year"] >= 2020: cov[(lid, s["year"])] = bool(s.get("coverage", {}).get("fixtures", {}).get("statistics_fixtures"))
FX = []
for (lid, yr), st in sorted(cov.items()):
    if not st or lid == 10 or nreq > MAXR - 60: continue
    for f in af("fixtures", league=lid, season=yr).get("response", []):
        if f["fixture"]["status"]["short"] in ("FT", "AET", "PEN"): FX.append(f)
ids = [str(f["fixture"]["id"]) for f in FX]
KS = {"Corner Kicks": "c", "Fouls": "f", "Total Shots": "s", "Shots on Goal": "st", "Yellow Cards": "y", "Red Cards": "r", "Offsides": "o"}
S = {}
for i in range(0, len(ids), 20):
    if nreq >= MAXR - 6: break
    for f in af("fixtures", ids="-".join(ids[i:i + 20])).get("response", []):
        st = {t["team"]["id"]: {x["type"]: x["value"] for x in t.get("statistics", [])} for t in f.get("statistics", [])}
        h, a = f["teams"]["home"]["id"], f["teams"]["away"]["id"]
        if h not in st or a not in st or st[h].get("Corner Kicks") is None: continue
        g = lambda d, k: (float(d.get(k)) if d.get(k) not in (None, "") else (0.0 if k in ("Yellow Cards", "Red Cards") else None))
        S[str(f["fixture"]["id"])] = dict(d=f["fixture"]["date"][:10], lg=f["league"]["id"], h=h, a=a, neutral=bool(f["fixture"].get("venue", {}).get("city")) and False,
                                          **{"h" + v: g(st[h], k) for k, v in KS.items()}, **{"a" + v: g(st[a], k) for k, v in KS.items()})
per = collections.Counter(COMP[v["lg"]] for v in S.values()); fin = collections.Counter(COMP[f["league"]["id"]] for f in FX)
note("Nazionali · 1 · dati", f"{nreq} richieste · partite giocate {len(FX)} · con statistiche complete {len(S)} (fetch limitato dalla riserva: {'sì' if len(ids) > 20 * (nreq) else 'no'}) ‖ " +
     " · ".join(f"{c}: {per[c]}/{fin[c]}" for c in fin) + " ‖ stagioni con statistiche: " + ", ".join(f"{COMP[l][:14]} {y}" for (l, y), s in sorted(cov.items()) if s))
# 2 · modello per squadra contro la media
M = sorted(S.values(), key=lambda v: v["d"])
for v in M: v["hk"] = (v["hy"] or 0) + (v["hr"] or 0); v["ak"] = (v["ay"] or 0) + (v["ar"] or 0)
per_ = lambda d: "scelta" if d <= "2024-06-30" else "verifica" if d <= "2025-06-30" else "holdout"
HL = 540.0; PRIOR = 4.0
out = []
for k, lab in (("c", "Corner"), ("f", "Falli"), ("s", "Tiri"), ("st", "Tiri in porta"), ("k", "Cartellini"), ("o", "Fuorigioco")):
    hist = collections.defaultdict(list); allv = []; R = collections.defaultdict(lambda: {"mae_m": [], "mae_b": [], "br_m": [], "br_b": []}); nfew = 0
    for v in M:
        x, y = v.get("h" + k), v.get("a" + k)
        if x is None or y is None: continue
        dd = datetime.date.fromisoformat(v["d"])
        if len(allv) >= 100:
            mu = sum(allv[-400:]) / len(allv[-400:]) / 2
            def rate(t, side):
                L = hist[t]; wsum = PRIOR; s_ = PRIOR * mu
                for (d0, f_, a_) in L:
                    w = 0.5 ** ((dd - d0).days / HL); wsum += w; s_ += w * (f_ if side == "f" else a_)
                return s_ / wsum, len(L)
            fh, nh = rate(v["h"], "f"); ah_, _ = rate(v["h"], "a"); fa, na = rate(v["a"], "f"); aa_, _ = rate(v["a"], "a")
            lh, la = fh * aa_ / mu, fa * ah_ / mu
            if min(nh, na) < 3: nfew += 1
            p = per_(v["d"]); R[p]["mae_m"].append(abs(x + y - lh - la)); R[p]["mae_b"].append(abs(x + y - 2 * mu))
            if x != y:
                ph = 1 / (1 + math.exp(-(lh - la) / max(0.5, math.sqrt(lh + la) * 0.9))); R[p]["br_m"].append((ph - (x > y)) ** 2); R[p]["br_b"].append(0.25)
        hist[v["h"]].append((dd, x, y)); hist[v["a"]].append((dd, y, x)); allv.append(x + y)
    def ci(a, b):
        d = [p - q for p, q in zip(a, b)]
        if len(d) < 20: return "pochi dati"
        m = sum(d) / len(d); random.seed(1); bs = sorted(sum(random.choice(d) for _ in d) / len(d) for _ in range(1000))
        return f"{m:+.3f} [{bs[25]:+.3f}, {bs[975]:+.3f}]"
    txt = []
    for p in ("scelta", "verifica", "holdout"):
        r = R[p]
        if not r["mae_m"]: txt.append(f"{p}: nessuna"); continue
        txt.append(f"{p} ({len(r['mae_m'])}): errore totale modello {sum(r['mae_m'])/len(r['mae_m']):.2f} contro media {sum(r['mae_b'])/len(r['mae_b']):.2f} (diff. {ci(r['mae_m'], r['mae_b'])}) · Brier chi ne fa di più {sum(r['br_m'])/max(1,len(r['br_m'])):.3f} contro 0,250 (diff. {ci(r['br_m'], r['br_b'])})")
    note(f"Nazionali · 2 · {lab}", " ‖ ".join(txt) + f" ‖ partite con meno di 3 precedenti per una delle due squadre: {nfew}")
# 3 · quote dei prossimi giorni
cnt = collections.Counter(); nfx = 0; books = collections.Counter()
for lid in (5, 10, 32, 960):
    if nreq >= MAXR: break
    for yr in (2026,):
        O = af("odds", league=lid, season=yr)
        for e in O.get("response", []):
            dd = e["fixture"]["date"][:10]
            if dd < datetime.date.today().isoformat(): continue
            nfx += 1
            for b in e.get("bookmakers", []):
                books[b["name"]] += 1
                for bt in b.get("bets", []):
                    n = (bt.get("name") or "").lower()
                    if "corner" in n: cnt["corner · " + bt["name"]] += 1
                    elif "card" in n: cnt["cartellini · " + bt["name"]] += 1
note("Nazionali · 3 · quote", f"partite in arrivo con quote: {nfx} · book: " + ", ".join(f"{b} {n}" for b, n in books.most_common(10)) + " ‖ mercati (book×partite): " + ", ".join(f"{m} {n}" for m, n in cnt.most_common(12)) + f" ‖ richieste totali {nreq}")
