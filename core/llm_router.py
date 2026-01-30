"""Module centralisé pour la gestion des appels LLM (tous providers)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal, Optional
from urllib import request
from urllib.error import URLError, HTTPError

from pydantic import BaseModel, Field
import requests

from core.errors import Result, OllamaError

logger = logging.getLogger(__name__)


# ============================================================================
# Modèles Pydantic pour configuration LLM
# ============================================================================

class LLMConfig(BaseModel):
    """Configuration LLM unifiée (tous providers)."""
    
    provider: Literal["ollama", "openai", "local"] = Field(
        default="ollama",
        description="Provider LLM: ollama, openai, local"
    )
    base_url: Optional[str] = Field(
        default="http://localhost:11434",
        description="URL de base du service LLM"
    )
    model: str = Field(
        ...,
        description="Nom du modèle (ex: qwen3-next:latest)"
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Température de génération"
    )
    max_tokens: int = Field(
        default=1024,
        ge=1,
        description="Nombre maximum de tokens générés"
    )
    top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Top-p sampling"
    )
    timeout: float = Field(
        default=120.0,
        ge=1.0,
        description="Timeout en secondes"
    )
    
    @classmethod
    def from_legacy(
        cls,
        model: str,
        host: str = "http://localhost:11434",
        temperature: float = 0.2,
        top_p: float = 0.9,
        timeout: float = 120.0,
        max_tokens: int = 1024,
    ) -> "LLMConfig":
        """Crée une config depuis les anciens paramètres (rétrocompatibilité)."""
        return cls(
            provider="ollama",
            base_url=host,
            model=model,
            temperature=temperature,
            top_p=top_p,
            timeout=timeout,
            max_tokens=max_tokens,
        )


class LLMResponse(BaseModel):
    """Réponse d'un appel LLM."""
    
    text: str
    provider: str
    model: str
    latency_ms: float
    tokens_used: Optional[int] = None


class LLMError(BaseModel):
    """Erreur détaillée d'un appel LLM."""
    
    provider: str
    base_url: str
    endpoint: str
    model: str
    status_code: Optional[int] = None
    error_type: str  # "connection_refused", "timeout", "endpoint_404", "model_404", "http_error", "unknown"
    message: str
    body_excerpt: Optional[str] = None


# ============================================================================
# Router LLM: fonction unique pour tous les providers
# ============================================================================

def call_llm(
    config: LLMConfig,
    prompt: str,
    *,
    messages: Optional[list[dict[str, str]]] = None,
    field_name: Optional[str] = None,
) -> Result[LLMResponse]:
    """
    Appelle le LLM selon le provider configuré.
    
    Args:
        config: Configuration LLM
        prompt: Prompt simple (si messages=None)
        messages: Messages format chat (optionnel, prioritaire sur prompt)
        field_name: Nom du champ généré (pour logs)
    
    Returns:
        Result[LLMResponse]: Succès avec réponse ou échec avec erreur détaillée
    """
    start_time = time.time()
    
    # Log début
    logger.info(
        "🤖 LLM [%s] field=%s provider=%s model=%s",
        "CALL",
        field_name or "unknown",
        config.provider,
        config.model,
    )
    
    # Router selon provider
    if config.provider == "ollama":
        result = _call_ollama(config, prompt, messages)
    elif config.provider == "openai":
        result = _call_openai(config, prompt, messages)
    elif config.provider == "local":
        result = _call_local(config, prompt, messages)
    else:
        error_obj = LLMError(
            provider=config.provider,
            base_url=config.base_url or "N/A",
            endpoint="N/A",
            model=config.model,
            error_type="unknown",
            message=f"Provider inconnu: {config.provider}",
        )
        return Result.fail(OllamaError(f"Provider inconnu: {config.provider}"))
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Log résultat
    if result.success:
        logger.info(
            "✅ LLM [OK] field=%s model=%s latency=%.0fms chars=%d",
            field_name or "unknown",
            config.model,
            latency_ms,
            len(result.value.text) if result.value else 0,
        )
    else:
        error_data = result.error
        logger.error(
            "❌ LLM [ERROR] field=%s provider=%s model=%s error_type=%s message=%s",
            field_name or "unknown",
            config.provider,
            config.model,
            getattr(error_data, "error_type", "unknown") if hasattr(error_data, "error_type") else "unknown",
            str(error_data),
        )
    
    return result


# ============================================================================
# Implémentations par provider
# ============================================================================

def _call_ollama(
    config: LLMConfig,
    prompt: str,
    messages: Optional[list[dict[str, str]]] = None,
) -> Result[LLMResponse]:
    """Appelle Ollama via /api/chat ou /api/generate."""
    
    base_url = (config.base_url or "http://localhost:11434").rstrip("/")
    
    # Utiliser /api/chat si messages fournis, sinon /api/generate
    if messages:
        endpoint = f"{base_url}/api/chat"
        payload = {
            "model": config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "num_predict": config.max_tokens,
            },
        }
    else:
        endpoint = f"{base_url}/api/generate"
        payload = {
            "model": config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "num_predict": config.max_tokens,
            },
        }
    
    try:
        # Appel HTTP
        response = requests.post(
            endpoint,
            json=payload,
            timeout=config.timeout,
        )
        
        # Gestion erreurs HTTP
        if response.status_code != 200:
            return _handle_ollama_error(
                config, endpoint, response.status_code, response.text
            )
        
        # Parse réponse
        data = response.json()
        
        if messages:
            # Format /api/chat
            text = data.get("message", {}).get("content", "")
        else:
            # Format /api/generate
            text = data.get("response", "")
        
        return Result.ok(
            LLMResponse(
                text=text,
                provider="ollama",
                model=config.model,
                latency_ms=0,  # Sera calculé par l'appelant
                tokens_used=data.get("eval_count"),
            )
        )
        
    except requests.exceptions.Timeout:
        error_obj = LLMError(
            provider="ollama",
            base_url=base_url,
            endpoint=endpoint,
            model=config.model,
            error_type="timeout",
            message=f"Timeout après {config.timeout}s",
        )
        return Result.fail(error_obj)
        
    except requests.exceptions.ConnectionError as exc:
        error_obj = LLMError(
            provider="ollama",
            base_url=base_url,
            endpoint=endpoint,
            model=config.model,
            error_type="connection_refused",
            message=f"Service Ollama indisponible: {exc}",
        )
        return Result.fail(error_obj)
        
    except Exception as exc:
        error_obj = LLMError(
            provider="ollama",
            base_url=base_url,
            endpoint=endpoint,
            model=config.model,
            error_type="unknown",
            message=str(exc),
        )
        return Result.fail(error_obj)


def _handle_ollama_error(
    config: LLMConfig,
    endpoint: str,
    status_code: int,
    body: str,
) -> Result[LLMResponse]:
    """Analyse une erreur HTTP Ollama et retourne un message clair."""
    
    body_lower = body.lower()
    body_excerpt = body[:800] if body else ""
    
    base_url = config.base_url or "http://localhost:11434"
    
    if status_code == 404:
        # Distinguer 404 route vs 404 model
        if "model" in body_lower or "not found" in body_lower:
            error_obj = LLMError(
                provider="ollama",
                base_url=base_url,
                endpoint=endpoint,
                model=config.model,
                status_code=404,
                error_type="model_404",
                message=f"Modèle '{config.model}' introuvable sur Ollama",
                body_excerpt=body_excerpt,
            )
            return Result.fail(error_obj)
        else:
            error_obj = LLMError(
                provider="ollama",
                base_url=base_url,
                endpoint=endpoint,
                model=config.model,
                status_code=404,
                error_type="endpoint_404",
                message=f"Endpoint Ollama invalide: {endpoint}",
                body_excerpt=body_excerpt,
            )
            return Result.fail(error_obj)
    
    # Autres erreurs HTTP
    error_obj = LLMError(
        provider="ollama",
        base_url=base_url,
        endpoint=endpoint,
        model=config.model,
        status_code=status_code,
        error_type="http_error",
        message=f"Erreur HTTP {status_code}",
        body_excerpt=body_excerpt,
    )
    
    return Result.fail(error_obj)


def _call_openai(
    config: LLMConfig,
    prompt: str,
    messages: Optional[list[dict[str, str]]] = None,
) -> Result[LLMResponse]:
    """Appelle OpenAI (à implémenter si besoin)."""
    return Result.fail(OllamaError("Provider OpenAI pas encore implémenté"))


def _call_local(
    config: LLMConfig,
    prompt: str,
    messages: Optional[list[dict[str, str]]] = None,
) -> Result[LLMResponse]:
    """Appelle un modèle local (à implémenter si besoin)."""
    return Result.fail(OllamaError("Provider local pas encore implémenté"))


# ============================================================================
# Healthcheck Ollama (utilise /api/version)
# ============================================================================

def check_ollama_health(
    base_url: str = "http://localhost:11434",
    model: Optional[str] = None,
    timeout: float = 5.0,
) -> Result[dict[str, Any]]:
    """
    Vérifie la santé d'Ollama avec /api/version et optionnellement un modèle.
    
    Returns:
        Result avec {"version": str, "model_available": bool}
    """
    base_url = base_url.rstrip("/")
    
    try:
        # 1. Ping serveur
        response = requests.get(
            f"{base_url}/api/version",
            timeout=timeout,
        )
        response.raise_for_status()
        
        version_data = response.json()
        version = version_data.get("version", "unknown")
        
        # 2. Vérifier modèle si demandé
        model_available = None
        if model:
            tags_response = requests.get(
                f"{base_url}/api/tags",
                timeout=timeout,
            )
            tags_response.raise_for_status()
            
            tags_data = tags_response.json()
            models = tags_data.get("models", [])
            model_names = {m.get("name") for m in models if isinstance(m, dict)}
            model_available = model in model_names
        
        return Result.ok({
            "version": version,
            "model_available": model_available,
        })
        
    except requests.exceptions.ConnectionError:
        return Result.fail(OllamaError(f"Service Ollama indisponible sur {base_url}"))
    except requests.exceptions.Timeout:
        return Result.fail(OllamaError(f"Timeout lors de la vérification Ollama"))
    except Exception as exc:
        return Result.fail(OllamaError(f"Erreur vérification Ollama: {exc}"))
