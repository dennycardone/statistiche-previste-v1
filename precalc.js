/* Previsioni della home calcolate su GitHub (Actions), dopo update_data.py.
   Usa lo stesso modello dell'app (la parte di index.html sopra "FINE MODELLO") e gli stessi dati di data/.
   Scrive data/precalc.json: per ogni partita da 11 giorni fa a 15 giorni avanti e per ogni metodo,
   Over 2,5 %, Gol %, pallini 3/3 e pronostici presi; per le partite da giocare anche tutti gli Over, corner/falli/tiri e il Confidence Score. L'app lo usa solo se è stato fatto con i suoi stessi dati. */
const fs = require("fs"), path = require("path"), vm = require("vm");
const DIR = __dirname, DATA = path.join(DIR, "data");
const html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] },
  localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API = { S, MODES, parseCSV, addParsed, resetState, allEntries, rowCompute, isoD, addDays, withLeague, confMatch, confPack, CONF_COEF };", ctx);
const A = ctx.API;
// impostazioni predefinite delle segnalazioni, lette dalla pagina (mercati accesi e probabilità minima)
const markets = [...html.matchAll(/class="chip sstat" data-k="([a-z0-9]+)" aria-pressed="true"/g)].map(m => m[1]);
const minP = +((html.match(/id="sigMin"[^>]*value="(\d+)"/) || [])[1] || 55) / 100;
const man = JSON.parse(fs.readFileSync(path.join(DATA, "manifest.json"), "utf8"));
A.resetState();
for (const f of man.files || []) { const p = path.join(DATA, f); if (fs.existsSync(p)) A.addParsed(A.parseCSV(fs.readFileSync(p, "utf8"))); }
A.S.meta = { fetched: man.updated };
const t0 = process.env.PRECALC_DAY || A.isoD(new Date());
const all = A.allEntries(A.addDays(t0, 1)).concat(A.allEntries(A.addDays(t0, -1)));   // finestra un po' più larga (fusi orari)
const seen = new Set(), entries = all.filter(e => !seen.has(e.id) && seen.add(e.id));
const rows = {}, r4 = x => x == null ? null : Math.round(x * 10000) / 10000, t = Date.now();
for (const mode of ["dyn", "classic"]) {   // i due metodi dell'app
  const cfg = A.MODES[mode];
  for (const e of entries) {
    try {
      const R = A.rowCompute(e, cfg, { markets, minP });
      const row = [R.G ? r4(R.G.over[1]) : null, R.G ? r4(R.G.btts) : null, R.sig.map(x => [x.mk, x.fav, r4(x.p)]), R.done ? R.done.length : null, R.done ? R.hit : null];
      row.push(R.G ? R.G.over.map(r4) : null);   // tutti gli Over (lista partite: O1,5 · O2,5 · O3,5)
      if (!e.m) {   // partite da giocare: anche corner/falli/tiri (Generali) e Confidence
        const st = {}; for (const [k, v] of Object.entries(R.stats || {})) st[k] = v.map(r4); row.push(st);
        row.push(R.G ? [r4(R.G.lh), r4(R.G.la)] : null);   // gol attesi casa/ospite (segnalazioni)
        // Confidence Score di tutte le previsioni della partita (sezione Selezione)
        if (Object.keys(A.CONF_COEF).length) {
          const fx = A.S.fixtures.find(x => x.div === e.lg.code && x.home === e.home && x.away === e.away && A.isoD(x.date) === e.d);
          row.push(A.withLeague(e.lg.code, () => { A.S.cutoff = null; return A.confMatch(e.home, e.away, e.date, fx && fx.odds || null, mode).map(A.confPack); }));
        }
      }
      rows[e.id + "|" + mode] = row;
    } catch (err) { console.log("errore", e.id, mode, err.message); }
  }
  console.log(mode, "fatto", Math.round((Date.now() - t) / 1000), "s");
}
fs.writeFileSync(path.join(DATA, "precalc.json"), JSON.stringify({ v: 1, updated: man.updated, st: { markets, minP }, rows }));
console.log("precalc:", entries.length, "partite ×2 metodi,", Math.round((Date.now() - t) / 1000), "s");
