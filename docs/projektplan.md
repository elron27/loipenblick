# Projektplan Loipenblick

Eine Datei für den Überblick: was ansteht, wer etwas tun muss, was schon erledigt ist.
Stand: 28.11.2026.

**So wird die Datei gepflegt**

- `[ ]` = offen, `[x]` = erledigt. Erledigtes wandert mit Datum und PR nach unten in „Erledigt“.
- **Wer:** `Stefan` = nur du kannst es tun. `Claude` = ein Thread macht es. `beide` = Claude bereitet vor, du entscheidest oder klickst.
- Jeder Thread hakt hier ab, was er erledigt hat, und trägt neue Aufgaben ein, die aus deinen Nachrichten entstehen. Du kannst auch selbst abhaken, im Browser auf GitHub mit dem Stift-Symbol.
- Hintergrund steht in [livegang.md](livegang.md) und Schritt für Schritt in [livegang-checkliste-stefan.md](livegang-checkliste-stefan.md). Diese Datei verweist nur darauf.

---

## 1. Offene Aufgaben nach Priorität

### Priorität 1: bis zum Livegang am 11.12.

- [ ] **Loipen näher recherchieren, weitere Etappen**: Mieming, Silberregion Karwendel, Hinterriß, dann Südostbayern und Salzburger Land; Verleih-Lücken Inzell und Berchtesgadener Land. Etappen 1–4 erledigt (PR #57, PR #61), Stand und Lücken in [recherche-handdaten-2026-11-27.md](recherche-handdaten-2026-11-27.md). Wer: `Claude`, gut für freie Kapazität.
- [x] **NAS aktualisieren**, damit die Testseite den aktuellen Stand zeigt (zuletzt war sie mehrere Versionen hinterher). Ablauf in [nas-update.md](nas-update.md). Wer: `Stefan`.
- [x] **Absturz-Log am NAS einschalten** (B34): Image neu holen ([nas-update.md](nas-update.md)). Danach steht das Log in `backup/logs/worker.log`, mit der neuen `docker-compose.yml` in `logs/worker.log` neben der `.env`. Für die Mail die `LOIPEN_SMTP_*`-Werte eintragen (Abschnitt 2). Wer: `Stefan`, Claude führt Schritt für Schritt.
- [x] **Impressum-Adresse klären** (eigene Adresse oder Familienadresse mit Zustellungsvollmacht). Checkliste Schritt 3. Wer: `Stefan`.
- [x] **Datenschutzerklärung** mit Generator erstellen oder eingebaute Vorlage bestätigen. Checkliste Schritt 11. Wer: `Stefan`, Claude hilft beim Text.
- [x] **Testseite auf Handy und PC durchklicken** (Standort, Karte, Impressum, Datenschutz, Push, Zähler). Checkliste Schritt 12. Wer: `Stefan`.
- [ ] **Wortlaut DWD-Quellenhinweis** auf dwd.de nachsehen und in einen Thread schreiben. Checkliste Schritt 14. Wer: `Stefan`.
- [ ] **Antworten der Quellen entscheiden** und alle `nur_test`-Quellen durchgehen (siehe Abschnitt 3). Checkliste Schritt 15 und 15a. Wer: `beide`.
- [ ] **Livegang freigeben** (Hauptadresse statt test., Suchmaschinen an). Nicht umkehrbar, nur auf dein Wort. Checkliste Schritt 16. Wer: `Stefan`.
- [ ] **Am Livegang-Tag:** Google Search Console und Bing Webmaster anmelden, UptimeRobot auf Hauptadresse umstellen. Checkliste 16a–16c. Wer: `Stefan`.

### Priorität 2: bald, aber kein Livegang-Hindernis

- [ ] **Parken und Gebühren weiter recherchieren**: Schweiz (Loipenpass), Südtirol (Tageskarten je Dolomiti-NordicSki-Region), Tirol-Lücken über tirol.at, Südostbayern-Lücken (Tegernsee, Berchtesgaden, Fischbachau, Siegsdorf). Stand und Lücken in [recherche-parken-gebuehren-2026-11-28.md](recherche-parken-gebuehren-2026-11-28.md). Wer: `Claude`.
- [ ] **Parkinfo je Gebiet ohne Koordinate anzeigen?** (z. B. „Tannheimer Tal Ticket 5 € für 24 h per App“). Heute zeigt die Seite nur Parkplätze mit Koordinate. Wer: `Stefan` entscheidet.
- [ ] **„Infos nachtragen“ für Besucher** (fehlende Angaben zu Parken, Gebühr, Webcam, Verleih melden). Gibt es noch nicht als Anforderung. Wer: `Claude` macht einen kleinen Plan, `Stefan` gibt frei.
- [ ] **Mail-Abo und „Angabe falsch? Melden“ einschalten** (gebaut, aber aus): Postfach `abo@`, SMTP-Werte in die .env. Checkliste 10a. Wer: `Stefan`.
- [ ] **Push für Besucher einschalten**: `LOIPEN_PUSH_PRAEFIX` setzen, mit ntfy-App testen. Checkliste 10b. Wer: `Stefan`.
- [ ] **Spendenlink**: PayPal.Me anlegen, Adresse in die .env. Checkliste 14a. Wer: `Stefan`.
- [ ] **Besucherzähler einschalten**: Passwort in die .env, einmal am PC und Handy anmelden. Checkliste 14b. Wer: `Stefan`.
- [ ] **Rechnungsbeträge** in `config/kosten.yaml` (Nachricht an einen Thread genügt). Checkliste 17. Wer: `beide`.

### Priorität 3: offene Entscheidungen für dich

- [ ] **Design-Vorschläge** aus der Impeccable-Prüfung (Liste einklappen, Kartenfarben geschlossen/unbekannt, Filter am Handy, Startseite schlanker, alte Daten ehrlich zeigen, …). Liste im Projektordner `impeccable-pruefung/vorschlaege.md`. Wer: `Stefan` wählt, `Claude` baut.
- [ ] **Lungau/Kärnten-Rest**: nur über bergfex erreichbar, anbinden oder lassen? Wer: `Stefan`.
- [ ] **Zugspitz Arena**: nur über Intermaps (Bezahldienst), anbinden oder lassen? Wer: `Stefan`.
- [ ] **seefeld-tourinfra**: Soll Seefeld auch den Loipenmanager ausdrücklich freigeben? Dann kurze Rückfrage an region@seefeld.com. Wer: `Stefan` entscheidet, `Claude` schreibt den Entwurf.

---

## 2. Beim nächsten NAS-Neustart in die .env aufnehmen

> **Nur die Namen stehen hier, nie die Werte.** Passwörter und Schlüssel gehören nur in die `.env` auf dem NAS, nicht in Nachrichten, nicht ins Repo. Nach dem Eintragen den Container neu erstellen ([nas-update.md](nas-update.md)). Vorlage mit Erklärung: [`.env.example`](../.env.example).

Jetzt:

- [ ] `LOIPEN_OEFFENTLICHE_URL` – die spätere Hauptadresse (`https://loipen-blick.de`). Ohne sie keine Sitemap und keine Meldung an Bing.
- [ ] `LOIPEN_ZAEHLER_PASSWORT` – eigenes Passwort, mindestens 12 Zeichen (Besucherzähler).
- [ ] `LOIPEN_SMTP_HOST`, `LOIPEN_SMTP_PORT`, `LOIPEN_SMTP_BENUTZER`, `LOIPEN_SMTP_PASSWORT` – jetzt schon nötig für die Absturz-Mails des Workers (B34), später auch fürs Mail-Abo.
- [ ] `LOIPEN_FEHLER_MAIL` (optional) – Empfänger der Absturz- und Fehler-Mails; leer = `LOIPEN_WAECHTER_MAIL`, sonst Impressum-Adresse.
- [ ] `LOIPEN_FEHLER_MAIL_STUNDEN` (optional, Standard 6) – Fehler-Mails höchstens so oft, 0 = nur bei Absturz.
- [ ] `LOIPEN_USER_AGENT` – Kontaktadresse statt Platzhalter (z. B. `service@loipen-blick.de`), damit Quellbetreiber uns erreichen.
- [ ] `CDSAPI_KEY` und `CDSAPI_URL` – Copernicus-Schlüssel für die Schneekarte (laut Stand 24.11. schon eingetragen, beim Neustart nur prüfen).

Wenn gewünscht:

- [ ] `LOIPEN_SPENDEN_URL` – PayPal.Me-Link.
- [ ] `LOIPEN_PUSH_PRAEFIX` – z. B. `loipenblick-` plus drei bis fünf zufällige Zeichen.

Später (Mail-Abo, Livegang):

- [ ] `LOIPEN_ABO_SCHLUESSEL`, `LOIPEN_ABO_ABSENDER`, `LOIPEN_ABO_MELDUNGEN_AN` – Mail-Abo und Meldungen.
- [ ] `LOIPEN_DATENSCHUTZ_DATEI` – nur wenn du einen eigenen Datenschutztext nimmst.
- [ ] `LOIPEN_OEFFENTLICH=true` und Upload-Pfad der Hauptadresse – **erst am Livegang-Tag**.

---

## 3. Wartet auf Antworten Dritter

Erlaubnis-Mails verschickt am 19.11.2026. **Frist: 11.12.2026.** Bei Schweigen zeigen wir die Quelle mit Quellenhinweis (Regel aus der Livegang-Planung). Stand je Stelle in [kontaktliste.md](kontaktliste.md).

- [ ] **Chiemgau GmbH** – vorerst keine Freigabe (20.11.), unsere Antwort ging am 21.11. raus. Bis dahin nur Testseite. Wenn bis Mitte Dezember nichts kommt: green-solutions (Systemanbieter) fragen. Wer: warten, dann `beide`.
- [ ] **Kitzbüheler Alpen** – noch nicht angefragt, Adresse fehlt. Wer: `Stefan` sucht Adresse im Impressum, `Claude` passt die Mail an.
- [ ] **Seefeld, tourinfra-Loipenmanager** – Zusage vom 27.11. nennt nur seefeld.com, tourinfra bleibt `ausstehend` (siehe Priorität 3).
- [ ] **Kaiserwinkl** – Zusage liegt vor, der Verband meldet sich wegen eines Widgets noch einmal. Dann neu entscheiden.
- [ ] **Ohne Antwort bisher:** Tegernseer Tal, Bayrischzell, Fischbachau, Aschau (Sachrang), Tannheimer Tal, Kufsteinerland, Faistenau, Berchtesgaden, Lungau.
- [ ] **Noch gar nicht angefragt** (vor öffentlicher Anzeige nötig oder bewusst `nur_test`): Zillertal, St. Anton, Dolomiti NordicSki, Engadin, Davos Klosters, Goms, Gastein, Ramsau, infosnow.ch, Nassfeld, Steiermark, Ortsseiten der Querprüfung. Liste in der Kontaktliste.
- [ ] **Schneekarte:** Lawinenwarndienste (Euregio, LWD Bayern, Salzburg) vor Livegang der Schneekarte anfragen. Wer: `Claude` Entwurf, `Stefan` verschickt.

---

## 4. Backlog (später)

- [ ] **Dezember: zweiter Satz Schnappschüsse** mit echtem Schnee und echten Saisonwörtern (P18 AK 2). Wer: `Claude`.
- [ ] **Nutzungsbedingungen aller Quellen prüfen** vor der öffentlichen Seite (inkl. steiermark.com). Wer: `Claude`.
- [ ] **Nur am NAS prüfbar:** Hyper-Backup-Ordner, echte .env, Push in der Handy-App, Dauerbetrieb. Wer: `Stefan`.
- [ ] **Workflow „Live-Prüfung“** einmal von Hand starten; optional Repo-Variable `LOIPEN_USER_AGENT`. Wer: `Stefan` (ein Klick auf GitHub unter „Actions“).
- [ ] **Let's Encrypt für die Hauptadresse** prüfen und „HTTP auf HTTPS“ an. Für test. läuft es schon. Wer: `Stefan`.
- [ ] **kontakt@ / service@-Weiterleitung** endgültig prüfen. Wer: `Stefan`.
- [ ] **UptimeRobot und Healthchecks** beim Livegang auf die Hauptadresse umstellen (für test. eingerichtet). Wer: `Stefan`.
- [ ] **Mehr Angaben je Loipe für den Google-Index** ([Issue #54](https://github.com/elron27/loipenblick/issues/54)), Start Januar 2027 nach den ersten Search-Console-Daten. Wer: `Claude`.
- [ ] **SEO Phasen 3–5** (Themenseiten, Outreach beim ersten großen Schneefall, Messen). Noch nicht freigegeben. Wer: `Stefan` gibt frei.
- [ ] **Schneekarte:** 7 Tage Sammeln beobachten, Archive nachladen, danach vier Designs zur Auswahl. Wer: `Claude`, Auswahl `Stefan`.
- [ ] **Cookies mit Banner** nur, falls der Besucherzähler nicht reicht (E-14, B18). Wer: `Stefan` entscheidet.
- [ ] **Ausbau weiterer Regionen** (Südtirol-Rest, Kärnten, Schweiz) nach dem Livegang.

---

## 5. Erledigt

Neueste oben. Vor dem 19.11. nur die großen Schritte.

- [x] 28.11. Parken und Loipengebühren recherchiert: 26 Gebiete neu mit Loipengebühr (jetzt 40), u. a. Seefeld/Leutasch, Ötztal, Pitztal, Osttirol, Zugspitz Arena, Tannheimer Tal, Gastein, Ramsau, Tauplitz, Inzell, Chieming; Parkplatz Aschauerweiher; Saisonprüfung liest „Euro 12,00“ – PR folgt

- [x] 27.11. Loipen-Recherche Etappe 4: St. Johann, Seefeld, Leutasch, Tux, Gerlos, Verleih Ruhpolding/Berchtesgaden, Webcams Pillerseetal – PR #61
- [x] 27.11. Worker-Absturz behoben (Loipenseite scheiterte an OSM-Parkplätzen ohne Gebühr, Absturz bei jedem Start; kaputte Einzelseiten stoppen den Lauf nicht mehr). Log zusätzlich in `logs/worker.log` (rotierend), Mail mit Traceback und Log bei Absturz, hartem Abbruch und gesammelten Fehlern, Geheimnisse geschwärzt; ein Fehler im ersten Lauf beendet den Container nicht mehr (B34) – PR #60
- [x] 27.11. Loipen näher recherchiert, Etappen 1–3 (Tegernsee bis Fuschlsee, Berchtesgaden, Kitzbüheler Alpen, Wilder Kaiser, Pillerseetal, Alpbachtal, Wildschönau): 36 Webcams, 10 Verleihe, Gebühren, Merkmale Einkehr/Familie; neue Felder Hunderegel und beleuchtete Loipen (D25) – PR #57
- [x] 27.11. Besucherzähler zeigt Herkunft und Gerät – PR #52
- [x] 27.11. Seefeld erlaubt Loipenstatus von seefeld.com – PR #55
- [x] 26.11. Eigene Seiten je Gebiet und Loipe, Sitemap, robots.txt, IndexNow (SEO Phase 1+2) – PR #53
- [x] 25.11. Achensee endgültig abgelehnt, nur noch auf der Testseite – PR #51
- [x] 25.11. Besucherzähler ohne Cookies – PR #50
- [x] 25.11. Design-Prüfung: Kontrast, Tippflächen, Feldränder – PR #49
- [x] 24.11. Kaiserwinkl erlaubt – PR #48
- [x] 24.11. Mehr Daten je Loipe: tourinfra-Stammdaten, OSM-Routen, Webcams Bayrischzell, Saisonprüfung – PR #47
- [x] 23.11. Schneekarte: Sammel-Job, Datenmodell, ERA5-Land – PR #43, #45
- [x] 23.11. Tirol Werbung erlaubt tirol.at – PR #44
- [x] 21.11. Antwort an Chiemgau GmbH verschickt – PR #42
- [x] 20.11. Worker robuster (Wiederholungen, tote Seiten) – PR #40
- [x] 20.11. Achensee abgeschaltet nach Absage – PR #41
- [x] 20.11. Chiemgau nur Testseite – PR #39
- [x] 20.11. Benachrichtigung je Loipe, Push ohne Konto – PR #38
- [x] 20.11. Allgäu über Ortsseiten – PR #37
- [x] 20.11. Strecken und Parkplätze aus OpenStreetMap – PR #35
- [x] 20.11. Spendenlink eingebaut – PR #34
- [x] 19.11. Testseite test.loipen-blick.de läuft (FTPS-Upload, Let's Encrypt für test., UptimeRobot, Healthchecks)
- [x] 19.11. 15 Erlaubnis-Mails verschickt
- [x] 19.11. netcup Webhosting 1000 bestellt, Domain loipen-blick.de, AVV abgeschlossen – PR #24
- [x] 19.11. Plausibilitätsprüfung und Erlaubnis-Status je Quelle – PR #26, #27
- [x] 19.–20.11. Ortsseiten Tirol zur Querprüfung – PR #28, #29, #31, #32
- [x] 14.11. Schweiz, Liechtenstein, St. Anton, Kärnten, Steiermark – PR #20, #22, #23
- [x] 13.11. Livegang Teil 1: Upload, Impressum, Datenschutz, Hinweise – PR #13, #14
- [x] 13.11. Mail-Abo, Statistik, Handy-App, Südtirol, Standort und Talprofil – PR #11, #15–#18
- [x] 12.11. Ausbaustufe 1: Tirol, Kitzbühel, Salzburger Umland, Berchtesgaden – PR #8, #10
- [x] 11.–12.11. Zusammenarbeitsregeln, Tests für alle V1-Anforderungen, Testumgebung ohne NAS – PR #5, #6, #7
- [x] 9.11. Gerüst, Anforderungen als ReqSeq, erste Seite – PR #1–#4
