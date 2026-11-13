// Service Worker (U8, U40, U41). App-Version __STAND__ = Hash der App-Dateien: Sie aendert sich nur,
// wenn sich die App aendert, nicht bei jedem neuen Datenstand.
// - App-Schale (HTML, JS, CSS, Icons, Textseiten): aus dem Cache, damit die App offline startet.
// - Daten (*.json): zuerst aus dem Netz. Kommt nach 4 Sekunden nichts (Funkloch am Parkplatz) oder gar
//   nichts, gilt der letzte gespeicherte Stand. Der Daten-Cache ueberlebt App-Updates.
const VERSION = "__STAND__";
const SCHALE_CACHE = "loipenblick-app-" + VERSION;
const DATEN_CACHE = "loipenblick-daten";
const SCHALE = ["./", "app.css?v=" + VERSION, "app.js?v=" + VERSION, "manifest.webmanifest",
  "icon-192.png", "icon-512.png", "icon-maskable-512.png", "icon-180.png",
  "vendor/leaflet.js", "vendor/leaflet.css", "vendor/leaflet.markercluster.js", "vendor/MarkerCluster.css",
  "impressum.html", "datenschutz.html", "hinweise.html"];
const WARTEN_MS = 4000;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SCHALE_CACHE).then((c) => c.addAll(SCHALE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((ks) => Promise.all(ks.filter((k) => k !== SCHALE_CACHE && k !== DATEN_CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// Gespeicherte Antwort mit Kennzeichen, damit die App "Offline, Stand vom ..." zeigen kann
function ausCache(antwort) {
  if (!antwort) return antwort;
  const h = new Headers(antwort.headers);
  h.set("X-Loipenblick-Cache", "1");
  return antwort.blob().then((b) => new Response(b, {status: antwort.status, statusText: antwort.statusText, headers: h}));
}

// Nur die Dateien behalten, auf die der aktuelle Index verweist (Dateinamen mit Inhalts-Hash, B21)
function aufraeumen(index) {
  const behalten = new Set(["daten.json"]);
  (index.regionen || []).forEach((r) => { if (r.datei) behalten.add(r.datei); if (r.strecken) behalten.add(r.strecken); });
  const basis = self.registration.scope;
  return caches.open(DATEN_CACHE).then((c) => c.keys().then((ks) => Promise.all(ks.map((k) => {
    const rel = k.url.startsWith(basis) ? k.url.slice(basis.length).split("?")[0] : k.url;
    return behalten.has(rel) ? null : c.delete(k);
  }))));
}

function daten(anfrage) {
  const gespeichert = () => caches.open(DATEN_CACHE).then((c) => c.match(anfrage, {ignoreSearch: true})).then(ausCache);
  const netz = fetch(anfrage).then((r) => {
    if (r.ok) {
      const kopie = r.clone();
      caches.open(DATEN_CACHE).then((c) => c.put(anfrage, kopie.clone())).then(() => {
        if (new URL(anfrage.url).pathname.endsWith("/daten.json")) return kopie.json().then(aufraeumen);
      }).catch(() => {});
    }
    return r;
  });
  const zeit = new Promise((ok) => setTimeout(ok, WARTEN_MS)).then(gespeichert);
  // Wer zuerst eine brauchbare Antwort hat, gewinnt; ohne Netz und ohne Cache bleibt der Netzfehler
  return new Promise((ok, fehler) => {
    let offen = 2;
    const nein = (e) => { if (--offen === 0) fehler(e || new Error("offline")); };
    netz.then(ok, () => gespeichert().then((r) => (r ? ok(r) : nein()), nein));
    zeit.then((r) => (r ? ok(r) : nein()), nein);
  });
}

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.includes("/abo/")) return; // Formulare (PHP) nie aus dem Cache
  if (url.pathname.endsWith(".json")) { e.respondWith(daten(e.request)); return; }
  if (e.request.mode === "navigate") {
    // Seiten: zuerst Netz, offline die gespeicherte Seite oder die App
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request, {ignoreSearch: true}).then((r) => r || caches.match("./"))));
    return;
  }
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
