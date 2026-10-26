"""Agente di ricerca · ipotesi 2: posta in gioco. Classifica di ogni campionato prima di ogni partita (solo partite precedenti della stagione,
dai file base). Per ogni squadra: partite rimaste (stima 2·(squadre−1) − giocate), "in corsa" se con i punti ancora disponibili può
raggiungere il 4° posto o può essere raggiunta dalla zona retrocessione (ultimi 3); variabili:
  xi_late    1 nelle ultime 10 giornate
  xi_nulla   1 se nelle ultime 10 giornate non è più in corsa né in alto né in basso (nulla in gioco)
  xi_gap     |differenza di posizione| tra le due squadre / squadre del campionato
Uscita feat_stakes.pkl con chiavi dell'app (campionato, data, casa, ospite)."""
import json, glob, pickle, collections
F = {}
for fn in glob.glob("/home/claude/research/p2/base/*.json"):
    lg = fn.split("/")[-1][:-5]; R = json.load(open(fn)); R.sort(key=lambda r: r["d"])
    by = collections.defaultdict(list)
    for r in R: by[r["se"]].append(r)
    for se, L in by.items():
        teams = {r["h"] for r in L} | {r["a"] for r in L}; N = len(teams); G = 2 * (N - 1)
        pts = collections.Counter(); gp = collections.Counter(); day = None; pend = []
        for r in L:
            if r["d"] != day:
                for h, a, hg, ag in pend:
                    gp[h] += 1; gp[a] += 1
                    if hg > ag: pts[h] += 3
                    elif hg == ag: pts[h] += 1; pts[a] += 1
                    else: pts[a] += 3
                pend = []; day = r["d"]
            table = sorted(teams, key=lambda t: -pts[t]); pos = {t: i + 1 for i, t in enumerate(table)}
            f = {}
            for side, t, o in (("h", r["h"], r["a"]), ("a", r["a"], r["h"])):
                rem = max(0, G - gp[t]); late = int(rem <= 10 and gp[t] >= G // 2)
                p4 = pts[table[3]] if N > 6 else pts[table[0]]; rel = pts[table[N - 3]] if N > 6 else 0
                can_top = pts[t] + 3 * rem >= p4; can_fall = rel + 3 * rem >= pts[t]
                f[side] = {"xi_late": late, "xi_nulla": int(late and not can_top and not can_fall), "xi_gap": abs(pos[t] - pos[o]) / N}
            F[(lg, r["d"], r["h"], r["a"])] = f
            if r["y"]["g"][0] is not None: pend.append((r["h"], r["a"], r["y"]["g"][0], r["y"]["g"][1]))
pickle.dump(F, open("/home/claude/research/p2/feat_stakes.pkl", "wb"))
print("partite", len(F), "· squadre-partita con nulla in gioco:", sum(1 for f in F.values() for s in "ha" if f[s]["xi_nulla"]),
      "· nelle ultime 10 giornate:", sum(1 for f in F.values() for s in "ha" if f[s]["xi_late"]))
