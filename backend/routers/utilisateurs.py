"""
KAHLO CAFÉ — Router Utilisateurs & Domaines
Gestion multi-utilisateurs (admin only) + gestion domaines avec validation DNS.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from datetime import datetime, timezone
import socket
import logging

from database import get_db
from models import Utilisateur, RoleUtilisateur, Domaine, StatutDomaine
from routers.auth import get_current_user_payload, require_admin, pwd_context

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
#  SCHEMAS
# ============================================================

class ChangerMotDePasse(BaseModel):
    ancien_mot_de_passe: str
    nouveau_mot_de_passe: str
    confirmer_mot_de_passe: str


class CreerUtilisateur(BaseModel):
    username: str
    nom: Optional[str] = None
    email: Optional[str] = None
    password: str
    role: str = "utilisateur"  # admin | utilisateur


class ModifierUtilisateur(BaseModel):
    nom: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    actif: Optional[bool] = None
    nouveau_mot_de_passe: Optional[str] = None


class CreerDomaine(BaseModel):
    domaine: str
    type: str = "principal"  # principal | alias | redirect
    dns_valeur_attendue: Optional[str] = None
    notes: Optional[str] = None


class ModifierDomaine(BaseModel):
    type: Optional[str] = None
    ssl_actif: Optional[bool] = None
    dns_valeur_attendue: Optional[str] = None
    notes: Optional[str] = None


# ============================================================
#  MOT DE PASSE (tout utilisateur connecté)
# ============================================================

@router.post("/mot-de-passe")
async def changer_mot_de_passe(
    data: ChangerMotDePasse,
    payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
):
    """Change le mot de passe de l'utilisateur connecté."""
    if data.nouveau_mot_de_passe != data.confirmer_mot_de_passe:
        raise HTTPException(status_code=400, detail="Les mots de passe ne correspondent pas")

    if len(data.nouveau_mot_de_passe) < 8:
        raise HTTPException(status_code=400, detail="Le mot de passe doit faire au moins 8 caractères")

    result = await db.execute(
        select(Utilisateur).where(Utilisateur.id == payload["user_id"])
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if not pwd_context.verify(data.ancien_mot_de_passe, user.password_hash):
        raise HTTPException(status_code=401, detail="Ancien mot de passe incorrect")

    user.password_hash = pwd_context.hash(data.nouveau_mot_de_passe)
    await db.commit()
    return {"message": "Mot de passe modifié avec succès"}


# ============================================================
#  GESTION UTILISATEURS (admin only)
# ============================================================

@router.get("/")
async def lister_utilisateurs(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Liste tous les utilisateurs (admin seulement)."""
    result = await db.execute(
        select(Utilisateur).order_by(Utilisateur.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "nom": u.nom,
            "email": u.email,
            "role": u.role.value,
            "actif": u.actif,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/")
async def creer_utilisateur(
    data: CreerUtilisateur,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Crée un nouvel utilisateur (admin seulement)."""
    # Vérifier unicité username
    existing = await db.execute(
        select(Utilisateur).where(Utilisateur.username == data.username)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="Ce nom d'utilisateur est déjà pris")

    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Le mot de passe doit faire au moins 8 caractères")

    if data.role not in ("admin", "utilisateur"):
        raise HTTPException(status_code=400, detail="Rôle invalide (admin ou utilisateur)")

    user = Utilisateur(
        username=data.username,
        nom=data.nom,
        email=data.email,
        password_hash=pwd_context.hash(data.password),
        role=RoleUtilisateur(data.role),
        actif=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "nom": user.nom,
        "role": user.role.value,
        "message": "Utilisateur créé",
    }


@router.patch("/{user_id}")
async def modifier_utilisateur(
    user_id: int,
    data: ModifierUtilisateur,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Modifie un utilisateur (admin seulement)."""
    result = await db.execute(
        select(Utilisateur).where(Utilisateur.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    # Empêcher un admin de se désactiver lui-même
    if user.id == admin["user_id"] and data.actif is False:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas désactiver votre propre compte")

    if user.id == admin["user_id"] and data.role and data.role != "admin":
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas retirer votre propre rôle admin")

    if data.nom is not None:
        user.nom = data.nom
    if data.email is not None:
        user.email = data.email
    if data.role is not None:
        if data.role not in ("admin", "utilisateur"):
            raise HTTPException(status_code=400, detail="Rôle invalide")
        user.role = RoleUtilisateur(data.role)
    if data.actif is not None:
        user.actif = data.actif
    if data.nouveau_mot_de_passe:
        if len(data.nouveau_mot_de_passe) < 8:
            raise HTTPException(status_code=400, detail="Le mot de passe doit faire au moins 8 caractères")
        user.password_hash = pwd_context.hash(data.nouveau_mot_de_passe)

    await db.commit()
    return {"message": "Utilisateur mis à jour"}


@router.delete("/{user_id}")
async def supprimer_utilisateur(
    user_id: int,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Supprime un utilisateur (admin seulement)."""
    if user_id == admin["user_id"]:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte")

    result = await db.execute(
        select(Utilisateur).where(Utilisateur.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    await db.delete(user)
    await db.commit()
    return {"message": "Utilisateur supprimé"}


# ============================================================
#  GESTION DOMAINES (admin only)
# ============================================================

import re as _re

# Regex stricte pour les noms de domaine (RFC 1035)
_DOMAIN_RE = _re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)(\.[a-z0-9-]{1,63})*\.[a-z]{2,}$")


def _verifier_dns(domaine: str, valeur_attendue: str) -> dict:
    """Vérifie les enregistrements DNS d'un domaine."""
    result = {
        "domaine": domaine,
        "valeur_attendue": valeur_attendue,
        "valeur_trouvee": None,
        "valide": False,
        "type_enregistrement": None,
        "erreur": None,
    }

    # Validation stricte du domaine avant toute opération réseau/subprocess
    if not _DOMAIN_RE.match(domaine):
        result["erreur"] = "Nom de domaine invalide"
        return result

    try:
        # Vérifier les enregistrements A
        try:
            ips = socket.getaddrinfo(domaine, None, socket.AF_INET)
            adresses = list(set(addr[4][0] for addr in ips))
            result["valeur_trouvee"] = ", ".join(adresses)
            result["type_enregistrement"] = "A"

            if valeur_attendue and valeur_attendue in adresses:
                result["valide"] = True
            elif not valeur_attendue and adresses:
                result["valide"] = True
        except socket.gaierror:
            pass

        # Si pas de A record, tenter CNAME via getfqdn
        if not result["valeur_trouvee"]:
            try:
                import subprocess
                dig = subprocess.run(
                    ["dig", "+short", "CNAME", domaine],
                    capture_output=True, text=True, timeout=5
                )
                cname = dig.stdout.strip()
                if cname:
                    result["valeur_trouvee"] = cname
                    result["type_enregistrement"] = "CNAME"
                    if valeur_attendue and valeur_attendue.rstrip(".") in cname.rstrip("."):
                        result["valide"] = True
            except Exception:
                pass

        if not result["valeur_trouvee"]:
            result["erreur"] = "Aucun enregistrement DNS trouvé pour ce domaine"

    except Exception as e:
        logger.error(f"Erreur DNS pour {domaine}: {e}")
        result["erreur"] = "Erreur lors de la vérification DNS"

    return result


@router.get("/domaines")
async def lister_domaines(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Liste tous les domaines configurés."""
    result = await db.execute(
        select(Domaine).order_by(Domaine.created_at.desc())
    )
    domaines = result.scalars().all()
    return [
        {
            "id": d.id,
            "domaine": d.domaine,
            "type": d.type,
            "ssl_actif": d.ssl_actif,
            "statut": d.statut.value,
            "dns_valeur_attendue": d.dns_valeur_attendue,
            "dns_valeur_actuelle": d.dns_valeur_actuelle,
            "derniere_verif": d.derniere_verif.isoformat() if d.derniere_verif else None,
            "notes": d.notes,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in domaines
    ]


@router.post("/domaines")
async def ajouter_domaine(
    data: CreerDomaine,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ajoute un nouveau domaine."""
    # Nettoyer le domaine
    domaine_clean = data.domaine.strip().lower()
    domaine_clean = domaine_clean.replace("https://", "").replace("http://", "").rstrip("/")

    # Valider le format du domaine
    if not _DOMAIN_RE.match(domaine_clean):
        raise HTTPException(status_code=400, detail="Nom de domaine invalide")

    # Vérifier unicité
    existing = await db.execute(
        select(Domaine).where(Domaine.domaine == domaine_clean)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail=f"Le domaine '{domaine_clean}' est déjà configuré")

    dom = Domaine(
        domaine=domaine_clean,
        type=data.type,
        dns_valeur_attendue=data.dns_valeur_attendue,
        notes=data.notes,
        statut=StatutDomaine.en_attente,
    )
    db.add(dom)
    await db.commit()
    await db.refresh(dom)

    return {
        "id": dom.id,
        "domaine": dom.domaine,
        "statut": dom.statut.value,
        "message": "Domaine ajouté — lancez une vérification DNS",
    }


@router.post("/domaines/{domaine_id}/verifier")
async def verifier_domaine(
    domaine_id: int,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lance une vérification DNS pour un domaine."""
    result = await db.execute(
        select(Domaine).where(Domaine.id == domaine_id)
    )
    dom = result.scalars().first()
    if not dom:
        raise HTTPException(status_code=404, detail="Domaine introuvable")

    dns_result = _verifier_dns(dom.domaine, dom.dns_valeur_attendue or "")

    dom.dns_valeur_actuelle = dns_result.get("valeur_trouvee")
    dom.derniere_verif = datetime.now(timezone.utc)
    dom.statut = StatutDomaine.verifie if dns_result["valide"] else StatutDomaine.erreur

    await db.commit()

    return {
        "id": dom.id,
        "domaine": dom.domaine,
        "statut": dom.statut.value,
        "dns": dns_result,
    }


@router.patch("/domaines/{domaine_id}")
async def modifier_domaine(
    domaine_id: int,
    data: ModifierDomaine,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Modifie un domaine."""
    result = await db.execute(
        select(Domaine).where(Domaine.id == domaine_id)
    )
    dom = result.scalars().first()
    if not dom:
        raise HTTPException(status_code=404, detail="Domaine introuvable")

    if data.type is not None:
        dom.type = data.type
    if data.ssl_actif is not None:
        dom.ssl_actif = data.ssl_actif
    if data.dns_valeur_attendue is not None:
        dom.dns_valeur_attendue = data.dns_valeur_attendue
    if data.notes is not None:
        dom.notes = data.notes

    await db.commit()
    return {"message": "Domaine mis à jour"}


@router.delete("/domaines/{domaine_id}")
async def supprimer_domaine(
    domaine_id: int,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Supprime un domaine."""
    result = await db.execute(
        select(Domaine).where(Domaine.id == domaine_id)
    )
    dom = result.scalars().first()
    if not dom:
        raise HTTPException(status_code=404, detail="Domaine introuvable")

    await db.delete(dom)
    await db.commit()
    return {"message": "Domaine supprimé"}
