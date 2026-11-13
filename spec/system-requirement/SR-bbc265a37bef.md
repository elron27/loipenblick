---
id: 6a6e934e-122a-427d-932d-bbc265a37bef
type: system-requirement
status: draft
title: Abgleich zwischen Webspace und NAS ohne offenen Port
kennung: N6
prio: muss
umfang: livegang
rationale: "E-18, E-10, N-09: Nur das NAS baut Verbindungen nach außen auf."
requirement-type: functional
acceptance-criteria:
  - Bestätigte Abos und Abmeldungen vom Webspace stehen nach dem nächsten Lauf in der Datenbank des NAS; erst danach wird die Warteschlange quittiert.
  - Ungültige Einträge der Warteschlange werden übersprungen.
  - Scheitert der Abgleich, gehen in diesem Lauf keine Abo-Mails raus.
  - Die Warteschlange gibt der Webspace nur mit dem Schlüssel aus der .env heraus; auf dem Webspace liegt nur dessen SHA-256.
  - Anmelden, Bestätigen, Abgleich, Mail und Abmelden funktionieren durchgehend zusammen.
packages:
  - { id: a6f1d0bb-483a-4c7c-be9b-7d3af3799ea7, version: n2:22b0303ec030d854, title: Benachrichtigung }
derives-from:
  - { id: 65b496e1-7160-4b71-89f2-524a2803d821, version: n2:f33339704ed6e26c, title: "Alarm, wenn eine Loipe gespurt wird" }
based-on:
  - { id: 061819e1-52ed-491c-8e09-5c0ecb309d33, version: n2:22b0303ec030d854, title: E-Mail-Abo und Fehlermeldungen über ein kleines PHP-Skript am Webspace }
  - { id: 2ae0ad55-3d2e-461b-975b-237a0a1f0ac5, version: n2:22b0303ec030d854, title: "Parsen auf dem NAS, Website extern" }
---

Das System muss Abos und Meldungen vom Webspace abholen, ohne dass das NAS von außen erreichbar ist.
