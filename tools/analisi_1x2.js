/* Verifica dei 1X2 delle statistiche contro le quote di 1xBet (archivio privato data/odds_hist.json), 19/10/2026.
   Mercati: corner, tiri, tiri in porta, falli, gialli, fuorigioco (partita intera) e corner del 1° tempo.
   Probabilità: le stesse dell'app (modelli della Media dinamica, Binomiali Negative per squadra, correlazione casa-ospite dove
   l'app la usa), calcolate con i soli dati dei giorni precedenti (S.cutoff). Gialli: modello cartellini v2 per squadra (gialli + rossi
   attesi, il mercato conta solo i gialli). 1° tempo: valori attesi × quota del 1° tempo del campionato (data/tempi.json), r del 1° tempo.
   Esiti reali: file dell'app; gialli e 1° tempo da esiti.json (tools/esiti_extra.py); fuorigioco da data/fuorigioco.json.
   Gira solo in GitHub Actions; stampa solo numeri aggregati. Nessuna richiesta API. */
const fs = require("fs"), vm = require("vm"), path = require("path");
const DIR = process.argv[2] || ".", DATA = path.join(DIR, "data"), PUB = path.join(DIR, "pub");
const html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API={S,MODES,parseCSV,addParsed,resetState,withLeague,model,modelShots,headToHeadProb,offModel,offFind,OFF_R_TEAM};", ctx);
const A = ctx.API;
const rd = (p, f) => { try { return fs.readFileSync(path.join(p, f), "utf8"); } catch (e) { return null; } };
const EXs = rd(PUB, "extra.json"), EX = EXs ? JSON.parse(EXs) : { partite: {} };
for (const [v, f] of [["EXTRA", "extra.json"], ["TAREA", "tiri_area.json"], ["OFFS", "fuorigioco.json"], ["HALF", "tempi.json"]]) {
  const t = rd(PUB, f); if (t) vm.runInContext(`${v} = ${t}; clearCache();`, ctx); else console.log("manca", f);
}
const HALF = JSON.parse(rd(PUB, "tempi.json") || "{}");
A.resetState();
for (const bf of ["bundle_storico.json", "bundle.json"]) { const t = rd(PUB, bf); if (t) for (const f of JSON.parse(t).files) A.addParsed(A.parseCSV(f.text)); }
const OH = JSON.parse(fs.readFileSync(path.join(DATA, "odds_hist.json"), "utf8"));
const ES = JSON.parse(rd(DIR, "esiti.json") || "{}");
const SEL = { Home: 0, "1": 0, Draw: 1, X: 1, Away: 2, "2": 2 };
const MK = [["c", "Corner 1X2", /^x\.c1x2:(.+)$/], ["s", "Tiri 1X2", /^x\.s1x2:(.+)$/], ["st", "Tiri in porta 1X2", /^x\.st1x2:(.+)$/], ["f", "Falli 1X2", /^x\.f1x2:(.+)$/],
  ["y", "Gialli 1X2", /^x\.y1x2:(.+)$/], ["o", "Fuorigioco 1X2", /^x\.off\.offsides_1x2:(.+)$/], ["c1", "Corner 1X2 1° tempo", /^x\.h1\.corners_1x2[a-z0-9_]*:(.+)$/]];
const odds3 = (q, re) => { const o = [null, null, null]; for (const [k, v] of Object.entries(q || {})) { const m = re.exec(k); if (m && SEL[m[1]] != null && v[0] > 1) o[SEL[m[1]]] = v[0]; } return o.every(x => x) ? o : null; };
const rows = []; let nPl = 0;
for (const [key, v] of Object.entries(OH)) {
  const m = A.S.matches.get(key); if (!m || m.hg == null) continue;
  nPl++;
  const [lg, d, h, a] = key.split("|"), es = ES[key] || {};
  const P = {}, R = {};
  const c0 = A.S.cutoff; A.S.cutoff = m.date;
  try {
    A.withLeague(lg, () => {
      A.S.season = m.season;
      const p3 = x => [x.home, x.draw, x.away];
      const C = A.model(h, a, A.MODES.dyn, "c");
      if (C && isFinite(C.lh)) {
        P.c = p3(A.headToHeadProb(C.lh, C.la, C.r, C.rTeam, C.cop));
        const H = HALF.campionati && HALF.campionati[lg];
        if (H && H.c && HALF.r) P.c1 = p3(A.headToHeadProb(C.lh * H.c[0], C.la * H.c[1], Infinity, HALF.r.c[0]));
      }
      const T = A.modelShots(h, a, A.MODES.dyn);
      if (T && T.MS && isFinite(T.MS.lh)) P.s = p3(A.headToHeadProb(T.MS.lh, T.MS.la, T.MS.r, T.MS.rTeam, T.MS.cop));
      if (T && T.MD && isFinite(T.MD.lh)) P.st = p3(A.headToHeadProb(T.MD.lh, T.MD.la, T.MD.r, T.MD.rTeam, T.MD.cop));
      const F = A.model(h, a, A.MODES.dyn, "f");
      if (F && isFinite(F.lh)) P.f = p3(A.headToHeadProb(F.lh, F.la, F.r, F.rTeam, F.cop));
      const x = EX.partite[key];
      if (x && x[6] && x[7]) { const al = EX.alpha, r = al > 2e-4 ? 1 / al : Infinity; P.y = p3(A.headToHeadProb(x[6], x[7], r, r, 0)); }
      const O = A.offModel(h, a);
      if (O && !O.nd) P.o = p3(A.headToHeadProb(O.lh, O.la, Infinity, A.OFF_R_TEAM));
      const of = A.offFind(lg, h, a, m.date); if (of) R.o = [of.oh, of.oa];
    });
  } catch (e) { } finally { A.S.cutoff = c0; }
  R.c = [m.hc, m.ac]; R.s = [m.hs, m.as]; R.st = [m.hst, m.ast]; R.f = [m.hf, m.af]; R.y = es.y; R.c1 = es.c1;
  for (const [k, , re] of MK) {
    const p = P[k], r = R[k]; if (!p || !r || r[0] == null || r[1] == null) continue;
    const qu = odds3(v.ultima && v.ultima.q, re); if (!qu) continue;
    const qp = odds3(v.prima && v.prima.q, re);
    rows.push({ k, lg, p, y: r[0] > r[1] ? 0 : r[0] === r[1] ? 1 : 2, qu, qp });
  }
}
const ci = B_ => { if (!B_ || !B_[0]) return "0 giocate"; const mu = B_[1] / B_[0], sd = Math.sqrt(Math.max(B_[2] / B_[0] - mu * mu, 0) / B_[0]); return `${B_[0]} giocate ROI ${(mu * 100).toFixed(1)}% (±${(196 * sd).toFixed(0)})`; };
const add = (B_, pr) => { B_[0]++; B_[1] += pr; B_[2] += pr * pr; };
const out = [`1X2 statistiche · partite nell'archivio quote ${Object.keys(OH).length}, giocate ${nPl}, righe ${rows.length}. ROI con la quota di chiusura (ultima vista prima del fischio) e del mattino (prima vista); ± = intervallo al 95%`];
for (const [k, name] of MK) {
  const L = rows.filter(r => r.k === k); if (!L.length) { out.push(`${name}: nessuna partita giocata con quote e dati`); continue; }
  let llM = 0, llB = 0, dd = 0, dd2 = 0, mg = 0, hitF = 0, nF = 0, pF = 0;
  const val = { u: { 0: [0, 0, 0], 0.05: [0, 0, 0], 0.1: [0, 0, 0] }, p: { 0.05: [0, 0, 0], 0.1: [0, 0, 0] } }, fav = [0, 0, 0], favX = [0, 0, 0];
  for (const r of L) {
    const s = r.qu.reduce((t, q) => t + 1 / q, 0), pb = r.qu.map(q => 1 / q / s); mg += s - 1;
    const lm = -Math.log(Math.max(1e-6, r.p[r.y])), lb = -Math.log(Math.max(1e-6, pb[r.y])); llM += lm; llB += lb; dd += lm - lb; dd2 += (lm - lb) ** 2;
    for (const [w, q] of [["u", r.qu], ["p", r.qp]]) {
      if (!q) continue;
      const ev = r.p.map((x, i) => x * q[i] - 1), b = ev.indexOf(Math.max(...ev));
      for (const th of Object.keys(val[w])) if (ev[b] >= +th) add(val[w][th], b === r.y ? q[b] - 1 : -1);
    }
    // favorito del modello (1 o 2, come Segnali e Grado) con probabilità almeno 60%, quota di chiusura
    const f = r.p[0] >= r.p[2] ? 0 : 2;
    if (r.p[f] >= 0.6) { add(fav, f === r.y ? r.qu[f] - 1 : -1); nF++; pF += r.p[f]; hitF += f === r.y ? 1 : 0; }
  }
  const n = L.length, md = dd / n, se = Math.sqrt(Math.max(dd2 / n - md * md, 0) / n);
  out.push(`${name}: n=${n} · margine 1xBet ${(mg / n * 100).toFixed(1)}% · log-loss noi ${(llM / n).toFixed(4)} book ${(llB / n).toFixed(4)} (differenza ${md >= 0 ? "+" : ""}${md.toFixed(4)} ±${(1.96 * se).toFixed(4)}) · ` +
    `valore, quota chiusura: v≥0 ${ci(val.u[0])}; v≥5% ${ci(val.u[0.05])}; v≥10% ${ci(val.u[0.1])} · quota mattino: v≥5% ${ci(val.p[0.05])}; v≥10% ${ci(val.p[0.1])} · ` +
    `favorito del modello ≥60%: ${nF ? `presi ${Math.round(hitF / nF * 100)}% (attesi ${Math.round(pF / nF * 100)}%), ${ci(fav)}` : "nessuno"}`);
}
for (const l of out) console.log("::notice title=Analisi 1X2::" + l.replace(/%/g, "%25"));
