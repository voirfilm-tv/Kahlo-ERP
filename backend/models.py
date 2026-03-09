"""
KAHLO CAFÉ — Modèles de base de données
SQLAlchemy ORM
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


# ============================================================
#  ENUMS
# ============================================================

class StatutCommande(str, enum.Enum):
    en_attente = "en_attente"
    prete = "prete"
    remise = "remise"
    annulee = "annulee"

class StatutMarche(str, enum.Enum):
    tentative = "tentative"
    confirme = "confirme"
    passe = "passe"
    annule = "annule"

class TypeEvenement(str, enum.Enum):
    marche = "marche"
    commande = "commande"
    fournisseur = "fournisseur"
    rappel = "rappel"

class RoleUtilisateur(str, enum.Enum):
    admin = "admin"
    utilisateur = "utilisateur"

class StatutDomaine(str, enum.Enum):
    en_attente = "en_attente"
    verifie = "verifie"
    erreur = "erreur"

class ProfilKahlo(str, enum.Enum):
    florale = "florale"
    intense = "intense"
    douce = "douce"
    aventuriere = "aventuriere"

class Mouture(str, enum.Enum):
    grains = "Grains entiers"
    filtre = "Filtre"
    expresso = "Expresso"
    italienne = "Cafetière italienne"
    chemex = "Chemex"


# ============================================================
#  UTILISATEURS
# ============================================================

class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id          = Column(Integer, primary_key=True)
    username    = Column(String(100), unique=True, nullable=False)
    email       = Column(String(200), unique=True)
    nom         = Column(String(200))
    password_hash = Column(String(200), nullable=False)
    role        = Column(Enum(RoleUtilisateur), default=RoleUtilisateur.utilisateur, nullable=False)
    actif       = Column(Boolean, default=True)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
#  DOMAINES
# ============================================================

class Domaine(Base):
    __tablename__ = "domaines"

    id          = Column(Integer, primary_key=True)
    domaine     = Column(String(300), unique=True, nullable=False)
    type        = Column(String(50), default="principal")  # principal, alias, redirect
    ssl_actif   = Column(Boolean, default=False)
    statut      = Column(Enum(StatutDomaine), default=StatutDomaine.en_attente)
    dns_valeur_attendue = Column(String(500))  # IP ou CNAME attendu
    dns_valeur_actuelle = Column(String(500))  # Dernière valeur DNS trouvée
    derniere_verif = Column(DateTime)
    notes       = Column(Text)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
#  STOCK & FOURNISSEURS
# ============================================================

class Fournisseur(Base):
    __tablename__ = "fournisseurs"

    id          = Column(Integer, primary_key=True)
    nom         = Column(String(200), nullable=False)
    email       = Column(String(200))
    telephone   = Column(String(50))
    pays        = Column(String(100))
    delai_moyen = Column(Integer, default=10)  # jours
    score       = Column(Float, default=5.0)
    notes       = Column(Text)
    created_at  = Column(DateTime, server_default=func.now())

    lots = relationship("Lot", back_populates="fournisseur")
    commandes_fournisseur = relationship("CommandeFournisseur", back_populates="fournisseur")


class Lot(Base):
    __tablename__ = "lots"

    id              = Column(Integer, primary_key=True)
    fournisseur_id  = Column(Integer, ForeignKey("fournisseurs.id"))
    origine         = Column(String(200), nullable=False)  # ex: "Éthiopie Yirgacheffe"
    numero_lot      = Column(String(100), unique=True)     # ex: "LOT-2026-014"
    stock_kg        = Column(Float, default=0.0)
    seuil_alerte_kg = Column(Float, default=3.0)
    prix_achat_kg   = Column(Float, nullable=False)
    prix_vente_kg   = Column(Float, nullable=False)
    date_arrivee    = Column(DateTime)
    dlc             = Column(DateTime)
    notes_degustation = Column(Text)
    actif           = Column(Boolean, default=True)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())

    fournisseur = relationship("Fournisseur", back_populates="lots")
    lignes_commande = relationship("LigneCommande", back_populates="lot")

    @property
    def marge_pct(self):
        return round(((self.prix_vente_kg - self.prix_achat_kg) / self.prix_vente_kg) * 100)

    @property
    def est_critique(self):
        return self.stock_kg < self.seuil_alerte_kg


class CommandeFournisseur(Base):
    __tablename__ = "commandes_fournisseurs"

    id             = Column(Integer, primary_key=True)
    fournisseur_id = Column(Integer, ForeignKey("fournisseurs.id"))
    date_commande  = Column(DateTime, server_default=func.now())
    date_reception = Column(DateTime)
    statut         = Column(String(50), default="en_attente")
    details        = Column(JSON)   # [{origine, quantite_kg, prix_kg}]
    notes          = Column(Text)

    fournisseur = relationship("Fournisseur", back_populates="commandes_fournisseur")


# ============================================================
#  CRM CLIENTS
# ============================================================

class Client(Base):
    __tablename__ = "clients"

    id              = Column(Integer, primary_key=True)
    prenom          = Column(String(100), nullable=False)
    nom             = Column(String(100), nullable=False)
    email           = Column(String(200), unique=True)
    telephone       = Column(String(50))
    ville           = Column(String(200))
    anniversaire    = Column(DateTime)
    profil          = Column(Enum(ProfilKahlo))
    mouture_pref    = Column(Enum(Mouture))
    quantite_hab_g  = Column(Integer, default=250)
    origines_fav    = Column(JSON, default=list)  # ["Éthiopie", "Kenya"]
    marches_freq    = Column(JSON, default=list)  # ["Croix-Rousse"]
    tampons         = Column(Integer, default=0)
    vip             = Column(Boolean, default=False)
    notes           = Column(Text)
    brevo_id        = Column(String(100))          # ID contact Brevo
    sumup_customer_id = Column(String(100))        # ID customer SumUp (si disponible)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())

    commandes = relationship("Commande", back_populates="client")

    @property
    def total_achats(self):
        return sum(c.montant for c in self.commandes if c.statut != StatutCommande.annulee)

    @property
    def nb_achats(self):
        return len([c for c in self.commandes if c.statut == StatutCommande.remise])


# ============================================================
#  COMMANDES CLIENTS
# ============================================================

class Commande(Base):
    __tablename__ = "commandes"

    id              = Column(Integer, primary_key=True)
    numero          = Column(String(20), unique=True)   # "CMD-041"
    client_id       = Column(Integer, ForeignKey("clients.id"))
    marche_id       = Column(Integer, ForeignKey("marches.id"), nullable=True)
    statut          = Column(Enum(StatutCommande), default=StatutCommande.en_attente)
    montant_total   = Column(Float, default=0.0)
    date_commande   = Column(DateTime, server_default=func.now())
    date_remise_prev = Column(DateTime)
    date_remise_reelle = Column(DateTime)
    paiement_mode   = Column(String(50), default="sumup")  # sumup | especes
    sumup_checkout_id = Column(String(200))      # ID du checkout SumUp
    sumup_transaction_code = Column(String(200)) # Code transaction après paiement
    sumup_paid     = Column(Boolean, default=False)
    facture_generee = Column(Boolean, default=False)
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client  = relationship("Client", back_populates="commandes")
    marche  = Column(Integer, ForeignKey("marches.id"))
    lignes  = relationship("LigneCommande", back_populates="commande")


class LigneCommande(Base):
    __tablename__ = "lignes_commande"

    id         = Column(Integer, primary_key=True)
    commande_id = Column(Integer, ForeignKey("commandes.id"))
    lot_id     = Column(Integer, ForeignKey("lots.id"))
    poids_g    = Column(Integer, nullable=False)     # 250, 500, 1000
    mouture    = Column(Enum(Mouture))
    prix_unitaire = Column(Float, nullable=False)

    commande = relationship("Commande", back_populates="lignes")
    lot      = relationship("Lot", back_populates="lignes_commande")


# ============================================================
#  MARCHÉS
# ============================================================

class Marche(Base):
    __tablename__ = "marches"

    id              = Column(Integer, primary_key=True)
    nom             = Column(String(200), nullable=False)
    lieu            = Column(String(300))
    date            = Column(DateTime, nullable=False)
    statut          = Column(Enum(StatutMarche), default=StatutMarche.tentative)
    frais_prevus    = Column(Float, default=0.0)
    frais_reels     = Column(Float)
    km_aller_retour = Column(Float)
    # Stats post-marché
    ca_realise      = Column(Float)
    stock_emmene_kg = Column(Float)
    stock_ramene_kg = Column(Float)
    nb_clients      = Column(Integer)
    meteo           = Column(String(100))
    notes           = Column(Text)
    # Sync calendrier
    google_event_id = Column(String(200))
    caldav_event_id = Column(String(200))
    created_at      = Column(DateTime, server_default=func.now())

    @property
    def marge_nette(self):
        if self.ca_realise and self.frais_reels:
            return self.ca_realise - self.frais_reels
        return None

    @property
    def taux_ecoulement(self):
        if self.stock_emmene_kg and self.stock_ramene_kg:
            vendu = self.stock_emmene_kg - self.stock_ramene_kg
            return round((vendu / self.stock_emmene_kg) * 100)
        return None


# ============================================================
#  CALENDRIER (événements génériques)
# ============================================================

class Evenement(Base):
    __tablename__ = "evenements"

    id              = Column(Integer, primary_key=True)
    type            = Column(Enum(TypeEvenement), nullable=False)
    titre           = Column(String(300), nullable=False)
    date_debut      = Column(DateTime, nullable=False)
    date_fin        = Column(DateTime)
    all_day         = Column(Boolean, default=True)
    notes           = Column(Text)
    # Liens vers d'autres entités
    marche_id       = Column(Integer, ForeignKey("marches.id"), nullable=True)
    commande_id     = Column(Integer, ForeignKey("commandes.id"), nullable=True)
    fournisseur_id  = Column(Integer, ForeignKey("fournisseurs.id"), nullable=True)
    # Sync
    google_event_id = Column(String(200))
    caldav_uid      = Column(String(200))
    created_at      = Column(DateTime, server_default=func.now())
