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
const S = { sv: "sq", view: "part", day: null, game: null, mt: "prev", rt: "gr", rday: null, sw: new Set(["0", "1"]), slg: "all", tlg: "all", dlg: "all" };

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
function show(v, push = true) {   // 15/11/2026: ogni vista entra nella cronologia, così il tasto indietro del telefono resta nel basket
  if (push && (S.view !== v || v === "match")) { try { history.pushState({ v, game: S.game, mt: S.mt }, ""); } catch (e) {} }
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
function rowHTML(g) {   // 15/11/2026 (Denny): in Partite solo il risultato reale, niente previsioni
  const tm = fin(g) ? "Finale" : live(g) ? "In corso" : timeOf(g.d);
  const sc = (x, y) => fin(g) ? `<b>${x}</b>` : "<b></b>";
  return `<button type="button" class="mrow" data-gid="${esc(g.id)}">
    <span class="tmc"><span class="tm${fin(g) ? " fin" : ""}">${tm}</span></span>
    <span class="tt"><span class="${fin(g) && g.sh[5] > g.sa[5] ? "w" : ""}">${logo(g.lg, g.h)}${esc(team(g.lg, g.h)[0])}</span>${sc(g.sh && g.sh[5])}
    <span class="${fin(g) && g.sa[5] > g.sh[5] ? "w" : ""}">${logo(g.lg, g.a)}${esc(team(g.lg, g.a)[0])}</span>${sc(g.sa && g.sa[5])}</span></button>`;
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
  box.innerHTML = sum + LG_ORD.filter(lg => G.some(g => g.lg === lg)).map(lg => lgBlock(lg, G.filter(g => g.lg === lg).sort((a, b) => a.d.localeCompare(b.d)), false)).join("");   // 15/11: campionati chiusi all'avvio
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
  // Lettura (15/11/2026, Denny: come il calcio, solo i numeri della previsione, niente percentuali né spiegazioni)
  const ini = t => t.split(/\s+/).filter(w => w.length > 2).map(w => w[0]).join("").slice(0, 3).toUpperCase() || t.slice(0, 3).toUpperCase();
  const badge = id => { const t = team(g.lg, id); return t[1] ? `<span class="bdg lg"><img src="${esc(t[1])}" alt="" referrerpolicy="no-referrer" onerror="this.parentElement.classList.remove('lg');this.parentElement.textContent='${esc(ini(t[0])).replace(/'/g, "")}'"></span>` : `<span class="bdg">${esc(ini(t[0]))}</span>`; };
  const real = fin(g), st = g.stat && g.stat.h && g.stat.a ? g.stat : null, ok = x => x != null && isFinite(x);
  const nd = `<span class="nd">—</span>`;
  const rowP = (lab, h, a, t, rh, ra) => {   // con la partita giocata: numero grande = reale, sotto la previsione
    if (real && ok(rh) && ok(ra)) { const hi = rh > ra ? "h" : rh < ra ? "a" : "";
      const cell = (rv, pv, top) => `<span class="sx-v pl${top ? " top" : ""}"><b class="rv">${rv}</b>${ok(pv) ? `<small class="pv">prev. ${f1(pv)}</small>` : ""}</span>`;
      return `<div class="sx-r">${cell(rh, h, hi === "h")}<span class="sx-m"><small>${lab}</small><b>${rh + ra}</b>${ok(t) ? `<small class="pv">prev. ${f1(t)}</small>` : ""}</span>${cell(ra, a, hi === "a")}</div>`; }
    if (!ok(t)) return "";
    const hi = ok(h) && ok(a) && Math.abs(h - a) > 0.05 ? (h > a ? "h" : "a") : "";
    return `<div class="sx-r"><span class="sx-v${hi === "h" ? " top" : ""}">${ok(h) ? f1(h) : nd}</span><span class="sx-m"><small>${lab}</small><b>${f1(t)}</b></span><span class="sx-v${hi === "a" ? " top" : ""}">${ok(a) ? f1(a) : nd}</span></div>`; };
  const BK = S.bk && !!R && R.R.some(r => r.q);
  let body = "";
  if (!p) body = `<p class="bk-none">Previsione non disponibile: poche partite delle squadre nella stagione.</p>`;
  else if (BK) body = R.R.filter(r => r.q).map(r => `<div class="sx-r"><span class="sx-v pl"><b class="rv">${f2(r.q)}</b><small class="pv">${esc(r.bk || "")}</small></span><span class="sx-m"><small>${esc(r.lab)}</small><b>${f2(r.fair)}</b><small class="pv">quota equa</small></span><span class="sx-v pl${r.ev >= VAL_MIN ? " top" : ""}"><b class="rv${r.ev >= VAL_MIN ? " vgood" : ""}">${r.ev >= 0 ? "+" : ""}${Math.round(r.ev * 100)}%</b><small class="pv">valore</small></span></div>`).join("") + `<p class="sx-fb">Quote solo informative, 18+.</p>`;
  else {
    const h1 = p.h1 || 0.5, ms = p.eh - p.ea;
    body = rowP("Punti", p.eh, p.ea, p.eh + p.ea, real ? g.sh[5] : null, real ? g.sa[5] : null)
      + rowP("1° tempo", p.eh * h1, p.ea * h1, (p.eh + p.ea) * h1, real && g.sh[1] != null ? g.sh[0] + g.sh[1] : null, real && g.sa[1] != null ? g.sa[0] + g.sa[1] : null)
      + (() => { if (!real) return `<div class="sx-r"><span class="sx-v${ms > 0 ? " top" : ""}">${ms > 0 ? "+" + f1(ms) : nd}</span><span class="sx-m"><small>Scarto</small><b>${f1(Math.abs(ms))}</b></span><span class="sx-v${ms < 0 ? " top" : ""}">${ms < 0 ? "+" + f1(-ms) : nd}</span></div>`;
        const d = g.sh[5] - g.sa[5], cell = (rv, pv, top) => `<span class="sx-v pl${top ? " top" : ""}"><b class="rv">${rv > 0 ? "+" + rv : "—"}</b>${pv > 0 ? `<small class="pv">prev. +${f1(pv)}</small>` : ""}</span>`;
        return `<div class="sx-r">${cell(d, ms, d > 0)}<span class="sx-m"><small>Scarto</small><b>${Math.abs(d)}</b><small class="pv">prev. ${f1(Math.abs(ms))}</small></span>${cell(-d, -ms, d < 0)}</div>`; })()
      + `<div class="sx-r"><span class="sx-v">${ok(p.pch) ? f1(p.pch) : nd}</span><span class="sx-m"><small>Possessi</small><b>${f1(p.pace)}</b></span><span class="sx-v">${ok(p.pca) ? f1(p.pca) : nd}</span></div>`
      + rowP("Rimbalzi", p.rh, p.ra, ok(p.rh) ? p.rh + p.ra : null, st ? st.h[6] : null, st ? st.a[6] : null)
      + rowP("Falli", p.fh, p.fa, ok(p.fh) ? p.fh + p.fa : null, g.fl ? g.fl[0] : null, g.fl ? g.fl[1] : null)
      + [["Assist", "ast", 9], ["Triple", "tri", 2], ["Palle perse", "pp", 12]].map(([lab, k, i]) => { const x = p[k];
          return x ? rowP(lab, x[0], x[1], x[0] + x[1], st ? st.h[i] : null, st ? st.a[i] : null) : real && st ? rowP(lab, null, null, null, st.h[i], st.a[i]) : ""; }).join("");
  }
  const nq = R ? R.R.filter(r => r.q).length : 0;
  $("#mhead").innerHTML = `<div class="sx-band"><span class="flag" aria-hidden="true">${FL[g.lg] || "🏀"}</span><span class="nm"><small>${esc(B.leghe[g.lg][1])} · ${dlab(g.day)} · ${timeOf(g.d)}</small><b>${esc(B.leghe[g.lg][0])}</b></span></div>
    <div class="sx">
      <div class="sx-r sx-h">
        <span class="sx-t">${badge(g.h)}<b>${esc(team(g.lg, g.h)[0])}</b><small>${ph ? `${ph.pos}° · ${ph.w}-${ph.l}` : "&nbsp;"}</small></span>
        <span class="sx-m sx-c">${nq ? `<button class="hsw${BK ? " on" : ""}" type="button" id="bkSw" role="switch" aria-checked="${BK}" aria-label="Passa da Modello a Mercato"><span class="hsw-t" aria-hidden="true"><i></i></span><span class="hsw-l">${BK ? "Mercato" : "Modello"}</span></button>` : ""}${real ? `<b class="scr">${g.sh[5]} – ${g.sa[5]}</b><small>${(g.sh[4] || 0) + (g.sa[4] || 0) > 0 ? "Finale d.t.s." : "Finale"}</small>` : live(g) ? `<b>VS</b><small>In corso</small>` : `<b>VS</b><small>${timeOf(g.d)}</small>`}</span>
        <span class="sx-t">${badge(g.a)}<b>${esc(team(g.lg, g.a)[0])}</b><small>${pa ? `${pa.pos}° · ${pa.w}-${pa.l}` : "&nbsp;"}</small></span>
      </div>${body}
    </div>`;
  const sw = $("#bkSw"); if (sw) sw.addEventListener("click", () => { S.bk = !S.bk; renderMatch(); });
  // Grado (15/11/2026, Denny: come il calcio)
  const GW = { "A+": "Ottima", A: "Molto buona", B: "Buona", C: "Discreta" }, GC = { "A+": "c-ap", A: "c-a", B: "c-b", C: "c-c" };
  const gTitle = r => r.k === "vittoria" ? `Vittoria ${r.lab.replace(/^Vince /, "")}` : r.k === "totale" ? `${r.lab}` : `Handicap ${r.lab}`;
  const gSub = r => r.k === "vittoria" ? `Vincente ${r.sh} (supplementari compresi)` : r.k === "totale" ? `Totale punti · ${r.book ? "linea dei book" : "linea del modello"}` : "Handicap · linea dei book";
  const gWhy = r => `<div class="gnums small"><span class="gck ok"><i>✓</i>Base: ${r.n} previsioni simili nelle stagioni 2024-25 e 2025-26, partite che il modello non aveva visto</span>${r.q ? `<span class="gck ${r.ev >= 0 ? "ok" : "ko"}"><i>${r.ev >= 0 ? "✓" : "✗"}</i>Quota ${f2(r.q)} contro equa ${f2(r.fair)}</span>` : ""}</div>`;
  const GR = R ? R.R.filter(r => r.g).sort((x, y) => y.uscite - x.uscite) : [];
  if (!GR.length) $("#mgrado").innerHTML = `<h2>Grado</h2><p class="gintro">Nessuna previsione di questa partita ha un grado: previsioni simili nelle stagioni passate sono uscite meno di 56 volte su 100.</p>`;
  else { const t = GR[0], dots = Math.round(t.uscite * 10);
    $("#mgrado").innerHTML = `<h2>Grado</h2>
    <p class="gintro">Quanto ci si può fidare di ogni previsione, in base a come sono andate previsioni simili nelle stagioni passate.</p>
    <div class="gtop ${GC[t.g]}"><small class="gk">La previsione più affidabile</small><b class="gq">${esc(gTitle(t))}</b><small class="muted">${esc(gSub(t))}</small>
      <div class="gline"><span class="ccls ${GC[t.g]} gbig">${t.g}</span><span class="gword">${GW[t.g]}</span><span class="gdots ${GC[t.g]}" role="img" aria-label="${dots} su 10">${Array.from({ length: 10 }, (_, i) => `<i class="${i < dots ? "on" : ""}"></i>`).join("")}</span></div>
      <p class="gsay">Previsioni come questa sono uscite <b>${Math.round(t.uscite * 100)} volte su 100</b>.</p>
      <details class="gmore"><summary>Perché questo grado</summary>${gWhy(t)}</details></div>
    <div class="gscale" aria-label="Scala del Grado"><span><span class="ccls c-ap">A+</span>Ottima</span><span><span class="ccls c-a">A</span>Molto buona</span><span><span class="ccls c-b">B</span>Buona</span><span><span class="ccls c-c">C</span>Discreta</span></div>
    <h3 class="gh">Tutte le previsioni della partita</h3>
    <div class="glist">${GR.map(r => `<details class="gitem"><summary><span class="gil"><b>${esc(gTitle(r))}</b><small class="muted">${esc(gSub(r))}</small></span><span class="gir"><span class="ccls ${GC[r.g]}">${r.g}</span><span class="gin"><b class="num">${Math.round(r.uscite * 100)}</b> su 100</span></span></summary>${gWhy(r)}</details>`).join("")}</div>
    <p class="small muted" style="margin:0">Tocca una previsione per vedere perché ha quel grado.</p>`; }
  const U = id => (B.ultime[`${g.lg}|${id}`] || []).slice().reverse().slice(0, 10);
  const swapSt = r => { const x = r.slice(5); const o = []; for (let i = 0; i < x.length; i += 2) o.push(x[i + 1], x[i]); return o; };
  // Precedenti (come il calcio): ultime partite delle due squadre (Generale / Casa-Trasferta) e scontri diretti, con le statistiche
  const STL = (x, o) => { const v = (i, lab) => x[o + i] != null && x[o + i + 1] != null ? `${lab} ${x[o + i]}-${x[o + i + 1]}` : null;
    return [v(10, "1°T"), v(0, "Rimb"), v(2, "Ass"), v(4, "Tri"), v(6, "PP"), v(8, "Falli")].filter(Boolean).map(t => `<span class="nw">${t}</span>`).join(" · "); };
  const avgTot = (B.tendenze[g.lg] || {}).media_punti;
  const hmRow = (d, hId, aId, hp, ap, meHome, stl, res) => `<div class="hm"><span class="dt">${d.slice(8, 10)}/${d.slice(5, 7)}.${d.slice(2, 4)}</span>
    <span class="tm2"><span class="${meHome === 1 ? "me" : ""}">${esc(team(g.lg, hId)[0])}</span><b>${hp}</b><span class="${meHome === 0 ? "me" : ""}">${esc(team(g.lg, aId)[0])}</span><b>${ap}</b></span>
    ${res ? `<span class="rb ${res}">${res}</span>` : "<span></span>"}<span class="st">${stl}</span></div>`;
  const hsum = L => { const n = L.length, w = L.filter(x => x.w).length, ov = L.filter(x => avgTot && x.t > avgTot).length;
    return `<div class="hsum"><span>V-P <b>${w}-${n - w}</b></span><span>Punti <b>${f1(L.reduce((a, x) => a + x.pf, 0) / (n || 1))}-${f1(L.reduce((a, x) => a + x.pa, 0) / (n || 1))}</b></span>${avgTot ? `<span>Sopra ${lnum(avgTot.toFixed(1))} <b>${ov}/${n}</b></span>` : ""}</div>`; };
  const block = (title, rows) => { if (!rows.length) return `<section class="card hh"><h3>${title}</h3><p class="small muted">Nessuna partita.</p></section>`;
    const vis = rows.slice(0, 5).map(r => r.html).join(""), more = rows.slice(5);
    return `<section class="card hh"><h3>${title}</h3>${hsum(rows)}${vis}${more.length ? `<div class="hmore" hidden>${more.map(r => r.html).join("")}</div><button class="morebtn" type="button" data-l="Mostra altre (${more.length})">Mostra altre (${more.length}) <span class="chv" aria-hidden="true"></span></button>` : ""}</section>`; };
  const ult = (id, side) => U(id).filter(r => S.hv !== "venue" || r[2] === (side === "h" ? 1 : 0)).map(r => { const w = r[3] > r[4];
    return { w, pf: r[3], pa: r[4], t: r[3] + r[4], html: hmRow(r[0], r[2] ? id : r[1], r[2] ? r[1] : id, r[2] ? r[3] : r[4], r[2] ? r[4] : r[3], r[2] ? 1 : 0, STL(r, 5) && r[2] ? STL(r, 5) : STL(swapSt(r), 0), w ? "V" : "P") }; });
  const PRx = (B.precedenti[g.id] || []).slice().reverse().map(x => { const hw = x[1] === g.h ? x[3] > x[4] : x[4] > x[3];
    return { w: hw, pf: x[1] === g.h ? x[3] : x[4], pa: x[1] === g.h ? x[4] : x[3], t: x[3] + x[4], html: hmRow(x[0], x[1], x[2], x[3], x[4], x[1] === g.h ? 1 : 0, STL(x, 5), hw ? "V" : "P") }; });
  $("#mh2h").innerHTML = `<div class="seg" role="group" aria-label="Filtro partite"><button type="button" class="segb" data-hv="all" aria-pressed="${S.hv !== "venue"}">Generale</button><button type="button" class="segb" data-hv="venue" aria-pressed="${S.hv === "venue"}">Casa / Trasferta</button></div>
    <div class="h2hlist">${block(`Ultime partite: ${esc(team(g.lg, g.h)[0])}${S.hv === "venue" ? " in casa" : ""}`, ult(g.h, "h"))}${block(`Ultime partite: ${esc(team(g.lg, g.a)[0])}${S.hv === "venue" ? " in trasferta" : ""}`, ult(g.a, "a"))}${block("Scontri diretti", PRx)}</div>`;
  $("#mh2h").querySelectorAll("[data-hv]").forEach(b => b.addEventListener("click", () => { S.hv = b.dataset.hv; renderMatch(); }));
  $("#mh2h").querySelectorAll(".morebtn").forEach(b => b.addEventListener("click", () => { const m = b.previousElementSibling; m.hidden = !m.hidden; b.innerHTML = m.hidden ? `${b.dataset.l} <span class="chv" aria-hidden="true"></span>` : `Mostra meno <span class="chv up" aria-hidden="true"></span>`; }));
  // Classifica
  const C = B.classifica[g.lg] || [];
  $("#mtab").innerHTML = `<h2>Classifica · ${esc(B.leghe[g.lg][0])}</h2><table class="bkt2 cls"><thead><tr><th>#</th><th>Squadra</th><th>G</th><th>V</th><th>P</th><th>Diff.</th></tr></thead><tbody>${C.map((r, i) => `<tr class="${r[0] === g.h || r[0] === g.a ? "hl" : ""}"><td>${i + 1}</td><td>${logo(g.lg, r[0])}${esc(team(g.lg, r[0])[0])}</td><td class="num">${r[1]}</td><td class="num">${r[2]}</td><td class="num">${r[3]}</td><td class="num">${sg(r[4] - r[5]).replace(",0", "")}</td></tr>`).join("")}</tbody></table>`;
  // Rendimento (come il calcio): classifica del campionato su una statistica, in casa (squadra di casa) o in trasferta
  const RK = [["pts", "Punti"], ["h1", "Punti 1° tempo"], ["reb", "Rimbalzi"], ["ast", "Assist"], ["tre", "Triple"], ["pp", "Palle perse"], ["fl", "Falli"]];
  const RDl = (B.rendimento || {})[g.lg] || {}, ven = S.rv || "home", rk = S.rk || "pts";
  const has = k => Object.values(RDl).some(t => t[ven] && t[ven][k] && t[ven][k][3]);
  const rows = Object.entries(RDl).map(([id, t]) => { const c = t[ven] && t[ven][rk]; return c && c[3] ? { id, f: c[0] / c[3], a: c[1] / c[3], w: c[2], n: c[3] } : null; }).filter(Boolean).sort((x, y) => y.f - x.f);
  const lgF = rows.reduce((a, r) => a + r.f * r.n, 0) / (rows.reduce((a, r) => a + r.n, 0) || 1), lgA = rows.reduce((a, r) => a + r.a * r.n, 0) / (rows.reduce((a, r) => a + r.n, 0) || 1);
  const me = ven === "home" ? g.h : g.a;
  $("#mrend").innerHTML = `<section class="card mtrend"><h2>Rendimento · ${esc(B.leghe[g.lg][0])}</h2>
    <div class="mtrc"><label for="bkMk" class="sr">Statistica</label><select id="bkMk">${RK.map(([k, n]) => `<option value="${k}"${k === rk ? " selected" : ""}>${n}</option>`).join("")}</select>
      <div class="seg" role="group" aria-label="Sede"><button type="button" class="segb" data-rv="home" aria-pressed="${ven === "home"}">Casa</button><button type="button" class="segb" data-rv="away" aria-pressed="${ven === "away"}">Trasferta</button></div></div>
    <div class="stdleg"><span class="mh">${esc(team(g.lg, g.h)[0])}${ven === "home" ? " · gioca in casa" : ""}</span><span class="ma">${esc(team(g.lg, g.a)[0])}${ven === "away" ? " · gioca in trasferta" : ""}</span></div>
    ${rows.length ? `<div class="lt lt2" role="table"><div class="lth" role="row"><span>#</span><span>Squadra</span><span>Fatti<em>media</em></span><span>Subiti<em>media</em></span><span>Sfide vinte<em>vinte/partite</em></span></div>
      ${rows.map((r, i) => `<div class="ltr${r.id === g.h ? " mh" : r.id === g.a ? " ma" : ""}" role="row"><span class="ltk">${i + 1}</span><span class="ltt">${esc(team(g.lg, r.id)[0])}</span><span class="lta"><b>${f1(r.f)}</b></span><span class="lta">${f1(r.a)}</span><span class="ltf"><b>${r.w}</b>/${r.n}</span></div>`).join("")}
      <div class="ltr ltavg" role="row"><span class="ltk"></span><span class="ltt">Campionato</span><span class="lta">${f1(lgF)}</span><span class="lta">${f1(lgA)}</span><span class="ltf">50%</span></div></div>` : `<p class="small muted">Dato non disponibile per questo campionato nella stagione in corso.</p>`}
    <p class="small muted">Partite ${ven === "home" ? "in casa" : "in trasferta"} della stagione in corso. Sfide vinte: partite in cui la squadra ne ha fatti più dell'avversaria.</p></section>`;
  $("#bkMk").addEventListener("change", e => { S.rk = e.target.value; renderMatch(); });
  $("#mrend").querySelectorAll("[data-rv]").forEach(b => b.addEventListener("click", () => { S.rv = b.dataset.rv; renderMatch(); }));
  void me;
  renderGio(g);
}
/* ---------- Giocatori (15/11/2026): probabilità con la binomiale negativa, stessi parametri dell'harness (B.giocatori.gpar) ---------- */
function nbSf(mu, line, fp) {   // P(X > line)
  mu = Math.max(mu, 0.05); let r, p;
  if (fp[0] === "nb1") { r = mu / (fp[1] - 1); p = 1 / fp[1]; } else { r = fp[1]; p = r / (r + mu); }
  const k = Math.floor(line); let pmf = Math.pow(p, r), cdf = pmf;
  for (let i = 1; i <= k; i++) { pmf *= (i - 1 + r) / i * (1 - p); cdf += pmf; }
  return Math.max(0, Math.min(1, 1 - cdf));
}
const GL = { pts: [9.5, 14.5, 19.5, 24.5, 29.5], reb: [3.5, 5.5, 7.5, 9.5, 11.5], ast: [2.5, 4.5, 6.5, 8.5] };
const GN = { pts: "Punti", reb: "Rimbalzi", ast: "Assist", pa: "Punti + Assist" };
const thr = x => `${Math.ceil(x)}+`;
function plStats(r) {   // r = [nome, id, minuti, punti, rimbalzi, assist, assenza, quote]
  const gp = B.giocatori.gpar, mu = { pts: r[3], reb: r[4], ast: r[5], pa: r[3] + r[5] };
  const p10 = k => nbSf(mu[k], 9.5, gp[k]), a = p10("pts"), b = p10("reb"), c = p10("ast");
  const il = z => 1 / (1 + Math.exp(-z)), lg = p => { p = Math.min(Math.max(p, 1e-6), 1 - 1e-6); return Math.log(p / (1 - p)); };
  const dd0 = a * b + a * c + b * c - 2 * a * b * c, td0 = a * b * c;
  return { mu, dd: il(gp.dd[0] + gp.dd[1] * lg(dd0)), td: il(gp.td[0] + gp.td[1] * lg(td0)) };
}
function plLines(r, X) {   // righe: soglie fisse + linea Punti+Assist del book (o del modello) + doppia/tripla
  const gp = B.giocatori.gpar, out = [], q = r[7] || {};
  for (const k of ["pts", "reb", "ast"]) for (const L of GL[k]) {
    const p = nbSf(X.mu[k], L, gp[k]); if (p < 0.03 || p > 0.985) continue;
    const bk = k === "pts" && q.pt && q.pt[String(Math.ceil(L))] ? q.pt[String(Math.ceil(L))] : null;
    out.push({ k, lab: `${GN[k]} ${thr(L)}`, p, q: bk ? bk[0] : null, book: bk ? bk[1] : null });
  }
  // linee Over/Under del book: Punti + Assist (Betano) e Rimbalzi ("Player Runs" di Betano); senza book, la linea del modello per P+A
  for (const [k, code] of [["pa", "pa"], ["reb", "rb"]]) {
    const LL = q[code] ? Object.keys(q[code]).map(Number) : [];
    if (!LL.length && k === "reb") continue;
    const L = LL.length ? LL.reduce((a, b) => Math.abs(b - X.mu[k]) < Math.abs(a - X.mu[k]) ? b : a) : Math.floor(X.mu.pa) + 0.5;
    const po = nbSf(X.mu[k], L, gp[k]), over = po >= 0.5, bq = q[code] && q[code][String(L)] ? q[code][String(L)][over ? "O" : "U"] : null;
    out.push({ k: k === "reb" ? "rbl" : "pa", lab: `${GN[k]} ${over ? "Over" : "Under"} ${lnum(L)}`, p: over ? po : 1 - po, q: bq ? bq[0] : null, book: bq ? bq[1] : null, line: !!LL.length });
  }
  out.push({ k: "dd", lab: "Doppia doppia", p: X.dd }); if (X.td >= 0.03) out.push({ k: "td", lab: "Tripla doppia", p: X.td });
  return out.map(o => ({ ...o, fair: 1 / o.p, ev: o.q ? o.p * o.q - 1 : null }));
}
const WHY = { 1: "mancava l'ultima partita", 2: "non quotato dai book" };
function teamPlayersHTML(g, side) {
  const G = B.giocatori && B.giocatori.partite[g.id]; const T = G && G[side]; if (!T) return "";
  const id = side === "h" ? g.h : g.a, absent = T.g.filter(r => r[6]);
  return `<div class="card gteam"><h3>${logo(g.lg, id)}${esc(team(g.lg, id)[0])}</h3>
    ${absent.length ? `<p class="gnote">Assenti in automatico: ${absent.map(r => `<b>${esc(r[0])}</b> (${WHY[r[6]]})`).join(", ")} → gli altri salgono (punti +${Math.round(T.miss.pts * B.giocatori.gpar.beta.pts * 100)}%, rimbalzi +${Math.round(T.miss.reb * B.giocatori.gpar.beta.reb * 100)}%, assist +${Math.round(T.miss.ast * B.giocatori.gpar.beta.ast * 100)}%).</p>` : `<p class="gnote">Nessun abituale assente all'ultima partita${T.ultima ? ` (${dlab(T.ultima)})` : ""}.</p>`}
    <div class="ghd"><span style="text-align:left">Giocatore · minuti</span><span>Pt</span><span>Rb</span><span>As</span><span>P+A</span><span>DD</span></div>
    ${T.g.map(r => { const X = plStats(r);
      if (r[6]) return `<details class="gpl out"><summary><b>${esc(r[0])}<span class="gtag">${r[6] === 2 ? "non quotato" : "assente"}</span><small>${f1(r[2])} min · ${WHY[r[6]]}</small></b><span>—</span><span>—</span><span>—</span><span>—</span><span>—</span></summary></details>`;
      const L = plLines(r, X);
      return `<details class="gpl"><summary><b>${esc(r[0])}<small>${f1(r[2])} min</small></b><span>${f1(X.mu.pts)}</span><span>${f1(X.mu.reb)}</span><span>${f1(X.mu.ast)}</span><span>${f1(X.mu.pa)}</span><span>${pc(X.dd)}</span></summary>
        <div class="gdet"><table><thead><tr><th>Mercato</th><td>Prevista</td><td>Equa</td><td>Book</td><td>Valore</td></tr></thead><tbody>${L.map(o => `<tr class="${o.p >= 0.72 ? "hi" : ""}"><th>${esc(o.lab)}</th><td>${pc(o.p)}</td><td>${f2(o.fair)}</td><td>${o.q ? `${f2(o.q)} <small>${esc(o.book)}</small>` : "—"}</td><td>${o.ev != null && o.p >= 0.5 ? `<span class="${o.ev >= VAL_MIN ? "vgood" : ""}">${o.ev >= 0 ? "+" : ""}${Math.round(o.ev * 100)}%</span>` : "—"}</td></tr>`).join("")}</tbody></table></div></details>`; }).join("")}
  </div>`;
}
function renderGio(g) {
  const G = B.giocatori && B.giocatori.partite[g.id];
  $("#mgio").innerHTML = G ? `<section class="card"><h2>Giocatori</h2><p class="small muted">Valori attesi oggi (tocca un giocatore per probabilità e quota equa = 100 / probabilità). Media al minuto × minuti medi, ancorata a punti e ritmo che Prevista si aspetta dalla squadra; chi mancava all'ultima partita (o, in NBA, una stella non quotata dai book) è assente e il suo peso passa ai compagni. Verificato sulle stagioni passate (punti e assist z −10, doppia doppia calibrata). In verde le probabilità da 72% in su. Quote solo informative, 18+.</p></section>` + teamPlayersHTML(g, "h") + teamPlayersHTML(g, "a")
    : `<section class="card"><h2>Giocatori</h2><p class="muted">Giocatori disponibili per le partite dei prossimi 3 giorni con abbastanza storico nel campionato.</p></section>`;
}
function playerEntries(G) {   // per Segnali e Mercato: righe giocatore di tutte le partite indicate
  const out = [];
  for (const g of G) { const P = B.giocatori && B.giocatori.partite[g.id]; if (!P) continue;
    for (const side of ["h", "a"]) for (const r of (P[side] ? P[side].g : [])) { if (r[6]) continue; const X = plStats(r);
      for (const o of plLines(r, X)) out.push({ g, side, r, o }); } }
  return out;
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
  const mkp = playerEntries(games().filter(g => g.day === S.rday && !fin(g) && !live(g))).filter(x => x.o.q && x.o.p >= 0.5 && x.o.ev >= VAL_MIN).sort((a, b) => b.o.ev - a.o.ev);
  const op = I.flatMap(({ g, R }) => R.R.filter(r => r.q && r.ev > 0 && r.g && r.g !== "C").map(r => ({ g, r }))).sort((a, b) => b.r.ev - a.r.ev);
  $("#rtA").textContent = gr.length || ""; $("#rtB").textContent = (mk.length + mkp.length) || ""; $("#rtO").textContent = op.length || "";
  document.querySelectorAll("#selTabs [data-rt]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.rt === S.rt)));
  const box = $("#selOut");
  if (S.rt === "gr") box.innerHTML = `<div class="selhead"><h2>Grado</h2><span class="small muted">${dlab(S.rday)}</span></div>` + (gr.length ? gr.map(({ g, r }) => itemHTML(g, r, `<b>${Math.round(r.uscite * 100)}</b><small>su 100</small>`)).join("") : `<p class="muted">Nessuna previsione con grado per questo giorno.</p>`);
  else if (S.rt === "mk") box.innerHTML = `<div class="selhead"><h2>Mercato</h2><span class="small muted">${dlab(S.rday)}</span></div><div class="opnote"><b>In verifica.</b> Lato della lettura con valore di almeno il ${Math.round(VAL_MIN * 100)}% sulla miglior quota. Il modello basket è verificato sui risultati ma non ancora contro le quote (archiviate dal 15/11/2026): i valori molto alti vanno letti con prudenza. Le linee arrivano il giorno prima e il giorno della partita.</div>` +
    (mk.length ? mk.map(({ g, r }) => itemHTML(g, r, `<b class="vgood">+${Math.round(r.ev * 100)}%</b><small>equa ${f2(r.fair)}</small>`)).join("") : `<p class="muted">Nessun valore sulle linee disponibili.</p>`) +
    `<div class="selhead" style="margin-top:14px"><h2>Giocatori</h2><span class="small muted">quote dei book nel feed (NBA)</span></div>` +
    (mkp.length ? mkp.map(({ g, r, o }) => itemHTML(g, { lab: `${r[0]} · ${o.lab}`, q: o.q }, `<b class="vgood">+${Math.round(o.ev * 100)}%</b><small>Prevista ${pc(o.p)} · equa ${f2(o.fair)}</small>`)).join("") : `<p class="muted">Nessun valore sulle quote giocatori disponibili (oggi le passano solo Bet365 e Betano sull'NBA: soglie punti e punti + assist).</p>`);
  else box.innerHTML = `<div class="selhead"><h2>Operatività</h2><span class="small muted">${dlab(S.rday)}</span></div><div class="opnote"><b>In osservazione, senza peso.</b> Le quote basket si archiviano dal 15/11/2026: finché il registro non dice se il valore è reale contro le quote, nessuna puntata. Giocate dal lato della lettura, grado B o meglio, valore positivo.</div>` +
    (op.length ? op.map(({ g, r }) => itemHTML(g, r, `<b>${r.ev >= 0 ? "+" : ""}${Math.round(r.ev * 100)}%</b><small>senza peso</small>`)).join("") : `<p class="muted">Nessuna giocata in osservazione per questo giorno.</p>`);
  bindRows(box);
}
/* Segnali */
const SQK = [["vittoria", "Vincente"], ["totale", "Totale punti"], ["handicap", "Handicap"]];
const GIK = [["pts", "Punti"], ["rbl", "Rimbalzi"], ["ast", "Assist"], ["pa", "Punti + Assist"], ["dd", "Doppia doppia"]];
function renderSeg() {   // 15/11/2026 (Denny): come i Segnali del calcio
  const t0 = todayIso(), want = new Set([...S.sw].filter(k => k !== "r").map(k => addDays(t0, +k)));
  document.querySelectorAll("#sigWhen [data-sw]").forEach(b => b.setAttribute("aria-pressed", String(S.sw.has(b.dataset.sw))));
  document.querySelectorAll("#sigView [data-sv]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.sv === S.sv)));
  const sel = $("#sigLeague");
  if (!sel.options.length) { sel.innerHTML = `<option value="all">Tutti i campionati</option>` + LG_ORD.map(lg => `<option value="${lg}">${esc(B.leghe[lg][1])} · ${esc(B.leghe[lg][0])}</option>`).join(""); sel.addEventListener("change", () => { S.slg = sel.value; renderSeg(); }); }
  const K = S.sv === "gi" ? GIK : SQK; if (!S.sk) S.sk = {}; const on = k => S.sk[k] !== false;
  $("#sigStats").innerHTML = K.map(([k, n]) => `<button type="button" class="chip sstat" data-k="${k}" aria-pressed="${on(k)}">${n}</button>`).join("");
  $("#sigStats").querySelectorAll("[data-k]").forEach(b => b.addEventListener("click", () => { S.sk[b.dataset.k] = !on(b.dataset.k); renderSeg(); }));
  const G = games().filter(g => !fin(g) && !live(g) && g.day >= t0 && (want.has(g.day) || (S.sw.has("r") && g.day <= addDays(t0, 4))) && (S.slg === "all" || g.lg === S.slg));
  const when = g => `${dlab(g.day)} ${timeOf(g.d)} · ${esc(B.leghe[g.lg][0])}`;
  const sigHTML = (g, m, pct, q, tag, pick, det, w, mt) => `<div class="sig"><button type="button" class="sigopen" data-gid="${esc(g.id)}" data-mt="${mt}"><span class="m">${m}</span><span class="p num">${pct}${q ? `<small class="qsm">@${f2(q)}</small>` : ""}</span>
      <span class="d"><span class="stag">${tag}</span><b>${pick}</b>${det ? ` · ${det}` : ""}</span><span class="w">${w}</span></button></div>`;
  let L = [], intro = "";
  if (S.sv === "gi") {
    intro = "Giocatori: per ogni voce la soglia più alta che Prevista dà tra il 72% e l'80% (quota equa da 1,25 in su), oppure con la quota del book (NBA). Si annulla se il giocatore non entra.";
    const best = new Map();
    for (const x of playerEntries(G)) { const kk = x.o.k === "reb" ? "rbl" : x.o.k; if (!on(kk === "td" ? "dd" : kk) || x.o.p < 0.72 || (x.o.p > 0.8 && !x.o.q)) continue;
      const key = `${x.g.id}|${x.r[1]}|${x.o.k}`; const b = best.get(key); if (!b || (x.o.k !== "pa" && x.o.lab.localeCompare(b.o.lab, "it", { numeric: true }) > 0)) best.set(key, x); }
    L = [...best.values()].sort((a, b) => b.o.p - a.o.p).map(({ g, side, r, o }) => { const tag = o.k === "pts" ? "Punti" : o.k === "reb" || o.k === "rbl" ? "Rimbalzi" : o.k === "ast" ? "Assist" : o.k === "pa" ? "Punti + Assist" : o.k === "dd" ? "Doppia doppia" : "Tripla doppia";
      const pick = o.lab.replace(/^(Punti \+ Assist|Punti|Rimbalzi|Assist) /, ""), det = `equa ${f2(o.fair)}${o.book ? ` · ${esc(o.book)}` : ""}`;
      return sigHTML(g, `${esc(r[0])} <small class="muted">${esc(team(g.lg, side === "h" ? g.h : g.a)[0])}</small>`, pc(o.p), o.q, tag, esc(pick), det, `${esc(team(g.lg, g.h)[0])} – ${esc(team(g.lg, g.a)[0])} · ${when(g)}`, "gio"); });
  } else {
    intro = "Previsioni dalla parte della lettura che nelle stagioni passate sono uscite almeno 72 volte su 100 (grado A o A+). Vincente supplementari compresi; totale e handicap sulla linea dei book quando c'è.";
    const rows = G.flatMap(g => { const R = reading(g); return R ? R.R.filter(r => on(r.k) && r.uscite != null && r.uscite >= 0.72).map(r => ({ g, r, R })) : []; }).sort((a, b) => b.r.uscite - a.r.uscite || b.r.p - a.r.p);
    L = rows.map(({ g, r, R }) => { const p = g.p;
      const tag = r.k === "vittoria" ? "Vincente" : r.k === "totale" ? "Totale" : "Handicap";
      const pick = r.k === "vittoria" ? `${r.sh} · ${esc(team(g.lg, r.sh === "1" ? g.h : g.a)[0])}` : esc(r.lab.replace(/ punti$/, ""));
      const det = r.k === "vittoria" ? `punti previsti ${f1(p.eh)} – ${f1(p.ea)}` : r.k === "totale" ? `previsti ${f1(R.mt)} · ${r.book ? "linea dei book" : "linea del modello"}` : `scarto previsto ${f1(Math.abs(R.ms))}`;
      return sigHTML(g, `${esc(team(g.lg, g.h)[0])} – ${esc(team(g.lg, g.a)[0])}`, `${Math.round(r.uscite * 100)}%`, r.q, tag, pick, det, when(g), "prev"); });
  }
  $("#sigOut").innerHTML = `<h2>${L.length} segnal${L.length === 1 ? "e" : "i"}</h2><p class="small muted" style="margin:0">${intro}</p>` + (L.length ? `<div class="siglist">${L.join("")}</div>` : `<p class="muted">Nessun segnale con questi filtri${S.sw.has("r") ? "" : ": prova Giornata"}.</p>`);
  $("#sigOut").querySelectorAll(".sigopen").forEach(b => b.addEventListener("click", () => { S.game = b.dataset.gid; S.mt = b.dataset.mt; show("match"); }));
}
/* ---------- Tendenze e Digiuni (15/11/2026, Denny: come il calcio) ---------- */
// riga partita della squadra: [data, avversaria, casa 1/0, punti f, s, rimb f, s, ass f, s, triple f, s, palle perse f, s, falli f, s, 1°T f, s, stagione in corso 1/0]
const TMK = [
  ["vit", "Vittorie", r => r[3] > r[4], "vince", "non vince"],
  ["sop", "Totale sopra la media del campionato", (r, m) => m && r[3] + r[4] > m, "partita sopra la media punti", "non ha una partita sopra la media punti del campionato"],
  ["sot", "Totale sotto la media del campionato", (r, m) => m && r[3] + r[4] < m, "partita sotto la media punti", "non ha una partita sotto la media punti del campionato"],
  ["v10", "Vince di 10 o più", r => r[3] - r[4] >= 10, "vince di 10+", "non vince di 10 o più"],
  ["h1", "Vince il 1° tempo", r => r[15] != null ? r[15] > r[16] : null, "vince il 1° tempo", "non vince il 1° tempo"],
  ["reb", "Più rimbalzi dell'avversaria", r => r[5] != null ? r[5] > r[6] : null, "più rimbalzi", "non prende più rimbalzi dell'avversaria"],
  ["ast", "Più assist dell'avversaria", r => r[7] != null ? r[7] > r[8] : null, "più assist", "non fa più assist dell'avversaria"],
  ["tri", "Più triple dell'avversaria", r => r[9] != null ? r[9] > r[10] : null, "più triple", "non segna più triple dell'avversaria"],
  ["pp", "Meno palle perse dell'avversaria", r => r[11] != null ? r[11] < r[12] : null, "meno palle perse", "non perde meno palloni dell'avversaria"],
  ["fl", "Più falli dell'avversaria", r => r[13] != null ? r[13] > r[14] : null, "più falli", "non commette più falli dell'avversaria"]];
const tGames = (lg, id) => B.ultime[`${lg}|${id}`] || [];
const nextOf = (lg, id) => games().filter(g => g.lg === lg && !fin(g) && !live(g) && (g.h === id || g.a === id) && g.day >= todayIso()).sort((a, b) => a.d.localeCompare(b.d))[0];
function nextProb(k, g, id) {   // probabilità di Prevista sull'esito nella prossima partita (dove c'è un modello)
  const R = g && reading(g); if (!R) return null; const home = g.h === id, s = B.sigma[g.lg], avg = (B.tendenze[g.lg] || {}).media_punti;
  if (k === "vit") return { p: home ? R.pw : 1 - R.pw, lab: "vittoria" };
  if ((k === "sop" || k === "sot") && avg) { const po = 1 - Phi((avg - R.mt) / s[1]); return { p: k === "sop" ? po : 1 - po, lab: k === "sop" ? `sopra ${lnum(avg.toFixed(1))}` : `sotto ${lnum(avg.toFixed(1))}` }; }
  if (k === "v10") { const ms = home ? R.ms : -R.ms; return { p: 1 - Phi((9.5 - ms) / s[0]), lab: "+10" }; }
  return null;
}
function leanOf(k, g, id) {   // la Lettura va verso l'esito? (per i Digiuni)
  if (!g || !g.p) return null; const p = g.p, home = g.h === id;
  const np = nextProb(k, g, id); if (np) return np.p >= 0.5;
  if (k === "h1") return home ? p.eh > p.ea : p.ea > p.eh;
  if (k === "reb" && p.rh != null) return home ? p.rh > p.ra : p.ra > p.rh;
  if (k === "fl" && p.fh != null) return home ? p.fh > p.fa : p.fa > p.fh;
  return null;
}
const G_ = { lg: "all", mk: "vit", v: "tot", per: "s", w: "all", more: 10 };
function renderTen() {
  const sel = $("#genLg"), mk = $("#genMk");
  if (!sel.options.length) {
    sel.innerHTML = `<option value="all">Tutti i campionati</option>` + LG_ORD.map(lg => `<option value="${lg}">${esc(B.leghe[lg][1])} · ${esc(B.leghe[lg][0])}</option>`).join("");
    mk.innerHTML = TMK.map(([k, n]) => `<option value="${k}">${n}</option>`).join("");
    sel.addEventListener("change", () => { G_.lg = sel.value; G_.more = 10; renderTen(); }); mk.addEventListener("change", () => { G_.mk = mk.value; G_.more = 10; renderTen(); });
    for (const [box, key, attr] of [["#genVenue", "v", "gv"], ["#genPer", "per", "gp"], ["#genWhen", "w", "gw"]]) $(box).querySelectorAll("[data-" + attr + "]").forEach(b => b.addEventListener("click", () => { G_[key] = b.dataset[attr]; G_.more = 10; renderTen(); }));
  }
  sel.value = G_.lg; mk.value = G_.mk;
  for (const [box, key, attr] of [["#genVenue", "v", "gv"], ["#genPer", "per", "gp"], ["#genWhen", "w", "gw"]]) $(box).querySelectorAll("[data-" + attr + "]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset[attr] === G_[key])));
  const M = TMK.find(x => x[0] === G_.mk), t0 = todayIso(), wantDay = G_.w === "all" ? null : addDays(t0, +G_.w);
  const rows = [], lgRate = {};
  for (const lg of LG_ORD) { if (G_.lg !== "all" && lg !== G_.lg) continue; const avg = (B.tendenze[lg] || {}).media_punti; let ln = 0, ly = 0;
    for (const id of Object.keys(B.squadre[lg] || {})) {
      let L = tGames(lg, id).filter(r => r[17]);
      if (G_.v !== "tot") L = L.filter(r => r[2] === (G_.v === "home" ? 1 : 0));
      if (G_.per !== "s") L = L.slice(-(+G_.per));
      const ev = L.map(r => M[2](r, avg)).filter(x => x != null); ln += ev.length; ly += ev.filter(Boolean).length;
      if (ev.length < 3) continue;
      const nx = nextOf(lg, id); if (wantDay && (!nx || nx.day !== wantDay)) continue;
      rows.push({ lg, id, y: ev.filter(Boolean).length, n: ev.length, nx });
    }
    lgRate[lg] = ln ? ly / ln : null; }
  rows.sort((a, b) => b.y / b.n - a.y / a.n || b.n - a.n);
  const out = rows.slice(0, G_.more).map((r, i) => { const rate = r.y / r.n, lr = lgRate[r.lg], np = r.nx ? nextProb(G_.mk, r.nx, r.id) : null;
    return `<button type="button" class="grow${i < 3 ? " top" : ""}" data-gid="${r.nx ? esc(r.nx.id) : ""}">
      <span class="grk">${i + 1}</span><span class="gmain"><span class="gteam">${esc(team(r.lg, r.id)[0])}</span><span class="glg">${esc(B.leghe[r.lg][1])} · ${esc(B.leghe[r.lg][0])}</span></span>
      <span class="gval"><b>${r.y}/${r.n}</b><small>${Math.round(rate * 100)}%</small></span>
      <span class="gbar" aria-hidden="true"><i style="width:${rate * 100}%"></i>${lr != null ? `<u style="left:${lr * 100}%"></u>` : ""}</span>
      <span class="gref">${lr != null ? `Media campionato ${Math.round(lr * 100)}%` : ""}</span>
      ${r.nx ? `<span class="gnext">${r.nx.h === r.id ? "In casa con" : "In trasferta con"} <b>${esc(team(r.lg, r.nx.h === r.id ? r.nx.a : r.nx.h)[0])}</b> · ${dlab(r.nx.day)} ${timeOf(r.nx.d)}${np ? ` · <em>${esc(np.lab)} ${pc(np.p)}</em>` : ""}</span>` : ""}
    </button>`; }).join("");
  $("#genOut").innerHTML = (out || `<section class="card"><p class="muted">Nessuna squadra con almeno 3 partite per questo mercato e questi filtri.</p></section>`) + (rows.length > G_.more ? `<button type="button" class="genmore" id="genMore">Mostra altre ${Math.min(10, rows.length - G_.more)}</button>` : "");
  $("#genOut").querySelectorAll(".grow[data-gid]").forEach(b => b.addEventListener("click", () => { if (b.dataset.gid) { S.game = b.dataset.gid; S.mt = "prev"; show("match"); } }));
  const mb = $("#genMore"); if (mb) mb.addEventListener("click", () => { G_.more += 10; renderTen(); });
}
const D_ = { lg: "all", t: "all", gr: "all", v: "all", w: "all", dot: false, grd: false };
const DGR = [["all", "Tutte le statistiche"], ["ris", "Risultati", ["vit", "v10", "h1"]], ["pun", "Punti", ["sop", "sot"]], ["reb", "Rimbalzi", ["reb"]], ["ast", "Assist", ["ast"]], ["tri", "Triple", ["tri"]], ["pp", "Palle perse", ["pp"]], ["fl", "Falli", ["fl"]]];
function renderDig() {
  const sl = $("#ritLg"), st = $("#ritTeam"), sg_ = $("#ritGr");
  if (!sl.options.length) {
    sl.innerHTML = `<option value="all">Tutti i campionati</option>` + LG_ORD.map(lg => `<option value="${lg}">${esc(B.leghe[lg][1])} · ${esc(B.leghe[lg][0])}</option>`).join("");
    sg_.innerHTML = DGR.map(([k, n]) => `<option value="${k}">${n}</option>`).join("");
    sl.addEventListener("change", () => { D_.lg = sl.value; D_.t = "all"; renderDig(); }); st.addEventListener("change", () => { D_.t = st.value; renderDig(); }); sg_.addEventListener("change", () => { D_.gr = sg_.value; renderDig(); });
    $("#ritVen").querySelectorAll("[data-v]").forEach(b => b.addEventListener("click", () => { D_.v = b.dataset.v; renderDig(); }));
  }
  sl.value = D_.lg; sg_.value = D_.gr;
  st.disabled = D_.lg === "all"; st.innerHTML = `<option value="all">Tutte le squadre</option>` + (D_.lg === "all" ? "" : Object.entries(B.squadre[D_.lg] || {}).sort((a, b) => a[1][0].localeCompare(b[1][0])).map(([id, t]) => `<option value="${id}">${esc(t[0])}</option>`).join("")); st.value = D_.t;
  $("#ritVen").querySelectorAll("[data-v]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.v === D_.v)));
  $("#ritWhen").innerHTML = [["all", "Sempre"], ["0", "Oggi"], ["1", "Domani"]].map(([k, n]) => `<button type="button" class="chip" data-rw="${k}" aria-pressed="${D_.w === k}">${n}</button>`).join("") +
    `<button type="button" class="chip" id="ritDot" aria-pressed="${D_.dot}"><i aria-hidden="true"></i>Lettura</button><button type="button" class="chip" id="ritGrd" aria-pressed="${D_.grd}"><em class="ccls c-a" aria-hidden="true">A</em>Grado</button>`;
  $("#ritWhen").querySelectorAll("[data-rw]").forEach(b => b.addEventListener("click", () => { D_.w = b.dataset.rw; renderDig(); }));
  $("#ritDot").addEventListener("click", () => { D_.dot = !D_.dot; renderDig(); }); $("#ritGrd").addEventListener("click", () => { D_.grd = !D_.grd; renderDig(); });
  const allow = D_.gr === "all" ? null : new Set(DGR.find(x => x[0] === D_.gr)[2]), t0 = todayIso(), wantDay = D_.w === "all" ? null : addDays(t0, +D_.w);
  const items = [];
  for (const lg of LG_ORD) { if (D_.lg !== "all" && lg !== D_.lg) continue; const avg = (B.tendenze[lg] || {}).media_punti;
    for (const id of Object.keys(B.squadre[lg] || {})) { if (D_.t !== "all" && id !== D_.t) continue;
      let L = tGames(lg, id); if (D_.v !== "all") L = L.filter(r => r[2] === (D_.v === "home" ? 1 : 0)); if (!L.length) continue;
      const nx = nextOf(lg, id); if (wantDay && (!nx || nx.day !== wantDay)) continue;
      for (const [k, , f, , neg] of TMK) { if (allow && !allow.has(k)) continue;
        let n = 0; for (let i = L.length - 1; i >= 0; i--) { const e = f(L[i], avg); if (e == null) break; if (e) break; n++; }
        if (n < 4) continue;
        const lean = nx ? leanOf(k, nx, id) : null; if (D_.dot && !lean) continue;
        const np = nx ? nextProb(k, nx, id) : null; let gr = null;
        if (np && nx) { const R = reading(nx); const r0 = R && R.R.find(x => (k === "vit" && x.k === "vittoria" && x.sh === (nx.h === id ? "1" : "2"))); gr = r0 && r0.g; }
        if (D_.grd && !gr) continue;
        items.push({ lg, id, k, n, neg, nx, lean, gr }); } } }
  items.sort((a, b) => b.n - a.n);
  const head = D_.lg === "all" ? `<span class="flag" aria-hidden="true">🌍</span><span class="nm"><small>Tutti</small><b>I campionati</b></span>` : `<span class="flag" aria-hidden="true">${FL[D_.lg] || "🏀"}</span><span class="nm"><small>${esc(B.leghe[D_.lg][1])}</small><b>${esc(B.leghe[D_.lg][0])}</b></span>`;
  const when = D_.w === "all" ? "Tutte le partite" : D_.w === "0" ? "Giocano oggi" : "Giocano domani";
  $("#ritOut").innerHTML = `<section class="card gl4"><div class="gl4h">${head}<span class="gl4m">${when}</span></div>` + (items.length ? `<ul class="rtl">${items.slice(0, 80).map(x => `<li class="rtr${x.nx ? " go" : ""}" data-gid="${x.nx ? esc(x.nx.id) : ""}" role="button" tabindex="0">
      <span class="rtt"><span>${esc(team(x.lg, x.id)[0])} <small class="rtlg">${esc(B.leghe[x.lg][1])} · ${esc(B.leghe[x.lg][0])}</small></span></span>
      <span class="rte">${x.neg} da <b>${x.n}</b> partite${D_.v === "home" ? " in casa" : D_.v === "away" ? " in trasferta" : ""}</span>
      <span class="rtn"><b>${x.n}</b><small>partite</small></span>${x.nx ? `<span class="rtl2 rtnx">${x.nx.h === x.id ? "In casa con" : "In trasferta con"} ${esc(team(x.lg, x.nx.h === x.id ? x.nx.a : x.nx.h)[0])} · ${dlab(x.nx.day)}${x.lean || x.gr ? `<span class="rtlp">${x.lean ? `<i class="rtdot" title="La Lettura di Prevista va verso questo esito"></i>` : ""}${x.gr ? `<span class="ccls ${x.gr === "A+" ? "c-ap" : x.gr === "A" ? "c-a" : x.gr === "B" ? "c-b" : "c-c"}" title="Grado della previsione su questo esito">${x.gr}</span>` : ""}</span>` : ""}</span>` : ""}</li>`).join("")}</ul>`
      : `<p class="muted" style="padding:14px 16px;margin:0">Nessuna squadra con un digiuno${D_.w === "0" ? " gioca oggi" : D_.w === "1" ? " gioca domani" : " con questi filtri"}.</p>`) + `</section>`;
  $("#ritOut").querySelectorAll(".rtr.go").forEach(li => li.addEventListener("click", () => { S.game = li.dataset.gid; S.mt = "prev"; show("match"); }));
}
/* ---------- Tendine come il calcio (15/11/2026): lo stile dell'app rende le <select> intoccabili (pointer-events:none) e il tocco sul riquadro
   apre un foglio con le voci; senza questo codice nel basket le tendine non si aprivano ---------- */
const DDS = (() => { const d = document.createElement("div"); d.className = "sheet ddsheet"; d.hidden = true;
  d.innerHTML = `<div class="sh" role="dialog" aria-modal="true"><div class="sh-h"><b></b><button type="button" class="sh-x" aria-label="Chiudi">✕</button></div><div class="sh-b" role="listbox"></div></div>`;
  document.body.appendChild(d); return d; })();
let DD_SEL = null; const DDN = { skip: false };
function ddTitle(sel) {
  for (const lab of [sel.closest("label"), sel.id && document.querySelector(`label[for="${sel.id}"]`)]) {
    if (!lab) continue; const c = lab.cloneNode(true); c.querySelectorAll("select").forEach(x => x.remove());
    const t = c.textContent.replace(/\s+/g, " ").trim(); if (t) return t;
  }
  return sel.getAttribute("aria-label") || "Scegli";
}
function ddClose() { if (DDS.hidden) return; DDS.hidden = true; if (history.state && history.state.dd) { DDN.skip = true; history.back(); } }
function ddOpen(sel) {
  DD_SEL = sel; DDS.querySelector(".sh-h b").textContent = ddTitle(sel);
  const opt = o => `<button type="button" class="ddo" role="option" data-v="${esc(o.value)}" aria-selected="${o.selected}"${o.disabled ? " disabled" : ""}>${esc(o.textContent)}</button>`;
  DDS.querySelector(".sh-b").innerHTML = [...sel.children].map(c => c.tagName === "OPTGROUP" ? `<div class="ddg">${esc(c.label)}</div>` + [...c.children].map(opt).join("") : opt(c)).join("");
  DDS.hidden = false; try { history.pushState(Object.assign({}, history.state, { dd: 1 }), ""); } catch (e) {}
  const cur = DDS.querySelector('.ddo[aria-selected="true"]'); if (cur) { cur.scrollIntoView({ block: "center" }); cur.focus(); }
}
DDS.addEventListener("click", ev => {
  if (ev.target === DDS || ev.target.closest(".sh-x")) { ddClose(); return; }
  const b = ev.target.closest(".ddo"); if (!b || !DD_SEL) return;
  const sel = DD_SEL, changed = sel.value !== b.dataset.v; sel.value = b.dataset.v; ddClose();
  if (changed) sel.dispatchEvent(new Event("change", { bubbles: true }));
});
document.addEventListener("click", ev => {
  if (ev.target.closest(".sheet")) return;
  const x = ev.clientX, y = ev.clientY;
  const sel = [...document.querySelectorAll("select")].find(s => { if (s.disabled || !s.offsetParent) return false; const r = s.getBoundingClientRect(); return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom; });
  if (sel) { ev.preventDefault(); ev.stopPropagation(); ddOpen(sel); }
}, true);
document.addEventListener("keydown", ev => {
  if (ev.target.tagName === "SELECT" && ["Enter", " ", "ArrowDown", "ArrowUp"].includes(ev.key)) { ev.preventDefault(); ddOpen(ev.target); }
  else if (!DDS.hidden && ev.key === "Escape") ddClose();
}, true);
/* ---------- avvio ---------- */
function wire() {
  $("#navStats").addEventListener("click", () => show("part"));
  $("#navSel").addEventListener("click", () => show("radar"));
  $("#navSig").addEventListener("click", () => show("seg"));
  $("#navGen").addEventListener("click", () => show("ten"));
  $("#navRit").addEventListener("click", () => show("dig"));
  $("#back").addEventListener("click", () => { if (history.state && history.state.v === "match") history.back(); else show("part"); });
  document.querySelectorAll("#viewMatch .mtab").forEach(b => b.addEventListener("click", () => { S.mt = b.dataset.mt; renderMatch(); }));
  document.querySelectorAll("#selTabs [data-rt]").forEach(b => b.addEventListener("click", () => { S.rt = b.dataset.rt; renderRadar(); }));
  document.querySelectorAll("#sigWhen [data-sw]").forEach(b => b.addEventListener("click", () => { const k = b.dataset.sw; if (S.sw.has(k)) S.sw.delete(k); else S.sw.add(k); renderSeg(); }));
  document.querySelectorAll("#sigView [data-sv]").forEach(b => b.addEventListener("click", () => { S.sv = b.dataset.sv; renderSeg(); }));
  
}
(async () => {
  wire();
  try {
    const st = await fetch("data/stato.json", { cache: "no-store" }).then(r => r.json()).catch(() => null);
    const v = st && st.v && st.v.basket ? st.v.basket : Date.now();
    B = await fetch("data/basket.json?v=" + v, { cache: "no-cache" }).then(r => r.json());
  } catch (e) { $("#boot").innerHTML = `<p class="muted">Dati del basket non disponibili in questo momento.</p>`; return; }
  try { localStorage.setItem("prevista.sport", "basket"); } catch (e) {}
  try { history.replaceState({ v: "part" }, ""); } catch (e) {}
  addEventListener("popstate", ev => { if (DDN.skip) { DDN.skip = false; return; } if (!DDS.hidden) { DDS.hidden = true; return; } const st = ev.state || { v: "part" }; if (st.game) S.game = st.game; if (st.mt) S.mt = st.mt; show(st.v || "part", false); });
  $("#boot").hidden = true; $("#stamp").textContent = `Aggiornato ${B.agg.slice(8, 10)}/${B.agg.slice(5, 7)} ${B.agg.slice(11)} UTC`;
  show("part", false);
})();
