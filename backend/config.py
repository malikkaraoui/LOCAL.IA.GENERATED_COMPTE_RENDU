"""Configuration du backend.

Notes:
- On ancre les chemins relatifs au *project root* (et pas au CWD) pour éviter
    les erreurs quand le backend/worker est lancé depuis un autre dossier.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configuration de l'application."""

    # Pydantic v2: ignorer les variables d'env non déclarées (pratique en dev)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # App
    APP_NAME: str = "RapportIA API"
    DEBUG: bool = False
    
    # API
    API_PREFIX: str = "/api"
    # Important: Vite peut tourner sur localhost OU 127.0.0.1 selon le host.
    # Si l'origine n'est pas listée, le navigateur bloque les requêtes (CORS) et l'UI
    # tombe en fallback (liste modèles "fake", boutons qui semblent ne rien faire).
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Server
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    
    # Ollama
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral:latest"
    OLLAMA_TIMEOUT: int = 300
    
    # Redis (pour queue)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Paths
    CLIENTS_DIR: Path = PROJECT_ROOT / "CLIENTS"
    OUTPUT_DIR: Path = PROJECT_ROOT / "out"
    TEMPLATES_DIR: Path = PROJECT_ROOT / "uploaded_templates"
    TEMPLATE_PATH: Path = PROJECT_ROOT / "TemplateRapportStage.docx"
    
    # Security
    SECRET_KEY: str = "change-me-in-production"  # À remplacer !
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"
    
settings = Settings()
