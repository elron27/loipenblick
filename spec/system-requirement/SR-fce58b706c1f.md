---
id: 0d257d8c-7991-4c70-b880-fce58b706c1f
type: system-requirement
status: draft
title: Hinweis „Schnee reicht vermutlich“
kennung: U20
prio: kann
umfang: spaeter
rationale: Aus dem Interview mit Stefan am 09.11.2026.
requirement-type: functional
acceptance-criteria:
  - Die Markierung erscheint nur, wenn die Schneehöhe am Gebiet über dem Mindestwert liegt und keine Loipe gespurt ist.
  - Der Mindestwert pro Gebiet wird aus vergangenen Wintern bestimmt (D4, D13).
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: 0b3d0db9-2a24-4441-8297-2d947c6d4164, version: n2:39094c9aeecf0f85, title: "Erkennen, wo es bald geht" }
---

Das System kann Gebiete markieren, in denen die Wetterhistorie genug Schnee erwarten lässt, aber noch keine Loipe gespurt ist. Die Regel wird aus den gesammelten Daten abgeleitet.
