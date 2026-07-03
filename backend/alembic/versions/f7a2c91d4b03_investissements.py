"""investissements + scenarios de prix

Revision ID: f7a2c91d4b03
Revises: e657bae136a6
Create Date: 2026-07-03 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a2c91d4b03'
down_revision: Union[str, Sequence[str], None] = 'e657bae136a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'investissements',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('nom', sa.String(200), nullable=False),
        sa.Column('categorie',
                  sa.Enum('materiel', 'consommable', 'marchandise', 'evenement', 'autre',
                          name='categorieinvestissement'),
                  nullable=False, server_default='materiel'),
        sa.Column('valeur_totale', sa.Float, nullable=False),
        sa.Column('quantite', sa.Float, nullable=False, server_default='1.0'),
        sa.Column('amortissement_unites', sa.Float, nullable=False, server_default='1.0'),
        sa.Column('unites_vendues', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('date_achat', sa.DateTime),
        sa.Column('notes', sa.Text),
        sa.Column('actif', sa.Boolean, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_investissements_actif', 'investissements', ['actif'])

    op.create_table(
        'scenarios_prix',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('nom', sa.String(200), nullable=False),
        sa.Column('composants', sa.JSON),
        sa.Column('marge_pct', sa.Float, nullable=False, server_default='30.0'),
        sa.Column('taux_impots', sa.Float, nullable=False, server_default='12.5'),
        sa.Column('taux_sumup', sa.Float, nullable=False, server_default='1.75'),
        sa.Column('unites_vendues', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('scenarios_prix')
    op.drop_index('idx_investissements_actif', table_name='investissements')
    op.drop_table('investissements')
    op.execute("DROP TYPE IF EXISTS categorieinvestissement")
