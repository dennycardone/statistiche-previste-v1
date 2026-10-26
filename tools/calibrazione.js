/* Fase 0 · monitoraggio settimanale della calibrazione (26/10/2026). Per ogni partita giocata negli ultimi 120 giorni, le probabilità
   dell'app con i soli dati dei giorni precedenti (S.cutoff): Over 1,5 / 2,5 / 3,5, Gol/No gol (lato probabile), 1X2 gol (favorito),
   1X2 di corner, tiri, tiri in porta, falli, fuorigioco (lato favorito, quello di Segnali e Grado), con l'esito reale.
   Scrive calib_eventi.json NEL RUNNER; tools/calibrazione.py stampa le note aggregate. Nessuna richiesta API. */
const fs = require("fs"), vm = require("vm"), path = require("path");
const DIR = process.argv[2] || ".", PUB = path.join(DIR, "pub"), DAYS = +(process.argv[3] || 120);
const html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API={S,MODES,parseCSV,addParsed,resetState,withLeague,model,modelShots,modelGoals,headToHeadProb,offModel,attachOffs};", ctx);
const A = ctx.API;
const rd = f => { try { return fs.readFileSync(path.join(PUB, f), "utf8"); } catch (e) { return null; } };
for (const [v, f] of [["EXTRA", "extra.json"], ["TAREA", "tiri_area.json"], ["OFFS", "fuorigioco.json"]]) { const t = rd(f); if (t) vm.runInContext(`${v} = ${t}; clearCache();`, ctx); }
A.resetState();
for (const bf of ["bundle_storico.json", "bundle.json"]) { const t = rd(bf); if (t) for (const f of JSON.parse(t).files) A.addParsed(A.parseCSV(f.text)); }
A.attachOffs();
const RT = vm.runInContext("OFF_R_TEAM", ctx), lim = Date.now() - DAYS * 864e5, out = [];
const ms = [...A.S.matches.values()].filter(m => +m.date >= lim && m.hg != null).sort((a, b) => a.date - b.date);
for (const m of ms) {
  const c0 = A.S.cutoff; A.S.cutoff = m.date;
  const add = (mk, p, y) => { if (p != null && isFinite(p) && y != null) out.push([m.div, m.date.toISOString().slice(0, 10), mk, Math.round(p * 1e4) / 1e4, y ? 1 : 0]); };
  try {
    A.withLeague(m.div, () => {
      A.S.season = m.season;
      const G = A.modelGoals(m.home, m.away, A.MODES.dyn), T = m.hg + m.ag;
      if (G) {
        [1.5, 2.5, 3.5].forEach((L, i) => add("Over " + String(L).replace(".", ","), G.over[i], T > L));
        const gg = m.hg > 0 && m.ag > 0; add("Gol/No gol", Math.max(G.btts, 1 - G.btts), G.btts >= 0.5 ? gg : !gg);
        const one = G.p1 >= G.p2; add("1X2 gol", one ? G.p1 : G.p2, one ? m.hg > m.ag : m.ag > m.hg);
      }
      const st = (name, R, xh, xa, indep) => {
        if (!R || !isFinite(R.lh) || xh == null || xa == null) return;
        const P = indep ? A.headToHeadProb(R.lh, R.la, Infinity, indep) : A.headToHeadProb(R.lh, R.la, R.r, R.rTeam, R.cop), one = P.home >= P.away;
        add(name, one ? P.home : P.away, one ? xh > xa : xa > xh);
      };
      st("Corner 1X2", A.model(m.home, m.away, A.MODES.dyn, "c"), m.hc, m.ac);
      const TS = A.modelShots(m.home, m.away, A.MODES.dyn); if (TS) { st("Tiri 1X2", TS.MS, m.hs, m.as); st("Tiri in porta 1X2", TS.MD, m.hst, m.ast); }
      st("Falli 1X2", A.model(m.home, m.away, A.MODES.dyn, "f"), m.hf, m.af);
      const O = A.offModel(m.home, m.away); if (O && !O.nd) st("Fuorigioco 1X2", O, m.ho, m.ao, RT);
    });
  } catch (e) { } finally { A.S.cutoff = c0; }
}
fs.writeFileSync(path.join(DIR, "calib_eventi.json"), JSON.stringify(out));
console.log("partite", ms.length, "previsioni", out.length);
