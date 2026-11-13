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
7. **Eigenes SFTP/FTPS-Konto** nur für den Web-Ordner anlegen, dazu eine Subdomain `test.` mit Passwortschutz.
8. **Zugangsdaten in die `.env` auf dem NAS** eintragen (Namen kommen mit dem Upload-PR). Nicht in Nachrichten oder ins Repo.
9. **Log-Aufbewahrung** beim Hoster auf kurz stellen (z. B. 7 Tage), wenn einstellbar.
10. **E-Mail-Weiterleitung** `kontakt@<domain>` auf dein Postfach einrichten.

## Bis Freitag, 4.12.

11. **Datenschutzerklärung erzeugen** mit einem Generator (z. B. datenschutz-generator.de oder e-recht24). Bausteine: Hosting/Server-Logs, Karte, Standort im Browser, lokale Speicherung, externe Links, Statistik. Den Text ablegen, wo der Upload-PR es vorgibt.
12. **Testadresse prüfen** auf Handy und PC: Standort, Karte, Impressum, Datenschutz.
13. **UptimeRobot** (Monitor auf `https://<domain>/`) und **Healthchecks.io** (Ping-URL in die `.env`) anlegen.
14. **Wortlaut DWD-Quellenhinweis** auf dwd.de nachsehen (die Seite sperrt automatische Abrufe), Ergebnis in den Thread schreiben.

## Bis Freitag, 11.12.

15. **Antworten der Quellen entscheiden:** Ja → bleibt. Nein → abschalten. Keine Antwort → zeigen mit Quellenhinweis oder bis zur Antwort abschalten.
16. **Livegang freigeben.** Erst danach lädt das NAS auf die Hauptadresse hoch und die Seite wird für Suchmaschinen geöffnet.
17. **Rechnungsbeträge** in `config/kosten.yaml` eintragen lassen (Nachricht an den Thread genügt).

## Später

- Nutzungsstatistik ansehen; nur wenn sie nicht reicht, Cookies mit Banner (E-14, B18).
- Anschriftenservice, wenn die Seite wächst und die Privatadresse stört.
