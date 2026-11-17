/* Gol attesi · fase 3 (17/11/2026): dati di ingresso e riferimento dell'app per la replica di M0 in Python.
   Per ogni campionato: tutte le partite caricate dall'app (bundle storico + bundle) e, per le partite dal 2023, i gol attesi dell'app con i
   soli dati dei giorni precedenti, con le parti intermedie (λ prima della qualità dei tiri, x qualità, Elo).
   Uso: node tools/p2/gol_dump.js LEGHE → ricerca/gol/<lg>.json */
const fs = require("fs"), vm = require("vm"), path = require("path"), REPO = path.join(__dirname, "..", "..");
const html = fs.readFileSync(path.join(REPO, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API = { S, MODES, parseCSV, addParsed, resetState, leagueMatches, modelGoals, goalDynParts, goalOnlyDynParts, gdynFit, eloAt, qualX, clearCache };", ctx);
const D = path.join(REPO, "pub") + "/";
for (const [v, f] of [["EXTRA", "extra"], ["TAREA", "tiri_area"], ["OFFS", "fuorigioco"]]) vm.runInContext(`${v} = ${fs.readFileSync(D + f + ".json", "utf8")}; clearCache();`, ctx);
const A = ctx.API; A.resetState();
for (const bf of ["bundle_storico", "bundle"]) for (const f of JSON.parse(fs.readFileSync(D + bf + ".json")).files) A.addParsed(A.parseCSV(f.text));
const r6 = v => v == null || !isFinite(v) ? null : Math.round(v * 1e6) / 1e6, iso = d => new Date(d).toISOString().slice(0, 10);
const OUT = path.join(REPO, "ricerca", "gol"); fs.mkdirSync(OUT, { recursive: true });
for (const code of process.argv[2].split(",")) {
  A.S.league = code;
  const all = [...A.S.matches.values()].filter(m => m.div === code).sort((a, b) => a.date - b.date);
  const fx = A.S.fixtures.filter(f => f.div === code).map(f => [iso(f.date), f.season, f.home, f.away]);
  const M = all.map(m => [iso(m.date), m.season, m.home, m.away, m.hg, m.ag, m.hst ?? null, m.ast ?? null, m.hs ?? null, m.as ?? null]);
  const ref = [];
  for (const m of all.filter(m => m.season >= 2023 && m.hg != null)) {
    A.S.season = m.season; A.S.cutoff = m.date;
    let r = { d: iso(m.date), h: m.home, a: m.away };
    try {
      const G = A.modelGoals(m.home, m.away, A.MODES.dyn); if (G) { r.lh = r6(G.lh); r.la = r6(G.la); r.p = [r6(G.p1), r6(G.px), r6(G.p2)]; }
      const P = A.goalDynParts(m.home, m.away); r.src = P ? "gdyn" : "altro";
      const Dd = +m.date, eH = A.eloAt(code, m.home, Dd), eA = A.eloAt(code, m.away, Dd); r.eh = eH ? r6(eH.elo) : null; r.ea = eA ? r6(eA.elo) : null;
      const QX = A.qualX(code, Dd, m.home, m.away); r.qx = QX ? QX.map(r6) : null;
    } catch (e) { r.err = String(e).slice(0, 80); }
    ref.push(r);
  }
  fs.writeFileSync(`${OUT}/${code}.json`, JSON.stringify({ M, fx, ref })); console.log(code, M.length, ref.length);
}
