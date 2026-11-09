---
id: 2ad4721b-ccf4-4de7-81bf-4f1c113e8ecf
type: system-requirement
status: draft
title: Tägliche Sicherung außerhalb des NAS
kennung: B14
prio: muss
umfang: v1
rationale: Blindspot-Analyse vom 09.11.2026, Punkt 1, von Stefan übernommen.
requirement-type: quality
acceptance-criteria:
  - Jeden Tag entsteht eine Sicherung, die älteste wird erst nach 30 Tagen gelöscht.
  - Eine Kopie liegt außerhalb des NAS.
  - Die Wiederherstellung aus einer Sicherung ist einmal erfolgreich getestet und in der README beschrieben.
packages:
  - { id: a1e07cef-f067-4f3b-a290-7b0bc167bcfa, version: n2:22b0303ec030d854, title: Betrieb }
derives-from:
  - { id: e49e16a5-f781-4689-9b0b-83d50e6817aa, version: n2:c1b590d45d84da6c, title: Gesammelte Daten nicht verlieren }
  - { id: a53c4a80-87f7-4dde-bea4-ede3361fcd00, version: n2:0fccd7eeb33c5af7, title: Statistiken über die Winter }
---

Das System muss die Datenbank täglich sichern und die Sicherung an einen zweiten Ort außerhalb des NAS kopieren (z. B. USB-Platte oder Cloud-Speicher). Die Wiederherstellung ist beschrieben und getestet.
