---
id: 46ece78e-31b9-431b-9408-32a523bcefa6
type: system-requirement
status: draft
title: Chiemgau als Gebiet aufnehmen
kennung: P11
prio: soll
umfang: v1
rationale: Aus dem Interview mit Stefan am 08.11.2026. Nach E-12 in Version 1.
requirement-type: functional
acceptance-criteria:
  - Für jedes Gebiet im Chiemgau bis Ruhpolding ist erfasst, ob und wie es angebunden ist.
  - Angebundene Gebiete erscheinen auf Karte und Liste wie die übrigen.
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 05987e34-b530-4a27-af28-276e48707a7f, version: n2:49aae3ee115ffed9, title: "Im größeren Umkreis suchen, wenn Freunde da sind" }
based-on:
  - { id: cd3f579f-4145-4de3-9988-4297bc2269ce, version: n2:22b0303ec030d854, title: "Gebiet von Version 1: Gebiet der alten App plus Umkreis" }
  - { id: 4a17d7a9-1920-4fbc-b47a-53d2aa307b09, version: n2:22b0303ec030d854, title: Chiemgau gehört zu Version 1 }
---

Das System soll die Langlaufgebiete im Chiemgau bis Ruhpolding als Quellen aufnehmen, soweit es dort parsebare Loipendaten gibt. Wo es nur Freitext gibt, erscheint das Gebiet mit Grobstatus.
