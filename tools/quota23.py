"""Quota 2 / Quota 3 · studio walk-forward sull'archivio privato delle quote 1xBet (25/10/2026). Stampa SOLO numeri aggregati.

Input: q23_candidati.json (tools/quota23.js): per ogni esito quotato da 1xBet in una partita già giocata, probabilità di Prevista con i
soli dati precedenti, quota "prima" (prima vista) e "ultima" (ultima prima del fischio), esito reale.

Per ogni giorno e per ogni metodo si sceglie AL MASSIMO una proposta per obiettivo:
  Quota 2 = quota 1xBet totale tra 1,85 e 2,20 · Quota 3 = tra 2,75 e 3,35
  struttura: singola, doppia, tripla (partite diverse; variante "campionati diversi")
  mercati: tutti · solo gol (1X2, Over/Under, Gol/No gol) · solo statistiche (1X2 corner, tiri, tiri in porta, falli, gialli, fuorigioco, cartellini)
  ordinamento: P (probabilità congiunta massima) · EV (valore atteso massimo P·Q−1) · P70 (solo esiti al 70% o più, poi P massima)
  astensione: "sempre" (si propone se c'è una combinazione nella fascia) · "EV≥0" (solo se il valore atteso del modello non è negativo)
Probabilità dichiarata: grezza (prodotto delle probabilità) e calibrata in walk-forward (fattore reale/dichiarata stimato sulle sole
giornate precedenti, ristretto verso 1), per misurare la distorsione da selezione del massimo.
Metriche: giorni con proposta, quota media, probabilità dichiarata media (grezza e calibrata), % prese con intervallo al 95%, ROI a
puntata fissa, log-loss, calibrazione per fasce, prima metà contro seconda metà del periodo.
Regola di decisione fissata il 25/10/2026 (prima di vedere i risultati): un metodo si può scegliere solo con almeno 100 giorni di
archivio; scelta sui primi due terzi dei giorni, verifica sull'ultimo terzo; deve avere probabilità calibrata entro ±5 punti dalla
frequenza reale nella verifica e ROI non peggiore di −margine medio di 1xBet. Prima di allora il rapporto dice solo "campione insufficiente"."""
import json, math, itertools, collections, statistics, os
C = json.load(open("q23_candidati.json"))
GOL = {"1X2 gol", "Over/Under 1.5", "Over/Under 2.5", "Over/Under 3.5", "Gol/No gol"}
TGT = {"Quota 2": (1.85, 2.20), "Quota 3": (2.75, 3.35)}
MIN_DAYS = 100
byday = collections.defaultdict(list)
for c in C: byday[c["d"]].append(c)
days = sorted(byday)
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))
note("Quota 2/3 · archivio", f"giorni con partite giocate e quote {len(days)} (dal {days[0] if days else '-'} al {days[-1] if days else '-'}), esiti quotati {len(C)}, "
     f"regola: si sceglie un metodo solo con almeno {MIN_DAYS} giorni ({'RAGGIUNTI' if len(days) >= MIN_DAYS else 'non ancora: campione insufficiente, i numeri sotto sono solo indicativi'})")

def best(cands, n, lo, hi, order, qk, diff_lg):
    pool = [c for c in cands if c.get(qk) and c[qk] <= hi and (order != "P70" or c["p"] >= 0.70)]
    if not pool: return None
    if order == "EV": pool.sort(key=lambda c: -(c["p"] * c[qk] - 1))
    else: pool.sort(key=lambda c: -c["p"])
    pool = pool[: {1: 400, 2: 60, 3: 28}[n]]
    top = None
    for comb in itertools.combinations(pool, n):
        if len({c["key"] for c in comb}) < n or (diff_lg and len({c["lg"] for c in comb}) < n): continue
        Q = math.prod(c[qk] for c in comb)
        if not (lo <= Q <= hi): continue
        P = math.prod(c["p"] for c in comb); ev = P * Q - 1
        sc = ev if order == "EV" else P
        if top is None or sc > top[0]: top = (sc, P, Q, int(all(c["y"] for c in comb)), ev)
    return top

def run(qk, tgt, n, mset, order, abst, diff_lg=False):
    lo, hi = TGT[tgt]; R = []
    for d in days:
        cands = [c for c in byday[d] if (mset == "tutti" or (mset == "gol") == (c["mk"] in GOL))]
        b = best(cands, n, lo, hi, order, qk, diff_lg)
        if b is None or (abst == "EV≥0" and b[4] < 0): R.append(None); continue
        R.append(dict(d=d, P=b[1], Q=b[2], y=b[3]))
    # calibrazione walk-forward (sole giornate precedenti)
    hy = hp = 0.0
    for r in R:
        if r is None: continue
        k = (hy + 5) / (hp + 5); r["Pc"] = min(0.99, r["P"] * k); hy += r["y"]; hp += r["P"]
    return R

def stats(R):
    X = [r for r in R if r]
    if not X: return None
    n = len(X); h = sum(r["y"] for r in X) / n
    ll = -statistics.mean(math.log(max(1e-6, r["Pc"] if r["y"] else 1 - r["Pc"])) for r in X)
    roi = statistics.mean(r["y"] * r["Q"] - 1 for r in X)
    half = len(R) // 2; A = [r for r in R[:half] if r]; B = [r for r in R[half:] if r]
    f = lambda L: f"{sum(r['y'] for r in L)}/{len(L)}" if L else "0/0"
    return dict(n=n, q=statistics.mean(r["Q"] for r in X), p=statistics.mean(r["P"] for r in X), pc=statistics.mean(r["Pc"] for r in X), h=h,
                ci=1.96 * math.sqrt(h * (1 - h) / n), roi=roi, ll=ll, a=f(A), b=f(B))

for qk, qlab in (("q1", "quota ultima prima del fischio"), ("q0", "quota prima vista")):
    for tgt in TGT:
        lines = []
        for n in (1, 2, 3):
            for mset in ("tutti", "gol", "statistiche"):
                for order in ("P", "EV", "P70"):
                    for abst in ("sempre", "EV≥0"):
                        s = stats(run(qk, tgt, n, mset, order, abst))
                        if not s: continue
                        lines.append(f"{['', 'singola', 'doppia', 'tripla'][n]}/{mset}/{order}/{abst}: {s['n']} giorni · quota {s['q']:.2f} · dichiarata {s['p']*100:.0f}% (calibrata {s['pc']*100:.0f}%) · presa {s['h']*100:.0f}% ±{s['ci']*100:.0f} · ROI {s['roi']*100:+.0f}% · log-loss {s['ll']:.3f} · metà1 {s['a']} metà2 {s['b']}")
            if n > 1:   # variante: campionati diversi
                s = stats(run(qk, tgt, n, "tutti", "P", "sempre", diff_lg=True))
                if s: lines.append(f"{['', '', 'doppia', 'tripla'][n]}/tutti/P/sempre/CAMPIONATI DIVERSI: {s['n']} giorni · quota {s['q']:.2f} · dichiarata {s['p']*100:.0f}% · presa {s['h']*100:.0f}% ±{s['ci']*100:.0f} · ROI {s['roi']*100:+.0f}%")
        note(f"{tgt} · {qlab}", " ‖ ".join(lines) if lines else "nessuna proposta possibile")
