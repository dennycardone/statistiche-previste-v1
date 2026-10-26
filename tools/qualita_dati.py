"""Fase 0 · controllo qualità dei dati che usano i modelli (26/10/2026), sui file pubblicati (bundle + fuorigioco). Solo numeri aggregati.
Per campionato e statistica (gol, tiri, tiri in porta, corner, falli, cartellini, fuorigioco), stagione in corso e precedente:
  - quota di partite giocate SENZA il dato (mancante);
  - zeri sospetti: entrambe le squadre a 0 dove è (quasi) impossibile (tiri, falli) o raro (corner) → probabile dato mancante scritto come 0;
  - valori impossibili (tiri in porta > tiri, oltre i limiti fisici) e anomali (oltre 6 deviazioni robuste dalla mediana del campionato);
  - fuorigioco: lo 0-0 vero è possibile ma raro (API-Football scrive i doppi zero come vuoti: la regola dei doppi null è in update_data.py)."""
import json, csv, io, collections, statistics, sys
P = sys.argv[1] if len(sys.argv) > 1 else "pub"
F = {"tiri": ("HS", "AS"), "tiri in porta": ("HST", "AST"), "corner": ("HC", "AC"), "falli": ("HF", "AF"), "cartellini": ("HK", "AK"), "gol": ("FTHG", "FTAG")}
CAP = {"tiri": 50, "tiri in porta": 25, "corner": 25, "falli": 40, "cartellini": 12, "gol": 12}
ZERO_BOTH_BAD = {"tiri": "impossibile", "falli": "impossibile", "corner": "raro"}
num = lambda x: int(float(x)) if x not in (None, "", "NA") else None
rows = []
for bf in ("bundle_storico.json", "bundle.json"):
    try: files = json.load(open(f"{P}/{bf}"))["files"]
    except Exception: continue
    for f in files:
        lgf = (f.get("name") or "").split(".")[0].split("_")[0]
        for r in csv.DictReader(io.StringIO(f["text"])):
            if "Div" not in r: r["Div"] = lgf; r["FTHG"], r["FTAG"] = r.get("HG"), r.get("AG")   # formato dei campionati "nuovi" di football-data
            if r.get("FTHG") in (None, ""): continue
            try: d = r["Date"].split("/"); y = int(d[2]) if len(d[2]) == 4 else 2000 + int(d[2])
            except Exception: continue
            if y < 2025: continue
            rows.append(r)
by = collections.defaultdict(list)
for r in rows: by[r["Div"]].append(r)
out, issues = [], collections.Counter()
for lg, L in sorted(by.items()):
    n = len(L); parts = []
    for name, (h, a) in F.items():
        vals = [(num(r.get(h)), num(r.get(a))) for r in L]
        miss = sum(1 for x in vals if x[0] is None or x[1] is None)
        ok = [x for x in vals if x[0] is not None and x[1] is not None]
        if not ok: parts.append(f"{name} assente"); continue
        z2 = sum(1 for x in ok if x[0] == 0 and x[1] == 0) if name in ZERO_BOTH_BAD else 0
        cap = sum(1 for x in ok if max(x) > CAP[name])
        flat = [v for x in ok for v in x]; med = statistics.median(flat); mad = statistics.median([abs(v - med) for v in flat]) or 1
        out6 = sum(1 for v in flat if abs(v - med) / (1.4826 * mad) > 6)
        if miss / n > 0.05: issues["mancanti"] += 1; parts.append(f"{name}: mancanti {miss}/{n}")
        if z2: issues["zeri doppi " + ZERO_BOTH_BAD[name]] += z2; parts.append(f"{name}: 0-0 {z2} ({ZERO_BOTH_BAD[name]})")
        if cap: issues["oltre i limiti"] += cap; parts.append(f"{name}: oltre il limite {cap}")
        if out6: issues["anomali"] += out6; parts.append(f"{name}: anomali {out6}")
    st = [(num(r.get("HS")), num(r.get("HST")), num(r.get("AS")), num(r.get("AST"))) for r in L]
    bad = sum(1 for s in st if None not in s and (s[1] > s[0] or s[3] > s[2]))
    if bad: issues["porta > tiri"] += bad; parts.append(f"tiri in porta > tiri {bad}")
    if parts: out.append(f"{lg} ({n} partite dal 2025): " + "; ".join(parts))
try:
    OFF = json.load(open(f"{P}/fuorigioco.json"))["campionati"]
    for lg, L in OFF.items():
        L = [x for x in L if x[0] >= "2025-01-01" and x[3] is not None and x[4] is not None]
        if not L: continue
        z = sum(1 for x in L if x[3] == 0 and x[4] == 0)
        if z / len(L) > 0.08: out.append(f"{lg} fuorigioco: 0-0 in {z}/{len(L)} partite (sopra l'8%: controllare la regola dei doppi null)")
except Exception as e: out.append(f"fuorigioco non letto: {e}")
print("::notice title=Qualità dati · riepilogo::" + f"{len(rows)} partite dal 2025 · " + (", ".join(f"{k} {v}" for k, v in issues.items()) or "nessun problema"))
for i in range(0, len(out), 25): print("::notice title=Qualità dati · campionati::" + " ‖ ".join(out[i:i + 25]))
