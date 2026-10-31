/* Prevista: service worker. Prima prova sempre la rete (dati sempre freschi); se la rete non c'è usa l'ultima copia salvata,
   così l'app si apre anche senza connessione con i dati dell'ultima volta. Solo file dello stesso sito.
   19/10/2026: i file dati chiesti con ?v=impronta (data/stato.json) non cambiano mai a parità di impronta: si prendono dalla copia
   salvata se c'è (nessun download); al primo arrivo di una impronta nuova si scaricano e le copie vecchie dello stesso file si tolgono. */
const CACHE = "prevista-v1";
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (url.searchParams.has("v")) {   // file con impronta: copia salvata, altrimenti rete
    e.respondWith(caches.open(CACHE).then(c => c.match(req).then(hit => hit || fetch(req).then(res => {
      if (res && res.ok) {
        const copy = res.clone();
        c.put(req, copy).then(() => c.keys()).then(ks => Promise.all(ks.filter(k => { const u = new URL(k.url); return u.pathname === url.pathname && u.search !== url.search; }).map(k => c.delete(k)))).catch(() => {});
      }
      return res;
    }))).catch(() => caches.match(req, { ignoreSearch: true }).then(r => r || new Response("Offline", { status: 503, statusText: "Offline" }))));
    return;
  }
  e.respondWith(fetch(req).then(res => {
    if (res && res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {}); }
    return res;
  }).catch(() => caches.match(req, { ignoreSearch: true }).then(r => r || (req.mode === "navigate" ? caches.match("index.html", { ignoreSearch: true }) : undefined))
    .then(r => r || new Response("Offline", { status: 503, statusText: "Offline" }))));
});
