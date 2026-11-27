---
id: 45021f19-920f-4509-8034-edd885a1fe13
type: system-requirement
status: draft
title: Hunderegel und beleuchtete Loipen je Gebiet
kennung: D25
prio: soll
umfang: details
rationale: "Handrecherche vom 27.11.2026: Hundeverbote (Bayrischzell, Faistenau/Hintersee) und beleuchtete Loipen mit Zeiten sind auf den Ortsseiten belegt, hatten aber kein Feld. Stefan hat am 27.11.2026 kleine Felder dafür erbeten."
requirement-type: functional
acceptance-criteria:
  - Ein Gebiet kann in config/gebiete.yaml eine Hunderegel (erlaubt ja/nein, Text, URL, Prüfdatum) und eine Liste beleuchteter Loipen (Name, Zeiten, URL, Prüfdatum) tragen; fehlt die Angabe, gilt sie als unbekannt.
  - Die Gebietsseite zeigt die Hunderegel und die beleuchteten Loipen mit Zeiten unter Anreise; ohne Angabe erscheint nichts.
  - Die Saisonprüfung (B32) legt beide Angaben wie Webcams und Verleih zur Prüfung vor.
packages:
  - { id: 1554c39a-9747-4c4a-b1a2-2d04b1153c7d, version: n2:22b0303ec030d854, title: Datenmodell }
derives-from:
  - { id: 1ea24370-2a91-4259-a154-e0ca66774ba6, version: n2:9eb82629adf1c087, title: Abends auf die Nachtloipe }
  - { id: efd60347-f4c8-4c6c-9b38-143045ad81d2, version: n2:1b243baea1d51dc3, title: Passende Loipe für die Gruppe }
---

Das System soll je Gebiet von Hand gepflegt führen, ob Hunde auf den Loipen erlaubt sind, und welche Loipen beleuchtet sind (Name, Beleuchtungszeiten), jeweils mit Quell-URL und Prüfdatum, und beides auf der Gebietsseite zeigen.
