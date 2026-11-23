---
id: 8064f0ee-d444-4067-8482-88d4ca236fcc
type: system-requirement
status: draft
title: Hinweis zur Lawinenlage auf jeder Seite
kennung: S15
prio: muss
umfang: schnee1
rationale: Blindspots und Business-Case Schneekarte vom 22.11.2026 (/mnt/project-files/schneekarte/blindspots-schneekarte.md), von Stefan am 23.11.2026 als Modul von Loipenblick angenommen.
requirement-type: constraint
acceptance-criteria:
  - "Jede Seite der Schneekarte zeigt gut sichtbar: „Kein Ersatz für den offiziellen Lawinenlagebericht. Lies vor jeder Tour den aktuellen Bericht.“ mit Link zum zuständigen Warndienst."
  - "Die Seite Hinweise (B25) erklärt zusätzlich: Messstationen stehen auf flachen, geschützten Feldern und sagen wenig über einen einzelnen Hang, Modellwerte sind Schätzungen, und alle Werte kommen mit Verzögerung."
  - Die Livegang-Checkliste verlangt vor dem ersten Affiliate-Link eine kurze anwaltliche Prüfung von Hinweis und Haftung.
packages:
  - { id: 80ca981e-5c25-447a-8a54-34679f59a1d7, version: n2:22b0303ec030d854, title: Schneekarte }
derives-from:
  - { id: 0dbc8a09-f827-4f6e-ac94-0b3b4b8452b6, version: n2:6b60e93868e97477, title: Haftung klarstellen }
based-on:
  - { id: 76be2276-2820-4682-8641-1517db627f9a, version: n2:46f6c637ac5b1278, title: Keine eigene Bewertung der Lawinenlage }
---

Das System muss auf jeder Seite der Schneekarte darauf hinweisen, dass sie den offiziellen Lagebericht nicht ersetzt.
