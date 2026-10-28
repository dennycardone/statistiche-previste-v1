/* Radar Mercato · "Ieri" (28/10/2026). Gira su GitHub dopo precalc.js, a ogni aggiornamento.
   1) Per ogni partita non ancora iniziata con linee 1xBet (data/linee.json) calcola le giocate del Radar Mercato con lo STESSO codice
      dell'app (modello sopra "FINE MODELLO" + bkCalc/isVal) e le registra in data/mercato_storico.json (magazzino privato). Al calcio
      d'inizio la partita non viene più ricalcolata: fa fede l'ultima versione vista prima del fischio (linea, quota, probabilità).
   2) Dopo la partita aggiunge il valore reale e l'esito (Over/Under riuscito o no).
   3) Pubblica data/mercato_ieri.json: le giocate bloccate delle partite degli ultimi 7 giorni, con esito. Le quote sono quelle che l'app
      mostrava prima della partita (data/linee.json è già pubblico). Nessuna richiesta API. */
const fs = require("fs"), path = require("path"), vm = require("vm");
const DIR = path.join(__dirname, ".."), DATA = path.join(DIR, "data");
process.on("uncaughtException", e => { console.log("::warning title=Mercato ieri::" + String(e && e.stack || e).replace(/\n/g, " | ").slice(0, 900)); process.exit(0); });
const html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const blk = (a, b) => { const i = html.indexOf(a), j = html.indexOf(b, i); if (i < 0 || j < 0) throw new Error("blocco non trovato: " + a); return html.slice(i, j); };
const BK = blk("const BK_ROWS", "\nlet QMOV") + "\n" + blk("const isVal", "function off1x2HTML");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }) });
vm.runInContext(html.slice(start, end) + "\nvar LINEE = null;\n" + BK + ";globalThis.API = { S, MODES, parseCSV, addParsed, resetState, allEntries, isoD, addDays, withLeague, model, modelGoals, modelShots, extraFor, bkCalc, isVal, BK_ROWS };", ctx);
const A = ctx.API;
const rd = f => { try { return fs.readFileSync(path.join(DATA, f), "utf8"); } catch (e) { return null; } };
for (const [v, f] of [["EXTRA", "extra.json"], ["MERCATI", "mercati.json"], ["TAREA", "tiri_area.json"], ["FORMAZ", "formazioni.json"], ["OFFS", "fuorigioco.json"], ["LINEE", "linee.json"]]) {
  const t = rd(f); if (t) vm.runInContext(`${v} = ${t}; clearCache();`, ctx);
}
const man = JSON.parse(rd("manifest.json"));
A.resetState();
for (const f of man.files || []) { const t = rd(f); if (t) A.addParsed(A.parseCSV(t)); }
A.S.meta = { fetched: man.updated };
// calcio d'inizio in UTC: data e ora italiane della partita (ora legale/solare con Intl)
const romeOff = d => { try { const s = new Intl.DateTimeFormat("en-US", { timeZone: "Europe/Rome", timeZoneName: "shortOffset" }).formatToParts(new Date(d + "T12:00:00Z")).find(p => p.type === "timeZoneName").value; const m = s.match(/GMT([+-]\d+)/); return m ? +m[1] : 1; } catch (e) { return 1; } };
const koOf = e => Date.parse(`${e.d}T${/^\d\d:\d\d$/.test(e.time) ? e.time : "23:59"}:00Z`) - romeOff(e.d) * 3600e3;
const SP = path.join(DATA, "mercato_storico.json");
let H = {}; try { H = JSON.parse(fs.readFileSync(SP, "utf8")); } catch (e) { H = {}; }
const now = Date.now(), t0 = A.isoD(new Date()), cfg = A.MODES.dyn, r4 = x => Math.round(x * 1e4) / 1e4;
const REALK = { s: ["hs", "as"], st: ["hst", "ast"], c: ["hc", "ac"], f: ["hf", "af"], k: ["hk", "ak"] };
let nUpd = 0, nRes = 0;
const seen = new Set(), entries = A.allEntries(t0, 8).filter(e => !seen.has(e.id) && seen.add(e.id));
for (const e of entries) {
  const LB = !e.lg.noStats && ctx.LINEE && ctx.LINEE.partite && ctx.LINEE.partite[e.id];   // come il Radar: niente campionati senza statistiche
  if (!e.m && LB && koOf(e) > now) {   // partita non iniziata: giocate di adesso (sostituiscono le precedenti)
    const out = [];
    A.withLeague(e.lg.code, () => { const c0 = A.S.cutoff; A.S.cutoff = null;
      try {
        let G = null, M = null, MT = null, MF = null; try { G = A.modelGoals(e.home, e.away, cfg); M = A.model(e.home, e.away, cfg); MT = A.modelShots(e.home, e.away, cfg); MF = A.model(e.home, e.away, cfg, "f"); } catch (x) {}
        const x = A.extraFor(e.home, e.away);
        for (const r of A.bkCalc({ G, M, MT, x, MF }, LB, null)) for (const [w, c] of [["t", r.t], ["h", r.h], ["a", r.a]])
          if (A.isVal(c)) out.push({ lab: r.lab, mk: r.mk, w, side: c.side, L: c.L, p: r4(c.p), q: c.odd, ev: r4(c.ev) });
      } finally { A.S.cutoff = c0; } });
    H[e.id] = { lg: e.lg.code, lgn: e.lg.name, paese: e.lg.country, d: e.d, ora: e.time, h: e.home, a: e.away, t: new Date().toISOString().slice(0, 16), g: out };
    nUpd++;
  }
  // giorni prima dell'inizio della registrazione (28/10/2026): ricostruzione walk-forward (solo dati precedenti alla partita, ultima
  // linea 1xBet vista prima del fischio, come tools/radar_mercato.js), segnata "ric" e mostrata come ricostruita nell'app
  if (e.m && LB && !H[e.id] && e.d >= A.addDays(t0, -7) && e.d < "2026-10-29") {
    const out = [];
    A.withLeague(e.lg.code, () => { const c0 = A.S.cutoff; A.S.cutoff = e.m.date; A.S.season = e.m.season;
      try {
        let G = null, M = null, MT = null, MF = null; try { G = A.modelGoals(e.home, e.away, cfg); M = A.model(e.home, e.away, cfg); MT = A.modelShots(e.home, e.away, cfg); MF = A.model(e.home, e.away, cfg, "f"); } catch (x) {}
        const x = A.extraFor(e.home, e.away);
        for (const r of A.bkCalc({ G, M, MT, x, MF }, LB, null)) for (const [w, c] of [["t", r.t], ["h", r.h], ["a", r.a]])
          if (A.isVal(c)) out.push({ lab: r.lab, mk: r.mk, w, side: c.side, L: c.L, p: r4(c.p), q: c.odd, ev: r4(c.ev) });
      } finally { A.S.cutoff = c0; } });
    H[e.id] = { lg: e.lg.code, lgn: e.lg.name, paese: e.lg.country, d: e.d, ora: e.time, h: e.home, a: e.away, t: null, ric: 1, g: out };
  }
  const x = H[e.id];
  if (e.m && x && !x.fine) {   // partita giocata: valori reali ed esito di ogni giocata bloccata
    let all = true;
    for (const g of x.g) {
      const K = REALK[g.mk]; const hv = K && e.m[K[0]], av = K && e.m[K[1]];
      if (hv == null || av == null) { all = false; continue; }
      g.r = g.w === "h" ? hv : g.w === "a" ? av : hv + av; g.ok = g.side === "O" ? (g.r > g.L ? 1 : 0) : (g.r < g.L ? 1 : 0);
    }
    if (all) { x.fine = 1; x.ris = `${e.m.hg}-${e.m.ag}`; nRes++; }
  }
}
// pulizia: 60 giorni
const lim = A.addDays(t0, -60); for (const k of Object.keys(H)) if (H[k].d < lim) delete H[k];
fs.writeFileSync(SP, JSON.stringify(H));
// pubblicato: partite degli ultimi 7 giorni (fino a ieri) con le giocate bloccate
const lo = A.addDays(t0, -7), P = {};
for (const [k, x] of Object.entries(H)) if (x.d >= lo && x.d < t0 && x.g.length) P[k] = x;
fs.writeFileSync(path.join(DATA, "mercato_ieri.json"), JSON.stringify({ agg: new Date().toISOString().slice(0, 16), da: lo, partite: P }));
const ng = Object.values(P).reduce((s, x) => s + x.g.length, 0), nok = Object.values(P).reduce((s, x) => s + x.g.filter(g => g.ok === 1).length, 0), ndone = Object.values(P).reduce((s, x) => s + x.g.filter(g => g.ok != null).length, 0);
console.log(`::notice title=Mercato ieri::partite aggiornate prima del fischio ${nUpd} · con esito in questo giro ${nRes} · pubblicate (ultimi 7 giorni) ${Object.keys(P).length} partite, ${ng} giocate, con esito ${ndone}, prese ${nok}`);
