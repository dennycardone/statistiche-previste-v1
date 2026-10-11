/* Prevista: service worker. Prima prova sempre la rete (dati sempre freschi); se la rete non c'è usa l'ultima copia salvata,
   così l'app si apre anche senza connessione con i dati dell'ultima volta. Solo file dello stesso sito. */
const CACHE = "prevista-v1";
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  e.respondWith(fetch(req).then(res => {
    if (res && res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {}); }
    return res;
  }).catch(() => caches.match(req, { ignoreSearch: true }).then(r => r || (req.mode === "navigate" ? caches.match("index.html", { ignoreSearch: true }) : undefined))
    .then(r => r || new Response("Offline", { status: 503, statusText: "Offline" }))));
});
