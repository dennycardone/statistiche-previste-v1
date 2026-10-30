/* Analisi IA delle partite (30/10/2026, richiesta di Denny): dati di ogni partita dei prossimi giorni da passare all'IA (tools/analisi_ia.py).
   Stesso modello dell'app (index.html fino a "FINE MODELLO") sugli stessi dati pubblicati: valori attesi di Prevista (gol, tiri, tiri in
   porta, corner, falli, cartellini), arbitro, ultime 5 partite di campionato delle due squadre e ultimi scontri diretti con i numeri reali.
   Uso: node tools/ia_contesto.js <cartella con index.html> <cartella dati pubblicati> <file di uscita>. Nessuna richiesta API. */
const fs = require("fs"), vm = require("vm"), path = require("path");
const DIR = process.argv[2] || ".", PUB = process.argv[3] || "pub", OUT = process.argv[4] || "ia_input.json";
process.on("uncaughtException", e => { console.log("::error title=Analisi IA · contesto::" + String(e && e.stack || e).replace(/\n/g, " | ").slice(0, 1500)); process.exit(0); });
const html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API={S,MODES,LEAGUES,parseCSV,addParsed,resetState,withLeague,model,modelShots,modelGoals,extraFor};", ctx);
const A = ctx.API;
const rd = f => { try { return fs.readFileSync(path.join(PUB, f), "utf8"); } catch (e) { return null; } };
for (const [v, f] of [["EXTRA", "extra.json"], ["TAREA", "tiri_area.json"], ["OFFS", "fuorigioco.json"], ["FORMAZ", "formazioni.json"]]) { const t = rd(f); if (t) vm.runInContext(`${v} = ${t}; clearCache();`, ctx); }
A.resetState();
for (const bf of ["bundle_storico.json", "bundle.json"]) { const t = rd(bf); if (t) for (const f of JSON.parse(t).files) A.addParsed(A.parseCSV(f.text)); }
const NEXT = JSON.parse(rd("prossime.json") || "[]");
const LG = new Map(A.LEAGUES.map(l => [l.code, l]));
const r1 = x => x == null || !isFinite(x) ? null : Math.round(x * 10) / 10;
const all = [...A.S.matches.values()];
const line = (m, team) => {   // una partita giocata vista da "team"
  const home = m.home === team, d = m.date.toISOString().slice(0, 10);
  const st = (h, a) => (h == null || a == null) ? null : home ? `${h}-${a}` : `${a}-${h}`;
  return { d, contro: home ? m.away : m.home, casa: home, ris: st(m.hg, m.ag), corner: st(m.hc, m.ac), tiri: st(m.hs, m.as), falli: st(m.hf, m.af), cartellini: st(m.hk, m.ak) };
};
const out = [];
for (const p of NEXT) {
  if (!LG.has(p.lg)) continue;
  const L = LG.get(p.lg), it = { fid: p.fid, lg: p.lg, campionato: `${L.country} · ${L.name}`, ko: p.ko, d: p.d, casa: p.h, ospite: p.a };
  try {
    A.withLeague(p.lg, () => {
      const c0 = A.S.cutoff; A.S.cutoff = null;
      try {
        const cfg = A.MODES.dyn; let G = null, M = null, MT = null, MF = null;
        try { G = A.modelGoals(p.h, p.a, cfg); } catch (e) {} try { M = A.model(p.h, p.a, cfg, "c"); } catch (e) {}
        try { MT = A.modelShots(p.h, p.a, cfg); } catch (e) {} try { MF = A.model(p.h, p.a, cfg, "f"); } catch (e) {}
        const x = A.extraFor(p.h, p.a);
        it.prevista = {
          gol: G ? [r1(G.lh), r1(G.la)] : null, tiri: MT && MT.MS ? [r1(MT.MS.lh), r1(MT.MS.la)] : null, tiri_in_porta: MT && MT.lh != null ? [r1(MT.lh), r1(MT.la)] : null,
          corner: M ? [r1(M.lh), r1(M.la)] : null, falli: MF ? [r1(MF.lh), r1(MF.la)] : null, cartellini: x && x[6] != null ? [r1(x[6]), r1(x[7])] : null };
        it.arbitro = x && x[0] ? x[0] : null;
      } finally { A.S.cutoff = c0; }
    });
  } catch (e) {}
  const played = all.filter(m => m.div === p.lg && m.hg != null).sort((a, b) => b.date - a.date);
  it.forma_casa = played.filter(m => m.home === p.h || m.away === p.h).slice(0, 5).map(m => line(m, p.h));
  it.forma_ospite = played.filter(m => m.home === p.a || m.away === p.a).slice(0, 5).map(m => line(m, p.a));
  it.precedenti = played.filter(m => (m.home === p.h && m.away === p.a) || (m.home === p.a && m.away === p.h)).slice(0, 5).map(m => line(m, p.h));
  out.push(it);
}
fs.writeFileSync(OUT, JSON.stringify(out));
console.log(`::notice title=Analisi IA · contesto::partite dei prossimi giorni ${NEXT.length} · con il contesto ${out.length} · con i valori di Prevista ${out.filter(o => o.prevista && o.prevista.gol).length}`);
