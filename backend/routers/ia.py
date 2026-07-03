"""KAHLO CAFÉ — Router IA Gemini"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import os
import logging

from database import get_db
from models import Commande, LigneCommande, Lot, Client, Marche, StatutCommande, StatutMarche
from services.ia import (
    analyser_marche, suggerer_stock_marche,
    generer_fiche_produit, analyser_dashboard
)
from routers.auth import verifier_token

logger = logging.getLogger(__name__)

router = APIRouter()


def _ia_configuree():
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="IA non configurée — ajoutez votre clé Gemini dans Paramètres → Gemini IA"
        )


class AnalyseMarcheRequest(BaseModel):
    marche_data: dict


class SuggestionStockRequest(BaseModel):
    marche: dict
    stocks: list
    historique: list


class FicheProduitRequest(BaseModel):
    lot: dict


@router.post("/analyser-dashboard")
async def analyser_situation_dashboard(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token),
):
    """Analyse business du mois : le backend rassemble les données puis interroge Gemini."""
    _ia_configuree()

    now = datetime.now()
    debut_mois = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    r = await db.execute(
        select(func.sum(Commande.montant_total)).where(
            Commande.statut != StatutCommande.annulee,
            Commande.date_commande >= debut_mois,
        )
    )
    ca_mois = round(r.scalar() or 0, 2)

    r = await db.execute(
        select(func.count()).where(
            Marche.statut == StatutMarche.passe,
            Marche.date >= debut_mois,
        )
    )
    nb_marches = r.scalar() or 0

    r = await db.execute(select(Lot).where(Lot.actif == True))
    lots = r.scalars().all()
    stocks_critiques = sum(1 for l in lots if l.est_critique)

    r = await db.execute(select(func.count()).where(Commande.statut == StatutCommande.en_attente))
    commandes_attente = r.scalar() or 0

    r = await db.execute(
        select(Lot.origine, func.sum(LigneCommande.prix_unitaire).label("ca"))
        .join(LigneCommande, LigneCommande.lot_id == Lot.id)
        .join(Commande, Commande.id == LigneCommande.commande_id)
        .where(Commande.statut != StatutCommande.annulee)
        .group_by(Lot.origine)
        .order_by(func.sum(LigneCommande.prix_unitaire).desc())
        .limit(1)
    )
    top = r.first()
    top_origine = top.origine if top else "aucune vente"

    seuil_inactif = now - timedelta(days=45)
    r = await db.execute(select(Client).options(selectinload(Client.commandes)))
    clients = r.scalars().all()
    clients_inactifs = 0
    for c in clients:
        dates = [cmd.date_commande for cmd in c.commandes if cmd.date_commande]
        if dates and max(dates) < seuil_inactif:
            clients_inactifs += 1

    try:
        texte = await analyser_dashboard({
            "ca_mois": ca_mois,
            "ca_objectif": float(os.getenv("OBJECTIF_CA_MENSUEL", "3500")),
            "nb_marches": nb_marches,
            "stocks_critiques": stocks_critiques,
            "commandes_attente": commandes_attente,
            "top_origine": top_origine,
            "clients_inactifs": clients_inactifs,
        })
        return {"analyse": texte}
    except Exception:
        logger.exception("Erreur Gemini lors de l'analyse dashboard")
        raise HTTPException(502, "L'analyse IA a échoué — vérifiez votre clé Gemini")


@router.post("/analyser-marche")
async def analyser(req: AnalyseMarcheRequest, token: str = Depends(verifier_token)):
    _ia_configuree()
    try:
        texte = await analyser_marche(req.marche_data)
        return {"analyse": texte}
    except Exception as e:
        raise HTTPException(500, f"Erreur Gemini: {e}")


@router.post("/suggestion-stock")
async def suggestion_stock(req: SuggestionStockRequest, token: str = Depends(verifier_token)):
    try:
        result = await suggerer_stock_marche(req.marche, req.stocks, req.historique)
        return result
    except Exception as e:
        raise HTTPException(500, f"Erreur Gemini: {e}")


@router.post("/fiche-produit")
async def fiche_produit(req: FicheProduitRequest, token: str = Depends(verifier_token)):
    try:
        result = await generer_fiche_produit(req.lot)
        return result
    except Exception as e:
        raise HTTPException(500, f"Erreur Gemini: {e}")
