"""OpenStreetMap-Loipen und -Parkplaetze je Region (P40, P39, E-29)

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "osm_daten",
        sa.Column("region_slug", sa.String(length=100), primary_key=True),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column("inhalt", sa.JSON(), nullable=False),
        sa.Column("abgerufen_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("osm_daten")
