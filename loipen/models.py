"""Datenmodell: Quelle -> Gebiet -> Loipe -> Zustand."""

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Status(StrEnum):
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


class Base(DeclarativeBase):
    pass


class Quelle(Base):
    """Eine konfigurierte Datenquelle, z. B. tegernsee.com mit Adapter 'ats'."""

    __tablename__ = "quellen"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    adapter: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(String(500))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Monitoring des letzten Laufs
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(16))
    last_count: Mapped[int | None] = mapped_column(Integer)
    last_error: Mapped[str | None] = mapped_column(Text)

    loipen: Mapped[list["Loipe"]] = relationship(back_populates="quelle")


class Gebiet(Base):
    """Ein Ort oder Loipennetz, z. B. 'Bayrischzell'."""

    __tablename__ = "gebiete"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(100))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    tourist_url: Mapped[str | None] = mapped_column(String(500))

    loipen: Mapped[list["Loipe"]] = relationship(back_populates="gebiet")


class Loipe(Base):
    """Stammdaten einer Loipe. Identitaet = Quelle + source_key, nicht der Name."""

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
    laenge_km: Mapped[float | None] = mapped_column(Float)
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
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
    """Ein beobachteter Zustand. Neue Zeile nur, wenn sich etwas geaendert hat."""

    __tablename__ = "zustaende"

    id: Mapped[int] = mapped_column(primary_key=True)
    loipe_id: Mapped[int] = mapped_column(ForeignKey("loipen.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default=Status.UNBEKANNT)
    gespurt_klassisch_km: Mapped[float | None] = mapped_column(Float)
    gespurt_skating_km: Mapped[float | None] = mapped_column(Float)
    gespurt_gesamt_km: Mapped[float | None] = mapped_column(Float)
    schneehoehe_cm: Mapped[int | None] = mapped_column(Integer)
    # Drei Zeiten getrennt halten: Aenderung laut Quelle, erster und letzter Abruf
    quelle_aktualisiert_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    abgerufen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    zuletzt_bestaetigt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    rohtext: Mapped[str | None] = mapped_column(Text)

    loipe: Mapped[Loipe] = relationship(back_populates="zustaende")
