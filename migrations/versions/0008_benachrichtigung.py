"""Benachrichtigung einzelner Loipen: Meldeprotokoll gegen Doppelversand (N11), Push-Zaehler je Tag (N10)

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
        "meldeprotokoll",
        sa.Column("loipe_id", sa.Integer(), sa.ForeignKey("loipen.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status_art", sa.String(length=16), nullable=True),
        sa.Column("status_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("befahrbar_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "push_tage",
        sa.Column("tag", sa.Date(), primary_key=True),
        sa.Column("anzahl", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("grenze_gemeldet", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_table("push_tage")
    op.drop_table("meldeprotokoll")
