# Tourismusverband Kaiserwinkl: Erlaubnis für den Loipenbericht (24.11.2026)

- **Quelle:** `kaiserwinkl` in `config/sources.yaml`, Loipenbericht „Geöffnete Loipen“ auf www.kaiserwinkl.com
  (Kössen, Schwendt, Walchsee): Name, Zustand, Länge und Stand der Liste
- **Anfrage:** Erlaubnis-Mail von Stefan vom 19.11.2026 an info@kaiserwinkl.com (Vorlage `docs/livegang.md`,
  Abschnitt 8: Status mit Namen als Quelle und Link auf die Seite, keine Texte und Bilder, höchstens dreimal am Tag).
  Der Verband fragte am 19.11. nach der Schnittstelle; Stefan beschrieb den Abruf (eine öffentliche Seite je Abruf).
- **Antwort:** 24.11.2026, Tourismusverband Kaiserwinkl, Kössen
- **Ergebnis:** Erlaubnis liegt vor, `erlaubnis: liegt_vor` (B31, E-41)
- **Bedingung:** Umsetzung „wie von Ihnen gewünscht“, also so, wie in der Anfrage beschrieben: Quellangabe mit
  Link auf kaiserwinkl.com, nur Fakten, keine Texte und Bilder
- **Vorbehalt:** Die Erlaubnis gilt „bis dahin“, also bis der Verband mit seiner Agentur geklärt hat, ob es ein
  Widget für externe Seiten gibt. Der Verband meldet sich dann wieder. Eine eigene Schnittstelle ist nicht geplant.

## Wortlaut (ohne Signatur und Telefonnummern)

> Eine zusätzliche Schnittstelle ist derzeit nicht geplant, da dadurch voraussichtlich weitere Kosten entstehen
> würden. Wir befinden uns jedoch aktuell mit unserer Agentur in Abstimmung, ob ein Widget erstellt werden kann,
> das künftig auch auf externen Websites eingebunden werden könnte.
>
> Sobald wir wissen, ob und in welcher Form dieses Widget umgesetzt wird, melde ich mich gerne noch einmal bei
> Ihnen. Bis dahin können Sie gerne das wie von Ihnen gewünscht umsetzen.

## Wie Loipenblick die Bedingung erfüllt

- Jede Loipe aus dem Loipenbericht nennt unter „Quelle und Stand“ den Namen „Tourismusverband Kaiserwinkl
  (Loipenbericht)“ mit Link auf den Loipenbericht bei kaiserwinkl.com.
- Die Seite „Hinweise und Betreiber“ führt den Tourismusverband Kaiserwinkl mit Link auf www.kaiserwinkl.com.
- Ein Test prüft beides auf der öffentlichen Seite (`tests/test_erlaubnis.py`, B31).

## Wenn sich der Verband wegen des Widgets meldet

- **Widget kommt und der Verband wünscht, dass wir es statt des Abrufs nutzen:** Ein Widget wäre ein eingebetteter
  fremder Inhalt (Datenschutz: Aufruf eines fremden Servers beim Besuch, siehe `docs/livegang.md`). Stefan
  entscheidet dann, ob er das Widget einbindet, nur verlinkt oder weiter abruft, falls der Verband das erlaubt.
- **Widget kommt, Abruf bleibt erlaubt:** nichts zu tun, Beleg um die neue Mail ergänzen.
- **Verband zieht die Erlaubnis zurück:** Quelle auf `abgelehnt` (B30) und prüfen, ob die Gebiete über tirol.at
  weiter gezeigt werden (wie bei Achensee, E-37).

## Andere Quellen mit Kaiserwinkl-Loipen

Die Gebiete Kössen, Schwendt und Walchsee kommen zusätzlich über tirol.at (Quelle `tirol`, Freigabe der Tirol
Werbung vom 23.11.2026). Der Loipenbericht des Verbands hat Vorrang (Rang 2 vor 3, P22); die Freigabe hier ändert
daran nichts.
