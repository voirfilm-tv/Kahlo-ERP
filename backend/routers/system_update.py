"""KAHLO CAFÉ — Mise à jour logicielle (admin uniquement)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import threading

import httpx

from routers.auth import require_admin

router = APIRouter()

GITHUB_RELEASE_API = os.getenv(
    "KAHLO_RELEASES_API",
    "https://api.github.com/repos/voirfilm-tv/Kahlo-ERP/releases/latest",
)
REPO_PATH = Path(os.getenv("KAHLO_REPO_PATH", "/workspace/Kahlo-ERP"))
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
AUTO_UPDATE_ENABLED = os.getenv("KAHLO_AUTO_UPDATE_ENABLED", "false").lower() in {"1", "true", "yes"}
STATUS_FILE = Path(os.getenv("KAHLO_UPDATE_STATUS_FILE", "/backups/kahlo/system_update_status.json"))


class UpdateState:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.job_id = None
        self.started_at = None
        self.finished_at = None
        self.status = "idle"
        self.logs: list[dict] = []
        self.technical_logs: list[str] = []
        self.error = None
        self.manual_instructions: list[str] = []
        self.last_check = None
        self.local_version = self._read_local_version()
        self.remote_version = None
        self.remote_error = None
        self.load_last_state()

    def _read_local_version(self) -> str:
        version_file = Path("/app/VERSION")
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip() or APP_VERSION
        return APP_VERSION

    def load_last_state(self):
        if not STATUS_FILE.exists():
            return
        try:
            data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            self.finished_at = data.get("finished_at")
            self.status = data.get("status", self.status)
            self.logs = data.get("logs", self.logs)[-30:]
            self.error = data.get("error")
            self.manual_instructions = data.get("manual_instructions", [])
        except Exception:
            return

    def persist(self):
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATUS_FILE.write_text(
            json.dumps(
                {
                    "finished_at": self.finished_at,
                    "status": self.status,
                    "logs": self.logs[-50:],
                    "error": self.error,
                    "manual_instructions": self.manual_instructions,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def human_log(self, message: str, level: str = "info"):
        self.logs.append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "message": message,
            }
        )

    def tech_log(self, message: str):
        self.technical_logs.append(message)


STATE = UpdateState()


class StartUpdateRequest(BaseModel):
    target_version: str | None = None


def _parse_version(v: str) -> tuple:
    cleaned = (v or "").strip().lstrip("v")
    nums = re.findall(r"\d+", cleaned)
    if not nums:
        return (0,)
    return tuple(int(n) for n in nums)


def _is_remote_newer(local: str, remote: str | None) -> bool:
    if not remote:
        return False
    return _parse_version(remote) > _parse_version(local)


async def _fetch_latest_release() -> tuple[str | None, str | None]:
    timeout = httpx.Timeout(8.0, connect=4.0)
    async with httpx.AsyncClient(timeout=timeout, headers={"Accept": "application/vnd.github+json"}) as client:
        resp = await client.get(GITHUB_RELEASE_API)
        resp.raise_for_status()
        payload = resp.json()
        tag_name = payload.get("tag_name")
        if not tag_name:
            raise RuntimeError("Release GitHub sans tag_name")
        return tag_name, payload.get("html_url")


def _build_manual_instructions(target: str) -> list[str]:
    return [
        f"cd {REPO_PATH}",
        "git fetch --tags origin",
        f"git checkout {target}",
        "docker compose up -d --build backend frontend nginx",
        "docker compose ps",
    ]


def _check_runtime_capabilities() -> tuple[bool, list[str]]:
    problems = []
    if not REPO_PATH.exists():
        problems.append(f"Dépôt introuvable: {REPO_PATH}")
    if shutil.which("git") is None:
        problems.append("Commande git indisponible")
    if shutil.which("docker") is None:
        problems.append("Commande docker indisponible")
    compose_file = REPO_PATH / "docker-compose.yml"
    if REPO_PATH.exists() and not compose_file.exists():
        problems.append("docker-compose.yml introuvable dans le dépôt")
    if REPO_PATH.exists() and not os.access(REPO_PATH, os.W_OK):
        problems.append("Le processus n'a pas les droits d'écriture sur le dépôt")
    return len(problems) == 0, problems


def _run_cmd(cmd: list[str]):
    return subprocess.run(cmd, cwd=str(REPO_PATH), capture_output=True, text=True)


def _execute_update(job_id: str, target: str):
    try:
        STATE.human_log("On prépare la mise à jour.")
        steps = [
            ("On récupère les informations de version…", ["git", "fetch", "--tags", "origin"]),
            ("On télécharge la version du logiciel…", ["git", "checkout", target]),
            ("On met à jour le logiciel sans toucher à vos données…", ["docker", "compose", "up", "-d", "--build", "backend", "frontend", "nginx"]),
            ("On redémarre les services…", ["docker", "compose", "ps"]),
            ("Vérification finale en cours…", ["docker", "compose", "ps"]),
        ]
        for text, cmd in steps:
            STATE.human_log(text)
            proc = _run_cmd(cmd)
            STATE.tech_log(f"$ {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
            if proc.returncode != 0:
                raise RuntimeError(f"Commande échouée: {' '.join(cmd)}")
        STATE.local_version = target
        STATE.human_log("Mise à jour terminée ✅", "success")
        STATE.status = "success"
    except Exception as exc:
        STATE.status = "error"
        STATE.error = {
            "friendly": "La mise à jour n'a pas pu se terminer automatiquement. Vos données n'ont pas été supprimées.",
            "technical": str(exc),
        }
        STATE.human_log("La mise à jour a rencontré un problème. On vous propose les étapes manuelles sécurisées.", "error")
    finally:
        STATE.running = False
        STATE.finished_at = datetime.now(timezone.utc).isoformat()
        STATE.persist()


@router.get("/status")
async def update_status(admin: dict = Depends(require_admin)):
    _ = admin
    up_to_date = None
    if STATE.remote_version:
        up_to_date = not _is_remote_newer(STATE.local_version, STATE.remote_version)
    return {
        "local_version": STATE.local_version,
        "remote_version": STATE.remote_version,
        "remote_error": STATE.remote_error,
        "state": (
            "verification_impossible"
            if STATE.remote_error
            else ("a_jour" if up_to_date else "mise_a_jour_disponible")
            if up_to_date is not None
            else "inconnu"
        ),
        "auto_update_enabled": AUTO_UPDATE_ENABLED,
        "job": {
            "id": STATE.job_id,
            "running": STATE.running,
            "status": STATE.status,
            "started_at": STATE.started_at,
            "finished_at": STATE.finished_at,
            "logs": STATE.logs[-20:],
            "error": STATE.error,
            "manual_instructions": STATE.manual_instructions,
            "technical_logs": STATE.technical_logs[-20:],
        },
    }


@router.post("/check")
async def check_update(admin: dict = Depends(require_admin)):
    _ = admin
    try:
        tag, html_url = await _fetch_latest_release()
        STATE.remote_version = tag
        STATE.remote_error = None
        STATE.last_check = datetime.now(timezone.utc).isoformat()
        return {
            "local_version": STATE.local_version,
            "remote_version": tag,
            "release_url": html_url,
            "update_available": _is_remote_newer(STATE.local_version, tag),
        }
    except Exception as exc:
        STATE.remote_error = str(exc)
        raise HTTPException(
            status_code=502,
            detail="Impossible de vérifier les releases GitHub pour le moment.",
        )


@router.post("/start")
async def start_update(req: StartUpdateRequest, admin: dict = Depends(require_admin)):
    _ = admin
    with STATE.lock:
        if STATE.running:
            raise HTTPException(status_code=409, detail="Une mise à jour est déjà en cours.")

        target = req.target_version or STATE.remote_version
        if not target:
            raise HTTPException(status_code=400, detail="Aucune version cible disponible. Lancez d'abord la vérification.")
        if not _is_remote_newer(STATE.local_version, target):
            raise HTTPException(status_code=400, detail="Le logiciel est déjà à jour.")

        ok, problems = _check_runtime_capabilities()
        STATE.manual_instructions = _build_manual_instructions(target)

        if not AUTO_UPDATE_ENABLED or not ok:
            reason = "Mise à jour automatique non disponible sur cet environnement."
            if problems:
                reason += " " + " | ".join(problems)
            STATE.status = "manual_required"
            STATE.error = {
                "friendly": "La mise à jour automatique n'est pas possible ici. Utilisez les commandes guidées ci-dessous.",
                "technical": reason,
            }
            STATE.human_log("On ne peut pas lancer l'auto-mise à jour ici, mais on a préparé des étapes sûres.", "warning")
            STATE.finished_at = datetime.now(timezone.utc).isoformat()
            STATE.persist()
            raise HTTPException(status_code=409, detail="Mise à jour automatique indisponible sur ce serveur.")

        STATE.running = True
        STATE.job_id = f"update-{int(datetime.now(timezone.utc).timestamp())}"
        STATE.started_at = datetime.now(timezone.utc).isoformat()
        STATE.finished_at = None
        STATE.status = "running"
        STATE.error = None
        STATE.logs = []
        STATE.technical_logs = []
        STATE.human_log("On regarde s'il existe une nouvelle version…")
        thread = threading.Thread(target=_execute_update, args=(STATE.job_id, target), daemon=True)
        thread.start()

        return {"message": "Mise à jour lancée", "job_id": STATE.job_id, "target_version": target}
