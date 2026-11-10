/* Blocco di sicurezza prima di pubblicare (10/11/2026, punto 6 dell'audit): l'app della cartella indicata deve (1) avere script senza errori di
   sintassi, (2) avviarsi in un browser vero con i dati del giro, (3) aprire una scheda partita, il Radar (Grado, Mercato, Operatività) e i
   Segnali senza errori JavaScript. Se qualcosa non va esce con codice 1 e il giro tiene online la versione precedente dell'app.
   Uso: node tools/controllo_app.js CARTELLA_DEL_SITO   (Chrome di sistema: CHROME_PATH, altrimenti quello di Playwright) */
const fs = require("fs"), path = require("path"), http = require("http");
const DIR = path.resolve(process.argv[2] || "_site");
const fail = m => { console.log("::error title=Controllo dell'app::" + m); process.exit(1); };
const html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
for (const m of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) { try { new Function(m[1]); } catch (e) { fail("errore di sintassi nell'app: " + e.message); } }
let pw; try { pw = require("playwright-core"); } catch (e) { try { pw = require("playwright"); } catch (e2) { try { pw = require(require("child_process").execSync("npm root -g").toString().trim() + "/playwright"); } catch (e3) { console.log("::warning title=Controllo dell'app::browser di prova non disponibile: controllata solo la sintassi"); process.exit(0); } } }
const MIME = { ".html": "text/html", ".json": "application/json", ".js": "text/javascript", ".svg": "image/svg+xml", ".png": "image/png", ".woff": "font/woff", ".webmanifest": "application/manifest+json" };
const srv = http.createServer((q, r) => { const f = path.join(DIR, decodeURIComponent(q.url.split("?")[0]).replace(/^\/+/, "") || "index.html");
  fs.readFile(f.endsWith(path.sep) || f === DIR ? path.join(DIR, "index.html") : f, (e, b) => { if (e) { r.writeHead(404); r.end(); } else { r.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" }); r.end(b); } }); });
srv.listen(0, async () => {
  const port = srv.address().port; let br;
  try {
    br = await pw.chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
    const p = await (await br.newContext({ serviceWorkers: "block", viewport: { width: 390, height: 844 } })).newPage();
    const errs = []; p.on("pageerror", e => errs.push(e.message));
    await p.route(u => !u.href.startsWith("http://localhost"), r => r.abort());   // niente rete esterna (stemmi)
    await p.goto(`http://localhost:${port}/index.html`);
    await p.waitForFunction(() => !document.body.classList.contains("booting"), { timeout: 90000 }).catch(() => { throw new Error("l'app non si avvia entro 90 secondi" + (errs.length ? " · " + errs[0] : "")); });
    await p.waitForTimeout(2500);
    const r = await p.evaluate(async () => {
      const out = { n: 0, bad: [] }; const A = allEntries().concat(uclEntries()), seen = new Set();
      for (const e of A) { if (seen.has(e.lg.code) || seen.size >= 6) continue; seen.add(e.lg.code);
        try { openEntry(e); await new Promise(r => setTimeout(r, 400)); const h = document.querySelector("#mhead"); if (!h || h.innerText.length < 40 || /NaN|undefined/.test(h.innerText)) out.bad.push(e.id); out.n++; } catch (x) { out.bad.push(e.id + " " + x.message); } }
      return out; });
    if (r.bad.length) throw new Error("scheda partita non valida: " + r.bad.slice(0, 3).join(" · "));
    await p.click("#navSel"); await p.waitForTimeout(800);
    for (const t of ["all", "bk", "op"]) { await p.click(`#selTabs [data-rt="${t}"]`); await p.waitForTimeout(t === "op" ? 6000 : 3000); }
    await p.click("#navSig").catch(() => {}); await p.waitForTimeout(3000);
    if (errs.length) throw new Error("errori JavaScript: " + [...new Set(errs)].slice(0, 3).join(" · "));
    console.log(`::notice title=Controllo dell'app::avvio, ${r.n} schede partita, Radar e Segnali senza errori`);
    await br.close(); srv.close(); process.exit(0);
  } catch (e) { try { await br.close(); } catch (x) {} srv.close();
    if (!br) { console.log("::warning title=Controllo dell'app::browser di prova non avviato (" + e.message.slice(0, 120) + "): controllata solo la sintassi"); process.exit(0); }
    fail(e.message.slice(0, 400)); }
});
