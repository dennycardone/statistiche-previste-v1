"""Quali campionati hanno i mercati di nicchia su 1xBet (archivio quote privato data/odds_hist.json).
Gira solo in GitHub Actions; stampa solo conteggi aggregati come annotazioni (nessuna quota, nessuna richiesta API)."""
# Rilanciato il 19/10/2026 per il promemoria del lunedì (1X2 partita intera e 1° tempo, fuorigioco).
import json, collections, sys
OH = json.load(open("data/odds_hist.json"))
NAMES = {"c1x2": "Corner 1X2", "cdc": "Corner doppia chance", "s1x2": "Tiri 1X2", "st1x2": "Tiri in porta 1X2", "f1x2": "Falli 1X2",
         "fdc": "Falli doppia chance", "y1x2": "Gialli 1X2", "ydc": "Gialli doppia chance", "cou": "Corner O/U", "hcou": "Corner casa O/U",
         "acou": "Corner ospite O/U", "sou": "Tiri O/U", "sot": "Tiri in porta O/U", "fou": "Falli O/U", "kou": "Cartellini O/U", "cah": "Corner handicap", "kah": "Cartellini handicap"}
tot = collections.Counter(); has = collections.defaultdict(collections.Counter); since = None
for k, v in OH.items():
    lg, d = k.split("|")[:2]
    keys = set()
    for part in ("prima", "ultima"):
        for q in (v.get(part) or {}).get("q", {}):
            if q.startswith("x."): keys.add(q[2:].split(":")[0])
    if not keys: continue
    tot[lg] += 1; since = min(since or d, d)
    for m in keys: has[m][lg] += 1
lines = []
for m, nm in NAMES.items():
    c = has.get(m, {})
    lst = sorted(((lg, n, tot[lg]) for lg, n in c.items()), key=lambda x: -x[1] / x[2])
    good = [f"{lg} {round(100*n/t)}%" for lg, n, t in lst if n / t >= 0.5]
    weak = [f"{lg} {round(100*n/t)}%" for lg, n, t in lst if n / t < 0.5]
    lines.append(f"{nm}: {len(good)} campionati ≥50% → " + (", ".join(good) or "nessuno") + (" | sotto 50%: " + ", ".join(weak) if weak else ""))
# mercati del primo tempo (x.h1.*) e dei fuorigioco (x.off.*, dal 17/10/2026): nomi come arrivano da API-Football
first = {}; bydate = []
for k, v in OH.items():
    lg, d = k.split("|")[:2]; ks = set()
    for part in ("prima", "ultima"):
        for q in (v.get(part) or {}).get("q", {}):
            if q.startswith("x."): ks.add(q[2:].split(":")[0])
    if not ks: continue
    bydate.append((lg, d, ks))
    for m in ks:
        if m not in first or d < first[m]: first[m] = d
def tot_from(d0): return collections.Counter(lg for lg, d, ks in bydate if d >= d0)
def has_from(m, d0): return collections.Counter(lg for lg, d, ks in bydate if d >= d0 and m in ks)
import datetime as _dt
_oggi = _dt.date.today().isoformat(); _ieri = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
for _g in (_ieri, _oggi):
    _t = collections.Counter(lg for lg, d, ks in bydate if d == _g)
    _o = collections.defaultdict(set)
    for lg, d, ks in bydate:
        if d == _g:
            for m in ks:
                if m.startswith("off."): _o[m[4:]].add(lg)
    _w = collections.Counter(lg for lg, d, ks in bydate if d == _g and any(m.startswith("off.") for m in ks))
    print(f"::notice title=Fuorigioco {_g}::partite con mercati fuorigioco per campionato: " + (", ".join(f"{lg} {n}/{_t[lg]}" for lg, n in _w.most_common()) or "nessuna") + " · mercati: " + (", ".join(sorted(_o)) or "nessuno"))
_lab = collections.defaultdict(collections.Counter)   # etichette dei valori dei mercati fuorigioco (solo nomi, nessuna quota)
for k, v in OH.items():
    for part in ("prima", "ultima"):
        for q in (v.get(part) or {}).get("q", {}):
            if q.startswith("x.off."): m, _, val = q[6:].partition(":"); _lab[m][val] += 1
print("::notice title=Etichette fuorigioco::" + " ‖ ".join(f"{m}: " + ", ".join(f"{x} ({n})" for x, n in c.most_common(12)) for m, c in sorted(_lab.items())))
# (GitHub mostra al massimo 10 annotazioni per passo: primo tempo e fuorigioco in due righe compatte, una voce per mercato)
for pref, title in (("h1.", "Primo tempo"), ("off.", "Fuorigioco")):
    ms = sorted(k for k in has if k.startswith(pref)); parts = []
    for m in ms:
        c = has[m]; d0 = first[m]; den = tot_from(d0)   # copertura contata solo dalle partite successive alla prima volta che il mercato è stato raccolto
        lst = sorted(((lg, c2, den[lg]) for lg, c2 in has_from(m, d0).items() if den[lg]), key=lambda x: -x[1] / x[2])
        parts.append(f"{m[len(pref):]} dal {d0} [" + " ".join(f"{lg} {n}/{t}" for lg, n, t in lst) + "]")
    print(f"::notice title={title}::" + (f"{len(ms)} mercati · " + " ‖ ".join(parts) if ms else "nessun mercato nell'archivio"))
print(f"::notice title=Base::partite con quote 1xBet dal {since}: {sum(tot.values())} in {len(tot)} campionati: " + ", ".join(f"{lg} {n}" for lg, n in tot.most_common()))
for i in range(0, len(lines), 2):
    print("::notice title=Mercati " + str(i // 2 + 1) + "::" + " ‖ ".join(lines[i:i + 2]))
