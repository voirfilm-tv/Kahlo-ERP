"""
KAHLO CAFÉ — Router Investissements
Suivi des investissements (amortissement par produit vendu) +
calculatrice de prix de vente (marge, impôts, SumUp) + rentabilité.
Reproduit la calculatrice Excel de Kahlo Café.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import Investissement, ScenarioPrix, CategorieInvestissement
from routers.auth import verifier_token

router = APIRouter()


# ============================================================
#  SCHEMAS
# ============================================================

class InvestissementCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=200)
    categorie: CategorieInvestissement = CategorieInvestissement.materiel
    valeur_totale: float = Field(gt=0)
    quantite: float = Field(default=1.0, gt=0)
    amortissement_unites: float = Field(default=1.0, gt=0)
    unites_vendues: float = Field(default=0.0, ge=0)
    date_achat: Optional[datetime] = None
    notes: Optional[str] = None


class InvestissementUpdate(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=1, max_length=200)
    categorie: Optional[CategorieInvestissement] = None
    valeur_totale: Optional[float] = Field(default=None, gt=0)
    quantite: Optional[float] = Field(default=None, gt=0)
    amortissement_unites: Optional[float] = Field(default=None, gt=0)
    unites_vendues: Optional[float] = Field(default=None, ge=0)
    date_achat: Optional[datetime] = None
    notes: Optional[str] = None
    actif: Optional[bool] = None


class EnregistrerVentes(BaseModel):
    quantite: float = Field(default=1.0, gt=0)


class ComposantPrix(BaseModel):
    libelle: str = Field(min_length=1, max_length=200)
    valeur: float = Field(ge=0)


class CalculPrixInput(BaseModel):
    composants: List[ComposantPrix]
    marge_pct: float = Field(default=30.0, ge=0, le=500)
    taux_impots: float = Field(default=12.5, ge=0, le=99)
    taux_sumup: float = Field(default=1.75, ge=0, le=99)

    @field_validator("taux_sumup")
    @classmethod
    def taux_cumules_valides(cls, v: float, info) -> float:
        impots = info.data.get("taux_impots", 0)
        if impots + v >= 100:
            raise ValueError("La somme des taux (impôts + SumUp) doit être inférieure à 100%")
        return v


class ScenarioCreate(CalculPrixInput):
    nom: str = Field(min_length=1, max_length=200)
    unites_vendues: float = Field(default=0.0, ge=0)
    notes: Optional[str] = None


class ScenarioUpdate(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=1, max_length=200)
    composants: Optional[List[ComposantPrix]] = None
    marge_pct: Optional[float] = Field(default=None, ge=0, le=500)
    taux_impots: Optional[float] = Field(default=None, ge=0, le=99)
    taux_sumup: Optional[float] = Field(default=None, ge=0, le=99)
    unites_vendues: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None


# ============================================================
#  HELPERS
# ============================================================

def calculer_prix_vente(composants: list[dict], marge_pct: float, taux_impots: float, taux_sumup: float) -> dict:
    """Formule de la calculatrice Excel :
    PV = (somme des coûts + valeur de marge) / (1 - (impôts + sumup)/100)
    """
    cout_total = sum((c.get("valeur") or 0) for c in composants)
    marge_valeur = cout_total * marge_pct / 100
    taux = (taux_impots + taux_sumup) / 100
    if taux >= 1:
        raise HTTPException(status_code=400, detail="Taux cumulés >= 100% — calcul impossible")
    prix_vente = (cout_total + marge_valeur) / (1 - taux)
    frais = prix_vente - cout_total - marge_valeur
    return {
        "cout_total": round(cout_total, 4),
        "marge_valeur": round(marge_valeur, 4),
        "frais_taxes_paiement": round(frais, 4),
        "prix_vente": round(prix_vente, 2),
        "prix_vente_exact": round(prix_vente, 4),
        "marge_pct": marge_pct,
        "taux_impots": taux_impots,
        "taux_sumup": taux_sumup,
    }


def _serialise_investissement(inv: Investissement) -> dict:
    return {
        "id": inv.id,
        "nom": inv.nom,
        "categorie": inv.categorie.value if inv.categorie else "autre",
        "valeur_totale": inv.valeur_totale,
        "quantite": inv.quantite,
        "amortissement_unites": inv.amortissement_unites,
        "unites_vendues": inv.unites_vendues,
        "cout_unitaire": round(inv.cout_unitaire, 4),
        "cout_par_produit": round(inv.cout_par_produit, 4),
        "somme_remboursee": round(inv.somme_remboursee, 2),
        "restant": round(inv.restant, 2),
        "progression_pct": inv.progression_pct,
        "date_achat": inv.date_achat.isoformat() if inv.date_achat else None,
        "notes": inv.notes,
        "actif": inv.actif,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }


def _serialise_scenario(s: ScenarioPrix) -> dict:
    return {
        "id": s.id,
        "nom": s.nom,
        "composants": s.composants or [],
        "marge_pct": s.marge_pct,
        "taux_impots": s.taux_impots,
        "taux_sumup": s.taux_sumup,
        "unites_vendues": s.unites_vendues,
        "cout_total": round(s.cout_total, 4),
        "marge_valeur": round(s.marge_valeur, 4),
        "prix_vente": round(s.prix_vente, 2),
        "marge_totale": round(s.marge_totale, 2),
        "notes": s.notes,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# ============================================================
#  STATS & CALCULATRICE (routes statiques avant /{id})
# ============================================================

@router.get("/stats")
async def stats_investissements(db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    """Vue globale : total investi, remboursé, restant, % amorti."""
    result = await db.execute(select(Investissement).where(Investissement.actif == True))
    invs = result.scalars().all()

    total_investi = sum(i.valeur_totale for i in invs)
    total_rembourse = sum(min(i.somme_remboursee, i.valeur_totale) for i in invs)
    total_restant = sum(max(i.restant, 0) for i in invs)
    nb_amortis = sum(1 for i in invs if i.restant <= 0)

    result_s = await db.execute(select(ScenarioPrix))
    scenarios = result_s.scalars().all()
    marge_totale = sum(s.marge_totale for s in scenarios)

    return {
        "nb_investissements": len(invs),
        "nb_amortis": nb_amortis,
        "total_investi": round(total_investi, 2),
        "total_rembourse": round(total_rembourse, 2),
        "total_restant": round(total_restant, 2),
        "progression_pct": min(100, round((total_rembourse / total_investi) * 100)) if total_investi else 100,
        "marge_totale_scenarios": round(marge_totale, 2),
    }


@router.post("/calculatrice")
async def calculatrice(data: CalculPrixInput, token: str = Depends(verifier_token)):
    """Calcule un prix de vente sans rien enregistrer (aperçu live)."""
    return calculer_prix_vente(
        [c.model_dump() for c in data.composants],
        data.marge_pct, data.taux_impots, data.taux_sumup,
    )


# ============================================================
#  SCÉNARIOS DE PRIX
# ============================================================

@router.get("/scenarios")
async def get_scenarios(db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    result = await db.execute(select(ScenarioPrix).order_by(ScenarioPrix.nom))
    return [_serialise_scenario(s) for s in result.scalars().all()]


@router.post("/scenarios", status_code=201)
async def creer_scenario(data: ScenarioCreate, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    scenario = ScenarioPrix(
        nom=data.nom,
        composants=[c.model_dump() for c in data.composants],
        marge_pct=data.marge_pct,
        taux_impots=data.taux_impots,
        taux_sumup=data.taux_sumup,
        unites_vendues=data.unites_vendues,
        notes=data.notes,
    )
    db.add(scenario)
    await db.flush()
    return _serialise_scenario(scenario)


@router.patch("/scenarios/{scenario_id}")
async def modifier_scenario(
    scenario_id: int,
    data: ScenarioUpdate,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token),
):
    result = await db.execute(select(ScenarioPrix).where(ScenarioPrix.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scénario introuvable")

    valeurs = data.model_dump(exclude_none=True)
    if "composants" in valeurs:
        valeurs["composants"] = [dict(c) for c in valeurs["composants"]]

    # Valider les taux cumulés après application
    impots = valeurs.get("taux_impots", scenario.taux_impots)
    sumup = valeurs.get("taux_sumup", scenario.taux_sumup)
    if (impots or 0) + (sumup or 0) >= 100:
        raise HTTPException(status_code=400, detail="Taux cumulés >= 100% — calcul impossible")

    for field, value in valeurs.items():
        setattr(scenario, field, value)
    await db.flush()
    return _serialise_scenario(scenario)


@router.delete("/scenarios/{scenario_id}", status_code=204)
async def supprimer_scenario(scenario_id: int, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    result = await db.execute(select(ScenarioPrix).where(ScenarioPrix.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scénario introuvable")
    await db.delete(scenario)


# ============================================================
#  CRUD INVESTISSEMENTS
# ============================================================

@router.get("/")
async def get_investissements(
    actif: bool = True,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token),
):
    result = await db.execute(
        select(Investissement)
        .where(Investissement.actif == actif)
        .order_by(Investissement.created_at.desc())
    )
    return [_serialise_investissement(i) for i in result.scalars().all()]


@router.post("/", status_code=201)
async def creer_investissement(
    data: InvestissementCreate,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token),
):
    inv = Investissement(**data.model_dump())
    db.add(inv)
    await db.flush()
    return _serialise_investissement(inv)


@router.get("/{inv_id}")
async def get_investissement(inv_id: int, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    result = await db.execute(select(Investissement).where(Investissement.id == inv_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investissement introuvable")
    return _serialise_investissement(inv)


@router.patch("/{inv_id}")
async def modifier_investissement(
    inv_id: int,
    data: InvestissementUpdate,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token),
):
    result = await db.execute(select(Investissement).where(Investissement.id == inv_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investissement introuvable")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(inv, field, value)
    await db.flush()
    return _serialise_investissement(inv)


@router.post("/{inv_id}/vente")
async def enregistrer_ventes(
    inv_id: int,
    data: EnregistrerVentes,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token),
):
    """Incrémente le compteur d'unités vendues (avance l'amortissement)."""
    result = await db.execute(select(Investissement).where(Investissement.id == inv_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investissement introuvable")

    inv.unites_vendues = (inv.unites_vendues or 0) + data.quantite
    await db.flush()
    return _serialise_investissement(inv)


@router.delete("/{inv_id}", status_code=204)
async def supprimer_investissement(inv_id: int, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    result = await db.execute(select(Investissement).where(Investissement.id == inv_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investissement introuvable")
    await db.delete(inv)
