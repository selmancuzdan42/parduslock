const CACHE = "pardus-lock-v1";
const STATIC = ["/", "/assets/js/jsqr.js", "/assets/img/favicon.png", "/manifest.json"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener("fetch", e => {
  // API isteklerini cache'leme
  if (e.request.url.includes("/api/")) return;
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
