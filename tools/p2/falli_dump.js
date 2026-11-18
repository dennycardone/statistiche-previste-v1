/* Falli · audit (18/11/2026, Denny): per ogni partita giocata dal 2023, con i soli dati dei giorni precedenti, falli attesi dell'app
   senza arbitro (modelBase "f": FDYN) e con l'arbitro come in produzione (modelRef: fattore di extra.json con tetto +4%), r del totale e
   della squadra, e le parti del modello (falli medi di lega, rating, ultime 5, intervallo, tiri). Le formazioni ufficiali non esistono
   per le partite passate (S.cutoff). Uso: node tools/p2/falli_dump.js LEGHE → ricerca/falli/<lg>.json */
const fs = require("fs"), vm = require("vm"), path = require("path"), REPO = path.join(__dirname, "..", "..");
const html = fs.readFileSync(path.join(REPO, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API = { S, MODES, parseCSV, addParsed, resetState, modelBase, modelRef, fdynFit, foulForm, extraFor, clearCache };", ctx);
const D = path.join(REPO, "pub") + "/";
for (const [v, f] of [["EXTRA", "extra"], ["TAREA", "tiri_area"], ["OFFS", "fuorigioco"]]) vm.runInContext(`${v} = ${fs.readFileSync(D + f + ".json", "utf8")}; clearCache();`, ctx);
const A = ctx.API; A.resetState();
for (const bf of ["bundle_storico", "bundle"]) for (const f of JSON.parse(fs.readFileSync(D + bf + ".json")).files) A.addParsed(A.parseCSV(f.text));
const r4 = v => v == null || !isFinite(v) ? null : Math.round(v * 1e4) / 1e4, iso = d => new Date(d).toISOString().slice(0, 10);
const OUT = path.join(REPO, "ricerca", "falli"); fs.mkdirSync(OUT, { recursive: true });
for (const code of process.argv[2].split(",")) {
  A.S.league = code; const rows = [];
  const all = [...A.S.matches.values()].filter(m => m.div === code && m.season >= 2023 && m.hf != null && m.af != null).sort((a, b) => a.date - b.date);
  for (const m of all) {
    A.S.season = m.season; A.S.cutoff = m.date;
    try {
      const B = A.modelBase(m.home, m.away, A.MODES.dyn, "f"), R = A.modelRef(m.home, m.away, A.MODES.dyn, "f"); if (!B) continue;
      const x = A.extraFor(m.home, m.away);
      rows.push([iso(m.date), m.home, m.away, m.hf, m.af, r4(B.lh), r4(B.la), r4(R.lh), r4(R.la), B.r, B.rTeam, x ? r4(x[2]) : null, x ? x[0] : null, m.hg, m.ag]);
    } catch (e) {}
  }
  fs.writeFileSync(`${OUT}/${code}.json`, JSON.stringify(rows)); console.log(code, rows.length);
}
