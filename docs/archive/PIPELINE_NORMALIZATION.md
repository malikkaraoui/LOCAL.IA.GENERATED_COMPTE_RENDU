# Pipeline de Normalisation RH-Pro

## 🎯 Objectif

Transformer les dossiers clients RH-Pro en format "pipeline-ready" :
- ✅ Détection automatique du GOLD (rapport final de référence)
- ✅ Extraction des sources RAG exploitables
- ✅ Normalisation en sandbox (sans toucher l'original)
- ✅ Préparation pour RAG + génération DOCX

## 📊 Résultats Tests

### Dataset : RH PRO BASE DONNEE/3. TERMINER/

**Test sur 20 premiers clients :**
- 📁 Total : 20 clients
- ✅ Scannés : 20 (100%)
- ✅ Pipeline-ready : 14 (70%)
- ✅ Normalisés : 14 (100% des ready)
- ❌ Erreurs : 0

**Taux de succès : 70% pipeline-ready**

Les 30% non-ready sont dus à :
- Absence de sources RAG (documents manquants)
- GOLD avec confiance trop faible (< 0.3)
- Structure désorganisée

## 📂 Structure Pipeline-Compatible

### Entrée (Dataset Original)
```
/RH PRO BASE DONNEE/3. TERMINER/
└── NOM Prénom/
    ├── 01 Dossier personnel/    ← Sources RAG
    ├── 03 Tests et bilans/      ← Sources RAG
    ├── 04 Stages/               ← Sources RAG
    ├── 05 Mesures AI/           ← Sources RAG
    ├── 06 Rapport final/        ← GOLD
    └── divers fichiers .docx, .pdf, .txt, .msg
```

### Sortie (Sandbox Normalisée)
```
./sandbox/BATCH_20/
└── client_slug/
    ├── sources/                 ← Copies des sources RAG
    │   ├── 01_personnel_001_cv.pdf
    │   ├── 03_tests_002_resultat.docx
    │   ├── 04_stages_003_convention.pdf
    │   └── root_004_document.msg
    ├── gold/
    │   └── rapport_final.docx   ← Copie du GOLD détecté
    ├── normalized/
    │   └── source.docx          ← Alias (optionnel)
    └── meta.json                ← Métadonnées complètes
```

## 🔍 Détection GOLD

### Stratégies (par ordre de priorité)

1. **06_rapport_final/** : Scanner d'abord le dossier "06 Rapport final"
2. **recursive_scan** : Si non trouvé, scanner tout le dossier client
3. **most_recent_fallback** : Prendre le .docx le plus récent

### Score de Confiance

Le score est calculé selon :
- ✅ **+0.30** : Présence dans dossier "06 Rapport final"
- ✅ **+0.15** par mot-clé : "rapport", "bilan", "orientation", "synthèse", "final"
- ✅ **+0.15** : Extension .docx
- ❌ **-0.50** : Noms génériques ("template", "modèle", "vierge")

**Seuil minimum** : 0.30 (configurable)

### Exemple de Détection

```
ARIFI Zejadin/
├── Bilan orientation RH-Pro 2021.docx   → score: 0.60 ✅ SELECTED
├── CV.docx                              → score: 0.15
└── notes.docx                           → score: 0.15
```

## 📚 Sources RAG

### Dossiers Scannés

- **01 Dossier personnel** : CV, lettres, pièces d'identité
- **03 Tests et bilans** : Tests psychotechniques, évaluations
- **04 Stages** : Conventions, rapports de stage
- **05 Mesures AI** : Attestations, contrats
- **Racine** : Documents directs (non récursif)

### Extensions Acceptées

`.docx`, `.pdf`, `.txt`, `.msg`, `.doc`

### Naming Convention

Format : `<category>_<idx>_<slug><ext>`

Exemples :
- `01_personnel_001_cv_2024.pdf`
- `03_tests_002_resultat_test_compta.docx`
- `root_003_vis_rh_pro.msg`

## 🛠️ Utilisation

### CLI : demo_training_pipeline.py

```bash
# Lister les clients
python demo_training_pipeline.py /path/to/dataset --list

# Scanner 1 client
python demo_training_pipeline.py /path/to/dataset --client "NOM Prenom"

# Scanner + normaliser 5 premiers
python demo_training_pipeline.py /path/to/dataset --limit 5 --normalize

# Batch complet avec 20 clients
python demo_training_pipeline.py /path/to/dataset \
  --limit 20 \
  --batch BATCH_20 \
  --sandbox ./sandbox \
  --normalize
```

### UI : Streamlit

```bash
streamlit run streamlit_app.py
```

1. Aller dans **🎓 Entraînement**
2. Mode **🔍 Analyser un client** ou **📦 Batch**
3. Browse pour sélectionner le dataset
4. Rechercher un client (fuzzy search)
5. Scanner → Affiche GOLD, sources, warnings
6. Normaliser → Crée la sandbox

### API : Backend

```python
import requests

# Analyser un client
response = requests.post("http://localhost:8000/api/training/analyze-client", json={
    "client_folder_path": "/path/to/NOM Prenom"
})
scan_result = response.json()["scan_result"]

# Normaliser
response = requests.post("http://localhost:8000/api/training/normalize-client", json={
    "client_folder_path": "/path/to/NOM Prenom",
    "batch_name": "BATCH_20",
    "sandbox_root": "./sandbox"
})
norm_result = response.json()["normalization_result"]

# Batch
response = requests.post("http://localhost:8000/api/training/normalize-batch", json={
    "dataset_root": "/path/to/dataset",
    "client_names": ["NOM1 Prenom1", "NOM2 Prenom2"],
    "batch_name": "BATCH_20"
})
batch_result = response.json()["batch_result"]
```

### Code Python

```python
from src.rhpro.client_scanner import scan_client_folder, format_scan_report
from src.rhpro.client_normalizer import normalize_client_to_sandbox

# Scanner
scan_result = scan_client_folder("/path/to/NOM Prenom")
print(format_scan_report(scan_result))

if scan_result["pipeline_ready"]:
    # Normaliser
    norm_result = normalize_client_to_sandbox(
        scan_result,
        batch_name="BATCH_20",
        sandbox_root="./sandbox",
    )
    print(f"✅ Sandbox : {norm_result['sandbox_path']}")
```

## 📋 meta.json Structure

```json
{
  "normalization_info": {
    "batch_name": "BATCH_20",
    "client_slug": "arifi_zejadin",
    "original_client_name": "ARIFI Zejadin",
    "original_client_path": "/path/to/ARIFI Zejadin",
    "normalized_at": "2025-12-27T14:41:00",
    "sandbox_path": "/sandbox/batch_20/arifi_zejadin"
  },
  "scan_result": {
    "client_name": "ARIFI Zejadin",
    "gold": {
      "path": "/path/to/Bilan orientation.docx",
      "score": 0.60,
      "strategy": "recursive_scan",
      "size_bytes": 1365109
    },
    "rag_sources": [
      {
        "path": "/path/to/test_compta.pdf",
        "category": "03_tests",
        "extension": ".pdf",
        "size_bytes": 245678
      }
    ],
    "folder_structure": {
      "01_personnel": null,
      "03_tests": "/path/to/03 Tests",
      "06_rapport": null
    },
    "warnings": [],
    "pipeline_ready": true,
    "stats": {
      "gold_found": true,
      "gold_score": 0.60,
      "rag_sources_count": 10,
      "extensions": {
        ".pdf": 8,
        ".docx": 1,
        ".msg": 1
      },
      "total_size_mb": 12.5
    }
  },
  "gold": {
    "original_path": "/path/to/Bilan orientation.docx",
    "normalized_path": "/sandbox/batch_20/arifi_zejadin/gold/rapport_final.docx",
    "size_bytes": 1365109,
    "copied_at": "2025-12-27T14:41:00"
  },
  "sources": [
    {
      "original_path": "/path/to/test_compta.pdf",
      "normalized_path": "/sandbox/batch_20/arifi_zejadin/sources/03_tests_001_test_compta.pdf",
      "category": "03_tests",
      "size_bytes": 245678,
      "copied_at": "2025-12-27T14:41:00"
    }
  ],
  "file_counts": {
    "gold": 1,
    "sources": 10,
    "total": 11
  },
  "pipeline_ready": true
}
```

## ⚠️ Warnings Types

| Warning | Cause | Impact | Solution |
|---------|-------|--------|----------|
| `❌ Aucun document GOLD détecté` | Pas de .docx trouvé | Bloquant | Vérifier la présence de rapports |
| `⚠️ Confiance GOLD faible (< 0.5)` | Score < 0.5 | Avertissement | Valider manuellement le GOLD |
| `❌ Aucune source RAG trouvée` | Pas de documents | Bloquant | Ajouter des documents sources |
| `⚠️ Peu de sources RAG (< 3)` | < 3 sources | Avertissement | RAG limité, résultats moyens |
| `⚠️ Dossiers manquants` | Structure incomplète | Info | Impact variable selon dossiers |

## 🚀 Prochaines Étapes

### V1 (Actuel) ✅
- ✅ Détection GOLD avec scoring
- ✅ Extraction sources RAG
- ✅ Normalisation sandbox
- ✅ CLI + UI + API
- ✅ Tests 20 clients (70% success)

### V2 (Prochain Sprint)
- 🔄 Intégration RAG sur sandbox
- 🔄 Génération DOCX automatique
- 🔄 Comparaison GOLD vs Generated
- 🔄 Métriques de qualité
- 🔄 Training loop avec feedback

### V3 (Future)
- 📅 Auto-correction des dossiers non-ready
- 📅 Suggestions d'amélioration structure
- 📅 Dashboard analytics global
- 📅 Export batch vers format training ML

## 📁 Fichiers Créés

### Modules Core
- `src/rhpro/client_scanner.py` (420 lignes)
  - `scan_client_folder()` : Analyse complète
  - `find_gold_document()` : Détection GOLD avec scoring
  - `find_rag_sources()` : Extraction sources RAG
  - `format_scan_report()` : Formatage console

- `src/rhpro/client_normalizer.py` (340 lignes)
  - `normalize_client_to_sandbox()` : Copie structurée
  - `normalize_batch_to_sandbox()` : Batch processing
  - `format_normalization_report()` : Rapport batch

### CLI & UI
- `demo_training_pipeline.py` (195 lignes)
  - CLI pour tests et production
  - Support client unique ou batch
  - Options --normalize, --limit, --list

- `pages_streamlit/training.py` (440 lignes)
  - Page Entraînement complète
  - Browse dataset + recherche client
  - Scan + normalisation interactive
  - Modes : single client, batch, config

### Backend API
- `backend/api/routes/training.py` (ajout)
  - `POST /api/training/analyze-client`
  - `POST /api/training/normalize-client`
  - `POST /api/training/normalize-batch`

### Documentation
- `docs/PIPELINE_NORMALIZATION.md` (ce fichier)
- `docs/DATASET_MODE_GUIDE.md` (précédent sprint)

## 🔧 Configuration

### Paramètres Scanner (à venir)

```yaml
# config/pipeline.yaml
scanner:
  gold:
    min_score: 0.3
    keywords:
      - rapport
      - bilan
      - orientation
      - synthèse
      - final
    extensions:
      - .docx
      - .doc
  
  rag:
    min_sources: 1
    extensions:
      - .docx
      - .pdf
      - .txt
      - .msg
    folders:
      - 01 Dossier personnel
      - 03 Tests et bilans
      - 04 Stages
      - 05 Mesures AI

normalizer:
  create_alias: true
  sandbox_root: ./sandbox
  continue_on_error: true
```

## 📊 Métriques Batch

Exemple de rapport batch (14 clients) :

```
📦 NORMALISATION BATCH : BATCH_20
📊 Résultats : 14 client(s)
  ✅ Succès      : 14
  ⚠️  Non prêts   : 0
  ❌ Erreurs     : 0
  📈 Taux succès : 100.0%

📁 Sandbox créée dans : /sandbox/batch_20
📊 14 client(s) normalisé(s)

Taille totale : ~180 MB
Fichiers copiés : ~140 (14 GOLD + 126 sources)
Temps traitement : ~45 secondes
```

## ✅ Validation

### Tests Unitaires (à venir)

```python
# tests/test_client_scanner.py
def test_scan_client_folder_with_gold():
    scan = scan_client_folder("data/samples/client_01")
    assert scan["pipeline_ready"] == True
    assert scan["gold"] is not None
    assert len(scan["rag_sources"]) > 0

# tests/test_client_normalizer.py
def test_normalize_creates_structure():
    norm = normalize_client_to_sandbox(scan, "TEST")
    assert Path(norm["gold_path"]).exists()
    assert Path(norm["sources_path"]).exists()
    assert Path(norm["meta_path"]).exists()
```

### Tests d'Intégration

```bash
# Test CLI complet
python demo_training_pipeline.py data/samples --limit 5 --normalize

# Test API
pytest tests/test_api_training.py -v

# Test UI (manuel)
streamlit run streamlit_app.py
```

## 🎓 Commandes Git

```bash
# Ajouter tous les fichiers
git add -A

# Commit
git commit -m "feat: Add pipeline normalization system

- Scanner de dossiers clients (GOLD + RAG detection)
- Normalisation en sandbox (structure pipeline-ready)
- CLI demo_training_pipeline.py
- Page Streamlit 🎓 Entraînement
- API endpoints /api/training/analyze-client, normalize-client, normalize-batch
- Tests sur 20 clients réels : 70% pipeline-ready
- Documentation complète

Résultats :
- 14/20 clients normalisés avec succès
- Structure sources/, gold/, normalized/, meta.json
- Naming convention : category_idx_slug.ext
- Meta.json complet avec scan_result + copie infos"

# Push
git push
```
