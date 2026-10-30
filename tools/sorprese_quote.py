"""SORPRESE sull'archivio privato delle quote 1xBet (30/10/2026, studio di Denny, passi 1 e 3). Gira nel runner dopo tools/quota23.js
(probabilità di Prevista con i soli dati precedenti) e tools/quota23.py (probabilità corretta walk-forward). Stampa SOLO numeri aggregati.
Per ogni 1X2 (gol, corner, tiri, tiri in porta, falli, fuorigioco, gialli) con le tre quote 1xBet "ultima prima del fischio":
  favorita = quota più bassa tra 1 e 2, sfavorita = l'altra; si tengono le partite con la sfavorita a quota ≥ 2,30.
  Caso A · inversione: Prevista dà la sfavorita più probabile della favorita.
  Caso B · forbice: 1xBet senza margine dà la sfavorita sotto il 35% e Prevista almeno +10 punti (anche +12).
  Caso C · valore con la probabilità corretta: sfavorita a quota ≥ 2,30 con valore atteso positivo usando la corretta.
  Riferimento: tutte le sfavorite a quota ≥ 2,30 (giocarle alla cieca costa il margine di 1xBet).
Misure: giocate, presa reale, probabilità 1xBet senza margine, di Prevista e corretta, quota media, rendimento a puntata fissa (IC 95%
raggruppato per partita), le due metà dei giorni, fasce di quota 2,30-2,99 · 3,00-4,00 · oltre 4.
Più il "blasone": quante volte 1xBet mette favorita nel mercato statistico la stessa squadra favorita nei gol, contro Prevista e la realtà."""
import json, math, os, sys, collections, traceback
import numpy as np
sys.excepthook = lambda t, v, tb: print("::error title=Sorprese::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))
C = json.load(open("q23_candidati.json"))
PC = {}
if os.path.exists("q23_corrette_q1.json"):
    for c in json.load(open("q23_corrette_q1.json")): PC[(c["key"], c["mk"], c["side"])] = c.get("pc_q1")
G = collections.defaultdict(dict)
for c in C:
    if c["mk"].startswith("1X2") and c.get("q1"): G[(c["key"], c["mk"])][c["side"]] = c
days = sorted({k[0].split("|")[1] for k in G}); half = days[len(days) // 2] if days else ""
rows = []
for (key, mk), S in G.items():
    if not all(s in S for s in ("1", "X", "2")): continue
    inv = {s: 1 / S[s]["q1"] for s in S}; tot = sum(inv.values()); m = {s: inv[s] / tot for s in S}
    fav, und = ("1", "2") if S["1"]["q1"] <= S["2"]["q1"] else ("2", "1")
    u = S[und]; pc = PC.get((key, mk, und))
    rows.append(dict(key=key, d=key.split("|")[1], mk=mk, q=u["q1"], y=u["y"], p=u["p"], pf=S[fav]["p"], m=m[und], mf=m[fav], pc=pc,
                     pxi=u.get("pxi"), pfxi=S[fav].get("pxi"), fav=fav, yfav=S[fav]["y"]))
def st(R, pk="p"):
    if not R: return "nessuna"
    n = len(R); h = np.mean([r["y"] for r in R]); pl = np.array([r["y"] * r["q"] - 1 for r in R]); roi = pl.mean()
    g = collections.defaultdict(float)
    for r, v in zip(R, pl): g[r["key"]] += v - roi
    ci = 1.96 * math.sqrt(sum(v * v for v in g.values())) / n
    pcs = [r["pc"] for r in R if r["pc"] is not None]
    return (f"{n} (presa {100 * h:.0f}% · 1xBet {100 * np.mean([r['m'] for r in R]):.0f}% · Prevista {100 * np.mean([r[pk] for r in R]):.0f}%"
            f"{f' · corretta {100 * np.mean(pcs):.0f}%' if pcs else ''} · quota {np.mean([r['q'] for r in R]):.2f} · rendimento {100 * roi:+.1f}% ±{100 * ci:.0f})")
def block(R, pk="p"):
    a, b = [r for r in R if r["d"] < half], [r for r in R if r["d"] >= half]
    bands = [("2,30-2,99", 2.30, 3.0), ("3,00-4,00", 3.0, 4.0001), ("oltre 4", 4.0001, 99)]
    return f"{st(R, pk)} · metà 1: {st(a, pk)} · metà 2: {st(b, pk)} · " + " · ".join(f"{lab}: {st([r for r in R if lo <= r['q'] < hi], pk)}" for lab, lo, hi in bands)
MKS = ["1X2 gol", "1X2 corner", "1X2 tiri", "1X2 tiri in porta", "1X2 falli", "1X2 fuorigioco", "1X2 gialli"]
note("Sorprese · archivio", f"giorni {days[0] if days else '-'} → {days[-1] if days else '-'} ({len(days)}) · 1X2 con le tre quote {len(rows)} · con sfavorita a quota ≥ 2,30 {sum(1 for r in rows if r['q'] >= 2.30)} · probabilità corretta disponibile per {sum(1 for r in rows if r['pc'] is not None)}")
for mk in MKS:
    R = [r for r in rows if r["mk"] == mk and r["q"] >= 2.30]
    if not R: continue
    A_ = [r for r in R if r["p"] > r["pf"]]
    B10 = [r for r in R if r["m"] < 0.35 and r["p"] - r["m"] >= 0.10]; B12 = [r for r in R if r["m"] < 0.35 and r["p"] - r["m"] >= 0.12]
    C_ = [r for r in R if r["pc"] is not None and r["pc"] * r["q"] - 1 > 0]
    txt = (f"TUTTE le sfavorite ≥ 2,30: {st(R)} ‖ A inversione: {block(A_)} ‖ B forbice +10: {block(B10)} ‖ B forbice +12: {st(B12)} ‖ "
           f"C valore con la corretta: {block(C_, 'pc')}")
    if mk == "1X2 falli":
        AX = [r for r in R if r["pxi"] is not None and r["pfxi"] is not None and r["pxi"] > r["pfxi"]]
        txt += f" ‖ A inversione con le formazioni ufficiali: {st(AX, 'pxi')}"
    note(f"Sorprese · {mk}", txt)
# blasone: la favorita di 1xBet nel mercato statistico è la stessa favorita nei gol?
fg = {r["key"]: r["fav"] for r in rows if r["mk"] == "1X2 gol"}
pg = {}
for (key, mk), S in G.items():
    if mk == "1X2 gol" and all(s in S for s in ("1", "2")): pg[key] = "1" if S["1"]["p"] >= S["2"]["p"] else "2"
out = []
for mk in MKS[1:]:
    R = [r for r in rows if r["mk"] == mk and r["key"] in fg and r["key"] in pg]
    if not R: continue
    same_bk = np.mean([r["fav"] == fg[r["key"]] for r in R])
    S_ = {(r["key"]): G[(r["key"], mk)] for r in R}
    same_pv = np.mean([("1" if S_[r["key"]]["1"]["p"] >= S_[r["key"]]["2"]["p"] else "2") == pg[r["key"]] for r in R])
    real = [("1" if S_[r["key"]]["1"]["y"] else "2" if S_[r["key"]]["2"]["y"] else None) for r in R]
    same_re = np.mean([rr == fg[r["key"]] for r, rr in zip(R, real) if rr is not None]) if any(real) else float("nan")
    out.append(f"{mk[4:]}: 1xBet {100 * same_bk:.0f}% · Prevista {100 * same_pv:.0f}% · vince davvero la favorita nei gol {100 * same_re:.0f}% ({len(R)})")
note("Sorprese · blasone (favorita nel mercato = favorita nei gol)", " ‖ ".join(out))
