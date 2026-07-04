"""
KAHLO CAFÉ — Service Calendrier
Sync bidirectionnelle CalDAV (Apple) + Google Calendar API
"""

import caldav
import vobject
import os
import asyncio
from datetime import datetime, timezone, date, time as dt_time
from functools import partial
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import logging

logger = logging.getLogger(__name__)


def _caldav_config() -> tuple[str, str, str]:
    """URL/identifiants lus à chaque appel : suivent la config à chaud
    (mot de passe auto-généré ou régénéré via caldav_admin)."""
    return (
        os.getenv("CALDAV_BASE_URL", "http://caldav:5232"),
        os.getenv("CALDAV_USER", "kahlo"),
        os.getenv("CALDAV_PASSWORD", "changeme"),
    )


async def _run_sync(func, *args, **kwargs):
    """Exécute une fonction synchrone (CalDAV/Google) dans un thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


# ============================================================
#  CALDAV (Apple Calendar — bidirectionnel)
# ============================================================

def get_caldav_client():
    url, user, password = _caldav_config()
    return caldav.DAVClient(
        url=f"{url}/{user}/",
        username=user,
        password=password,
    )


# ── Détection de changement ultra-légère (ctag) ────────────
# Permet une fréquence de sync très courte (jusqu'à 1 s) sans coût :
# une seule petite requête PROPFIND locale ; la vraie synchronisation
# ne se déclenche que si l'empreinte des calendriers a changé.

_PROPFIND_CTAG = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<propfind xmlns="DAV:" xmlns:CS="http://calendarserver.org/ns/">'
    "<prop><CS:getctag/></prop></propfind>"
)


def _empreinte_caldav_sync() -> str | None:
    """Empreinte (concat des ctags) des collections de l'utilisateur.
    None si Radicale est injoignable."""
    import httpx
    import re
    url, user, password = _caldav_config()
    try:
        resp = httpx.request(
            "PROPFIND",
            f"{url}/{user}/",
            content=_PROPFIND_CTAG,
            headers={"Depth": "1", "Content-Type": "application/xml"},
            auth=(user, password),
            timeout=3,
        )
        if resp.status_code >= 400:
            return None
        ctags = re.findall(r"getctag[^>]*>([^<]+)<", resp.text)
        return "|".join(sorted(ctags)) or "vide"
    except Exception:
        return None


_derniere_empreinte: str | None = None


async def caldav_a_change() -> bool | None:
    """True si les calendriers ont changé depuis le dernier appel,
    False sinon, None si Radicale est injoignable."""
    global _derniere_empreinte
    empreinte = await _run_sync(_empreinte_caldav_sync)
    if empreinte is None:
        return None
    if empreinte == _derniere_empreinte:
        return False
    _derniere_empreinte = empreinte
    return True


def _creer_evenement_caldav_sync(evenement: dict) -> str:
    """Crée un événement dans Radicale (CalDAV) — synchrone."""
    import uuid
    client = get_caldav_client()
    principal = client.principal()
    calendars = principal.calendars()

    if not calendars:
        cal = principal.make_calendar(name="Kahlo Café")
    else:
        cal = calendars[0]

    vcal = vobject.iCalendar()
    vevent = vobject.newFromBehavior("vevent")

    uid = str(uuid.uuid4())
    vevent.add("uid").value = uid
    vevent.add("summary").value = evenement["titre"]
    vevent.add("dtstart").value = evenement["date_debut"]
    vevent.add("dtend").value = evenement.get("date_fin", evenement["date_debut"])
    if evenement.get("notes"):
        vevent.add("description").value = evenement["notes"]
    if evenement.get("lieu"):
        vevent.add("location").value = evenement["lieu"]

    vcal.add(vevent)
    cal.save_event(vcal.serialize())
    return uid


async def creer_evenement_caldav(evenement: dict) -> str:
    """Crée un événement dans Radicale (CalDAV) → sync Apple Calendar"""
    try:
        uid = await _run_sync(_creer_evenement_caldav_sync, evenement)
        logger.info(f"Événement CalDAV créé: {evenement['titre']}")
        return uid
    except Exception as e:
        logger.error(f"Erreur CalDAV: {e}")
        return None


def _dt_naif(valeur) -> datetime | None:
    """Convertit un dtstart/dtend iCal (date ou datetime aware) en datetime
    naïf UTC — les colonnes PostgreSQL sont sans timezone."""
    if valeur is None:
        return None
    if isinstance(valeur, datetime):
        if valeur.tzinfo is not None:
            return valeur.astimezone(timezone.utc).replace(tzinfo=None)
        return valeur
    if isinstance(valeur, date):
        return datetime.combine(valeur, dt_time.min)
    return None


def _sync_caldav_sync() -> list:
    """Récupère les événements CalDAV — synchrone."""
    client = get_caldav_client()
    principal = client.principal()
    calendars = principal.calendars()

    resultats = []
    for cal in calendars:
        for event in cal.events():
            vevent = event.vobject_instance.vevent
            resultats.append({
                "uid": str(vevent.uid.value),
                "titre": str(getattr(vevent, "summary", None) and vevent.summary.value or "Sans titre"),
                "date_debut": _dt_naif(vevent.dtstart.value),
                "date_fin": _dt_naif(getattr(vevent, "dtend", None) and vevent.dtend.value),
                "notes": str(getattr(vevent, "description", None) and vevent.description.value or "") or None,
            })
    return resultats


async def sync_caldav_vers_db(db) -> list:
    """Sync entrante : importe dans l'ERP les événements créés sur les
    appareils (iPhone/Mac...) qui n'existent pas encore en base."""
    from sqlalchemy import select
    from models import Evenement, TypeEvenement

    try:
        distants = await _run_sync(_sync_caldav_sync)
    except Exception as e:
        logger.error(f"Erreur sync CalDAV: {e}")
        return []

    if not distants:
        return []

    result = await db.execute(select(Evenement.caldav_uid).where(Evenement.caldav_uid != None))
    uids_connus = {row[0] for row in result.all()}

    nouveaux = []
    for ev in distants:
        if ev["uid"] in uids_connus or not ev["date_debut"]:
            continue
        db.add(Evenement(
            type=TypeEvenement.rappel,
            titre=ev["titre"],
            date_debut=ev["date_debut"],
            date_fin=ev["date_fin"],
            notes=ev["notes"],
            caldav_uid=ev["uid"],
        ))
        nouveaux.append({"uid": ev["uid"], "titre": ev["titre"]})

    if nouveaux:
        await db.commit()
        logger.info("CalDAV → ERP : %d événement(s) importé(s)", len(nouveaux))
    return nouveaux


def _supprimer_caldav_sync(uid: str) -> bool:
    """Supprime un événement CalDAV — synchrone."""
    client = get_caldav_client()
    principal = client.principal()
    for cal in principal.calendars():
        for event in cal.events():
            if str(event.vobject_instance.vevent.uid.value) == uid:
                event.delete()
                return True
    return False


async def supprimer_evenement_caldav(uid: str):
    """Supprime un événement CalDAV"""
    try:
        return await _run_sync(_supprimer_caldav_sync, uid)
    except Exception as e:
        logger.error(f"Erreur suppression CalDAV: {e}")
    return False


# ============================================================
#  GOOGLE CALENDAR (bidirectionnel via OAuth)
# ============================================================

def get_google_service(credentials_dict: dict):
    creds = Credentials(
        token=credentials_dict.get("token"),
        refresh_token=credentials_dict.get("refresh_token"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token"
    )
    return build("calendar", "v3", credentials=creds)


async def creer_evenement_google(credentials: dict, evenement: dict) -> str:
    """Crée un événement Google Calendar"""
    try:
        service = await _run_sync(get_google_service, credentials)

        google_event = {
            "summary": evenement["titre"],
            "description": evenement.get("notes", ""),
            "location": evenement.get("lieu", ""),
            "start": {
                "date": evenement["date_debut"].strftime("%Y-%m-%d")
                if isinstance(evenement["date_debut"], datetime)
                else evenement["date_debut"]
            },
            "end": {
                "date": evenement.get("date_fin", evenement["date_debut"]).strftime("%Y-%m-%d")
                if isinstance(evenement.get("date_fin", evenement["date_debut"]), datetime)
                else evenement.get("date_fin", evenement["date_debut"])
            },
            "colorId": _color_for_type(evenement.get("type", "rappel")),
        }

        result = await _run_sync(
            service.events().insert(calendarId="primary", body=google_event).execute
        )

        logger.info(f"Événement Google Calendar créé: {result['id']}")
        return result["id"]

    except Exception as e:
        logger.error(f"Erreur Google Calendar: {e}")
        return None


async def sync_google_vers_db(credentials: dict, db) -> list:
    """Récupère les nouveaux événements Google Calendar et les importe"""
    try:
        service = await _run_sync(get_google_service, credentials)
        now = datetime.now(timezone.utc).isoformat()

        events_result = await _run_sync(
            service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=50,
                singleEvents=True,
                orderBy="startTime"
            ).execute
        )

        events = events_result.get("items", [])
        nouveaux = []
        for event in events:
            nouveaux.append({
                "google_id": event["id"],
                "titre": event.get("summary", ""),
                "date": event["start"].get("date") or event["start"].get("dateTime"),
                "notes": event.get("description", ""),
                "lieu": event.get("location", ""),
            })

        return nouveaux

    except Exception as e:
        logger.error(f"Erreur sync Google Calendar: {e}")
        return []


def _color_for_type(event_type: str) -> str:
    """Couleurs Google Calendar par type d'événement"""
    colors = {
        "marche": "5",       # banane (jaune)
        "commande": "7",     # paon (rose)
        "fournisseur": "2",  # sauge (vert)
        "rappel": "8",       # graphite
    }
    return colors.get(event_type, "1")


# ============================================================
#  CRÉER ÉVÉNEMENT REMISE (appelé depuis webhook sumup)
# ============================================================

async def creer_evenement_remise(db, commande):
    """
    Crée automatiquement un événement de remise dans le calendrier
    quand une commande est payée via sumup
    """
    from models import Evenement, TypeEvenement

    client_label = f"{commande.client.prenom} {commande.client.nom}" if commande.client else "Client"
    evenement = Evenement(
        type=TypeEvenement.commande,
        titre=f"Remise — {client_label}",
        date_debut=commande.date_remise_prev,
        commande_id=commande.id,
        notes=f"Commande {commande.numero} · {commande.montant_total} €",
    )
    db.add(evenement)

    # Sync CalDAV
    uid = await creer_evenement_caldav({
        "titre": evenement.titre,
        "date_debut": evenement.date_debut,
        "notes": evenement.notes,
    })
    if uid:
        evenement.caldav_uid = uid

    logger.info(f"Événement remise créé pour commande {commande.numero}")
