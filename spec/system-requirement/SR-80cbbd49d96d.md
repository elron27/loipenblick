---
id: b6e73e60-effc-409a-b98e-80cbbd49d96d
type: system-requirement
status: draft
title: Seite bleibt bei NAS-Ausfall erreichbar
kennung: B10
prio: muss
umfang: livegang
rationale: Aus der Bedarfsrunde mit Stefan am 08.11.2026. Erst relevant, wenn die Seite online ist (E-11).
requirement-type: quality
acceptance-criteria:
  - Bei ausgeschaltetem NAS liefert die öffentliche Adresse die zuletzt hochgeladene Seite.
  - Ist der Stand älter als 48 h, weist die Startseite darauf hin (U6).
packages:
  - { id: a1e07cef-f067-4f3b-a290-7b0bc167bcfa, version: n2:22b0303ec030d854, title: Betrieb }
derives-from:
  - { id: 88ed187b-a41a-4008-9f85-bc0627125553, version: n2:b57af34b37bb86fa, title: Öffentlich erreichbar }
  - { id: 3cc0b4ba-48ea-4c59-bc3e-a269e781aa26, version: n2:641911ee7fdb8aa9, title: "Wissen, wie alt und woher die Daten sind" }
  - { id: e4545660-d4de-42b3-ab57-8775bd2236fc, version: n2:59358067b6210a34, title: Diesen Winter öffentlich live gehen }
based-on:
  - { id: 2ae0ad55-3d2e-461b-975b-237a0a1f0ac5, version: n2:22b0303ec030d854, title: "Parsen auf dem NAS, Website extern" }
  - { id: 4e6c0430-b562-4fd0-9279-e19cc6172d7f, version: n2:22b0303ec030d854, title: Version 1 zuerst lokal auf dem NAS testen }
  - { id: f32c0018-f80b-48eb-b0c6-3cb8e012e03e, version: n2:87927ec1a6b0bf2c, title: "Livegang: deutscher Webspace, Upload in zwei Phasen, keine Drittanbieter beim Aufruf" }
---

Das System muss erreichbar bleiben, wenn das NAS aus ist. Die Seite zeigt dann den letzten Stand mit seinem Alter.
