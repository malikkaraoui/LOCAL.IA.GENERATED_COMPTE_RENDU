# Module RH-Pro - Documentation

## Vue d'ensemble

Le module `src/rhpro` contient tous les composants pour le traitement des dossiers clients RH-Pro, de la détection à la génération de comptes-rendus.

## Architecture

```
src/rhpro/
├── client_finder.py          # Recherche floue de clients
├── client_scanner.py          # Scan structure dossier client
├── client_normalizer.py       # Normalisation en sandbox
├── batch_analyzer.py          # Analyse batch + scoring ✨ NEW
├── rag_generator.py           # RAG + LLM extraction ✨ NEW
├── report_generator.py        # Génération DOCX + outputs ✨ NEW
├── validation_profiles.py     # Validation GO/NO-GO ✨ NEW v2.1
├── batch_runner.py            # Runner batch legacy
├── parse_bilan.py             # Parser DOCX bilan
├── normalizer.py              # Normalisation données
├── mapper.py                  # Mapping champs
├── ruleset_loader.py          # Chargement rulesets
├── segmenter.py               # Segmentation texte
├── inline_extractor.py        # Extraction inline
└── docx_structure.py          # Analyse structure DOCX
```

## Modules Nouveaux (v2.1.0)

### 1. `batch_analyzer.py`

**Analyse batch de clients avec scoring.**

#### Fonctions principales

```python
def scan_batch_clients(
    batch_path: str,
    limit: Optional[int] = None,
    min_pipeline_score: float = 0.3
) -> Dict[str, Any]:
    """
    Scanne tous les clients d'un batch.
    
    Returns:
        - batch_name, batch_path
        - clients: Liste analyses clients
        - summary: Stats globales
    """
```

```python
def calculate_compatibility_score(
    scan_result: Dict[str, Any]
) -> float:
    """
    Calcule score de compatibilité pipeline (0.0-1.0).
    
    Critères:
    - GOLD détecté et score >= 0.5 : 40%
    - Au moins 3 sources RAG : 30%
    - Structure dossiers >= 4/7 : 20%
    - Pipeline ready : 10%
    """
```

```python
def get_client_analysis_detail(
    scan_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyse détaillée client (4 sections).
    
    Returns:
        - what_found: Trouvé (GOLD, sources, dossiers)
        - what_usable: Exploitable
        - what_missing: Manquant pour 100%
        - gold_choice: Justification GOLD
    """
```

#### Usage

```python
from src.rhpro.batch_analyzer import scan_batch_clients

result = scan_batch_clients("data/samples/BATCH_20")

for client in result["clients"]:
    print(f"{client['folder_name']}: {client['compatibility_score']:.2f}")
```

### 2. `rag_generator.py`

**Génération RAG avec LlamaIndex + garde-fous.**

#### Classe principale

```python
class RAGGenerator:
    """Générateur RAG pour comptes-rendus RH-Pro."""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4o-mini",
        temperature: float = 0.1,
    ):
        """Initialise le générateur."""
    
    def build_index_from_sources(
        self,
        sources_folder: str,
        file_extensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Construit index RAG depuis sources/.
        
        Returns:
            - sources_count, chunks_created
            - chunks_preview (10 premiers)
        """
    
    def generate_report(
        self,
        template_fields: List[str],
        strict_mode: bool = True,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Génère rapport structuré avec garde-fous.
        
        Returns:
            - fields: Champs remplis
            - debug: Citations + confiance
            - metrics: Couverture + qualité
        """
```

#### Garde-fous

- **Mode strict** : Interdiction d'inventer
- **Si non trouvé** : Retourne "Non renseigné"
- **Détection hallucinations** : Patterns surveillés
- **Citations obligatoires** : Source + snippet

#### Usage

```python
from src.rhpro.rag_generator import RAGGenerator

rag = RAGGenerator()
index_result = rag.build_index_from_sources("sources/")
report = rag.generate_report(
    template_fields=["nom", "prenom", "objectifs"],
    strict_mode=True,
)

print(f"Couverture: {report['metrics']['coverage_pct']}%")
```

### 3. `report_generator.py`

**Génération DOCX + outputs structurés.**

#### Classe principale

```python
class RHProReportGenerator:
    """Générateur de comptes-rendus RH-Pro."""
    
    def __init__(
        self,
        template_path: Optional[str] = None,
        template_fields: Optional[List[str]] = None,
    ):
        """Initialise le générateur."""
    
    def generate_from_client(
        self,
        sources_folder: str,
        gold_path: Optional[str] = None,
        output_dir: str = "output",
        client_name: str = "client",
        strict_mode: bool = True,
    ) -> Dict[str, Any]:
        """
        Pipeline complet: RAG → DOCX → outputs.
        
        Returns:
            - outputs: Chemins DOCX, JSON
            - metrics: Qualité
            - index_stats: Stats RAG
        """
```

#### Outputs générés

1. **generated.docx** : Compte-rendu rempli
2. **debug.json** : Preuves + citations
3. **metrics.json** : Métriques qualité
4. **validation.json** : Statut GO/NO-GO ✨ NEW v2.1

#### Template DOCX

Placeholders supportés :
```
{{nom}}
{{prenom}}
{{date_naissance}}
{{situation_professionnelle}}
{{objectifs_professionnels}}
...
```

#### Usage

```python
from src.rhpro.report_generator import generate_report_from_normalized
from src.rhpro.validation_profiles import ValidationProfile

result = generate_report_from_normalized(
    normalized_folder="sandbox/BATCH_20/client_01",
    output_dir="output",
    strict_mode=True,
    validation_profile=ValidationProfile.STRICT,  # ✨ NEW
)

print(f"DOCX: {result['outputs']['generated_docx']}")
print(f"Qualité: {result['metrics']['quality_score']:.2f}")
print(f"Statut: {result['validation']['status']}")  # GO | NO_GO | DRAFT
```

### 4. `validation_profiles.py` ✨ NEW v2.1

**Validation GO/NO-GO indépendante de la génération.**

#### Concept

```
Génération ≠ Validation
```

- ✅ DOCX **toujours généré** (même en NO_GO)
- 🔍 Validation **indépendante** après génération
- 🎯 3 profils : STRICT, STANDARD, DRAFT
- 📊 Statut clair : GO | NO_GO | DRAFT

#### Profils

| Profil | Coverage | Quality | Champs critiques | Sources |
|--------|----------|---------|------------------|---------|
| **STRICT** | ≥85% | ≥0.75 | 0 manquants | ≥3 |
| **STANDARD** | ≥75% | ≥0.65 | ≤1 manquant | ≥2 |
| **DRAFT** | Aucune limite | Toujours DRAFT | - | - |

#### Fonctions principales

```python
def validate_report(
    metrics_path: Path,
    debug_path: Optional[Path] = None,
    meta_path: Optional[Path] = None,
    profile: ValidationProfile = ValidationProfile.STANDARD,
) -> ValidationResult:
    """
    Valide un rapport selon un profil donné.
    
    Returns:
        ValidationResult avec:
        - status: "GO" | "NO_GO" | "DRAFT"
        - profile: "strict" | "standard" | "draft"
        - reasons: ["missing_critical_fields", ...]
        - actions: ["add_sources", "confirm_identity", ...]
        - scores: {quality_score, required_coverage, ...}
    """

def validate_batch(
    output_dir: Path,
    profile: ValidationProfile = ValidationProfile.STANDARD,
) -> Dict[str, ValidationResult]:
    """
    Valide tous les rapports d'un batch.
    
    Returns:
        Dict {client_name: ValidationResult}
    """
```

#### Usage

```python
from src.rhpro.validation_profiles import validate_report, ValidationProfile

result = validate_report(
    metrics_path=Path("output/client_metrics.json"),
    debug_path=Path("output/client_debug.json"),
    profile=ValidationProfile.STRICT,
)

if result.status == "GO":
    print("✅ Rapport validé pour production")
elif result.status == "NO_GO":
    print(f"❌ Refusé : {result.reasons}")
    print(f"🔧 Actions : {result.actions}")
else:
    print("📝 Brouillon - à compléter")
```

#### Champs Critiques

4 champs obligatoires pour STRICT :
- `nom`
- `prenom`
- `date_naissance`
- `situation_professionnelle`

#### Actions Recommandées

| Action | Description |
|--------|-------------|
| `add_identity_sources` | Ajouter CV, pièce d'identité |
| `add_sources` | Augmenter documents RAG |
| `select_gold_candidate` | Choisir rapport GOLD |
| `confirm_identity` | Confirmer identité client |
| `review_and_complete` | Réviser brouillon |



## Modules Existants

### `client_scanner.py`

**Scan d'un dossier client individuel.**

```python
def scan_client_folder(client_folder_path: str) -> Dict[str, Any]:
    """
    Analyse complète dossier client.
    
    Returns:
        - gold: Document GOLD détecté
        - rag_sources: Sources RAG
        - folder_structure: Dossiers
        - pipeline_ready: bool
        - warnings: Liste warnings
    """
```

**Détection GOLD** :
1. Chercher dans `06 Rapport final/`
2. Scan récursif si non trouvé
3. Scoring multi-critères
4. Fallback sur DOCX le plus récent

### `client_normalizer.py`

**Normalisation dossier client en sandbox.**

```python
def normalize_client_to_sandbox(
    scan_result: Dict[str, Any],
    batch_name: str,
    sandbox_root: str = "sandbox",
    create_normalized_alias: bool = True,
) -> Dict[str, Any]:
    """
    Copie structurée en sandbox.
    
    Structure:
    sandbox/BATCH_NAME/client_slug/
      ├── sources/
      ├── gold/
      ├── normalized/
      └── meta.json
    """
```

### `client_finder.py`

**Recherche floue de clients.**

```python
def find_client_folders(
    dataset_root: str,
    search_query: str,
    min_score: float = 0.3,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    Recherche floue (nom, prénom).
    
    Returns: Liste avec folder_name, path, score
    """
```

## Workflow Complet

```python
# 1. Scanner batch
from src.rhpro.batch_analyzer import scan_batch_clients
batch_result = scan_batch_clients("BATCH_20")

# 2. Sélectionner client
client = batch_result["clients"][0]

# 3. Normaliser
from src.rhpro.client_normalizer import normalize_client_to_sandbox
norm_result = normalize_client_to_sandbox(
    client["scan_result"],
    batch_name="BATCH_20",
)

# 4. Générer rapport
from src.rhpro.report_generator import generate_report_from_normalized
gen_result = generate_report_from_normalized(
    norm_result["normalized_path"],
    output_dir="output",
)

# 5. Résultat
print(f"DOCX: {gen_result['outputs']['generated_docx']}")
print(f"Qualité: {gen_result['metrics']['quality_score']:.2f}")
```

## Métriques

### Score Compatibilité

```python
score = 0.0

# GOLD (max 40%)
if gold_score >= 0.5: score += 0.4
elif gold_score >= 0.3: score += 0.3

# Sources RAG (max 30%)
if rag_count >= 3: score += 0.3
elif rag_count >= 1: score += 0.2

# Structure (max 20%)
if folders >= 4: score += 0.2
elif folders >= 2: score += 0.1

# Bonus pipeline_ready (10%)
if ready: score += 0.1
```

### Score Qualité

```python
quality_score = coverage * 0.6 + confidence * 0.4
```

- 60% : Couverture champs
- 40% : Confiance moyenne

## Tests

```bash
pytest tests/test_training_ui.py -v
```

Tests unitaires :
- Imports modules
- Calcul score compatibilité
- Analyse détaillée client
- Champs template par défaut

## Documentation

- [TRAINING_QUICKSTART.md](../../TRAINING_QUICKSTART.md) : Guide rapide
- [TRAINING_UI_GUIDE.md](../../docs/TRAINING_UI_GUIDE.md) : Guide complet
- [TRAINING_IMPLEMENTATION.md](../../docs/TRAINING_IMPLEMENTATION.md) : Détails techniques
- [TRAINING_DATA_STRUCTURES.md](../../docs/TRAINING_DATA_STRUCTURES.md) : Structures JSON

## Exemples

Voir [examples_training_ui.py](../../examples_training_ui.py) pour 10 exemples complets.

## Dépendances

```
python-docx>=1.1.0
llama-index>=0.10.0
llama-index-embeddings-openai>=0.1.0
llama-index-llms-openai>=0.1.0
pandas>=2.0.0
```

Installation :
```bash
pip install -r requirements.txt
```

## Support

Questions ? Voir la documentation ou ouvrir une issue GitHub.
