"""Diagnosi della copertura delle quote 1xBet (27/10/2026). Legge l'archivio privato (data/odds_hist.json, data/apif.json) nel runner e
stampa SOLO presenza e orari dei mercati, mai le quote.
  DIAG_DATE = giorni da esaminare (es. "2026-10-25,2026-10-26")   DIAG_MATCH = testo da cercare nelle partite (es. "Paris SG")
Per ogni partita: abbinata o no all'archivio, prima e ultima volta vista, mercati 1xBet delle statistiche presenti e quando sono comparsi
rispetto al calcio d'inizio. Riepilogo per campionato: quante partite avevano il 1X2 falli/tiri/tiri in porta/corner/gialli."""
import json, os, sys, datetime, collections, traceback
sys.excepthook = lambda t, v, tb: print("::error title=Diagnosi quote::" + " | ".join(traceback.format_exception(t, v, tb)).replace("\n", " ")[-1500:])
DATES = [d.strip() for d in os.environ.get("DIAG_DATE", "").split(",") if d.strip()]
PAT = [p.strip().lower() for p in os.environ.get("DIAG_MATCH", "").split(",") if p.strip()]
OH = json.load(open("data/odds_hist.json")) if os.path.exists("data/odds_hist.json") else {}
AP = json.load(open("data/apif.json")) if os.path.exists("data/apif.json") else {}
MK = {"x.c1x2": "corner", "x.s1x2": "tiri", "x.st1x2": "tiri in porta", "x.f1x2": "falli", "x.y1x2": "gialli", "x.off.offsides_1x2": "fuorigioco"}
note = lambda t, m: print(f"::notice title={t}::" + m.replace("%", "%25").replace("\n", " "))
# calcio d'inizio dall'archivio partite API-Football (ora UTC) per chiave approssimata campionato|data
KO = {}
for fid, v in (AP.get("partite") or {}).items():
    try: KO.setdefault((v[1], v[0][:10]), []).append((v[0], v[2], v[3], v[9]))
    except Exception: pass
def ko_of(lg, d, h, a):
    for dd in (d, (datetime.date.fromisoformat(d) - datetime.timedelta(days=1)).isoformat(), (datetime.date.fromisoformat(d) + datetime.timedelta(days=1)).isoformat()):
        for t, x, y, st in KO.get((lg, dd), []):
            if (h.lower()[:5] in x.lower() or x.lower()[:5] in h.lower()) and (a.lower()[:5] in y.lower() or y.lower()[:5] in a.lower()): return t, st
    return None, None
lines = []; cov = collections.defaultdict(collections.Counter); ntot = collections.Counter()
for k, x in sorted(OH.items()):
    lg, d, h, a = k.split("|")
    if DATES and d not in DATES: continue
    q = {**(x.get("prima") or {}).get("q", {}), **(x.get("ultima") or {}).get("q", {})}
    ks = {qk.split(":")[0] for qk in q}
    ntot[lg] += 1
    for m in MK:
        if m in ks: cov[lg][m] += 1
    if PAT and not any(p in k.lower() for p in PAT): continue
    t, st = ko_of(lg, d, h, a)
    ore = (x.get("prima") or {}).get("ore", {})
    def when(m):
        if m not in ks: return "assente"
        first = next((ore[qk] for qk in ore if qk.startswith(m + ":")), (x.get("prima") or {}).get("ora"))
        if t and first:
            try:
                ko = datetime.datetime.fromisoformat(t + ":00+00:00").astimezone(datetime.timezone(datetime.timedelta(hours=1)))   # ora italiana (solare)
                fm = datetime.datetime.strptime(first, "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone(datetime.timedelta(hours=1)))
                return f"dalle {first[11:]} ({(ko - fm).total_seconds() / 3600:+.1f} h prima del fischio)"
            except Exception: pass
        return f"dalle {first[11:] if first else '?'}"
    lines.append(f"{k} · fischio {t or '?'} UTC ({st or '?'}) · vista {(x.get('prima') or {}).get('ora', '?')} → {(x.get('ultima') or {}).get('ora', '?')} · "
                 f"giri con quote {len(x.get('serie') or [])} · 1X2/OU gol {'sì' if '1x2' in ks else 'NO'} · " + " · ".join(f"{MK[m]} {when(m)}" for m in MK))
if PAT:
    found = bool(lines)
    note("Diagnosi quote · partite cercate", (" ‖ ".join(lines[:12])) if found else f"nessuna partita con {PAT} nell'archivio quote dei giorni {DATES or 'tutti'}")
    # partite cercate presenti nel calendario API-Football ma assenti dall'archivio quote
    miss = []
    for (lg, d), L in KO.items():
        if DATES and d not in DATES: continue
        for t, x, y, st in L:
            if any(p in f"{x} {y}".lower() for p in PAT): miss.append(f"{lg} {d} {x}–{y} ({t} UTC, {st})")
    note("Diagnosi quote · calendario API-Football", " ‖ ".join(miss[:12]) or "nessuna")
rows = [f"{lg}: {ntot[lg]} partite · " + ", ".join(f"{MK[m]} {cov[lg][m]}" for m in MK if cov[lg][m]) for lg in sorted(ntot)]
note("Diagnosi quote · copertura per campionato", f"giorni {DATES or 'tutti'} ‖ " + " ‖ ".join(rows))
# per giorno: partite con quote e quante avevano i mercati delle statistiche (tutti i campionati insieme), per vedere quando cambia qualcosa
byd = collections.defaultdict(collections.Counter)
for k, x in OH.items():
    lg, d = k.split("|")[:2]
    if DATES and d not in DATES: continue
    q = {**(x.get("prima") or {}).get("q", {}), **(x.get("ultima") or {}).get("q", {})}; ks = {qk.split(":")[0] for qk in q}
    byd[d]["partite"] += 1
    for m in MK:
        if m in ks: byd[d][MK[m]] += 1
    # nomi dei mercati 1xBet "grezzi" archiviati (x.h1., x.off.): servono a capire se API-Football ha cambiato nome a un mercato
    for qk in ks:
        if qk.startswith("x.") and qk not in MK and not qk.startswith("x.h1."): byd[d]["altri:" + qk] += 1
note("Diagnosi quote · per giorno", " ‖ ".join(f"{d}: " + ", ".join(f"{k} {v}" for k, v in c.most_common() if not k.startswith("altri:")) for d, c in sorted(byd.items())))
oth = collections.Counter()
for d, c in byd.items():
    for k, v in c.items():
        if k.startswith("altri:"): oth[k[6:]] += v
note("Diagnosi quote · altri mercati 1xBet archiviati", ", ".join(f"{k} {v}" for k, v in oth.most_common(40)))
