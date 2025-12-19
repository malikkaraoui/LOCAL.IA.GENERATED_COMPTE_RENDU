"""Init pour les routes de l'API."""

from backend.api.routes import health, reports, auth, branding, llm

__all__ = ["health", "reports", "auth", "branding", "llm"]
