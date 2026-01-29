# PATCH TRAINING_STATE v1.0 → v1.1 — Plan d'Implémentation

## 📋 Contexte

**Run problématique** : ESSAI 100 (571 clients)
- Métriques incohérentes (clients_used=571 mais 47 sans sources)
- gold_missing sans diagnostic
- 245 unknown_titles (dont beaucoup de meta/admin)
- Sections POSITIONNEMENT traitées par LLM → hallucinations
- Coverage sections très faible (ressources ~1%)

## 🎯 Objectifs (5 AC)

| AC | Description | Priorité |
|----|-------------|----------|
| AC1 | Séparer clients_scanned / clients_usable / ready_{STRICT,STANDARD,DRAFT} | ⭐⭐⭐ |
| AC2 | clients_used = clients_usable (sources>=1) | ⭐⭐⭐ |
| AC3 | Diagnostic GOLD missing par client (fichiers + raison) | ⭐⭐ |
| AC4 | POSITIONNEMENT = extract-only (CECRL/score, jamais LLM) | ⭐⭐⭐ |
| AC5 | ignored_titles pour titres admin (META/IGNORE) | ⭐⭐ |

## 📂 Fichiers à Modifier

### Core
1. `src/rhpro/dataset_training.py`
   - ✅ AC1: Calculer ready par profil (STRICT/STANDARD/DRAFT)
   - ✅ AC2: Déjà fait (clients_used exclut sources=0)
   - ⭐ AC3: Générer diagnostics GOLD missing
   - ⭐ AC5: Ajouter ignored_titles filter

2. `src/rhpro/positionnement_extractor.py`
   - ✅ Déjà créé (commit 279c3f4)
   - ⏳ AC4: Intégrer dans pipeline

3. `src/rhpro/normalizer.py` ou `src/rhpro/segmenter.py`
   - ⏳ AC4: Détecter POSITIONNEMENT et bypass LLM
   - ⏳ AC5: Filter ignored_titles

### Tests
4. `tests/test_training_state_v1_1.py` (NOUVEAU)
   - test_ac1_ready_counts_by_profile()
   - test_ac3_gold_missing_diagnostics()
   - test_ac4_positionnement_extract_only()
   - test_ac5_ignored_titles_not_in_unknown()

### UI
5. `pages_streamlit/training.py`
   - ⏳ AC1: Afficher badges STRICT/STANDARD/DRAFT

## 🔨 Implémentation Détaillée

### AC1 : Séparer ready_STRICT / ready_STANDARD / ready_DRAFT

**Problème actuel** :
```python
pipeline_ready = sum(1 for c in successful_clients if c.get("pipeline_ready"))
```
→ Compte TOUS les clients (équivalent DRAFT)

**Solution** :
```python
from src.rhpro.validation_profiles import ValidationProfile, validate_client_readiness

ready_strict = sum(1 for c in successful_clients 
                   if validate_client_readiness(c, ValidationProfile.STRICT))
ready_standard = sum(1 for c in successful_clients 
                     if validate_client_readiness(c, ValidationProfile.STANDARD))
ready_draft = sum(1 for c in successful_clients 
                  if validate_client_readiness(c, ValidationProfile.DRAFT))

result.stats.update({
    "ready_strict": ready_strict,
    "ready_standard": ready_standard,
    "ready_draft": ready_draft,
    "ready_strict_rate": ready_strict / len(successful_clients) if successful_clients else 0,
    "ready_standard_rate": ready_standard / len(successful_clients) if successful_clients else 0,
    "ready_draft_rate": ready_draft / len(successful_clients) if successful_clients else 0,
})
```

**Fichier** : `src/rhpro/dataset_training.py` ligne ~1591

---

### AC2 : clients_used = clients_usable

**Statut** : ✅ DÉJÀ FAIT (ESSAI 100)

Ligne 1600-1603 :
```python
clients_used_list = [c for c in successful_clients if c.get('sources_count', 0) > 0]
clients_used = len(clients_used_list)
clients_no_sources = len(successful_clients) - clients_used
```

**Test existant** : `tests/test_essai_100_fixes.py::test_clients_used_excludes_sources_zero`

---

### AC3 : Diagnostic GOLD missing

**Localisation actuelle** :
```python
# Ligne 1434-1450
if not scan_result.get("gold_detected"):
    gold_missing_diagnostics.append(...)
```

**Amélioration** :
```python
from src.rhpro.gold_diagnostics import diagnose_gold_missing

diagnostic = diagnose_gold_missing(
    client_folder=client_folder,
    scan_result=scan_result,
    sources_list=scan_result.get("sources", [])
)

gold_missing_diagnostics.append({
    "client_id": client_uid,
    "folder": str(client_folder),
    "sources_count": len(scan_result.get("sources", [])),
    "candidates": diagnostic["candidates"],  # [{filename, ext, score}]
    "best_attempt": diagnostic["best_attempt"],  # {filename, reason}
    "snippets": diagnostic["snippets"][:3],  # Top 3 anchor texts
    "reason_summary": diagnostic["reason"]
})
```

**Fichier** : `src/rhpro/dataset_training.py` ligne ~1434
**Module** : `src/rhpro/gold_diagnostics.py` (déjà existant depuis commit précédent)

**Output** : `output/training/gold_missing_debug.jsonl` + section markdown

---

### AC4 : POSITIONNEMENT = extract-only

**Module** : `src/rhpro/positionnement_extractor.py` ✅ créé

**Intégration** : Dans `src/rhpro/normalizer.py` ou pipeline génération

**Étape 1** : Détecter sections POSITIONNEMENT
```python
from src.rhpro.positionnement_extractor import is_positionnement_title

for segment in segments:
    if is_positionnement_title(segment['normalized_title']):
        segment['extract_policy'] = 'EXTRACT_ONLY_SCALAR'
        segment['no_llm'] = True
```

**Étape 2** : Dans pipeline génération (core/generate.py)
```python
from src.rhpro.positionnement_extractor import extract_positionnement_level

if segment.get('extract_policy') == 'EXTRACT_ONLY_SCALAR':
    # NE PAS appeler le LLM
    level = extract_positionnement_level(segment['content'])
    return {
        "value": level,
        "method": "extract_only",
        "llm_called": False
    }
```

**Fichiers** :
- `src/rhpro/normalizer.py` : Taguer les segments
- `core/generate.py` : Bypass LLM si extract_policy

---

### AC5 : ignored_titles (META/IGNORE)

**Nouvelle constante** :
```python
# src/rhpro/dataset_training.py ligne ~50 (après META_HEADERS_NORM)

IGNORED_TITLES_ADMIN = {
    "PARTICIPATION AU PROGRAMME",
    "A L ATTENTION DE",
    "OFFICE CANTONAL DES ASSURANCES SOCIALES OCAS",
    "OFFICE CANTONAL DES ASSURANCES SOCIALES",
    "OCAS",
    # Ajouter d'autres variantes normalisées
}
```

**Filter** :
```python
# Dans normalize_doc() ou équivalent
if normalized_title in IGNORED_TITLES_ADMIN:
    segment['ignored'] = True
    segment['reason'] = 'ADMIN_META'
    # NE PAS créer de section
    # NE PAS incrémenter unknown_titles
    continue
```

**Impact** :
- unknown_titles passera de ~245 à ~200-220
- Les titres admin ne pollueront plus les stats

---

## 🧪 Tests à Créer

### tests/test_training_state_v1_1.py

```python
class TestAC1ReadyByProfile:
    """AC1: Compter ready par profil (STRICT/STANDARD/DRAFT)"""
    
    def test_ready_counts_distinct(self):
        # Créer 3 mock clients: 1 STRICT, 1 STANDARD, 1 DRAFT only
        # Vérifier que ready_strict=1, ready_standard=2, ready_draft=3
        pass

class TestAC3GoldMissingDiagnostics:
    """AC3: Diagnostics GOLD missing détaillés"""
    
    def test_gold_missing_emits_diagnostics_block(self):
        # Mock 1 client GOLD missing
        # Vérifier que diagnostic contient: candidates, best_attempt, snippets, reason
        pass

class TestAC4PositionnementExtractOnly:
    """AC4: POSITIONNEMENT bypass LLM"""
    
    def test_positionnement_no_llm_call(self, mocker):
        # Mock LLM
        # Processus un segment "FRANCAIS - POSITIONNEMENT DE NIVEAU: C2"
        # Vérifier que LLM n'est jamais appelé
        # Vérifier que output = "C2"
        pass

class TestAC5IgnoredTitles:
    """AC5: Titres admin ignorés"""
    
    def test_ignored_titles_not_in_unknown(self):
        # Processus doc avec "PARTICIPATION AU PROGRAMME"
        # Vérifier que ce titre n'apparaît PAS dans unknown_titles
        pass
```

---

## 📊 Critères de Succès

### Métriques Avant/Après (ESSAI 100)

| Métrique | Avant | Après Attendu |
|----------|-------|---------------|
| clients_scanned | 571 | 571 |
| clients_usable | ❌ 571 | ✅ 524 |
| clients_no_sources | ❌ 0 (implicite) | ✅ 47 |
| ready_strict | ❌ N/A | ✅ ~450 (78%) |
| ready_standard | ❌ N/A | ✅ ~500 (87%) |
| ready_draft | ❌ 571 (100%) | ✅ 524 (100% des usable) |
| gold_missing_diagnostics | ❌ 10 sans détail | ✅ 10 avec raisons |
| unknown_titles count | 245 | ~200 (après filter admin) |
| POSITIONNEMENT hallucinations | ❌ OUI (listes inventées) | ✅ NON (valeurs extraites) |

---

## 🚀 Ordre d'Implémentation Recommandé

### Phase 1 : Quick Wins (1-2h)
1. ✅ AC2: Déjà fait
2. ⭐ AC5: Ajouter IGNORED_TITLES_ADMIN (30min)
3. ⭐ AC1: Calculer ready par profil (30min)

### Phase 2 : Intégrations (2-3h)
4. ⭐ AC4: Intégrer positionnement_extractor dans pipeline (1h)
5. ⭐ AC3: Enrichir diagnostics GOLD missing (1h)

### Phase 3 : Tests & Validation (1h)
6. Créer tests/test_training_state_v1_1.py
7. Re-run ESSAI 100 et valider métriques

### Phase 4 : UI (30min)
8. Modifier pages_streamlit/training.py pour afficher badges

---

## 📝 Documentation

**Fichier** : `PATCH_TRAINING_STATE_v1_1.md`

Contenu :
- Problèmes résolus (5 AC)
- Changements techniques
- Tests ajoutés
- Métriques avant/après
- Impact utilisateur

---

## ✅ Checklist Pré-Commit

- [ ] AC1: ready_{STRICT,STANDARD,DRAFT} calculés
- [ ] AC2: clients_used vérifié (déjà OK)
- [ ] AC3: gold_missing_diagnostics enrichis
- [ ] AC4: POSITIONNEMENT extract-only intégré
- [ ] AC5: IGNORED_TITLES_ADMIN appliqué
- [ ] Tests créés et passent (5 nouveaux tests min)
- [ ] Documentation PATCH_TRAINING_STATE_v1_1.md
- [ ] Re-run ESSAI 100 validé
- [ ] UI streamlit mise à jour

---

**Status** : 🟡 EN COURS
**Commit Target** : `feat(training): Patch v1.1 — ready par profil + GOLD diagnostics + extract-only POSITIONNEMENT`
