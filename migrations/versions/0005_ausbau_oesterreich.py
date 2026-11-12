"""Ausbaustufe 1 Oesterreich: Bundesland an der Region, mehrsprachige Namen, Wetterdienst und
Grenzhinweis am Gebiet (D16, P12, D17, U31)

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("regionen", sa.Column("bundesland", sa.String(length=64), nullable=True))
    op.add_column("gebiete", sa.Column("namen", sa.JSON(), nullable=True))
    op.add_column("gebiete", sa.Column("wetterdienst", sa.String(length=16), nullable=True))
    op.add_column("gebiete", sa.Column("grenzinfo", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("gebiete", "grenzinfo")
    op.drop_column("gebiete", "wetterdienst")
    op.drop_column("gebiete", "namen")
    op.drop_column("regionen", "bundesland")
