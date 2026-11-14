"""Player props · dati per la tab "Giocatori" della scheda partita (14/11/2026, Denny). Solo Serie A, Premier, Liga, Bundesliga, Ligue 1
(e le stesse squadre in Champions).

Stesso modello del test (tools/props/test_props.py + test_props_cal.py, IPOTESI.md 14/11/2026), con i parametri scelti nel periodo "scelta":
  valore ogni 90' del giocatore da TUTTE le competizioni dell'archivio formazioni (media mobile per presenza, peso DP) ristretto verso la
  media del ruolo con K partite fittizie × minuti attesi da titolare (media mobile 0,9, ristretta verso il ruolo con 3 partite) × scala.
  Mercati: tiri in porta (DP 0,97, K 5, α 0,2, scala 0,94) · falli commessi (0,97, 5, 0,1, 0,97) · falli subiti (0,97, 5, 0,1, 0,96)
  · cartellini (0,99, 20, Poisson, nessuna scala).
L'app moltiplica il valore per (attesi di oggi della squadra da Prevista / media abituale delle attese della squadra): tiri in porta e falli
della squadra, falli subiti = falli attesi dell'AVVERSARIA, cartellini = falli × severità dell'arbitro. Qui le medie abituali (dalla base
walk-forward dell'app, ramo ricerca) e la severità degli arbitri (cartellini a partita / media del campionato, 10 partite fittizie).
Probabili titolari: gli 11 con più presenze da titolare recenti (peso 0,85 a partita, tutte le competizioni): 1 portiere + 10.
Uso: python tools/props/giocatori.py FORMAZIONI BASE STORICO USCITA.json"""
import json, glob, sys, os, datetime, collections
import numpy as np
FORM, BASE, STOR, OUT = (sys.argv[1:5] + ["ricerca/form2", "ricerca/base", "ricerca/storico", "giocatori.json"][len(sys.argv) - 1:])[:4]
TOP = ["I1", "E0", "SP1", "D1", "F1"]
POS = {"G": 0, "D": 1, "M": 2, "F": 3}
ST = ["sot", "fc", "fd", "yc"]
DP = {"sot": 0.97, "fc": 0.97, "fd": 0.97, "yc": 0.99}; KK = {"sot": 5.0, "fc": 5.0, "fd": 5.0, "yc": 20.0}
ALPHA = {"sot": 0.2, "fc": 0.1, "fd": 0.1, "yc": 0.0}; SCALA = {"sot": 0.94, "fc": 0.97, "fd": 0.96, "yc": 1.0}
def vec(r): return np.array([r[10] or 0, r[7] or 0, r[8] or 0, (r[5] or 0) + (r[6] or 0)], float)

FX, NOMI = [], {}
for fn in glob.glob(FORM + "/*.json"):
    D = json.load(open(fn))
    if "lega" not in D or not isinstance(D.get("partite"), dict): continue
    NOMI.update(D.get("nomi") or {})
    for fid, v in D["partite"].items():
        if v[9]: FX.append((v[0], D["lega"], fid, v))
FX.sort()
REF = {}
for fn in glob.glob(STOR + "/*.json"):
    P = json.load(open(fn)).get("partite") or {}
    for fid, v in (P.items() if isinstance(P, dict) else P):
        if len(v) > 5 and v[5]: REF[str(fid)] = str(v[5]).split(",")[0].strip()
B = {lg: json.load(open(f"{BASE}/{lg}.json")) for lg in TOP if os.path.exists(f"{BASE}/{lg}.json")}

# nomi API-Football → nomi dell'app (stessa data ±1 e stesso risultato, come nel test)
bidx = collections.defaultdict(list)
for lg, rows in B.items():
    for r in rows: bidx[(lg, r["d"], r["y"]["g"][0], r["y"]["g"][1])].append(r)
vote = collections.defaultdict(collections.Counter)
for d, lg, fid, v in FX:
    if lg not in B: continue
    for dd in (0, -1, 1):
        k = (lg, str(datetime.date.fromisoformat(d[:10]) + datetime.timedelta(days=dd)), v[5], v[6])
        if len(bidx.get(k, [])) == 1:
            b = bidx[k][0]; vote[(lg, v[1])][b["h"]] += 1; vote[(lg, v[2])][b["a"]] += 1
NAME = {k: c.most_common(1)[0][0] for k, c in vote.items() if c.most_common(1)[0][1] >= 3}
TEAM_LG = {tid: lg for (lg, tid) in NAME}

# medie abituali delle attese dell'app per squadra (peso 0,9 a partita)
hab = collections.defaultdict(lambda: np.zeros(4))
for lg, rows in B.items():
    for r in sorted(rows, key=lambda r: r["d"]):
        for nm, sk in ((r["h"], 0), (r["a"], 1)):
            st, f = r.get("st"), r.get("f")
            if not st or not f: continue
            x = np.array([st[sk], f[sk], f[1 - sk], 1.0]); h = hab[(lg, nm)]; h *= 0.9; h += x

pl, pmin, role, team_starts, team_of = {}, {}, {}, collections.defaultdict(dict), {}
last_seen, team_last = {}, {}
G = np.zeros((4, 2, 4)); G[:, 0] = 1e-9; GM = np.zeros((4, 2)); GM[:, 1] = 1e-9
ref_st, lgc = {}, collections.defaultdict(lambda: [0.0, 1e-9])
for d, lg, fid, v in FX:
    _, hid, aid, hn, an, hg, ag, xh, xa, P = v
    xs = set(xh) | set(xa)
    if lg in TOP and d[:10] <= datetime.date.today().isoformat(): team_last[hid] = team_last[aid] = d[:10]
    for tid, xi in ((hid, xh), (aid, xa)):
        stt = team_starts[tid]
        for p in list(stt): stt[p] *= 0.85
        for p in xi: stt[p] = stt.get(p, 0) + 1
    tc = 0
    for r in P:
        p = r[0]
        if r[11]: role[p] = r[11]
        team_of[p] = hid if r[1] == 0 else aid; last_seen[p] = d[:10]
        rr = POS.get(role.get(p, "M"), 2); x = vec(r); mi = r[2] or 0; tc += x[3]
        a = pl.setdefault(p, np.zeros((2, 4)))
        for j, s in enumerate(ST): a[0, j] = a[0, j] * DP[s] + mi; a[1, j] = a[1, j] * DP[s] + x[j]
        G[rr] *= 0.9999; G[rr, 0] += mi; G[rr, 1] += x
        if p in xs:
            m = pmin.setdefault(p, [0.0, 0.0]); m[0] = m[0] * 0.9 + mi; m[1] = m[1] * 0.9 + 1
            GM[rr] *= 0.9999; GM[rr, 0] += mi; GM[rr, 1] += 1
    ref = REF.get(fid)
    if ref:
        rs = ref_st.setdefault(ref, [0.0, 0.0, lg]); rs[0] = rs[0] * 0.95 + tc; rs[1] = rs[1] * 0.95 + 1; rs[2] = lg
    c = lgc[lg]; c[0] = c[0] * 0.995 + tc; c[1] = c[1] * 0.995 + 1

def mu(p, rr=None):
    rr = POS.get(role.get(p, "M"), 2) if rr is None else rr
    g = G[rr, 1] / G[rr, 0] * 90; a = pl.get(p)
    rate = np.array([g[j] if a is None else (a[1, j] + KK[s] * g[j]) / (a[0, j] / 90 + KK[s]) for j, s in enumerate(ST)])
    gm = GM[rr, 0] / GM[rr, 1]; m = pmin.get(p); mins = gm if m is None else (m[0] + 3 * gm) / (m[1] + 3)
    return rate * mins / 90 * np.array([SCALA[s] for s in ST]), mins

today = min(max(d for d, *_ in FX)[:10], datetime.date.today().isoformat()); cut = str(datetime.date.fromisoformat(today) - datetime.timedelta(days=400))
SQ, GI = {}, {}
for (lg, tid), nm in NAME.items():
    h = hab.get((lg, nm))
    if h is None or h[3] < 3 or team_last.get(tid, "") < str(datetime.date.fromisoformat(today) - datetime.timedelta(days=60)): continue   # solo squadre che giocano ora in quel campionato
    stt = team_starts.get(tid, {})
    rosa = [p for p, w in sorted(stt.items(), key=lambda z: -z[1]) if team_of.get(p) == tid and last_seen.get(p, "") >= cut]
    gk = [p for p in rosa if role.get(p) == "G"][:1]; out = [p for p in rosa if role.get(p) != "G"][:10]
    SQ[nm] = {"lg": lg, "id": tid, "ab": [round(float(z), 3) for z in h[:3] / h[3]], "xi": gk + out,
              "rosa": [p for p in rosa if role.get(p) == "G"][:3] + [p for p in rosa if role.get(p) != "G"][:20]}   # 14/11: riserve per sostituire gli assenti
    for p in rosa[:30]:
        m, mins = mu(p); GI[str(p)] = [NOMI.get(str(p), ""), role.get(p, "M"), round(float(mins)), *[round(float(z), 4) for z in m]]
RUOLO = {k: [round(float(z), 4) for z in mu(None, i)[0]] for k, i in POS.items()}
ARB = {}
for ref, (c, n, lg) in ref_st.items():
    lm = lgc[lg][0] / lgc[lg][1]
    if n >= 3 and lm > 0: ARB[ref] = round(((c + 10 * lm) / (n + 10)) / lm, 3)
API = {}
for d, lg, fid, v in FX:
    if lg in TOP:
        for tid, an_ in ((v[1], v[3]), (v[2], v[4])):
            nm = NAME.get((lg, tid))
            if nm in SQ and an_ != nm: API[an_] = nm   # nomi di API-Football (Champions) → nomi dell'app
J = {"api": API, "agg": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"), "dati_fino_al": today, "mercati": ST, "alpha": ALPHA, "scala": SCALA,
     "squadre": SQ, "giocatori": GI, "ruolo": RUOLO, "arbitri": ARB}
json.dump(J, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"::notice title=Giocatori::squadre {len(SQ)} · giocatori {len(GI)} (con nome {sum(1 for g in GI.values() if g[0])}) · arbitri {len(ARB)} · dati fino al {today}")
