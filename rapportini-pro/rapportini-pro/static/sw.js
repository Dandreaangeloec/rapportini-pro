// Service Worker per Rapportini Pro v5 - Solo caching statico, mai blocca Streamlit
const CACHE_NAME = "rapportini-pro-v5";

const urlsToCache = [
  "./static/manifest.json",
  "./static/db.js",
  "./static/sync.js"
];

// Installazione: mette in cache solo le risorse statiche dell'app
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(urlsToCache).catch(() => {});
    })
  );
  self.skipWaiting();
});

// Attivazione: pulisce le cache vecchie
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch: NON intercettiamo NULLA di Streamlit.
// Rispondiamo solo per file statici esplicitamente nella cache.
// Per tutto il resto lasciamo passare la richiesta normale.
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Non intercettare MAI richieste verso Streamlit o Google
  if (
    url.hostname.includes("streamlit") ||
    url.hostname.includes("streamlit") ||
    url.hostname.includes("googleapis") ||
    url.hostname.includes("gstatic") ||
    url.hostname.includes("googleusercontent") ||
    url.hostname.includes("dataframe")
  ) {
    return;
  }

  // Non intercettare richieste non-GET
  if (event.request.method !== "GET") return;

  // Solo per i nostri file statici esplicitamente elencati: Cache First
  const staticFiles = [
    "/static/manifest.json",
    "/static/db.js", 
    "/static/sync.js",
    "/static/logo-192.png",
    "/static/logo-512.png"
  ];
  
  const isStaticFile = staticFiles.some(f => url.pathname.endsWith(f) || url.pathname === f);
  
  if (isStaticFile) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
    return;
  }

  // Per tutto il resto (Streamlit HTML, componenti, etc.) — SOLO rete, mai cache
  // Non facciamo niente, lasciamo passare la richiesta normalmente
  return;
});