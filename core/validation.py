"""Modèles de validation avec pydantic."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class OllamaConfig(BaseModel):
    """Configuration pour Ollama."""

    host: str = Field(default="http://localhost:11434", description="URL du serveur Ollama")
    model: str = Field(default="llama2", description="Nom du modèle à utiliser")
    temperature: float = Field(default=0.3, ge=0.0, le=1.0, description="Température de génération")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling")
    timeout: int = Field(default=300, gt=0, description="Timeout en secondes")
    max_retries: int = Field(default=3, ge=0, description="Nombre de tentatives max")

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Valide que l'host est une URL valide."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Host doit commencer par http:// ou https://")
        return v.rstrip("/")


class ExtractConfig(BaseModel):
    """Configuration pour l'extraction de documents."""

    enable_soffice: bool = Field(default=True, description="Activer LibreOffice pour formats Office")
    max_file_size_mb: int = Field(default=50, gt=0, description="Taille max fichier en MB")
    chunk_size: int = Field(default=1200, gt=0, description="Taille des chunks de texte")
    chunk_overlap: int = Field(default=200, ge=0, description="Chevauchement entre chunks")
    exclude_patterns: list[str] = Field(
        default_factory=lambda: [".git/", "__pycache__/", "node_modules/"],
        description="Patterns de fichiers à exclure",
    )

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        """Valide que l'overlap est inférieur à la taille du chunk."""
        # Note: info.data contient les autres champs déjà validés
        chunk_size = info.data.get("chunk_size", 1200)
        if v >= chunk_size:
            raise ValueError("chunk_overlap doit être < chunk_size")
        return v


class RenderConfig(BaseModel):
    """Configuration pour le rendu de rapports."""

    template_path: Path = Field(description="Chemin vers le template DOCX")
    output_dir: Path = Field(description="Répertoire de sortie")
    overwrite: bool = Field(default=False, description="Écraser fichiers existants")
    export_pdf: bool = Field(default=True, description="Exporter aussi en PDF")

    @field_validator("template_path")
    @classmethod
    def validate_template(cls, v: Path) -> Path:
        """Valide que le template existe."""
        if not v.exists():
            raise ValueError(f"Template non trouvé: {v}")
        if v.suffix.lower() != ".docx":
            raise ValueError(f"Template doit être un fichier .docx, pas {v.suffix}")
        return v

    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, v: Path) -> Path:
        """Crée le répertoire de sortie s'il n'existe pas."""
        v.mkdir(parents=True, exist_ok=True)
        return v


class FieldGenerationConfig(BaseModel):
    """Configuration pour la génération d'un champ."""

    key: str = Field(description="Clé du champ (ex: PROFESSION)")
    query: str = Field(description="Question pour le LLM")
    instructions: str = Field(description="Instructions de génération")
    max_chars: int = Field(default=400, gt=0, description="Nombre max de caractères")
    max_lines: int = Field(default=4, gt=0, description="Nombre max de lignes")
    require_sources: bool = Field(default=False, description="Sources requises")
    allowed_values: list[str] | None = Field(default=None, description="Valeurs autorisées")
    field_type: Literal["short", "narrative", "list", "constrained", "deterministic"] = Field(
        default="narrative", description="Type de champ"
    )


class AppConfig(BaseModel):
    """Configuration globale de l'application."""

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    extract: ExtractConfig = Field(default_factory=ExtractConfig)
    render: RenderConfig | None = Field(default=None)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_file: Path | None = Field(default=None, description="Fichier de log")

    class Config:
        """Configuration pydantic."""

        # Permettre Path et autres types custom
        arbitrary_types_allowed = True


def load_config(config_file: Path | None = None) -> AppConfig:
    """
    Charge la configuration depuis un fichier JSON/YAML ou retourne config par défaut.
    
    Args:
        config_file: Chemin vers fichier de config (optionnel)
        
    Returns:
        Configuration validée
    """
    if config_file and config_file.exists():
        import json

        if config_file.suffix == ".json":
            with open(config_file) as f:
                data = json.load(f)
            return AppConfig(**data)
        elif config_file.suffix in (".yaml", ".yml"):
            try:
                import yaml

                with open(config_file) as f:
                    data = yaml.safe_load(f)
                return AppConfig(**data)
            except ImportError:
                raise ImportError("PyYAML non installé. Installez avec: pip install pyyaml")
        else:
            raise ValueError(f"Format non supporté: {config_file.suffix}")

    return AppConfig()
