---
id: 2ad4721b-ccf4-4de7-81bf-4f1c113e8ecf
type: system-requirement
status: draft
title: Täglicher Datenbank-Dump für das NAS-Backup
kennung: B14
prio: muss
umfang: v1
rationale: Blindspot-Analyse vom 09.11.2026, Punkt 1. Stefans NAS sichert bereits auf eine USB-Platte; das System liefert nur den konsistenten Dump dafür.
requirement-type: quality
acceptance-criteria:
  - Jeden Tag entsteht ein Dump im Backup-Ordner, Dumps älter als 30 Tage werden gelöscht.
  - Der Backup-Ordner liegt in einem vom NAS-Backup erfassten Verzeichnis.
  - Die Wiederherstellung aus einem Dump ist einmal erfolgreich getestet und in der README beschrieben.
packages:
  - { id: a1e07cef-f067-4f3b-a290-7b0bc167bcfa, version: n2:22b0303ec030d854, title: Betrieb }
derives-from:
  - { id: e49e16a5-f781-4689-9b0b-83d50e6817aa, version: n2:c1b590d45d84da6c, title: Gesammelte Daten nicht verlieren }
  - { id: a53c4a80-87f7-4dde-bea4-ede3361fcd00, version: n2:0fccd7eeb33c5af7, title: Statistiken über die Winter }
---

Das System muss die Datenbank täglich als Dump in einen Ordner auf dem NAS schreiben, den das vorhandene NAS-Backup auf die USB-Platte mitsichert. Ein Dump ist nötig, weil eine Dateikopie der laufenden PostgreSQL-Datenbank unbrauchbar sein kann.
