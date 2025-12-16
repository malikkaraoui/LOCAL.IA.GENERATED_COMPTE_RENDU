"""Tests pour le module errors.py (Pattern Result)."""

import pytest
from core.errors import (
    Result,
    AppError,
    ExtractionError,
    GenerationError,
    OllamaError,
    safe_call,
)


class TestResultPattern:
    """Tests pour la classe Result[T]."""

    def test_ok_creates_success_result(self):
        """Result.ok crée un résultat de succès."""
        result = Result.ok("valeur")
        assert result.success is True
        assert result.value == "valeur"
        assert result.error is None

    def test_fail_creates_failure_result(self):
        """Result.fail crée un résultat d'échec."""
        error = AppError("erreur test")
        result = Result.fail(error)
        assert result.success is False
        assert result.error == error
        assert result.value is None

    def test_unwrap_returns_value_on_success(self):
        """unwrap() retourne la valeur si succès."""
        result = Result.ok(42)
        assert result.unwrap() == 42

    def test_unwrap_raises_on_failure(self):
        """unwrap() lève l'erreur si échec."""
        error = AppError("échec")
        result = Result.fail(error)
        with pytest.raises(AppError, match="échec"):
            result.unwrap()

    def test_unwrap_or_returns_value_on_success(self):
        """unwrap_or() retourne la valeur si succès."""
        result = Result.ok("valeur")
        assert result.unwrap_or("défaut") == "valeur"

    def test_unwrap_or_returns_default_on_failure(self):
        """unwrap_or() retourne la valeur par défaut si échec."""
        result = Result.fail(AppError("erreur"))
        assert result.unwrap_or("défaut") == "défaut"

    def test_map_transforms_success_value(self):
        """map() transforme la valeur si succès."""
        result = Result.ok(10)
        mapped = result.map(lambda x: x * 2)
        assert mapped.success is True
        assert mapped.value == 20

    def test_map_preserves_failure(self):
        """map() préserve l'échec sans appliquer la fonction."""
        error = AppError("erreur")
        result: Result[int] = Result.fail(error)
        mapped = result.map(lambda x: x * 2)
        assert mapped.success is False
        assert mapped.error == error

    def test_and_then_chains_successful_operations(self):
        """and_then() chaîne des opérations qui réussissent."""
        result = Result.ok(5)
        chained = result.and_then(lambda x: Result.ok(x + 10))
        assert chained.success is True
        assert chained.value == 15

    def test_and_then_short_circuits_on_failure(self):
        """and_then() court-circuite si échec."""
        error = AppError("erreur initiale")
        result: Result[int] = Result.fail(error)
        chained = result.and_then(lambda x: Result.ok(x + 10))
        assert chained.success is False
        assert chained.error == error

    def test_and_then_propagates_second_failure(self):
        """and_then() propage l'échec de la seconde opération."""
        result = Result.ok(5)
        new_error = GenerationError("échec dans chaîne")
        chained = result.and_then(lambda x: Result.fail(new_error))
        assert chained.success is False
        assert chained.error == new_error


class TestSafeCall:
    """Tests pour le wrapper safe_call."""

    def test_safe_call_returns_ok_on_success(self):
        """safe_call retourne Result.ok si la fonction réussit."""
        def add(a: int, b: int) -> int:
            return a + b

        result = safe_call(add, 2, 3)
        assert result.success is True
        assert result.value == 5

    def test_safe_call_returns_fail_on_exception(self):
        """safe_call retourne Result.fail si la fonction lève une exception."""
        def divide(a: int, b: int) -> float:
            return a / b

        result = safe_call(divide, 10, 0)
        assert result.success is False
        assert isinstance(result.error, AppError)
        assert "division by zero" in str(result.error).lower()

    def test_safe_call_with_kwargs(self):
        """safe_call fonctionne avec des arguments nommés."""
        def greet(name: str, prefix: str = "Hello") -> str:
            return f"{prefix}, {name}!"

        result = safe_call(greet, "World", prefix="Bonjour")
        assert result.success is True
        assert result.value == "Bonjour, World!"


class TestErrorHierarchy:
    """Tests pour la hiérarchie d'erreurs."""

    def test_extraction_error_is_app_error(self):
        """ExtractionError hérite de AppError."""
        error = ExtractionError("erreur extraction")
        assert isinstance(error, AppError)
        assert str(error) == "erreur extraction"

    def test_generation_error_is_app_error(self):
        """GenerationError hérite de AppError."""
        error = GenerationError("erreur génération")
        assert isinstance(error, AppError)
        assert str(error) == "erreur génération"

    def test_ollama_error_is_app_error(self):
        """OllamaError hérite de AppError."""
        error = OllamaError("erreur Ollama")
        assert isinstance(error, AppError)
        assert str(error) == "erreur Ollama"

    def test_different_error_types_are_distinct(self):
        """Les différents types d'erreurs sont distincts."""
        extraction = ExtractionError("extraction")
        generation = GenerationError("generation")
        ollama = OllamaError("ollama")

        assert type(extraction) != type(generation)
        assert type(generation) != type(ollama)
        assert type(extraction) != type(ollama)


class TestResultChaining:
    """Tests pour le chaînage complexe de Result."""

    def test_complex_chain_all_success(self):
        """Chaînage complexe avec toutes les opérations qui réussissent."""
        result = (
            Result.ok(10)
            .map(lambda x: x * 2)
            .and_then(lambda x: Result.ok(x + 5))
            .map(lambda x: str(x))
        )
        assert result.success is True
        assert result.value == "25"

    def test_complex_chain_fails_at_second_step(self):
        """Chaînage qui échoue à la deuxième étape."""
        error = AppError("échec milieu")
        result = (
            Result.ok(10)
            .map(lambda x: x * 2)
            .and_then(lambda x: Result.fail(error))
            .map(lambda x: str(x))  # Ne devrait jamais être appelé
        )
        assert result.success is False
        assert result.error == error
