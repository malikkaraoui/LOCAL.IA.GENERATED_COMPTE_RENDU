# 📡 API Reference - SCRIPT.IA

**Version** : 4.1  
**Dernière mise à jour** : 28 décembre 2025

Documentation complète des API et modules Python du projet.

---

## 🏗️ Architecture

```
SCRIPT.IA/
├── backend/           # API FastAPI + Workers RQ
│   ├── api/          # Endpoints REST
│   └── workers/      # Jobs asynchrones
├── core/             # Modules métier
│   ├── extract.py    # Extraction multi-format
│   ├── generate.py   # Génération LLM
│   ├── context.py    # RAG (LlamaIndex)
│   ├── validation.py # Validation champs
│   ├── render.py     # DOCX rendering
│   └── extractors/   # Extracteurs spécialisés
└── src/rhpro/        # Logique RH-Pro
    ├── dataset_training.py
    ├── production_gate.py
    └── batch_analyzer.py
```

---

## 📦 Core Modules

### 1. core.extract

#### extract_sources()

```python
def extract_sources(
    source_files: list[Path],
    output_dir: Path,
    enable_doc_conversion: bool = True,
    enable_msg: bool = True,
    msg_attachments_dir: Path | None = None
) -> tuple[list[Path], dict]:
    """
    Extrait texte de multiples sources (PDF/DOCX/TXT/DOC/MSG).
    
    Args:
        source_files: Liste chemins sources
        output_dir: Dossier sortie .txt
        enable_doc_conversion: Convertir .doc via LibreOffice
        enable_msg: Extraire emails .msg
        msg_attachments_dir: Dossier pièces jointes .msg
        
    Returns:
        (txt_files, metadata)
        - txt_files: Liste Path fichiers .txt extraits
        - metadata: {
            "total_sources": int,
            "formats": {"pdf": int, "docx": int, ...},
            "errors": [str],
            "warnings": [str],
            "msg_attachments": [Path]  # Si enable_msg=True
          }
          
    Raises:
        ExtractionError: Si échec critique (>80% sources)
        
    Example:
        >>> txt_files, meta = extract_sources(
        ...     [Path("CV.pdf"), Path("Email.msg")],
        ...     Path("output/")
        ... )
        >>> print(meta["formats"])
        {'pdf': 1, 'msg': 1}
        >>> print(meta["msg_attachments"])
        [Path("output/msg_attachments/CV_Candidat.pdf")]
    """
```

**Formats supportés** :
- `.pdf` : PyMuPDF (fitz)
- `.docx` : python-docx
- `.txt` : natif
- `.doc` : LibreOffice (soffice)
- `.msg` : extract-msg (optionnel)

**Workflow** :
1. Validation existence fichiers
2. Extraction parallèle (max 4 workers)
3. Gestion erreurs gracieuse
4. Génération métadonnées

#### extract_pdf()

```python
def extract_pdf(pdf_path: Path, output_dir: Path) -> Path:
    """
    Extrait texte PDF via PyMuPDF.
    
    Args:
        pdf_path: Chemin PDF source
        output_dir: Dossier sortie
        
    Returns:
        Path: Fichier .txt généré
        
    Raises:
        ExtractionError: Si PDF corrompu/protégé
        
    Example:
        >>> txt = extract_pdf(Path("CV.pdf"), Path("output/"))
        >>> txt.read_text()[:50]
        'CURRICULUM VITAE\n\nJean Dupont\nDéveloppeur Senior'
    """
```

#### extract_docx()

```python
def extract_docx(docx_path: Path, output_dir: Path) -> Path:
    """
    Extrait texte DOCX via python-docx.
    
    Returns:
        Path: Fichier .txt avec paragraphes
    """
```

#### extract_msg()

```python
def extract_msg(
    msg_path: Path,
    output_dir: Path,
    attachments_dir: Path | None = None
) -> tuple[Path, list[Path]]:
    """
    Extrait email .msg + pièces jointes.
    
    Args:
        msg_path: Chemin .msg
        output_dir: Dossier email .txt
        attachments_dir: Dossier pièces jointes (auto si None)
        
    Returns:
        (email_txt, attachment_paths)
        - email_txt: Contenu email formaté
        - attachment_paths: Liste pièces jointes extraites
        
    Requires:
        extract-msg>=0.48.0 installé
        
    Format email:
        [EMAIL_MSG]
        Subject: {subject}
        From: {sender}
        To: {recipients}
        Date: {date}
        
        {body_text}
        
        [ATTACHMENTS: {count} files]
        - {attachment1.pdf}
        - {attachment2.docx}
    """
```

---

### 2. core.extractors.msg_extractor

#### extract_msg_to_text()

```python
def extract_msg_to_text(
    msg_path: Path,
    output_dir: Path
) -> tuple[str, dict]:
    """
    Extrait contenu email .msg avec métadonnées.
    
    Args:
        msg_path: Chemin fichier .msg
        output_dir: Dossier extraction pièces jointes
        
    Returns:
        (text, metadata)
        - text: Contenu email formaté
        - metadata: {
            "subject": str,
            "sender": str,
            "recipients": str,
            "date": str,
            "attachments_count": int,
            "attachments": [
                {"name": str, "path": Path, "size": int}
            ]
          }
          
    Example:
        >>> text, meta = extract_msg_to_text(
        ...     Path("candidature.msg"),
        ...     Path("output/")
        ... )
        >>> meta["subject"]
        'Candidature - Poste Développeur'
        >>> meta["attachments_count"]
        2
    """
```

#### MSG_SUPPORT_AVAILABLE

```python
MSG_SUPPORT_AVAILABLE: bool
```

**Description** : Flag indiquant si extract-msg est disponible.

**Usage** :
```python
from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE

if MSG_SUPPORT_AVAILABLE:
    process_msg_files(...)
else:
    warnings.append("MSG_EXTRACTOR_MISSING")
```

---

### 3. core.generate

#### generate_bilan()

```python
def generate_bilan(
    client_name: str,
    source_files: list[Path],
    template_path: Path,
    training_state: dict | None = None,
    llm_config: dict | None = None
) -> dict[str, str]:
    """
    Génère bilan complet via LLM + RAG.
    
    Args:
        client_name: Nom client (contexte)
        source_files: Sources extraites (.txt)
        template_path: Template DOCX pour structure
        training_state: Patterns training (field_max_lines, etc.)
        llm_config: Config LLM (model, temperature, etc.)
        
    Returns:
        dict: {nom_champ: valeur}
        
    Example:
        >>> fields = generate_bilan(
        ...     "Jean Dupont",
        ...     [Path("CV.txt"), Path("Email.txt")],
        ...     Path("template.docx"),
        ...     training_state=load_training_state()
        ... )
        >>> fields["nom"]
        'Dupont'
        >>> len(fields["experiences_professionnelles"].split('\n'))
        32  # Respecte field_max_lines du training_state
    """
```

#### generate_field()

```python
def generate_field(
    field_name: str,
    context: str,
    max_lines: int | None = None,
    format_regex: str | None = None,
    llm_config: dict | None = None
) -> str:
    """
    Génère un champ unique via LLM.
    
    Args:
        field_name: Nom champ (ex: "nom", "experiences")
        context: Contexte RAG
        max_lines: Limite lignes (from training_state)
        format_regex: Validation format (ex: email)
        llm_config: Config LLM
        
    Returns:
        str: Valeur générée
        
    Example:
        >>> nom = generate_field(
        ...     "nom",
        ...     context="CV Jean Dupont...",
        ...     max_lines=2
        ... )
        >>> nom
        'Dupont'
    """
```

---

### 4. core.context

#### build_rag_index()

```python
from llama_index.core import VectorStoreIndex

def build_rag_index(
    txt_files: list[Path],
    chunk_size: int = 1024,
    chunk_overlap: int = 200
) -> VectorStoreIndex:
    """
    Construit index vectoriel LlamaIndex.
    
    Args:
        txt_files: Fichiers texte sources
        chunk_size: Taille chunks embeddings
        chunk_overlap: Overlap entre chunks
        
    Returns:
        VectorStoreIndex: Index RAG queryable
        
    Example:
        >>> index = build_rag_index([Path("CV.txt")])
        >>> engine = index.as_query_engine(similarity_top_k=5)
        >>> response = engine.query("Quelle est l'expérience principale ?")
        >>> print(response.response)
        'Développeur Senior chez Entreprise SA (2018-2023)'
    """
```

#### get_relevant_context()

```python
def get_relevant_context(
    query: str,
    index: VectorStoreIndex,
    top_k: int = 5
) -> str:
    """
    Récupère contexte pertinent via RAG.
    
    Args:
        query: Question/besoin (ex: "expériences professionnelles")
        index: Index vectoriel
        top_k: Nombre chunks retournés
        
    Returns:
        str: Contexte concaténé (max 4000 chars)
        
    Example:
        >>> context = get_relevant_context(
        ...     "formations académiques",
        ...     index,
        ...     top_k=3
        ... )
        >>> "Master Informatique" in context
        True
    """
```

---

### 5. core.validation

#### validate_bilan()

```python
def validate_bilan(
    fields: dict[str, str],
    training_state: dict | None = None
) -> tuple[bool, list[str]]:
    """
    Valide bilan complet (champs, formats, longueurs).
    
    Args:
        fields: Dict champs générés
        training_state: Pour field_max_lines
        
    Returns:
        (is_valid, errors)
        - is_valid: True si valide
        - errors: Liste messages erreur
        
    Example:
        >>> valid, errors = validate_bilan({
        ...     "nom": "Dupont",
        ...     "email": "invalid"
        ... })
        >>> valid
        False
        >>> errors
        ['Email invalide: invalid', 'Champ obligatoire manquant: prenom']
    """
```

#### validate_field_format()

```python
def validate_field_format(field_name: str, value: str) -> bool:
    """
    Valide format champ via regex.
    
    Args:
        field_name: Nom champ (email, telephone, avs, etc.)
        value: Valeur à valider
        
    Returns:
        bool: True si format valide
        
    Formats supportés:
        - email: RFC 5322 simplifié
        - telephone: +41/0 XX XXX XX XX
        - avs: 756.XXXX.XXXX.XX
        - date_naissance: JJ.MM.AAAA
        
    Example:
        >>> validate_field_format("email", "test@example.com")
        True
        >>> validate_field_format("avs", "756.1234.5678.90")
        True
    """
```

---

### 6. core.render

#### render_to_docx()

```python
def render_to_docx(
    fields: dict[str, str],
    template_path: Path,
    output_path: Path,
    branding: dict | None = None
) -> Path:
    """
    Remplit template DOCX et applique branding.
    
    Args:
        fields: Dict {placeholder: valeur}
        template_path: Template avec {{placeholders}}
        output_path: Chemin sortie
        branding: {
            "logo_path": Path,
            "primary_color": "#RRGGBB",
            "font_family": str
          }
          
    Returns:
        Path: Document final
        
    Example:
        >>> output = render_to_docx(
        ...     {"nom": "Dupont", "prenom": "Jean"},
        ...     Path("template.docx"),
        ...     Path("output/bilan.docx"),
        ...     {"logo_path": Path("logo.png")}
        ... )
        >>> output.exists()
        True
    """
```

---

## 🧪 src.rhpro Modules

### 1. dataset_training

#### analyze_client_dataset()

```python
def analyze_client_dataset(
    clients_dir: Path,
    client_limit: int = 0,
    scan_depth: int = 4,
    merge_with_existing: bool = False
) -> dict:
    """
    Analyse dataset clients et génère training_state.
    
    Args:
        clients_dir: Dossier CLIENTS/
        client_limit: Max clients (0 = tous)
        scan_depth: Max docs/client
        merge_with_existing: Fusionner avec training_state.json existant
        
    Returns:
        dict: training_state_v1.0
        {
          "run_id": str,
          "created_at": str,
          "dataset": {...},
          "patterns": {
            "section_stats": {...},
            "field_max_lines": {...},
            "unknown_titles_top": [...]
          },
          "warnings": [str]
        }
        
    Example:
        >>> state = analyze_client_dataset(
        ...     Path("CLIENTS/"),
        ...     client_limit=5,
        ...     scan_depth=3
        ... )
        >>> state["dataset"]["clients_used"]
        5
        >>> state["patterns"]["section_stats"]["Expérience professionnelle"]
        {
          "coverage_pct": 85.0,
          "clients_count": 4,
          "lines_avg": 28.5,
          "lines_median": 25.0,
          "lines_p90": 42.0
        }
    """
```

#### merge_training_states()

```python
def merge_training_states(
    state_a: dict,
    state_b: dict
) -> dict:
    """
    Fusionne 2 training_states de manière safe.
    
    Stratégie:
        - dataset.clients_used: somme
        - field_max_lines: max valeur
        - section_stats: max p90/coverage
        - warnings: union
        
    Args:
        state_a, state_b: training_state_v1.0
        
    Returns:
        dict: training_state fusionné
        
    Raises:
        Jamais (défensif, try/except partout)
        
    Example:
        >>> merged = merge_training_states(
        ...     {"patterns": {"field_max_lines": {"nom": 2}}},
        ...     {"patterns": {"field_max_lines": {"nom": 3}}}
        ... )
        >>> merged["patterns"]["field_max_lines"]["nom"]
        3  # max(2, 3)
    """
```

#### load_training_state()

```python
def load_training_state(path: Path = Path("training_state.json")) -> dict:
    """
    Charge training_state.json avec validation schéma.
    
    Returns:
        dict: training_state_v1.0 validé
        
    Raises:
        ValidationError: Si schéma invalide
    """
```

---

### 2. production_gate

#### ProductionGate

```python
class ProductionGate:
    """Évaluation Go/No-Go qualité bilan."""
    
    def __init__(self, profile: str = "normal"):
        """
        Args:
            profile: "strict" | "normal" | "permissive"
        """
        
    def evaluate(self, bilan: dict) -> Score:
        """
        Évalue qualité bilan (score 0-100).
        
        Args:
            bilan: Dict champs + metadata
            
        Returns:
            Score: {
              "total": int,  # 0-100
              "breakdown": {
                "sources_count": int,  # 0-20
                "gold_detected": int,  # 0-20
                "critical_fields": int,  # 0-30
                "warnings": int  # 0 ou -10
              },
              "go_decision": "GO" | "WARNING" | "NO-GO",
              "recommendation": str
            }
            
        Example:
            >>> gate = ProductionGate(profile="normal")
            >>> score = gate.evaluate({
            ...     "sources": ["CV.pdf", "Email.msg"],
            ...     "avs": "756.1234.5678.90",
            ...     "nom": "Dupont",
            ...     "warnings": []
            ... })
            >>> score["total"]
            75
            >>> score["go_decision"]
            'GO'
        """
```

**Profils** :

| Profile | GO Seuil | WARNING Seuil | NO-GO |
|---------|----------|---------------|-------|
| strict | ≥80 | 70-79 | <70 |
| normal | ≥70 | 50-69 | <50 |
| permissive | ≥60 | 40-59 | <40 |

---

### 3. batch_analyzer

#### analyze_batch()

```python
def analyze_batch(
    clients_dir: Path,
    output_dir: Path,
    scan_depth: int = 4
) -> dict:
    """
    Analyse batch complète dossiers clients.
    
    Args:
        clients_dir: Dossier CLIENTS/
        output_dir: Sortie rapports
        scan_depth: Max docs/client
        
    Returns:
        dict: {
          "total_clients": int,
          "gold_count": int,
          "avg_sources_per_client": float,
          "formats_distribution": {...},
          "stats": {...}
        }
        
    Example:
        >>> report = analyze_batch(
        ...     Path("CLIENTS/"),
        ...     Path("output/batch_report/"),
        ...     scan_depth=4
        ... )
        >>> report["gold_count"]
        42
        >>> report["total_clients"]
        120
    """
```

---

## 🌐 Backend API (FastAPI)

### Base URL

**Local** : `http://localhost:8000`  
**Production** : `https://api.script-ia.ch` (exemple)

### Endpoints

#### POST /api/generate

```http
POST /api/generate
Content-Type: application/json

{
  "client_name": "Jean Dupont",
  "source_files": [
    "/path/to/CV.pdf",
    "/path/to/Email.msg"
  ],
  "template_path": "/path/to/template.docx",
  "enable_msg": true,
  "merge_training": true
}
```

**Response** :
```json
{
  "job_id": "job_abc123",
  "status": "queued",
  "estimated_time": 180
}
```

#### GET /api/status/{job_id}

```http
GET /api/status/job_abc123
```

**Response** :
```json
{
  "job_id": "job_abc123",
  "status": "completed",
  "progress": 100,
  "result": {
    "output_path": "/path/to/bilan_final.docx",
    "score": 82,
    "go_decision": "GO"
  }
}
```

**Status possibles** : `queued`, `started`, `completed`, `failed`

#### POST /api/training/analyze

```http
POST /api/training/analyze
Content-Type: application/json

{
  "clients_dir": "/path/to/CLIENTS",
  "client_limit": 0,
  "scan_depth": 4,
  "merge": true
}
```

**Response** :
```json
{
  "training_state": {...},
  "stats": {
    "clients_analyzed": 120,
    "gold_count": 42,
    "total_sources": 487
  }
}
```

---

## 🔧 Configuration

### Fichier : backend/config.py

```python
# LLM
LLM_MODEL = "gpt-4"
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 2000

# RAG
RAG_CHUNK_SIZE = 1024
RAG_SIMILARITY_TOP_K = 5

# Extraction
MAX_TEXT_LENGTH = 500_000
ENABLE_DOC_CONVERSION = True
ENABLE_MSG = True

# Training
SCAN_DEPTH_DEFAULT = 4
CLIENT_LIMIT_DEFAULT = 0

# Production Gate
PRODUCTION_GATE_PROFILE = "normal"  # strict/normal/permissive
```

### Variables d'environnement

```bash
# .env
OPENAI_API_KEY=sk-...
LLAMA_INDEX_CACHE_DIR=~/.cache/llama_index
SOFFICE_PATH=/usr/bin/soffice
CLIENTS_DIR=/path/to/CLIENTS
OUTPUT_DIR=/path/to/output
```

---

## 🧪 Tests

### Modules de test

```
tests/
├── test_extraction.py           # Extraction multi-format
├── test_msg_extraction.py       # Emails .msg spécifique
├── test_generation.py           # Génération LLM
├── test_validation.py           # Validation champs
├── test_training_state_integrity.py  # Training state schema
├── test_production_gate.py      # Scoring Go/No-Go
└── fixtures/                    # Données test
```

### Lancer tests

```bash
# Tous les tests
pytest tests/ -v

# Tests spécifiques
pytest tests/test_msg_extraction.py -v

# Coverage
pytest tests/ --cov=core --cov=src/rhpro --cov-report=html
```

---

## 📊 Types & Schemas

### training_state_v1.0 Schema

```python
from typing import TypedDict

class SectionStats(TypedDict):
    coverage_pct: float  # ∈ [0..100]
    clients_count: int
    lines_avg: float
    lines_median: float
    lines_p90: float

class TrainingState(TypedDict):
    run_id: str
    created_at: str  # ISO 8601
    dataset: dict[str, int | dict]
    patterns: dict[str, dict | list]
    warnings: list[str]
```

### Bilan Fields Schema

```python
BILAN_FIELDS = [
    # Identité
    "nom", "prenom", "date_naissance", "lieu_naissance",
    "nationalite", "etat_civil", "avs",
    
    # Contact
    "adresse", "code_postal", "ville",
    "telephone", "email",
    
    # Professionnel
    "experiences_professionnelles",
    "formations",
    "competences",
    "langues",
    
    # Optionnel
    "loisirs", "references"
]
```

---

## 🔗 Liens Utiles

### Documentation externe

- **LlamaIndex** : https://docs.llamaindex.ai/
- **python-docx** : https://python-docx.readthedocs.io/
- **PyMuPDF** : https://pymupdf.readthedocs.io/
- **extract-msg** : https://github.com/TeamMsgExtractor/msg-extractor

### Dépôts GitHub

- **FastAPI** : https://github.com/tiangolo/fastapi
- **Streamlit** : https://github.com/streamlit/streamlit

---

## 📝 Changelog API

### v4.1 (28 déc 2025)
- ✅ Support .msg (emails Outlook)
- ✅ Merge safe training_states
- ✅ Presets UX Streamlit
- ✅ 7 tests intégrité training_state

### v4.0 (déc 2025)
- ✅ Production Gate (Go/No-Go)
- ✅ Scoring multi-critères
- ✅ 3 profils validation

### v3.0 (nov 2025)
- ✅ Batch analyzer
- ✅ Training UI complète
- ✅ Section_stats normalisé

---

**Maintenu par** : Équipe SCRIPT.IA  
**Dernière revue** : 28 décembre 2025  
**Support** : support@script-ia.ch (exemple)
