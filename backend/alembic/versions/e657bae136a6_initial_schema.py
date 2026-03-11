"""initial schema

Revision ID: e657bae136a6
Revises:
Create Date: 2026-03-10 21:33:20.164268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e657bae136a6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Utilisateurs ---
    op.create_table(
        'utilisateurs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('email', sa.String(200), unique=True),
        sa.Column('nom', sa.String(200)),
        sa.Column('password_hash', sa.String(200), nullable=False),
        sa.Column('role', sa.Enum('admin', 'utilisateur', name='roleutilisateur'), nullable=False, server_default='utilisateur'),
        sa.Column('actif', sa.Boolean, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # --- Domaines ---
    op.create_table(
        'domaines',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('domaine', sa.String(300), unique=True, nullable=False),
        sa.Column('type', sa.String(50), server_default='principal'),
        sa.Column('ssl_actif', sa.Boolean, server_default=sa.text('false')),
        sa.Column('statut', sa.Enum('en_attente', 'verifie', 'erreur', name='statutdomaine'), server_default='en_attente'),
        sa.Column('dns_valeur_attendue', sa.String(500)),
        sa.Column('dns_valeur_actuelle', sa.String(500)),
        sa.Column('derniere_verif', sa.DateTime),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # --- Fournisseurs ---
    op.create_table(
        'fournisseurs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('nom', sa.String(200), nullable=False),
        sa.Column('email', sa.String(200)),
        sa.Column('telephone', sa.String(50)),
        sa.Column('pays', sa.String(100)),
        sa.Column('delai_moyen', sa.Integer, server_default='10'),
        sa.Column('score', sa.Float, server_default='5.0'),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # --- Lots ---
    op.create_table(
        'lots',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('fournisseur_id', sa.Integer, sa.ForeignKey('fournisseurs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('origine', sa.String(200), nullable=False),
        sa.Column('numero_lot', sa.String(100), unique=True),
        sa.Column('stock_kg', sa.Float, server_default='0.0'),
        sa.Column('seuil_alerte_kg', sa.Float, server_default='3.0'),
        sa.Column('prix_achat_kg', sa.Float, nullable=False),
        sa.Column('prix_vente_kg', sa.Float, nullable=False),
        sa.Column('date_arrivee', sa.DateTime),
        sa.Column('dlc', sa.DateTime),
        sa.Column('notes_degustation', sa.Text),
        sa.Column('actif', sa.Boolean, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # --- Commandes fournisseurs ---
    op.create_table(
        'commandes_fournisseurs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('fournisseur_id', sa.Integer, sa.ForeignKey('fournisseurs.id', ondelete='CASCADE')),
        sa.Column('date_commande', sa.DateTime, server_default=sa.func.now()),
        sa.Column('date_reception', sa.DateTime),
        sa.Column('statut', sa.String(50), server_default='en_attente'),
        sa.Column('details', sa.JSON),
        sa.Column('notes', sa.Text),
    )

    # --- Clients ---
    op.create_table(
        'clients',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('prenom', sa.String(100), nullable=False),
        sa.Column('nom', sa.String(100), nullable=False),
        sa.Column('email', sa.String(200), unique=True),
        sa.Column('telephone', sa.String(50)),
        sa.Column('ville', sa.String(200)),
        sa.Column('anniversaire', sa.DateTime),
        sa.Column('profil', sa.Enum('florale', 'intense', 'douce', 'aventuriere', name='profilkahlo')),
        sa.Column('mouture_pref', sa.Enum('Grains entiers', 'Filtre', 'Expresso', 'Cafetière italienne', 'Chemex', name='mouture')),
        sa.Column('quantite_hab_g', sa.Integer, server_default='250'),
        sa.Column('origines_fav', sa.JSON),
        sa.Column('marches_freq', sa.JSON),
        sa.Column('tampons', sa.Integer, server_default='0'),
        sa.Column('vip', sa.Boolean, server_default=sa.text('false')),
        sa.Column('notes', sa.Text),
        sa.Column('brevo_id', sa.String(100)),
        sa.Column('sumup_customer_id', sa.String(100)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # --- Marchés ---
    op.create_table(
        'marches',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('nom', sa.String(200), nullable=False),
        sa.Column('lieu', sa.String(300)),
        sa.Column('date', sa.DateTime, nullable=False),
        sa.Column('statut', sa.Enum('tentative', 'confirme', 'passe', 'annule', name='statutmarche'), server_default='tentative'),
        sa.Column('frais_prevus', sa.Float, server_default='0.0'),
        sa.Column('frais_reels', sa.Float),
        sa.Column('km_aller_retour', sa.Float),
        sa.Column('ca_realise', sa.Float),
        sa.Column('stock_emmene_kg', sa.Float),
        sa.Column('stock_ramene_kg', sa.Float),
        sa.Column('nb_clients', sa.Integer),
        sa.Column('meteo', sa.String(100)),
        sa.Column('notes', sa.Text),
        sa.Column('google_event_id', sa.String(200)),
        sa.Column('caldav_event_id', sa.String(200)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # --- Commandes ---
    op.create_table(
        'commandes',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('numero', sa.String(20), unique=True),
        sa.Column('client_id', sa.Integer, sa.ForeignKey('clients.id', ondelete='SET NULL'), nullable=True),
        sa.Column('marche_id', sa.Integer, sa.ForeignKey('marches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('statut', sa.Enum('en_attente', 'prete', 'remise', 'annulee', name='statutcommande'), server_default='en_attente'),
        sa.Column('montant_total', sa.Float, server_default='0.0'),
        sa.Column('date_commande', sa.DateTime, server_default=sa.func.now()),
        sa.Column('date_remise_prev', sa.DateTime),
        sa.Column('date_remise_reelle', sa.DateTime),
        sa.Column('paiement_mode', sa.String(50), server_default='sumup'),
        sa.Column('sumup_checkout_id', sa.String(200)),
        sa.Column('sumup_transaction_code', sa.String(200)),
        sa.Column('sumup_paid', sa.Boolean, server_default=sa.text('false')),
        sa.Column('facture_generee', sa.Boolean, server_default=sa.text('false')),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # --- Lignes commande ---
    op.create_table(
        'lignes_commande',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('commande_id', sa.Integer, sa.ForeignKey('commandes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lot_id', sa.Integer, sa.ForeignKey('lots.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('poids_g', sa.Integer, nullable=False),
        sa.Column('mouture', sa.Enum('Grains entiers', 'Filtre', 'Expresso', 'Cafetière italienne', 'Chemex', name='mouture', create_type=False)),
        sa.Column('prix_unitaire', sa.Float, nullable=False),
    )

    # --- Evenements ---
    op.create_table(
        'evenements',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('type', sa.Enum('marche', 'commande', 'fournisseur', 'rappel', name='typeevenement'), nullable=False),
        sa.Column('titre', sa.String(300), nullable=False),
        sa.Column('date_debut', sa.DateTime, nullable=False),
        sa.Column('date_fin', sa.DateTime),
        sa.Column('all_day', sa.Boolean, server_default=sa.text('true')),
        sa.Column('notes', sa.Text),
        sa.Column('marche_id', sa.Integer, sa.ForeignKey('marches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('commande_id', sa.Integer, sa.ForeignKey('commandes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('fournisseur_id', sa.Integer, sa.ForeignKey('fournisseurs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('google_event_id', sa.String(200)),
        sa.Column('caldav_uid', sa.String(200)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # --- Index de performance ---
    op.create_index('idx_lots_origine', 'lots', ['origine'])
    op.create_index('idx_lots_actif', 'lots', ['actif'])
    op.create_index('idx_commandes_statut', 'commandes', ['statut'])
    op.create_index('idx_commandes_date', 'commandes', ['date_commande'])
    op.create_index('idx_commandes_client', 'commandes', ['client_id'])
    op.create_index('idx_commandes_marche', 'commandes', ['marche_id'])
    op.create_index('idx_commandes_sumup', 'commandes', ['sumup_checkout_id'])
    op.create_index('idx_clients_email', 'clients', ['email'])
    op.create_index('idx_clients_nom', 'clients', ['nom', 'prenom'])
    op.create_index('idx_evenements_date', 'evenements', ['date_debut'])
    op.create_index('idx_marches_date', 'marches', ['date'])
    op.create_index('idx_lignes_commande_id', 'lignes_commande', ['commande_id'])
    op.create_index('idx_lignes_lot_id', 'lignes_commande', ['lot_id'])


def downgrade() -> None:
    op.drop_table('evenements')
    op.drop_table('lignes_commande')
    op.drop_table('commandes')
    op.drop_table('marches')
    op.drop_table('clients')
    op.drop_table('commandes_fournisseurs')
    op.drop_table('lots')
    op.drop_table('fournisseurs')
    op.drop_table('domaines')
    op.drop_table('utilisateurs')

    # Drop enums
    for enum_name in ['roleutilisateur', 'statutdomaine', 'profilkahlo', 'mouture',
                      'statutmarche', 'statutcommande', 'typeevenement']:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
