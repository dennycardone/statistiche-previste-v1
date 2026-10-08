/* Analisi delle quote archiviate (data/odds_hist.json) contro le previsioni di Prevista e i risultati.
   Gira solo in GitHub Actions (l'archivio è nel magazzino privato); stampa solo numeri aggregati come annotazioni.
   Per ogni partita giocata e mercato: la linea principale (la più vicina al 50%), quota "prima" (mattina) e "ultima"
   (prima del fischio), mediana tra i bookmaker. Previsione con i soli dati precedenti alla partita (S.cutoff). */
const fs = require("fs"), vm = require("vm"), path = require("path");
const DIR = process.argv[2] || ".", DATA = path.join(DIR, "data");
const html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API={S,MODES,parseCSV,addParsed,resetState,isoD,withLeague,model,modelShots,modelGoals,pmfTotal,headToHeadProb};", ctx);
const A = ctx.API;
const EX = JSON.parse(fs.readFileSync(path.join(DIR, "pub", "extra.json"), "utf8"));
vm.runInContext("EXTRA = " + JSON.stringify(EX) + "; clearCache();", ctx);
const B = JSON.parse(fs.readFileSync(path.join(DIR, "pub", "bundle.json"), "utf8"));
A.resetState(); for (const f of B.files) A.addParsed(A.parseCSV(f.text));
const OH = JSON.parse(fs.readFileSync(path.join(DATA, "odds_hist.json"), "utf8"));
const cdf = (pmf, L) => { let o = 0, eq = 0; pmf.forEach((p, k) => { if (k > L) o += p; else if (k === L) eq += p; }); return { o, eq }; };
const conv = (ph, pa) => { const out = new Array(ph.length + pa.length).fill(0); ph.forEach((x, i) => pa.forEach((y, j) => out[i + j] += x * y)); return out; };
const rows = [];
let nMatch = 0, nPlayed = 0;
for (const [k, v] of Object.entries(OH)) {
  nMatch++;
  const m = A.S.matches.get(k); if (!m || m.hg == null) continue;
  nPlayed++;
  const [lg, d, h, a] = k.split("|");
  const c0 = A.S.cutoff; A.S.cutoff = m.date;
  let P = {};
  try {
    A.withLeague(lg, () => {
      A.S.season = m.season;
      const C = A.model(h, a, A.MODES.dyn, "c");
      if (C && isFinite(C.lh)) { const rt = C.rTeam != null ? C.rTeam : C.r; P.c = { tot: C.pmf || A.pmfTotal(C.lh + C.la, C.r, 40), h: A.pmfTotal(C.lh, rt, 30), a: A.pmfTotal(C.la, rt, 30), hh: A.headToHeadProb(C.lh, C.la, C.r, C.rTeam) }; }
      const T = A.modelShots(h, a, A.MODES.dyn);
      if (T && T.MD && isFinite(T.MD.lh)) P.st = { tot: T.MD.pmf || A.pmfTotal(T.MD.lh + T.MD.la, T.MD.r, 40) };
      const G = A.modelGoals(h, a, A.MODES.dyn);
      if (G) P.g = G;
      const x = EX.partite[k];
      if (x && x[4]) { const al = EX.alpha, r = al > 2e-4 ? 1 / al : Infinity; P.k = { tot: A.pmfTotal(x[4], r, 25), h: x[6] ? A.pmfTotal(x[6], r, 15) : null, a: x[7] ? A.pmfTotal(x[7], r, 15) : null }; }
    });
  } catch (e) { } finally { A.S.cutoff = c0; }
  const real = { c: m.hc != null && m.ac != null ? m.hc + m.ac : null, hc: m.hc, ac: m.ac, st: m.hst != null && m.ast != null ? m.hst + m.ast : null,
    k: m.hk != null && m.ak != null ? m.hk + m.ak : null, hk: m.hk, ak: m.ak, g: m.hg + m.ag };
  // mercati O/U: [chiave quote, nome, distribuzione, reale]
  const OU = [["cou", "Corner totali", P.c && P.c.tot, real.c], ["hcou", "Corner squadra casa", P.c && P.c.h, real.hc], ["acou", "Corner squadra ospite", P.c && P.c.a, real.ac],
    ["sot", "Tiri in porta totali", P.st && P.st.tot, real.st], ["kou", "Cartellini totali", P.k && P.k.tot, real.k], ["hk", "Cartellini casa", P.k && P.k.h, real.hk], ["ak", "Cartellini ospite", P.k && P.k.a, real.ak]];
  for (const [key, name, pmf, rv] of OU) {
    if (!pmf || rv == null) continue;
    // linea principale: la più equilibrata nelle quote "ultima"
    const qs = v.ultima.q, lines = new Set(Object.keys(qs).filter(q => q.startsWith(key + ":")).map(q => q.split(" ").pop()));
    let best = null;
    for (const L of lines) {
      const qo = qs[`${key}:Over ${L}`], qu = qs[`${key}:Under ${L}`]; if (!qo || !qu) continue;
      const pb = (1 / qo[0]) / (1 / qo[0] + 1 / qu[0]); if (!best || Math.abs(pb - 0.5) < Math.abs(best.pb - 0.5)) best = { L: +L, pb, qo: qo[0], qu: qu[0], nb: Math.min(qo[1], qu[1]) };
    }
    if (!best) continue;
    const pr = v.prima.q, po = pr[`${key}:Over ${best.L}`], pu = pr[`${key}:Under ${best.L}`];
    const { o, eq } = cdf(pmf, best.L);
    rows.push({ mk: name, L: best.L, real: rv, pO: o, pE: eq, pb: best.pb, qo: best.qo, qu: best.qu, nb: best.nb, qo0: po ? po[0] : null, qu0: pu ? pu[0] : null, lg });
  }
  // gol O/U 2.5 per confronto
  if (P.g && v.ultima.q["ou2.5:O"] && v.ultima.q["ou2.5:U"]) {
    const qo = v.ultima.q["ou2.5:O"][0], qu = v.ultima.q["ou2.5:U"][0], po = v.prima.q["ou2.5:O"], pu = v.prima.q["ou2.5:U"];
    rows.push({ mk: "Gol O/U 2,5 (confronto)", L: 2.5, real: real.g, pO: P.g.over[1], pE: 0, pb: (1 / qo) / (1 / qo + 1 / qu), qo, qu, nb: v.ultima.q["ou2.5:O"][1], qo0: po ? po[0] : null, qu0: pu ? pu[0] : null, lg });
  }
}
// riepilogo per mercato
const by = {};
for (const r of rows) (by[r.mk] = by[r.mk] || []).push(r);
const fmt = x => (x * 100).toFixed(1);
const lines = [`Partite nell'archivio ${nMatch}, giocate con risultato ${nPlayed}, righe ${rows.length}`];
for (const [mk, R] of Object.entries(by)) {
  let bU = 0, bB = 0, n = 0;
  const bets = { ultima: {}, prima: {} };
  for (const r of R) {
    const y = r.real > r.L ? 1 : r.real === r.L ? null : 0; if (y === null) continue; n++;
    const pO = r.pO / (1 - r.pE || 1);
    bU += (pO - y) ** 2; bB += (r.pb - y) ** 2;
    for (const [when, qo, qu] of [["ultima", r.qo, r.qu], ["prima", r.qo0, r.qu0]]) {
      if (!qo || !qu) continue;
      for (const th of [0, 0.05, 0.10, 0.15]) {
        const eO = pO * qo - 1, eU = (1 - pO) * qu - 1; let pr = null;
        if (eO >= th && eO >= eU) pr = y ? qo - 1 : -1; else if (eU >= th) pr = y ? -1 : qu - 1;
        if (pr === null) continue; const B_ = bets[when][th] = bets[when][th] || [0, 0, 0]; B_[0]++; B_[1] += pr; B_[2] += pr * pr;
      }
    }
  }
  if (!n) continue;
  const roi = B_ => { if (!B_) return "0 giocate"; const m_ = B_[1] / B_[0], sd = Math.sqrt(Math.max(B_[2] / B_[0] - m_ * m_, 0) / B_[0]); return `${B_[0]} giocate ROI ${(m_ * 100).toFixed(1)}% (±${(1.96 * sd * 100).toFixed(0)})`; };
  const avgMargin = R.reduce((s, r) => s + (1 / r.qo + 1 / r.qu - 1), 0) / R.length;
  lines.push(`${mk}: n=${n} · margine book ${fmt(avgMargin)}% · Brier noi ${(bU / n).toFixed(4)} book ${(bB / n).toFixed(4)} · ` +
    `quota ULTIMA: v≥0 ${roi(bets.ultima[0])}; v≥5% ${roi(bets.ultima[0.05])}; v≥10% ${roi(bets.ultima[0.1])}; v≥15% ${roi(bets.ultima[0.15])} · ` +
    `quota PRIMA (mattina): v≥5% ${roi(bets.prima[0.05])}; v≥10% ${roi(bets.prima[0.1])}`);
}
for (const l of lines) console.log("::notice title=Analisi quote::" + l.replace(/%/g, "%25"));
fs.writeFileSync("analisi_righe.json", JSON.stringify(rows));
