"""KAHLO CAFÉ — Router IA Gemini"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.ia import (
    analyser_marche, suggerer_stock_marche,
    generer_fiche_produit, analyser_dashboard
)

router = APIRouter()


class AnalyseMarcheRequest(BaseModel):
    marche_data: dict


class SuggestionStockRequest(BaseModel):
    marche: dict
    stocks: list
    historique: list


class FicheProduitRequest(BaseModel):
    lot: dict


@router.post("/analyser-marche")
async def analyser(req: AnalyseMarcheRequest):
    try:
        texte = await analyser_marche(req.marche_data)
        return {"analyse": texte}
    except Exception as e:
        raise HTTPException(500, f"Erreur Gemini: {e}")


@router.post("/suggestion-stock")
async def suggestion_stock(req: SuggestionStockRequest):
    try:
        result = await suggerer_stock_marche(req.marche, req.stocks, req.historique)
        return result
    except Exception as e:
        raise HTTPException(500, f"Erreur Gemini: {e}")


@router.post("/fiche-produit")
async def fiche_produit(req: FicheProduitRequest):
    try:
        result = await generer_fiche_produit(req.lot)
        return result
    except Exception as e:
        raise HTTPException(500, f"Erreur Gemini: {e}")
