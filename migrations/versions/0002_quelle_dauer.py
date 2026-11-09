"""Dauer des letzten Abrufs je Quelle (B2)

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quellen", sa.Column("last_dauer_s", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("quellen", "last_dauer_s")
