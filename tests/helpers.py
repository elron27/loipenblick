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
