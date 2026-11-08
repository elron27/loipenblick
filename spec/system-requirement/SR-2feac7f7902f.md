---
id: f0463b5d-0cbc-4c9a-94ef-2feac7f7902f
type: system-requirement
status: draft
title: Schneehöhe und Neuschnee pro Gebiet
kennung: D11
prio: soll
umfang: v1
rationale: Aus dem Interview mit Stefan am 08.11.2026.
requirement-type: functional
acceptance-criteria:
  - Jedes Gebiet hat Schneehöhe in cm und Neuschnee in cm für 24, 48 und 72 h, jeweils mit Zeitpunkt und Quelle.
  - Fehlt ein Wert, ist er als unbekannt gespeichert, nicht als 0.
packages:
  - { id: 1554c39a-9747-4c4a-b1a2-2d04b1153c7d, version: n2:22b0303ec030d854, title: Datenmodell }
derives-from:
  - { id: 336b2c0a-3750-430a-a545-ffb48f31dedb, version: n2:fb1eee7dc7f860a6, title: "Wissen, wo guter Schnee liegt" }
---

Das System soll für jedes Gebiet die aktuelle Schneehöhe und den Neuschnee der letzten 24, 48 und 72 Stunden führen, aus der Quelle des Gebiets oder aus offenen Daten des Deutschen Wetterdienstes.
