/* Audit completo di calibrazione (9/11/2026, richiesta di Denny). Per ogni partita giocata dal 1/7/2023 le probabilità dell'app con i soli
   dati dei giorni precedenti (S.cutoff), su tutti i mercati a 90' che l'app calcola, con l'esito reale; più i valori attesi per squadra
   (per il 1° tempo, calcolato in tools/calib_full.py con le statistiche per tempo). Nessuna richiesta API.
   Uso: node tools/calib_full.js DIR SHARD NSHARD → DIR/calib_full_SHARD.json
   Righe E: [campionato, data, mercato, p, esito 0/1, scarto linea − atteso (Over/Under) o null]
   Righe X: [campionato, data, casa, ospite, {stat: [atteso casa, atteso ospite]}, risultato 1° tempo gol [casa, ospite] o null] */
const fs = require("fs"), vm = require("vm"), path = require("path");
const DIR = process.argv[2] || ".", SH = +(process.argv[3] || 0), NSH = +(process.argv[4] || 1), PUB = path.join(DIR, "pub");
const html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API={S,MODES,parseCSV,addParsed,resetState,withLeague,model,modelShots,modelGoals,headToHeadProb,offModel,attachOffs,extraFor,pmfTotal,pOver};", ctx);
const A = ctx.API;
const rd = f => { try { return fs.readFileSync(path.join(PUB, f), "utf8"); } catch (e) { return null; } };
for (const [v, f] of [["EXTRA", "extra.json"], ["TAREA", "tiri_area.json"], ["OFFS", "fuorigioco.json"]]) { const t = rd(f); if (t) vm.runInContext(`${v} = ${t}; clearCache();`, ctx); }
A.resetState();
for (const bf of ["bundle_storico.json", "bundle.json"]) { const t = rd(bf); if (t) for (const f of JSON.parse(t).files) A.addParsed(A.parseCSV(f.text)); }
A.attachOffs();
const RT = vm.runInContext("OFF_R_TEAM", ctx), RTOT = vm.runInContext("OFF_R_TOT", ctx), EX = vm.runInContext("EXTRA", ctx);
const al = EX && EX.alpha, RK = al > 2e-4 ? 1 / al : Infinity;
const ms = [...A.S.matches.values()].filter(m => m.hg != null && isoD(m.date) >= "2023-07-01" && !/^(UCL|UEL|NAZ)$/.test(m.div)).sort((a, b) => a.date - b.date);
function isoD(d) { return d.toISOString().slice(0, 10); }
const E = [], X = [];
let i = -1, t0 = Date.now();
for (const m of ms) {
  i++; if (i % NSH !== SH) continue;
  const c0 = A.S.cutoff; A.S.cutoff = m.date; const d = isoD(m.date), lg = m.div;
  const add = (mk, p, y, off = null) => { if (p != null && isFinite(p) && p > 0 && p < 1 && y != null) E.push([lg, d, mk, Math.round(p * 1e4) / 1e4, y ? 1 : 0, off == null ? null : Math.round(off * 100) / 100]); };
  const xs = {};
  try {
    A.withLeague(lg, () => {
      A.S.season = m.season;
      const G = A.modelGoals(m.home, m.away, A.MODES.dyn);
      if (G) {
        const r = m.hg > m.ag ? 0 : m.hg === m.ag ? 1 : 2;
        add("Gol 1X2 · 1", G.p1, r === 0); add("Gol 1X2 · X", G.px, r === 1); add("Gol 1X2 · 2", G.p2, r === 2);
        add("Gol DC · 1X", G.p1 + G.px, r !== 2); add("Gol DC · X2", G.px + G.p2, r !== 0); add("Gol DC · 12", G.p1 + G.p2, r !== 1);
        [1.5, 2.5, 3.5].forEach((L, j) => add("Gol Over " + L, G.over[j], m.hg + m.ag > L, L - G.tot));
        add("Gol Gol/NoGol · Gol", G.btts, m.hg > 0 && m.ag > 0);
        xs.g = [G.lh, G.la];
      }
      const pO = (mu, r, L) => A.pOver(A.pmfTotal(mu, r, Math.ceil(L) + 30), L);
      const stat = (k, R, xh, xa, rTot, rTeam, cop, indep) => {
        if (!R || !isFinite(R.lh) || !isFinite(R.la) || !(R.lh > 0) || !(R.la > 0)) return;
        xs[k] = [R.lh, R.la];
        if (xh == null || xa == null) return;
        const P = indep ? A.headToHeadProb(R.lh, R.la, Infinity, indep) : A.headToHeadProb(R.lh, R.la, rTot, rTeam, cop);
        const r = xh > xa ? 0 : xh === xa ? 1 : 2;
        add(k + " 1X2 · 1", P.home, r === 0); add(k + " 1X2 · X", P.draw, r === 1); add(k + " 1X2 · 2", P.away, r === 2);
        const tot = R.lh + R.la;
        for (let o = -3.5; o <= 3.5; o += 1) { const L = Math.round(tot) + o; if (L > 0) add(k + " totale Over", pO(tot, rTot, L), xh + xa > L, L - tot); }
        for (const [mu, real] of [[R.lh, xh], [R.la, xa]]) for (let o = -2.5; o <= 2.5; o += 1) { const L = Math.round(mu) + o; if (L > 0) add(k + " squadra Over", pO(mu, rTeam, L), real > L, L - mu); }
      };
      const rT = R => R ? (R.rTeam != null ? R.rTeam : R.r) : null;
      const M = A.model(m.home, m.away, A.MODES.dyn, "c"); if (M) stat("Corner", M, m.hc, m.ac, M.r, rT(M), M.cop);
      const TS = A.modelShots(m.home, m.away, A.MODES.dyn);
      if (TS && TS.MS) stat("Tiri", TS.MS, m.hs, m.as, TS.MS.r, rT(TS.MS), TS.MS.cop);
      if (TS && TS.MD) stat("Tiri in porta", TS.MD, m.hst, m.ast, TS.MD.r, rT(TS.MD), TS.MD.cop);
      const MF = A.model(m.home, m.away, A.MODES.dyn, "f"); if (MF) stat("Falli", MF, m.hf, m.af, MF.r, rT(MF), MF.cop);
      const O = A.offModel(m.home, m.away); if (O && !O.nd) stat("Fuorigioco", O, m.ho, m.ao, RTOT, RT, null, RT);
      const x = A.extraFor(m.home, m.away);
      if (x && x[6] > 0 && x[7] > 0) stat("Cartellini", { lh: x[6], la: x[7] }, m.hk, m.ak, RK, RK, null, RK);
    });
  } catch (e) { } finally { A.S.cutoff = c0; }
  if (Object.keys(xs).length) X.push([lg, d, m.home, m.away, Object.fromEntries(Object.entries(xs).map(([k, v]) => [k, v.map(z => Math.round(z * 1000) / 1000)])), m.hht != null && m.aht != null ? [m.hht, m.aht] : null]);
  if (i % 4000 === SH) console.log("partite", i, "di", ms.length, "eventi", E.length, Math.round((Date.now() - t0) / 1000) + "s");
}
fs.writeFileSync(path.join(DIR, `calib_full_${SH}.json`), JSON.stringify({ E, X }));
console.log("fatto · shard", SH, "eventi", E.length, "partite", X.length);
