---
id: 3ce4171f-9842-47c8-9f0a-76b89ae5ad0b
type: system-requirement
status: draft
title: Sommer-Modus
kennung: U28
prio: soll
umfang: spaeter
rationale: "Blindspot-Analyse vom 09.11.2026, Punkt 12: Stefan hat „übernehmen“ gewählt. Braucht die Statistiken (U19)."
requirement-type: functional
acceptance-criteria:
  - Zwischen Saisonende und erstem gespurten Tag zeigt die Startseite den Rückblick.
  - Die Saisongrenzen stehen in der Konfiguration.
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: 5409d341-378c-4f82-afd1-110dd46e0744, version: n2:cb2542f9a7e83262, title: Sinnvoll außerhalb der Saison }
---

Das System soll außerhalb der Saison statt einer Karte voller geschlossener Loipen einen Rückblick auf den letzten Winter zeigen (gespurte Tage, beste Gebiete) und den Hinweis, ab wann wieder Daten kommen.
