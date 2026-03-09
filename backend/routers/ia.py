"""KAHLO CAFÉ — Router IA Gemini"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from services.ia import (
    analyser_marche, suggerer_stock_marche,
    generer_fiche_produit, analyser_dashboard
)
from routers.auth import verifier_token

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
async def analyser(req: AnalyseMarcheRequest, token: str = Depends(verifier_token)):
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
