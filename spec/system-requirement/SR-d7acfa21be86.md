---
id: d6d95325-a7d2-4908-88d4-d7acfa21be86
type: system-requirement
status: draft
title: Sperrungen mit Grund erfassen
kennung: D14
prio: soll
umfang: v1
rationale: Blindspot-Analyse vom 09.11.2026, Punkt 4, von Stefan übernommen.
requirement-type: functional
acceptance-criteria:
  - Ein Quelltext mit „wegen Veranstaltung gesperrt“ ergibt Status geschlossen mit Grund „Veranstaltung“.
  - Die Stichwörter stehen in der Zuordnungstabelle (P5).
  - Der Grund erscheint in Liste und Detailseite.
packages:
  - { id: 1554c39a-9747-4c4a-b1a2-2d04b1153c7d, version: n2:22b0303ec030d854, title: Datenmodell }
derives-from:
  - { id: dcb44782-e73f-479f-ba4a-1d47a5ee4512, version: n2:3e3240e4bb887194, title: Sperrungen und Veranstaltungen kennen }
---

Das System soll Sperrhinweise aus den Quelltexten erkennen (z. B. „gesperrt“, „Rennen“, „Forstarbeiten“), den Status „geschlossen“ mit Grund und Zeitraum speichern und den Grund anzeigen.
