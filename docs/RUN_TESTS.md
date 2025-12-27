# Guide d'Exécution - Tests DoD

## Installation des dépendances

```bash
# Dépendances minimales pour tests unitaires
pip install pytest pytest-mock

# Dépendances pour tests E2E (optionnel)
pip install python-docx
```

## Exécution

### Tests Unitaires (RECOMMANDÉ)

```bash
# Tous les tests unitaires
pytest tests/test_validation_profiles.py -v

# Tests avec détails
pytest tests/test_validation_profiles.py -v --tb=short

# Un profil spécifique
pytest tests/test_validation_profiles.py::test_validation_strict_profile -v

# Tests rapides (sans coverage)
pytest tests/test_validation_profiles.py -v --no-cov
```

**Résultat attendu** :
```
============================== 14 passed in 0.24s ==============================
```

### Tests E2E (OPTIONNEL)

```bash
# Tous les tests E2E
pytest tests/test_end2end_one_client.py -v

# Test spécifique
pytest tests/test_end2end_one_client.py::test_end2end_pipeline_complete -v

# Avec le marker e2e
pytest tests/ -v -m e2e
```

**Note** : Les tests E2E seront **SKIPPED** si les dépendances ne sont pas installées. C'est normal.

### Tous les tests DoD

```bash
# Tests unitaires + E2E
pytest tests/test_validation_profiles.py tests/test_end2end_one_client.py -v
```

## Vérification rapide

```bash
# Lancer uniquement les tests unitaires (toujours disponibles)
cd /path/to/SCRIPT.IA
pytest tests/test_validation_profiles.py -v
```

Si vous voyez `14 passed`, c'est ✅ **BON** !

## Debugging

### Test échoue ?

```bash
# Voir le traceback complet
pytest tests/test_validation_profiles.py -v --tb=long

# Voir les valeurs
pytest tests/test_validation_profiles.py -v -s
```

### Test lent ?

```bash
# Profiler les tests
pytest tests/test_validation_profiles.py --durations=10
```

## Intégration Continue

Ajoutez à votre CI/CD :

```yaml
# GitHub Actions / GitLab CI
- name: Run DoD Tests
  run: pytest tests/test_validation_profiles.py -v --tb=short
```

---

**Temps total** : < 1 seconde pour tests unitaires  
**Pré-requis** : pytest, pytest-mock
