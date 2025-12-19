"""Routes de santé de l'API."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

import requests
from backend.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Vérification de santé de l'API."""
    return {
        "status": "healthy",
        "version": "2.0.1"
    }


@router.get("/health/ollama")
async def ollama_health():
    """Vérification de la connexion Ollama."""
    try:
        resp = requests.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json() if hasattr(resp, "json") else {}
        models = data.get("models", [])
        return {
            "status": "healthy",
            "models": models,
        }
    except Exception as e:
        return JSONResponse(status_code=503, content={"error": str(e)})


@router.get("/ollama/models")
async def list_ollama_models(host: str | None = Query(default=None, description="Host Ollama (optionnel)")):
    """Récupérer la liste des modèles Ollama disponibles.

    Note: l'UI permet de saisir un host Ollama; si on ignore ce champ et qu'on utilise
    toujours settings.OLLAMA_HOST, la liste paraît "fake".
    """
    try:
        base = (host or settings.OLLAMA_HOST).rstrip("/")
        resp = requests.get(f"{base}/api/tags", timeout=5)
        resp.raise_for_status()

        data = resp.json()
        models = data.get("models", [])

        # Formater la réponse
        model_list = []
        for model in models:
            model_list.append({
                "name": model.get("name"),
                "size": model.get("size", 0),
                "modified": model.get("modified_at"),
                "available": True
            })

        return {
            "models": model_list,
            "host": base,
            "count": len(model_list)
        }

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama non accessible: {str(e)}")
