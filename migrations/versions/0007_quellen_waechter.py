"""Quellen-Waechter: Abrufprotokoll je Lauf und Alarmzustand je Quelle (B26)

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "abrufprotokoll",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quelle_id", sa.Integer(), sa.ForeignKey("quellen.id"), nullable=False),
        sa.Column("zeit", sa.DateTime(timezone=True), nullable=False),
        sa.Column("anzahl", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("befund", sa.String(length=16), nullable=True),
        sa.Column("fehler", sa.Text(), nullable=True),
        sa.Column("dauer_s", sa.Float(), nullable=True),
    )
    op.create_index("ix_abrufprotokoll_quelle_id", "abrufprotokoll", ["quelle_id"])
    op.add_column("quellen", sa.Column("waechter_alarm", sa.String(length=16), nullable=True))
    op.add_column("quellen", sa.Column("waechter_seit", sa.DateTime(timezone=True), nullable=True))
    op.add_column("quellen", sa.Column("waechter_gemeldet_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("quellen", "waechter_gemeldet_at")
    op.drop_column("quellen", "waechter_seit")
    op.drop_column("quellen", "waechter_alarm")
    op.drop_index("ix_abrufprotokoll_quelle_id", table_name="abrufprotokoll")
    op.drop_table("abrufprotokoll")
