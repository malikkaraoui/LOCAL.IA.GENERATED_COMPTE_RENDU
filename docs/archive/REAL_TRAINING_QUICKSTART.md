# 🚀 REAL TRAINING - GUIDE RAPIDE

Guide pratique pour utiliser le système d'analyse de dataset RH-Pro avec extraction réelle de sections.

---

## ⚡ DÉMARRAGE RAPIDE

### 1. Analyser un Dataset

```python
from src.rhpro.dataset_training import analyze_dataset, export_training_artifacts

# Analyse complète
result = analyze_dataset(
    root_dir="CLIENTS",           # Dossier racine contenant les clients
    limit=None,                   # None = tous les clients, ou int pour limiter
    out_dir="output/training"     # Dossier de sortie
)

# Exporter les artefacts
export_training_artifacts(result, "output/training")
```

**Outputs générés** :
```
output/training/{dataset_id}/
├── training_state.json      ← État complet (schema v1.0)
├── dataset_manifest.json    ← Liste des clients
├── dataset_stats.json       ← Statistiques globales
└── training_report.md       ← Rapport lisible
```

---

## 📊 UTILISATION AVANCÉE

### Analyser 10 Premiers Clients

```python
result = analyze_dataset("CLIENTS", limit=10)

print(f"Clients détectés: {result.stats['successful_scans']}")
print(f"Extensions: {result.stats['extensions_distribution']}")
print(f"Sections: {len(result.patterns['sections_stats'])}")
```

### Extraire Sections d'un DOCX

```python
from src.rhpro.dataset_training import extract_sections_from_docx
from pathlib import Path

sections = extract_sections_from_docx(Path("client/rapport.docx"))

for section in sections:
    print(f"{section['title']}")
    print(f"  → Canonique: {section['canonical']}")
    print(f"  → Lignes: {section['lines']}")
```

### Normaliser un Titre

```python
from src.rhpro.dataset_training import normalize_title, match_title_to_canonical

title = "Ressources : Points d'appui"
normalized = normalize_title(title)  # "RESSOURCES POINTS D APPUI"
canonical = match_title_to_canonical(title)  # "ressources_points_appui"

print(f"{title} → {normalized} → {canonical}")
```

---

## 🔍 INSPECTION DU training_state.json

### Charger et Explorer

```python
import json
from pathlib import Path

# Charger
state_path = Path("output/training/{dataset_id}/training_state.json")
with open(state_path) as f:
    state = json.load(f)

# Schema
print(f"Version: {state['schema_version']}")
print(f"Run ID: {state['run_id']}")
print(f"Clients: {state['dataset']['clients_detected']}")

# Sections apprises
for canonical, stats in state['learned_patterns']['sections_stats'].items():
    print(f"\n{canonical}:")
    print(f"  Coverage: {stats['coverage']*100:.0f}%")
    print(f"  Lignes: avg={stats['avg_lines']}, p90={stats['p90_lines']}")
    print(f"  Variants: {stats['title_variants_top'][:3]}")
```

### Vérifier Profil de Validation

```python
strict = state['validation_profiles']['STRICT']
print(f"Required coverage: {strict['required_coverage_min']}%")
print(f"Quality score: {strict['quality_score_min']}")
print(f"Critical fields: {strict['critical_fields']}")
```

---

## ✅ VALIDATION

### Tests DoD

```bash
# Tous les tests (15)
pytest tests/test_training_state_schema.py tests/test_end2end_one_client.py -v

# Tests training_state uniquement (8)
pytest tests/test_training_state_schema.py -v

# Tests end2end uniquement (7)
pytest tests/test_end2end_one_client.py -v
```

### Validator P0

```bash
python validate_training_implementation.py
```

**Attendu** :
```
🟢 STATUT: PASS
   Tous les tests (critiques + optionnels) réussis
```

---

## 📈 STATISTIQUES DISPONIBLES

### Dans result.patterns

```python
result.patterns = {
    "sections_stats": {
        "formation": {
            "title_variants_top": ["FORMATION", "PARCOURS"],
            "avg_lines": 8.3,
            "p50_lines": 7,
            "p90_lines": 15,
            "clients_with_section": 45,
            "coverage": 0.78
        }
        # ... autres sections
    },
    
    "learned_title_map": {
        "OBJECTIFS DE STAGE": "objectifs",
        "HORAIRES SELON PLANNING": "plan_action"
        # ... nouveaux mappings appris
    },
    
    "doc_types_stats": {
        ".docx": {"count": 234, "clients_coverage": 0.95}
        # ... autres extensions
    }
}
```

### Dans result.stats

```python
result.stats = {
    "total_clients": 58,
    "successful_scans": 56,
    "gold_detected": 52,
    "pipeline_ready": 54,
    "extensions_distribution": {".docx": 123, ".pdf": 87},
    "avg_sources_per_client": 4.2
}
```

---

## 🎯 CAS D'USAGE

### 1. Explorer un Nouveau Dataset

```python
# Tester sur 5 clients
result = analyze_dataset("NEW_DATASET", limit=5)

print("📊 Résumé:")
print(f"  Clients: {result.stats['successful_scans']}/{result.stats['total_clients']}")
print(f"  Extensions: {list(result.stats['extensions_distribution'].keys())}")
print(f"  Sections détectées: {len(result.patterns['sections_stats'])}")

# Identifier les problèmes
for client in result.clients:
    if 'error' in client:
        print(f"❌ {client['folder_name']}: {client['error']}")
```

### 2. Apprendre de Nouveaux Titres

```python
# Analyser avec apprentissage
result = analyze_dataset("CLIENTS", limit=50)

# Voir nouveaux patterns
learned = result.patterns['learned_title_map']
print(f"📚 {len(learned)} nouveaux titres appris:")
for title, canonical in learned.items():
    print(f"  {title} → {canonical}")
```

### 3. Calculer max_lines_defaults

```python
# Analyser pour obtenir p90
result = analyze_dataset("CLIENTS")

# Extraire defaults
defaults = {}
for canonical, stats in result.patterns['sections_stats'].items():
    defaults[canonical] = int(stats['p90_lines'])

print("max_lines_defaults:", defaults)
# → {"formation": 15, "competences": 8, ...}
```

### 4. Détecter Anomalies

```python
# Analyser
result = analyze_dataset("CLIENTS")

# Sections courtes (potentiellement incomplètes)
for canonical, stats in result.patterns['sections_stats'].items():
    if stats['avg_lines'] < 2:
        print(f"⚠️  {canonical}: seulement {stats['avg_lines']} lignes en moyenne")

# Coverage faible
for canonical, stats in result.patterns['sections_stats'].items():
    if stats['coverage'] < 0.5:
        print(f"⚠️  {canonical}: coverage {stats['coverage']*100:.0f}% (< 50%)")
```

---

## 🔧 CONFIGURATION

### Ajouter un Titre au Seed Mapping

Éditer [src/rhpro/dataset_training.py](src/rhpro/dataset_training.py):

```python
SEED_SECTION_TITLE_MAP = {
    # ... existants
    "NOUVEAU TITRE": "competences",  # ← Ajouter ici
}
```

### Ajuster le Seuil Fuzzy

```python
def match_title_to_canonical(title: str) -> Optional[str]:
    # ...
    ratio = SequenceMatcher(None, title_norm, known_title).ratio()
    if ratio >= 0.80:  # ← Changer de 0.85 à 0.80 pour plus de matches
        return canonical
```

### Modifier les Profils de Validation

Éditer `_build_training_state()`:

```python
"STRICT": {
    "required_coverage_min": 90.0,  # ← Plus strict (85 → 90)
    # ...
}
```

---

## 🐛 DEBUGGING

### Vérifier qu'un DOCX est Parsable

```python
from src.rhpro.dataset_training import extract_sections_from_docx
from pathlib import Path

try:
    sections = extract_sections_from_docx(Path("problematic.docx"))
    print(f"✅ {len(sections)} sections extraites")
    for s in sections:
        print(f"  - {s['title']} ({s['lines']} lignes)")
except Exception as e:
    print(f"❌ Erreur: {e}")
```

### Voir Pourquoi un Titre N'est Pas Mappé

```python
from src.rhpro.dataset_training import normalize_title, match_title_to_canonical

title = "Mon titre problématique"
normalized = normalize_title(title)
canonical = match_title_to_canonical(title)

print(f"Original: {title}")
print(f"Normalisé: {normalized}")
print(f"Canonique: {canonical}")  # None si pas mappé

# Si None, vérifier:
# 1) Est-il dans SEED_SECTION_TITLE_MAP?
# 2) Est-ce qu'une heuristique devrait matcher?
# 3) Fuzzy ratio avec les seeds connus?
```

### Tracer l'Analyse

```python
# Activer logging
import logging
logging.basicConfig(level=logging.DEBUG)

result = analyze_dataset("CLIENTS", limit=1)
# → Affiche tous les détails d'extraction
```

---

## 📖 RESSOURCES

### Documentation
- [REAL_TRAINING_COMPLETE.md](REAL_TRAINING_COMPLETE.md) - Documentation complète
- [tests/test_training_state_schema.py](tests/test_training_state_schema.py) - Tests schéma
- [tests/test_end2end_one_client.py](tests/test_end2end_one_client.py) - Tests e2e

### Fichiers Clés
- [src/rhpro/dataset_training.py](src/rhpro/dataset_training.py) - Logique principale
- [validate_training_implementation.py](validate_training_implementation.py) - Validator

### Tests
```bash
# Tous les tests
pytest tests/test_training_state_schema.py tests/test_end2end_one_client.py -v

# Avec coverage
pytest --cov=src.rhpro.dataset_training tests/test_training_state_schema.py -v
```

---

## 💡 TIPS & ASTUCES

### 1. **Performance avec Grand Dataset**

```python
# Traiter par batches
for i in range(0, 580, 50):
    result = analyze_dataset("CLIENTS", limit=50, offset=i)
    export_training_artifacts(result, f"output/training/batch_{i}")
```

### 2. **Merge de Plusieurs Runs**

```python
# Combiner learned_title_map de plusieurs analyses
import json

maps = []
for batch_dir in Path("output/training").glob("batch_*"):
    with open(batch_dir / "training_state.json") as f:
        state = json.load(f)
        maps.append(state['learned_patterns']['learned_title_map'])

# Merge
combined = {}
for m in maps:
    combined.update(m)

print(f"Total mappings: {len(combined)}")
```

### 3. **Export Excel pour Analyse**

```python
import pandas as pd

# Extraire sections_stats
sections_data = []
for canonical, stats in result.patterns['sections_stats'].items():
    sections_data.append({
        'Section': canonical,
        'Coverage': stats['coverage'],
        'Avg Lines': stats['avg_lines'],
        'P90 Lines': stats['p90_lines'],
        'Clients': stats['clients_with_section']
    })

df = pd.DataFrame(sections_data)
df.to_excel("output/sections_analysis.xlsx", index=False)
```

---

**🎉 Vous êtes prêt à utiliser le système de Real Training !**

Pour toute question, référez-vous à [REAL_TRAINING_COMPLETE.md](REAL_TRAINING_COMPLETE.md).
