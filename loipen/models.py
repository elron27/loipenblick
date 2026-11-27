"""Datenmodell: Region -> Gebiet -> Loipe -> Zustand, dazu Quelle, Parkplatz und Wetter.

Anforderungen: D1 (Hierarchie, stabile IDs), D2 (Stammdaten), D3 (Zustand pro Abruf),
D4 (Historie nur bei Aenderung), D7 (Gebiet), D8 (Parkplaetze und Gebuehren),
D11/D13 (Schnee und Wetter pro Gebiet).
"""

from datetime import date, datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Status(StrEnum):
    """Die vier normierten Status (D3). Quelltexte werden per Zuordnungstabelle (P5) abgebildet."""

    OFFEN = "offen"
    EINGESCHRAENKT = "eingeschraenkt"
    GESCHLOSSEN = "geschlossen"
    UNBEKANNT = "unbekannt"


class Technik(StrEnum):
    KLASSISCH = "klassisch"
    SKATING = "skating"
    BEIDES = "beides"
    UNBEKANNT = "unbekannt"


class Schwierigkeit(StrEnum):
    LEICHT = "leicht"
    MITTEL = "mittel"
    SCHWER = "schwer"
    UNBEKANNT = "unbekannt"


class Herkunft(StrEnum):
    """Woher ein Stammdatum kommt. Werte der Quelle haben Vorrang vor Handdaten (D8)."""

    QUELLE = "quelle"
    HAND = "hand"


class WetterArt(StrEnum):
    MESSUNG = "messung"
    VORHERSAGE = "vorhersage"


class Base(DeclarativeBase):
    pass


class Region(Base):
    """Oberste Ebene, z. B. 'Tegernseer Tal' oder 'Chiemgau'."""

    __tablename__ = "regionen"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    land: Mapped[str] = mapped_column(String(2), default="DE")
    # D16: Bundesland (Bayern, Tirol, Salzburg); das Gebiet erbt Land und Bundesland von der Region
    bundesland: Mapped[str | None] = mapped_column(String(64))

    gebiete: Mapped[list["Gebiet"]] = relationship(back_populates="region")


class Quelle(Base):
    """Eine konfigurierte Datenquelle, z. B. tegernsee.com mit Adapter 'ats' (P2)."""

    __tablename__ = "quellen"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    adapter: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(String(500))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Monitoring des letzten Laufs (B2)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(16))
    last_count: Mapped[int | None] = mapped_column(Integer)
    last_dauer_s: Mapped[float | None] = mapped_column(Float)
    last_error: Mapped[str | None] = mapped_column(Text)

    # Quellen-Waechter (B26): laufender Alarm, seit wann, wann zuletzt gemeldet
    waechter_alarm: Mapped[str | None] = mapped_column(String(16))
    waechter_seit: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    waechter_gemeldet_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    loipen: Mapped[list["Loipe"]] = relationship(back_populates="quelle")


class Abrufprotokoll(Base):
    """Ein Eintrag je Abruf einer Quelle (B26): Grundlage fuer den Waechter und spaeter fuer die
    Zuverlaessigkeit der Quellen in der Statistik. befund ist leer, wenn der Abruf unauffaellig war."""

    __tablename__ = "abrufprotokoll"

    id: Mapped[int] = mapped_column(primary_key=True)
    quelle_id: Mapped[int] = mapped_column(ForeignKey("quellen.id"), index=True)
    zeit: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    anzahl: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    befund: Mapped[str | None] = mapped_column(String(16))  # fehler, leer, einbruch
    fehler: Mapped[str | None] = mapped_column(Text)
    dauer_s: Mapped[float | None] = mapped_column(Float)


gebiet_nachbarn = Table(
    "gebiet_nachbarn",
    Base.metadata,
    Column("gebiet_id", ForeignKey("gebiete.id"), primary_key=True),
    Column("nachbar_id", ForeignKey("gebiete.id"), primary_key=True),
)


class Gebiet(Base):
    """Ein Ort oder Loipennetz zwischen Region und Loipe, z. B. 'Bayrischzell' (D7)."""

    __tablename__ = "gebiete"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    region_id: Mapped[int] = mapped_column(ForeignKey("regionen.id"))
    tourist_url: Mapped[str] = mapped_column(String(500))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    hoehe_m: Mapped[int | None] = mapped_column(Integer)
    # Loipengebuehr: None bei loipengebuehr_eur heisst unbekannt, nie kostenlos (D8)
    loipengebuehr_eur: Mapped[float | None] = mapped_column(Float)
    loipengebuehr_text: Mapped[str | None] = mapped_column(String(300))
    loipengebuehr_url: Mapped[str | None] = mapped_column(String(500))
    # Naechste Haltestellen fuer Bus und Bahn (U26): [{name, lat, lon, url}]
    haltestellen: Mapped[list] = mapped_column(JSON, default=list)
    # DWD-Station fuer Schnee und Wetter (D11, D13)
    wetterstation_id: Mapped[str | None] = mapped_column(String(10))
    wetterstation_name: Mapped[str | None] = mapped_column(String(200))
    # D17: "dwd" (Standard) oder "geosphere" fuer Gebiete in Oesterreich
    wetterdienst: Mapped[str | None] = mapped_column(String(16))
    # P12: weitere Namen je Sprache, z. B. {"it": "Dobbiaco"}
    namen: Mapped[dict | None] = mapped_column(JSON)
    # U31: Hinweis fuer die Anfahrt ueber die Grenze (Vignette), von Hand gepflegt
    grenzinfo: Mapped[str | None] = mapped_column(String(300))
    # D9: Webcams [{name, url, herkunft, geprueft_am}], nur als Link (U49)
    webcams: Mapped[list | None] = mapped_column(JSON)
    # D10/D22/D24: Skiverleihe [{name, lat, lon, url, herkunft, auto_min, fuss_min}]
    verleih: Mapped[list | None] = mapped_column(JSON)
    # B32: Pruefdatum der Handangaben des Gebiets (Gebuehr, Parkplaetze, Webcams, Verleih)
    hand_geprueft_am: Mapped[date | None] = mapped_column(Date)
    # D25: Hunderegel {erlaubt, text, url, geprueft_am} und beleuchtete Loipen [{name, zeiten, url, geprueft_am}]
    hunde: Mapped[dict | None] = mapped_column(JSON)
    beleuchtet: Mapped[list | None] = mapped_column(JSON)

    region: Mapped[Region] = relationship(back_populates="gebiete")
    loipen: Mapped[list["Loipe"]] = relationship(back_populates="gebiet")
    parkplaetze: Mapped[list["Parkplatz"]] = relationship(back_populates="gebiet")
    nachbarn: Mapped[list["Gebiet"]] = relationship(
        secondary=gebiet_nachbarn,
        primaryjoin=id == gebiet_nachbarn.c.gebiet_id,
        secondaryjoin=id == gebiet_nachbarn.c.nachbar_id,
    )


class Loipe(Base):
    """Stammdaten einer Loipe (D2). Identitaet = Quelle + source_key, nicht der Name (D1)."""

    __tablename__ = "loipen"
    __table_args__ = (UniqueConstraint("quelle_id", "source_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    quelle_id: Mapped[int] = mapped_column(ForeignKey("quellen.id"))
    gebiet_id: Mapped[int] = mapped_column(ForeignKey("gebiete.id"))
    source_key: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(200))
    technik: Mapped[str] = mapped_column(String(16), default=Technik.UNBEKANNT)
    schwierigkeit: Mapped[str] = mapped_column(String(16), default=Schwierigkeit.UNBEKANNT)
    nachtloipe: Mapped[bool | None] = mapped_column(Boolean)
    rundkurs: Mapped[bool | None] = mapped_column(Boolean)
    laenge_km: Mapped[float | None] = mapped_column(Float)
    hoehe_m: Mapped[int | None] = mapped_column(Integer)
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    # Streckenverlauf als GeoJSON-Geometrie (LineString), optional
    verlauf: Mapped[dict | None] = mapped_column(JSON)
    gebuehr_text: Mapped[str | None] = mapped_column(String(300))
    hund_erlaubt: Mapped[bool | None] = mapped_column(Boolean)
    # P41: Kunstschnee, Loipengebiet und weitere Einstiege [{ort, detail}] laut Quelle
    kunstschnee: Mapped[bool | None] = mapped_column(Boolean)
    loipengebiet: Mapped[str | None] = mapped_column(String(200))
    einstiege: Mapped[list | None] = mapped_column(JSON)
    # D21: Stammdaten aus Detailseiten, Handrecherche oder Hoehenmodell
    hoehenmeter: Mapped[int | None] = mapped_column(Integer)
    hoechster_punkt_m: Mapped[int | None] = mapped_column(Integer)
    tiefster_punkt_m: Mapped[int | None] = mapped_column(Integer)
    dauer_min: Mapped[int | None] = mapped_column(Integer)
    kondition: Mapped[int | None] = mapped_column(Integer)  # 1 bis 6 (tirol.at)
    technik_note: Mapped[int | None] = mapped_column(Integer)  # 1 bis 6 (tirol.at)
    merkmale: Mapped[list | None] = mapped_column(JSON)  # feste Liste, D21 AK 2
    webcams: Mapped[list | None] = mapped_column(JSON)  # [{name, url}] (P42)
    # D21 AK 1: je Feld {herkunft: quelle|osm|hand|berechnet, url, geprueft_am}
    herkunft: Mapped[dict | None] = mapped_column(JSON)
    source_url: Mapped[str] = mapped_column(String(500))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    quelle: Mapped[Quelle] = relationship(back_populates="loipen")
    gebiet: Mapped[Gebiet] = relationship(back_populates="loipen")
    zustaende: Mapped[list["Zustand"]] = relationship(
        back_populates="loipe", order_by="Zustand.abgerufen_at.desc()"
    )


class Zustand(Base):
    """Ein beobachteter Zustand (D3). Neue Zeile nur bei Aenderung, sonst wird
    zuletzt_bestaetigt_at fortgeschrieben (D4). Die Tabelle ist damit die Historie."""

    __tablename__ = "zustaende"

    id: Mapped[int] = mapped_column(primary_key=True)
    loipe_id: Mapped[int] = mapped_column(ForeignKey("loipen.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default=Status.UNBEKANNT)
    # Manche Quellen (tourinfra) melden klassisch und Skating getrennt
    status_klassisch: Mapped[str | None] = mapped_column(String(16))
    status_skating: Mapped[str | None] = mapped_column(String(16))
    gespurt_klassisch_km: Mapped[float | None] = mapped_column(Float)
    gespurt_skating_km: Mapped[float | None] = mapped_column(Float)
    gespurt_gesamt_km: Mapped[float | None] = mapped_column(Float)
    schneehoehe_cm: Mapped[int | None] = mapped_column(Integer)
    # P41: Schneehoehe am Berg (schneehoehe_cm = Tal), Hinweis und Sperrgrund des Betreibers
    schneehoehe_berg_cm: Mapped[int | None] = mapped_column(Integer)
    hinweis: Mapped[str | None] = mapped_column(Text)
    sperrgrund: Mapped[str | None] = mapped_column(String(100))
    # Zeiten getrennt: Praeparierung bzw. Aenderung laut Quelle, erster und letzter Abruf
    quelle_aktualisiert_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    abgerufen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    zuletzt_bestaetigt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    rohtext: Mapped[str | None] = mapped_column(Text)

    loipe: Mapped[Loipe] = relationship(back_populates="zustaende")


class Parkplatz(Base):
    """Parkplatz eines Gebiets oder einer Loipe (D8). Gebuehr None = unbekannt."""

    __tablename__ = "parkplaetze"
    __table_args__ = (UniqueConstraint("gebiet_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    gebiet_id: Mapped[int] = mapped_column(ForeignKey("gebiete.id"))
    loipe_id: Mapped[int | None] = mapped_column(ForeignKey("loipen.id"))
    name: Mapped[str] = mapped_column(String(200))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    gebuehr_eur_tag: Mapped[float | None] = mapped_column(Float)
    gebuehr_text: Mapped[str | None] = mapped_column(String(300))
    herkunft: Mapped[str] = mapped_column(String(16), default=Herkunft.HAND)
    quelle_url: Mapped[str | None] = mapped_column(String(500))
    # true, wenn die Koordinate nur der Loipenstart ist und kein bestaetigter Parkplatz
    koordinate_geschaetzt: Mapped[bool] = mapped_column(Boolean, default=False)

    gebiet: Mapped[Gebiet] = relationship(back_populates="parkplaetze")


class Wetter(Base):
    """Tageswerte pro Gebiet, gemessen oder vorhergesagt (D11, D13)."""

    __tablename__ = "wetter"
    __table_args__ = (UniqueConstraint("gebiet_id", "datum", "art"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    gebiet_id: Mapped[int] = mapped_column(ForeignKey("gebiete.id"), index=True)
    datum: Mapped[date] = mapped_column(Date)
    art: Mapped[str] = mapped_column(String(16))
    temp_min_c: Mapped[float | None] = mapped_column(Float)
    temp_max_c: Mapped[float | None] = mapped_column(Float)
    niederschlag_mm: Mapped[float | None] = mapped_column(Float)
    neuschnee_cm: Mapped[float | None] = mapped_column(Float)
    schneehoehe_cm: Mapped[float | None] = mapped_column(Float)
    sonne_h: Mapped[float | None] = mapped_column(Float)
    symbol: Mapped[str | None] = mapped_column(String(16))
    station_id: Mapped[str | None] = mapped_column(String(10))
    quelle: Mapped[str] = mapped_column(String(100))
    abgerufen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Abonnent(Base):
    """Bestaetigtes E-Mail-Abo (N2, N7). Unbestaetigte Anmeldungen gibt es hier nicht: Sie liegen nur
    verschluesselt im Bestaetigungslink. Abmelden loescht die Zeile."""

    __tablename__ = "abonnenten"

    # ID und Abmelde-Token vergibt der Webspace (abo/bestaetigen.php)
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    email: Mapped[str] = mapped_column(String(254))
    # "l:<loipen-id>" oder "g:<gebiet-slug>"
    ziele: Mapped[list] = mapped_column(JSON)
    ereignisse: Mapped[list] = mapped_column(JSON)
    abmelde_token: Mapped[str] = mapped_column(String(64))
    # Nachweis der Einwilligung (Art. 7 Abs. 1 DSGVO): wann angefragt und wann bestaetigt
    angefragt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    bestaetigt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    letzte_mail_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OsmDaten(Base):
    """Verdichtete OpenStreetMap-Daten je Region (P40, P39): benannte Loipen (piste:type=nordic) und
    Parkplaetze. Lizenz ODbL; wird woechentlich neu geholt (loipen/osm.py)."""

    __tablename__ = "osm_daten"

    region_slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    bbox: Mapped[list] = mapped_column(JSON)
    inhalt: Mapped[dict] = mapped_column(JSON)
    abgerufen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Meldeprotokoll(Base):
    """Was zuletzt je Loipe gemeldet wurde, ueber alle Kanaele (N11). Verhindert doppelte Nachrichten,
    etwa wenn eine Quelle kurz "unbekannt" meldet und die Loipe danach wieder "oeffnet"."""

    __tablename__ = "meldeprotokoll"

    loipe_id: Mapped[int] = mapped_column(ForeignKey("loipen.id", ondelete="CASCADE"), primary_key=True)
    status_art: Mapped[str | None] = mapped_column(String(16))  # zuletzt gemeldet: oeffnet oder schliesst
    status_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    befahrbar_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # oeffnet oder frisch_gespurt


class PushTag(Base):
    """Oeffentliche Push-Nachrichten je Tag (N10): ntfy.sh begrenzt die Nachrichten je Absender und Tag."""

    __tablename__ = "push_tage"

    tag: Mapped[date] = mapped_column(Date, primary_key=True)
    anzahl: Mapped[int] = mapped_column(Integer, default=0)
    grenze_gemeldet: Mapped[bool] = mapped_column(Boolean, default=False)


# --------------------------------------------------------------------------------------------- Schneekarte
# Eigene Tabellen (S9, E-31), die Loipen-Tabellen bleiben unveraendert. Grundsatz E-34: jeder Rohwert wird
# unveraendert gespeichert, die Antwort der Quelle zusaetzlich als gepackte Datei (SchneeRohdatei).


class Messart(StrEnum):
    """S2 AK 3: Wie ein Wert entstanden ist."""

    AUTOMATISCH = "automatisch"
    HAND = "hand"
    MODELL = "modell"


class SchneeRohdatei(Base):
    """Eine Antwort einer Schneequelle, gepackt im Rohdatei-Ordner (S1 AK 2). Gleicher Inhalt = eine Zeile."""

    __tablename__ = "schnee_rohdateien"

    id: Mapped[int] = mapped_column(primary_key=True)
    quelle: Mapped[str] = mapped_column(String(64), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    pfad: Mapped[str] = mapped_column(String(500))  # relativ zum Rohdatei-Ordner
    groesse: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(100))
    abgerufen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SchneeStation(Base):
    """Messstation mit Hoehe (S2). Verschwundene Stationen werden inaktiv, nie geloescht (S2 AK 4)."""

    __tablename__ = "schnee_stationen"
    __table_args__ = (UniqueConstraint("quelle", "kennung"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    quelle: Mapped[str] = mapped_column(String(64))
    kennung: Mapped[str] = mapped_column(String(64))  # ID der Station bei der Quelle
    name: Mapped[str] = mapped_column(String(200))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    hoehe_m: Mapped[int] = mapped_column(Integer)
    betreiber: Mapped[str | None] = mapped_column(String(200))
    land: Mapped[str | None] = mapped_column(String(8))
    warnregion: Mapped[str | None] = mapped_column(String(32), index=True)  # EAWS-Mikroregion, z. B. AT-07-04-01
    messart: Mapped[str] = mapped_column(String(16), default=Messart.AUTOMATISCH)
    messgroessen: Mapped[list] = mapped_column(JSON, default=list)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)
    erstmals_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    zuletzt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SchneeMesswert(Base):
    """Ein Rohwert einer Station (S1, S3). Aendert die Quelle einen Wert, entsteht eine neue Fassung (S1 AK 3).
    Ein fehlender Wert wird gar nicht gespeichert, nie als 0 (D11). verdacht nennt die Regel aus S7."""

    __tablename__ = "schnee_messwerte"
    __table_args__ = (UniqueConstraint("station_id", "zeitpunkt", "groesse", "fassung"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("schnee_stationen.id"), index=True)
    zeitpunkt: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # hs (Schneehoehe), hn24 (Neuschnee 24 h), ta (Lufttemperatur), ta_min, ta_max, rr (Niederschlag), ff (Wind)
    groesse: Mapped[str] = mapped_column(String(16))
    wert: Mapped[float] = mapped_column(Float)
    einheit: Mapped[str] = mapped_column(String(8))
    # tag = Tageswert der Quelle, stunde = Einzelwert; Tageswerte aus Stundenwerten bildet erst die Auswertung
    takt: Mapped[str] = mapped_column(String(8), default="tag")
    fassung: Mapped[int] = mapped_column(Integer, default=1)
    verdacht: Mapped[str | None] = mapped_column(String(32))
    rohdatei_id: Mapped[int | None] = mapped_column(ForeignKey("schnee_rohdateien.id"))
    abgerufen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SchneeModellwert(Base):
    """Modellierte Schneehoehe (SNOWGRID) als Mittel je Warnregion und 500-m-Hoehenband (S10)."""

    __tablename__ = "schnee_modellwerte"
    __table_args__ = (UniqueConstraint("quelle", "warnregion", "hoehe_von", "datum", "groesse"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    quelle: Mapped[str] = mapped_column(String(64))
    warnregion: Mapped[str] = mapped_column(String(32), index=True)
    hoehe_von: Mapped[int] = mapped_column(Integer)  # Band hoehe_von bis hoehe_von + 500 m
    datum: Mapped[date] = mapped_column(Date, index=True)
    groesse: Mapped[str] = mapped_column(String(16))
    mittel: Mapped[float] = mapped_column(Float)
    minimum: Mapped[float] = mapped_column(Float)
    maximum: Mapped[float] = mapped_column(Float)
    zellen: Mapped[int] = mapped_column(Integer)
    rohdatei_id: Mapped[int | None] = mapped_column(ForeignKey("schnee_rohdateien.id"))
    abgerufen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Warnregion(Base):
    """EAWS-Mikroregion (E-35) mit Umriss als GeoJSON."""

    __tablename__ = "warnregionen"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # z. B. AT-07-04-01
    name: Mapped[str | None] = mapped_column(String(200))
    land: Mapped[str] = mapped_column(String(8))
    dienst: Mapped[str] = mapped_column(String(64))
    geometrie: Mapped[dict | None] = mapped_column(JSON)
    aktualisiert_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LageberichtFassung(Base):
    """Eine veroeffentlichte Fassung eines Lawinenlageberichts (S4). Abendbericht und Morgen-Aktualisierung
    sind zwei Fassungen mit eigener Ausgabezeit. Die Rohdatei bleibt die Quelle der Wahrheit (S4 AK 4)."""

    __tablename__ = "lagebericht_fassungen"
    __table_args__ = (UniqueConstraint("dienst", "bulletin_id", "ausgabe_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dienst: Mapped[str] = mapped_column(String(64), index=True)  # Quelle aus schnee.yaml
    bulletin_id: Mapped[str] = mapped_column(String(100))
    ausgabe_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    gueltig_von: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    gueltig_bis: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sprache: Mapped[str | None] = mapped_column(String(8))
    link: Mapped[str | None] = mapped_column(String(500))
    tendenz: Mapped[str | None] = mapped_column(String(16))
    nachgeladen: Mapped[bool] = mapped_column(Boolean, default=False)  # S5 AK 3
    rohdatei_id: Mapped[int | None] = mapped_column(ForeignKey("schnee_rohdateien.id"))
    abgerufen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    regionen: Mapped[list["LageberichtRegion"]] = relationship(
        back_populates="fassung", cascade="all, delete-orphan")


class LageberichtRegion(Base):
    """Was eine Fassung fuer eine Warnregion sagt, genau wie veroeffentlicht (E-32):
    stufen = [{"stufe": "considerable", "zahl": 3, "tageszeit": "vormittag"|"nachmittag"|"ganztags",
               "hoehe_unten": 2000 | "treeline" | None, "hoehe_oben": ..., "expositionen": []}, ...]
    probleme = [{"art": "wind_slab", "expositionen": ["N", "NE"], "hoehe_unten": 2000, "hoehe_oben": None,
                 "tageszeit": "ganztags"}, ...]"""

    __tablename__ = "lagebericht_regionen"
    __table_args__ = (UniqueConstraint("fassung_id", "warnregion"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    fassung_id: Mapped[int] = mapped_column(ForeignKey("lagebericht_fassungen.id", ondelete="CASCADE"), index=True)
    warnregion: Mapped[str] = mapped_column(String(32), index=True)
    stufen: Mapped[list] = mapped_column(JSON, default=list)
    probleme: Mapped[list] = mapped_column(JSON, default=list)

    fassung: Mapped[LageberichtFassung] = relationship(back_populates="regionen")


class SchneeAbruf(Base):
    """Ein Abruf einer Schneequelle (S8): Grundlage fuer Luecken-Alarm und Statusuebersicht."""

    __tablename__ = "schnee_abrufe"

    id: Mapped[int] = mapped_column(primary_key=True)
    quelle: Mapped[str] = mapped_column(String(64), index=True)
    zeit: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    tag: Mapped[date] = mapped_column(Date, index=True)
    werte: Mapped[int] = mapped_column(Integer, default=0)  # gelesene Messwerte, Berichtsregionen oder Modellwerte
    neu: Mapped[int] = mapped_column(Integer, default=0)  # davon neu gespeichert (ohne Wiederholungen)
    stationen: Mapped[int] = mapped_column(Integer, default=0)
    fehler: Mapped[str | None] = mapped_column(Text)
    dauer_s: Mapped[float | None] = mapped_column(Float)
