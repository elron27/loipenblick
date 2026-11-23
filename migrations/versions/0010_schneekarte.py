"""Schneekarte: Stationen, Messwerte, Modellwerte, Warnregionen, Lageberichte, Rohdateien (S1-S9, E-31)

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa


revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('schnee_abrufe',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('quelle', sa.String(length=64), nullable=False),
    sa.Column('zeit', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tag', sa.Date(), nullable=False),
    sa.Column('werte', sa.Integer(), nullable=False),
    sa.Column('neu', sa.Integer(), nullable=False),
    sa.Column('stationen', sa.Integer(), nullable=False),
    sa.Column('fehler', sa.Text(), nullable=True),
    sa.Column('dauer_s', sa.Float(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_schnee_abrufe_quelle'), 'schnee_abrufe', ['quelle'], unique=False)
    op.create_index(op.f('ix_schnee_abrufe_tag'), 'schnee_abrufe', ['tag'], unique=False)
    op.create_index(op.f('ix_schnee_abrufe_zeit'), 'schnee_abrufe', ['zeit'], unique=False)
    op.create_table('schnee_rohdateien',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('quelle', sa.String(length=64), nullable=False),
    sa.Column('url', sa.String(length=1000), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('pfad', sa.String(length=500), nullable=False),
    sa.Column('groesse', sa.Integer(), nullable=False),
    sa.Column('content_type', sa.String(length=100), nullable=True),
    sa.Column('abgerufen_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sha256')
    )
    op.create_index(op.f('ix_schnee_rohdateien_quelle'), 'schnee_rohdateien', ['quelle'], unique=False)
    op.create_table('schnee_stationen',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('quelle', sa.String(length=64), nullable=False),
    sa.Column('kennung', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('lat', sa.Float(), nullable=False),
    sa.Column('lon', sa.Float(), nullable=False),
    sa.Column('hoehe_m', sa.Integer(), nullable=False),
    sa.Column('betreiber', sa.String(length=200), nullable=True),
    sa.Column('land', sa.String(length=8), nullable=True),
    sa.Column('warnregion', sa.String(length=32), nullable=True),
    sa.Column('messart', sa.String(length=16), nullable=False),
    sa.Column('messgroessen', sa.JSON(), nullable=False),
    sa.Column('aktiv', sa.Boolean(), nullable=False),
    sa.Column('erstmals_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('zuletzt_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('quelle', 'kennung')
    )
    op.create_index(op.f('ix_schnee_stationen_warnregion'), 'schnee_stationen', ['warnregion'], unique=False)
    op.create_table('warnregionen',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=True),
    sa.Column('land', sa.String(length=8), nullable=False),
    sa.Column('dienst', sa.String(length=64), nullable=False),
    sa.Column('geometrie', sa.JSON(), nullable=True),
    sa.Column('aktualisiert_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('lagebericht_fassungen',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('dienst', sa.String(length=64), nullable=False),
    sa.Column('bulletin_id', sa.String(length=100), nullable=False),
    sa.Column('ausgabe_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('gueltig_von', sa.DateTime(timezone=True), nullable=False),
    sa.Column('gueltig_bis', sa.DateTime(timezone=True), nullable=False),
    sa.Column('sprache', sa.String(length=8), nullable=True),
    sa.Column('link', sa.String(length=500), nullable=True),
    sa.Column('tendenz', sa.String(length=16), nullable=True),
    sa.Column('nachgeladen', sa.Boolean(), nullable=False),
    sa.Column('rohdatei_id', sa.Integer(), nullable=True),
    sa.Column('abgerufen_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['rohdatei_id'], ['schnee_rohdateien.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dienst', 'bulletin_id', 'ausgabe_at')
    )
    op.create_index(op.f('ix_lagebericht_fassungen_dienst'), 'lagebericht_fassungen', ['dienst'], unique=False)
    op.create_index(op.f('ix_lagebericht_fassungen_gueltig_von'), 'lagebericht_fassungen', ['gueltig_von'], unique=False)
    op.create_table('schnee_messwerte',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('station_id', sa.Integer(), nullable=False),
    sa.Column('zeitpunkt', sa.DateTime(timezone=True), nullable=False),
    sa.Column('groesse', sa.String(length=16), nullable=False),
    sa.Column('wert', sa.Float(), nullable=False),
    sa.Column('einheit', sa.String(length=8), nullable=False),
    sa.Column('takt', sa.String(length=8), nullable=False),
    sa.Column('fassung', sa.Integer(), nullable=False),
    sa.Column('verdacht', sa.String(length=32), nullable=True),
    sa.Column('rohdatei_id', sa.Integer(), nullable=True),
    sa.Column('abgerufen_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['rohdatei_id'], ['schnee_rohdateien.id'], ),
    sa.ForeignKeyConstraint(['station_id'], ['schnee_stationen.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('station_id', 'zeitpunkt', 'groesse', 'fassung')
    )
    op.create_index(op.f('ix_schnee_messwerte_station_id'), 'schnee_messwerte', ['station_id'], unique=False)
    op.create_index(op.f('ix_schnee_messwerte_zeitpunkt'), 'schnee_messwerte', ['zeitpunkt'], unique=False)
    op.create_table('schnee_modellwerte',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('quelle', sa.String(length=64), nullable=False),
    sa.Column('warnregion', sa.String(length=32), nullable=False),
    sa.Column('hoehe_von', sa.Integer(), nullable=False),
    sa.Column('datum', sa.Date(), nullable=False),
    sa.Column('groesse', sa.String(length=16), nullable=False),
    sa.Column('mittel', sa.Float(), nullable=False),
    sa.Column('minimum', sa.Float(), nullable=False),
    sa.Column('maximum', sa.Float(), nullable=False),
    sa.Column('zellen', sa.Integer(), nullable=False),
    sa.Column('rohdatei_id', sa.Integer(), nullable=True),
    sa.Column('abgerufen_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['rohdatei_id'], ['schnee_rohdateien.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('quelle', 'warnregion', 'hoehe_von', 'datum', 'groesse')
    )
    op.create_index(op.f('ix_schnee_modellwerte_datum'), 'schnee_modellwerte', ['datum'], unique=False)
    op.create_index(op.f('ix_schnee_modellwerte_warnregion'), 'schnee_modellwerte', ['warnregion'], unique=False)
    op.create_table('lagebericht_regionen',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fassung_id', sa.Integer(), nullable=False),
    sa.Column('warnregion', sa.String(length=32), nullable=False),
    sa.Column('stufen', sa.JSON(), nullable=False),
    sa.Column('probleme', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['fassung_id'], ['lagebericht_fassungen.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fassung_id', 'warnregion')
    )
    op.create_index(op.f('ix_lagebericht_regionen_fassung_id'), 'lagebericht_regionen', ['fassung_id'], unique=False)
    op.create_index(op.f('ix_lagebericht_regionen_warnregion'), 'lagebericht_regionen', ['warnregion'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_lagebericht_regionen_warnregion'), table_name='lagebericht_regionen')
    op.drop_index(op.f('ix_lagebericht_regionen_fassung_id'), table_name='lagebericht_regionen')
    op.drop_table('lagebericht_regionen')
    op.drop_index(op.f('ix_schnee_modellwerte_warnregion'), table_name='schnee_modellwerte')
    op.drop_index(op.f('ix_schnee_modellwerte_datum'), table_name='schnee_modellwerte')
    op.drop_table('schnee_modellwerte')
    op.drop_index(op.f('ix_schnee_messwerte_zeitpunkt'), table_name='schnee_messwerte')
    op.drop_index(op.f('ix_schnee_messwerte_station_id'), table_name='schnee_messwerte')
    op.drop_table('schnee_messwerte')
    op.drop_index(op.f('ix_lagebericht_fassungen_gueltig_von'), table_name='lagebericht_fassungen')
    op.drop_index(op.f('ix_lagebericht_fassungen_dienst'), table_name='lagebericht_fassungen')
    op.drop_table('lagebericht_fassungen')
    op.drop_table('warnregionen')
    op.drop_index(op.f('ix_schnee_stationen_warnregion'), table_name='schnee_stationen')
    op.drop_table('schnee_stationen')
    op.drop_index(op.f('ix_schnee_rohdateien_quelle'), table_name='schnee_rohdateien')
    op.drop_table('schnee_rohdateien')
    op.drop_index(op.f('ix_schnee_abrufe_zeit'), table_name='schnee_abrufe')
    op.drop_index(op.f('ix_schnee_abrufe_tag'), table_name='schnee_abrufe')
    op.drop_index(op.f('ix_schnee_abrufe_quelle'), table_name='schnee_abrufe')
    op.drop_table('schnee_abrufe')
