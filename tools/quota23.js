/* Quota 2 / Quota 3 · candidati (25/10/2026). Per ogni partita già giocata dell'archivio privato delle quote 1xBet (data/odds_hist.json):
   probabilità di Prevista calcolate con i soli dati dei giorni precedenti (S.cutoff, stessi modelli dell'app) per ogni esito che 1xBet
   quotava, con la quota "prima" (prima vista) e "ultima" (ultima vista prima del fischio), ed esito reale.
   Mercati: 1X2 gol, Over/Under 1,5 · 2,5 · 3,5, Gol/No gol, 1X2 corner · tiri · tiri in porta · falli · gialli · fuorigioco, Over/Under
   cartellini (linee 2,5–5,5). Scrive q23_candidati.json NEL RUNNER (mai pubblicato): lo legge tools/quota23.py, che stampa solo numeri
   aggregati. Nessuna richiesta API. */
const fs = require("fs"), vm = require("vm"), path = require("path");
const DIR = process.argv[2] || ".", DATA = path.join(DIR, "data"), PUB = path.join(DIR, "pub");
const html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + ";globalThis.API={S,MODES,parseCSV,addParsed,resetState,withLeague,model,modelShots,modelGoals,headToHeadProb,offModel,cardProbs,CARD_LINES,attachOffs};", ctx);
const A = ctx.API;
const rd = (p, f) => { try { return fs.readFileSync(path.join(p, f), "utf8"); } catch (e) { return null; } };
for (const [v, f] of [["EXTRA", "extra.json"], ["TAREA", "tiri_area.json"], ["OFFS", "fuorigioco.json"]]) { const t = rd(PUB, f); if (t) vm.runInContext(`${v} = ${t}; clearCache();`, ctx); }
const EX = JSON.parse(rd(PUB, "extra.json") || "{\"partite\":{}}"), ES = JSON.parse(rd(DIR, "esiti.json") || "{}");
A.resetState();
for (const bf of ["bundle_storico.json", "bundle.json"]) { const t = rd(PUB, bf); if (t) for (const f of JSON.parse(t).files) A.addParsed(A.parseCSV(f.text)); }
A.attachOffs();
const OH = JSON.parse(fs.readFileSync(path.join(DATA, "odds_hist.json"), "utf8"));
// 26/10/2026: correzioni dei falli con le formazioni ufficiali registrate prima della partita (archivio privato di update_data.py)
const XIH = JSON.parse(rd(DATA, "formazioni_hist.json") || "{}");
const RT = vm.runInContext("OFF_R_TEAM", ctx);
const q = (v, part, k) => { const x = v[part] && v[part].q && v[part].q[k]; const o = Array.isArray(x) ? x[0] : x; return o > 1 ? o : null; };
const out = []; let nPl = 0;
for (const [key, v] of Object.entries(OH)) {
  const m = A.S.matches.get(key); if (!m || m.hg == null) continue;
  nPl++;
  const [lg, d, h, a] = key.split("|"), es = ES[key] || {};
  const add = (mk, side, p, hit, k, pxi) => { if (p == null || !isFinite(p) || hit == null) return; const q0 = q(v, "prima", k), q1 = q(v, "ultima", k); if (!q0 && !q1) return;
    out.push({ key, d, lg, t: m.time || "", mk, side, p: Math.round(p * 1e4) / 1e4, pxi: pxi != null && isFinite(pxi) ? Math.round(pxi * 1e4) / 1e4 : null, y: hit ? 1 : 0, q0, q1 }); };
  const c0 = A.S.cutoff; A.S.cutoff = m.date;
  try {
    A.withLeague(lg, () => {
      A.S.season = m.season;
      const G = A.modelGoals(h, a, A.MODES.dyn), T = m.hg + m.ag;
      if (G) {
        add("1X2 gol", "1", G.p1, m.hg > m.ag, "1x2:1"); add("1X2 gol", "X", G.px, m.hg === m.ag, "1x2:X"); add("1X2 gol", "2", G.p2, m.ag > m.hg, "1x2:2");
        [1.5, 2.5, 3.5].forEach((L, i) => { add("Over/Under " + L, "Over", G.over[i], T > L, `ou${L}:O`); add("Over/Under " + L, "Under", 1 - G.over[i], T < L, `ou${L}:U`); });
        const gg = m.hg > 0 && m.ag > 0; add("Gol/No gol", "Gol", G.btts, gg, "gg:S"); add("Gol/No gol", "No gol", 1 - G.btts, !gg, "gg:N");
      }
      const st = (name, R, xh, xa, k, indep) => {
        if (!R || !isFinite(R.lh) || xh == null || xa == null) return;
        const P = indep ? A.headToHeadProb(R.lh, R.la, Infinity, indep) : A.headToHeadProb(R.lh, R.la, R.r, R.rTeam, R.cop);
        const X = k === "x.f1x2" && XIH[key] ? A.headToHeadProb(R.lh * XIH[key].fh, R.la * XIH[key].fa, R.r, R.rTeam, R.cop) : null;
        add(name, "1", P.home, xh > xa, k + ":Home", X && X.home); add(name, "X", P.draw, xh === xa, k + ":Draw", X && X.draw); add(name, "2", P.away, xa > xh, k + ":Away", X && X.away);
      };
      st("1X2 corner", A.model(h, a, A.MODES.dyn, "c"), m.hc, m.ac, "x.c1x2");
      const TS = A.modelShots(h, a, A.MODES.dyn);
      if (TS) { st("1X2 tiri", TS.MS, m.hs, m.as, "x.s1x2"); st("1X2 tiri in porta", TS.MD, m.hst, m.ast, "x.st1x2"); }
      st("1X2 falli", A.model(h, a, A.MODES.dyn, "f"), m.hf, m.af, "x.f1x2");
      const O = A.offModel(h, a); if (O && !O.nd) st("1X2 fuorigioco", O, m.ho, m.ao, "x.off.offsides_1x2", RT);
      const x = EX.partite[key];
      if (x && x[6] && x[7] && es.y) { const al = EX.alpha, r = al > 2e-4 ? 1 / al : Infinity; st("1X2 gialli", { lh: x[6], la: x[7], r, rTeam: r, cop: 0 }, es.y[0], es.y[1], "x.y1x2"); }
      if (x && x[4] && m.hk != null && m.ak != null) {
        const P = A.cardProbs(x[4]), K = m.hk + m.ak;
        A.CARD_LINES.forEach((L, i) => { add("Cartellini " + L, "Over", P[i], K > L, `kou:Over ${L}`); add("Cartellini " + L, "Under", 1 - P[i], K < L, `kou:Under ${L}`); });
      }
    });
  } catch (e) { } finally { A.S.cutoff = c0; }
}
fs.writeFileSync(path.join(DIR, "q23_candidati.json"), JSON.stringify(out));
console.log("candidati", out.length, "partite giocate", nPl);
