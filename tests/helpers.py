"""Hilfen fuer Tests mit gespeicherten Seiten. Kein Test ruft echte Quellen ab."""

from pathlib import Path

from loipen.fetcher import HttpFehler

FIXTURES = Path(__file__).resolve().parent / "fixtures"


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
    ):
        self.seiten = seiten or {}
        self.verzeichnis = FIXTURES / quelle
        self.base_url = base_url.rstrip("/")
        self.ersetze = ersetze or {}
        self.abgerufen: list[str] = []

    def get(self, url: str) -> str:
        self.abgerufen.append(url)
        pfad = url[len(self.base_url):].strip("/")
        if pfad in self.ersetze:
            return self.ersetze[pfad]
        if pfad in self.seiten:
            datei = self.verzeichnis / self.seiten[pfad]
        elif pfad.startswith("langlaufen"):
            n = pfad.split("/")[1] if "/" in pfad else "0"
            datei = self.verzeichnis / f"langlaufen_{n}.html"
        else:
            datei = self.verzeichnis / "schneebericht" / f"{pfad}.html"
        if not datei.exists():
            raise HttpFehler(url, 404)
        return datei.read_text(encoding="utf-8")

    def seite(self, relativ: str) -> str:
        return (self.verzeichnis / relativ).read_text(encoding="utf-8")


SEITEN_QUELLEN = {
    "sachrang": {"schneebericht-sachrang": "schneebericht.html"},
    "chiemgau": {"inc/ajax.php?ajaxtype=getLoipenmanager": "loipenmanager.json"},
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
        from tests.test_wetter import WetterFetcher, brightsky, dwd_zip

        heute = jetzt.date()
        zeilen = [(heute - timedelta(days=3 - i), 1.0, 20 + i, 2.0 * i) for i in range(4)]
        tage = {heute + timedelta(days=i): [(-6.0 + h * .4, 0.1 if h in (2, 3) else 0.0, "snow" if h in (2, 3) else "dry")
                                            for h in range(24)] for i in range(8)}
        aktualisiere_wetter(session, WetterFetcher(dwd_zip(zeilen), brightsky(tage)), jetzt)
