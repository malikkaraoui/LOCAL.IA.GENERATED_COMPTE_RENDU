# Guide d'utilisation - Sprint 2 : Gestion d'erreurs robuste

Ce guide explique comment utiliser les nouvelles fonctionnalités introduites dans le Sprint 2.

## Table des matières
1. [Pattern Result[T]](#pattern-resultt)
2. [Logging structuré](#logging-structuré)
3. [Validation de configuration](#validation-de-configuration)
4. [Migration du code existant](#migration-du-code-existant)

---

## Pattern Result[T]

### Qu'est-ce que Result[T] ?

`Result[T]` est un type générique qui représente soit un **succès avec une valeur** (`Result.ok`), soit un **échec avec une erreur** (`Result.fail`). Cela remplace les exceptions pour une gestion d'erreurs **explicite et type-safe**.

### Création de Result

```python
from core.errors import Result, ExtractionError

# Succès
result = Result.ok("valeur réussie")
print(result.success)  # True
print(result.value)    # "valeur réussie"

# Échec
error = ExtractionError("Impossible de lire le fichier")
result = Result.fail(error)
print(result.success)  # False
print(result.error)    # ExtractionError: Impossible de lire le fichier
```

### Utilisation basique

```python
from core.extract import extract_pdf

# Méthode 1 : Vérification explicite
result = extract_pdf(path)
if result.success:
    data = result.value
    print(f"Texte extrait : {len(data['text'])} caractères")
    if data['pages']:
        print(f"Nombre de pages : {len(data['pages'])}")
else:
    print(f"Erreur : {result.error}")
```

### Méthodes utiles

#### unwrap() - Récupérer la valeur (dangereux)
```python
result = extract_pdf(path)
data = result.unwrap()  # ⚠️ Lève une exception si échec
```

#### unwrap_or() - Valeur par défaut (sûr)
```python
result = extract_pdf(path)
data = result.unwrap_or({"text": "", "pages": None})  # Toujours OK
```

#### map() - Transformer la valeur
```python
# Extraire le texte et le mettre en majuscules
result = extract_pdf(path).map(lambda data: data["text"].upper())

if result.success:
    uppercase_text = result.value
```

#### and_then() - Chaîner des opérations
```python
def analyze_text(data: dict) -> Result[int]:
    """Compte le nombre de mots."""
    word_count = len(data["text"].split())
    return Result.ok(word_count)

# Chaînage : extraction → analyse
result = extract_pdf(path).and_then(analyze_text)

if result.success:
    print(f"Nombre de mots : {result.value}")
```

### Exemple complet

```python
from pathlib import Path
from core.extract import extract_pdf, extract_docx, extract_txt
from core.errors import Result

def extract_file(filepath: Path) -> Result[dict]:
    """Extrait un fichier selon son extension."""
    ext = filepath.suffix.lower()
    
    if ext == ".pdf":
        return extract_pdf(filepath)
    elif ext == ".docx":
        return extract_docx(filepath)
    elif ext == ".txt":
        return extract_txt(filepath)
    else:
        from core.errors import ExtractionError
        return Result.fail(ExtractionError(f"Format non supporté : {ext}"))

# Utilisation
filepath = Path("document.pdf")
result = (
    extract_file(filepath)
    .map(lambda data: data["text"])
    .map(lambda text: text.strip())
    .map(lambda text: text[:1000])  # Garder 1000 premiers caractères
)

text = result.unwrap_or("Aucun texte disponible")
print(text)
```

---

## Logging structuré

### Configuration initiale

```python
from core.logger import setup_logging

# Configuration simple (console uniquement)
setup_logging(console_level="INFO")

# Configuration complète (console + fichier)
setup_logging(
    log_file="logs/app.log",
    console_level="INFO",
    file_level="DEBUG",
    format_json=True  # JSON pour logs machine-readable
)
```

### Obtenir un logger

```python
from core.logger import get_logger

LOG = get_logger(__name__)  # Nom du module automatique
# ou
LOG = get_logger("mon_module")
```

### Niveaux de log

```python
LOG.debug("Détails techniques pour debug")
LOG.info("Information normale")
LOG.warning("Avertissement")
LOG.error("Erreur non fatale")
LOG.critical("Erreur fatale")
```

### Logging avec contexte (extra)

```python
# Ajouter des données structurées
LOG.info("Utilisateur connecté", extra={
    "user_id": 42,
    "username": "malik",
    "ip": "192.168.1.1"
})

# En JSON : {"message": "Utilisateur connecté", "user_id": 42, ...}
```

### Logging d'exceptions

```python
try:
    result = risky_operation()
except Exception as exc:
    LOG.error("Opération échouée", exc_info=True)
    # Inclut le traceback complet
```

### Configuration par module

Dans `core/logger.py`, vous pouvez définir des niveaux différents par module :

```python
MODULE_LEVELS = {
    "core.extract": "DEBUG",    # Très verbeux
    "core.generate": "INFO",    # Normal
    "core.render": "WARNING",   # Silencieux sauf problèmes
}
```

---

## Validation de configuration

### Charger une configuration

```python
from core.validation import load_config

# Depuis JSON
config = load_config("config.json")

# Depuis YAML (si PyYAML installé)
config = load_config("config.yaml")
```

### Accéder aux valeurs

```python
# Configuration Ollama
print(config.ollama.host)        # "http://localhost:11434"
print(config.ollama.model)       # "llama2"
print(config.ollama.temperature) # 0.7 (validé 0-1)

# Configuration extraction
print(config.extract.chunk_size)    # 1200
print(config.extract.chunk_overlap) # 200 (< chunk_size)

# Configuration rendu
print(config.render.template_path)  # Path("template.docx")
print(config.render.output_dir)     # Path("output/")
```

### Créer une configuration manuellement

```python
from core.validation import OllamaConfig, ExtractConfig, AppConfig

ollama = OllamaConfig(
    host="http://192.168.1.10:11434",
    model="mistral",
    temperature=0.5,
    top_p=0.9,
    timeout=120,
    max_retries=3
)

extract = ExtractConfig(
    enable_soffice=True,
    max_file_size_mb=50,
    chunk_size=1500,
    chunk_overlap=250
)

config = AppConfig(
    ollama=ollama,
    extract=extract,
    log_level="DEBUG"
)
```

### Validation automatique

Pydantic valide automatiquement :

```python
from pydantic import ValidationError

try:
    ollama = OllamaConfig(
        temperature=1.5  # ❌ ERREUR : doit être entre 0 et 1
    )
except ValidationError as e:
    print(e)
    # ValidationError: temperature must be between 0 and 1
```

### Exemple de fichier config.json

```json
{
  "ollama": {
    "host": "http://localhost:11434",
    "model": "llama2",
    "temperature": 0.7,
    "top_p": 0.9,
    "timeout": 300,
    "max_retries": 3
  },
  "extract": {
    "enable_soffice": true,
    "max_file_size_mb": 100,
    "chunk_size": 1200,
    "chunk_overlap": 200,
    "exclude_patterns": ["*.tmp", "*.log"]
  },
  "render": {
    "template_path": "templates/rapport.docx",
    "output_dir": "output",
    "overwrite": true,
    "export_pdf": false
  },
  "log_level": "INFO",
  "log_file": "logs/app.log"
}
```

---

## Migration du code existant

### Adapter les appels à extract_*()

**Avant Sprint 2 :**
```python
data = extract_pdf(path)
text = data["text"]
pages = data["pages"]
```

**Après Sprint 2 :**
```python
result = extract_pdf(path)
if result.success:
    data = result.value
    text = data["text"]
    pages = data["pages"]
else:
    LOG.error(f"Échec extraction : {result.error}")
    text = ""
    pages = None
```

**Ou version courte avec unwrap_or :**
```python
data = extract_pdf(path).unwrap_or({"text": "", "pages": None})
text = data["text"]
pages = data["pages"]
```

### Adapter check_llm_status()

**Avant Sprint 2 :**
```python
success, message = check_llm_status(host, model)
if success:
    print(f"✓ {message}")
else:
    print(f"✗ {message}")
```

**Après Sprint 2 :**
```python
result = check_llm_status(host, model)
if result.success:
    print(f"✓ {result.value}")
else:
    print(f"✗ {result.error}")
```

### Ajouter du logging

**Avant Sprint 2 :**
```python
def process_file(path):
    data = extract_pdf(path)
    return analyze(data)
```

**Après Sprint 2 :**
```python
from core.logger import get_logger

LOG = get_logger(__name__)

def process_file(path):
    LOG.info("Traitement fichier", extra={"path": str(path)})
    result = extract_pdf(path)
    
    if not result.success:
        LOG.error("Échec extraction", extra={"error": str(result.error)})
        return None
    
    LOG.debug("Extraction réussie", extra={"chars": len(result.value["text"])})
    return analyze(result.value)
```

---

## Bonnes pratiques

### ✅ À FAIRE

1. **Toujours vérifier result.success** avant d'accéder à `result.value`
2. **Utiliser unwrap_or()** pour des valeurs par défaut sûres
3. **Logger les erreurs** avec contexte (`extra={}`)
4. **Chaîner avec map/and_then** pour du code fonctionnel propre
5. **Valider les configs** au démarrage de l'application

### ❌ À ÉVITER

1. **Ne jamais faire** `result.value` sans vérifier `result.success`
2. **Ne pas ignorer** les `result.error` en cas d'échec
3. **Ne pas utiliser unwrap()** sauf si vous êtes **absolument sûr** du succès
4. **Ne pas logger** en `DEBUG` dans des boucles serrées (performance)
5. **Ne pas créer** de configs invalides manuellement

---

## Aide et support

- 📖 **Documentation complète** : `docs/sprint2-report.md`
- 🧪 **Exemples de tests** : `tests/test_errors.py`
- 🔍 **Code source** :
  - `core/errors.py` - Pattern Result
  - `core/logger.py` - Logging
  - `core/validation.py` - Configuration

Pour toute question, consultez le code source ou les tests !
