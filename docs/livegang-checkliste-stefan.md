# Livegang: Was Stefan selbst tun muss

Reihenfolge und Zieltermine. Hintergrund und Quellen stehen in [livegang.md](livegang.md). Alles andere (Upload, Seiten, Header, Karte, Monitoring im Code) erledigen die Threads.

## Bis Freitag, 20.11.

1. ~~Anbieter wählen.~~ Erledigt am 19.11.: **netcup Webhosting 1000** (2,69 €/Monat, .de-Domain dabei, 12 Monate Laufzeit). Ob SSH/SFTP dabei ist, widerspricht sich auf der netcup-Seite; nach der Bestellung im Panel nachsehen, sonst FTPS.
2. ~~Domainnamen wählen.~~ Erledigt am 19.11.: **`loipen-blick.de`** (passt zum Namen Loipenblick; `loipenblick.de` ist vergeben, die inklusive `.com` gäbe es bei netcup nur mit US-Standort). Vor der Bestellung kurz nach „Loipenblick“ im [DPMAregister](https://register.dpma.de/DPMAregister/marke/basis) und bei [TMview](https://www.tmdn.org/tmview/) suchen.
3. **Impressum-Adresse klären.** Pflicht sind Vor- und Nachname und eine ladungsfähige Anschrift, ein Postfach reicht nicht. Möglich: eigene Adresse, oder Adresse eines Familienangehörigen mit schriftlicher Zustellungsvollmacht, oder ein Anschriftenservice mit Vollmacht (kostet).
4. **Quellbetreiber um Erlaubnis bitten** mit der Vorlage aus `livegang.md`, Abschnitt 8. Zuerst Tirol Werbung (info@tirol.at), dann Tegernseer Tal Tourismus, Bayrischzell, Fischbachau, Chiemgau (tourinfra), Aschau, Tannheimer Tal, Seefeld, Achensee, Kufstein, Kaiserwinkl, Kitzbüheler Alpen, Faistenau/Hintersee, Berchtesgaden. Antworten sammeln (Datum, Ja/Nein, Wunsch zum Quellenhinweis).

## Bis Freitag, 27.11.

5. **Webspace und Domain bestellen.** AVV (Vertrag zur Auftragsverarbeitung) im Kundenmenü abschließen, bei netcup im Kundenmenü (CCP), dort ein Klick.
6. **Let's Encrypt** für die Domain einschalten, „HTTP auf HTTPS umleiten“ aktivieren.
7. **Eigenes SFTP/FTPS-Konto** nur für den Web-Ordner anlegen, dazu eine Subdomain `test.` (ohne Passwortschutz per `.htaccess`, weil der Upload die `.htaccess` mitbringt; die Testseite sperrt Suchmaschinen selbst).
8. **Zugangsdaten in die `.env` auf dem NAS** eintragen: `LOIPEN_UPLOAD_URL`, `LOIPEN_UPLOAD_PASSWORT`, Impressum-Angaben und `LOIPEN_HOSTER` (Vorlage `.env.example`, Ablauf im README unter „Online stellen“). Nicht in Nachrichten oder ins Repo.
9. **Log-Aufbewahrung** beim Hoster auf kurz stellen (z. B. 7 Tage), wenn einstellbar.
10. **E-Mail-Weiterleitung** `kontakt@<domain>` auf dein Postfach einrichten.
10a. **Postfach `abo@<domain>`** für das E-Mail-Abo anlegen und Zugangsdaten (SMTP) sowie einen Schlüssel (`openssl rand -hex 32`) in die `.env` eintragen (`LOIPEN_ABO_*`, `LOIPEN_SMTP_*`, README „E-Mail-Abo“). Prüfen, dass der Tarif PHP und `mail()` erlaubt.
10b. **Push für Besucher einschalten** (E-25, freiwillig): in der `.env` auf dem NAS `LOIPEN_PUSH_PRAEFIX=loipenblick-` plus drei bis fünf zufällige Zeichen eintragen (z. B. `loipenblick-x7q`), Container neu erstellen. Danach zeigt jede Loipe „Per Push aufs Handy“. Test: ntfy-App installieren, Thema einer Loipe abonnieren. Details in [benachrichtigung.md](benachrichtigung.md).

## Bis Freitag, 4.12.

11. **Datenschutzerklärung erzeugen** mit einem Generator (z. B. datenschutz-generator.de oder e-recht24). Bausteine: Hosting/Server-Logs, Karte, Standort im Browser, lokale Speicherung, externe Links, Statistik, Newsletter/E-Mail-Benachrichtigung mit Double-Opt-In, Kontaktformular (für „Angabe falsch? Melden“). Die eingebaute Vorlage hat dafür schon die Abschnitte „E-Mail-Benachrichtigung“ und „Falsche Angaben melden“; bei eigenem Text diese übernehmen. Den Text als `geheim/datenschutz.html` neben die `docker-compose.yml` legen und `LOIPEN_DATENSCHUTZ_DATEI=/app/geheim/datenschutz.html` setzen. Ohne eigenen Text nimmt die Seite die eingebaute Vorlage.
12. **Testadresse prüfen** auf Handy und PC: Standort, Karte, Impressum, Datenschutz, ein Abo anlegen und bestätigen, eine Testmeldung schicken.
13. **UptimeRobot** (Monitor auf `https://<domain>/`) und **Healthchecks.io** (Ping-URL in die `.env`) anlegen.
14. **Wortlaut DWD-Quellenhinweis** auf dwd.de nachsehen (die Seite sperrt automatische Abrufe), Ergebnis in den Thread schreiben.

14a. **Spendenlink (wenn gewünscht).** Unter [paypal.com/paypalme](https://www.paypal.com/paypalme) mit dem eigenen PayPal-Konto einen Link anlegen (z. B. `paypal.me/Loipenblick`), dann in die NAS-`.env` die Zeile `LOIPEN_SPENDEN_URL=https://paypal.me/<Name>` eintragen und den Container neu erstellen. Auf der Testadresse prüfen: Fußzeile, „Hinweise und Betreiber“, Datenschutz. Hintergrund und Vergleich mit Buy Me a Coffee in [livegang.md](livegang.md), Abschnitt „Spendenlink“. Bei eigenem Datenschutztext den Baustein für PayPal ergänzen.
14b. **Besucherzähler.** In die NAS-`.env` die Zeile `LOIPEN_ZAEHLER_PASSWORT=` mit einem eigenen Passwort (mindestens 12 Zeichen, nur in der .env, nicht im Chat) eintragen und den Container neu erstellen. Nach dem nächsten Lauf `https://test.loipen-blick.de/zaehler/auswertung.php` öffnen und anmelden: Ab dann zählt dieser Browser nicht mehr mit. Am Handy einmal ebenfalls anmelden. Hintergrund in README.md, Abschnitt „Besucherzähler“.

## Bis Freitag, 11.12.

15. **Antworten der Quellen entscheiden:** Ja → bleibt. Nein → abschalten. Keine Antwort → zeigen mit Quellenhinweis oder bis zur Antwort abschalten.
15a. **Pflicht: Quellen ohne Zustimmung prüfen.** Vor der Freigabe in `config/sources.yaml` alle Quellen mit `erlaubnis: nur_test` durchgehen (Liste: `python -c "from loipen.konfig import *; print(nur_test_quellen(lade_yaml(CONFIG_DIR / 'sources.yaml')))"`). Die öffentliche Seite blendet sie automatisch aus. Für jede gilt: Betreiber mit Vorführung der Testseite anfragen (Kontakte und Stand in [kontaktliste.md](kontaktliste.md)), bei Zustimmung auf `liegt_vor` setzen. Beispiel: Zillertal Tourismus verbietet im Impressum das Speichern ohne Einwilligung (geprüft 19.11.2026); die Testphase nutzt die Daten trotzdem, das Risiko trägt Stefan bewusst. Sonderfall Innsbruck (`innsbruck`): Der Bericht kommt vom Bezahldienst Intermaps, den P17 sonst ausschließt; die Ausnahme gilt nur für die Testversion (Stefan, 19.11.2026). Öffentlich nur mit schriftlicher Zustimmung von Innsbruck Tourismus. Abgelehnte Quellen (`erlaubnis: abgelehnt`) bleiben immer aus, auch in der Testversion (B30). Stand 20.11.2026: **Achensee Tourismus hat abgelehnt**; achensee.com bleibt deshalb aus. Stand 23.11.2026: **Tirol Werbung hat zugestimmt** (Abholung über die Website mit Quellangabe und Link, Beleg in `docs/erlaubnisse/`); `tirol` steht auf `liegt_vor`, Nachfassen entfällt. Stefan hat entschieden, die Gebiete Achensee und Steinberg am Rofan über tirol.at wieder zu zeigen (E-37); der Block `ausgeblendet` in `config/gebiete.yaml` ist leer. Beschwert sich Achensee, dort wieder eintragen. Stand 25.11.2026: **Achensee Tourismus hat endgültig abgelehnt.** Die Gebiete Achensee, Steinberg am Rofan und die Loipe W1 Buchbergl stehen deshalb unter `nur_test` in `config/gebiete.yaml` (E-43): Die Testseite zeigt sie mit dem Hinweis „nur Test, nicht öffentlich“, die öffentliche Seite (`LOIPEN_OEFFENTLICH=true`) lässt sie automatisch weg. Vor der Freigabe prüfen, dass auf der Hauptadresse kein Achensee-Gebiet und kein gelbes Testband erscheint. Stand 24.11.2026: **Tourismusverband Kaiserwinkl hat zugestimmt** (Umsetzung wie angefragt, Beleg in `docs/erlaubnisse/`); `kaiserwinkl` steht auf `liegt_vor`. Vorbehalt: Der Verband klärt mit seiner Agentur ein Widget für externe Seiten und meldet sich dann wieder; erst dann ist neu zu entscheiden.
16. **Livegang freigeben.** Erst danach lädt das NAS auf die Hauptadresse hoch und die Seite wird für Suchmaschinen geöffnet.
17. **Rechnungsbeträge** in `config/kosten.yaml` eintragen lassen (Nachricht an den Thread genügt).

## Später

- Nutzungsstatistik ansehen; nur wenn sie nicht reicht, Cookies mit Banner (E-14, B18).
- Anschriftenservice, wenn die Seite wächst und die Privatadresse stört.
