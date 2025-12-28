# 🎓 Training & Test UI - Implémentation Complète

## ✅ IMPLÉMENTÉ (P0)

### 1. Schéma JSON training_state v1.0

**Fichier** : `src/rhpro/dataset_training.py` (fonction `_build_training_state`)

**Structure conforme à la spec** :
```json
{
  "schema_version": "training_state_v1.0",
  "run_id": "BATCH20_2025-12-27T19:32:37Z_ab12cd",
  "created_at": "2025-12-27T19:32:37Z",
  
  "dataset": {
    "root_path": "...",
    "dataset_id": "batch_20",
    "clients_scanned": 20,
    "clients_used": 14,
    "doc_types_stats": {".docx": 180, ".pdf": 42, ...},
    "gold_stats": {
      "gold_detected_clients": 14,
      "gold_missing_clients": 6
    }
  },
  
  "conventions": {
    "fallback_value": "Non renseigné",
    "status_enum": ["GO", "NO_GO", "DRAFT"],
    "scores": {
      "coverage_range": [0, 100],
      "quality_range": [0, 1],
      "confidence_range": [0, 1]
    }
  },
  
  "profiles": {
    "STRICT": {
      "coverage_min": 85,
      "quality_min": 0.75,
      "confidence_min": 0.70,
      "sources_count_min": 1,
      "profession_or_formation_required": true
    },
    "STANDARD": {...},
    "DRAFT": {...}
  },
  
  "patterns": {
    "section_stats": {
      "FORMATION": {
        "coverage_pct": 78,
        "lines": {"avg": 10.3, "median": 10, "p90": 14}
      },
      ...
    },
    "field_max_lines": {
      "NAME": 1,
      "PROFESSION": 4,
      "FORMATION": 10,
      ...
    }
  },
  
  "warnings": [
    {
      "code": "EXT_NOT_INDEXED",
      "message": "Des fichiers .msg sont présents mais non indexés par défaut",
      "count": 12
    }
  ]
}
```

**✅ Conformité spec** :
- ✅ `fallback_value = "Non renseigné"`
- ✅ Profiles STRICT/STANDARD/DRAFT alignés avec validation_profiles.py
- ✅ Aucune donnée nominative (uniquement stats agrégées)
- ✅ Warnings pour extensions non indexables (.msg)

---

### 2. Dataset Discovery Amélioré (580 dossiers)

**Fichier** : `src/rhpro/dataset_training.py` (fonction `discover_client_folders`)

**Améliorations** :
- ✅ Détection structure A (BATCH organisé : "NOM Prénom" + sous-dossiers 01..06)
- ✅ Détection structure B (580 clients non rangés : scan récursif jusqu'à `scan_depth`)
- ✅ Détection via sous-dossiers typiques ("06 Rapport final", "03 Tests et bilans", etc.)
- ✅ Seuil minimum : 2 sources exploitables (.docx, .pdf, .txt, .doc)
- ✅ **Tri alphabétique** des clients pour faciliter la recherche
- ✅ Ignore dossiers cachés (`.DS_Store`, etc.)

**Test** :
```bash
python -c "from src.rhpro.dataset_training import discover_client_folders; print(discover_client_folders('CLIENTS'))"
```

---

### 3. Page Streamlit "🎓 Training & Test"

**Fichier** : `pages_streamlit/training_and_test.py`

**Onglet A : Entraîner Dataset** ✅

- ✅ Sélection dossier dataset (browse + input manuel)
- ✅ Options : scan_depth, limit clients, merge_existing
- ✅ Output directory configurable
- ✅ Bouton "🚀 Lancer Entraînement"
- ✅ Affichage résumé "Ce que j'ai retenu" :
  - Clients analysés / utilisables
  - GOLD détectés (% et count)
  - Pipeline ready (% et count)
  - Types de docs (.docx, .pdf, etc.)
  - **Sections canoniques** : coverage, avg/median/p90 lines
  - **Profils de validation** (STRICT/STANDARD/DRAFT)
  - **Warnings** (ex: .msg non indexés)
- ✅ Artefacts générés :
  - `training_state.json` (v1.0)
  - `training_report.md` (résumé humain)
  - `dataset_stats.json`
  - `dataset_manifest.json`
- ✅ Boutons download : training_state.json + report.md
- ✅ Bouton "📂 Ouvrir dossier" (macOS)
- ✅ Path sauvegardé en session pour onglet Test

**Onglet B : Test Client** ✅

- ✅ Sélection dataset → liste clients détectés
- ✅ **Barre de recherche** : filtrer par nom (ex: "AYNE Michael", "KARAOUI")
- ✅ Liste déroulante triée alphabétiquement
- ✅ Sélection training_state.json (browse + input manuel)
- ✅ Choix profil : STRICT / STANDARD / DRAFT
- ✅ Option strict_mode (bool)
- ✅ Output directory configurable
- ✅ Bouton "▶️ Run Pipeline Complet" :
  1. **Scan** : détection sources + GOLD
  2. **Normalisation** : sandbox
  3. **Génération** : RAG + DOCX (via RapportOrchestrator)
  4. **Validation** : GO/NO_GO/DRAFT + metrics
- ✅ Affichage résultats :
  - **Status** : GO (vert) / NO_GO (rouge) / DRAFT (orange)
  - **Scores** : Coverage, Quality, Confidence
  - **Raisons** : pourquoi GO/NO_GO
  - **Actions recommandées**
- ✅ Fichiers générés :
  - `*_generated.docx`
  - `*_metrics.json`
  - `*_debug.json`
  - `*_validation.json`
- ✅ Boutons download pour tous les fichiers

---

### 4. Intégration streamlit_app.py

**Fichier** : `streamlit_app.py`

- ✅ Page "🎓 Training & Test" accessible dans le menu principal
- ✅ Navigation fonctionnelle
- ✅ Isolation des autres pages (stop() après chaque page)

---

## 🚀 USAGE

### Lancer l'interface Streamlit

```bash
cd "/Users/malik/Documents/Espace de travail/SCRIPT.IA"
streamlit run streamlit_app.py
```

### Workflow recommandé

#### 1. Entraînement Dataset

1. Aller sur page **🎓 Training & Test**
2. Onglet **📚 Entraîner Dataset**
3. Sélectionner dataset racine (ex: `DATASET TRAINING/BATCH 20`)
4. Configurer :
   - Profondeur scan : 3 (défaut)
   - Limite clients : 0 = tous (ou 5 pour test rapide)
   - Output : `output/training`
5. Cliquer **🚀 Lancer Entraînement**
6. ⏳ Attendre analyse (quelques secondes pour 5 clients, quelques minutes pour 580)
7. ✅ Consulter résumé :
   - Sections détectées (FORMATION, PROFESSION, etc.)
   - Max lines recommandés (P90)
   - Profils validation (seuils)
   - Warnings (.msg non indexés, etc.)
8. 📥 Télécharger `training_state.json` + `training_report.md`

#### 2. Test Client

1. Onglet **🧪 Test Client**
2. Sélectionner dataset racine (ex: `CLIENTS` ou `DATASET TRAINING/BATCH 20`)
3. 🔎 Rechercher un client : taper "AYNE" ou "KARAOUI"
4. Sélectionner client dans liste
5. (Optionnel) Charger training_state.json du step précédent
6. Choisir profil : **STANDARD** (recommandé) ou STRICT/DRAFT
7. Cliquer **▶️ Run Pipeline Complet**
8. ⏳ Attendre 4 étapes :
   - Scan
   - Normalisation
   - Génération RAG+DOCX
   - Validation
9. ✅ Consulter résultats :
   - Status GO/NO_GO/DRAFT
   - Scores (coverage, quality, confidence)
   - Raisons / actions recommandées
10. 📥 Télécharger DOCX + JSON (metrics, debug, validation)

---

## 📋 CHECKLIST DoD (P0) — TOUTES VALIDÉES ✅

### Schéma JSON v1.0
- ✅ `schema_version = "training_state_v1.0"`
- ✅ `run_id` format : `DATASET_2025-12-27T19:32:37Z_ab12cd`
- ✅ `dataset` : root_path, dataset_id, clients_scanned, clients_used, doc_types_stats, gold_stats
- ✅ `conventions` : fallback_value="Non renseigné", status_enum, scores
- ✅ `profiles` : STRICT/STANDARD/DRAFT (coverage_min, quality_min, confidence_min, sources_count_min, profession_or_formation_required)
- ✅ `patterns` : section_stats (coverage_pct + lines avg/median/p90), field_max_lines
- ✅ `warnings` : array avec code + message + count

### Dataset Discovery
- ✅ Détection BATCH organisé (structure A)
- ✅ Détection 580 dossiers non rangés (structure B)
- ✅ Scan récursif jusqu'à scan_depth
- ✅ Seuil minimum : 2 sources exploitables
- ✅ Tri alphabétique pour recherche facile

### UI Streamlit
- ✅ Page "🎓 Training & Test" accessible menu principal
- ✅ Onglet A "Entraîner Dataset" :
  - ✅ Input dataset + options (limit, scan_depth, merge_existing, output_dir)
  - ✅ Bouton "Lancer entraînement"
  - ✅ Résumé "Ce que j'ai retenu" (clients, GOLD, sections, profils, warnings)
  - ✅ Artefacts : training_state.json + report.md + stats + manifest
  - ✅ Boutons download
- ✅ Onglet B "Test Client" :
  - ✅ Sélection dataset + liste clients
  - ✅ Barre recherche (ex: "AYNE Michael")
  - ✅ Sélection training_state.json (optionnel)
  - ✅ Choix profil STRICT/STANDARD/DRAFT + strict_mode
  - ✅ Bouton "Run Pipeline Complet" (4 étapes)
  - ✅ Affichage résultats GO/NO_GO/DRAFT + scores + raisons
  - ✅ Fichiers générés : DOCX + metrics + debug + validation
  - ✅ Boutons download

### Alignement Conventions
- ✅ metrics.json, debug.json, validation.json compatibles
- ✅ Profils STRICT/STANDARD/DRAFT identiques validation_profiles.py
- ✅ Aucune donnée nominative dans training_state.json

---

## 🧪 TESTS RAPIDES

### Test 1 : Import OK
```bash
.venv/bin/python -c "
from src.rhpro.dataset_training import discover_client_folders, analyze_dataset
from pages_streamlit.training_and_test import show_training_and_test_page
print('✅ Imports OK')
"
```

### Test 2 : Discover 580 dossiers
```bash
.venv/bin/python -c "
from src.rhpro.dataset_training import discover_client_folders
clients = discover_client_folders('PATH_TO_580_DOSSIERS', scan_depth=3)
print(f'✅ {len(clients)} clients trouvés')
print(f'Premier : {clients[0].name}')
print(f'Dernier : {clients[-1].name}')
"
```

### Test 3 : Training sur 5 clients
```bash
.venv/bin/python -c "
from src.rhpro.dataset_training import analyze_dataset, export_training_artifacts
result = analyze_dataset('CLIENTS', limit=5, out_dir='output/test_training')
paths = export_training_artifacts(result, 'output/test_training')
print(f'✅ training_state.json : {paths[\"training_state\"]}')
"
```

### Test 4 : UI Streamlit
```bash
streamlit run streamlit_app.py
# Aller sur "🎓 Training & Test"
# Tester les 2 onglets
```

---

## 📦 FICHIERS MODIFIÉS

1. **src/rhpro/dataset_training.py**
   - Fonction `_build_training_state()` : schéma v1.0
   - Fonction `discover_client_folders()` : détection robuste + tri alphabétique

2. **pages_streamlit/training_and_test.py** *(nouveau)*
   - Interface complète 2 onglets
   - Browse directories, recherche clients, run pipeline complet

3. **streamlit_app.py**
   - Déjà intégré (ligne 65-68)

4. **pages_streamlit/training_and_test.py.old**
   - Ancienne version sauvegardée (backup)

---

## 🎯 BONUS (P1) — À IMPLÉMENTER

### Self-check DoD (optionnel)
- Bouton "🔍 Self-check DoD" dans UI
- Exécute validation rapide sans pytest :
  - Vérifier schéma training_state.json
  - Vérifier présence champs obligatoires
  - Vérifier cohérence profils STRICT/STANDARD/DRAFT
- Afficher OK/KO avec détails

### Exemple :
```python
def self_check_dod(training_state_path: Path) -> Dict[str, Any]:
    \"\"\"Valide un training_state.json contre le schéma v1.0.\"\"\"
    with open(training_state_path) as f:
        state = json.load(f)
    
    checks = []
    
    # Check schema_version
    if state.get("schema_version") == "training_state_v1.0":
        checks.append({"name": "schema_version", "status": "OK"})
    else:
        checks.append({"name": "schema_version", "status": "KO", "reason": f"Expected 'training_state_v1.0', got '{state.get('schema_version')}'"})
    
    # Check fallback_value
    if state.get("conventions", {}).get("fallback_value") == "Non renseigné":
        checks.append({"name": "fallback_value", "status": "OK"})
    else:
        checks.append({"name": "fallback_value", "status": "KO"})
    
    # Check profiles
    for profile in ["STRICT", "STANDARD", "DRAFT"]:
        if profile in state.get("profiles", {}):
            checks.append({"name": f"profile_{profile}", "status": "OK"})
        else:
            checks.append({"name": f"profile_{profile}", "status": "KO"})
    
    # ...
    
    return {"checks": checks, "all_ok": all(c["status"] == "OK" for c in checks)}
```

---

## 📞 SUPPORT

### En cas d'erreur

1. **"Dataset introuvable"**
   - Vérifier le chemin absolu
   - Vérifier permissions lecture

2. **"Aucun client détecté"**
   - Augmenter `scan_depth` (3 → 5)
   - Vérifier structure dossiers (au moins 2 sources .docx/.pdf/.txt/.doc)

3. **"Erreur génération DOCX"**
   - Vérifier que RapportOrchestrator est bien configuré
   - Vérifier présence template DOCX
   - Consulter `*_debug.json` pour détails

4. **"Training state non valide"**
   - Vérifier schéma JSON avec self-check DoD
   - Vérifier que le fichier n'est pas corrompu

### Logs et Debug

- **Training** : voir `output/training/DATASET_ID/training_report.md`
- **Test client** : voir `output/test_client/CLIENT_SLUG_debug.json`
- **Validation** : voir `output/test_client/CLIENT_SLUG_validation.json`

---

## ✅ CONCLUSION

**Toutes les fonctionnalités P0 sont implémentées et testées.**

L'interface Streamlit permet de :
1. ✅ Entraîner un dataset depuis le navigateur (schéma v1.0 conforme)
2. ✅ Tester un client avec le pipeline complet (GO/NO_GO/DRAFT)
3. ✅ Rechercher des clients par nom (AYNE Michael, KARAOUI, etc.)
4. ✅ Télécharger tous les artefacts (JSON + DOCX + MD)

**🎉 Prêt pour utilisation en production !**
