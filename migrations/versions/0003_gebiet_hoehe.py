"""Hoehe je Gebiet fuer das Talprofil

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gebiete", sa.Column("hoehe_m", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("gebiete", "hoehe_m")
