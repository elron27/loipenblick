"""Hilfen fuer Tests mit gespeicherten Seiten. Kein Test ruft echte Quellen ab."""

from pathlib import Path

from loipen.fetcher import HttpFehler

FIXTURES = Path(__file__).resolve().parent / "fixtures"


# Quellen mit Schnappschuss-Ordner nach Datum (B19, CLAUDE.md Regel 10)
STAND_QUELLEN = {"tirol": "2026-11-12", "kitzbueheler-alpen": "2026-11-12", "langlaufdorf": "2026-11-12",
                 "berchtesgaden": "2026-11-12", "myswitzerland": "2026-11-13",
                 # P34 (E-24)
                 "alpbachtal": "2026-11-19", "wildschoenau": "2026-11-19", "wilderkaiser": "2026-11-19",
                 "hall-wattens": "2026-11-19", "silberregion-karwendel": "2026-11-19",  # P32
                 # P38 (Allgaeu)
                 "oberstdorf": "2026-11-20", "wertach": "2026-11-20", "pfronten": "2026-11-20",
                 "kleinwalsertal": "2026-11-20", "fuessen": "2026-11-20", "isny": "2026-11-20",
                 "hoernerdoerfer": "2026-11-20"}


class FixtureFetcher:
    """Liefert Seiten aus tests/fixtures/<quelle>/ statt aus dem Netz.

    /langlaufen[/n]  -> langlaufen_<n>.html
    /<slug>          -> schneebericht/<slug>.html
    seiten: {Pfad: Datei} ordnet einzelne Pfade Dateien zu (z. B. schneebericht-sachrang).
    ersetze: {Pfad: Text} ueberschreibt einzelne Seiten (fuer abgeleitete Seiten).
    """

    def __init__(
        self,
        quelle: str,
        base_url: str,
        ersetze: dict[str, str] | None = None,
        seiten: dict[str, str] | None = None,
        stand: str | None = None,
    ):
        self.stand = stand or STAND_QUELLEN.get(quelle)
        self.seiten = seiten or {}
        self.verzeichnis = FIXTURES / quelle
        self.base_url = base_url.rstrip("/")
        self.ersetze = ersetze or {}
        self.abgerufen: list[str] = []

    def get(self, url: str) -> str:
        inhalt = self._lies(url)
        return inhalt if isinstance(inhalt, str) else inhalt.decode("utf-8")

    def get_bytes(self, url: str) -> bytes:
        """Wie HoeflicherFetcher.get_bytes, z. B. fuer PDF-Berichte (P28)."""
        inhalt = self._lies(url)
        return inhalt.encode("utf-8") if isinstance(inhalt, str) else inhalt

    def _lies(self, url: str) -> str | bytes:
        self.abgerufen.append(url)
        pfad = url[len(self.base_url):].strip("/")
        if pfad in self.ersetze:
            return self.ersetze[pfad]
        if pfad in self.seiten:
            datei = self.verzeichnis / self.seiten[pfad]
        elif self.stand:
            # Schnappschuss mit Datum (tests/fixtures/<quelle>/<datum>/): letzter Pfadteil als Datei
            name = pfad.rsplit("/", 1)[-1] or "index"
            datei = self.verzeichnis / self.stand / (name if "." in name else f"{name}.html")
        elif pfad.startswith("langlaufen"):
            n = pfad.split("/")[1] if "/" in pfad else "0"
            datei = self.verzeichnis / f"langlaufen_{n}.html"
        else:
            datei = self.verzeichnis / "schneebericht" / f"{pfad}.html"
        if not datei.exists():
            raise HttpFehler(url, 404)
        return datei.read_bytes()

    def seite(self, relativ: str) -> str:
        return (self.verzeichnis / relativ).read_text(encoding="utf-8")


TIROL_LISTE = "aktivitaeten/sport/langlaufen/loipen"
STEIERMARK_LISTE = "de/Urlaub-planen/Tourenportal?tourCategory=46459526"
PAZNAUN_ANLAGEN = "de/winter/silvretta-arena/geoeffnete-anlagen?type=cross-country"
# Oetztal: 6 der 22 Loipen-Detailseiten liegen als Schnappschuss vor (Pfad laut Sitemap, Outdooractive-ID)
OETZTAL_TOUREN = [("lehen-loipe-umhausen-niederthai.r-23683688", "23683688"),
                  ("4-1-nachtloipe-variante-laengenfeld.r-801776311", "801776311"),
                  ("langlaufloipe-zwieselstein-soelden.r-7230466", "7230466"),
                  ("uebungsloipe-obergurgl-nr-3.r-6925433", "6925433"),
                  ("uebungsloipe-bergsteigerdorf-vent.r-7100318", "7100318"),
                  ("loipe-ochsengarten.r-7120810", "7120810")]
SEITEN_QUELLEN = {
    "innsbruck": {"innsbruck_new/lebensraum_innsbruck.aspx?lang=de": "2026-11-19/lebensraum_innsbruck.html"},  # P32
    "steiermark": {STEIERMARK_LISTE: "2026-11-14/tourenportal-langlauf-p1.html",
                   **{f"{STEIERMARK_LISTE}&page={n}": f"2026-11-14/tourenportal-langlauf-p{n}.html" for n in range(2, 8)}},
    "sachrang": {"schneebericht-sachrang": "schneebericht.html"},
    "chiemgau": {"inc/ajax.php?ajaxtype=getLoipenmanager": "loipenmanager.json"},
    "tannheimer": {"inc/ajax.php?ajaxtype=getLoipenmanager": "2026-11-13/loipenmanager.json"},
    "seefeld": {"de/loipenbericht.html": "2026-11-13/loipenbericht.html"},
    "achensee": {"de/live/schneebericht": "2026-11-13/schneebericht.html"},
    "kufsteinerland": {"de/schneebericht.html": "2026-11-13/schneebericht.html"},
    "st-anton": {"de/service/aktueller-loipenzustand": "2026-11-13/aktueller-loipenzustand.html"},
    "nassfeld-nlw": {"sportbericht/print/wintersportbericht-nps.pdf": "2026-11-13/wintersportbericht-nps.pdf"},
    "zugspitzarena": {"zugspitzarena/snowreport_zugspitzarena.aspx?lang=de": "2026-11-19/snowreport.html"},
    "osttirol": {"aktiv-outdoor/langlaufen-und-biathlon/alle-loipen": "2026-11-19/alle-loipen.html"},
    "kaiserwinkl": {"de/langlaufen-tirol/geoeffnete-loipen.html": "2026-11-13/geoeffnete-loipen.html"},
    # Listen vom 13.11. (mit Laenge, Stil je Eintrag; 12 offene Loipen), Detailseiten vom 12.11.
    "tirol": {TIROL_LISTE: "2026-11-13/loipen.html",
              f"{TIROL_LISTE}?addressbaseOpened%5B209%5D%5B%5D=OPEN": "2026-11-13/loipen_offen.html",
              f"{TIROL_LISTE}?addressbaseOpened%5B209%5D%5B0%5D=OPEN&listpos=2": "2026-11-13/loipen_offen_listpos2.html"},
    "kitzbueheler-alpen": {"de/bri/aktuelles/loipen-status.html": "2026-11-12/bri.html"},
    "langlaufdorf": {"": "2026-11-12/index.html"},
    **{k: {"inc/ajax.php?ajaxtype=getLoipenmanager": "2026-11-13/loipenmanager.json"}
       for k in ("engadin", "davos-klosters", "goms", "gastein", "ramsau", "seefeld-tourinfra")},
    "dolomiti-nordicski": {"de/regionen/alta-badia/geoeffnete-loipen/2.html": "2026-11-13/loipen-de.html"},
    "opendatahub": {"v1/ODHActivityPoi?odhtagfilter=loipen&pagesize=400&language=de&removenullvalues=true":
                    "2026-11-13/loipen.json"},
    # P31 (19.11.2026): Tiroler Ortsseiten Oetztal bis Paznaun
    "oetztal": {"sitemap.xml": "2026-11-19/sitemap.xml", "sitemap.tours_6.xml?t=1795094140": "2026-11-19/sitemap-tours.xml",
                **{f"de/aktivitaeten/alle-routen-touren/{n}": f"2026-11-19/touren/{i}.html" for n, i in OETZTAL_TOUREN}},
    "pitztal": {"de/tourenportal-langlaufen.html": "2026-11-19/tourenportal-langlaufen.html",
                "de/tourenportal-langlaufen.html?page=2": "2026-11-19/tourenportal-langlaufen-page2.html"},
    "tiroler-oberland": {"de/Aktuelles/Geoeffnete-Einrichtungen": "2026-11-19/geoeffnete-einrichtungen.html"},
    "nauders": {"de/Aktuelles/Einrichtungen-Nauders": "2026-11-19/einrichtungen.html"},
    "serfaus-fiss-ladis": {"de/winterurlaub/skigebiet-und-winteraktivitaeten/langlaufen": "2026-11-19/langlaufen.html",
                           "de/winterurlaub/skigebietsstatus-und-pistenplan": "2026-11-19/status.html"},
    "paznaun": {PAZNAUN_ANLAGEN: "2026-11-19/ischgl-anlagen.html",
                f"{PAZNAUN_ANLAGEN}&sorting=status-desc&ajax=1": "2026-11-19/ischgl-anlagen.json"},
}


def lade_alle_fixtures(session, jetzt, mit_wetter: bool = True) -> None:
    """Alle Quellen aus den Beispielseiten abrufen, dazu (erfundenes) Wetter im DWD- und Bright-Sky-Format."""
    from sqlalchemy import select

    from loipen.ablauf import rufe_quelle_ab
    from loipen.konfig import lade_und_abgleichen
    from loipen.models import Quelle

    lade_und_abgleichen(session)
    for q in session.scalars(select(Quelle).order_by(Quelle.key)).all():
        rufe_quelle_ab(session, q, FixtureFetcher(q.key, q.base_url, seiten=SEITEN_QUELLEN.get(q.key)), jetzt)
    if mit_wetter:
        from datetime import date, timedelta

        from loipen.wetter import aktualisiere_wetter
        from tests.test_wetter import WetterFetcher
        from tests.wetterformat import brightsky, dwd_zip

        heute = jetzt.date()
        zeilen = [(heute - timedelta(days=3 - i), 1.0, 20 + i, 2.0 * i) for i in range(4)]
        tage = {heute + timedelta(days=i): [(-6.0 + h * .4, 0.1 if h in (2, 3) else 0.0, "snow" if h in (2, 3) else "dry")
                                            for h in range(24)] for i in range(8)}
        aktualisiere_wetter(session, WetterFetcher(dwd_zip(zeilen), brightsky(tage)), jetzt)
