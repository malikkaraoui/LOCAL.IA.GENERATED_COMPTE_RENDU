"""Init pour les routes de l'API."""

from backend.api.routes import health, reports, auth, branding, llm, rag_audio, admin, training, filesystem

__all__ = ["health", "reports", "auth", "branding", "llm", "rag_audio", "admin", "training", "filesystem"]
