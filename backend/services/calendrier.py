"""
KAHLO CAFÉ — Service Calendrier
Sync bidirectionnelle CalDAV (Apple) + Google Calendar API
"""

import caldav
import vobject
import os
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import logging

logger = logging.getLogger(__name__)

CALDAV_URL = os.getenv("CALDAV_BASE_URL", "http://caldav:5232")
CALDAV_USER = "kahlo"
CALDAV_PASSWORD = os.getenv("CALDAV_PASSWORD", "kahlo")


# ============================================================
#  CALDAV (Apple Calendar — bidirectionnel)
# ============================================================

def get_caldav_client():
    return caldav.DAVClient(
        url=f"{CALDAV_URL}/{CALDAV_USER}/",
        username=CALDAV_USER,
        password=CALDAV_PASSWORD
    )


async def creer_evenement_caldav(evenement: dict) -> str:
    """Crée un événement dans Radicale (CalDAV) → sync Apple Calendar"""
    try:
        client = get_caldav_client()
        principal = client.principal()
        calendars = principal.calendars()

        if not calendars:
            cal = principal.make_calendar(name="Kahlo Café")
        else:
            cal = calendars[0]

        # Construire le vEvent
        vcal = vobject.iCalendar()
        vevent = vobject.newFromBehavior("vevent")

        import uuid
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
        logger.info(f"Événement CalDAV créé: {evenement['titre']}")
        return uid

    except Exception as e:
        logger.error(f"Erreur CalDAV: {e}")
        return None


async def sync_caldav_vers_db(db) -> list:
    """
    Sync bidirectionnelle : récupère les événements Apple Calendar
    et les importe dans l'ERP si nouveaux
    """
    try:
        client = get_caldav_client()
        principal = client.principal()
        calendars = principal.calendars()

        nouveaux = []
        for cal in calendars:
            events = cal.events()
            for event in events:
                vevent = event.vobject_instance.vevent
                uid = str(vevent.uid.value)
                titre = str(vevent.summary.value)

                # Vérifier si existe déjà en DB
                # (à compléter avec la vraie vérification DB)
                nouveaux.append({
                    "uid": uid,
                    "titre": titre,
                    "date": vevent.dtstart.value,
                })

        return nouveaux

    except Exception as e:
        logger.error(f"Erreur sync CalDAV: {e}")
        return []


async def supprimer_evenement_caldav(uid: str):
    """Supprime un événement CalDAV"""
    try:
        client = get_caldav_client()
        principal = client.principal()
        for cal in principal.calendars():
            for event in cal.events():
                if str(event.vobject_instance.vevent.uid.value) == uid:
                    event.delete()
                    return True
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
        service = get_google_service(credentials)

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

        result = service.events().insert(
            calendarId="primary",
            body=google_event
        ).execute()

        logger.info(f"Événement Google Calendar créé: {result['id']}")
        return result["id"]

    except Exception as e:
        logger.error(f"Erreur Google Calendar: {e}")
        return None


async def sync_google_vers_db(credentials: dict, db) -> list:
    """Récupère les nouveaux événements Google Calendar et les importe"""
    try:
        service = get_google_service(credentials)
        now = datetime.utcnow().isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=50,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

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

    evenement = Evenement(
        type=TypeEvenement.commande,
        titre=f"Remise — {commande.client.prenom} {commande.client.nom}",
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
