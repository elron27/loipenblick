---
id: 09a0db94-25ec-4ff4-b3bb-ef78e995bc8f
type: system-requirement
status: draft
title: Sicherheits- und Cache-Header, nur freigegebene Dateien
kennung: B24
prio: muss
umfang: livegang
rationale: Recherche Livegang vom 13.11.2026 (docs/livegang.md).
requirement-type: constraint
acceptance-criteria:
  - Der Upload enthält nur Dateien aus einer Freigabeliste (html, css, js, json, png, svg, webmanifest, pmtiles, .htaccess).
  - Ein Test prüft, dass site/ keine .env, keine Dumps und keinen Rohtext der Quellen enthält.
  - Eine 404-Seite ist vorhanden.
packages:
  - { id: a1e07cef-f067-4f3b-a290-7b0bc167bcfa, version: n2:22b0303ec030d854, title: Betrieb }
derives-from:
  - { id: e4545660-d4de-42b3-ab57-8775bd2236fc, version: n2:59358067b6210a34, title: Diesen Winter öffentlich live gehen }
based-on:
  - { id: f32c0018-f80b-48eb-b0c6-3cb8e012e03e, version: n2:87927ec1a6b0bf2c, title: "Livegang: deutscher Webspace, Upload in zwei Phasen, keine Drittanbieter beim Aufruf" }
---

Das System muss Sicherheits- und Cache-Header mitliefern (HSTS, Content-Security-Policy mit default-src self, X-Content-Type-Options, Referrer-Policy strict-origin-when-cross-origin; HTML und index.json kurz cachen, Hash-Dateien lange) und nur freigegebene Dateiarten hochladen.
