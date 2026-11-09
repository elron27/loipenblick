---
id: 9982edc1-510e-420e-9633-d255daaa5fca
type: system-requirement
status: draft
title: Beleuchtungszeiten der Nachtloipen
kennung: D12
prio: soll
umfang: spaeter
rationale: Aus dem Interview mit Stefan am 08.11.2026. In Version 1 gibt es schon den einfachen Filter Nachtloipe (U3).
requirement-type: functional
acceptance-criteria:
  - Eine Nachtloipe hat Beleuchtungstage und -zeiten aus der Quelle oder der Konfiguration.
  - Der Filter „heute Abend beleuchtet“ zeigt nur Nachtloipen, die heute nach 17 Uhr beleuchtet sind.
packages:
  - { id: 1554c39a-9747-4c4a-b1a2-2d04b1153c7d, version: n2:22b0303ec030d854, title: Datenmodell }
derives-from:
  - { id: 1ea24370-2a91-4259-a154-e0ca66774ba6, version: n2:9eb82629adf1c087, title: Abends auf die Nachtloipe }
---

Das System soll für Nachtloipen die Beleuchtungszeiten führen (Wochentage, Uhrzeit bis wann) und mit dem Filter „heute Abend beleuchtet“ anzeigen.
