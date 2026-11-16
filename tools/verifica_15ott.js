/* Verifica sul campo delle modifiche del 15/10/2026 (controllo programmato chiesto da Denny il 17/10). Partite giocate dal 15/10 a oggi,
   previsioni con i soli dati dei giorni precedenti (S.cutoff), app così com'è. Due passate: con il rating dei tiri non in porta (CNS_B) e senza.
   Uscita verifica_15ott.json: righe [campionato, data, casa, ospite, {corner: [lh, la, lh0, la0, r, rTeam], tiri: [lh, la, r, rTeam], tip: [lh, la, r, rTeam],
   reali: [hc, ac, hs, as, hst, ast]}]. Nessuna richiesta API. Uso: node tools/verifica_15ott.js DIR [DA] */
const fs = require("fs"), vm = require("vm"), path = require("path");
const DIR = process.argv[2] || ".", DA = process.argv[3] || "2026-10-15", PUB = path.join(DIR, "pub");
let html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
html = html.replace("const CNS_B = 0.166", "var CNS_B = 0.166");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API={S,MODES,parseCSV,addParsed,resetState,withLeague,model,modelShots,attachOffs};", ctx);
const A = ctx.API;
const rd = f => { try { return fs.readFileSync(path.join(PUB, f), "utf8"); } catch (e) { return null; } };
for (const [v, f] of [["EXTRA", "extra.json"], ["TAREA", "tiri_area.json"], ["OFFS", "fuorigioco.json"]]) { const t = rd(f); if (t) vm.runInContext(`${v} = ${t}; clearCache();`, ctx); }
A.resetState();
for (const bf of ["bundle_storico.json", "bundle.json"]) { const t = rd(bf); if (t) for (const f of JSON.parse(t).files) A.addParsed(A.parseCSV(f.text)); }
A.attachOffs();
const iso = d => d.toISOString().slice(0, 10);
const ms = [...A.S.matches.values()].filter(m => m.hg != null && iso(m.date) >= DA && !/^(UCL|UEL|UECL|NAZ)$/.test(m.div) && m.hc != null && m.ac != null).sort((a, b) => a.date - b.date);
const out = new Map();
for (const pass of [1, 0]) {
  vm.runInContext(`CNS_B = ${pass ? 0.166 : 0}; clearCache();`, ctx);
  for (const m of ms) {
    const key = `${m.div}|${iso(m.date)}|${m.home}|${m.away}`, c0 = A.S.cutoff; A.S.cutoff = m.date;
    try {
      A.withLeague(m.div, () => {
        A.S.season = m.season;
        const C = A.model(m.home, m.away, A.MODES.dyn, "c"); if (!C || !isFinite(C.lh)) return;
        let o = out.get(key);
        if (pass) {
          o = { corner: [C.lh, C.la, null, null, C.r, C.rTeam], reali: [m.hc, m.ac, m.hs, m.as, m.hst, m.ast] };
          const T = A.modelShots(m.home, m.away, A.MODES.dyn);
          if (T && T.MS && isFinite(T.MS.lh)) o.tiri = [T.MS.lh, T.MS.la, T.MS.r, T.MS.rTeam];
          if (T && T.MD && isFinite(T.MD.lh)) o.tip = [T.MD.lh, T.MD.la, T.MD.r, T.MD.rTeam];
          out.set(key, o);
        } else if (o) { o.corner[2] = C.lh; o.corner[3] = C.la; }
      });
    } catch (e) { } finally { A.S.cutoff = c0; }
  }
}
fs.writeFileSync(path.join(DIR, "verifica_15ott.json"), JSON.stringify([...out].map(([k, v]) => [...k.split("|"), v])));
console.log("partite", ms.length, "con previsione", out.size);
