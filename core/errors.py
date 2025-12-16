"""Gestion d'erreurs robuste avec pattern Result."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")


@dataclass
class Result(Generic[T]):
    """
    Pattern Result pour gestion d'erreurs explicite sans exceptions.
    
    Usage:
        result = extract_pdf(path)
        if result.success:
            print(f"Extracted: {result.value}")
        else:
            print(f"Error: {result.error}")
    """

    value: T | None
    error: str | None
    success: bool

    @staticmethod
    def ok(value: T) -> Result[T]:
        """Crée un résultat réussi."""
        return Result(value=value, error=None, success=True)

    @staticmethod
    def fail(error: str) -> Result[T]:
        """Crée un résultat échoué."""
        return Result(value=None, error=error, success=False)

    def map(self, func: Callable[[T], U]) -> Result[U]:
        """Transforme la valeur si succès, propage l'erreur sinon."""
        if self.success and self.value is not None:
            try:
                return Result.ok(func(self.value))
            except Exception as e:
                return Result.fail(str(e))
        return Result.fail(self.error or "Unknown error")

    def and_then(self, func: Callable[[T], Result[U]]) -> Result[U]:
        """Chaîne des opérations qui retournent Result."""
        if self.success and self.value is not None:
            return func(self.value)
        return Result.fail(self.error or "Unknown error")

    def unwrap(self) -> T:
        """Récupère la valeur ou lève une exception si erreur."""
        if self.success and self.value is not None:
            return self.value
        # Lever l'erreur AppError déjà stockée
        if isinstance(self.error, Exception):
            raise self.error
        raise AppError(f"Unwrap on failed Result: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Récupère la valeur ou retourne la valeur par défaut."""
        return self.value if self.success and self.value is not None else default


class AppError(Exception):
    """Erreur de base pour l'application."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ExtractionError(AppError):
    """Erreur lors de l'extraction de documents."""

    pass


class GenerationError(AppError):
    """Erreur lors de la génération de contenu."""

    pass


class RenderError(AppError):
    """Erreur lors du rendu de template."""

    pass


class ValidationError(AppError):
    """Erreur de validation de données."""

    pass


class ConfigError(AppError):
    """Erreur de configuration."""

    pass


class OllamaError(GenerationError):
    """Erreur spécifique à Ollama."""

    pass


class TimeoutError(AppError):
    """Erreur de timeout."""

    pass


def safe_call(func: Callable[..., T], *args, **kwargs) -> Result[T]:
    """
    Exécute une fonction et capture les exceptions dans un Result.
    
    Args:
        func: Fonction à exécuter
        *args: Arguments positionnels
        **kwargs: Arguments nommés
        
    Returns:
        Result[T] avec la valeur ou l'erreur
    """
    try:
        value = func(*args, **kwargs)
        return Result.ok(value)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        return Result.fail(AppError(error_msg))
