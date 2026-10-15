"""1X2 per tempo di corner, tiri e tiri in porta: quota del 1° tempo per campionato e sede (casa / ospite), dai soli dati REALI per tempo
di API-Football (ramo tempi, scaricati da halves.yml, dalla stagione 2024-25). Una partita entra solo se per quella statistica i due tempi
ci sono entrambi e la loro somma coincide con il totale della partita nell'archivio (data/apif.json); niente stime o ripartizioni.
Campionato in data/tempi.json solo con almeno 200 partite valide. Backtest (15/10/2026): valori attesi della partita (Media dinamica) ×
quota del tempo, Binomiale Negativa per squadra; scelto sul 2024-25, verificato sul 2025-26 e 2026-27 contro le frequenze di lega e le
medie per tempo delle squadre (migliore in tutti e sei i mercati)."""
import json, os, glob, datetime, sys
TEMPI = sys.argv[1] if len(sys.argv) > 1 else "tempi"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/tempi.json"
FULL = {}   # id partita API -> statistiche per squadra [tiri, tiri in porta, corner, ...]
if os.path.exists("data/apif.json"):
    for fid, v in json.load(open("data/apif.json"))["partite"].items():
        if v[7] and v[8]: FULL[fid] = (v[7], v[8])
for f in glob.glob(os.environ.get("HALF_STORICO", "")):   # solo per le prove in locale (archivio storico)
    for fid, v in json.load(open(f)).get("partite", {}).items():
        if v[6] and v[7]: FULL.setdefault(fid, (v[6], v[7]))
IDX = {"c": (0, 2), "s": (1, 0), "st": (2, 1)}   # statistica: (posizione nei dati per tempo, posizione nell'archivio)
out = {}
for fn in sorted(glob.glob(os.path.join(TEMPI, "*.json"))):
    lg = os.path.basename(fn)[:-5]
    if lg in ("UCL", "UEL", "UECL"): continue   # coppe: non nel backtest
    acc = {k: [0, 0, 0, 0, 0] for k in IDX}   # 1° tempo casa, totale casa, 1° tempo ospite, totale ospite, partite
    for fid, v in json.load(open(fn)).items():
        if not (v[3] and v[4] and v[5] and v[6]) or fid not in FULL: continue
        H, A = FULL[fid]
        for k, (i, j) in IDX.items():
            h1, a1, h2, a2 = v[3][i], v[4][i], v[5][i], v[6][i]
            fh, fa = H[j] if len(H) > j else None, A[j] if len(A) > j else None
            if None in (h1, a1, h2, a2, fh, fa) or h1 + h2 != fh or a1 + a2 != fa: continue
            x = acc[k]; x[0] += h1; x[1] += fh; x[2] += a1; x[3] += fa; x[4] += 1
    L = {k: [round(x[0] / x[1], 4), round(x[2] / x[3], 4), x[4]] for k, x in acc.items() if x[4] >= 200 and x[1] and x[3]}
    if L: out[lg] = L
json.dump({"agg": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"), "r": {"c": [8.80, 3.37], "s": [17.54, 8.79], "st": [296.8, 7.34]},
           "campionati": out}, open(OUT, "w"), separators=(",", ":"))
print("tempi.json:", len(out), "campionati", {k: {s: v[2] for s, v in L.items()} for k, L in list(out.items())[:3]})
