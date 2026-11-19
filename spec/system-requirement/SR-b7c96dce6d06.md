---
id: c0f2c900-49e0-4b21-86df-b7c96dce6d06
type: system-requirement
status: draft
title: Loipenstatus der Ortsseiten Innsbruck, Hall-Wattens und Silberregion Karwendel
kennung: P32
prio: kann
umfang: ausbau3
rationale: "Stefan am 19.11.2026 (E-24): Tiroler Ortsseiten als Querprüfung für tirol.at aufnehmen, zunächst nur für die Testversion. Innsbruck bettet einen Intermaps-Wintersportbericht ein; Intermaps ist nach E-15 und P17 ausgeschlossen, Stefan hat am 19.11.2026 eine Ausnahme nur für die Testversion freigegeben. Hall-Wattens und die Silberregion Karwendel zeigen den Status je Loipe im Tourenportal. Stubai (robots.txt 403) und Wipptal (nur tirol.at-Daten) entfallen."
requirement-type: functional
acceptance-criteria:
  - "Innsbruck: alle Langlaufloipen des Wintersportberichts mit Ort, Gebiet, Technik, Status und dem Stand der Meldung; was ein Status-Symbol heißt, kommt aus der Legende derselben Seite (offen, geschlossen, in Vorbereitung = geschlossen, offen nicht frisch präpariert = eingeschränkt)."
  - "Hall-Wattens und Silberregion Karwendel: alle Loipen der Langlaufseite mit Status, Länge, Schwierigkeit, Startpunkt und Lage; Testeinträge der Quelle fallen weg, vertauschte Breite und Länge werden korrigiert."
  - Ein unbekanntes Status-Symbol oder Statuswort ergibt Status unbekannt mit Rohtext, eine leere oder umgebaute Seite eine Warnung statt einer leeren Meldung ohne Hinweis.
  - "Die drei Quellen tragen erlaubnis nur_test, Rang 4 und querpruefung: true; tirol.at bleibt führend, ihre Geschlossen-Meldungen dienen nur der Plausibilitätsprüfung und treffen die gleichnamige Loipe, nicht eine nummerierte Nachbarloipe. Innsbruck trägt die P17-Ausnahme mit Begründung; Stubai und Wipptal sind nicht konfiguriert."
packages:
  - { id: aecf250b-eb6d-41e6-9041-3ce5eb9763a3, version: n2:22b0303ec030d854, title: Datenerfassung }
derives-from:
  - { id: 61222249-ffc3-4fb4-802a-be8cb6cfcf5e, version: n2:59e73627210f5a49, title: Offensichtliche Fehlmeldungen nicht als offen sehen }
based-on:
  - { id: a2715ad5-85dd-40c4-a964-8148c8fe3659, version: n2:cd357b270c742bf5, title: "Quellen ohne Zustimmung erst testen, dann mit Vorführung fragen" }
---

Das System soll den Loipenstatus der Ortsseiten von Innsbruck, Hall-Wattens und der Silberregion Karwendel lesen und damit die Meldungen von tirol.at gegenprüfen.
