# 📚 Guide Training - Dataset & Analyse

**Version** : 4.1  
**Dernière mise à jour** : 28 décembre 2025

Ce guide explique comment utiliser le module Training pour analyser vos données clients et construire un dataset de patterns pour améliorer la génération.

---

## 🎯 Objectif

Le **Training** permet de :
1. **Analyser** massivement vos dossiers clients existants
2. **Extraire** des patterns récurrents (sections, champs, structures)
3. **Générer** un `training_state.json` pour optimiser la génération
4. **Détecter** les données GOLD (AVS fiables, structure cohérente)
5. **Valider** la qualité avec scoring automatique

---

## 🚀 Quickstart

### 1. Lancer l'interface Training

```bash
streamlit run pages_streamlit/training_and_test.py
```

### 2. Choisir votre mode

**Mode Test** (recommandé pour débuter) :
- ✅ Limite : 5 clients
- ✅ Profondeur : 3 documents max/client
- ✅ Merge : OFF (analyse isolée)
- ✅ Rapide : ~30 sec

**Mode Batch** (production) :
- ✅ Limite : 0 (tous les clients)
- ✅ Profondeur : 4 documents max/client
- ✅ Merge : ON (incrémental)
- ✅ Complet : ~10-30 min selon corpus

### 3. Cliquer sur "🔄 Lancer le training"

L'analyse va :
1. Scanner le dossier CLIENTS/
2. Extraire les sources (PDF/DOCX/TXT/DOC/MSG)
3. Analyser la structure
4. Générer training_state.json

---

## 📖 Concepts Clés

### 1. Scan Depth (Profondeur)

**Définition** : Nombre max de documents analysés **par client**.

| Profondeur | Usage | Performance | Fiabilité |
|------------|-------|-------------|-----------|
| 1 | Test rapide | ~5 sec/client | ⚠️ Faible |
| 2 | Validation | ~10 sec/client | 🔵 Moyenne |
| 3 | **Recommandé** | ~15 sec/client | ✅ Bonne |
| 4+ | Production | ~20+ sec/client | ✅ Optimale |

**Conseil** : Commencez avec 2-3 pour tests, puis 4+ en production.

### 2. Limite Clients

**Définition** : Nombre max de clients analysés.

- **0** : Tous les clients (Mode Batch complet)
- **5** : Mode Test (rapide, validations)
- **10-50** : Mode Partiel (sous-échantillon)

**Conseil** : Utilisez `limit=5` pour vos premiers tests, puis `limit=0` pour production.

### 3. Merge Incrémental

**Définition** : Fusionne avec le training_state.json existant.

**Activé** (recommandé en production) :
- ✅ Conserve les patterns découverts précédemment
- ✅ Enrichit progressivement le dataset
- ✅ Agrège stats (max pour field_max_lines, max p90/coverage pour sections)

**Désactivé** (tests/développement) :
- Analyse isolée
- Écrase le training_state.json précédent
- Utile pour comparer versions

**Conseil** : Merge ON en production, OFF pour tests A/B.

---

## 📊 training_state.json : Structure

### Vue d'ensemble

```json
{
  "run_id": "train_20251228_143022",
  "created_at": "2025-12-28T14:30:22",
  "dataset": {
    "clients_used": 25,
    "total_sources": 87,
    "formats": {"pdf": 45, "docx": 30, "txt": 12}
  },
  "patterns": {
    "section_stats": { ... },
    "field_max_lines": { ... },
    "unknown_titles_top": [ ... ]
  },
  "warnings": [ ... ]
}
```

### Section 1 : Métadonnées

```json
"run_id": "train_20251228_143022",
"created_at": "2025-12-28T14:30:22"
```

- **run_id** : Identifiant unique de l'analyse
- **created_at** : Timestamp ISO 8601

### Section 2 : Dataset

```json
"dataset": {
  "clients_used": 25,
  "total_sources": 87,
  "formats": {"pdf": 45, "docx": 30, "txt": 12},
  "scan_depth": 4,
  "client_limit": 0
}
```

- **clients_used** : Nombre réel de clients analysés
- **total_sources** : Nombre total de documents extraits
- **formats** : Répartition par type (PDF, DOCX, TXT, DOC, MSG)
- **scan_depth** : Profondeur configurée
- **client_limit** : Limite clients configurée (0 = tous)

### Section 3 : Section Stats

```json
"section_stats": {
  "Expérience professionnelle": {
    "coverage_pct": 92.5,
    "clients_count": 87,
    "lines_avg": 25.3,
    "lines_median": 22,
    "lines_p90": 45
  }
}
```

**Métriques par section** :
- **coverage_pct** ∈ [0..100] : % clients contenant cette section
- **clients_count** : Nombre absolu de clients concernés
- **lines_avg** : Moyenne lignes dans la section
- **lines_median** : Médiane lignes
- **lines_p90** : Percentile 90 (valeur max pour 90% des cas)

**Contraintes validation** :
- ✅ coverage_pct ≤ 100
- ✅ clients_count ≤ clients_used
- ✅ lines_p90 ≥ lines_median ≥ lines_avg ≥ 1

### Section 4 : Field Max Lines

```json
"field_max_lines": {
  "nom": 2,
  "prenom": 2,
  "adresse": 3,
  "experiences_professionnelles": 50,
  "formations": 30
}
```

**Objectif** : Limiter la taille des champs générés pour éviter tokens excessifs.

**Valeurs** :
- **Champs courts** (nom, prénom) : 1-3 lignes
- **Champs moyens** (adresse, email) : 3-5 lignes
- **Champs longs** (expériences, compétences) : 20-50 lignes

**Merge** : Prend le **max** entre existant et nouveau (jamais de régression).

### Section 5 : Unknown Titles Top

```json
"unknown_titles_top": [
  {"title": "Projet réalisés", "count": 12},
  {"title": "References", "count": 8}
]
```

**Objectif** : Identifier les sections non reconnues pour enrichir le prompt.

**Usage** :
- Détecter variantes orthographiques
- Ajouter sections personnalisées
- Améliorer coverage

---

## 🔍 Détection GOLD

### Critères GOLD

Un dossier client est **GOLD** si :
1. ✅ **AVS détectés** : ≥ 2 numéros AVS dans les sources
2. ✅ **Structure cohérente** : ≥ 3 sections reconnues
3. ✅ **Volume suffisant** : ≥ 500 lignes total

**Importance** :
- Données GOLD = haute confiance
- Utilisées prioritairement pour patterns
- Scoring production gate

### AVS : Format Suisse

**Format** : `756.XXXX.XXXX.XX` (13 chiffres)

Exemples :
- ✅ `756.1234.5678.90`
- ✅ `7561234567890` (sans points)
- ❌ `123.4567.8901.23` (pas 756)

**Extraction** :
- Regex : `\b756[.\s]?\d{4}[.\s]?\d{4}[.\s]?\d{2}\b`
- Normalisation : suppression points/espaces
- Validation : checksum Luhn (optionnel)

---

## 📈 Analyse des Stats

### Coverage Optimal

| Section | Coverage Cible | Interprétation |
|---------|----------------|----------------|
| Identité | 95-100% | ✅ Essentiel |
| Expériences | 80-95% | ✅ Très fréquent |
| Formations | 70-85% | ✅ Fréquent |
| Compétences | 60-75% | 🔵 Courant |
| Langues | 50-65% | 🔵 Variable |
| Loisirs | 10-30% | ⚠️ Optionnel |

**Conseil** : Si coverage < 50%, la section est probablement peu fiable.

### Lines P90 : Seuils

| Champ | P90 Attendu | Action si dépassé |
|-------|-------------|-------------------|
| Nom | 1-2 | ⚠️ Erreur extraction |
| Prénom | 1-2 | ⚠️ Erreur extraction |
| Adresse | 3-5 | OK |
| Email | 1-2 | OK |
| Téléphone | 1-2 | OK |
| Expériences | 30-60 | OK si détaillées |
| Formations | 20-40 | OK |
| Compétences | 10-30 | OK |

**P90 > 100** : Probable problème (parsing, mise en page).

---

## 🎛️ Configuration Avancée

### Fichier config : dataset_training.py

```python
# Extensions supportées
exploitable_extensions = {".docx", ".pdf", ".txt", ".doc", ".msg"}

# Limites extraction
MAX_TEXT_LENGTH = 500_000  # Caractères max/document
MAX_LINES_PER_SECTION = 200  # Lignes max/section

# Paramètres analyse
MIN_LINES_FOR_STATS = 5  # Min lignes pour stats valides
MIN_CLIENTS_FOR_COVERAGE = 3  # Min clients pour coverage
```

### Paramètres Streamlit

```python
# Pages_streamlit/training_and_test.py

# Presets
MODE_TEST = {"limit": 5, "depth": 3, "merge": False}
MODE_BATCH = {"limit": 0, "depth": 4, "merge": True}

# Affichage
show_warnings = True  # Afficher warnings
show_provenance = True  # Afficher provenance patterns
export_markdown = True  # Export rapport MD
```

---

## ⚠️ Warnings & Troubleshooting

### Warnings Courants

#### MSG_EXTRACTOR_MISSING
```
Warning: extract-msg non installé, fichiers .msg ignorés
```
**Solution** :
```bash
pip install extract-msg>=0.48.0
```

#### LOW_COVERAGE
```
Warning: Section "Langues" coverage = 35% < 50%
```
**Interprétation** : Section peu présente, patterns peu fiables.

#### HIGH_P90
```
Warning: Champ "nom" p90 = 15 lignes (attendu < 3)
```
**Action** : Vérifier parsing, mise en page sources.

#### UNKNOWN_TITLES_HIGH
```
Warning: 25 titres inconnus détectés
```
**Action** : Enrichir prompt avec variantes.

### Erreurs Fatales

#### NO_CLIENTS_FOUND
```
Error: Aucun client trouvé dans CLIENTS/
```
**Solution** : Vérifier structure dossiers (CLIENTS/<nom_client>/).

#### EXTRACTION_FAILED
```
Error: Échec extraction 80% des sources
```
**Solution** : 
- Vérifier formats supportés
- Installer LibreOffice (soffice) pour .doc
- Vérifier permissions fichiers

#### INVALID_TRAINING_STATE
```
Error: training_state.json corrompu
```
**Solution** :
- Supprimer training_state.json
- Relancer training avec merge=False

---

## 🚀 Workflow Recommandé

### Phase 1 : Découverte (1ère fois)

```bash
# 1. Test rapide (5 clients)
Mode Test → scan_depth=2, limit=5, merge=OFF

# 2. Validation résultats
- Coverage ≥ 50% pour sections importantes ?
- P90 cohérent ?
- Warnings acceptables ?

# 3. Ajustements
- Si coverage faible : augmenter scan_depth
- Si P90 bizarre : vérifier parsing sources
- Si warnings critiques : résoudre avant batch
```

### Phase 2 : Production (routine)

```bash
# 1. Batch complet initial
Mode Batch → scan_depth=4, limit=0, merge=OFF

# 2. Batch incrémental (nouveau corpus)
Mode Batch → scan_depth=4, limit=0, merge=ON

# 3. Validation continue
- Exporter rapport MD
- Vérifier évolution coverage
- Monitorer warnings
```

### Phase 3 : Maintenance (mensuelle)

```bash
# 1. Analyse complète
Mode Batch → scan_depth=4, limit=0, merge=OFF

# 2. Comparer avec précédent
- Coverage amélioré ?
- P90 stable ?
- Nouveaux patterns ?

# 3. Nettoyer si besoin
- Supprimer dossiers obsolètes
- Archiver anciens training_state
```

---

## 📊 Métriques de Succès

### Bon Dataset

✅ **Clients** : ≥ 50 clients analysés  
✅ **Coverage** : ≥ 80% pour sections core (identité, expériences, formations)  
✅ **P90** : Cohérent avec attentes (voir tableau)  
✅ **Warnings** : < 5 warnings critiques  
✅ **GOLD** : ≥ 30% clients GOLD détectés

### Dataset à Améliorer

⚠️ **Clients** : < 20 clients  
⚠️ **Coverage** : < 50% sections core  
⚠️ **P90** : Valeurs aberrantes (> 100)  
⚠️ **Warnings** : > 10 warnings critiques  
⚠️ **GOLD** : < 10% clients GOLD

---

## 🔗 Intégration Pipeline

### 1. Training → Production Gate

```python
# Après training
training_state = load_training_state()

# Validation automatique
from src.rhpro.production_gate import ProductionGate
gate = ProductionGate(profile="normal")
score = gate.evaluate(training_state)

if score.go_decision == "GO":
    print("✅ Dataset validé, prêt pour génération")
elif score.go_decision == "WARNING":
    print("⚠️ Dataset acceptable, vérifier warnings")
else:
    print("❌ Dataset insuffisant, refaire training")
```

### 2. Training → Génération

```python
# core/generate.py utilise training_state.json automatiquement

# Field max lines appliqué
experiences = generate_field(
    "experiences_professionnelles",
    max_lines=training_state["patterns"]["field_max_lines"]["experiences_professionnelles"]
)

# Section stats pour priorisation
sections_by_coverage = sorted(
    training_state["patterns"]["section_stats"].items(),
    key=lambda x: x[1]["coverage_pct"],
    reverse=True
)
```

---

## 📚 Ressources

### Fichiers Clés

- **Code** : `src/rhpro/dataset_training.py`
- **UI** : `pages_streamlit/training_and_test.py`
- **Tests** : `tests/test_training_state_integrity.py`
- **Config** : training_state.json (auto-généré)

### Commandes Utiles

```bash
# Lancer training UI
streamlit run pages_streamlit/training_and_test.py

# Tests intégrité
pytest tests/test_training_state_integrity.py -v

# Validation training_state.json
python validate_training_implementation.py

# Export rapport
python demo_training_pipeline.py --export
```

### Documentation Connexe

- [GUIDE_GENERATION.md](GUIDE_GENERATION.md) - Utilisation patterns training
- [API_REFERENCE.md](API_REFERENCE.md) - API dataset_training
- [HISTORIQUE_IMPLEMENTATION.md](HISTORIQUE_IMPLEMENTATION.md) - Évolution features

---

**Maintenu par** : Équipe SCRIPT.IA  
**Dernière revue** : 28 décembre 2025
