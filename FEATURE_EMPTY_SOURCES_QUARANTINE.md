# Feature: Exclusion et Quarantaine des Clients avec sources_count=0

**Date**: 2025-12-29  
**Version**: v1.2  
**Contexte**: Amélioration de la gestion des clients sans sources RAG

---

## 📋 Résumé

Cette feature implémente l'exclusion logique et la quarantaine optionnelle des dossiers clients qui n'ont aucune source RAG (`sources_count=0`).

**Problème identifié (ESSAI 100)**:
- 571 clients scannés, mais 47 avaient `sources_count=0`
- Ces clients polluent les métriques `clients_used` et `ready_*`
- Impossible de les utiliser pour l'entraînement ou la génération

**Solution**:
1. **Exclusion logique** (obligatoire): Ne plus compter les clients avec `sources=0` dans `clients_used`
2. **Quarantaine physique** (optionnel): Déplacer ces dossiers vers `data/_trash/` avec manifest

---

## 🎯 Acceptance Criteria

### AC1: Exclusion logique (✅ Obligatoire)

**Règle**:
```python
clients_scanned = len(all_clients)  # Tous détectés
clients_usable = len([c for c in all_clients if c['sources_count'] >= 1])
clients_used = clients_usable  # Par défaut
```

**Résultat ESSAI 100**:
- `clients_scanned` = 571
- `clients_usable` = 524 (exclut 47)
- `clients_used` = 524

### AC2: Reporting (✅ Obligatoire)

**Champs ajoutés dans `result.stats`**:
```python
{
    "empty_sources_clients_count": 47,
    "empty_sources_clients": [
        "CLIENT_001",
        "CLIENT_002",
        # ... (top 50 max)
    ],
    "quarantine_manifest_path": None  # ou chemin si activé
}
```

### AC3: Quarantaine physique (✅ Optionnel)

**Flag CLI**:
```bash
python demo_training_pipeline.py \
    --clients-folder CLIENTS \
    --quarantine-empty-sources  # Default: false
```

**Comportement**:
1. Déplacer (shutil.move) vers: `data/_trash/empty_sources/<run_id>/`
2. Créer `manifest.json`:
   ```json
   {
     "run_id": "abc123",
     "timestamp": "2025-12-29T10:00:00",
     "total_quarantined": 47,
     "entries": [
       {
         "client_id": "CLIENT_001",
         "path_before": "/path/to/CLIENTS/CLIENT_001",
         "path_after": "data/_trash/empty_sources/abc123/CLIENT_001",
         "timestamp": "2025-12-29T10:00:01",
         "reason": "sources_count=0"
       }
     ]
   }
   ```

**Sécurité**:
- ✅ Utilise `shutil.move()` (pas `rm -rf`)
- ✅ Try/except avec continue (ne casse pas le run)
- ✅ Log chaque opération
- ❌ JAMAIS de suppression définitive

---

## 📁 Fichiers modifiés

### 1. `src/rhpro/dataset_training.py`

**Imports ajoutés**:
```python
import shutil
import uuid
```

**Signature `analyze_dataset()`**:
```python
def analyze_dataset(
    root_dir: str,
    out_dir: str = "output/training",
    scan_depth: int = 3,
    limit: Optional[int] = None,
    validation_profile: Optional[ValidationProfile] = None,
    index_msg: bool = True,
    quarantine_empty_sources: bool = False,  # ✅ NOUVEAU
) -> DatasetTrainingResult:
```

**Logique d'exclusion** (lignes ~1640):
```python
# Identifier clients avec sources_count=0
empty_sources_clients = [c for c in successful_clients if c.get('sources_count', 0) == 0]
clients_no_sources = len(empty_sources_clients)

# clients_used exclut sources=0
clients_used_list = [c for c in successful_clients if c.get('sources_count', 0) > 0]
clients_used = len(clients_used_list)
```

**Logique de quarantaine** (lignes ~1645-1690):
```python
if quarantine_empty_sources and empty_sources_clients:
    run_id = str(uuid.uuid4())[:8]
    quarantine_base = Path("data/_trash/empty_sources") / run_id
    quarantine_base.mkdir(parents=True, exist_ok=True)
    
    for client_data in empty_sources_clients:
        try:
            dest_path = quarantine_base / client_folder_path.name
            shutil.move(str(client_folder_path), str(dest_path))
            # ... manifest entry ...
        except Exception as e:
            print(f"  ❌ Erreur quarantaine {client_id}: {e}")
            continue  # Ne pas casser le run
```

**Stats ajoutées** (lignes ~1700):
```python
result.stats = {
    # ... existing stats ...
    "empty_sources_clients_count": clients_no_sources,
    "empty_sources_clients": [c["folder_name"] for c in empty_sources_clients[:50]],
    "quarantine_manifest_path": str(quarantine_base / "manifest.json") if quarantine_manifest else None,
}
```

### 2. `tests/test_empty_sources_quarantine.py` (NEW - 500+ lignes)

**Classes de tests**:
1. `TestExcludeEmptySources` (2 tests)
   - `test_exclude_empty_sources_from_used`
   - `test_clients_usable_equals_clients_used_by_default`

2. `TestReportEmptySources` (3 tests)
   - `test_report_includes_empty_sources_count`
   - `test_report_includes_empty_sources_list`
   - `test_empty_clients_list_matches_count`

3. `TestQuarantineEmptySources` (5 tests)
   - `test_quarantine_disabled_by_default`
   - `test_quarantine_moves_folder_and_writes_manifest`
   - `test_quarantine_does_not_delete`
   - `test_quarantine_handles_errors_gracefully`
   - `test_manifest_structure`

4. `TestIntegrationEmptySourcesFeature` (3 tests)
   - `test_essai_100_expected_metrics`
   - `test_ready_rates_calculated_on_usable_only`
   - `test_quarantine_path_in_stats`

5. `TestAntiRegressionEmptySources` (2 tests)
   - `test_imports_not_broken`
   - `test_backwards_compatible_default`

---

## 🧪 Tests

### Coverage

```bash
pytest tests/test_empty_sources_quarantine.py -v
# ✅ 15 passed in 0.43s
```

### Breakdown

| Test Class | Tests | Status |
|-----------|-------|--------|
| TestExcludeEmptySources | 2 | ✅ |
| TestReportEmptySources | 3 | ✅ |
| TestQuarantineEmptySources | 5 | ✅ |
| TestIntegrationEmptySourcesFeature | 3 | ✅ |
| TestAntiRegressionEmptySources | 2 | ✅ |
| **TOTAL** | **15** | **✅** |

---

## 📊 Métriques AVANT/APRÈS (ESSAI 100)

### AVANT feature

```python
total_clients = 571
clients_used = 571  # ❌ Inclut 47 avec sources=0
clients_no_sources = 0  # ❌ Non reporté

ready_strict_rate = 450/571 = 78.8%  # ❌ Calculé sur total (inclut vides)
ready_standard_rate = 500/571 = 87.5%
ready_draft_rate = 571/571 = 100%
```

### APRÈS feature

```python
total_clients = 571
clients_scanned = 571
clients_usable = 524  # ✅ Exclut sources=0
clients_used = 524

empty_sources_clients_count = 47  # ✅ Reporté
empty_sources_clients = [...]  # ✅ Liste des IDs

# Rates calculés sur usable (524, pas 571)
ready_strict_rate = 450/524 = 85.9%  # ✅ Plus précis
ready_standard_rate = 500/524 = 95.4%
ready_draft_rate = 524/524 = 100%
```

**Gains**:
- ✅ `clients_used` reflète la réalité (524 utilisables)
- ✅ Rates plus précis (+7.1% pour STRICT, +7.9% pour STANDARD)
- ✅ Transparence totale sur clients vides (count + liste + manifest)

---

## 🚀 Utilisation

### Mode 1: Exclusion logique seule (default)

```bash
python demo_training_pipeline.py \
    --clients-folder CLIENTS \
    --output output/training_v1_2
```

**Résultat**:
- `clients_used = 524` (exclut 47 vides)
- Rapport JSON/Markdown avec liste des vides
- ❌ Aucun déplacement physique

### Mode 2: Avec quarantaine

```bash
python demo_training_pipeline.py \
    --clients-folder CLIENTS \
    --output output/training_v1_2 \
    --quarantine-empty-sources
```

**Résultat**:
- `clients_used = 524`
- 47 dossiers déplacés vers `data/_trash/empty_sources/<run_id>/`
- `manifest.json` créé avec traçabilité complète

### Vérifier la quarantaine

```bash
# Lister les runs de quarantaine
ls -la data/_trash/empty_sources/

# Voir le manifest
cat data/_trash/empty_sources/<run_id>/manifest.json | jq

# Restaurer un client (si besoin)
mv data/_trash/empty_sources/<run_id>/CLIENT_001 CLIENTS/
```

---

## 🔒 Sécurité

### ✅ Garanties

1. **Pas de suppression définitive**
   - Utilise `shutil.move()` (pas `rm`, `rmtree`, `unlink`)
   - Données préservées dans `_trash/`

2. **Traçabilité complète**
   - `manifest.json` avec timestamps
   - Paths before/after pour chaque client
   - Run ID unique (UUID)

3. **Résilience**
   - Try/except sur chaque move
   - Erreur n'arrête pas le run (log + continue)
   - Manifest écrit même en cas d'erreurs partielles

4. **Désactivé par défaut**
   - `quarantine_empty_sources=False`
   - Opt-in explicite requis

### ❌ Risques éliminés

- ❌ `shutil.rmtree()` - INTERDIT
- ❌ `Path.unlink()` - INTERDIT
- ❌ `os.remove()` - INTERDIT
- ❌ Suppression sans backup - INTERDIT

---

## 📝 Exemples de rapports

### Rapport sans quarantaine

```json
{
  "stats": {
    "total_clients": 571,
    "clients_used": 524,
    "empty_sources_clients_count": 47,
    "empty_sources_clients": [
      "ALI Mohammed",
      "ATTOU Abdelkader",
      "..."
    ],
    "quarantine_manifest_path": null
  }
}
```

### Rapport avec quarantaine

```json
{
  "stats": {
    "total_clients": 571,
    "clients_used": 524,
    "empty_sources_clients_count": 47,
    "empty_sources_clients": [...],
    "quarantine_manifest_path": "data/_trash/empty_sources/a1b2c3d4/manifest.json"
  }
}
```

### Manifest de quarantaine

```json
{
  "run_id": "a1b2c3d4",
  "timestamp": "2025-12-29T14:30:00",
  "total_quarantined": 47,
  "entries": [
    {
      "client_id": "ALI Mohammed",
      "path_before": "/path/to/CLIENTS/ALI Mohammed",
      "path_after": "data/_trash/empty_sources/a1b2c3d4/ALI Mohammed",
      "timestamp": "2025-12-29T14:30:01",
      "reason": "sources_count=0"
    }
  ]
}
```

---

## 🔄 Workflow recommandé

### Étape 1: Analyse initiale (sans quarantaine)

```bash
python demo_training_pipeline.py \
    --clients-folder CLIENTS \
    --output output/training_check
```

**Vérifier**:
```bash
cat output/training_check/training_report.json | jq '.stats.empty_sources_clients'
```

### Étape 2: Review manuel

- Analyser la liste des clients vides
- Vérifier si ce sont vraiment des dossiers à écarter
- Identifier causes (oublis upload, mauvais nommage, etc.)

### Étape 3: Quarantaine (si confirmé)

```bash
python demo_training_pipeline.py \
    --clients-folder CLIENTS \
    --output output/training_prod \
    --quarantine-empty-sources
```

### Étape 4: Validation post-quarantaine

```bash
# Vérifier que clients_used = attendu
cat output/training_prod/training_report.json | jq '.stats.clients_used'
# → 524

# Vérifier manifest
cat data/_trash/empty_sources/*/manifest.json | jq '.total_quarantined'
# → 47
```

---

## 🔗 Liens

- **Issue**: ESSAI 100 inconsistencies (571 clients, 47 vides)
- **PR précédent**: PATCH_TRAINING_STATE_v1_1.md
- **Tests**: tests/test_empty_sources_quarantine.py

---

## ✅ Checklist

- [x] AC1: Exclusion logique implémentée
- [x] AC2: Reporting des clients vides
- [x] AC3: Quarantaine optionnelle avec manifest
- [x] Tests créés (15/15 passing)
- [x] Sécurité: shutil.move (pas rm)
- [x] Résilience: try/except + continue
- [x] Default: quarantine disabled
- [x] Documentation complète

---

**Status**: ✅ Prêt pour production  
**Breaking changes**: ❌ Aucun (backwards compatible)
