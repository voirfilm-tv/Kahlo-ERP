"""KAHLO CAFÉ — Router Calendrier"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse
from html import escape
import os
import uuid
import plistlib
import logging

from jose import jwt, JWTError

from database import get_db
from models import Evenement, TypeEvenement
from services.calendrier import (
    creer_evenement_caldav, sync_caldav_vers_db,
    creer_evenement_google, sync_google_vers_db
)
from services import caldav_admin
from routers.auth import verifier_token, require_admin, SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
#  CONNEXION DES APPAREILS (CalDAV zéro-config)
#  L'ERP gère le serveur et les identifiants tout seul :
#  l'utilisateur copie l'URL/identifiants ou scanne un QR code.
# ============================================================

def _premier_header(valeur: str | None) -> str:
    """Premier élément d'un header proxy potentiellement séparé par virgules."""
    return (valeur or "").split(",", 1)[0].strip()


def _host_avec_port(host: str, proto: str, port: str | None) -> str:
    if not host or not port:
        return host
    if ":" in host and not host.startswith("["):
        return host
    if host.startswith("[") and "]:" in host:
        return host
    if (proto == "http" and port == "80") or (proto == "https" and port == "443"):
        return host
    return f"{host}:{port}"


def _base_publique(request: Request) -> str:
    """URL de base vue par les appareils : PUBLIC_BASE_URL si configurée,
    sinon l'adresse par laquelle l'utilisateur accède à l'ERP."""
    configuree = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configuree:
        return configuree
    proto = _premier_header(request.headers.get("x-forwarded-proto")) or request.url.scheme
    host = (
        _premier_header(request.headers.get("x-forwarded-host"))
        or _premier_header(request.headers.get("host"))
        or request.url.netloc
    )
    host = _host_avec_port(host, proto, _premier_header(request.headers.get("x-forwarded-port")))
    return f"{proto}://{host}"


def _infos_connexion(request: Request) -> dict:
    user, password = caldav_admin.identifiants_caldav()
    base = _base_publique(request)
    return {
        "url": f"{base}/caldav/{user}/",
        "username": user,
        "password": password,
        "base": base,
    }


def _reponse_mobileconfig(infos: dict) -> Response:
    base = urlparse(infos["base"])
    use_ssl = base.scheme == "https"
    port = base.port or (443 if use_ssl else 80)

    compte = {
        "CalDAVAccountDescription": "Kahlo Café — Calendrier",
        "CalDAVHostName": base.hostname or "",
        "CalDAVPort": port,
        "CalDAVUseSSL": use_ssl,
        "CalDAVUsername": infos["username"],
        "CalDAVPassword": infos["password"],
        "CalDAVPrincipalURL": f"/caldav/{infos['username']}/",
        "PayloadDescription": "Compte calendrier Kahlo Café (CalDAV)",
        "PayloadDisplayName": "Calendrier Kahlo Café",
        "PayloadIdentifier": "fr.kahlocafe.erp.caldav.account",
        "PayloadType": "com.apple.caldav.account",
        "PayloadUUID": str(uuid.uuid4()),
        "PayloadVersion": 1,
    }
    profil = {
        "PayloadContent": [compte],
        "PayloadDescription": "Ajoute le calendrier Kahlo Café à cet appareil",
        "PayloadDisplayName": "Kahlo Café — Calendrier",
        "PayloadIdentifier": "fr.kahlocafe.erp.caldav",
        "PayloadRemovalDisallowed": False,
        "PayloadType": "Configuration",
        "PayloadUUID": str(uuid.uuid4()),
        "PayloadVersion": 1,
    }
    return Response(
        content=plistlib.dumps(profil),
        media_type="application/x-apple-aspen-config",
        headers={
            "Content-Disposition": 'inline; filename="kahlo-calendrier.mobileconfig"',
            "Cache-Control": "no-store",
        },
    )


def _page_aide_apple(infos: dict, token: str) -> HTMLResponse:
    download_url = (
        f"{infos['base']}/api/calendrier/profil-apple?"
        f"{urlencode({'token': token, 'download': '1'})}"
    )
    html = f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Installer le calendrier Kahlo</title>
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #261810;
      color: #f5eee8;
      line-height: 1.55;
    }}
    main {{
      max-width: 720px;
      margin: 0 auto;
      padding: 28px 20px 44px;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 28px;
      line-height: 1.1;
    }}
    .panel {{
      background: rgba(0, 0, 0, 0.22);
      border: 1px solid rgba(193, 138, 74, 0.25);
      border-radius: 10px;
      padding: 16px;
      margin: 16px 0;
    }}
    .field {{
      margin: 10px 0;
    }}
    .label {{
      display: block;
      color: #c18a4a;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    code {{
      display: block;
      overflow-x: auto;
      margin-top: 4px;
      padding: 10px 12px;
      border-radius: 8px;
      background: rgba(0, 0, 0, 0.35);
      color: #fff;
      font-size: 13px;
    }}
    a.button {{
      display: inline-block;
      margin: 10px 0 4px;
      padding: 12px 16px;
      border-radius: 8px;
      background: #c18a4a;
      color: #1a0f0a;
      font-weight: 800;
      text-decoration: none;
    }}
    ol {{
      padding-left: 22px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Calendrier Kahlo</h1>
    <p>Sur iPhone, l'installation automatique peut nécessiter HTTPS. Si Safari ne propose pas l'installation du profil, utilisez la configuration manuelle ci-dessous.</p>

    <div class="panel">
      <a class="button" href="{escape(download_url)}">Télécharger le profil Apple</a>
      <p>Après téléchargement, ouvrez Réglages : le profil téléchargé apparaît généralement en haut de l'écran.</p>
    </div>

    <div class="panel">
      <h2>Configuration manuelle</h2>
      <p>Réglages → Apps → Calendrier → Comptes → Autre → Compte CalDAV.</p>
      <div class="field">
        <span class="label">Serveur</span>
        <code>{escape(infos["url"])}</code>
      </div>
      <div class="field">
        <span class="label">Identifiant</span>
        <code>{escape(infos["username"])}</code>
      </div>
      <div class="field">
        <span class="label">Mot de passe</span>
        <code>{escape(infos["password"])}</code>
      </div>
    </div>

    <div class="panel">
      <h2>En HTTP local</h2>
      <p>L'adresse locale fonctionne pour la configuration manuelle. Pour une installation automatique plus fiable, exposez l'ERP en HTTPS avec un domaine, puis renseignez cette adresse dans l'URL publique de l'ERP.</p>
    </div>
  </main>
</body>
</html>"""
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


def _page_token_invalide() -> HTMLResponse:
    return HTMLResponse(
        status_code=403,
        content="""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lien expiré</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:28px;line-height:1.5">
<h1>Lien expiré ou invalide</h1>
<p>Retournez dans l'ERP, ouvrez Paramètres → Calendrier, puis générez un nouveau QR code Apple.</p>
</body></html>""",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/connexion")
async def connexion_appareils(request: Request, admin: dict = Depends(require_admin)):
    """Tout ce qu'il faut pour connecter un appareil (admin uniquement —
    le mot de passe est retourné en clair car il est nécessaire à la
    configuration de l'appareil ; il est géré/généré par l'ERP)."""
    infos = _infos_connexion(request)
    return {
        "url": infos["url"],
        "username": infos["username"],
        "password": infos["password"],
        "gestion_auto": caldav_admin.gestion_auto_possible(),
        "https": infos["base"].startswith("https://"),
        "frequence_secondes": int(os.getenv("CALDAV_INTERVAL_SECONDS", "0") or 0)
        or int(os.getenv("CALDAV_INTERVAL", "5") or 5) * 60,
    }


@router.post("/connexion/regenerer")
async def regenerer_mot_de_passe(request: Request, admin: dict = Depends(require_admin)):
    """Nouveau mot de passe CalDAV (les appareils déjà connectés devront
    être reconfigurés)."""
    try:
        nouveau = caldav_admin.regenerer_mot_de_passe()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    infos = _infos_connexion(request)
    return {"password": nouveau, "url": infos["url"], "username": infos["username"]}


@router.post("/connexion/verifier")
async def verifier_connexion_caldav(request: Request, admin: dict = Depends(require_admin)):
    """Diagnostic CalDAV réel : volume htpasswd, hash affiché, auth Radicale
    interne et URL publique utilisée par les appareils."""
    infos = _infos_connexion(request)
    user = infos["username"]
    password = infos["password"]
    checks = []

    volume = caldav_admin.etat_volume_htpasswd()
    if volume["ok"]:
        checks.append({
            "code": "volume_htpasswd",
            "ok": True,
            "niveau": "ok",
            "message": f"Volume htpasswd accessible en écriture ({volume['path']})",
        })
    else:
        checks.append({
            "code": "volume_htpasswd",
            "ok": False,
            "niveau": "erreur",
            "message": (
                "Volume htpasswd absent ou non inscriptible : "
                f"{volume['path']} — vérifiez le volume Docker caldav_data côté backend"
            ),
        })

    htpasswd = caldav_admin.verifier_mot_de_passe_htpasswd(user, password)
    checks.append({
        "code": "htpasswd_password",
        "ok": htpasswd["ok"],
        "niveau": "ok" if htpasswd["ok"] else "erreur",
        "message": htpasswd["message"],
    })

    url_interne = caldav_admin.url_interne_caldav(user)
    interne = await caldav_admin.tester_auth_caldav(url_interne, user, password)
    checks.append({
        "code": "radicale_interne",
        "ok": interne["ok"],
        "niveau": "ok" if interne["ok"] else "erreur",
        "message": interne["message"],
        "url": url_interne,
        "status_code": interne.get("status_code"),
    })

    externe = await caldav_admin.tester_auth_caldav(infos["url"], user, password, timeout=4)
    checks.append({
        "code": "url_externe",
        "ok": externe["ok"],
        "niveau": "ok" if externe["ok"] else "erreur",
        "message": (
            "URL externe accessible avec les identifiants affichés"
            if externe["ok"]
            else f"URL externe inaccessible ou mal proxifiée : {externe['message']}"
        ),
        "url": infos["url"],
        "status_code": externe.get("status_code"),
    })

    if not infos["base"].startswith("https://"):
        checks.append({
            "code": "apple_https",
            "ok": True,
            "niveau": "attention",
            "message": "Profil Apple généré, mais HTTPS est recommandé pour une installation automatique fiable sur iPhone",
        })

    erreurs = [c for c in checks if c["niveau"] == "erreur"]
    avertissements = [c for c in checks if c["niveau"] == "attention"]
    if erreurs:
        message = erreurs[0]["message"]
        ok = False
        niveau = "erreur"
    elif avertissements:
        message = "Connexion CalDAV OK. " + avertissements[0]["message"]
        ok = True
        niveau = "attention"
    else:
        message = "Connexion CalDAV OK : Radicale accepte les identifiants affichés et l'URL publique répond"
        ok = True
        niveau = "ok"

    return {
        "ok": ok,
        "niveau": niveau,
        "message": message,
        "url": infos["url"],
        "username": user,
        "checks": checks,
    }


@router.post("/connexion/lien-apple")
async def generer_lien_apple(request: Request, admin: dict = Depends(require_admin)):
    """Lien signé temporaire (15 min) vers le profil Apple .mobileconfig.
    Encodé en QR côté interface : scanner → le compte calendrier s'installe
    tout seul sur iPhone/iPad/Mac."""
    token = jwt.encode(
        {
            "typ": "caldav-profile",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
        SECRET_KEY, algorithm=ALGORITHM,
    )
    base = _base_publique(request)
    profil_url = f"{base}/api/calendrier/profil-apple?token={token}"
    return {
        "url": profil_url,
        "download_url": f"{profil_url}&download=1",
        "expire_minutes": 15,
    }


@router.get("/profil-apple")
async def profil_apple(
    request: Request,
    token: str = Query(...),
    download: bool = Query(False),
):
    """Profil de configuration Apple (.mobileconfig) avec le compte CalDAV
    pré-rempli. Accessible sans session (le téléphone qui scanne le QR n'en
    a pas) mais protégé par un jeton signé à durée courte."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("typ") != "caldav-profile":
            raise JWTError("mauvais type de jeton")
    except JWTError:
        if "text/html" in request.headers.get("accept", ""):
            return _page_token_invalide()
        raise HTTPException(status_code=403, detail="Lien expiré ou invalide — régénérez le QR code")

    infos = _infos_connexion(request)
    if download or infos["base"].startswith("https://"):
        return _reponse_mobileconfig(infos)
    return _page_aide_apple(infos, token)


class EvenementCreate(BaseModel):
    type: TypeEvenement
    titre: str
    date_debut: datetime
    date_fin: Optional[datetime] = None
    all_day: bool = True
    notes: Optional[str] = None
    marche_id: Optional[int] = None
    commande_id: Optional[int] = None
    fournisseur_id: Optional[int] = None


@router.get("/")
async def get_evenements(
    mois: Optional[int] = None,
    annee: Optional[int] = None,
    debut: Optional[datetime] = None,
    fin: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token)
):
    """Liste les événements. Filtrable par mois/annee OU par plage debut/fin."""
    query = select(Evenement).order_by(Evenement.date_debut)
    if mois and annee:
        from sqlalchemy import extract
        query = query.where(
            extract("month", Evenement.date_debut) == mois,
            extract("year", Evenement.date_debut) == annee,
        )
    else:
        if debut:
            query = query.where(Evenement.date_debut >= debut)
        if fin:
            # Inclure toute la journée de fin
            query = query.where(Evenement.date_debut < fin + timedelta(days=1))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", status_code=201)
async def creer_evenement(data: EvenementCreate, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    ev = Evenement(**data.model_dump())
    db.add(ev)
    await db.flush()

    # Sync CalDAV automatique
    uid = await creer_evenement_caldav({
        "titre": ev.titre,
        "date_debut": ev.date_debut,
        "date_fin": ev.date_fin or ev.date_debut,
        "notes": ev.notes,
    })
    if uid:
        ev.caldav_uid = uid

    await db.commit()
    await db.refresh(ev)
    return ev


@router.delete("/{eid}")
async def supprimer_evenement(eid: int, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    from services.calendrier import supprimer_evenement_caldav
    result = await db.execute(select(Evenement).where(Evenement.id == eid))
    ev = result.scalar_one_or_none()
    if not ev:
        raise HTTPException(404, "Événement introuvable")

    if ev.caldav_uid:
        await supprimer_evenement_caldav(ev.caldav_uid)

    await db.delete(ev)
    await db.commit()
    return {"ok": True}


@router.post("/sync/caldav")
async def sync_caldav(db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    """Force une sync bidirectionnelle CalDAV"""
    nouveaux = await sync_caldav_vers_db(db)
    return {"importes": len(nouveaux), "evenements": nouveaux}


@router.post("/sync/google")
async def sync_google(credentials: dict, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    """Force une sync Google Calendar (nécessite token OAuth)"""
    nouveaux = await sync_google_vers_db(credentials, db)
    return {"importes": len(nouveaux)}
