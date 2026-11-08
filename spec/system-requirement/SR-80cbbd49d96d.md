---
id: b6e73e60-effc-409a-b98e-80cbbd49d96d
type: system-requirement
status: draft
title: Seite bleibt bei NAS-Ausfall erreichbar
kennung: B10
prio: muss
umfang: v1
rationale: Aus der Bedarfsrunde mit Stefan am 08.11.2026.
requirement-type: quality
acceptance-criteria:
  - Bei ausgeschaltetem NAS liefert die öffentliche Adresse die zuletzt hochgeladene Seite.
  - Ist der Stand älter als 48 h, weist die Startseite darauf hin (U6).
packages:
  - { id: a1e07cef-f067-4f3b-a290-7b0bc167bcfa, version: n2:22b0303ec030d854, title: Betrieb }
derives-from:
  - { id: 88ed187b-a41a-4008-9f85-bc0627125553, version: n2:b57af34b37bb86fa, title: Öffentlich erreichbar }
  - { id: 3cc0b4ba-48ea-4c59-bc3e-a269e781aa26, version: n2:641911ee7fdb8aa9, title: "Wissen, wie alt und woher die Daten sind" }
based-on:
  - { id: 2ae0ad55-3d2e-461b-975b-237a0a1f0ac5, version: n2:22b0303ec030d854, title: "Parsen auf dem NAS, Website extern" }
---

Das System muss erreichbar bleiben, wenn das NAS aus ist. Die Seite zeigt dann den letzten Stand mit seinem Alter.
