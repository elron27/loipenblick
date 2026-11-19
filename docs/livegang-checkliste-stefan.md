# Livegang: Was Stefan selbst tun muss

Reihenfolge und Zieltermine. Hintergrund und Quellen stehen in [livegang.md](livegang.md). Alles andere (Upload, Seiten, Header, Karte, Monitoring im Code) erledigen die Threads.

## Bis Freitag, 20.11.

1. **Anbieter wählen.** Empfehlung: netcup Webhosting 1000 (2,69 €/Monat, .de-Domain dabei, 12 Monate Laufzeit). Vor der Bestellung im Tarif nachsehen, ob SFTP oder SSH dabei ist, sonst FTPS. Alternative: Cloudflare Pages (kostenlos, US-Anbieter, keine eigene Kartendatei möglich).
2. **Domainnamen prüfen** bei https://www.denic.de (z. B. `loipenblick.de`). Keine Orts- oder Markennamen Dritter.
3. **Impressum-Adresse klären.** Pflicht sind Vor- und Nachname und eine ladungsfähige Anschrift, ein Postfach reicht nicht. Möglich: eigene Adresse, oder Adresse eines Familienangehörigen mit schriftlicher Zustellungsvollmacht, oder ein Anschriftenservice mit Vollmacht (kostet).
4. **Quellbetreiber um Erlaubnis bitten** mit der Vorlage aus `livegang.md`, Abschnitt 8. Zuerst Tirol Werbung (info@tirol.at), dann Tegernseer Tal Tourismus, Bayrischzell, Fischbachau, Chiemgau (tourinfra), Aschau, Tannheimer Tal, Seefeld, Achensee, Kufstein, Kaiserwinkl, Kitzbüheler Alpen, Faistenau/Hintersee, Berchtesgaden. Antworten sammeln (Datum, Ja/Nein, Wunsch zum Quellenhinweis).

## Bis Freitag, 27.11.

5. **Webspace und Domain bestellen.** AVV (Vertrag zur Auftragsverarbeitung) im Kundenmenü abschließen, bei netcup und Hetzner ist das ein Klick.
6. **Let's Encrypt** für die Domain einschalten, „HTTP auf HTTPS umleiten“ aktivieren.
7. **Eigenes SFTP/FTPS-Konto** nur für den Web-Ordner anlegen, dazu eine Subdomain `test.` (ohne Passwortschutz per `.htaccess`, weil der Upload die `.htaccess` mitbringt; die Testseite sperrt Suchmaschinen selbst).
8. **Zugangsdaten in die `.env` auf dem NAS** eintragen: `LOIPEN_UPLOAD_URL`, `LOIPEN_UPLOAD_PASSWORT`, Impressum-Angaben und `LOIPEN_HOSTER` (Vorlage `.env.example`, Ablauf im README unter „Online stellen“). Nicht in Nachrichten oder ins Repo.
9. **Log-Aufbewahrung** beim Hoster auf kurz stellen (z. B. 7 Tage), wenn einstellbar.
10. **E-Mail-Weiterleitung** `kontakt@<domain>` auf dein Postfach einrichten.
10a. **Postfach `abo@<domain>`** für das E-Mail-Abo anlegen und Zugangsdaten (SMTP) sowie einen Schlüssel (`openssl rand -hex 32`) in die `.env` eintragen (`LOIPEN_ABO_*`, `LOIPEN_SMTP_*`, README „E-Mail-Abo“). Prüfen, dass der Tarif PHP und `mail()` erlaubt.

## Bis Freitag, 4.12.

11. **Datenschutzerklärung erzeugen** mit einem Generator (z. B. datenschutz-generator.de oder e-recht24). Bausteine: Hosting/Server-Logs, Karte, Standort im Browser, lokale Speicherung, externe Links, Statistik, Newsletter/E-Mail-Benachrichtigung mit Double-Opt-In, Kontaktformular (für „Angabe falsch? Melden“). Die eingebaute Vorlage hat dafür schon die Abschnitte „E-Mail-Benachrichtigung“ und „Falsche Angaben melden“; bei eigenem Text diese übernehmen. Den Text als `geheim/datenschutz.html` neben die `docker-compose.yml` legen und `LOIPEN_DATENSCHUTZ_DATEI=/app/geheim/datenschutz.html` setzen. Ohne eigenen Text nimmt die Seite die eingebaute Vorlage.
12. **Testadresse prüfen** auf Handy und PC: Standort, Karte, Impressum, Datenschutz, ein Abo anlegen und bestätigen, eine Testmeldung schicken.
13. **UptimeRobot** (Monitor auf `https://<domain>/`) und **Healthchecks.io** (Ping-URL in die `.env`) anlegen.
14. **Wortlaut DWD-Quellenhinweis** auf dwd.de nachsehen (die Seite sperrt automatische Abrufe), Ergebnis in den Thread schreiben.

## Bis Freitag, 11.12.

15. **Antworten der Quellen entscheiden:** Ja → bleibt. Nein → abschalten. Keine Antwort → zeigen mit Quellenhinweis oder bis zur Antwort abschalten.
16. **Livegang freigeben.** Erst danach lädt das NAS auf die Hauptadresse hoch und die Seite wird für Suchmaschinen geöffnet.
17. **Rechnungsbeträge** in `config/kosten.yaml` eintragen lassen (Nachricht an den Thread genügt).

## Später

- Nutzungsstatistik ansehen; nur wenn sie nicht reicht, Cookies mit Banner (E-14, B18).
- Anschriftenservice, wenn die Seite wächst und die Privatadresse stört.
