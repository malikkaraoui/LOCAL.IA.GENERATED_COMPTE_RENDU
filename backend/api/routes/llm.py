"""Routes d'administration LLM (Ollama).

Objectif: fournir un "restart" soft depuis l'UI quand les modèles sont bloqués/occupés.

⚠️ Important:
- On ne peut pas redémarrer le daemon Ollama lui-même depuis Python sans privilèges OS.
- On implémente donc un "restart" logique: demander à Ollama de libérer (unload) les modèles
  en mémoire via keep_alive=0, ce qui réinitialise souvent l'état.

Référence pratique:
- /api/ps: liste des modèles en mémoire
- /api/generate: supporte keep_alive=0 pour décharger après la requête
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class OllamaRestartRequest(BaseModel):
    host: Optional[str] = Field(default=None, description="URL du serveur Ollama (optionnel)")


def _coerce_model_name(item: Any) -> Optional[str]:
    if isinstance(item, str):
        return item.strip() or None
    if isinstance(item, dict):
        for k in ("name", "model"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


@router.post("/ollama/restart")
async def restart_ollama(req: OllamaRestartRequest) -> Dict[str, Any]:
    """Restart soft des LLM Ollama.

    Étapes:
    1) Vérifier que le serveur répond (/api/version)
    2) Lire les modèles en mémoire (/api/ps)
    3) Pour chaque modèle actif, envoyer une requête "minimale" avec keep_alive=0 pour forcer le unload.

    Retourne un résumé (unloaded + erreurs par modèle).
    """

    host = (req.host or settings.OLLAMA_HOST or "").strip()
    if not host:
        raise HTTPException(status_code=400, detail="Host Ollama manquant")

    base = host.rstrip("/")

    # 1) ping
    try:
        r = requests.get(f"{base}/api/version", timeout=5)
        r.raise_for_status()
        version_payload = r.json() if hasattr(r, "json") else {}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Ollama non accessible: {exc}")

    version = (
        (version_payload.get("version") if isinstance(version_payload, dict) else None)
        or (version_payload.get("name") if isinstance(version_payload, dict) else None)
        or "unknown"
    )

    # 2) modèles actifs
    running_models: List[str] = []
    ps_error: Optional[str] = None
    try:
        ps = requests.get(f"{base}/api/ps", timeout=5)
        ps.raise_for_status()
        payload = ps.json()
        items = payload.get("models", []) if isinstance(payload, dict) else payload
        if isinstance(items, list):
            for it in items:
                name = _coerce_model_name(it)
                if name and name not in running_models:
                    running_models.append(name)
    except Exception as exc:
        ps_error = str(exc)

    unloaded: List[str] = []
    errors: List[Dict[str, str]] = []

    # 3) unload
    for model in running_models:
        try:
            # Requête minimale: num_predict=1 pour éviter de générer inutilement.
            # keep_alive=0 demande à Ollama de décharger le modèle après la requête.
            payload = {
                "model": model,
                "prompt": "ping",
                "stream": False,
                "keep_alive": 0,
                "options": {"num_predict": 1},
            }
            resp = requests.post(f"{base}/api/generate", json=payload, timeout=30)
            resp.raise_for_status()
            unloaded.append(model)
        except Exception as exc:
            logger.warning("restart ollama: failed unload model=%s: %s", model, exc)
            errors.append({"model": model, "error": str(exc)})

    return {
        "status": "ok",
        "host": base,
        "version": version,
        "running_models": running_models,
        "unloaded": unloaded,
        "errors": errors,
        "ps_error": ps_error,
        "message": (
            "Aucun modèle actif à décharger" if not running_models else f"Déchargé: {len(unloaded)}/{len(running_models)}"
        ),
    }
