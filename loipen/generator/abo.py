"""Dateien fuer den Abo-Teil auf dem Webspace (E-18): die PHP-Skripte aus loipen/generator/abo,
dazu einstellungen.php (ohne Geheimnisse, nur der SHA-256 des Abgleich-Schluessels) und ziele.php
(welche Loipen und Gebiete man abonnieren oder melden kann).

Ohne fertige Abo-Konfiguration (seite_url, Schluessel, Absender) entsteht kein abo/-Ordner und
die Seite zeigt keine Formulare. So bleibt die lokale Vorschau auf dem NAS (B12) unveraendert.
"""

import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.mailabo import AboKonfig
from loipen.models import Gebiet, Loipe

PHP = Path(__file__).parent / "abo"


def php_str(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def php_array(d: dict[str, str]) -> str:
    zeilen = ",\n".join(f"  {php_str(k)} => {php_str(v)}" for k, v in d.items())
    return "<?php\n// Erzeugt vom NAS bei jedem Lauf. Nicht von Hand aendern.\nreturn [\n" + zeilen + "\n];\n"


def ziele(session: Session) -> dict[str, str]:
    z: dict[str, str] = {}
    for g in session.scalars(select(Gebiet).order_by(Gebiet.slug)):
        z[f"g:{g.slug}"] = f"Alle Loipen im Gebiet {g.name}"
    for l in session.scalars(select(Loipe).where(Loipe.active).order_by(Loipe.id)):
        z[f"l:{l.id}"] = f"{l.name} ({l.gebiet.name})"
    return z


def dateien(session: Session, cfg: AboKonfig, meldungen_an: str | None = None,
            datenschutz: str = "datenschutz.html", datenordner: str = "") -> dict[str, bytes]:
    """Relativer Pfad unter site/ -> Inhalt. Leer, wenn das Abo nicht eingerichtet ist."""
    if not cfg.aktiv:
        return {}
    out: dict[str, bytes] = {}
    for datei in sorted(PHP.rglob("*")):
        if datei.is_file():
            out["abo/" + datei.relative_to(PHP).as_posix()] = datei.read_bytes()
    einstellungen = {
        "seitenname": cfg.seitenname,
        "seite_url": cfg.basis,
        "absender": cfg.absender or "",
        "schluessel_sha256": hashlib.sha256((cfg.schluessel or "").encode()).hexdigest(),
        "datenschutz": datenschutz,
        "meldungen_an": meldungen_an or "",
        "datenordner": datenordner,
    }
    out["abo/einstellungen.php"] = php_array(einstellungen).encode()
    out["abo/ziele.php"] = php_array(ziele(session)).encode()
    return out
