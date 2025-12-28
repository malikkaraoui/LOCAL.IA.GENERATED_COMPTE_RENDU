# Sprint 2 - Gestion d'erreurs robuste

## 📋 Résumé

Le Sprint 2 introduit une infrastructure de gestion d'erreurs moderne basée sur le pattern **Result[T]**, un système de **logging structuré** et une **validation de configuration** avec Pydantic.

## ✅ Livrables complétés

### 1. Pattern Result[T] (`core/errors.py`)
- **Type générique** `Result[T]` pour gestion d'erreurs fonctionnelle
- **Méthodes chaînables** : `map()`, `and_then()`, `unwrap()`, `unwrap_or()`
- **Factory methods** : `Result.ok(value)`, `Result.fail(error)`
- **Wrapper** `safe_call()` pour convertir exceptions → Result
- **Hiérarchie d'erreurs** : `AppError` → `ExtractionError`, `GenerationError`, `OllamaError`, `ValidationError`, `ConfigError`, `RenderError`, `TimeoutError`

### 2. Logging structuré (`core/logger.py`)
- **Formatters** : `ColoredFormatter` (console ANSI), `JsonFormatter` (logs machine)
- **Configuration** : `setup_logging()` avec rotation de fichiers
- **Module-level verbosity** : `MODULE_LEVELS` dict pour contrôle granulaire
- **Helper** : `get_logger(name)` pour obtenir un logger configuré

### 3. Validation de configuration (`core/validation.py`)
- **Pydantic v2** models avec validators
- **OllamaConfig** : validation host URL, température/top_p 0-1, timeout, retries
- **ExtractConfig** : validation chunk overlap < chunk_size, patterns d'exclusion
- **RenderConfig** : vérification existence template, création auto output_dir
- **AppConfig** : configuration globale avec load_config() JSON/YAML

### 4. Intégration dans extract.py
- ✅ `extract_pdf()` → `Result[dict]` avec logging DEBUG
- ✅ `extract_docx()` → `Result[dict]` avec gestion tables
- ✅ `extract_txt()` → `Result[dict]` avec détection encodage
- ✅ `extract_via_soffice()` → `Result[dict]` avec erreurs explicites
- ✅ `extract_sources()` adapté pour gérer Result pattern

### 5. Intégration dans generate.py
- ✅ `ollama_generate()` → `Result[str]` avec timeout configurable
- ✅ `check_llm_status()` → `Result[str]` au lieu de `tuple[bool, str]`
- ✅ Gestion retry avec logging des échecs
- ✅ Imports `URLError`, `HTTPError` pour distinguer erreurs réseau

### 6. Tests complets
- ✅ **20 tests** pour `core/errors.py` (95% couverture)
  - Result.ok/fail, map/and_then, unwrap/unwrap_or
  - safe_call avec exceptions
  - Hiérarchie d'erreurs
  - Chaînage complexe
- ✅ **Adaptation** de 8 fichiers de tests existants pour Result pattern
- ✅ **194 tests** passent au total (+20 nouveaux)
- ✅ **Couverture** : 50% (up from 28%, +78% increase)

## 📊 Métriques

| Métrique | Avant Sprint 2 | Après Sprint 2 | Amélioration |
|----------|----------------|----------------|--------------|
| **Tests passants** | 174 | 194 | +20 (+11%) |
| **Couverture globale** | 28% | 50% | +22 pts |
| **Modules core** | 11 | 14 | +3 (errors, logger, validation) |
| **Lignes de code** | ~950 | ~1079 | +129 (+14%) |
| **Gestion d'erreurs** | Exceptions | Result pattern | ✅ |

## 🔧 Utilisation

### Pattern Result

```python
from core.errors import Result, ExtractionError
from core.extract import extract_pdf

# Utilisation avec unwrap_or (valeur par défaut)
result = extract_pdf(path)
text = result.unwrap_or({"text": "", "pages": None})

# Utilisation avec chaînage
result = (
    extract_pdf(path)
    .map(lambda data: data["text"])
    .map(lambda text: text.upper())
)
if result.success:
    print(result.value)

# Vérification explicite
result = extract_pdf(path)
if result.success:
    data = result.value
    print(f"Extrait : {len(data['text'])} caractères")
else:
    print(f"Erreur : {result.error}")
```

### Logging structuré

```python
from core.logger import setup_logging, get_logger

# Configuration (à faire une seule fois)
setup_logging(
    log_file="logs/app.log",
    console_level="INFO",
    file_level="DEBUG",
    format_json=True  # JSON pour les logs fichier
)

# Utilisation
LOG = get_logger("mon_module")
LOG.info("Opération démarrée", extra={"user": "malik"})
LOG.debug("Détails techniques", extra={"count": 42})
LOG.error("Erreur", exc_info=True)
```

### Validation config

```python
from core.validation import AppConfig, load_config

# Charger config depuis fichier
config = load_config("config.json")

# Accès avec validation automatique
assert 0 <= config.ollama.temperature <= 1  # Validé par pydantic
assert config.extract.chunk_overlap < config.extract.chunk_size

# Validation manuelle
from core.validation import OllamaConfig
try:
    ollama = OllamaConfig(
        host="http://localhost:11434",
        temperature=1.5  # ❌ ERREUR : > 1
    )
except ValidationError as e:
    print(e)
```

## 🔄 Migrations nécessaires

### Pour les appelants de extract_pdf/docx/txt :
```python
# ❌ AVANT
data = extract_pdf(path)
text = data["text"]

# ✅ APRÈS
result = extract_pdf(path)
if result.success:
    text = result.value["text"]
else:
    print(f"Erreur : {result.error}")
```

### Pour check_llm_status :
```python
# ❌ AVANT
success, message = check_llm_status(host, model)
if success:
    print(message)

# ✅ APRÈS
result = check_llm_status(host, model)
if result.success:
    print(result.value)
else:
    print(f"Erreur : {result.error}")
```

## 🐛 Bugs corrigés

1. **unwrap()** levait `ValueError` au lieu de `AppError` → corrigé
2. **safe_call()** retournait `Result.fail(str)` au lieu de `Result.fail(AppError)` → corrigé
3. **Tests** utilisaient `result["text"]` au lieu de `result.value["text"]` → 8 fichiers adaptés

## 📈 Prochaines étapes (Sprint 3+)

- [ ] Tests pour `core/logger.py` (actuellement 30% couverture)
- [ ] Tests pour `core/validation.py` (actuellement 0% couverture)
- [ ] Intégration logging dans `render.py` et `build_context.py`
- [ ] Métriques de performance (temps d'extraction, retry count)
- [ ] Configuration des niveaux de log via fichier config
- [ ] Retry automatique avec backoff exponentiel pour Ollama

## 🎯 Objectifs atteints

✅ Pattern Result[T] fonctionnel et testé  
✅ Logging structuré avec formatters multiples  
✅ Validation Pydantic pour configs  
✅ Intégration dans extract.py (4 fonctions)  
✅ Intégration dans generate.py (2 fonctions)  
✅ 20 nouveaux tests (95% couverture errors.py)  
✅ Couverture globale +22 points (28% → 50%)  
✅ 194 tests passants  
✅ Documentation complète  

---

**Date** : 2024  
**Sprint** : 2 / 5  
**Statut** : ✅ COMPLÉTÉ
