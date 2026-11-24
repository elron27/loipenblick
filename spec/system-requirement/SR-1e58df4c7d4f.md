---
id: 21ddaa91-0259-4f07-83aa-1e58df4c7d4f
type: system-requirement
status: draft
title: Erlaubnis-Status je Quelle
kennung: B27
prio: muss
umfang: livegang
rationale: "Stefan am 19.11.2026 (E-24): Ortsseiten wie zillertal.at für die Testversion nutzen, beim Livegang ohne Zustimmung ausblenden, Kontaktliste führen."
requirement-type: functional
acceptance-criteria:
  - Eine Quelle mit erlaubnis nur_test erscheint in der Testversion, auf der öffentlichen Seite (LOIPEN_OEFFENTLICH=true) fehlen ihre Loipen, ihr Eintrag in der Quellenliste und im Impressum.
  - Die Konfigurationsprüfung lehnt andere Werte als liegt_vor, ausstehend und nur_test ab; ohne Angabe gilt ausstehend.
  - Die Livegang-Checkliste verlangt vor der Freigabe, alle nur_test-Quellen zu prüfen, und verweist auf die Kontaktliste (docs/kontaktliste.md) mit Stelle, Zweck, Kontakt und Stand je Quelle.
packages:
  - { id: a1e07cef-f067-4f3b-a290-7b0bc167bcfa, version: n2:22b0303ec030d854, title: Betrieb }
based-on:
  - { id: a2715ad5-85dd-40c4-a964-8148c8fe3659, version: n2:cd357b270c742bf5, title: "Quellen ohne Zustimmung erst testen, dann mit Vorführung fragen" }
  - { id: 3cb681d8-75d4-404f-9ca6-fd66c8537995, version: n2:edb6bc4736c1e9b9, title: "Kaiserwinkl freigegeben, Widget-Klärung abwarten" }
derives-from:
  - { id: 914f2148-aa61-463c-839d-0cd4039bc354, version: n2:946e559473e10418, title: Daten fair und rechtlich sauber übernehmen }
---

Das System soll für jede Quelle den Erlaubnis-Status des Betreibers führen (liegt vor, ausstehend, nur Test) und Quellen mit nur Test ausschließlich in der Testversion zeigen.
