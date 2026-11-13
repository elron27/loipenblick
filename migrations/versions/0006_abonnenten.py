"""E-Mail-Abo: bestaetigte Abonnenten (N2, N7, E-18)

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "abonnenten",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("ziele", sa.JSON(), nullable=False),
        sa.Column("ereignisse", sa.JSON(), nullable=False),
        sa.Column("abmelde_token", sa.String(length=64), nullable=False),
        sa.Column("angefragt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bestaetigt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("letzte_mail_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("abonnenten")
