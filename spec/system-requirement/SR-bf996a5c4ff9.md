---
id: 949cbbc6-1f07-41b4-9fb7-bf996a5c4ff9
type: system-requirement
status: draft
title: Gefahrenstufe nur mit Pflichtangaben
kennung: S14
prio: muss
umfang: schnee1
rationale: Blindspots und Business-Case Schneekarte vom 22.11.2026 (/mnt/project-files/schneekarte/blindspots-schneekarte.md), von Stefan am 23.11.2026 als Modul von Loipenblick angenommen.
requirement-type: constraint
acceptance-criteria:
  - Die Stufe erscheint als Zahl und Wort (U22) zusammen mit Ausgabe- und Gültigkeitszeit, Höhengrenze oder Höhenbändern, Vormittag und Nachmittag, wenn der Bericht das trennt, den Lawinenproblemen und dem Link zum Originalbericht.
  - Ist der Bericht nicht mehr gültig, wird die Stufe ausgegraut und mit „nicht aktuell, Stand …“ beschriftet.
  - Gibt es für eine Region keinen Bericht, steht dort „Kein aktueller Lagebericht“ und keine Stufe, auch nicht Stufe 1.
  - Die Seite berechnet keine Stufe, mittelt nicht über Regionen und überträgt keine Stufe auf eine Region ohne Bericht.
  - "Außerhalb zitierter Berichtstexte kommen auf den Seiten der Schneekarte die Wörter der Verbotsliste nicht vor: „Tour möglich“, „sicher“, „unbedenklich“, „empfohlen“, „gute Verhältnisse“. Die Liste steht in der Konfiguration und wird ergänzt."
packages:
  - { id: 80ca981e-5c25-447a-8a54-34679f59a1d7, version: n2:22b0303ec030d854, title: Schneekarte }
derives-from:
  - { id: e6553bd6-0da3-43b1-a35a-181c1f926441, version: n2:e3457ffe0783cfb0, title: Offizielle Lawinenlage im Verlauf sehen }
  - { id: 0dbc8a09-f827-4f6e-ac94-0b3b4b8452b6, version: n2:6b60e93868e97477, title: Haftung klarstellen }
based-on:
  - { id: 76be2276-2820-4682-8641-1517db627f9a, version: n2:46f6c637ac5b1278, title: Keine eigene Bewertung der Lawinenlage }
---

Das System muss die Gefahrenstufe nur so zeigen, wie der Warndienst sie veröffentlicht hat, mit allen Angaben, die zu ihr gehören.
