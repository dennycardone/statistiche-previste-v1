"""Studio 8/11/2026 (domanda di Denny, da un post di un "software" esterno): quando il valore atteso di Prevista è molto sopra (o sotto)
la linea Over/Under del book, giocare Over (o Under) rende? Archivio privato 1xBet (linea x,5 più equilibrata, ultima quota prima del fischio),
previsioni di Prevista con i soli dati precedenti (tools/radar_mercato.js → rm_all.json). Stampa SOLO numeri aggregati.
Fasce di distanza d = atteso − linea; Over se d > 0, Under se d < 0. Per ogni fascia: giocate, presa, quota media, rendimento a puntata
fissa con IC 95% raggruppato per partita, le due metà dei giorni. Più il confronto con la regola già in uso (valore atteso > 0)."""
import json, math, collections
import numpy as np
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))
A = [r for r in json.load(open("rm_all.json")) if r.get("mu") is not None]
days = sorted({r["d"] for r in A}); half = days[len(days) // 2]
def st(R):
    if not R: return "nessuna"
    pl = np.array([r["y"] * r["q"] - 1 for r in R]); roi = pl.mean(); g = collections.defaultdict(float)
    for r, v in zip(R, pl): g[r["key"]] += v - roi
    ci = 1.96 * math.sqrt(sum(v * v for v in g.values())) / len(R)
    return f"{len(R)} · presa {100 * np.mean([r['y'] for r in R]):.0f}% · quota {np.mean([r['q'] for r in R]):.2f} · rendimento {100 * roi:+.1f}% ±{100 * ci:.0f}"
def blk(R): return f"{st(R)} ‖ metà 1: {st([r for r in R if r['d'] < half])} ‖ metà 2: {st([r for r in R if r['d'] >= half])}"
def bet(r, side): return dict(key=r["key"], d=r["d"], q=r["o"] if side == "O" else r["u"], y=r["over"] if side == "O" else 1 - r["over"])
note("Distanza dalla linea · archivio", f"{len(A)} linee con atteso di Prevista, giorni {days[0]} → {days[-1]} ({len(days)})")
GR = [("Corner totali", lambda r: r["k"] == "c"), ("Corner squadra", lambda r: r["k"] in ("hc", "ac")), ("Tiri totali", lambda r: r["k"] == "s"),
      ("Tiri in porta", lambda r: r["k"] in ("st", "hst", "ast")), ("Falli", lambda r: r["fam"] == "Falli"), ("Cartellini", lambda r: r["fam"] == "Cartellini")]
for name, f in GR:
    R = [r for r in A if f(r)]
    if not R: continue
    out = []
    for lab, lo, hi in (("Over d ≥ 3", 3, 99), ("Over 2 ≤ d < 3", 2, 3), ("Over 1 ≤ d < 2", 1, 2), ("Over 0 < d < 1", 0, 1)):
        out.append(f"{lab}: {st([bet(r, 'O') for r in R if lo <= r['mu'] - r['L'] < hi and r['mu'] > r['L']])}")
    for lab, lo, hi in (("Under −1 < d < 0", -1, 0), ("Under −2 < d ≤ −1", -2, -1), ("Under d ≤ −2", -99, -2)):
        out.append(f"{lab}: {st([bet(r, 'U') for r in R if lo < r['mu'] - r['L'] <= hi and r['mu'] < r['L']])}")
    note(f"Distanza · {name}", " ‖ ".join(out))
    big = [bet(r, "O") for r in R if r["mu"] - r["L"] >= 2]
    rel = [bet(r, "O") for r in R if r["L"] > 0 and r["mu"] / r["L"] >= 1.25]
    val = [bet(r, "O" if r["po"] * r["o"] - 1 >= (1 - r["po"]) * r["u"] - 1 else "U") for r in R if max(r["po"] * r["o"], (1 - r["po"]) * r["u"]) > 1]
    note(f"Distanza · {name} · regole", f"Over con atteso ≥ linea + 2: {blk(big)} ‖‖ Over con atteso ≥ 125% della linea: {blk(rel)} ‖‖ regola attuale (lato con valore atteso > 0): {blk(val)}")
# la loro combo: corner casa e ospite entrambi Over con atteso ≥ linea + 1,5 (stima a quote separate: due singole, non la combo del book)
H = {r["key"]: r for r in A if r["k"] == "hc"}; W = {r["key"]: r for r in A if r["k"] == "ac"}
C = [(H[k], W[k]) for k in H if k in W and H[k]["mu"] - H[k]["L"] >= 1.5 and W[k]["mu"] - W[k]["L"] >= 1.5]
note("Distanza · corner casa + ospite entrambi molto sopra la linea", f"partite {len(C)} · entrambi Over riusciti {100 * np.mean([h['over'] * w['over'] for h, w in C]):.0f}%" if C else "nessuna partita")
# quanto è lontana la linea del book dal reale, contro l'atteso di Prevista (errore medio assoluto)
for name, f in GR[:2]:
    R = [r for r in A if f(r)]
    if R: note(f"Distanza · {name} · precisione", f"errore medio assoluto: linea del book {np.mean([abs(r['real'] - r['L']) for r in R]):.2f} · atteso di Prevista {np.mean([abs(r['real'] - r['mu']) for r in R]):.2f} ({len(R)})")
