"""Fase 0 · monitoraggio settimanale della calibrazione (26/10/2026): note aggregate da calib_eventi.json (tools/calibrazione.js).
Per mercato: dichiarata media contro uscita reale e ECE (errore medio per fasce di 10 punti), ultimi 120 giorni e ultime 4 settimane.
Avvisi: combinazioni campionato × mercato con scarto oltre 2 errori standard e oltre 4 punti (con quante se ne aspetterebbero per caso)."""
import json, math, collections, datetime
E = json.load(open("calib_eventi.json"))
note = lambda t, m, k="notice": print(f"::{k} title={t}::" + m.replace("%", "%25"))
def summ(L):
    n = len(L); p = sum(x[3] for x in L) / n; y = sum(x[4] for x in L) / n
    se = math.sqrt(max(y * (1 - y), 1e-9) / n); bins = collections.defaultdict(list)
    for x in L: bins[min(9, int(x[3] * 10))].append(x)
    ece = sum(len(b) * abs(sum(v[4] for v in b) / len(b) - sum(v[3] for v in b) / len(b)) for b in bins.values()) / n
    return n, p, y, (y - p), se, ece
last4 = (datetime.date.today() - datetime.timedelta(days=28)).isoformat()
by_m = collections.defaultdict(list)
for x in E: by_m[x[2]].append(x)
lines = []
for m, L in sorted(by_m.items()):
    n, p, y, d, se, ece = summ(L); r = [x for x in L if x[1] >= last4]
    s4 = summ(r) if len(r) >= 50 else None
    lines.append(f"{m}: {n} previsioni · dichiarata {p*100:.1f}% presa {y*100:.1f}% (scarto {d*100:+.1f} ±{1.96*se*100:.1f}) · ECE {ece*100:.1f}" + (f" · ultime 4 settimane scarto {s4[3]*100:+.1f} ±{1.96*s4[4]*100:.1f}" if s4 else ""))
note("Calibrazione · per mercato (120 giorni)", " ‖ ".join(lines))
by = collections.defaultdict(list)
for x in E: by[(x[2], x[0])].append(x)
flag, tot = [], 0
for (m, lg), L in by.items():
    if len(L) < 60: continue
    tot += 1; n, p, y, d, se, ece = summ(L)
    if abs(d) > 0.04 and abs(d / se) > 2: flag.append((d, f"{m} {lg}: {n} · dichiarata {p*100:.0f}% presa {y*100:.0f}% ({d*100:+.0f} punti)"))
flag.sort()
note("Calibrazione · campionati che scivolano", f"{len(flag)} combinazioni campionato×mercato su {tot} (per caso se ne aspettano circa {round(tot*0.046)}): " + " ‖ ".join(t for _, t in flag[:40]), "warning" if len(flag) > tot * 0.08 else "notice")
