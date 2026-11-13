---
id: f8e15567-bf3c-493c-aec9-d3a6ee7f5e40
type: system-requirement
status: draft
title: Kennzahlen der Startseite führen zur Liste
kennung: U34
prio: soll
umfang: ausbau1
rationale: Stefan am 13.11.2026 nach dem Test auf dem NAS (E-16). Auf die 11 befahrbaren konnte man nicht klicken.
requirement-type: functional
acceptance-criteria:
  - Ein Klick auf die Zahl der befahrbaren Loipen öffnet die Liste mit dem Filter nur offene, sortiert nach Entfernung.
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: a1ad23a0-cdad-4ff8-bb51-af00893d9a9d, version: n2:83edd6a0956f785e, title: Heute gut langlaufen in meiner Nähe }
based-on:
  - { id: 10ac94df-d2fa-437c-b0fc-56ccd995237d, version: n2:70d79e4302373dae, title: "Regionale Loipenberichte vor tirol.at, Standort per Gerät" }
---

Das System soll die Kennzahlen der Startseite als Links zeigen: befahrbar führt zur Liste nur der offenen Loipen.
