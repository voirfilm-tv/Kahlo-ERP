#!/usr/bin/env python3
"""Diagnostic CalDAV a executer dans le conteneur backend.

Exemple :
  docker compose exec backend python /app/scripts/diagnostic_caldav.py
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx
from passlib.hash import bcrypt


PROPFIND = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<propfind xmlns="DAV:"><prop><resourcetype/></prop></propfind>'
)


def _print(ok: bool, message: str):
    prefix = "OK " if ok else "ERR"
    print(f"{prefix} - {message}")


def verifier_htpasswd(path: Path, user: str, password: str) -> bool:
    if not path.exists():
        _print(False, f"htpasswd absent : {path}")
        return False
    try:
        lignes = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _print(False, f"htpasswd illisible : {exc}")
        return False

    prefix = f"{user}:"
    for ligne in lignes:
        if not ligne.startswith(prefix):
            continue
        try:
            ok = bcrypt.verify(password, ligne[len(prefix):].strip())
        except ValueError as exc:
            _print(False, f"hash htpasswd invalide : {exc}")
            return False
        _print(ok, "mot de passe ERP valide dans le htpasswd Radicale" if ok else "mot de passe ERP different du htpasswd Radicale")
        return ok

    _print(False, f"utilisateur {user!r} absent du htpasswd Radicale")
    return False


async def verifier_radicale(url: str, user: str, password: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            resp = await client.request(
                "PROPFIND",
                url,
                content=PROPFIND,
                headers={"Depth": "0", "Content-Type": "application/xml"},
                auth=(user, password),
            )
    except httpx.RequestError as exc:
        _print(False, f"Radicale injoignable sur {url} : {exc}")
        return False

    ok = resp.status_code in (200, 207)
    if ok:
        _print(True, f"PROPFIND CalDAV accepte les identifiants ERP ({resp.status_code})")
    elif resp.status_code in (401, 403):
        _print(False, f"Radicale refuse les identifiants ERP ({resp.status_code})")
    else:
        _print(False, f"reponse CalDAV inattendue sur {url} ({resp.status_code})")
    return ok


async def main() -> int:
    user = os.getenv("CALDAV_USER", "kahlo")
    password = os.getenv("CALDAV_PASSWORD", "")
    base = os.getenv("CALDAV_BASE_URL", "http://caldav:5232").rstrip("/")
    url = os.getenv("CALDAV_DIAGNOSTIC_URL", f"{base}/{user}/")
    htpasswd = Path(os.getenv("CALDAV_HTPASSWD_PATH", "/app/caldav-data/users"))

    print(f"Utilisateur ERP : {user}")
    print(f"URL testee      : {url}")
    print(f"htpasswd       : {htpasswd}")

    ok_password = bool(password)
    _print(ok_password, "mot de passe ERP present" if ok_password else "CALDAV_PASSWORD absent dans l'environnement backend")
    ok_file = verifier_htpasswd(htpasswd, user, password) if ok_password else False
    ok_radicale = await verifier_radicale(url, user, password) if ok_password else False
    return 0 if ok_password and ok_file and ok_radicale else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
