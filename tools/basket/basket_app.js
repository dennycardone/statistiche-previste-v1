/* Prevista · Basket (15/11/2026, Denny: "stesse sezioni del calcio"). Dati: data/basket.json (tools/basket/pubblica.py ogni 3 ore).
   Tutto parte dalla LETTURA (regola del 15/11): si propone solo il lato che Prevista dà più probabile; la quota decide solo se conviene.
   Modello: ritmo × attacco/difesa ogni 100 possessi + vantaggio del campo, verificato walk-forward (IPOTESI.md 15/11/2026).
   Operatività: in osservazione (lo storico delle quote basket parte dal 15/11), nessuna puntata. */
"use strict";
const $ = s => document.querySelector(s);
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const f1 = x => x == null || !isFinite(x) ? "—" : x.toFixed(1).replace(".", ",");
const f2 = x => x == null || !isFinite(x) ? "—" : x.toFixed(2).replace(".", ",");
const pc = x => x == null || !isFinite(x) ? "—" : Math.round(x * 100) + "%";
const sg = x => (x > 0 ? "+" : x < 0 ? "−" : "") + f1(Math.abs(x)).replace(",0", "");
const lnum = x => String(x).replace(".", ",");
const Phi = z => { const t = 1 / (1 + 0.2316419 * Math.abs(z)), d = 0.3989423 * Math.exp(-z * z / 2), p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274)))); return z > 0 ? 1 - p : p; };
const TZ = "Europe/Rome";
const dayOf = iso => new Date(iso + ":00Z").toLocaleDateString("sv-SE", { timeZone: TZ });
const timeOf = iso => new Date(iso + ":00Z").toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit", timeZone: TZ });
const todayIso = () => new Date().toLocaleDateString("sv-SE", { timeZone: TZ });
const addDays = (iso, k) => { const d = new Date(iso + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + k); return d.toISOString().slice(0, 10); };
const DAYS = ["dom", "lun", "mar", "mer", "gio", "ven", "sab"];
const dlab = iso => { const d = new Date(iso + "T12:00:00Z"); return `${DAYS[d.getUTCDay()]} ${+iso.slice(8)}/${+iso.slice(5, 7)}`; };
const FL = { NBA: "🇺🇸", EL: "🇪🇺", EC: "🇪🇺", ITA: "🇮🇹", ACB: "🇪🇸", BBL: "🇩🇪", LNB: "🇫🇷" };
const LG_ORD = ["NBA", "EL", "EC", "ITA", "ACB", "BBL", "LNB"];
let B = null;
const S = { view: "part", day: null, game: null, mt: "prev", rt: "gr", rday: null, sw: new Set(["0", "1"]), slg: "all", tlg: "all", dlg: "all" };

/* ---------- calcolo ---------- */
const team = (lg, id) => (B.squadre[lg] || {})[id] || ["—", ""];
const logo = (lg, id, big) => { const t = team(lg, id); return t[1] ? `<img class="tlogo${big ? " big" : ""}" src="${esc(t[1])}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()">` : ""; };
const fin = g => g.sh && g.sa && g.sh[5] != null;
const live = g => !fin(g) && g.st && !["NS", "TBD", "POST", "CANC"].includes(g.st);
function reading(g) {
  const p = g.p, sgm = B.sigma[g.lg]; if (!p || !sgm) return null;
  const [ss, st] = sgm, ms = p.eh - p.ea, mt = p.eh + p.ea, LN = B.linee[g.id] || {};
  const pw = Phi(ms / ss), out = { ms, mt, pw, LN, R: [] };
  // vittoria (supplementari compresi)
  { const home = pw >= 0.5, q = LN.ml ? (home ? LN.ml[0] : LN.ml[2]) : null, bk = LN.ml ? (home ? LN.ml[1] : LN.ml[3]) : null, p_ = home ? pw : 1 - pw;
    out.R.push({ k: "vittoria", lab: `Vince ${team(g.lg, home ? g.h : g.a)[0]}`, sh: home ? "1" : "2", p: p_, q, bk, hit: fin(g) ? (g.sh[5] > g.sa[5]) === home : null }); }
  // totale punti alla linea del book (senza linea: la linea del modello)
  { const L = LN.tot ? LN.tot[0] : Math.round(mt) + 0.5, po = 1 - Phi((L - mt) / st), ov = po >= 0.5, p_ = ov ? po : 1 - po;
    out.R.push({ k: "totale", lab: `${ov ? "Over" : "Under"} ${lnum(L)} punti`, sh: `${ov ? "O" : "U"} ${lnum(L)}`, p: p_, L, book: !!LN.tot, q: LN.tot ? (ov ? LN.tot[1] : LN.tot[3]) : null, bk: LN.tot ? (ov ? LN.tot[2] : LN.tot[4]) : null,
      hit: fin(g) ? (g.sh[5] + g.sa[5] > L) === ov : null }); }
  // handicap alla linea del book: "Home −5,5" = la squadra di casa deve vincere di 6 o più
  if (LN.hcp) { const Lh = LN.hcp[0], ph = 1 - Phi((-Lh - ms) / ss), home = ph >= 0.5, p_ = home ? ph : 1 - ph;
    out.R.push({ k: "handicap", lab: `${team(g.lg, home ? g.h : g.a)[0]} ${home ? sg(Lh) : sg(-Lh)}`, sh: `${home ? "1" : "2"} ${home ? sg(Lh) : sg(-Lh)}`, p: p_, L: Lh, book: true, q: home ? LN.hcp[1] : LN.hcp[3], bk: home ? LN.hcp[2] : LN.hcp[4],
      hit: fin(g) ? ((g.sh[5] - g.sa[5] + Lh > 0) === home) : null }); }
  for (const r of out.R) { r.ev = r.q ? r.p * r.q - 1 : null; r.fair = 1 / r.p; const gr = gradeOf(r.k, r.p); r.uscite = gr.u; r.n = gr.n; r.g = gr.g; }
  return out;
}
function gradeOf(k, p) {
  const T = (B.grado || {})[k] || {}; let b = Math.floor(p * 20); while (b > 10 && !T[b]) b--;
  const x = T[b]; if (!x) return { u: null, n: 0, g: null };
  const u = x[1]; return { u, n: x[0], g: u >= 0.80 ? "A+" : u >= 0.72 ? "A" : u >= 0.64 ? "B" : u >= 0.56 ? "C" : null };
}
const gcls = g => g === "A+" ? "ap" : g === "A" ? "a" : g === "B" ? "b" : "c";
const gbadge = g => g ? `<span class="gbadge ${gcls(g)}">${g}</span>` : "";
const games = () => B.partite.map(g => ({ ...g, day: dayOf(g.d) }));
const VAL_MIN = 0.03;

/* ---------- viste ---------- */
function show(v) {
  S.view = v;
  for (const [id, vv] of [["#viewPart", "part"], ["#viewMatch", "match"], ["#viewSel", "radar"], ["#viewSig", "seg"], ["#viewGen", "ten"], ["#viewRit", "dig"]]) $(id).hidden = vv !== v;
  for (const [id, vv] of [["#navStats", "part"], ["#navSel", "radar"], ["#navSig", "seg"], ["#navGen", "ten"], ["#navRit", "dig"]]) $(id).setAttribute("aria-pressed", String(vv === v || (v === "match" && vv === "part")));
  window.scrollTo(0, 0);
  ({ part: renderPart, match: renderMatch, radar: renderRadar, seg: renderSeg, ten: renderTen, dig: renderDig })[v]();
}
function dayStrip(box, cur, onPick, opts = {}) {
  const t0 = todayIso(), G = games(), set = new Set(G.map(g => g.day)); set.add(t0);
  const days = [...set].filter(d => !opts.future || d >= t0).sort();
  box.innerHTML = days.map(d => { const n = G.filter(g => g.day === d).length;
    return `<button type="button" class="day${d < t0 ? " past" : ""}" role="tab" data-d="${d}" aria-selected="${d === cur}"><b>${d === t0 ? "Oggi" : DAYS[new Date(d + "T12:00:00Z").getUTCDay()]}</b><span>${d.slice(8)}.${d.slice(5, 7)}</span><small>${n ? n + " partite" : "—"}</small></button>`; }).join("");
  box.querySelectorAll(".day").forEach(b => b.addEventListener("click", () => onPick(b.dataset.d)));
  const sel = box.querySelector('[aria-selected="true"]'); if (sel) { const r = sel.getBoundingClientRect(), bb = box.getBoundingClientRect(); box.scrollLeft += (r.left + r.width / 2) - (bb.left + bb.width / 2); }
}
function rowHTML(g) {
  const R = reading(g), v = R && R.R[0];
  const tm = fin(g) ? "Finale" : live(g) ? "In corso" : timeOf(g.d);
  const end = v ? `<span class="pv${v.hit == null ? (v.p >= 0.7 ? " hi" : "") : v.hit ? " ok" : " ko"}"><small>${esc(v.sh)}</small><b>${Math.round(v.p * 100)}</b></span>` : "";
  return `<button type="button" class="mrow" data-gid="${esc(g.id)}">
    <span class="tmc"><span class="tm${fin(g) ? " fin" : ""}">${tm}</span>${end}</span>
    <span class="tt"><span class="${fin(g) && g.sh[5] > g.sa[5] ? "w" : ""}">${logo(g.lg, g.h)}${esc(team(g.lg, g.h)[0])}</span><b>${fin(g) ? g.sh[5] : g.p ? `<small class="prevpt">${Math.round(g.p.eh)}</small>` : ""}</b>
    <span class="${fin(g) && g.sa[5] > g.sh[5] ? "w" : ""}">${logo(g.lg, g.a)}${esc(team(g.lg, g.a)[0])}</span><b>${fin(g) ? g.sa[5] : g.p ? `<small class="prevpt">${Math.round(g.p.ea)}</small>` : ""}</b></span></button>`;
}
function bindRows(box) { box.querySelectorAll("[data-gid]").forEach(b => b.addEventListener("click", () => openGame(b.dataset.gid))); }
function openGame(id) { S.game = id; S.mt = "prev"; show("match"); }
function lgBlock(lg, rows, open = true) {
  return `<section class="lgblock${open ? "" : " closed"}" data-lg="${lg}"><button type="button" class="lghead" aria-expanded="${open}"><span class="flag" aria-hidden="true">${FL[lg] || "🏀"}</span><span class="nm"><small>${esc(B.leghe[lg][1])}</small><b>${esc(B.leghe[lg][0])}</b></span><span class="cnt">${rows.length}</span><svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>${rows.map(rowHTML).join("")}</section>`;
}
function renderPart() {
  const t0 = todayIso(); if (!S.day) S.day = t0;
  dayStrip($("#days"), S.day, d => { S.day = d; renderPart(); });
  const G = games().filter(g => g.day === S.day);
  const box = $("#sched");
  if (!G.length) { box.innerHTML = `<div class="empty">${S.day === t0 ? "Oggi nessuna partita" : "Nessuna partita"} di questi campionati.</div>`; return; }
  const played = G.map(g => reading(g)).filter(R => R && R.R[0].hit != null);
  const sum = played.length ? `<div class="daysum"><span>Vincente giusta in questo giorno</span><b class="${played.filter(R => R.R[0].hit).length / played.length >= 0.5 ? "good" : "bad"}">${Math.round(played.filter(R => R.R[0].hit).length / played.length * 100)}%</b><small>${played.filter(R => R.R[0].hit).length} su ${played.length}</small></div>` : "";
  box.innerHTML = sum + LG_ORD.filter(lg => G.some(g => g.lg === lg)).map(lg => lgBlock(lg, G.filter(g => g.lg === lg).sort((a, b) => a.d.localeCompare(b.d)))).join("");
  box.querySelectorAll(".lghead").forEach(h => h.addEventListener("click", () => { const s = h.parentElement; s.classList.toggle("closed"); h.setAttribute("aria-expanded", String(!s.classList.contains("closed"))); }));
  bindRows(box);
}
function posOf(lg, id) { const C = B.classifica[lg] || []; const i = C.findIndex(r => r[0] === id); return i < 0 ? null : { pos: i + 1, w: C[i][2], l: C[i][3] }; }
function renderMatch() {
  const g = games().find(x => x.id === S.game); if (!g) { show("part"); return; }
  document.querySelectorAll("#viewMatch .mtab").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.mt === S.mt)));
  document.querySelectorAll("#viewMatch .mpane").forEach(p => { p.hidden = p.dataset.mp !== S.mt; });
  $("#seasonTag").textContent = `${B.leghe[g.lg][0]} · ${B.stagioni[g.lg]}`;
  const R = reading(g), ph = posOf(g.lg, g.h), pa = posOf(g.lg, g.a), p = g.p;
  const head = `<div class="bkhead"><div class="bkt">${logo(g.lg, g.h, 1)}<b>${esc(team(g.lg, g.h)[0])}</b><small>${ph ? `${ph.pos}° · ${ph.w}-${ph.l}` : ""}</small></div>
    <div class="bkc"><small>${FL[g.lg] || ""} ${esc(B.leghe[g.lg][0])}</small><b class="bksc">${fin(g) ? `${g.sh[5]} – ${g.sa[5]}` : p ? `${Math.round(p.eh)} – ${Math.round(p.ea)}` : "vs"}</b><small>${fin(g) ? "Finale" + ((g.sh[4] || 0) + (g.sa[4] || 0) > 0 ? " d.t.s." : "") : live(g) ? "In corso" : `${dlab(g.day)} · ${timeOf(g.d)}`}</small>${fin(g) || !p ? "" : `<small class="muted">punti previsti</small>`}</div>
    <div class="bkt">${logo(g.lg, g.a, 1)}<b>${esc(team(g.lg, g.a)[0])}</b><small>${pa ? `${pa.pos}° · ${pa.w}-${pa.l}` : ""}</small></div></div>`;
  // Lettura
  let lett = "";
  if (p && R) {
    const row = (lab, h, c, a) => `<tr><td class="num">${h}</td><th>${lab}</th><td class="num">${a}</td></tr>${c != null ? `<tr class="sub"><td></td><td>${c}</td><td></td></tr>` : ""}`;
    const real = fin(g), h1 = p.h1 || 0.5;
    lett = `<table class="bkl"><tbody>
      ${row("Punti", `<b>${real ? g.sh[5] : ""}</b> <small>prev. ${f1(p.eh)}</small>`, `Totale ${real ? `<b>${g.sh[5] + g.sa[5]}</b> · ` : ""}prev. ${f1(R.mt)}`, `<b>${real ? g.sa[5] : ""}</b> <small>prev. ${f1(p.ea)}</small>`)}
      ${row("1° tempo", real && g.sh[1] != null ? `<b>${g.sh[0] + g.sh[1]}</b> <small>prev. ${f1(p.eh * h1)}</small>` : `<small>prev. ${f1(p.eh * h1)}</small>`, null, real && g.sa[1] != null ? `<b>${g.sa[0] + g.sa[1]}</b> <small>prev. ${f1(p.ea * h1)}</small>` : `<small>prev. ${f1(p.ea * h1)}</small>`)}
      ${row("Vittoria", `<b>${pc(R.pw)}</b>`, `Scarto previsto ${sg(R.ms)} per ${team(g.lg, R.ms >= 0 ? g.h : g.a)[0]}`, `<b>${pc(1 - R.pw)}</b>`)}
      ${row("Possessi", "", `${f1(p.pace)} a squadra (ritmo previsto)`, "")}
      ${real && g.stat && g.stat.h && g.stat.a ? row("Rimbalzi", g.stat.h[6] ?? "—", null, g.stat.a[6] ?? "—") + row("Assist", g.stat.h[9] ?? "—", null, g.stat.a[9] ?? "—") + row("Triple", `${g.stat.h[2] ?? "—"}/${g.stat.h[3] ?? "—"}`, null, `${g.stat.a[2] ?? "—"}/${g.stat.a[3] ?? "—"}`) + row("Palle perse", g.stat.h[12] ?? "—", null, g.stat.a[12] ?? "—") : ""}
    </tbody></table>`;
    const LN = R.LN, lines = R.R.filter(r => r.q);
    lett += lines.length ? `<div class="card bkq"><h3>Linee dei book · lato della lettura</h3><table class="bkt2"><thead><tr><th></th><th>Prevista</th><th>Quota</th><th>Equa</th><th>Valore</th></tr></thead><tbody>${lines.map(r => `<tr><th>${esc(r.lab)}${r.hit != null ? ` <span class="${r.hit ? "okc" : "koc"}">${r.hit ? "✓" : "✗"}</span>` : ""}</th><td class="num">${pc(r.p)}</td><td class="num"><b>${f2(r.q)}</b><small>${esc(r.bk || "")}</small></td><td class="num">${f2(r.fair)}</td><td class="num ${r.ev >= VAL_MIN ? "vgood" : ""}">${r.ev == null ? "—" : (r.ev >= 0 ? "+" : "−") + Math.round(Math.abs(r.ev) * 100) + "%"}</td></tr>`).join("")}</tbody></table>
      <p class="small muted">Solo il lato che Prevista dà più probabile; equa = 100 / probabilità; valore = probabilità × quota − 1 (miglior quota tra ${LN.tot ? LN.tot[9] : "i"} book). Il modello è verificato sui risultati, non ancora contro le quote: un valore grande, soprattutto contro Pinnacle, è più spesso un limite del modello che un errore del book. Quote solo informative, 18+.</p></div>`
      : `<p class="small muted">Linee dei book non ancora disponibili per questa partita (arrivano il giorno prima e il giorno della partita).</p>`;
  } else lett = `<p class="muted">Previsione non disponibile (poche partite delle squadre nella stagione).</p>`;
  $("#mhead").innerHTML = head + lett;
  // Grado
  $("#mgrado").innerHTML = R ? `<h2>Grado</h2><p class="small muted">Quante volte previsioni come questa sono uscite nelle stagioni 2024-25 e 2025-26 (partite che il modello non aveva visto).</p>
    ${R.R.map(r => `<div class="grow"><div><b>${esc(r.lab)}</b><small>${r.book ? "linea del book" : r.k === "totale" ? "linea del modello" : ""}</small></div>${gbadge(r.g)}<div class="num"><b>${r.uscite == null ? "—" : Math.round(r.uscite * 100)}</b> su 100<small>Prevista ${pc(r.p)}</small></div></div>`).join("")}
    <div class="glegend"><span class="gbadge ap">A+</span> 80+ su 100 · <span class="gbadge a">A</span> 72+ · <span class="gbadge b">B</span> 64+ · <span class="gbadge c">C</span> 56+</div>` : `<p class="muted">Grado non disponibile.</p>`;
  // Precedenti
  const PR = (B.precedenti[g.id] || []).slice().reverse();
  $("#mh2h").innerHTML = `<h2>Precedenti</h2>` + (PR.length ? `<table class="bkt2"><tbody>${PR.map(x => `<tr><td class="small">${dlab(x[0])} ${x[0].slice(0, 4)}</td><td>${esc(team(g.lg, x[1])[0])}</td><td class="num"><b>${x[3]} – ${x[4]}</b></td><td>${esc(team(g.lg, x[2])[0])}</td></tr>`).join("")}</tbody></table>` : `<p class="muted">Nessun precedente nell'archivio dal 2019.</p>`);
  // Classifica
  const C = B.classifica[g.lg] || [];
  $("#mtab").innerHTML = `<h2>Classifica · ${esc(B.leghe[g.lg][0])}</h2><table class="bkt2 cls"><thead><tr><th>#</th><th>Squadra</th><th>G</th><th>V</th><th>P</th><th>Diff.</th></tr></thead><tbody>${C.map((r, i) => `<tr class="${r[0] === g.h || r[0] === g.a ? "hl" : ""}"><td>${i + 1}</td><td>${logo(g.lg, r[0])}${esc(team(g.lg, r[0])[0])}</td><td class="num">${r[1]}</td><td class="num">${r[2]}</td><td class="num">${r[3]}</td><td class="num">${sg(r[4] - r[5]).replace(",0", "")}</td></tr>`).join("")}</tbody></table>`;
  // Rendimento
  const U = id => (B.ultime[`${g.lg}|${id}`] || []).slice().reverse();
  const rend = id => { const L = U(id), w = L.filter(r => r[3] > r[4]).length, pf = L.reduce((a, r) => a + r[3], 0) / (L.length || 1), pa_ = L.reduce((a, r) => a + r[4], 0) / (L.length || 1);
    return `<div class="card"><h3>${logo(g.lg, id)}${esc(team(g.lg, id)[0])}</h3><p class="small">Ultime ${L.length}: <b>${w} vinte</b>, ${L.length - w} perse · punti fatti ${f1(pf)}, subiti ${f1(pa_)}</p>
      <div class="formrow">${L.map(r => `<span class="fpill ${r[3] > r[4] ? "w" : "l"}" title="${esc(team(g.lg, r[1])[0])}">${r[3] > r[4] ? "V" : "P"}</span>`).join("")}</div>
      <table class="bkt2"><tbody>${L.map(r => `<tr><td class="small">${dlab(r[0])}</td><td>${r[2] ? "vs" : "@"} ${esc(team(g.lg, r[1])[0])}</td><td class="num"><b class="${r[3] > r[4] ? "okc" : "koc"}">${r[3]} – ${r[4]}</b></td></tr>`).join("")}</tbody></table></div>`; };
  $("#mrend").innerHTML = rend(g.h) + rend(g.a);
}
/* Radar */
function radarItems(day) {
  return games().filter(g => g.day === day && !fin(g) && !live(g)).map(g => ({ g, R: reading(g) })).filter(x => x.R);
}
function itemHTML(g, r, extra) {
  return `<button type="button" class="selrow" data-gid="${esc(g.id)}"><span class="selt"><b>${esc(team(g.lg, g.h)[0])} – ${esc(team(g.lg, g.a)[0])}</b><small>${FL[g.lg] || ""} ${esc(B.leghe[g.lg][0])} · ${timeOf(g.d)}</small></span>
    <span class="selp"><span>${esc(r.lab)}</span>${r.q ? `<small>@${f2(r.q)}</small>` : ""}${gbadge(r.g)}</span><span class="selv">${extra}</span></button>`;
}
function renderRadar() {
  const t0 = todayIso(); if (!S.rday || S.rday < t0) S.rday = t0;
  dayStrip($("#rdays"), S.rday, d => { S.rday = d; renderRadar(); }, { future: true });
  const I = radarItems(S.rday);
  const gr = I.flatMap(({ g, R }) => R.R.filter(r => r.g).map(r => ({ g, r }))).sort((a, b) => b.r.uscite - a.r.uscite);
  const mk = I.flatMap(({ g, R }) => R.R.filter(r => r.q && r.ev >= VAL_MIN).map(r => ({ g, r }))).sort((a, b) => b.r.ev - a.r.ev);
  const op = I.flatMap(({ g, R }) => R.R.filter(r => r.q && r.ev > 0 && r.g && r.g !== "C").map(r => ({ g, r }))).sort((a, b) => b.r.ev - a.r.ev);
  $("#rtA").textContent = gr.length || ""; $("#rtB").textContent = mk.length || ""; $("#rtO").textContent = op.length || "";
  document.querySelectorAll("#selTabs [data-rt]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.rt === S.rt)));
  const box = $("#selOut");
  if (S.rt === "gr") box.innerHTML = `<div class="selhead"><h2>Grado</h2><span class="small muted">${dlab(S.rday)}</span></div>` + (gr.length ? gr.map(({ g, r }) => itemHTML(g, r, `<b>${Math.round(r.uscite * 100)}</b><small>su 100</small>`)).join("") : `<p class="muted">Nessuna previsione con grado per questo giorno.</p>`);
  else if (S.rt === "mk") box.innerHTML = `<div class="selhead"><h2>Mercato</h2><span class="small muted">${dlab(S.rday)}</span></div><div class="opnote"><b>In verifica.</b> Lato della lettura con valore di almeno il ${Math.round(VAL_MIN * 100)}% sulla miglior quota. Il modello basket è verificato sui risultati ma non ancora contro le quote (archiviate dal 15/11/2026): i valori molto alti vanno letti con prudenza. Le linee arrivano il giorno prima e il giorno della partita.</div>` +
    (mk.length ? mk.map(({ g, r }) => itemHTML(g, r, `<b class="vgood">+${Math.round(r.ev * 100)}%</b><small>equa ${f2(r.fair)}</small>`)).join("") : `<p class="muted">Nessun valore sulle linee disponibili.</p>`);
  else box.innerHTML = `<div class="selhead"><h2>Operatività</h2><span class="small muted">${dlab(S.rday)}</span></div><div class="opnote"><b>In osservazione, senza peso.</b> Le quote basket si archiviano dal 15/11/2026: finché il registro non dice se il valore è reale contro le quote, nessuna puntata. Giocate dal lato della lettura, grado B o meglio, valore positivo.</div>` +
    (op.length ? op.map(({ g, r }) => itemHTML(g, r, `<b>${r.ev >= 0 ? "+" : ""}${Math.round(r.ev * 100)}%</b><small>senza peso</small>`)).join("") : `<p class="muted">Nessuna giocata in osservazione per questo giorno.</p>`);
  bindRows(box);
}
/* Segnali */
function renderSeg() {
  const t0 = todayIso(), want = new Set([...S.sw].filter(k => k !== "r").map(k => addDays(t0, +k)));
  document.querySelectorAll("#sigWhen [data-sw]").forEach(b => b.setAttribute("aria-pressed", String(S.sw.has(b.dataset.sw))));
  const G = games().filter(g => !fin(g) && !live(g) && g.day >= t0 && (want.has(g.day) || (S.sw.has("r") && g.day <= addDays(t0, 4))) && (S.slg === "all" || g.lg === S.slg));
  const rows = G.flatMap(g => { const R = reading(g); return R ? R.R.filter(r => r.uscite != null && r.uscite >= 0.72).map(r => ({ g, r })) : []; }).sort((a, b) => b.r.uscite - a.r.uscite || b.r.p - a.r.p);
  const sel = $("#sigLeague"); if (!sel.options.length) { sel.innerHTML = `<option value="all">Tutti</option>` + LG_ORD.map(lg => `<option value="${lg}">${esc(B.leghe[lg][0])}</option>`).join(""); sel.addEventListener("change", () => { S.slg = sel.value; renderSeg(); }); }
  $("#sigOut").innerHTML = `<div class="selhead"><h2>${rows.length} segnali</h2></div>` + (rows.length ? rows.map(({ g, r }) => `<button type="button" class="sigrow" data-gid="${esc(g.id)}"><span class="sigp"><b>${Math.round(r.uscite * 100)}%</b>${gbadge(r.g)}</span>
      <span class="sigt"><b>${esc(team(g.lg, g.h)[0])} – ${esc(team(g.lg, g.a)[0])}</b><span>${esc(r.lab)}${r.q ? ` · @${f2(r.q)}` : ""}</span><small>${FL[g.lg] || ""} ${esc(B.leghe[g.lg][0])} · ${dlab(g.day)} ${timeOf(g.d)} · Prevista ${pc(r.p)}</small></span></button>`).join("")
    : `<p class="muted">Nessun segnale con questi filtri${S.sw.has("r") ? "" : ": prova Giornata"}.</p>`);
  bindRows($("#sigOut"));
}
/* Tendenze */
function renderTen() {
  const T = B.tendenze;
  $("#genOut").innerHTML = `<h2>Tendenze · stagione in corso</h2>` + LG_ORD.filter(lg => T[lg]).map(lg => { const t = T[lg];
    return `<div class="card tcard"><h3>${FL[lg] || ""} ${esc(B.leghe[lg][0])} <small>${t.partite} partite</small></h3><div class="tgrid">
      <div><b>${f1(t.media_punti)}</b><small>punti a partita</small></div><div><b>${pc(t.casa_vince)}</b><small>vince la squadra di casa</small></div>
      <div><b>${f1(t.scarto_medio)}</b><small>scarto medio</small></div><div><b>${pc(t.supplementari)}</b><small>ai supplementari</small></div>
      <div><b>${t.max_punti}</b><small>totale più alto</small></div><div><b>${t.min_punti}</b><small>totale più basso</small></div></div></div>`; }).join("");
}
/* Digiuni (serie aperte) */
function renderDig() {
  const K = [["vittorie", "Vittorie consecutive"], ["sconfitte", "Sconfitte consecutive"], ["vittorie_casa", "Vittorie in casa di fila"], ["sconfitte_trasferta", "Sconfitte in trasferta di fila"],
    ["sopra_media", "Partite sopra la media punti del campionato"], ["sotto_media", "Partite sotto la media punti del campionato"]];
  const chips = [["all", "Tutti"], ...LG_ORD.map(lg => [lg, B.leghe[lg][0]])];
  $("#ritOut").innerHTML = `<h2>Serie aperte</h2><div class="self">${chips.map(([c, n]) => `<button type="button" class="chip" data-dlg="${c}" aria-pressed="${S.dlg === c}">${esc(n)}</button>`).join("")}</div>` +
    K.map(([k, lab]) => { const L = Object.entries(B.serie).filter(([key]) => S.dlg === "all" || key.startsWith(S.dlg + "|")).map(([key, v]) => ({ lg: key.split("|")[0], id: key.split("|")[1], n: v[k] })).filter(x => x.n >= 3).sort((a, b) => b.n - a.n).slice(0, 8);
      return `<div class="card"><h3>${lab}</h3>${L.length ? `<table class="bkt2"><tbody>${L.map(x => `<tr><td>${logo(x.lg, x.id)}${esc(team(x.lg, x.id)[0])} <small class="muted">${esc(B.leghe[x.lg][0])}</small></td><td class="num"><b>${x.n}</b></td></tr>`).join("")}</tbody></table>` : `<p class="small muted">Nessuna serie di almeno 3.</p>`}</div>`; }).join("");
  document.querySelectorAll("#ritOut [data-dlg]").forEach(b => b.addEventListener("click", () => { S.dlg = b.dataset.dlg; renderDig(); }));
}
/* ---------- avvio ---------- */
function wire() {
  $("#navStats").addEventListener("click", () => show("part"));
  $("#navSel").addEventListener("click", () => show("radar"));
  $("#navSig").addEventListener("click", () => show("seg"));
  $("#navGen").addEventListener("click", () => show("ten"));
  $("#navRit").addEventListener("click", () => show("dig"));
  $("#back").addEventListener("click", () => show("part"));
  document.querySelectorAll("#viewMatch .mtab").forEach(b => b.addEventListener("click", () => { S.mt = b.dataset.mt; renderMatch(); }));
  document.querySelectorAll("#selTabs [data-rt]").forEach(b => b.addEventListener("click", () => { S.rt = b.dataset.rt; renderRadar(); }));
  document.querySelectorAll("#sigWhen [data-sw]").forEach(b => b.addEventListener("click", () => { const k = b.dataset.sw; if (S.sw.has(k)) S.sw.delete(k); else S.sw.add(k); renderSeg(); }));
  
}
(async () => {
  wire();
  try {
    const st = await fetch("data/stato.json", { cache: "no-store" }).then(r => r.json()).catch(() => null);
    const v = st && st.v && st.v.basket ? st.v.basket : Date.now();
    B = await fetch("data/basket.json?v=" + v, { cache: "no-cache" }).then(r => r.json());
  } catch (e) { $("#boot").innerHTML = `<p class="muted">Dati del basket non disponibili in questo momento.</p>`; return; }
  try { localStorage.setItem("prevista.sport", "basket"); } catch (e) {}
  $("#boot").hidden = true; $("#stamp").textContent = `Aggiornato ${B.agg.slice(8, 10)}/${B.agg.slice(5, 7)} ${B.agg.slice(11)} UTC`;
  show("part");
})();
