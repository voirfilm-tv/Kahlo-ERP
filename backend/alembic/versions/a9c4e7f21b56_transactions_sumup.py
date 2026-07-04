"""transactions sumup importées

Revision ID: a9c4e7f21b56
Revises: f7a2c91d4b03
Create Date: 2026-07-04 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9c4e7f21b56'
down_revision: Union[str, Sequence[str], None] = 'f7a2c91d4b03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transactions_sumup',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('transaction_code', sa.String(100), unique=True, nullable=False),
        sa.Column('montant', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('devise', sa.String(10), server_default='EUR'),
        sa.Column('frais', sa.Float, server_default='0.0'),
        sa.Column('statut', sa.String(50)),
        sa.Column('payment_type', sa.String(50)),
        sa.Column('entry_mode', sa.String(50)),
        sa.Column('produits', sa.JSON),
        sa.Column('date_transaction', sa.DateTime),
        sa.Column('stock_traite', sa.Boolean, server_default=sa.text('false')),
        sa.Column('stock_details', sa.JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_tx_sumup_date', 'transactions_sumup', ['date_transaction'])
    op.create_index('idx_tx_sumup_statut', 'transactions_sumup', ['statut'])


def downgrade() -> None:
    op.drop_index('idx_tx_sumup_statut', table_name='transactions_sumup')
    op.drop_index('idx_tx_sumup_date', table_name='transactions_sumup')
    op.drop_table('transactions_sumup')
