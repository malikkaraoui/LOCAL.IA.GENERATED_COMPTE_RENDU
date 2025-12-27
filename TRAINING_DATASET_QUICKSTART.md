# Training Dataset - Guide Démarrage Rapide

## 🚀 Installation

```bash
# S'assurer que l'environnement virtuel est activé
source .venv/bin/activate

# Vérifier les dépendances
pip install -r requirements.txt
```

## 🎯 Workflow Complet

### 1. Training : Analyser le Dataset

```bash
streamlit run streamlit_app.py
```

1. **Navigation** : Aller à **🎓 Training & Test**
2. **Onglet** : **🎓 Training Dataset**
3. **Browse** : Sélectionner dataset root
   - Ex: `/Users/malik/Documents/RH PRO BASE DONNEE/DATASET TRAINING/BATCH 20`
4. **Configuration** :
   - Profondeur scan : `3` (défaut)
   - Limite clients : `0` (tous) ou nombre spécifique pour test
   - Merge avec existant : décocher (première fois)
5. **Lancer Training** 🚀
6. **Résultats** :
   - Métriques : clients analysés, GOLD détectés, pipeline ready, sources moy.
   - Titres inconnus : top 10 avec occurrences
   - Recommandations : actions suggérées

**Outputs générés** :
```
output/training/<dataset_id>/
├── dataset_manifest.json   # Métadonnées
├── dataset_stats.json      # Statistiques complètes
├── training_report.md      # Rapport lisible
└── training_state.json     # ★ État à réutiliser
```

### 2. Test : Générer pour un Client

1. **Onglet** : **🧪 Test Client**
2. **Sélection client** (2 méthodes) :
   
   **Méthode A - Browse direct** :
   - Sélectionner dossier client directement
   
   **Méthode B - Recherche** (recommandé) :
   - Browse dataset root
   - Entrer nom : ex `"ARIFI"`, `"Malik"`, `"Karaoui"`
   - Sélectionner dans top 5 matches
   
3. **Training State** :
   - ✅ Cocher "Utiliser training_state"
   - Browse vers `output/training/<dataset_id>/training_state.json`
   - ✅ Message : "Training state chargé (X clients)"
   
4. **Configuration** :
   - Dossier sortie : `output/test_client` (ou autre)
   - Template DOCX : laisser vide (template par défaut)
   - Mode strict : ✅ coché (recommandé)
   
5. **Run (RAG + DOCX)** 🚀

**Pipeline exécuté** :
```
Scan client
  ↓
Normalisation sandbox
  ↓
Index RAG (chunks + embeddings)
  ↓
Extraction champs (avec training_state)
  ↓
Remplissage DOCX
  ↓
Génération outputs
```

**Outputs générés** :
```
output/test_client/
├── client_01_generated.docx        # ★ Rapport rempli
├── client_01_debug.json            # Preuves + citations
├── client_01_metrics.json          # Métriques qualité
├── client_01_gold_reference.docx   # GOLD copié (si détecté)
└── client_01_validation.json       # Status GO/NO_GO/DRAFT
```

### 3. Analyser les Résultats

**Métriques affichées** :
- **Couverture** : % champs remplis (pondérée)
- **Couv. requise** : % champs obligatoires remplis
- **Confiance** : Score moyen de confiance (0-1)
- **Qualité** : Score global (0-1)

**Status validation** :
- ✅ **GO** : Qualité suffisante, prêt production
- ⚠️ **DRAFT** : Qualité moyenne, révision recommandée
- ❌ **NO_GO** : Qualité insuffisante, retravail nécessaire

**Raisons** : Liste des problèmes/warnings détectés

## 🎓 API Programmatique

### Training

```python
from src.rhpro.dataset_training import (
    analyze_dataset,
    export_training_artifacts,
)

# Analyser dataset
result = analyze_dataset(
    root_dir="/path/to/BATCH_20",
    out_dir="output/training",
    limit=None,  # Tous les clients
)

# Exporter artefacts
paths = export_training_artifacts(
    result,
    out_dir="output/training",
    merge_existing=False,  # True pour incrémental
)

print(f"Training state : {paths['training_state']}")
print(f"Clients : {result.stats['total_clients']}")
print(f"GOLD : {result.stats['gold_detection_rate']:.1%}")
```

### Test Client

```python
from src.rhpro.dataset_training import load_training_state
from src.rhpro.report_generator import generate_report_from_normalized

# Charger training_state
training_state = load_training_state(
    "output/training/<dataset_id>/training_state.json"
)

# Générer rapport
output = generate_report_from_normalized(
    normalized_client_path="sandbox/BATCH_20/client_01",
    output_dir="output/test",
    strict_mode=True,
    training_state=training_state,  # ★ Patterns appris
)

# Résultats
print(f"Qualité : {output['metrics']['quality_score']:.2f}")
print(f"Couverture : {output['metrics']['weighted_coverage']:.1f}%")
print(f"Status : {output['validation']['status']}")
```

## 🔧 Configuration Avancée

### Training Incrémental

Pour fusionner plusieurs runs (ajout de données) :

```python
paths = export_training_artifacts(
    result,
    out_dir="output/training",
    merge_existing=True,  # ★ Fusion avec existant
)
```

**Comportement** :
- Historique préservé (run_id, timestamp, nb clients)
- Comptages fusionnés (moyennes pondérées)
- Patterns combinés

### Extensions Personnalisées

Modifier dans `dataset_training.py` :

```python
exploitable_extensions = {".docx", ".pdf", ".txt", ".doc", ".msg", ".odt"}
```

## 📊 Interpréter les Patterns

### Titres Inconnus

**Exemple** :
```
Titre                          | Occurrences
-------------------------------|------------
"Parcours professionnel"       | 45
"Compétences comportementales" | 38
"Projet de formation"          | 32
```

**Action** : Ajouter mappings dans `core/field_specs.py` :
```python
TITLE_MAPPINGS = {
    "parcours professionnel": "experience_professionnelle",
    "compétences comportementales": "competences_transversales",
    ...
}
```

### Recommandations

**Type** | **Action**
---------|----------
`⚠️ Moins de 50% de GOLD détectés` | Améliorer stratégies détection GOLD
`📝 Titres inconnus fréquents` | Ajouter mappings field_specs
`📉 Moyenne sources faible` | Vérifier qualité dataset / ajouter fichiers

## 🐛 Troubleshooting

### Erreur : "LlamaIndex non disponible"

```bash
pip install llama-index llama-index-embeddings-openai llama-index-llms-openai
```

### Erreur : "OpenAI API key not found"

```bash
export OPENAI_API_KEY="sk-..."
```

Ou créer `.env` :
```
OPENAI_API_KEY=sk-...
```

### Aucun client détecté

**Vérifier** :
- Structure dataset (dossiers "NOM Prénom" ou sources >= 3)
- Profondeur scan (augmenter si structure profonde)
- Extensions supportées (`.docx`, `.pdf`, `.txt`, `.doc`)

### Score compatibilité faible

**Causes** :
- Pas de GOLD → Améliorer détection
- Peu de sources RAG → Ajouter fichiers
- Structure incomplète → Réorganiser dossiers

## ✅ Tests

### Validation Rapide

```bash
python3 validate_training_implementation.py
```

### Tests DoD

```bash
pytest -q tests/test_validation_profiles.py tests/test_end2end_one_client.py
```

### Tests Complets

```bash
pytest -v
```

## 📚 Documentation Complète

- [TRAINING_DATASET_IMPLEMENTATION.md](TRAINING_DATASET_IMPLEMENTATION.md) : Implémentation détaillée
- [TRAINING_QUICKSTART.md](TRAINING_QUICKSTART.md) : Guide UI existant
- [docs/TRAINING_UI_GUIDE.md](docs/TRAINING_UI_GUIDE.md) : Guide UI RH-Pro

## 🎯 Checklist Première Utilisation

- [ ] Environnement virtuel activé
- [ ] Dependencies installées (`pip install -r requirements.txt`)
- [ ] OpenAI API key configurée
- [ ] Dataset disponible (structure vérifiée)
- [ ] Streamlit lancé (`streamlit run streamlit_app.py`)
- [ ] Training exécuté sur dataset
- [ ] training_state.json généré
- [ ] Test client exécuté avec training_state
- [ ] Outputs vérifiés (debug.json, metrics.json, generated.docx)

---

**Date** : 27/12/2025  
**Version** : 2.2.0  
**Status** : ✅ Production Ready
