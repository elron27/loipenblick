---
id: b106b5fc-ca18-4d6f-8d30-f727e71fabee
type: system-requirement
status: draft
title: Tests der Schneekarte
kennung: S21
prio: muss
umfang: schnee0
rationale: Blindspots und Business-Case Schneekarte vom 22.11.2026 (/mnt/project-files/schneekarte/blindspots-schneekarte.md), von Stefan am 23.11.2026 als Modul von Loipenblick angenommen.
requirement-type: quality
acceptance-criteria:
  - Jeder Adapter hat einen Fixture-Regressionstest auf einem echten Schnappschuss; bricht eine Quelle, kommt zuerst der Test, dann die Reparatur.
  - Die Lagebericht-Sonderfälle aus S4 und die Ausreißer-Regeln aus S7 haben je einen eigenen Test.
  - Ein Test des Generators prüft, dass keine Gefahrenstufe ohne Datum, Höhengrenze und Link erscheint und dass die Wörter der Verbotsliste aus S14 nicht vorkommen.
  - Oberflächen-Änderungen werden mit Playwright-Screenshots auf Desktop und Handy geprüft.
  - Was nur gegen Mock oder Schnappschuss getestet ist, wird im Abschluss so genannt; der Livebetrieb wird über die sieben Tage aus S1 nachgewiesen.
packages:
  - { id: 80ca981e-5c25-447a-8a54-34679f59a1d7, version: n2:22b0303ec030d854, title: Schneekarte }
derives-from:
  - { id: 3cc0b4ba-48ea-4c59-bc3e-a269e781aa26, version: n2:641911ee7fdb8aa9, title: "Wissen, wie alt und woher die Daten sind" }
  - { id: 0dbc8a09-f827-4f6e-ac94-0b3b4b8452b6, version: n2:6b60e93868e97477, title: Haftung klarstellen }
based-on:
  - { id: 39036f2d-2d27-4398-bcbb-6ed620a1eb1b, version: n2:ac4199910ef8b0ea, title: "Zuerst sammeln, dann zeigen" }
---

Das System muss die Schneekarte mit eigenen Tests absichern, die ohne NAS und ohne Netz laufen.
