// Service Worker per Rapportini Pro
const CACHE_NAME = "rapportini-pro-v2";
const urlsToCache = [
  "./",
  "./manifest.json",
  "./logo-192.png",
  "./logo-512.png"
];

// Installazione: mette in cache le risorse statiche
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(urlsToCache).catch(() => {
        // Ignora errori per le risorse mancanti
      });
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

// Fetch: serve dalla cache se disponibile, altrimenti dalla rete
self.addEventListener("fetch", (event) => {
  // Non intercettare le richieste API/Streamlit (sonno di Streamlit Cloud)
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  // Lascia passare le richieste a streamlit, googleapis, ecc.
  if (
    url.hostname.includes("streamlit") ||
    url.hostname.includes("googleapis") ||
    url.hostname.includes("googleusercontent")
  ) {
    return;
  }
  event.respondWith(
    caches.match(event.request).then((response) => {
      return (
        response ||
        fetch(event.request).then((networkResponse) => {
          return networkResponse;
        }).catch(() => {
          // Offline fallback
          return new Response("Offline - apri l'app quando sei connesso.", {
            status: 503,
            statusText: "Service Unavailable",
            headers: new Headers({ "Content-Type": "text/plain" })
          });
        })
      );
    })
  );
});
