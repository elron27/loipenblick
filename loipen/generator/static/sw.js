// Service Worker: App-Dateien offline, Daten zuerst aus dem Netz (U8). Version __STAND__
const CACHE = "loipenblick-__STAND__";
const SCHALE = ["./", "app.css?v=__STAND__", "app.js?v=__STAND__", "statistik.js?v=__STAND__", "manifest.webmanifest", "icon-192.png", "vendor/leaflet.js", "vendor/leaflet.css", "vendor/leaflet.markercluster.js", "vendor/MarkerCluster.css"];
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SCHALE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  const daten = url.pathname.endsWith(".json");
  e.respondWith(
    daten
      ? fetch(e.request).then((r) => { const k = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, k)); return r; }).catch(() => caches.match(e.request))
      : caches.match(e.request).then((r) => r || fetch(e.request))
  );
});
