---
id: a54b7cb3-0b4f-4b26-acf0-544df3a2faed
type: system-requirement
status: draft
title: Länge und Stil der tirol.at-Loipen ohne Wartezeit
kennung: P25
prio: muss
umfang: ausbau1
rationale: "Stefan am 13.11.2026 nach dem Test am NAS: Viele Loipen lassen sich nicht anklicken, Daten sind oft unbekannt, die Rahmendaten (wie viele km es gibt, wie viele offen sind) sollten bekannt sein; Snowfarming-, Opening- und Gletscherloipen stehen als offen da."
requirement-type: functional
acceptance-criteria:
  - Die Liste der geöffneten Loipen wird über alle Seiten gelesen (höchstens offen_seiten_max); jeder Eintrag liefert Länge, Schwierigkeit und Stile.
  - Die Detailseiten eines Laufs gehen zuerst an Loipen, deren Länge weder in der Datenbank noch in der Liste steht; der Rest des Kontingents im Wechsel wie bisher.
  - Fehlt eine Folgeseite der Liste, bleiben die Daten der übrigen Seiten und es gibt eine Warnung.
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 3cc0b4ba-48ea-4c59-bc3e-a269e781aa26, version: n2:641911ee7fdb8aa9, title: "Wissen, wie alt und woher die Daten sind" }
---

Das System muss Länge, Schwierigkeit und Stile aller offenen tirol.at-Loipen bei jedem Lauf aus der Liste übernehmen und Detailseiten zuerst für Loipen ohne bekannte Länge abrufen.
