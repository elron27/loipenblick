"""Mehr Daten je Loipe: Hinweis, Sperrgrund, Schneehoehe Berg, Stammdaten, Webcams, Verleih (P41, D21, D9, D10)

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

ZUSTAND = [
    ("schneehoehe_berg_cm", sa.Integer()),
    ("hinweis", sa.Text()),
    ("sperrgrund", sa.String(length=100)),
]
LOIPE = [
    ("kunstschnee", sa.Boolean()),
    ("loipengebiet", sa.String(length=200)),
    ("einstiege", sa.JSON()),
    ("hoehenmeter", sa.Integer()),
    ("hoechster_punkt_m", sa.Integer()),
    ("tiefster_punkt_m", sa.Integer()),
    ("dauer_min", sa.Integer()),
    ("kondition", sa.Integer()),
    ("technik_note", sa.Integer()),
    ("merkmale", sa.JSON()),
    ("webcams", sa.JSON()),
    ("herkunft", sa.JSON()),
]
GEBIET = [
    ("webcams", sa.JSON()),
    ("verleih", sa.JSON()),
    ("hand_geprueft_am", sa.Date()),
]


def upgrade() -> None:
    for tabelle, spalten in (("zustaende", ZUSTAND), ("loipen", LOIPE), ("gebiete", GEBIET)):
        for name, typ in spalten:
            op.add_column(tabelle, sa.Column(name, typ, nullable=True))


def downgrade() -> None:
    for tabelle, spalten in (("zustaende", ZUSTAND), ("loipen", LOIPE), ("gebiete", GEBIET)):
        for name, _ in reversed(spalten):
            op.drop_column(tabelle, name)
