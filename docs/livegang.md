# Livegang im Winter 2026/27

Stand 13.11.2026. Recherche und Abwägung. Teil 1 der Umsetzung (Upload, Textseiten, Header, Karte nach Klick) ist im Code, siehe [README, Online stellen](../README.md#online-stellen-livegang). Ziel: Die statische Seite, die das NAS erzeugt (E-10), geht noch diesen Winter öffentlich online, für höchstens 5 € im Monat (N-08, B9).

> **Keine Rechtsberatung.** Die rechtlichen Abschnitte fassen Gesetzestexte, Leitfäden von Aufsichtsbehörden und Ratgeberseiten zusammen und nennen die Quelle. Für eine verbindliche Auskunft ist eine Anwältin oder ein Anwalt zuständig. Wo eine Aussage nicht geprüft werden konnte, steht das dabei.

Die Anforderungen dazu stehen in `spec/` (Filter `livegang`, Entscheidung E-17). Was Stefan selbst tun muss, steht in [livegang-checkliste-stefan.md](livegang-checkliste-stefan.md).

## Kurzfassung

| Thema | Empfehlung |
|---|---|
| Hosting | Deutscher Webspace mit SFTP oder FTPS, z. B. netcup Webhosting 1000 (2,69 €/Monat mit .de-Domain). Zweite Wahl: Cloudflare Pages (kostenlos, aber US-Anbieter, max. 25 MiB je Datei). |
| Domain | .de, im Webspace-Tarif enthalten oder bei INWX (4,71 € Registrierung, 3,60 € Verlängerung pro Jahr). |
| Update vom NAS | Upload in zwei Phasen: zuerst Daten-Dateien mit Inhalts-Hash im Namen, zuletzt `index.json` und HTML. Ein abgebrochener Upload lässt die alte Seite heil. |
| Impressum | Nötig (§ 18 Abs. 1 MStV): Vor- und Nachname plus ladungsfähige Anschrift. Postfach reicht nicht. Lösung für die Privatadresse: Adresse mit Zustellungsvollmacht (Familie, Büroservice, Anwalt). |
| Datenschutz | Datenschutzerklärung nötig. Ziel: Die Seite lädt beim Aufruf nichts von fremden Servern, dann braucht es keinen Cookie-Banner. Dafür die Kartenkacheln selbst hosten oder erst nach Klick laden. |
| Statistik | Erst ohne Cookies (Zugriffsstatistik des Webspace oder GoatCounter). Cookies mit Banner (E-14) erst, wenn das nicht reicht. |
| Datenquellen | Fakten (offen, km, Datum) sind frei, die Sammlung kann aber als Datenbank geschützt sein (§ 87b UrhG). Vor dem Livegang die Betreiber per Mail um Erlaubnis bitten, zuerst Tirol Werbung (701 Loipen). |
| Haftung | „Ohne Gewähr“ ist schon da (B15). Dazu ein Hinweis, dass Sperrungen und Beschilderung vor Ort gelten. |
| Monitoring | UptimeRobot (kostenlos) prüft die Seite von außen, Healthchecks.io (kostenlos) merkt, wenn das NAS keine Daten mehr schickt. |
| Kosten | ca. 32 € im Jahr mit netcup (Webspace und Domain), Budget 60 €. |

## 1. Was die Seite vom Hosting braucht

Die erzeugte Seite (`site/`) besteht aus HTML, CSS, JavaScript, JSON und Bildern. Leaflet liegt schon lokal unter `vendor/`, Schriften kommen nicht von Google. Daraus folgen diese Anforderungen:

| Anforderung | Warum | Wo im Spec |
|---|---|---|
| Nur statische Dateien, kein PHP, keine Datenbank | E-10 | B7 |
| HTTPS mit automatisch erneuertem Zertifikat (z. B. Let's Encrypt), HTTP leitet um | GPS-Standort und Service Worker funktionieren im Browser nur über HTTPS (siehe [Befund vom 13.11.](#befunde-aus-dem-bisherigen-betrieb)) | B20 |
| Eigene Domain | Unabhängig vom Anbieter, Adresse bleibt beim Umzug | B20 |
| Upload per SFTP oder FTPS (verschlüsselt), eigenes Konto nur für den Web-Ordner | Zugangsdaten auf dem NAS, kein Klartext-FTP | B8, B21 |
| Server-Standort Deutschland oder EU, Vertrag zur Auftragsverarbeitung (AVV, Art. 28 DSGVO) | Der Webspace sieht die IP-Adressen der Besucher | B6 |
| Eigene Header per `.htaccess` (Apache) oder Konfiguration | Cache-Steuerung, Sicherheits-Header, HSTS | B24 |
| HTTP-Range-Requests | Nur nötig für selbst gehostete Kartenkacheln als PMTiles-Datei (Abschnitt 6) | B23 |
| Einzeldateien über 25 MiB | Nur für PMTiles | B23 |
| Traffic | Unkritisch: Die Seite ist klein, die Daten pro Region einige 100 KB. Selbst gehostete Kacheln machen den größten Teil aus. | – |
| Zugriffsstatistik ohne Cookies | Statistik ohne Banner (B13) | B13 |

## 2. Anbieter-Vergleich

Preise laut Anbieterseite am 13.11.2026, inklusive 19 % MwSt.

| Anbieter | Preis | Domain | Upload | Standort | Bewertung |
|---|---|---|---|---|---|
| **netcup Webhosting 1000** | 2,69 €/Monat, 12 Monate Laufzeit | 1 .de inklusive | „SSH access available“ laut Tarifliste, die Vergleichstabelle derselben Seite sagt „nicht enthalten“. Vor Bestellung prüfen. | Deutschland (laut Tabelle auch AT/USA, beim Bestellen wählen) | **Empfehlung.** Günstig, Domain dabei, deutscher Vertrag. [Quelle](https://www.netcup.com/en/hosting/hosting-comparison) |
| Hetzner Webhosting S | 1,90 €/Monat, keine Mindestlaufzeit | nicht enthalten, ab 5,83 €/Jahr | SSH erst ab Tarif L (9,90 €) | Nürnberg | Gut, wenn netcup nicht passt. [Quelle](https://www.hetzner.com/de/webhosting/) |
| all-inkl Privat | 4,95 €/Monat, monatlich kündbar | 3 inklusive | SSH erst ab Premium (9,95 €); SSL in der Liste erst ab Privat+ (7,95 €) genannt | Deutschland | Am Budgetrand, SSL unklar. [Quelle](https://all-inkl.com/webhosting/) |
| Uberspace | Zahl, was du für fair hältst | eigene Domain möglich | volle Linux-Shell, also SSH und rsync | nicht angegeben | Technisch am bequemsten (rsync, atomarer Wechsel per Symlink), Preis selbst gewählt. [Quelle](https://uberspace.de/de/) |
| **Cloudflare Pages** | 0 € | eigene Domain (DNS bei Cloudflare) | `wrangler pages deploy site/`, jede Veröffentlichung ist ein eigener Stand mit Rollback | weltweites Netz, US-Firma | **Zweite Wahl.** Unbegrenzte Bandbreite, atomare Deploys. Aber: max. 20.000 Dateien und 25 MiB je Datei, also keine PMTiles-Karte; US-Anbieter in der Datenschutzerklärung; Node/wrangler auf dem NAS. [Limits](https://developers.cloudflare.com/pages/platform/limits/), [Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/), [Bandbreite](https://pages.cloudflare.com/) |
| GitHub Pages | 0 € | eigene Domain | Push in ein Repo | US-Firma | Nicht empfohlen: Die Daten lägen mit Historie in einem öffentlichen Repo (Datenbankrecht, Abschnitt 8), dreimal täglich ein Commit bläht das Repo auf (Limit 1 GB), Soft-Limit 100 GB/Monat. [Quelle](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) |
| Netlify Free | 0 € | eigene Domain | CLI | US-Firma | Fällt raus: 300 Credits im Monat, ein Produktions-Deploy kostet 15. Drei Läufe am Tag sind 90 Deploys, also 1.350 Credits. [Quelle](https://www.netlify.com/pricing/) |

**Warum Webspace vor Cloudflare Pages:** Stefan will Deutschland/EU und eine einfache Datenschutzerklärung. Ein deutscher Webspace hat einen deutschen AVV, kein Drittland, kann große Kartendateien ausliefern und braucht auf dem NAS nur einen SFTP-Client. Den Vorteil von Cloudflare (atomare Deploys) holt der Upload-Ablauf in Abschnitt 4 nach. Bleibt netcup ohne SFTP/SSH, geht FTPS (FTP über TLS) genauso.

## 3. Domain

- **Endung .de.** Bei DENIC sind die Inhaberdaten von Privatpersonen im öffentlichen Whois nicht sichtbar, nur der Provider ([DENIC](https://www.denic.de/services/whois-service/)). Die Privatadresse erscheint also nicht über die Domain, sondern nur über das Impressum.
- **Registrar.** Im netcup-Tarif ist eine .de-Domain enthalten. Sonst INWX: 4,71 € Registrierung, 3,60 € Verlängerung pro Jahr ([INWX](https://www.inwx.de/de/domain/pricelist)). Ob die Preise brutto sind, war auf der Seite nicht eindeutig.
- **Name.** Kurz, ohne Umlaut, z. B. `loipenblick.de`. Ob er frei ist, prüft Stefan bei DENIC. Keine Ortsnamen oder Marken Dritter im Namen (z. B. nicht „tirol-loipen.de“), um Streit um Namensrechte zu vermeiden.
- **E-Mail.** Eine Adresse auf der Domain (z. B. `kontakt@…`) als Weiterleitung auf Stefans Postfach. Sie steht im Impressum und auf der Seite für Quellbetreiber (B16). Die meisten Webspace-Tarife haben Weiterleitungen dabei.

## 4. Update-Workflow vom NAS

### Ablauf (B8, B21)

Nach jedem erfolgreichen Lauf (Saison 7, 12, 17 Uhr) lädt der Worker die neue Seite hoch. Nur das NAS baut die Verbindung auf, das Heimnetz bleibt zu (N-09).

1. **Erzeugen.** Der Generator schreibt Daten-Dateien mit Inhalts-Hash im Namen, z. B. `daten/region-tirol.3f2a9c.json`. `index.json` verweist auf die aktuellen Namen. Gleiche Daten ergeben den gleichen Namen, unveränderte Regionen werden nicht neu hochgeladen.
2. **Phase 1: neue Dateien.** Alle Dateien hochladen, die es auf dem Server noch nicht gibt. Vorhandene Dateien werden nie überschrieben.
3. **Phase 2: Einstieg.** Zuletzt `index.json`, `index.html` und `sw.js` hochladen, jeweils zuerst unter einem temporären Namen und dann per Umbenennen (SFTP `rename` ist auf demselben Dateisystem atomar). Erst jetzt sehen Besucher den neuen Stand.
4. **Prüfen.** `https://<domain>/index.json` abrufen und den Stand vergleichen. Stimmt er nicht, gilt der Upload als fehlgeschlagen.
5. **Aufräumen.** Hash-Dateien löschen, auf die weder der aktuelle noch der vorige Stand verweist. So bekommt ein Browser, der gerade noch den alten Index geladen hat, seine Daten.

Mit SSH-Zugang geht es noch einfacher: `rsync` in einen neuen Ordner `releases/<stand>/`, dann den Symlink `aktuell` umbiegen. Das setzt voraus, dass der Webserver dem Symlink folgt, und ist deshalb nur eine Option.

### Fehlerfall

- Bricht der Upload ab, bleibt die alte Seite vollständig (Phase 2 ist noch nicht gelaufen). Der nächste Lauf holt den Upload nach.
- Drei Versuche mit Pause (30 s, 2 min, 10 min), dann Fehler ins Parser-Monitoring (B2) und Push über ntfy, einmal beim Wechsel wie heute bei den Quellen.
- Ist das NAS aus, liefert der Webspace weiter den letzten Stand (B10), die Seite zeigt ab 48 h einen Hinweis auf das Alter (U6).

### Zugangsdaten

- Eigenes SFTP/FTPS-Konto nur für den Web-Ordner, nicht das Hauptkonto des Webspace.
- Passwort oder SSH-Schlüssel (ed25519) nur in der `.env` auf dem NAS (`LOIPEN_UPLOAD_URL`, `LOIPEN_UPLOAD_BENUTZER`, `LOIPEN_UPLOAD_PASSWORT` oder `LOIPEN_UPLOAD_SCHLUESSEL`). Nichts davon im Repo, in Memory oder in Nachrichten (CLAUDE.md Regel 15).
- Den Fingerabdruck des Servers einmal festhalten (`known_hosts`), damit der Upload nicht an einen falschen Server geht.
- Bei Cloudflare: API-Token nur mit dem Recht „Cloudflare Pages: Edit“.

### Werkzeug

Im Worker-Image reicht Python mit `paramiko` (SFTP) oder `ftplib` mit TLS (FTPS), beides ohne Zusatzdienst. Alternative ist `lftp` im Image. Der Upload wird im Teststack gegen einen lokalen SFTP-Container geprüft, genauso wie heute ntfy.

### Testphase vor dem Livegang

Erst auf eine Testadresse hochladen (Subdomain `test.<domain>`). Solange `LOIPEN_OEFFENTLICH=false` ist, schickt die Seite `noindex` und eine sperrende `robots.txt`. Ein Passwortschutz per `.htaccess` geht nicht, weil der Upload die eigene `.htaccess` mitbringt. Sobald Impressum, Datenschutz und die Antworten der Quellen da sind, auf die Hauptadresse umstellen. Das Öffentlichschalten ist ein Schritt, den nur Stefan freigibt (CLAUDE.md Regel 6).

## 5. Impressum

### Pflicht

- **§ 5 DDG** (früher TMG) gilt für „geschäftsmäßige, in der Regel gegen Entgelt angebotene digitale Dienste“ ([Gesetz](https://www.gesetze-im-internet.de/ddg/__5.html)). Ohne Werbung, Spenden-Aufruf oder Affiliate-Links ist Loipenblick das eher nicht. Schon ein Werbebanner würde das ändern ([e-recht24](https://www.e-recht24.de/impressum/13095-impressum-fuer-die-private-homepage.html), [NLM-Leitfaden](https://www.nlm.de/fileadmin/dateien/pdf/leitfaden_impressumspflicht_2024.pdf), Abschnitt 2.1).
- **§ 18 Abs. 1 MStV** gilt für alle Angebote, die „nicht ausschließlich persönlichen oder familiären Zwecken dienen“. Die Landesmedienanstalten legen die Ausnahme „sehr eng“ aus. Eine Seite für die Öffentlichkeit fällt darunter ([NLM-Leitfaden](https://www.nlm.de/fileadmin/dateien/pdf/leitfaden_impressumspflicht_2024.pdf), Abschnitt 2.3, [Datenschutz-Generator](https://datenschutz-generator.de/ratgeber-impressum/)).
- **Pflichtangaben** nach § 18 Abs. 1 MStV: Vor- und Nachname und eine ladungsfähige Anschrift. Telefon ist nicht verlangt. Eine E-Mail-Adresse wird trotzdem empfohlen (Kontakt für Quellbetreiber, B16).
- **§ 18 Abs. 2 MStV** (Verantwortlicher für journalistisch-redaktionelle Inhalte) betrifft eher Nachrichten und Blogs. Eine Datenübersicht ist das eher nicht. Wer sicher gehen will, schreibt „Verantwortlich nach § 18 Abs. 2 MStV: <Name, Anschrift>“ dazu, das kostet nichts.

### Problem Privatadresse und Lösungen

Laut NLM-Leitfaden (Abschnitt 2.3.2) darf die Anschrift auch die einer Agentur, eines Büroservices, eines Rechtsanwalts oder eines Familienangehörigen sein, wenn dort wirksam zugestellt werden kann, also mit **Zustellungsvollmacht**. Eine bloße Drittanschrift oder ein Postfach reicht nicht.

| Lösung | Kosten | Bewertung |
|---|---|---|
| Eigene Wohnadresse | 0 € | Einfach und sicher, aber die Adresse ist öffentlich. |
| Adresse eines Familienangehörigen mit schriftlicher Zustellungsvollmacht | 0 € | Gut, wenn jemand Post zuverlässig weitergibt. |
| Impressum- oder Anschriftenservice (c/o, Büroservice) mit Zustellungsvollmacht | Preise nicht geprüft, meist ein Monatsbetrag | Schützt die Privatadresse, kann das Budget von 5 €/Monat sprengen. Vor Vertrag prüfen, dass Gerichtspost angenommen und weitergeleitet wird. |
| Postfach, nur E-Mail | – | Reicht nicht. |

**Empfehlung:** Adresse eines Familienangehörigen mit Vollmacht, sonst die eigene Adresse. Ein Service lohnt erst, wenn die Seite wächst.

## 6. Datenschutz, Cookies und Einwilligung

Eine öffentliche Seite ist keine rein private Tätigkeit, die DSGVO gilt also. Stefan ist Verantwortlicher. Was die Seite heute mit Daten tut (geprüft im Code, `loipen/generator/static/`):

| Was | Wohin | Folge |
|---|---|---|
| Aufruf der Seite | Webspace, Zugriffsprotokoll mit IP | In der Datenschutzerklärung nennen, Rechtsgrundlage berechtigtes Interesse (Art. 6 Abs. 1 lit. f DSGVO), AVV mit dem Hoster, Löschfrist der Logs (beim Hoster einstellen, z. B. 7 Tage). |
| Kartenkacheln von `tile.openstreetmap.org` | OpenStreetMap Foundation, Protokoll mit IP, Speicher UK/NL, Auslieferung über ein weltweites CDN ([OSMF](https://osmfoundation.org/wiki/Privacy_Policy)) | Siehe unten. |
| GPS-Standort (Knopf „Mein Standort“) | bleibt im Browser, wird nicht gesendet | Nur auf Knopfdruck, Browser fragt selbst. In der Datenschutzerklärung erwähnen. |
| Ortssuche | lokal aus `index.json`, kein Dienst | Nichts zu tun. |
| `localStorage` (gewählter Ort, Einstellungen) und Service-Worker-Cache | im Browser | Ausnahme nach § 25 Abs. 2 Nr. 2 TDDDG: unbedingt erforderlich für einen vom Nutzer ausdrücklich gewünschten Dienst ([Gesetz](https://www.gesetze-im-internet.de/ttdsg/__25.html)). Kein Banner, aber in der Datenschutzerklärung nennen. Nur für Funktionen speichern, die der Nutzer selbst auslöst. |
| Links zu Google Maps (Navigation, Fahrplan) | erst beim Klick | Normaler Link, kein Einbetten. Hinweis in der Datenschutzerklärung genügt. |
| Push über ntfy | nur Stefan und Freunde mit geheimem Thema | Nicht Teil der öffentlichen Seite. Wird Push öffentlich angeboten, kommt ntfy.sh in die Datenschutzerklärung (IP für Rate-Limiting, Nachrichten 12 h zwischengespeichert, [ntfy](https://docs.ntfy.sh/privacy/)). |

### Kartenkacheln

Das Landgericht München I hat 2022 das Laden von Google Fonts vom Google-Server ohne Einwilligung als Verstoß gewertet (Az. 3 O 17493/20; aus dem Gedächtnis, nicht im Original geprüft). Seitdem gilt es als Risiko, beim Seitenaufruf ohne Einwilligung Inhalte von fremden Servern zu laden. Die OSMF-Kacheln sind genau so ein Fall. Außerdem verlangt die [OSM-Kachelrichtlinie](https://operations.osmfoundation.org/policies/tiles/) Attribution (vorhanden), einen gültigen Referer, kein Vorladen für offline und gibt keine Garantie: Zugriffe können ohne Ankündigung gesperrt werden.

| Option | Aufwand | Bewertung |
|---|---|---|
| A: So lassen (OSM-Kacheln direkt) | 0 | Funktioniert, aber Restrisiko DSGVO und keine Verfügbarkeitsgarantie. |
| B: Karte erst nach Klick „Karte laden“ (Zwei-Klick-Lösung) | klein | Rechtlich sauber, etwas umständlicher. Einwilligung im `localStorage` merken. |
| C: Kacheln selbst hosten als PMTiles-Datei auf dem Webspace | mittel | **Empfehlung.** Ein Ausschnitt (Südbayern, Tirol, Salzburg) wird einmal mit `pmtiles extract … --bbox=…` erzeugt und als eine Datei hochgeladen. Der Browser liest per Range-Request nur, was er braucht ([Protomaps](https://docs.protomaps.com/pmtiles/cli)). Keine Anfrage an Dritte, auch offline-fähig, Attribution OSM (ODbL) bleibt. Braucht Range-Support (Apache kann das) und Dateien über 25 MiB, also nicht Cloudflare Pages. Größe und Darstellung (Vektor-Stil, ggf. MapLibre statt reiner Leaflet-Raster) im Umsetzungsschritt prüfen. |

Für den Livegang reicht B. C ist das Ziel, wenn es bis Dezember fertig wird.

### Cookie-Banner

Ziel ist eine Seite ohne Banner: Keine Cookies, keine Drittanbieter beim Aufruf (B23). Dann braucht es keine Einwilligung.

Die Nutzungsstatistik (B13) zuerst ohne Cookies:

- Zugriffsstatistik des Webspace (aus den Server-Logs), kostet nichts extra.
- Oder [GoatCounter](https://www.goatcounter.com/): zählt ohne Cookies und ohne dauerhafte Kennungen, kostenlos für vernünftige Nutzung. Laut [Betreiber](https://www.goatcounter.com/help/gdpr) „wahrscheinlich“ ohne Banner (der Betreiber ist kein Anwalt). Ist aber ein Drittanbieter, also in die Datenschutzerklärung. Der Serverstandort ließ sich nicht prüfen.

Entscheidung E-14 (Cookies mit Einwilligung) bleibt gültig, wird aber erst gebraucht, wenn diese Zahlen nicht reichen. Dann gilt B18.

### Datenschutzerklärung

Inhalt: Verantwortlicher (wie Impressum), Hosting und Server-Logs mit Frist, AVV, Karte (je nach Option), Standort im Browser, `localStorage` und Service Worker, externe Links, Statistik, Rechte der Betroffenen, Beschwerderecht bei der Aufsichtsbehörde (für Privatpersonen in Bayern das Bayerische Landesamt für Datenschutzaufsicht, BayLDA). Ein Generator wie [datenschutz-generator.de](https://datenschutz-generator.de/) oder der von e-recht24 liefert die Texte; die Nutzungsbedingungen des Generators (privat/kostenlos) prüft Stefan selbst. Der Generator der Seite schreibt die Seiten `impressum.html` und `datenschutz.html` aus Vorlagen mit Platzhaltern, die echten Daten kommen aus der `.env` bzw. `config/` auf dem NAS, nicht aus dem Repo.

## 7. Haftungshinweise

- Für eigene Inhalte haftet der Betreiber nach den allgemeinen Gesetzen, auch für übernommene Angaben, wenn er sie sich zu eigen macht. Darum zeigt jede Loipe Quelle und Stand (B15, U5) und verlinkt die Originalseite.
- Text für die Fußzeile (gibt es schon): „Alle Angaben ohne Gewähr. … maßgeblich ist immer die Quelle vor Ort.“
- Neu auf einer Seite „Hinweise“: Der Status kann veraltet sein; Sperrungen, Beschilderung und Hinweise der Betreiber vor Ort gehen vor; Loipenbenutzung auf eigene Gefahr; ggf. Loipengebühr (Österreich) beachten.
- Ein „Disclaimer“ schließt die gesetzliche Haftung nicht aus, er macht aber klar, was die Seite ist. Wichtiger ist, veraltete Daten deutlich zu kennzeichnen (U6, „unbestätigt“ aus P22) und Fehler nach Hinweis schnell zu korrigieren.

## 8. Nutzungsbedingungen und Rechte der Datenquellen

### Rechtslage kurz

- Reine Fakten (Loipe offen, 12 km gespurt, präpariert am 13.12.) sind nicht urheberrechtlich geschützt. Texte und Fotos der Seiten schon. Loipenblick übernimmt nur Fakten und zeigt keinen Rohtext (geprüft in `loipen/generator/daten.py`).
- **Datenbankherstellerrecht, § 87b UrhG:** Wer viel in eine Datenbank investiert hat, hat das ausschließliche Recht, sie „insgesamt oder einen nach Art oder Umfang wesentlichen Teil“ zu vervielfältigen und öffentlich wiederzugeben. Gleichgestellt ist die „wiederholte und systematische“ Übernahme unwesentlicher Teile, wenn sie der normalen Auswertung zuwiderläuft ([Gesetz](https://www.gesetze-im-internet.de/urhg/__87b.html)). Das Recht beruht auf der EU-Datenbankrichtlinie und gilt so auch in Österreich. Alle 701 Loipen von tirol.at dreimal täglich zu übernehmen, ist genau dieser Fall. Ein Urteil zu Loipendaten gibt es nach meiner Recherche nicht; das Risiko ist realistisch eine Aufforderung zur Unterlassung, mit Abmahnkosten.
- **Gegenmittel:** Erlaubnis einholen, jede Loipe mit Quelle und Link (lenkt Besucher zur Quelle, nützt dem Betreiber), Abschalten einer Quelle per Konfiguration (B16), kein Text und keine Bilder.

### Quelle für Quelle

| Quelle | Befund | Vor dem Livegang |
|---|---|---|
| tirol.at (Tirol Werbung GmbH, Innsbruck) | Impressum: fremde Inhalte werden mit Quelle gekennzeichnet; keine Aussage zu Weiterverwendung oder automatischem Abruf. Eigene Nutzungsbedingungen-Seite war nicht abrufbar ([Impressum](https://www.tirol.at/impressum)). | **Erlaubnis anfragen** (info@tirol.at). Größte Quelle, höchste Priorität. |
| tegernsee.com, bayrischzell.de, fischbachau.de | Tegernsee-Impressum: Texte, Bilder, Layout geschützt, unerlaubte Verwendung wird verfolgt ([Impressum](https://www.tegernsee.com/impressum)). Zu Daten nichts. | Erlaubnis anfragen (info@tegernsee.com u. a.). |
| tourinfra (Chiemgau, Tannheimer Tal), aschau.de, Kitzbüheler Alpen, langlaufdorf.at, berchtesgaden.de, seefeld.com, achensee.com, kufstein.com, kaiserwinkl.com | Nicht einzeln geprüft. | Erlaubnis beim jeweiligen Tourismusverband anfragen (Sammelmail, Vorlage unten). |
| DWD (direkt und über Bright Sky) | Daten frei und ohne Registrierung ([README](https://opendata.dwd.de/README.txt)). Es gelten die DWD-Nutzungsbedingungen und die GeoNutzV: Quellenvermerke mitführen, Veränderungen kennzeichnen ([§ 3 GeoNutzV](https://www.gesetze-im-internet.de/geonutzv/__3.html)). Die DWD-Seite mit dem genauen Wortlaut blockiert automatische Abrufe und ist nicht geprüft. | Quellenvermerk „Quelle: Deutscher Wetterdienst“ bei den Wetterwerten, Wortlaut auf dwd.de von Hand prüfen. |
| GeoSphere Austria | CC BY 4.0, Pflichtangabe „Datenquelle: GeoSphere Austria - https://data.hub.geosphere.at“ ([Rechtliches](https://data.hub.geosphere.at/legal), [API](https://dataset.api.hub.geosphere.at/v1/docs/)). | Wortlaut mit Link ergänzen (heute steht nur „GeoSphere Austria (CC BY 4.0)“). |
| OpenStreetMap | ODbL, Attribution „© OpenStreetMap-Mitwirkende“ mit Link ([Richtlinie](https://operations.osmfoundation.org/policies/tiles/)). | Vorhanden. Bleibt auch bei selbst gehosteten Kacheln. |
| Google Maps | Nur Links, keine Daten. | Nichts. |

P17 verlangt schon, dass jede Quelle in `sources.yaml` „Nutzungsbedingungen geprüft am“ trägt. Neu: auch „Erlaubnis angefragt am / Antwort“.

### Vorlage für die Anfrage an Quellbetreiber

> Betreff: Loipenstatus auf loipenblick.de verlinken
>
> Guten Tag,
>
> ich betreibe privat und ohne Werbung die Seite <domain>, eine Übersicht über den Loipenzustand zwischen Tegernsee, Chiemgau und Tirol. Ich möchte dort den Status Ihrer Loipen zeigen (offen/geschlossen, gespurte Kilometer, Datum der Präparierung), jeweils mit Ihrem Namen als Quelle und einem Link auf Ihre Seite. Texte und Bilder übernehme ich nicht. Die Daten rufe ich höchstens dreimal am Tag automatisch von <URL> ab.
>
> Sind Sie damit einverstanden? Wenn Sie eine Schnittstelle oder einen bestimmten Quellenhinweis bevorzugen, richte ich mich gern danach. Auf Wunsch nehme ich Ihre Loipen jederzeit heraus.
>
> Viele Grüße
> <Name>, <Kontakt>

Ohne Antwort nach zwei Wochen: Quelle mit Quellenhinweis und Link zeigen und auf Rückmeldung sofort reagieren, oder sie bis zur Antwort abschalten. Das entscheidet Stefan je Quelle. Eine ausdrückliche Absage heißt: abschalten.

## 9. Was die Seite sonst noch braucht

| Punkt | Stand | Anforderung |
|---|---|---|
| Impressum, Datenschutz | fehlt | B6 |
| Seite „Für Gemeinden und Loipenbetreiber“ mit Kontakt und Opt-out | fehlt | B16 |
| Haftungs- und Sicherheitshinweise | Fußzeile vorhanden, Seite fehlt | B15, B25 |
| Sicherheits-Header (`Strict-Transport-Security`, `Content-Security-Policy` mit `default-src 'self'`, `X-Content-Type-Options`, `Referrer-Policy: strict-origin-when-cross-origin`, damit OSM den Referer bekommt) | fehlt | B24 |
| Cache-Header: HTML und `index.json` kurz, Hash-Dateien „immutable“ | fehlt | B21, B24 |
| Nur freigegebene Dateien im Upload (keine `.env`, keine Dumps, kein Rohtext) | – | B24 |
| `robots.txt`, `sitemap.xml`, eigene Titel je Gebiet | fehlt | B17 (kann nach dem Livegang kommen) |
| Fehlerseite 404 | fehlt | B24 |
| Offline-Hinweis „offline, Stand …“ | halb | U29 |
| Statistik ohne Cookies | fehlt | B13 |

## 10. Monitoring

| Was | Wie | Kosten |
|---|---|---|
| Seite erreichbar, HTTPS gültig | [UptimeRobot](https://uptimerobot.com/pricing/) Free: 50 Monitore, alle 5 min, auch Keyword-Prüfung | 0 € |
| Daten kommen noch an | [Healthchecks.io](https://healthchecks.io/pricing/) Free (20 Checks): Das NAS ruft nach jedem erfolgreichen Upload eine geheime Ping-URL auf. Bleibt der Ping in der Saison länger als 8 h aus, kommt eine Mail. Fällt auch auf, wenn das NAS ganz aus ist. | 0 € |
| Quelle liefert nichts, Upload scheitert | vorhandenes Parser-Monitoring (B2) mit ntfy-Push | 0 € |
| Zertifikat | erneuert der Webspace selbst; UptimeRobot meldet Ablauf | 0 € |

Die Ping-URL ist ein Geheimnis und gehört in die `.env` (`LOIPEN_HEARTBEAT_URL`).

## 11. Kosten

| Posten | netcup (Empfehlung) | Hetzner | Cloudflare Pages |
|---|---|---|---|
| Webspace | 32,28 € | 22,80 € | 0 € |
| Domain .de | inklusive | 5,83 € | 4,71 € (INWX) |
| Monitoring, Statistik, Wetter, ntfy | 0 € | 0 € | 0 € |
| Impressum-Adresse mit Vollmacht in der Familie | 0 € | 0 € | 0 € |
| **Summe pro Jahr** | **ca. 32 €** | **ca. 29 €** | **ca. 5 €** |

Alle liegen unter dem Budget von 60 € (B9). `config/kosten.yaml` wird nach der Bestellung mit echten Beträgen nachgeführt.

## 12. Zeitplan

Annahme: Stefan entscheidet sich bis 20.11. für einen Anbieter. Ziel ist der Livegang vor den Weihnachtsferien, wenn die ersten Loipen gespurt sind.

| Woche | Stefan | Claude (Threads) |
|---|---|---|
| bis 20.11. | Anbieter wählen, Domainnamen prüfen, Impressum-Adresse klären, Anfragen an Quellen schicken | – |
| bis 27.11. | Webspace und Domain bestellen, SFTP-Konto anlegen, Zugang in die NAS-`.env` | Upload mit Fehlerbehandlung (B8, B21), Impressum/Datenschutz-Vorlagen (B6), Seite für Betreiber und Hinweise (B16, B25), Sicherheits-Header (B24) |
| bis 4.12. | Datenschutzerklärung mit Generator erzeugen, Testadresse prüfen, UptimeRobot und Healthchecks anlegen | Karte ohne Drittanbieter (B23), Heartbeat (B22), Statistik ohne Cookies (B13), Teststack mit SFTP |
| bis 11.12. | Antworten der Quellen auswerten, Quellen ohne Erlaubnis entscheiden, **Livegang freigeben** | Umstellung auf Hauptadresse, Kontrolle mit Screenshots Desktop und Handy |

## Befunde aus dem bisherigen Betrieb

- GPS-Standort funktioniert nur über HTTPS, das NAS liefert die Vorschau über HTTP (Befund 13.11.2026). Mit dem Webspace erledigt sich das.
- Der Service Worker cacht nur Dateien der eigenen Seite, keine Kacheln. Das passt zur OSM-Richtlinie (kein Vorladen für offline).
- In der Fußzeile steht schon „Alle Angaben ohne Gewähr“ und die Quellenliste; der GeoSphere-Wortlaut ist zu ergänzen.

## Quellen

- § 5 DDG: https://www.gesetze-im-internet.de/ddg/__5.html
- NLM, Leitfaden Impressumspflicht 2024: https://www.nlm.de/fileadmin/dateien/pdf/leitfaden_impressumspflicht_2024.pdf
- e-recht24, Impressum für die private Homepage: https://www.e-recht24.de/impressum/13095-impressum-fuer-die-private-homepage.html
- Datenschutz-Generator, Ratgeber Impressum: https://datenschutz-generator.de/ratgeber-impressum/
- § 25 TDDDG: https://www.gesetze-im-internet.de/ttdsg/__25.html
- § 87b UrhG: https://www.gesetze-im-internet.de/urhg/__87b.html
- § 3 GeoNutzV: https://www.gesetze-im-internet.de/geonutzv/__3.html
- OSM-Kachelrichtlinie: https://operations.osmfoundation.org/policies/tiles/
- OSMF-Datenschutz: https://osmfoundation.org/wiki/Privacy_Policy
- Protomaps PMTiles: https://docs.protomaps.com/pmtiles/cli
- GeoSphere Austria: https://data.hub.geosphere.at/legal
- DWD Open Data: https://opendata.dwd.de/README.txt
- Bright Sky: https://brightsky.dev/
- DENIC Whois: https://www.denic.de/services/whois-service/
- netcup, Hetzner, all-inkl, Uberspace, INWX, Cloudflare, GitHub, Netlify: Links in Abschnitt 2 und 3
- UptimeRobot, Healthchecks.io, GoatCounter, ntfy: Links in Abschnitt 6 und 10
