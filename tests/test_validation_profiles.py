"""
Test de validation des profils GO/NO_GO/DRAFT - Definition of Done.

Contraintes :
- 100% déterministe, rapide, local
- Aucun appel réseau
- Données fictives générées dans tmp_path
- Vérification cohérence status vs métriques

Tests :
- Profile STRICT : seuils élevés, champs critiques obligatoires
- Profile STANDARD : seuils moyens
- Profile DRAFT : pas de blocage
- Vérification reasons + actions
"""
import json
import pytest
from pathlib import Path
from typing import Dict, Any

from src.rhpro.validation_profiles import (
    validate_report,
    ValidationProfile,
    ValidationStatus,
)


@pytest.fixture
def create_validation_files(tmp_path):
    """
    Factory pour créer des fichiers metrics.json et debug.json fictifs.
    
    Returns:
        Fonction callable(metrics_data, debug_data) -> (metrics_path, debug_path)
    """
    def _create_files(
        metrics_data: Dict[str, Any],
        debug_data: Dict[str, Any]
    ) -> tuple[Path, Path, Path]:
        """Crée les fichiers JSON et retourne leurs chemins."""
        metrics_path = tmp_path / "test_metrics.json"
        debug_path = tmp_path / "test_debug.json"
        meta_path = tmp_path / "test_meta.json"
        
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, indent=2)
        
        with open(debug_path, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2)
        
        # Créer meta.json avec gold_score pour éviter blocage en STRICT
        meta_data = {
            "gold_score": 0.85,  # Bon score par défaut
            "sources_rag": ["source1.pdf", "source2.pdf"],
            "timestamp": "2025-12-27T10:00:00",
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, indent=2)
        
        return metrics_path, debug_path, meta_path
    
    return _create_files


def create_metrics(
    required_coverage: float = 85.0,
    quality_score: float = 0.75,
    avg_confidence: float = 0.7,
) -> Dict[str, Any]:
    """Crée un dictionnaire metrics standard."""
    return {
        "timestamp": "2025-12-27T10:00:00",
        "required_coverage": required_coverage,
        "weighted_coverage": required_coverage - 5,  # Légèrement moins
        "quality_score": quality_score,
        "avg_confidence": avg_confidence,
        "total_fields": 20,
        "filled_fields": int(20 * required_coverage / 100),
        "required_fields": 10,
        "required_filled": int(10 * required_coverage / 100),
    }


def create_debug(
    nom_value: str = "DUPONT",
    prenom_value: str = "Jean",
    profession_value: str = "Conseiller en orientation",
    formation_value: str = "Master en psychologie",
    sources_count: int = 3,
) -> Dict[str, Any]:
    """Crée un dictionnaire debug standard avec evidence."""
    fields = {}
    
    # Identité
    if nom_value and nom_value != "Non renseigné":
        fields["nom"] = {
            "value": nom_value,
            "evidence": [{"source": "CV.pdf", "text": f"{nom_value}", "score": 0.9}],
            "confidence": 0.9,
        }
    else:
        fields["nom"] = {
            "value": "Non renseigné",
            "evidence": [],
            "confidence": 0.0,
        }
    
    if prenom_value and prenom_value != "Non renseigné":
        fields["prenom"] = {
            "value": prenom_value,
            "evidence": [{"source": "CV.pdf", "text": f"{prenom_value}", "score": 0.9}],
            "confidence": 0.9,
        }
    else:
        fields["prenom"] = {
            "value": "Non renseigné",
            "evidence": [],
            "confidence": 0.0,
        }
    
    # Profession
    if profession_value and profession_value != "Non renseigné":
        fields["situation_professionnelle"] = {
            "value": profession_value,
            "evidence": [{"source": "CV.pdf", "text": profession_value, "score": 0.85}],
            "confidence": 0.85,
        }
    else:
        fields["situation_professionnelle"] = {
            "value": "Non renseigné",
            "evidence": [],
            "confidence": 0.0,
        }
    
    # Formation
    if formation_value and formation_value != "Non renseigné":
        fields["niveau_formation"] = {
            "value": formation_value,
            "evidence": [{"source": "CV.pdf", "text": formation_value, "score": 0.85}],
            "confidence": 0.85,
        }
    else:
        fields["niveau_formation"] = {
            "value": "Non renseigné",
            "evidence": [],
            "confidence": 0.0,
        }
    
    # AVS
    fields["numero_avs"] = {
        "value": "Non renseigné / à confirmer",
        "evidence": [],
        "confidence": 0.0,
    }
    
    return {
        "timestamp": "2025-12-27T10:00:00",
        "fields": fields,
        "index": {
            "sources_count": sources_count,
            "sources": [{"file": f"source_{i}.pdf", "extension": ".pdf"} for i in range(sources_count)],
        },
    }


# ============================================================================
# Tests paramétrés : Profile STRICT
# ============================================================================

@pytest.mark.parametrize("test_case,metrics_data,debug_data,expected_status,expected_reasons_keywords", [
    # CAS 1 : Tout OK → GO
    (
        "strict_all_ok",
        create_metrics(required_coverage=90.0, quality_score=0.80, avg_confidence=0.75),
        create_debug(
            nom_value="DUPONT",
            prenom_value="Jean",
            profession_value="Conseiller",
            formation_value="Master",
            sources_count=3,
        ),
        ValidationStatus.GO,
        [],  # Pas de raisons d'échec
    ),
    
    # CAS 2 : Identité manquante (nom) → NO_GO
    (
        "strict_missing_nom",
        create_metrics(required_coverage=90.0, quality_score=0.80, avg_confidence=0.75),
        create_debug(
            nom_value="Non renseigné",  # NOM MANQUANT
            prenom_value="Jean",
            profession_value="Conseiller",
            formation_value="Master",
            sources_count=3,
        ),
        ValidationStatus.NO_GO,
        ["missing_critical_fields", "nom"],
    ),
    
    # CAS 3 : Identité manquante (prénom) → NO_GO
    (
        "strict_missing_prenom",
        create_metrics(required_coverage=90.0, quality_score=0.80, avg_confidence=0.75),
        create_debug(
            nom_value="DUPONT",
            prenom_value="Non renseigné",  # PRENOM MANQUANT
            profession_value="Conseiller",
            formation_value="Master",
            sources_count=3,
        ),
        ValidationStatus.NO_GO,
        ["missing_critical_fields", "prenom"],
    ),
    
    # CAS 4 : Aucune source → NO_GO
    (
        "strict_no_sources",
        create_metrics(required_coverage=90.0, quality_score=0.80, avg_confidence=0.75),
        create_debug(
            nom_value="DUPONT",
            prenom_value="Jean",
            profession_value="Conseiller",
            formation_value="Master",
            sources_count=0,  # AUCUNE SOURCE
        ),
        ValidationStatus.NO_GO,
        ["insufficient_sources"],
    ),
    
    # CAS 5 : Ni profession ni formation → NO_GO
    (
        "strict_no_profession_no_formation",
        create_metrics(required_coverage=90.0, quality_score=0.80, avg_confidence=0.75),
        create_debug(
            nom_value="DUPONT",
            prenom_value="Jean",
            profession_value="Non renseigné",  # PROFESSION MANQUANTE
            formation_value="Non renseigné",   # FORMATION MANQUANTE
            sources_count=3,
        ),
        ValidationStatus.NO_GO,
        ["profession_or_formation"],
    ),
    
    # CAS 6 : Coverage trop faible → NO_GO
    (
        "strict_low_coverage",
        create_metrics(required_coverage=70.0, quality_score=0.80, avg_confidence=0.75),  # 70% < 85%
        create_debug(
            nom_value="DUPONT",
            prenom_value="Jean",
            profession_value="Conseiller",
            formation_value="Master",
            sources_count=3,
        ),
        ValidationStatus.NO_GO,
        ["low_required_coverage"],
    ),
    
    # CAS 7 : Quality score trop faible → NO_GO
    (
        "strict_low_quality",
        create_metrics(required_coverage=90.0, quality_score=0.60, avg_confidence=0.75),  # 0.60 < 0.75
        create_debug(
            nom_value="DUPONT",
            prenom_value="Jean",
            profession_value="Conseiller",
            formation_value="Master",
            sources_count=3,
        ),
        ValidationStatus.NO_GO,
        ["low_quality_score"],
    ),
    
    # CAS 8 : Confiance trop faible → NO_GO
    (
        "strict_low_confidence",
        create_metrics(required_coverage=90.0, quality_score=0.80, avg_confidence=0.50),  # 0.50 < 0.70
        create_debug(
            nom_value="DUPONT",
            prenom_value="Jean",
            profession_value="Conseiller",
            formation_value="Master",
            sources_count=3,
        ),
        ValidationStatus.NO_GO,
        ["low_confidence"],
    ),
])
def test_validation_strict_profile(
    test_case,
    metrics_data,
    debug_data,
    expected_status,
    expected_reasons_keywords,
    create_validation_files,
):
    """
    Test profile STRICT avec différents scénarios.
    
    Vérifie :
    - Status attendu (GO/NO_GO)
    - Présence des raisons attendues
    - Cohérence actions vs raisons
    """
    # Créer les fichiers
    metrics_path, debug_path, meta_path = create_validation_files(metrics_data, debug_data)
    
    # Valider
    result = validate_report(
        metrics_path=metrics_path,
        debug_path=debug_path,
        meta_path=meta_path,
        profile=ValidationProfile.STRICT,
    )
    
    # Vérifications
    assert result.status == expected_status.value, (
        f"[{test_case}] Status attendu: {expected_status.value}, obtenu: {result.status}"
    )
    
    # Vérifier les raisons si NO_GO
    if expected_status == ValidationStatus.NO_GO:
        assert len(result.reasons) > 0, f"[{test_case}] NO_GO doit avoir des raisons"
        
        # Vérifier présence des keywords attendus
        reasons_str = " ".join(result.reasons).lower()
        for keyword in expected_reasons_keywords:
            assert keyword.lower() in reasons_str, (
                f"[{test_case}] Raison attendue '{keyword}' non trouvée dans: {result.reasons}"
            )
        
        # Vérifier présence d'actions
        assert len(result.actions) > 0, f"[{test_case}] NO_GO doit avoir des actions recommandées"
    
    # Si GO, pas de raisons bloquantes
    if expected_status == ValidationStatus.GO:
        # Les raisons peuvent contenir des warnings non bloquants, mais pas d'erreurs critiques
        reasons_str = " ".join(result.reasons).lower()
        assert "missing_critical_fields" not in reasons_str, (
            f"[{test_case}] GO ne doit pas avoir de champs critiques manquants"
        )
    
    # Vérifier cohérence scores vs status (ANTI-REGRESSION : pas de tests light)
    if expected_status == ValidationStatus.GO:
        assert result.scores.get("required_coverage", 0) >= 0.85, (
            f"[{test_case}] GO doit avoir required_coverage >= 0.85"
        )
        assert result.scores.get("quality_score", 0) >= 0.75, (
            f"[{test_case}] GO doit avoir quality_score >= 0.75"
        )
        assert result.scores.get("avg_confidence", 0) >= 0.70, (
            f"[{test_case}] GO doit avoir avg_confidence >= 0.70"
        )


# ============================================================================
# Tests paramétrés : Profile STANDARD
# ============================================================================

@pytest.mark.parametrize("test_case,metrics_data,debug_data,expected_status", [
    # CAS 1 : Seuils STANDARD OK → GO
    (
        "standard_ok",
        create_metrics(required_coverage=80.0, quality_score=0.70, avg_confidence=0.65),
        create_debug(
            nom_value="DUPONT",
            prenom_value="Jean",
            profession_value="Conseiller",
            formation_value="Master",
            sources_count=2,  # 2 sources OK pour STANDARD
        ),
        ValidationStatus.GO,
    ),
    
    # CAS 2 : 1 champ critique manquant OK pour STANDARD (max=1)
    (
        "standard_one_missing_ok",
        create_metrics(required_coverage=80.0, quality_score=0.70, avg_confidence=0.65),
        create_debug(
            nom_value="DUPONT",
            prenom_value="Non renseigné",  # 1 manquant OK
            profession_value="Conseiller",
            formation_value="Master",
            sources_count=2,
        ),
        ValidationStatus.GO,
    ),
    
    # CAS 3 : Coverage trop faible même pour STANDARD → NO_GO
    (
        "standard_low_coverage",
        create_metrics(required_coverage=60.0, quality_score=0.70, avg_confidence=0.65),  # 60% < 75%
        create_debug(
            nom_value="DUPONT",
            prenom_value="Jean",
            profession_value="Conseiller",
            formation_value="Master",
            sources_count=2,
        ),
        ValidationStatus.NO_GO,
    ),
])
def test_validation_standard_profile(
    test_case,
    metrics_data,
    debug_data,
    expected_status,
    create_validation_files,
):
    """
    Test profile STANDARD avec seuils plus bas.
    
    Vérifie :
    - Seuils : coverage >= 75%, quality >= 0.65
    - Max 1 champ critique manquant toléré
    - Min 2 sources
    """
    metrics_path, debug_path, meta_path = create_validation_files(metrics_data, debug_data)
    
    result = validate_report(
        metrics_path=metrics_path,
        debug_path=debug_path,
        meta_path=meta_path,
        profile=ValidationProfile.STANDARD,
    )
    
    assert result.status == expected_status.value, (
        f"[{test_case}] Status attendu: {expected_status.value}, obtenu: {result.status}"
    )
    
    # Vérifier cohérence pour GO (ANTI-REGRESSION)
    if expected_status == ValidationStatus.GO:
        assert result.scores.get("required_coverage", 0) >= 0.75, (
            f"[{test_case}] STANDARD GO doit avoir required_coverage >= 0.75"
        )
        assert result.scores.get("quality_score", 0) >= 0.65, (
            f"[{test_case}] STANDARD GO doit avoir quality_score >= 0.65"
        )


# ============================================================================
# Tests paramétrés : Profile DRAFT
# ============================================================================

@pytest.mark.parametrize("test_case,metrics_data,debug_data", [
    # CAS 1 : Données minimales → DRAFT
    (
        "draft_minimal",
        create_metrics(required_coverage=30.0, quality_score=0.30, avg_confidence=0.30),
        create_debug(
            nom_value="Non renseigné",
            prenom_value="Non renseigné",
            profession_value="Non renseigné",
            formation_value="Non renseigné",
            sources_count=0,
        ),
    ),
    
    # CAS 2 : Bonnes données → DRAFT quand même
    (
        "draft_good_data",
        create_metrics(required_coverage=95.0, quality_score=0.90, avg_confidence=0.85),
        create_debug(
            nom_value="DUPONT",
            prenom_value="Jean",
            profession_value="Conseiller",
            formation_value="Master",
            sources_count=5,
        ),
    ),
])
def test_validation_draft_profile(
    test_case,
    metrics_data,
    debug_data,
    create_validation_files,
):
    """
    Test profile DRAFT : toujours DRAFT, jamais GO/NO_GO bloquant.
    
    Vérifie :
    - Status toujours DRAFT
    - Raisons et actions présentes
    """
    metrics_path, debug_path, meta_path = create_validation_files(metrics_data, debug_data)
    
    result = validate_report(
        metrics_path=metrics_path,
        debug_path=debug_path,
        meta_path=meta_path,
        profile=ValidationProfile.DRAFT,
    )
    
    assert result.status == ValidationStatus.DRAFT.value, (
        f"[{test_case}] DRAFT profile doit toujours retourner DRAFT"
    )
    
    # DRAFT doit avoir au moins une raison
    assert len(result.reasons) > 0, f"[{test_case}] DRAFT doit avoir des raisons"
    
    # DRAFT doit avoir au moins une action
    assert len(result.actions) > 0, f"[{test_case}] DRAFT doit avoir des actions"


# ============================================================================
# Test : Vérification structure result
# ============================================================================

def test_validation_result_structure(create_validation_files):
    """
    Vérifie que le ValidationResult a la structure attendue.
    """
    metrics_data = create_metrics()
    debug_data = create_debug()
    
    metrics_path, debug_path, meta_path = create_validation_files(metrics_data, debug_data)
    
    result = validate_report(
        metrics_path=metrics_path,
        debug_path=debug_path,
        meta_path=meta_path,
        profile=ValidationProfile.STRICT,
    )
    
    # Vérifier attributs obligatoires
    assert hasattr(result, "status"), "ValidationResult doit avoir 'status'"
    assert hasattr(result, "profile"), "ValidationResult doit avoir 'profile'"
    assert hasattr(result, "reasons"), "ValidationResult doit avoir 'reasons'"
    assert hasattr(result, "actions"), "ValidationResult doit avoir 'actions'"
    assert hasattr(result, "scores"), "ValidationResult doit avoir 'scores'"
    
    # Vérifier types
    assert isinstance(result.status, str), "status doit être string"
    assert isinstance(result.reasons, list), "reasons doit être list"
    assert isinstance(result.actions, list), "actions doit être list"
    assert isinstance(result.scores, dict), "scores doit être dict"
    
    # Vérifier scores obligatoires
    assert "required_coverage" in result.scores, "scores doit contenir 'required_coverage'"
    assert "quality_score" in result.scores, "scores doit contenir 'quality_score'"
    assert "avg_confidence" in result.scores, "scores doit contenir 'avg_confidence'"
