---
id: 75d5b55d-4c67-45b7-b41f-e245ec0ce7a5
type: system-requirement
status: draft
title: Betriebskosten höchstens 5 € im Monat
kennung: B9
prio: muss
umfang: v1
rationale: Aus der Bedarfsrunde mit Stefan am 08.11.2026.
requirement-type: constraint
acceptance-criteria:
  - Die Summe der Rechnungen für Webspace, Domain und Dienste liegt im Jahr bei höchstens 60 €.
packages:
  - { id: a1e07cef-f067-4f3b-a290-7b0bc167bcfa, version: n2:22b0303ec030d854, title: Betrieb }
derives-from:
  - { id: 74e4361d-47e5-4ab3-b04d-3e2e5f25ec16, version: n2:cdda38f1ace5147f, title: Günstiger Betrieb }
based-on:
  - { id: 2ae0ad55-3d2e-461b-975b-237a0a1f0ac5, version: n2:22b0303ec030d854, title: "Parsen auf dem NAS, Website extern" }
---

Das System muss mit Diensten auskommen, die zusammen höchstens 5 € im Monat kosten (Webspace, Domain, Wetterdaten, Push), den Strom des NAS nicht mitgerechnet.
