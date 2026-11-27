"""Hunderegel und beleuchtete Loipen je Gebiet (D25)

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gebiete", sa.Column("hunde", sa.JSON(), nullable=True))
    op.add_column("gebiete", sa.Column("beleuchtet", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("gebiete", "beleuchtet")
    op.drop_column("gebiete", "hunde")
