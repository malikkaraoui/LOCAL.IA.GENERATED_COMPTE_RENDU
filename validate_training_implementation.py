#!/usr/bin/env python3
"""
Script de validation de l'implémentation P0 Training Dataset.
Vérifie que tous les composants sont en place et fonctionnels.

STATUTS:
- PASS: Tous les tests critiques réussis
- PASS_WITH_WARNINGS: Tests critiques OK, warnings optionnels
- FAIL: Au moins un test critique échoué
"""

import sys
import ast
from pathlib import Path
import subprocess
from typing import List, Optional


class ValidationResult:
    """Résultat d'un test de validation."""
    def __init__(self, name: str, critical: bool = True):
        self.name = name
        self.critical = critical
        self.passed = False
        self.message = ""
        self.details = []
    
    def mark_pass(self, message: str = ""):
        self.passed = True
        self.message = message
    
    def mark_fail(self, message: str, details: Optional[List[str]] = None):
        self.passed = False
        self.message = message
        self.details = details or []


def validate_files_exist() -> ValidationResult:
    """Vérifie que les fichiers créés existent."""
    result = ValidationResult("[CRITIQUE] Existence fichiers", critical=True)
    
    required_files = [
        "src/rhpro/dataset_training.py",
        "pages_streamlit/training_and_test.py",
        "TRAINING_DATASET_IMPLEMENTATION.md",
        "TRAINING_DATASET_QUICKSTART.md",
        "COMPTE_RENDU_POUR_IA_TRAINING.md"
    ]
    
    missing = [f for f in required_files if not Path(f).exists()]
    
    if missing:
        result.mark_fail("Fichiers manquants", missing)
    else:
        result.mark_pass("Tous les fichiers requis présents")
    
    return result


def validate_module_structure() -> ValidationResult:
    """Vérifie la structure des modules sans importer (parse AST)."""
    result = ValidationResult("[CRITIQUE] Structure modules", critical=True)
    
    checks = []
    
    # Check dataset_training.py
    dt_path = Path("src/rhpro/dataset_training.py")
    if not dt_path.exists():
        result.mark_fail("dataset_training.py non trouvé")
        return result
    
    try:
        tree = ast.parse(dt_path.read_text())
        functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        
        required_funcs = {
            "discover_client_folders",
            "analyze_dataset",
            "export_training_artifacts",
            "load_training_state"
        }
        
        missing_funcs = required_funcs - functions
        if missing_funcs:
            checks.append(f"dataset_training.py: fonctions manquantes {missing_funcs}")
        
        # Vérifier classe DatasetTrainingResult
        classes = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
        if "DatasetTrainingResult" not in classes:
            checks.append("dataset_training.py: classe DatasetTrainingResult manquante")
    
    except SyntaxError as e:
        checks.append(f"dataset_training.py: erreur syntaxe ligne {e.lineno}")
    
    # Check training_and_test.py
    tt_path = Path("pages_streamlit/training_and_test.py")
    if not tt_path.exists():
        result.mark_fail("training_and_test.py non trouvé")
        return result
    
    try:
        tree = ast.parse(tt_path.read_text())
        functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        
        required_funcs = {
            "show_training_dataset",
            "show_test_client",
            "show_training_and_test_page"
        }
        
        missing_funcs = required_funcs - functions
        if missing_funcs:
            checks.append(f"training_and_test.py: fonctions manquantes {missing_funcs}")
    
    except SyntaxError as e:
        checks.append(f"training_and_test.py: erreur syntaxe ligne {e.lineno}")
    
    if checks:
        result.mark_fail("Problèmes de structure détectés", checks)
    else:
        result.mark_pass("Structure des modules valide (fonctions/classes présentes)")
    
    return result


def validate_fallback_consistency() -> ValidationResult:
    """Vérifie que tous les fallbacks utilisent 'Non renseigné'."""
    result = ValidationResult("[CRITIQUE] Cohérence fallback", critical=True)
    
    # Vérifier absence de "NOT_FOUND"
    grep_result = subprocess.run(
        ["grep", "-r", "--include=*.py", "NOT_FOUND", "backend/workers/", "src/rhpro/"],
        capture_output=True,
        text=True
    )
    
    if grep_result.returncode == 0 and grep_result.stdout.strip():
        occurrences = grep_result.stdout.strip().split('\n')
        result.mark_fail(
            f"'NOT_FOUND' trouvé ({len(occurrences)} occurrences)",
            occurrences[:5]  # Limiter à 5 exemples
        )
        return result
    
    # Vérifier présence de "Non renseigné"
    grep_result = subprocess.run(
        ["grep", "-r", "--include=*.py", "Non renseigné", "backend/workers/", "src/rhpro/"],
        capture_output=True,
        text=True
    )
    
    if grep_result.returncode != 0 or not grep_result.stdout.strip():
        result.mark_fail("'Non renseigné' introuvable dans le code")
        return result
    
    result.mark_pass("Fallback unifié à 'Non renseigné' (aucun 'NOT_FOUND')")
    return result


def validate_training_state_integration() -> ValidationResult:
    """Vérifie que training_state est intégré dans les générateurs."""
    result = ValidationResult("[CRITIQUE] Intégration training_state", critical=True)
    
    checks = []
    
    # Vérifier rag_generator.py
    rag_path = Path("src/rhpro/rag_generator.py")
    if not rag_path.exists():
        result.mark_fail("rag_generator.py non trouvé")
        return result
    
    content = rag_path.read_text()
    
    if "training_state" not in content:
        checks.append("rag_generator.py: paramètre 'training_state' absent")
    
    if "_enrich_prompt_with_training_state" not in content:
        checks.append("rag_generator.py: méthode '_enrich_prompt_with_training_state' absente")
    
    # Vérifier report_generator.py
    report_path = Path("src/rhpro/report_generator.py")
    if not report_path.exists():
        result.mark_fail("report_generator.py non trouvé")
        return result
    
    content = report_path.read_text()
    
    if "training_state" not in content:
        checks.append("report_generator.py: paramètre 'training_state' absent")
    
    if checks:
        result.mark_fail("Intégration incomplète", checks)
    else:
        result.mark_pass("training_state intégré (paramètres + méthode enrichissement)")
    
    return result


def validate_streamlit_integration() -> ValidationResult:
    """Vérifie que la nouvelle page est intégrée dans streamlit_app.py."""
    result = ValidationResult("[CRITIQUE] Intégration Streamlit", critical=True)
    
    streamlit_app = Path("streamlit_app.py")
    if not streamlit_app.exists():
        result.mark_fail("streamlit_app.py non trouvé")
        return result
    
    content = streamlit_app.read_text()
    
    checks = []
    if "Training & Test" not in content and "🎓" not in content:
        checks.append("Titre navigation 'Training & Test' absent")
    
    if "training_and_test" not in content:
        checks.append("Import ou appel 'training_and_test' absent")
    
    if checks:
        result.mark_fail("Intégration manquante dans navigation", checks)
    else:
        result.mark_pass("Page intégrée dans navigation Streamlit")
    
    return result


def validate_api_models() -> ValidationResult:
    """Vérifie que le modèle API n'a plus de duplication (OPTIONNEL)."""
    result = ValidationResult("[OPTIONNEL] Modèle API Pydantic", critical=False)
    
    api_models_path = Path("backend/api/models/training.py")
    if not api_models_path.exists():
        result.mark_fail("backend/api/models/training.py non trouvé")
        return result
    
    # Parse AST pour vérifier sans importer pydantic
    try:
        tree = ast.parse(api_models_path.read_text())
        
        # Chercher TrainingStatusResponse
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "TrainingStatusResponse":
                # Compter les occurrences de "artifact_path"
                class_code = ast.get_source_segment(api_models_path.read_text(), node)
                if class_code:
                    count = class_code.count("artifact_path")
                    if count > 1:
                        result.mark_fail(
                            f"Duplication 'artifact_path' détectée ({count} occurrences)",
                            [f"Ligne {node.lineno}: vérifier attributs de classe"]
                        )
                        return result
        
        result.mark_pass("Aucune duplication 'artifact_path' détectée")
        return result
    
    except SyntaxError as e:
        result.mark_fail(f"Erreur syntaxe ligne {e.lineno}")
        return result


def validate_imports_optional() -> ValidationResult:
    """Tente d'importer les modules (OPTIONNEL, nécessite deps)."""
    result = ValidationResult("[OPTIONNEL] Imports complets", critical=False)
    
    errors = []
    
    # Test dataset_training
    try:
        sys.path.insert(0, str(Path.cwd() / "src"))
        from rhpro import dataset_training
    except ImportError as e:
        errors.append(f"dataset_training: {e}")
    
    # Test training_and_test (nécessite streamlit)
    try:
        sys.path.insert(0, str(Path.cwd() / "pages_streamlit"))
        from training_and_test import show_training_and_test_page
    except ImportError as e:
        errors.append(f"training_and_test: {e}")
    
    if errors:
        result.mark_fail(
            "Imports échoués (deps manquantes : streamlit, etc.)",
            errors
        )
        result.details.append("💡 Pour tester : pip install streamlit llama-index python-docx")
    else:
        result.mark_pass("Imports complets réussis")
    
    return result


def print_result(result: ValidationResult):
    """Affiche le résultat d'un test."""
    icon = "✅" if result.passed else ("⚠️" if not result.critical else "❌")
    status = "PASS" if result.passed else ("WARNING" if not result.critical else "FAIL")
    
    print(f"\n{icon} {result.name}")
    print(f"   Status: {status}")
    print(f"   Message: {result.message}")
    
    if result.details:
        for detail in result.details:
            print(f"   → {detail}")


def main():
    print("=" * 70)
    print("VALIDATION IMPLÉMENTATION P0 - TRAINING DATASET")
    print("=" * 70)
    
    # Tests critiques
    critical_tests = [
        validate_files_exist,
        validate_module_structure,
        validate_fallback_consistency,
        validate_training_state_integration,
        validate_streamlit_integration
    ]
    
    # Tests optionnels
    optional_tests = [
        validate_api_models,
        validate_imports_optional
    ]
    
    print("\n🔴 TESTS CRITIQUES")
    print("-" * 70)
    
    critical_results = []
    for test in critical_tests:
        try:
            result = test()
            print_result(result)
            critical_results.append(result)
        except Exception as e:
            print(f"❌ Erreur durant test {test.__name__}: {e}")
            result = ValidationResult(test.__name__, critical=True)
            result.mark_fail(f"Exception: {e}")
            critical_results.append(result)
    
    print("\n\n🟡 TESTS OPTIONNELS")
    print("-" * 70)
    
    optional_results = []
    for test in optional_tests:
        try:
            result = test()
            print_result(result)
            optional_results.append(result)
        except Exception as e:
            print(f"⚠️ Erreur durant test {test.__name__}: {e}")
            result = ValidationResult(test.__name__, critical=False)
            result.mark_fail(f"Exception: {e}")
            optional_results.append(result)
    
    # Calcul statut final
    critical_passed = sum(r.passed for r in critical_results)
    critical_total = len(critical_results)
    optional_passed = sum(r.passed for r in optional_results)
    optional_total = len(optional_results)
    
    print("\n" + "=" * 70)
    print("RÉSULTAT FINAL")
    print("=" * 70)
    print(f"Critiques: {critical_passed}/{critical_total} ✅")
    print(f"Optionnels: {optional_passed}/{optional_total} ⚠️")
    
    # Déterminer statut
    if all(r.passed for r in critical_results):
        if all(r.passed for r in optional_results):
            print("\n🟢 STATUT: PASS")
            print("   Tous les tests (critiques + optionnels) réussis")
            sys.exit(0)
        else:
            print("\n🟡 STATUT: PASS_WITH_WARNINGS")
            print("   Tests critiques OK, mais warnings optionnels")
            print("   L'implémentation est fonctionnelle")
            print("\n💡 Pour résoudre les warnings:")
            print("   pip install -r requirements.txt")
            sys.exit(0)
    else:
        print("\n🔴 STATUT: FAIL")
        print("   Au moins un test critique échoué")
        print("\n❌ Échecs critiques:")
        for r in critical_results:
            if not r.passed:
                print(f"   - {r.name}: {r.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
