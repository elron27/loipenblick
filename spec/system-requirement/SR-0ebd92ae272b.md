---
id: 30cc4a54-ad7d-4dfd-a40e-0ebd92ae272b
type: system-requirement
status: draft
title: Gekennzeichnete Affiliate-Links
kennung: S23
prio: kann
umfang: spaeter
rationale: Blindspots und Business-Case Schneekarte vom 22.11.2026 (/mnt/project-files/schneekarte/blindspots-schneekarte.md), von Stefan am 23.11.2026 als Modul von Loipenblick angenommen.
requirement-type: constraint
acceptance-criteria:
  - Affiliate-Links lassen sich nur einschalten, wenn in S6 keine sichtbare Quelle Einnahmen erlaubt = nein oder unklar hat; sonst bricht der Generator mit einer Meldung ab.
  - Jeder Link ist als „Anzeige“ gekennzeichnet, ein gewöhnlicher Link mit rel="sponsored", ohne Skript oder Bild des Händlers.
  - Affiliate-Links stehen nie im Bereich der Gefahrenstufe, auf der Seite Hinweise oder neben dem Lawinenhinweis.
packages:
  - { id: 80ca981e-5c25-447a-8a54-34679f59a1d7, version: n2:22b0303ec030d854, title: Schneekarte }
derives-from:
  - { id: d5a7d951-0737-4456-914d-e908068a9e9c, version: n2:ebd9f74cdabab2dc, title: Loipenblick freiwillig unterstützen können }
based-on:
  - { id: 7804a5c6-40e2-4a03-9661-e554f6db7832, version: n2:7ee82c9ad96d0078, title: "Nur offene Quellen, die Einnahmen erlauben; kein Open-Meteo" }
---

Das System kann Affiliate-Links zu Bergsport-Händlern zeigen, sobald alle genutzten Quellen eine Nutzung mit Einnahmen erlauben.
