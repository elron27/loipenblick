---
id: 9fc59957-61bd-4406-b04f-e5c2cb7798cf
type: system-requirement
status: draft
title: Standort per Gerät oder Ortssuche
kennung: U35
prio: soll
umfang: ausbau1
rationale: Stefan am 13.11.2026 nach dem Test auf dem NAS (E-16). Der Standort ließ sich bisher nur aus einer langen Liste wählen; im Heimnetz über http gibt der Browser kein GPS frei.
requirement-type: functional
acceptance-criteria:
  - Beim ersten Besuch auf einer sicheren Seite (https) fragt die Seite einmal nach dem Standort und zeigt danach Mein Standort mit dem nächsten bekannten Ort.
  - Die Ortssuche findet bekannte Orte und Gebiete beim Tippen und andere Orte oder Postleitzahlen online.
  - Ohne https oder ohne Freigabe nennt die Seite den Grund und bietet die Suche an, ohne Fehlermeldung des Browsers.
packages:
  - { id: 7b29aa02-4a82-499c-9654-8d13c0c2d64c, version: n2:22b0303ec030d854, title: Oberfläche }
derives-from:
  - { id: 05987e34-b530-4a27-af28-276e48707a7f, version: n2:49aae3ee115ffed9, title: "Im größeren Umkreis suchen, wenn Freunde da sind" }
based-on:
  - { id: 66582671-424e-461b-8164-f2a49df3492f, version: n2:22b0303ec030d854, title: Entfernung zunächst als Luftlinie }
---

Das System soll den Standort beim ersten Besuch einmal beim Gerät erfragen und ihn sonst per Ortssuche einstellen lassen, auch für Orte und Postleitzahlen ohne eigene Loipe.
