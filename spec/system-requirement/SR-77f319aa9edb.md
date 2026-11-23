---
id: 4c3c6151-3681-452b-b95a-77f319aa9edb
type: system-requirement
status: draft
title: Herkunft und Höhe an jedem Wert
kennung: S13
prio: muss
umfang: schnee1
rationale: Blindspots und Business-Case Schneekarte vom 22.11.2026 (/mnt/project-files/schneekarte/blindspots-schneekarte.md), von Stefan am 23.11.2026 als Modul von Loipenblick angenommen.
requirement-type: constraint
acceptance-criteria:
  - Jeder Wert nennt Station oder Höhenband, Höhe, Messzeitpunkt, Messart und Quelle.
  - Werte verschiedener Länder werden nicht zu einer gemeinsamen Fläche oder Zahl verrechnet.
  - Verdächtige Werte (S7) sind sichtbar markiert und fließen in keine Kennzahl ein.
  - Die Quellenangabe der Schneekarte nennt jede genutzte Quelle mit ihrem Namensnennungstext aus S6.
packages:
  - { id: 80ca981e-5c25-447a-8a54-34679f59a1d7, version: n2:22b0303ec030d854, title: Schneekarte }
derives-from:
  - { id: 3cc0b4ba-48ea-4c59-bc3e-a269e781aa26, version: n2:641911ee7fdb8aa9, title: "Wissen, wie alt und woher die Daten sind" }
  - { id: ae600941-6d80-4a3b-8917-d2874d27de31, version: n2:9fb6d2fe12997dab, title: Schnee in meiner Höhenlage kennen }
based-on:
  - { id: 5065998b-1e63-40c6-95ce-96210602301e, version: n2:e75f64a749047dbf, title: Warnregionen als Gebietszuschnitt }
---

Das System muss bei jedem Schneewert zeigen, woher er kommt, auf welcher Höhe er gilt und ob er gemessen oder modelliert ist.
