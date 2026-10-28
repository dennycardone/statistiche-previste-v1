/* Prevista 2.0 · baseline per i test: per ogni partita giocata (dal 2023) le previsioni dell'app con i soli dati dei giorni precedenti
   (S.cutoff): valori attesi casa/ospite e parametri delle distribuzioni di corner, tiri, tiri in porta, falli, fuorigioco, gol.
   Uso: node base.js LEGHE STAGIONE_DA  → $P2_OUT/<lg>.json (default ricerca/base; riprende dai campionati mancanti).
   28/10/2026: percorsi da P2_APP (index.html), P2_DATA (dati pubblicati), P2_OUT; gira in ricerca.yml ogni settimana */
const fs = require("fs"), vm = require("vm");
const [,, lgs, fromS] = process.argv;
const path = require("path"), REPO = path.join(__dirname, "..", "..");
const html = fs.readFileSync(process.env.P2_APP || path.join(REPO, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API = { S, MODES, parseCSV, addParsed, resetState, leagueMatches, model, modelShots, modelGoals, offModel, attachOffs };", ctx);
const D = (process.env.P2_DATA || path.join(REPO, "pub")) + "/";   // dati pubblicati (bundle, extra, tiri_area, fuorigioco)
for (const [v, f] of [["EXTRA", "extra"], ["TAREA", "tiri_area"], ["OFFS", "fuorigioco"]]) vm.runInContext(`${v} = ${fs.readFileSync(D + f + ".json", "utf8")}; clearCache();`, ctx);
const A = ctx.API; A.resetState();
for (const bf of ["bundle_storico", "bundle"]) for (const f of JSON.parse(fs.readFileSync(D + bf + ".json")).files) A.addParsed(A.parseCSV(f.text));
A.attachOffs();
const RT = vm.runInContext("[OFF_R_TEAM, OFF_R_TOT]", ctx), cfg = A.MODES.dyn;
const r4 = v => v == null || !isFinite(v) ? null : Math.round(v * 1e4) / 1e4;
const pk = M => M && isFinite(M.lh) && isFinite(M.la) ? [r4(M.lh), r4(M.la), M.r === Infinity ? -1 : r4(M.r), M.rTeam == null ? null : M.rTeam === Infinity ? -1 : r4(M.rTeam), r4(M.cop || 0)] : null;
for (const code of lgs.split(",")) {
  const OUTD = process.env.P2_OUT || path.join(REPO, "ricerca", "base"); fs.mkdirSync(OUTD, { recursive: true });
  const fin = `${OUTD}/${code}.json`; if (fs.existsSync(fin)) continue;
  A.S.league = code; const out = []; const t0 = Date.now();
  const ms = A.leagueMatches().filter(m => m.season >= +fromS).sort((a, b) => a.date - b.date);
  for (const m of ms) {
    A.S.season = m.season; A.S.cutoff = m.date;
    const row = { d: m.date.toISOString().slice(0, 10), se: m.season, h: m.home, a: m.away, y: { g: [m.hg, m.ag], c: [m.hc, m.ac], s: [m.hs, m.as], st: [m.hst, m.ast], f: [m.hf, m.af], o: [m.ho, m.ao], k: [m.hk, m.ak] } };
    try { row.c = pk(A.model(m.home, m.away, cfg, "c")); } catch (e) {}
    try { row.f = pk(A.model(m.home, m.away, cfg, "f")); } catch (e) {}
    try { const T = A.modelShots(m.home, m.away, cfg); if (T) { row.s = pk(T.MS); row.st = pk(T.MD); } } catch (e) {}
    try { const G = A.modelGoals(m.home, m.away, cfg); if (G) row.g = [r4(G.lh), r4(G.la), r4(G.rho || 0)]; } catch (e) {}
    try { const O = A.offModel(m.home, m.away); if (O && !O.nd) row.o = [r4(O.lh), r4(O.la), -1, RT[0], 0]; } catch (e) {}
    out.push(row);
  }
  fs.writeFileSync(fin, JSON.stringify(out)); console.log("fatto", code, out.length, Math.round((Date.now() - t0) / 1000) + "s");
}
