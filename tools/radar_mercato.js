/* Verifica del Radar Mercato (27/10/2026) sull'archivio privato delle quote 1xBet. Stampa SOLO numeri aggregati.
   Per ogni partita giocata dell'archivio: linee Over/Under di 1xBet come le mostra l'app (data/linee.json: per mercato la linea x,5 più
   equilibrata, ultima quota vista prima del fischio), previsioni di Prevista con i soli dati dei giorni precedenti (S.cutoff, stessi modelli
   dell'app), stesso calcolo di bkCalc e stessa regola del Radar: si propone il lato con valore atteso più alto se è almeno +5%
   (BK_MIN), solo tiri, tiri in porta, corner, falli e cartellini (niente gol né fuorigioco, come il Radar). Esito: Over/Under riuscito.
   Nessuna richiesta API. */
const fs = require("fs"), vm = require("vm"), path = require("path");
const DIR = process.argv[2] || ".", DATA = path.join(DIR, "data"), PUB = path.join(DIR, "pub");
process.on("uncaughtException", e => { console.log("::error title=Radar Mercato::" + String(e && e.stack || e).replace(/\n/g, " | ").slice(0, 1500)); process.exit(0); });
const html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API={S,MODES,parseCSV,addParsed,resetState,withLeague,model,modelShots,pmfTotal,pOver};", ctx);
const A = ctx.API;
const rd = (p, f) => { try { return fs.readFileSync(path.join(p, f), "utf8"); } catch (e) { return null; } };
for (const [v, f] of [["EXTRA", "extra.json"], ["TAREA", "tiri_area.json"], ["OFFS", "fuorigioco.json"]]) { const t = rd(PUB, f); if (t) vm.runInContext(`${v} = ${t}; clearCache();`, ctx); }
const EX = JSON.parse(rd(PUB, "extra.json") || "{\"partite\":{}}");
A.resetState();
for (const bf of ["bundle_storico.json", "bundle.json"]) { const t = rd(PUB, bf); if (t) for (const f of JSON.parse(t).files) A.addParsed(A.parseCSV(f.text)); }
const OH = JSON.parse(fs.readFileSync(path.join(DATA, "odds_hist.json"), "utf8"));
const LMK = { c: "x.cou", hc: "x.hcou", ac: "x.acou", k: "x.kou", hk: "x.hk", ak: "x.ak", st: "x.sot", hst: "x.hsot", ast: "x.asot", s: "x.sou", f: "x.fou", hf: "x.hfou", af: "x.afou" };
const FAM = { c: "Corner", hc: "Corner", ac: "Corner", k: "Cartellini", hk: "Cartellini", ak: "Cartellini", st: "Tiri in porta", hst: "Tiri in porta", ast: "Tiri in porta", s: "Tiri", f: "Falli", hf: "Falli", af: "Falli" };
const BK_MIN = 0.05;
function lines(q) {   // come update_data.py (linee.json)
  const out = {};
  for (const [short, mk] of Object.entries(LMK)) {
    const L = {};
    for (const [k2, v] of Object.entries(q)) {
      if (!k2.startsWith(mk + ":")) continue;
      const parts = k2.split(":")[1].split(" "); if (parts.length !== 2) continue;
      const ln = parseFloat(parts[1]); if (!isFinite(ln) || Math.abs(ln - Math.floor(ln) - 0.5) > 1e-9) continue;
      (L[ln] = L[ln] || {})[parts[0][0]] = v;
    }
    let best = null;
    for (const [ln, o] of Object.entries(L)) if (o.O && o.U && o.O[0] > 1 && o.U[0] > 1) {
      const d = Math.abs(1 / o.O[0] - 1 / o.U[0]), n = Math.min(o.O[1], o.U[1]);
      if (!best || d < best[0] - 1e-9 || (Math.abs(d - best[0]) < 1e-9 && n > best[4])) best = [d, +ln, o.O[0], o.U[0], n];
    }
    if (best) out[short] = [best[1], best[2], best[3]];
  }
  return out;
}
const rows = []; let nPl = 0, nLB = 0;
for (const [key, v] of Object.entries(OH)) {
  const m = A.S.matches.get(key); if (!m || m.hg == null) continue;
  nPl++;
  const LB = lines((v.ultima || {}).q || {}); if (!Object.keys(LB).length) continue;
  nLB++;
  const [lg, d, h, a] = key.split("|"), c0 = A.S.cutoff; A.S.cutoff = m.date;
  try {
    A.withLeague(lg, () => {
      A.S.season = m.season;
      let M = null, MT = null, MF = null; try { M = A.model(h, a, A.MODES.dyn, "c"); MT = A.modelShots(h, a, A.MODES.dyn); MF = A.model(h, a, A.MODES.dyn, "f"); } catch (e) {}
      const x = EX.partite[key], al = EX.alpha, rk = al > 2e-4 ? 1 / al : Infinity, ok = v => v != null && isFinite(v) && v > 0;
      const pO = (mean, r, L) => ok(mean) ? A.pOver(A.pmfTotal(mean, r, Math.ceil(L) + 2), L) : null;
      const rT = R => R ? (R.rTeam != null ? R.rTeam : R.r) : null;
      const D = {
        st: L => MT ? pO(MT.tot, MT.MD && MT.MD.r, L) : null, hst: L => MT ? pO(MT.lh, rT(MT.MD), L) : null, ast: L => MT ? pO(MT.la, rT(MT.MD), L) : null,
        s: L => MT && MT.MS ? pO(MT.MS.lh + MT.MS.la, MT.MS.r, L) : null,
        f: L => MF ? pO(MF.tot, MF.r, L) : null, hf: L => MF ? pO(MF.lh, MF.rTeam != null ? MF.rTeam : MF.r, L) : null, af: L => MF ? pO(MF.la, MF.rTeam != null ? MF.rTeam : MF.r, L) : null,
        c: L => M ? pO(M.tot, M.r, L) : null, hc: L => M ? pO(M.lh, rT(M), L) : null, ac: L => M ? pO(M.la, rT(M), L) : null,
        k: L => x && x[4] ? pO(x[4], rk, L) : null, hk: L => x && x[6] ? pO(x[6], rk, L) : null, ak: L => x && x[7] ? pO(x[7], rk, L) : null };
      const REAL = { s: [m.hs, m.as], st: [m.hst, m.ast], c: [m.hc, m.ac], f: [m.hf, m.af], k: [m.hk, m.ak] };
      for (const [k, c] of Object.entries(LB)) {
        const [L, o, u] = c, po = D[k](L); if (po == null || !isFinite(po)) continue;
        const base = k.replace(/^[ha](?=(st|c|f|k)$)/, ""), R = REAL[base]; if (!R || R[0] == null || R[1] == null) continue;
        const real = k[0] === "h" && k !== "hst" ? R[0] : k[0] === "a" && k !== "ast" ? R[1] : k === "hst" ? R[0] : k === "ast" ? R[1] : R[0] + R[1];
        const eo = po * o - 1, eu = (1 - po) * u - 1, side = eo >= eu ? "O" : "U", ev = Math.max(eo, eu);
        const p = side === "O" ? po : 1 - po, odd = side === "O" ? o : u, hit = side === "O" ? real > L : real < L;
        rows.push({ key, d, lg, k, fam: FAM[k], side, p, odd, ev, hit: hit ? 1 : 0, val: ev >= BK_MIN, team: k.length > 1 && k !== "st" });
      }
    });
  } catch (e) { } finally { A.S.cutoff = c0; }
}
const note = (t, s) => console.log(`::notice title=${t}::` + s.replace(/%/g, "%25").replace(/\n/g, " "));
function st(R) {   // presa, probabilità dichiarata, quota media, rendimento a puntata fissa con intervallo raggruppato per partita
  if (!R.length) return null;
  const n = R.length, h = R.reduce((s, r) => s + r.hit, 0) / n, p = R.reduce((s, r) => s + r.p, 0) / n, q = R.reduce((s, r) => s + r.odd, 0) / n;
  const pl = R.map(r => r.hit * r.odd - 1), roi = pl.reduce((s, x) => s + x, 0) / n;
  const G = new Map(); R.forEach((r, i) => { const g = G.get(r.key) || [0, 0]; g[0] += pl[i] - roi; g[1]++; G.set(r.key, g); });
  const ng = G.size, se = ng > 1 ? Math.sqrt([...G.values()].reduce((s, g) => s + g[0] * g[0], 0)) / n : NaN;
  return { n, ng, h, p, q, roi, ci: 1.96 * se };
}
const fmt = s => s ? `${s.n} giocate in ${s.ng} partite · presa ${Math.round(s.h * 100)}% (dichiarata ${Math.round(s.p * 100)}%) · quota media ${s.q.toFixed(2)} · rendimento ${s.roi >= 0 ? "+" : ""}${(s.roi * 100).toFixed(1)}% ±${(s.ci * 100).toFixed(0)}` : "nessuna";
const V = rows.filter(r => r.val), days = [...new Set(rows.map(r => r.d))].sort();
note("Radar Mercato · archivio", `partite giocate con quote ${nPl}, con linee Over/Under 1xBet ${nLB} (dal ${days[0] || "-"} al ${days[days.length - 1] || "-"}) · linee valutate ${rows.length} · proposte dal Radar (valore ≥ +5%) ${V.length}`);
note("Radar Mercato · tutte le proposte", fmt(st(V)) + " ‖ riferimento, tutte le linee senza filtro di valore: " + fmt(st(rows)));
const by = (R, f) => { const M = new Map(); R.forEach(r => { const k = f(r); (M.get(k) || M.set(k, []).get(k)).push(r); }); return [...M.entries()]; };
note("Radar Mercato · per mercato", by(V, r => r.fam + (r.team ? " (squadra)" : " (totale)")).sort().map(([k, R]) => `${k}: ${fmt(st(R))}`).join(" ‖ "));
note("Radar Mercato · Over contro Under", by(V, r => r.side === "O" ? "Over" : "Under").map(([k, R]) => `${k}: ${fmt(st(R))}`).join(" ‖ "));
const evb = r => r.ev < 0.10 ? "valore 5-10%" : r.ev < 0.20 ? "valore 10-20%" : r.ev < 0.40 ? "valore 20-40%" : "valore oltre 40%";
note("Radar Mercato · per valore (ordinamento Guadagno)", by(V, evb).sort().map(([k, R]) => `${k}: ${fmt(st(R))}`).join(" ‖ "));
const pb = r => r.p < 0.5 ? "probabilità sotto 50%" : r.p < 0.6 ? "50-60%" : r.p < 0.7 ? "60-70%" : "70% e oltre";
note("Radar Mercato · per probabilità (ordinamento Riuscita)", by(V, pb).sort().map(([k, R]) => `${k}: ${fmt(st(R))}`).join(" ‖ "));
const half = days[Math.floor(days.length / 2)] || "";
note("Radar Mercato · stabilità", `prima metà (fino al ${half}): ${fmt(st(V.filter(r => r.d < half)))} ‖ seconda metà: ${fmt(st(V.filter(r => r.d >= half)))}`);
// 27/10/2026: le prime N giocate di ogni giorno con i due ordinamenti dell'app (Guadagno = valore atteso, Riuscita = probabilità)
const byDay = new Map(); V.forEach(r => (byDay.get(r.d) || byDay.set(r.d, []).get(r.d)).push(r));
const topN = (N, f) => [...byDay.values()].flatMap(L => L.slice().sort(f).slice(0, N));
const fEV = (a, b) => b.ev - a.ev || b.p - a.p, fP = (a, b) => b.p - a.p || b.ev - a.ev;
note("Radar Mercato · prime giocate del giorno: Guadagno contro Riuscita", [1, 3, 5, 10].map(N => `prime ${N}: Guadagno ${fmt(st(topN(N, fEV)))} | Riuscita ${fmt(st(topN(N, fP)))}`).join(" ‖ "));
// 27/10/2026: soglia minima di riuscita per alleggerire il Radar Mercato. Scelta sulla prima metà dei giorni, verifica sulla seconda.
const nd = Math.max(1, days.length);
note("Radar Mercato · soglia minima di riuscita", [0.55, 0.60, 0.62, 0.65, 0.68, 0.70, 0.72, 0.75].map(t => {
  const R = V.filter(r => r.p >= t), a = st(R.filter(r => r.d < half)), b = st(R.filter(r => r.d >= half));
  return `da ${Math.round(t * 100)}%: ${(R.length / nd).toFixed(1)} al giorno · prima metà ${a ? `${a.n} presa ${Math.round(a.h * 100)}% (dich ${Math.round(a.p * 100)}%) ${a.roi >= 0 ? "+" : ""}${(a.roi * 100).toFixed(1)}% ±${(a.ci * 100).toFixed(0)}` : "-"} | seconda ${b ? `${b.n} presa ${Math.round(b.h * 100)}% (dich ${Math.round(b.p * 100)}%) ${b.roi >= 0 ? "+" : ""}${(b.roi * 100).toFixed(1)}% ±${(b.ci * 100).toFixed(0)}` : "-"}`;
}).join(" ‖ "));
note("Radar Mercato · soglia 65% per mercato", by(V.filter(r => r.p >= 0.65), r => r.fam + (r.team ? " (squadra)" : "") + " " + (r.side === "O" ? "Over" : "Under")).sort().map(([k, R]) => `${k}: ${fmt(st(R))}`).join(" ‖ "));
