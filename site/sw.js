// Keeps the site and the catalog on the device so the list works inside the fair tent, where the signal is weak.
// Network first: online visitors always get the latest catalog; the cache is only the offline fallback.
const CACHE_NAME = "guia-nao-oficial-festa-do-livro-v1";

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(["./", "./index.html"])));
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(names => Promise.all(names.filter(name => name !== CACHE_NAME).map(name => caches.delete(name))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin) return;
  event.respondWith(
    fetch(event.request)
      .then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() =>
        caches.match(event.request, { ignoreSearch: true }).then(cached => cached || caches.match("./index.html"))
      )
  );
});
