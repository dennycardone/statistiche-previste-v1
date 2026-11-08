/* Radar · Operatività · storico (31/10/2026, richiesta di Denny). Gira su GitHub dopo tools/mercato_ieri.js, a ogni aggiornamento.
   1) Per ogni partita non ancora iniziata calcola gli esiti candidati della vista Operatività con lo STESSO codice dell'app (opEntry:
      quote 1xBet attuali, probabilità corretta di oggi) e li registra in data/operativita_storico.json (magazzino privato). Al calcio
      d'inizio fa fede l'ultima versione vista prima del fischio.
   2) Dopo la partita aggiunge i valori reali e l'esito di ogni candidato.
   3) Giorni prima dell'inizio della registrazione (31/10/2026), fino a 7 giorni fa: ricostruzione walk-forward (solo dati precedenti alla
      partita, ultima quota 1xBet vista prima del fischio dall'archivio privato, coefficienti della probabilità corretta stimati sui soli
      giorni precedenti: corretta.json "per_giorno"), segnata "ric".
   4) Pubblica data/operativita_ieri.json (ultimi 7 giorni, fino a ieri): l'app applica le stesse regole (opSelect) e mostra le giocate
      del giorno con l'esito. Nessuna richiesta API. */
const fs = require("fs"), path = require("path"), vm = require("vm");
const DIR = path.join(__dirname, ".."), DATA = path.join(DIR, "data");
process.on("uncaughtException", e => { console.log("::warning title=Operatività storico::" + String(e && e.stack || e).replace(/\n/g, " | ").slice(0, 900)); process.exit(0); });
const html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
const start = html.indexOf("<script>") + 8, end = html.indexOf("/* ===== FINE MODELLO");
const blk = (a, b) => { const i = html.indexOf(a), j = html.indexOf(b, i); if (i < 0 || j < 0) throw new Error("blocco non trovato: " + a); return html.slice(i, j); };
const CUPB = "\nvar CUR = null;\n" + blk("/* ===== Champions League (13/10/2026)", "/* ===== Scheda partita");   // 8/11/2026: nazionali (naz.json) come le coppe
const CODE = CUPB + blk("const BK_ROWS", "\nlet QMOV") + "\nvar QMOV = null;\n" + blk("const isVal", "function off1x2HTML") + "\n" + blk("const NO_1XBET", "const qWhen") + "\n" + blk("let CORR = null", "const opCassa");
const noop = () => {};
const ctx = vm.createContext({ console, Math, Date, JSON, Intl, Map, Set, Number, String, Object, Array, isFinite, isNaN, parseFloat, parseInt, Infinity, NaN, Float64Array, WeakMap,
  document: { addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] }, localStorage: { getItem: () => null, setItem: noop, removeItem: noop }, matchMedia: () => ({ matches: false }), performance: { now: () => Date.now() } });
vm.runInContext(html.slice(start, end) + "\nvar LINEE = null;\n" + CODE + ";globalThis.API = { S, MODES, parseCSV, addParsed, resetState, allEntries, nazEntries, setNaz: j => { CUPD.NAZ = j; }, isoD, addDays, withLeague, attachOffs, opEntry, opSelect, opKelly, OP_C, setCorr: c => { CORR = c; OP_C.clear(); }, setOdds: (q, l) => { QMOV = q; LINEE = l; } };", ctx);
const A = ctx.API;
const rd = f => { try { return fs.readFileSync(path.join(DATA, f), "utf8"); } catch (e) { return null; } };
for (const [v, f] of [["EXTRA", "extra.json"], ["MERCATI", "mercati.json"], ["TAREA", "tiri_area.json"], ["FORMAZ", "formazioni.json"], ["OFFS", "fuorigioco.json"]]) {
  const t = rd(f); if (t) vm.runInContext(`${v} = ${t}; clearCache();`, ctx);
}
const CORR = JSON.parse(rd("corretta.json") || "null");
if (!CORR || !CORR.gruppi || !CORR.gruppi.statistiche) { console.log("::notice title=Operatività storico::probabilità corretta non disponibile: nessun aggiornamento"); process.exit(0); }
const QMOV = JSON.parse(rd("quote_mov.json") || "{\"partite\":{}}"), LINEE = JSON.parse(rd("linee.json") || "{\"partite\":{}}");
const OH = JSON.parse(rd("odds_hist.json") || "{}");
// gialli per squadra (il mercato 1X2 gialli conta solo i gialli): esiti.json di tools/esiti_extra.py, dalle statistiche API-Football
let ES = {}; try { ES = JSON.parse(fs.readFileSync(path.join(DIR, "esiti.json"), "utf8")); } catch (e) { ES = {}; }
const man = JSON.parse(rd("manifest.json"));
A.resetState();
for (const f of man.files || []) { const t = rd(f); if (t) A.addParsed(A.parseCSV(t)); }
A.S.meta = { fetched: man.updated }; A.attachOffs();
const romeOff = d => { try { const s = new Intl.DateTimeFormat("en-US", { timeZone: "Europe/Rome", timeZoneName: "shortOffset" }).formatToParts(new Date(d + "T12:00:00Z")).find(p => p.type === "timeZoneName").value; const m = s.match(/GMT([+-]\d+)/); return m ? +m[1] : 1; } catch (e) { return 1; } };
const koOf = e => Date.parse(`${e.d}T${/^\d\d:\d\d$/.test(e.time) ? e.time : "23:59"}:00Z`) - romeOff(e.d) * 3600e3;
const SP = path.join(DATA, "operativita_storico.json");
let H = {}; try { H = JSON.parse(fs.readFileSync(SP, "utf8")); } catch (e) { H = {}; }
const now = Date.now(), t0 = A.isoD(new Date()), cfg = A.MODES.dyn, r4 = x => Math.round(x * 1e4) / 1e4;
const strip = c => ({ k: c.k, mk: c.mk, side: c.side, who: c.who, p: r4(c.p), m: r4(c.m), pc: r4(c.pc), q: c.q, ev: r4(c.ev), und: c.und ? 1 : 0, invA: c.invA ? 1 : 0, hasXi: c.hasXi ? 1 : 0, nb: c.nb || 1, qmax: c.qmax || c.q, bk: c.bk || "1xBet" });
// quote dall'archivio privato (ultima vista prima del fischio) nello stesso formato di quote_mov.json e linee.json
const oddsOf = v => { const q = {}; for (const [k, x] of Object.entries((v.ultima || {}).q || {})) { const o = Array.isArray(x) ? x[0] : x; if (o > 1) q[k] = o; } return q; };
function kLine(q) {   // linea Over/Under cartellini più equilibrata (come update_data.py · linee.json)
  const L = {};
  for (const [k, o] of Object.entries(q)) { if (!k.startsWith("x.kou:")) continue; const pr = k.slice(6).split(" "); if (pr.length !== 2) continue; const ln = parseFloat(pr[1]); if (!isFinite(ln) || Math.abs(ln - Math.floor(ln) - 0.5) > 1e-9) continue; (L[ln] = L[ln] || {})[pr[0][0]] = o; }
  let best = null; for (const [ln, o] of Object.entries(L)) if (o.O > 1 && o.U > 1) { const d = Math.abs(1 / o.O - 1 / o.U); if (!best || d < best[0]) best = [d, +ln, o.O, o.U]; }
  return best ? [best[1], best[2], best[3], 0] : null;
}
let nUpd = 0, nRes = 0, nRic = 0;
// 8/11/2026 (Denny): anche le nazionali (previsioni da naz.json, file dell'app)
try { const nj = JSON.parse(fs.readFileSync(path.join(DIR, "data", "naz.json"), "utf8")); A.setNaz(nj); } catch (e) {}
const seen = new Set(), entries = A.allEntries(t0, 8).concat(A.nazEntries().filter(e => e.d >= A.addDays(t0, -8) && e.d <= A.addDays(t0, 14))).filter(e => !seen.has(e.id) && seen.add(e.id));
A.setCorr(CORR); A.setOdds(QMOV, LINEE);
for (const e of entries) {
  if (e.lg.noStats) continue;
  if (!e.m && koOf(e) > now) {
    const c = A.opEntry(e, cfg).map(strip);
    if (c.length || H[e.id]) { H[e.id] = { lg: e.lg.code, lgn: e.lg.name, paese: e.lg.country, d: e.d, ora: e.time, h: e.home, a: e.away, t: new Date().toISOString().slice(0, 16), c }; nUpd++; }
  }
}
// ricostruzione dei giorni prima della registrazione
const PG = CORR.per_giorno || {};
for (const e of entries) {
  if (e.lg.noStats || !e.m || H[e.id] || e.d < A.addDays(t0, -7) || e.d >= "2026-10-31" || !PG[e.d] || !OH[e.id]) continue;
  const q = oddsOf(OH[e.id]), kl = kLine(q);
  A.setCorr({ agg: "ric" + e.d, gruppi: { statistiche: { b: PG[e.d] } } });
  A.setOdds({ partite: { [e.id]: [["ric", q]] } }, { partite: kl ? { [e.id]: { k: kl } } : {} });
  const c = A.opEntry(e, cfg, e.m.date).map(strip);
  if (c.length) { H[e.id] = { lg: e.lg.code, lgn: e.lg.name, paese: e.lg.country, d: e.d, ora: e.time, h: e.home, a: e.away, t: null, ric: 1, c }; nRic++; }
}
A.setCorr(CORR); A.setOdds(QMOV, LINEE);
/* 2/11/2026 (Denny: "il giorno prima non riporta la Quota 2 che mi aveva consigliato"). REGISTRO delle proposte: lo storico ricalcolato con le
   ultime quote prima del fischio non coincide con quello che l'app mostrava quando lo si guardava (quote e giocate cambiano nel corso della
   giornata). Da oggi ogni proposta della giornata (singola, Controtendenza, Quota 2, Quota 3) viene FISSATA al primo giro in cui compare, con
   quota, probabilità corretta e peso di quel momento, e non cambia più: l'app mostra il registro (oggi e giorni passati), lo storico è lo
   stesso registro con l'esito. Pesi: Kelly 1/8 (tetto 3%); budget del giorno 10% della cassa, assegnato in ordine di comparsa (le proposte
   nuove si riducono se il budget rimasto non basta, a budget finito non si fissano più proposte). */
const LP = path.join(DATA, "operativita_registro.json");
let LR = {}; try { LR = JSON.parse(fs.readFileSync(LP, "utf8")); } catch (e) { LR = {}; }
const romeDate = new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Rome" }).format(new Date());
const nowIso = new Date().toISOString().slice(0, 16);
const base = e => ({ id: e.id, lg: e.lg.code, lgn: e.lg.name, ora: e.time, h: e.home, a: e.away });
const prop = c => ({ ...base(c.e), k: c.k, mk: c.mk, side: c.side, who: c.who, p: r4(c.p), pc: r4(c.pc), q: c.q, ev: r4(c.ev), und: c.und ? 1 : 0, hasXi: c.hasXi ? 1 : 0, nb: c.nb || 1, qmax: c.qmax || c.q, bk: c.bk || "1xBet" });
let nLock = 0;
{
  const todayE = entries.filter(e => !e.lg.noStats && !e.m && e.d === romeDate && koOf(e) > now);
  const Ad = todayE.flatMap(e => A.opEntry(e, cfg));
  const X = A.opSelect(Ad, 0);
  const day = LR[romeDate] || (LR[romeDate] = { singole: [], contro: [], q2: null, q3: null });
  const used = () => [...day.singole, ...day.contro, day.q2, day.q3].filter(Boolean).reduce((a, o) => a + (o.w || 0), 0);
  const neu = [];
  for (const c of X.S1) if (!day.singole.some(o => o.id === c.e.id)) neu.push(["singole", { ...prop(c), f: A.opKelly(c.pc, c.q) }]);
  for (const c of X.S3) if (!day.contro.some(o => o.id === c.e.id)) {
    const dup = day.singole.concat(neu.filter(n => n[0] === "singole").map(n => n[1])).some(o => o.id === c.e.id && o.k === c.k && o.side === c.side);
    neu.push(["contro", { ...prop(c), f: dup ? 0 : A.opKelly(c.pc, c.q), dup: dup ? 1 : 0 }]);
  }
  const comb = b => ({ legs: b.legs.map(prop), q: r4(b.q), p: r4(b.p), ev: r4(b.ev), f: A.opKelly(b.p, b.q) });
  if (!day.q2 && X.D2) neu.push(["q2", comb(X.D2)]);
  if (!day.q3 && X.T3) neu.push(["q3", comb(X.T3)]);
  const Rm = Math.max(0, 0.10 - used()), tf = neu.reduce((a, [, o]) => a + o.f, 0), sc = tf > 0 ? Math.min(1, Rm / tf) : 0;
  for (const [kind, o] of neu) {
    o.w = r4(o.f * sc); o.t = nowIso;
    if (!o.dup && o.w < 1e-4) continue;   // budget del giorno finito
    if (kind === "q2" || kind === "q3") day[kind] = o; else day[kind].push(o);
    nLock++;
  }
}
// esiti
const RK = { c: ["hc", "ac"], s: ["hs", "as"], st: ["hst", "ast"], f: ["hf", "af"], o: ["ho", "ao"] };
for (const e of entries) {
  const x = H[e.id]; if (!e.m || !x || (x.fine && e.d < A.addDays(t0, -3))) continue;   // 2/11/2026: esiti ricalcolati per 3 giorni
  let all = true;
  for (const g of x.c) {
    if (g.k === "kou" || g.k === "sou") {
      const [sd, ln] = g.side.split(" "), L = parseFloat(ln.replace(",", ".")), K = g.k === "kou" ? ["hk", "ak"] : ["hs", "as"];
      if (e.m[K[0]] == null || e.m[K[1]] == null) { all = false; continue; }
      g.r = e.m[K[0]] + e.m[K[1]]; g.ok = sd === "Over" ? (g.r > L ? 1 : 0) : (g.r < L ? 1 : 0); continue;
    }
    const Y = g.k === "y" && ES[e.id] && ES[e.id].y, K = RK[g.k], hv = Y ? Y[0] : K && e.m[K[0]], av = Y ? Y[1] : K && e.m[K[1]];
    if (hv == null || av == null) { all = false; continue; }
    g.r = `${hv}-${av}`; g.ok = g.side === "1" ? (hv > av ? 1 : 0) : g.side === "2" ? (av > hv ? 1 : 0) : (hv === av ? 1 : 0);
  }
  if (all) { x.fine = 1; x.ris = `${e.m.hg}-${e.m.ag}`; nRes++; }
}
// esiti delle proposte del registro (ricalcolati per 3 giorni, come i candidati)
const byId = new Map(entries.map(e => [e.id, e]));
function grade(g) {
  const e = byId.get(g.id); if (!e || !e.m) return;
  if (g.k === "kou" || g.k === "sou") { const [sd, ln] = g.side.split(" "), L = parseFloat(ln.replace(",", ".")), K = g.k === "kou" ? ["hk", "ak"] : ["hs", "as"]; if (e.m[K[0]] == null || e.m[K[1]] == null) return; g.r = e.m[K[0]] + e.m[K[1]]; g.ok = sd === "Over" ? (g.r > L ? 1 : 0) : (g.r < L ? 1 : 0); g.ris = `${e.m.hg}-${e.m.ag}`; return; }
  const Y = g.k === "y" && ES[e.id] && ES[e.id].y, K = RK[g.k], hv = Y ? Y[0] : K && e.m[K[0]], av = Y ? Y[1] : K && e.m[K[1]];
  if (hv == null || av == null) return;
  g.r = `${hv}-${av}`; g.ok = g.side === "1" ? (hv > av ? 1 : 0) : g.side === "2" ? (av > hv ? 1 : 0) : (hv === av ? 1 : 0); g.ris = `${e.m.hg}-${e.m.ag}`;
}
for (const [d, day] of Object.entries(LR)) {
  if (d < A.addDays(t0, -4)) continue;
  for (const o of [...day.singole, ...day.contro]) grade(o);
  for (const b of [day.q2, day.q3]) if (b) { b.legs.forEach(grade); b.ok = b.legs.some(l => l.ok === 0) ? 0 : b.legs.every(l => l.ok === 1) ? 1 : null; }
}
for (const d of Object.keys(LR)) if (d < A.addDays(t0, -60)) delete LR[d];
fs.writeFileSync(LP, JSON.stringify(LR));
const PR = {}; for (const [d, day] of Object.entries(LR)) if (d >= A.addDays(t0, -7)) PR[d] = day;
fs.writeFileSync(path.join(DATA, "operativita.json"), JSON.stringify({ agg: nowIso, giorni: PR }));
const lim = A.addDays(t0, -60); for (const k of Object.keys(H)) if (H[k].d < lim) delete H[k];
fs.writeFileSync(SP, JSON.stringify(H));
const lo = A.addDays(t0, -7), P = {};
for (const [k, x] of Object.entries(H)) if (x.d >= lo && x.d < t0 && x.c.length) P[k] = x;
fs.writeFileSync(path.join(DATA, "operativita_ieri.json"), JSON.stringify({ agg: new Date().toISOString().slice(0, 16), da: lo, partite: P }));
console.log(`::notice title=Operatività storico::registro: proposte fissate in questo giro ${nLock} (oggi ${romeDate}) · partite aggiornate prima del fischio ${nUpd} · ricostruite ${nRic} · con esito in questo giro ${nRes} · pubblicate (ultimi 7 giorni) ${Object.keys(P).length} partite`);
