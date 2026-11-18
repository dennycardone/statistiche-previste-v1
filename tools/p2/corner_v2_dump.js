/* Corner V2 in ombra · verifica app = Python (18/11/2026, Denny). Per ogni partita giocata dal 2023 (soli dati dei giorni precedenti, S.cutoff):
   corner ufficiali dell'app (cornerDynParts), medie di lega, Corner V2 (cornerV2) con i suoi otto indici; più l'elenco grezzo delle partite
   del campionato (corner, tiri, tiri in porta) per la replica indipendente in Python (corner_v2_check.py).
   Uso: node corner_v2_dump.js LEGHE STAGIONE_DA → $P2_OUT/<lg>.json (default ricerca/corner_v2) */
const fs = require("fs"), vm = require("vm"), path = require("path");
const [,, lgs, fromS] = process.argv, REPO = path.join(__dirname, "..", "..");
const html = fs.readFileSync(process.env.P2_APP || path.join(REPO, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API = { S, parseCSV, addParsed, resetState, leagueMatches, attachOffs, cornerDynParts, cornerV2: typeof cornerV2 === 'function' ? cornerV2 : null };", ctx);
const D = (process.env.P2_DATA || path.join(REPO, "pub")) + "/";
for (const [v, f] of [["EXTRA", "extra"], ["TAREA", "tiri_area"], ["OFFS", "fuorigioco"]]) try { vm.runInContext(`${v} = ${fs.readFileSync(D + f + ".json", "utf8")}; clearCache();`, ctx); } catch (e) {}
const A = ctx.API; A.resetState();
for (const bf of ["bundle_storico", "bundle"]) for (const f of JSON.parse(fs.readFileSync(D + bf + ".json")).files) A.addParsed(A.parseCSV(f.text));
A.attachOffs();
const r6 = v => v == null || !isFinite(v) ? null : Math.round(v * 1e6) / 1e6, iso = d => new Date(d).toISOString().slice(0, 10);
const OUTD = process.env.P2_OUT || path.join(REPO, "ricerca", "corner_v2"); fs.mkdirSync(OUTD, { recursive: true });
for (const code of lgs.split(",")) {
  A.S.league = code; const t0 = Date.now();
  const all = [...A.S.matches.values()].filter(m => m.div === code).sort((a, b) => a.date - b.date);
  const raw = all.map(m => [iso(m.date), m.home, m.away, m.hc ?? null, m.ac ?? null, m.hs ?? null, m.as ?? null, m.hst ?? null, m.ast ?? null]);
  const ms = A.leagueMatches().filter(m => m.season >= +fromS && m.hc != null && m.ac != null).sort((a, b) => a.date - b.date), out = [];
  for (const m of ms) {
    A.S.season = m.season; A.S.cutoff = m.date;
    let P = null, V = null; try { P = A.cornerDynParts(m.home, m.away); V = P && A.cornerV2 ? A.cornerV2(m.home, m.away, P) : null; } catch (e) {}
    out.push([iso(m.date), m.home, m.away, m.hc, m.ac, P ? r6(P.lh) : null, P ? r6(P.la) : null, P ? r6(P.muH) : null, P ? r6(P.muA) : null,
              V ? r6(V.lh) : null, V ? r6(V.la) : null, V ? (V.on ? 1 : 0) : null, V ? V.ix.map(x => [r6(x[0]), x[1]]) : null]);
  }
  A.S.cutoff = null;
  fs.writeFileSync(`${OUTD}/${code}.json`, JSON.stringify({ raw, rows: out }));
  console.log(code, out.length, "partite", Math.round((Date.now() - t0) / 1000), "s");
}
