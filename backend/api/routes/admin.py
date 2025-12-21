"""Routes d'administration (local dev) pour piloter les workers.

⚠️ Sécurité:
- Ces endpoints sont destinés à un usage local (dev) uniquement.
- Ils sont refusés si l'appel ne provient pas de localhost.

Objectif:
- Permettre depuis le frontend de redémarrer les workers si une queue est bloquée
  ou si l'on veut explicitement interrompre les jobs en cours.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request

from backend.config import PROJECT_ROOT

router = APIRouter()


def _ensure_localhost(request: Request) -> None:
    host = getattr(getattr(request, "client", None), "host", None)
    if host not in {"127.0.0.1", "::1"}:
        raise HTTPException(status_code=403, detail="Admin endpoints: localhost only")


def _project_python() -> str:
    # On privilégie la venv du projet si présente.
    cand = PROJECT_ROOT / ".venv" / "bin" / "python"
    return str(cand) if cand.exists() else "python"


def _spawn_worker(*, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(log_path, "ab", buffering=0)

    env = os.environ.copy()
    # Fix macOS fork safety
    env.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

    proc = subprocess.Popen(
        [_project_python(), str(PROJECT_ROOT / "scripts" / "start_worker.py")],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=f,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return int(proc.pid)


@router.post("/admin/workers/restart")
async def restart_workers(
    request: Request,
    count: int = Query(1, ge=1, le=8, description="Nombre de workers à (re)démarrer"),
    kill: bool = Query(True, description="Tuer les workers existants avant de relancer"),
):
    """Redémarre les workers RQ.

    - kill=true: arrête tous les workers existants puis en relance `count`.
    - kill=false: conserve les workers existants et en lance `count` supplémentaires.

    Réponse: liste des PIDs lancés.
    """
    _ensure_localhost(request)

    killed = False
    if kill:
        # pkill renvoie code != 0 si aucun process trouvé.
        subprocess.run(["pkill", "-f", "scripts/start_worker.py"], check=False)
        killed = True
        # Laisser le temps au système de libérer les ressources.
        time.sleep(0.6)

    pids: list[int] = []
    for i in range(count):
        log = Path("/tmp") / ("worker.log" if i == 0 else f"worker_{i+1}.log")
        pids.append(_spawn_worker(log_path=log))

    return {
        "message": "workers restarted" if killed else "workers started",
        "killed": killed,
        "count": count,
        "pids": pids,
        "logs": ["/tmp/worker.log"] + [f"/tmp/worker_{i+1}.log" for i in range(1, count)],
    }
