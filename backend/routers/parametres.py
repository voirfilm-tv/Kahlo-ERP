"""
KAHLO CAFÉ — Router Paramètres
Lecture / écriture de la configuration dans un fichier .env persistant.
Les clés sensibles (API, mots de passe) ne sont jamais retournées en clair côté frontend
sauf les champs non-secrets (emails, noms, délais).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import os
import re
import logging
from pathlib import Path
from datetime import datetime
from dotenv import dotenv_values, set_key

logger = logging.getLogger(__name__)

from database import get_db
from routers.auth import verifier_token, require_admin, pwd_context

router = APIRouter()

ENV_PATH = Path(os.getenv("ENV_FILE_PATH", "/app/.env")).resolve()
# Sécurité : vérifier que le chemin reste dans /app/
if not str(ENV_PATH).startswith("/app/"):
    logger.error("ENV_FILE_PATH pointe hors de /app/ : %s — fallback sur /app/.env", ENV_PATH)
    ENV_PATH = Path("/app/.env")


# ============================================================
#  HELPERS
# ============================================================

def _lire_env() -> dict:
    if not ENV_PATH.exists():
        return {}
    return dotenv_values(ENV_PATH)

def _ecrire_cle(key: str, value: str):
    """Écrit ou met à jour une variable dans le .env"""
    ENV_PATH.touch(exist_ok=True)
    set_key(str(ENV_PATH), key, value)

def _masquer(val: Optional[str]) -> str:
    """Retourne '••••••••' si la valeur est renseignée, chaîne vide sinon"""
    if not val:
        return ""
    return "••••••••"

def _est_vide_ou_masque(val: Optional[str]) -> bool:
    """Vrai si la valeur n'a pas changé (masquée par le frontend)"""
    return not val or val == "••••••••"


# ============================================================
#  SCHEMAS
# ============================================================

class ParametresGeneral(BaseModel):
    nom: Optional[str] = None
    ville: Optional[str] = None
    email: Optional[str] = None
    tel: Optional[str] = None
    objectif_ca: Optional[str] = None
    devise: Optional[str] = None
    timezone: Optional[str] = None
    format_date: Optional[str] = None

class ParametresSumUp(BaseModel):
    api_key: Optional[str] = None
    merchant_email: Optional[str] = None
    webhook_secret: Optional[str] = None
    mode: Optional[str] = None

class ParametresBrevo(BaseModel):
    api_key: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    tpl_anniversaire: Optional[str] = None
    tpl_confirmation: Optional[str] = None
    tpl_prete: Optional[str] = None
    tpl_relance: Optional[str] = None
    liste_clients: Optional[str] = None
    liste_vip: Optional[str] = None
    liste_relance: Optional[str] = None
    envoi_anniversaire: Optional[bool] = None
    envoi_relance: Optional[bool] = None
    envoi_confirmation: Optional[bool] = None
    envoi_prete: Optional[bool] = None

class ParametresCalendrier(BaseModel):
    caldav_user: Optional[str] = None
    caldav_password: Optional[str] = None
    caldav_interval: Optional[str] = None
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    sync_marches: Optional[bool] = None
    sync_commandes: Optional[bool] = None
    sync_fournisseurs: Optional[bool] = None

class ParametresIA(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None
    analyse_marche: Optional[bool] = None
    suggestion_stock: Optional[bool] = None
    fiche_produit: Optional[bool] = None
    analyse_dashboard: Optional[bool] = None

class ParametresStock(BaseModel):
    seuil_alerte: Optional[str] = None
    alerte_dlc_jours: Optional[str] = None
    lot_vieux_jours: Optional[str] = None
    fifo_auto: Optional[bool] = None
    alerte_rupture: Optional[bool] = None
    bon_commande_auto: Optional[bool] = None
    qte_min_reappro: Optional[str] = None

class ParametresCRM(BaseModel):
    tampons_max: Optional[str] = None
    recompense_label: Optional[str] = None
    inactivite_jours: Optional[str] = None
    anniv_jours_avant: Optional[str] = None
    vip_ca_seuil: Optional[str] = None
    vip_auto: Optional[bool] = None

class ParametresSecurite(BaseModel):
    username: Optional[str] = None
    new_password: Optional[str] = None
    secret_key: Optional[str] = None
    session_longue: Optional[bool] = None

class ParametresSauvegarde(BaseModel):
    backup_auto: Optional[bool] = None
    backup_freq: Optional[str] = None
    backup_retention: Optional[str] = None
    backup_path: Optional[str] = None

class TousParametres(BaseModel):
    general:    Optional[ParametresGeneral] = None
    sumup:      Optional[ParametresSumUp] = None
    brevo:      Optional[ParametresBrevo] = None
    calendrier: Optional[ParametresCalendrier] = None
    ia:         Optional[ParametresIA] = None
    stock:      Optional[ParametresStock] = None
    crm:        Optional[ParametresCRM] = None
    securite:   Optional[ParametresSecurite] = None
    sauvegarde: Optional[ParametresSauvegarde] = None


# ============================================================
#  LECTURE
# ============================================================

@router.get("/")
async def get_parametres(token: str = Depends(verifier_token)):
    """
    Retourne la configuration courante.
    Les clés secrètes sont masquées — on retourne juste si elles sont configurées ou non.
    """
    env = _lire_env()

    return {
        "general": {
            "nom":         env.get("BOUTIQUE_NOM", "Kahlo Café"),
            "ville":       env.get("BOUTIQUE_VILLE", "Lyon, France"),
            "email":       env.get("BOUTIQUE_EMAIL", ""),
            "tel":         env.get("BOUTIQUE_TEL", ""),
            "objectif_ca": env.get("OBJECTIF_CA_MENSUEL", "3500"),
            "devise":      env.get("DEVISE", "EUR"),
            "timezone":    env.get("TIMEZONE", "Europe/Paris"),
            "format_date": env.get("FORMAT_DATE", "dd/MM/yyyy"),
        },
        "sumup": {
            "api_key":        _masquer(env.get("SUMUP_API_KEY")),
            "merchant_email": env.get("SUMUP_MERCHANT_EMAIL", ""),
            "webhook_secret": _masquer(env.get("SUMUP_WEBHOOK_SECRET")),
            "mode":           env.get("SUMUP_MODE", "sandbox"),
            "configure":      bool(env.get("SUMUP_API_KEY")),
        },
        "brevo": {
            "api_key":          _masquer(env.get("BREVO_API_KEY")),
            "from_email":       env.get("BREVO_FROM_EMAIL", ""),
            "from_name":        env.get("BREVO_FROM_NAME", "Kahlo Café"),
            "tpl_anniversaire": env.get("BREVO_TPL_ANNIVERSAIRE", ""),
            "tpl_confirmation": env.get("BREVO_TPL_CONFIRMATION", ""),
            "tpl_prete":        env.get("BREVO_TPL_PRETE", ""),
            "tpl_relance":      env.get("BREVO_TPL_RELANCE", ""),
            "liste_clients":    env.get("BREVO_LIST_CLIENTS", ""),
            "liste_vip":        env.get("BREVO_LIST_VIP", ""),
            "liste_relance":    env.get("BREVO_LIST_RELANCE", ""),
            "envoi_anniversaire":  env.get("BREVO_ENVOI_ANNIVERSAIRE", "true") == "true",
            "envoi_relance":       env.get("BREVO_ENVOI_RELANCE", "true") == "true",
            "envoi_confirmation":  env.get("BREVO_ENVOI_CONFIRMATION", "true") == "true",
            "envoi_prete":         env.get("BREVO_ENVOI_PRETE", "true") == "true",
            "configure":       bool(env.get("BREVO_API_KEY")),
        },
        "calendrier": {
            "caldav_user":         env.get("CALDAV_USER", "kahlo"),
            "caldav_password":     _masquer(env.get("CALDAV_PASSWORD")),
            "caldav_interval":     env.get("CALDAV_INTERVAL", "30"),
            "google_client_id":    env.get("GOOGLE_CLIENT_ID", ""),
            "google_client_secret": _masquer(env.get("GOOGLE_CLIENT_SECRET")),
            "sync_marches":     env.get("SYNC_MARCHES", "true") == "true",
            "sync_commandes":   env.get("SYNC_COMMANDES", "true") == "true",
            "sync_fournisseurs": env.get("SYNC_FOURNISSEURS", "false") == "true",
        },
        "ia": {
            "api_key":         _masquer(env.get("GEMINI_API_KEY")),
            "model":           env.get("GEMINI_MODEL", "gemini-1.5-flash"),
            "analyse_marche":  env.get("IA_ANALYSE_MARCHE", "true") == "true",
            "suggestion_stock": env.get("IA_SUGGESTION_STOCK", "true") == "true",
            "fiche_produit":   env.get("IA_FICHE_PRODUIT", "true") == "true",
            "analyse_dashboard": env.get("IA_ANALYSE_DASHBOARD", "false") == "true",
            "configure":       bool(env.get("GEMINI_API_KEY")),
        },
        "stock": {
            "seuil_alerte":      env.get("STOCK_SEUIL_ALERTE", "3"),
            "alerte_dlc_jours":  env.get("STOCK_ALERTE_DLC_JOURS", "30"),
            "lot_vieux_jours":   env.get("STOCK_LOT_VIEUX_JOURS", "90"),
            "fifo_auto":         env.get("STOCK_FIFO_AUTO", "true") == "true",
            "alerte_rupture":    env.get("STOCK_ALERTE_RUPTURE", "true") == "true",
            "bon_commande_auto": env.get("STOCK_BON_COMMANDE_AUTO", "false") == "true",
            "qte_min_reappro":   env.get("STOCK_QTE_MIN_REAPPRO", "5"),
        },
        "crm": {
            "tampons_max":       env.get("CRM_TAMPONS_MAX", "10"),
            "recompense_label":  env.get("CRM_RECOMPENSE_LABEL", "1 café offert (250g au choix)"),
            "inactivite_jours":  env.get("CRM_INACTIVITE_JOURS", "45"),
            "anniv_jours_avant": env.get("CRM_ANNIV_JOURS_AVANT", "14"),
            "vip_ca_seuil":      env.get("CRM_VIP_CA_SEUIL", "200"),
            "vip_auto":          env.get("CRM_VIP_AUTO", "true") == "true",
        },
        "securite": {
            "username":       env.get("APP_USERNAME", "kahlo"),
            "session_longue": env.get("SESSION_LONGUE", "true") == "true",
        },
        "sauvegarde": {
            "backup_auto":      env.get("BACKUP_AUTO", "true") == "true",
            "backup_freq":      env.get("BACKUP_FREQ", "daily"),
            "backup_retention": env.get("BACKUP_RETENTION_JOURS", "30"),
            "backup_path":      env.get("BACKUP_PATH", "/backups/kahlo"),
        },
    }


# ============================================================
#  ÉCRITURE
# ============================================================

@router.post("/")
async def sauvegarder_parametres(
    data: TousParametres,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Sauvegarde les paramètres dans le .env.
    Les champs masqués (••••••••) sont ignorés — on ne réécrit pas les secrets.
    """
    def w(key, val):
        """Écrit la clé seulement si la valeur est non-vide et non-masquée"""
        if val is not None and not _est_vide_ou_masque(str(val)):
            _ecrire_cle(key, str(val))

    def wb(key, val):
        """Écrit un booléen"""
        if val is not None:
            _ecrire_cle(key, "true" if val else "false")

    if data.general:
        g = data.general
        w("BOUTIQUE_NOM", g.nom)
        w("BOUTIQUE_VILLE", g.ville)
        w("BOUTIQUE_EMAIL", g.email)
        w("BOUTIQUE_TEL", g.tel)
        w("OBJECTIF_CA_MENSUEL", g.objectif_ca)
        w("DEVISE", g.devise)
        w("TIMEZONE", g.timezone)
        w("FORMAT_DATE", g.format_date)

    if data.sumup:
        s = data.sumup
        w("SUMUP_API_KEY", s.api_key)
        w("SUMUP_MERCHANT_EMAIL", s.merchant_email)
        w("SUMUP_WEBHOOK_SECRET", s.webhook_secret)
        w("SUMUP_MODE", s.mode)

    if data.brevo:
        b = data.brevo
        w("BREVO_API_KEY", b.api_key)
        w("BREVO_FROM_EMAIL", b.from_email)
        w("BREVO_FROM_NAME", b.from_name)
        w("BREVO_TPL_ANNIVERSAIRE", b.tpl_anniversaire)
        w("BREVO_TPL_CONFIRMATION", b.tpl_confirmation)
        w("BREVO_TPL_PRETE", b.tpl_prete)
        w("BREVO_TPL_RELANCE", b.tpl_relance)
        w("BREVO_LIST_CLIENTS", b.liste_clients)
        w("BREVO_LIST_VIP", b.liste_vip)
        w("BREVO_LIST_RELANCE", b.liste_relance)
        wb("BREVO_ENVOI_ANNIVERSAIRE", b.envoi_anniversaire)
        wb("BREVO_ENVOI_RELANCE", b.envoi_relance)
        wb("BREVO_ENVOI_CONFIRMATION", b.envoi_confirmation)
        wb("BREVO_ENVOI_PRETE", b.envoi_prete)

    if data.calendrier:
        c = data.calendrier
        w("CALDAV_USER", c.caldav_user)
        w("CALDAV_PASSWORD", c.caldav_password)
        w("CALDAV_INTERVAL", c.caldav_interval)
        w("GOOGLE_CLIENT_ID", c.google_client_id)
        w("GOOGLE_CLIENT_SECRET", c.google_client_secret)
        wb("SYNC_MARCHES", c.sync_marches)
        wb("SYNC_COMMANDES", c.sync_commandes)
        wb("SYNC_FOURNISSEURS", c.sync_fournisseurs)

    if data.ia:
        i = data.ia
        w("GEMINI_API_KEY", i.api_key)
        w("GEMINI_MODEL", i.model)
        wb("IA_ANALYSE_MARCHE", i.analyse_marche)
        wb("IA_SUGGESTION_STOCK", i.suggestion_stock)
        wb("IA_FICHE_PRODUIT", i.fiche_produit)
        wb("IA_ANALYSE_DASHBOARD", i.analyse_dashboard)

    if data.stock:
        s = data.stock
        w("STOCK_SEUIL_ALERTE", s.seuil_alerte)
        w("STOCK_ALERTE_DLC_JOURS", s.alerte_dlc_jours)
        w("STOCK_LOT_VIEUX_JOURS", s.lot_vieux_jours)
        wb("STOCK_FIFO_AUTO", s.fifo_auto)
        wb("STOCK_ALERTE_RUPTURE", s.alerte_rupture)
        wb("STOCK_BON_COMMANDE_AUTO", s.bon_commande_auto)
        w("STOCK_QTE_MIN_REAPPRO", s.qte_min_reappro)

    if data.crm:
        c = data.crm
        w("CRM_TAMPONS_MAX", c.tampons_max)
        w("CRM_RECOMPENSE_LABEL", c.recompense_label)
        w("CRM_INACTIVITE_JOURS", c.inactivite_jours)
        w("CRM_ANNIV_JOURS_AVANT", c.anniv_jours_avant)
        w("CRM_VIP_CA_SEUIL", c.vip_ca_seuil)
        wb("CRM_VIP_AUTO", c.vip_auto)

    if data.securite:
        s = data.securite
        w("APP_USERNAME", s.username)
        if s.new_password and not _est_vide_ou_masque(s.new_password):
            if len(s.new_password) < 8:
                raise HTTPException(status_code=400, detail="Le mot de passe doit faire au moins 8 caractères")
            # 1. Mettre à jour le mot de passe en DB immédiatement
            from models import Utilisateur
            admin_username = os.getenv("APP_USERNAME", "kahlo")
            result_user = await db.execute(
                select(Utilisateur).where(Utilisateur.username == admin_username)
            )
            admin_user = result_user.scalars().first()
            if admin_user:
                admin_user.password_hash = pwd_context.hash(s.new_password)
                await db.commit()
            # 2. Persister dans .env pour les futurs redémarrages
            _ecrire_cle("APP_DEFAULT_PASSWORD", s.new_password)
        if s.secret_key and not _est_vide_ou_masque(s.secret_key):
            w("SECRET_KEY", s.secret_key)
        wb("SESSION_LONGUE", s.session_longue)

    if data.sauvegarde:
        sv = data.sauvegarde
        wb("BACKUP_AUTO", sv.backup_auto)
        w("BACKUP_FREQ", sv.backup_freq)
        w("BACKUP_RETENTION_JOURS", sv.backup_retention)
        w("BACKUP_PATH", sv.backup_path)

    return {"message": "Paramètres sauvegardés"}


# ============================================================
#  TESTS DE CONNEXION
# ============================================================

@router.post("/tester-sumup")
async def tester_sumup(token: str = Depends(verifier_token)):
    from services.sumup import verifier_connexion
    ok = await verifier_connexion()
    if ok:
        return {"ok": True, "message": "Connexion SumUp opérationnelle"}
    raise HTTPException(status_code=502, detail="Impossible de joindre l'API SumUp — vérifiez votre clé")


@router.post("/tester-brevo")
async def tester_brevo(token: str = Depends(verifier_token)):
    import httpx
    api_key = os.getenv("BREVO_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="Clé Brevo non configurée")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.brevo.com/v3/account",
                headers={"api-key": api_key},
                timeout=5
            )
            if resp.status_code == 200:
                info = resp.json()
                return {"ok": True, "message": f"Connecté au compte Brevo : {info.get('email', '')}"}
            raise HTTPException(status_code=502, detail="Clé Brevo invalide")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Erreur lors du test Brevo")
        raise HTTPException(status_code=502, detail="Impossible de joindre Brevo — vérifiez votre configuration")


@router.post("/tester-gemini")
async def tester_gemini(token: str = Depends(verifier_token)):
    import httpx
    api_key = os.getenv("GEMINI_API_KEY", "")
    model   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    if not api_key:
        raise HTTPException(status_code=400, detail="Clé Gemini non configurée")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                json={"contents": [{"parts": [{"text": "Réponds juste 'OK' en français."}]}]},
                timeout=10
            )
            if resp.status_code == 200:
                return {"ok": True, "message": f"Gemini {model} répond correctement"}
            raise HTTPException(status_code=502, detail="Clé Gemini invalide ou quota dépassé")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Erreur lors du test Gemini")
        raise HTTPException(status_code=502, detail="Impossible de joindre Gemini — vérifiez votre configuration")


# ============================================================
#  SAUVEGARDE MANUELLE
# ============================================================

@router.post("/sauvegarde")
async def sauvegarde_manuelle(admin: dict = Depends(require_admin)):
    """Lance un dump PostgreSQL immédiat"""
    import subprocess
    backup_path = os.getenv("BACKUP_PATH", "/backups/kahlo")
    os.makedirs(backup_path, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    fichier = f"{backup_path}/kahlo-{timestamp}.sql.gz"
    db_url = os.getenv("DATABASE_URL", "")

    # Extraire les infos de connexion depuis la DATABASE_URL
    # Formats supportés : postgresql://... ou postgresql+asyncpg://...
    m = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^:/]+):?(\d*)/([^?]+)", db_url)
    if not m:
        raise HTTPException(status_code=500, detail="DATABASE_URL malformée — impossible de sauvegarder")

    user, password, host, port, dbname = m.groups()
    port = port or "5432"

    env_copy = os.environ.copy()
    env_copy["PGPASSWORD"] = password

    result = subprocess.run(
        ["pg_dump", "-h", host, "-p", port, "-U", user, "-d", dbname, "-Fc"],
        capture_output=True, env=env_copy, timeout=120
    )

    if result.returncode != 0:
        logger.error("pg_dump echoue (code %d)", result.returncode)
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde de la base de données")

    with open(fichier, "wb") as f:
        f.write(result.stdout)

    taille_ko = round(len(result.stdout) / 1024, 1)
    return {
        "message": "Sauvegarde effectuée",
        "fichier": fichier,
        "taille_ko": taille_ko,
        "timestamp": timestamp,
    }
