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

    loipen: Mapped[list["Loipe"]] = relationship(back_populates="quelle")


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
