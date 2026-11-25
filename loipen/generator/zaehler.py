"""Dateien fuer den Besucherzaehler auf dem Webspace (B13, E-42): die PHP-Skripte aus
loipen/generator/zaehler, dazu einstellungen.php (nur ein PBKDF2-Wert des Passworts, nie das Passwort)
und ziele.php (Namen der Gebiete und Loipen fuer die Auswertung, Gebiet je Loipe).

Ohne LOIPEN_ZAEHLER_PASSWORT entsteht kein zaehler/-Ordner und die App zaehlt nichts. Auf der
lokalen Vorschau am NAS laeuft kein PHP; dort geht der Aufruf ins Leere.
"""

import hashlib
import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.generator.abo import php_str
from loipen.konfig import CONFIG_DIR, ausgeblendet, lade_yaml
from loipen.models import Gebiet, Loipe

log = logging.getLogger(__name__)

PHP = Path(__file__).parent / "zaehler"
RUNDEN = 200_000
MIN_LAENGE = 12


def passwort_ok(passwort: str | None) -> bool:
    if not passwort:
        return False
    if len(passwort) < MIN_LAENGE:
        log.warning("LOIPEN_ZAEHLER_PASSWORT ist kuerzer als %d Zeichen, Besucherzaehler bleibt aus", MIN_LAENGE)
        return False
    return True


def php_json(daten) -> str:
    """PHP-Datei, die die Daten als Array zurueckgibt."""
    roh = json.dumps(daten, ensure_ascii=False, sort_keys=True)
    return ("<?php\n// Erzeugt vom NAS bei jedem Lauf. Nicht von Hand aendern.\n"
            f"return json_decode({php_str(roh)}, true);\n")


def ziele(session: Session, config_dir: Path = CONFIG_DIR) -> dict:
    gebiete_aus, loipen_aus = ausgeblendet(lade_yaml(config_dir / "gebiete.yaml"))
    gebiete = {g.slug: g.name for g in session.scalars(select(Gebiet).order_by(Gebiet.slug)) if g.slug not in gebiete_aus}
    loipen = {}
    for l in session.scalars(select(Loipe).where(Loipe.active).order_by(Loipe.id)):
        if l.gebiet.slug in gebiete and (l.gebiet.slug, l.name) not in loipen_aus:
            loipen[str(l.id)] = [l.name, l.gebiet.slug]
    return {"gebiete": gebiete, "loipen": loipen}


def einstellungen(passwort: str, salz_quelle: str, oeffentlich: bool, datenordner: str = "") -> dict:
    # Das Salz haengt nur an der Seite, damit sich die Datei nicht bei jedem Lauf aendert
    salz = hashlib.sha256(("loipenblick-zaehler:" + salz_quelle).encode()).hexdigest()[:32]
    wert = hashlib.pbkdf2_hmac("sha256", passwort.encode(), salz.encode(), RUNDEN).hex()
    return {"passwort_pbkdf2": wert, "passwort_salz": salz, "passwort_runden": RUNDEN,
            "oeffentlich": oeffentlich, "datenordner": datenordner}


def dateien(session: Session, passwort: str | None, oeffentlich: bool = False, seite: str = "",
            datenordner: str = "", config_dir: Path = CONFIG_DIR) -> dict[str, bytes]:
    """Relativer Pfad unter site/ -> Inhalt. Leer ohne gueltiges Passwort."""
    if not passwort_ok(passwort):
        return {}
    out = {"zaehler/" + d.relative_to(PHP).as_posix(): d.read_bytes() for d in sorted(PHP.rglob("*")) if d.is_file()}
    out["zaehler/einstellungen.php"] = php_json(einstellungen(passwort, seite, oeffentlich, datenordner)).encode()
    out["zaehler/ziele.php"] = php_json(ziele(session, Path(config_dir))).encode()
    return out
