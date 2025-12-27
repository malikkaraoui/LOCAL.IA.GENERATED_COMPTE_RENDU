# Tests Definition of Done (DoD) - RH-Pro Validation

## Vue d'ensemble

Deux fichiers de tests ont été créés pour prévenir **toute régression** sur le système de validation GO/NO_GO :

1. **`tests/test_validation_profiles.py`** : Tests unitaires de validation  
2. **`tests/test_end2end_one_client.py`** : Test d'intégration E2E

---

## 🔒 Contraintes STRICTES

### Absolument INTERDITES ("au fer rouge") :
- ❌ **Aucun appel réseau** (OpenAI, embeddings, LLM)
- ❌ **Aucune donnée réelle RH-Pro** (utilisation de données fictives uniquement)
- ❌ **Tests non déterministes** (résultats doivent être 100% reproductibles)

### Requis :
- ✅ **100% local** : tout se passe dans `tmp_path` ou fixtures
- ✅ **Rapide** : exécution en quelques secondes
- ✅ **Déterministe** : mêmes entrées → mêmes sorties
- ✅ **Complet** : vérifier la **cohérence** entre status et métriques

---

## 1️⃣ Tests Unitaires (`test_validation_profiles.py`)

### Objectif
Tester la logique de validation (`validation_profiles.py`) avec des **données JSON fictives**.

### Couverture

#### Profil STRICT (8 cas de test)
1. **`strict_all_ok`** : Toutes les conditions remplies → **GO**
   - Coverage ≥ 85%, quality ≥ 0.75, confidence ≥ 0.70
   - Nom + prénom présents, profession/formation OK, ≥ 1 source
   
2. **`strict_missing_nom`** : Nom manquant → **NO_GO**
   - Champ critique manquant dans l'identité
   
3. **`strict_missing_prenom`** : Prénom manquant → **NO_GO**
   - Champ critique manquant dans l'identité
   
4. **`strict_no_sources`** : Aucune source RAG → **NO_GO**
   - `sources_count = 0`
   
5. **`strict_no_profession_no_formation`** : Ni profession ni formation → **NO_GO**
   - Champs professionnels critiques manquants
   
6. **`strict_low_coverage`** : Coverage < 85% → **NO_GO**
   - Métriques insuffisantes
   
7. **`strict_low_quality`** : Quality score < 0.75 → **NO_GO**
   - Score qualité trop faible
   
8. **`strict_low_confidence`** : Confidence < 0.70 → **NO_GO**
   - Confiance moyenne insuffisante

#### Profil STANDARD (3 cas de test)
1. **`standard_ok`** : Données complètes → **GO**
   - Seuils : coverage ≥ 75%, quality ≥ 0.65
   
2. **`standard_one_missing_ok`** : 1 champ manquant toléré → **GO**
   - Max 1 champ critique manquant autorisé
   
3. **`standard_low_coverage`** : Coverage < 75% → **NO_GO**

#### Profil DRAFT (2 cas de test)
1. **`draft_minimal`** : Données minimales → **DRAFT**
   - Aucun blocage même avec métriques faibles
   
2. **`draft_good_data`** : Bonnes données → **DRAFT**
   - Toujours DRAFT (jamais GO/NO_GO)

#### Test de structure (1 cas)
- **`test_validation_result_structure`** : Vérifie que `ValidationResult` a :
  - `status`, `profile`, `reasons`, `actions`, `scores`

### Vérifications Anti-Régression 🔐

Chaque test vérifie la **COHÉRENCE** :

```python
# Si status = GO → métriques DOIVENT respecter les seuils
if status == "GO":
    assert coverage >= 0.85
    assert quality >= 0.75
    assert confidence >= 0.70
    assert sources_count >= 1
    assert len(missing_critical) == 0

# Si status = NO_GO → au moins UNE condition bloquante
if status == "NO_GO":
    assert len(reasons) > 0
    assert len(actions) > 0
    assert (condition_bloquante_trouvée)
```

### Exécution

```bash
# Tous les tests unitaires
pytest tests/test_validation_profiles.py -v

# Un test spécifique
pytest tests/test_validation_profiles.py::test_validation_strict_profile -v

# Tests rapides uniquement (skip E2E)
pytest tests/test_validation_profiles.py -v
```

**Résultat attendu** : ✅ **14 passed** (en ~0.2s)

---

## 2️⃣ Test E2E (`test_end2end_one_client.py`)

### Objectif
Tester le **pipeline complet** : `normalize → index → generate → validate`

### Architecture

#### Fixtures
1. **`mini_client_folder`** : Crée un mini-dossier client fictif
   - `cv.txt` : identité + profession
   - `entretien.txt` : compléments
   - `formation.txt` : formation
   
2. **`mock_rag_components`** : Patche LlamaIndex pour éviter appels réseau
   - `FakeEmbedding` : retourne vecteurs déterministes (hash MD5)
   - `FakeLLM` : répond selon les mots-clés du prompt
   - `FakeVectorStoreIndex` : simule l'indexation RAG
   - `FakeQueryEngine` : simule les requêtes avec sources fake

### Cas de test

#### Test 1 : Pipeline complet (`test_end2end_pipeline_complete`)
1. **Génération** : Appelle `RHProReportGenerator.generate_from_client()`
2. **Vérification outputs** :
   - `client_generated.docx`
   - `client_debug.json`
   - `client_metrics.json`
   - `client_validation.json`
3. **Vérification structure** : JSON bien formés, champs présents
4. **Vérification cohérence** :
   - Si GO : métriques ≥ seuils STRICT
   - Si NO_GO : au moins 1 condition bloquante
5. **Vérification DOCX** : document non vide

#### Test 2 : Données minimales → NO_GO (`test_end2end_minimal_data_no_go`)
- Dossier quasi-vide (1 fichier avec peu d'info)
- **Attendu** : `status = NO_GO` ou `DRAFT`
- Vérifie que le système détecte les données insuffisantes

#### Test 3 : Déterminisme (`test_end2end_deterministic`)
- Exécute le pipeline **2 fois** avec mêmes entrées
- **Attendu** : même `status` dans les 2 exécutions
- Prévient les tests "flaky"

### Mocking LlamaIndex 🔒

Le mocking est **ESSENTIEL** pour respecter la contrainte "zéro appel réseau".

```python
class FakeEmbedding:
    """Embedding déterministe basé sur hash MD5."""
    def get_text_embedding(self, text):
        h = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(h % 100) / 100.0] * 1536

class FakeLLM:
    """LLM qui répond selon les mots-clés."""
    def complete(self, prompt, **kwargs):
        if "nom" in prompt.lower():
            return "DUPONT"
        elif "prenom" in prompt.lower():
            return "Jean"
        # ... etc
```

Patches appliqués :
- `src.rhpro.rag_generator.OpenAIEmbedding` → `FakeEmbedding()`
- `src.rhpro.rag_generator.OpenAI` → `FakeLLM()`
- `src.rhpro.rag_generator.VectorStoreIndex` → `FakeVectorStoreIndex`

### Exécution

```bash
# Tous les tests E2E
pytest tests/test_end2end_one_client.py -v -m e2e

# Un test spécifique
pytest tests/test_end2end_one_client.py::test_end2end_pipeline_complete -v

# Skip si dépendances manquantes (comportement actuel)
pytest tests/test_end2end_one_client.py -v  # → 1 skipped si llama-index absent
```

**Résultat attendu** :
- ✅ **PASSED** si toutes les dépendances sont présentes
- ⚠️ **SKIPPED** si `src.rhpro.report_generator` non disponible (acceptable)

---

## 🎯 Résumé des Garanties

### Ce que les tests garantissent :
1. ✅ **Pas de régression** sur les seuils STRICT/STANDARD/DRAFT
2. ✅ **Cohérence status ↔ métriques** (GO implique métriques OK, NO_GO implique blocage)
3. ✅ **Champs critiques** correctement validés (nom, prénom, profession/formation)
4. ✅ **Zero appel réseau** (100% local, déterministe)
5. ✅ **Rapidité** (< 1 seconde pour tests unitaires)

### Ce que les tests NE garantissent PAS :
- ❌ Qualité réelle du RAG (LLM mocké, pas de vrai OpenAI)
- ❌ Performance avec vrais documents (mini-dossiers fictifs)
- ❌ Bugs dans le parsing DOCX réel

---

## 📊 Métriques

### Tests Unitaires
- **Fichier** : `tests/test_validation_profiles.py`
- **Lignes** : ~545
- **Nombre de tests** : 14 (paramétrés)
- **Temps d'exécution** : ~0.2s
- **Status** : ✅ **14/14 PASSED**

### Tests E2E
- **Fichier** : `tests/test_end2end_one_client.py`
- **Lignes** : ~580
- **Nombre de tests** : 3
- **Temps d'exécution** : ~1-3s (si dépendances disponibles)
- **Status** : ⚠️ **SKIPPED** (si llama-index/report_generator non installés)

---

## 🔧 Maintenance

### Ajouter un nouveau cas de test unitaire

```python
@pytest.mark.parametrize("test_case,metrics_data,debug_data,expected_status", [
    (
        "nouveau_cas",
        create_metrics(required_coverage=80.0, quality_score=0.60),
        create_debug(nom_value="DUPONT", prenom_value="Jean"),
        ValidationStatus.NO_GO,
    ),
])
def test_validation_strict_profile(...):
    ...
```

### Modifier un seuil de validation

1. **Modifier** : `src/rhpro/validation_profiles.py` → `PROFILE_THRESHOLDS`
2. **Mettre à jour** : Tests correspondants dans `test_validation_profiles.py`
3. **Vérifier** : `pytest tests/test_validation_profiles.py -v`

---

## ✅ Checklist DoD

Avant chaque release/commit sur `validation_profiles.py` :

- [ ] Tests unitaires passent : `pytest tests/test_validation_profiles.py -v`
- [ ] Tests E2E passent (si disponibles) : `pytest tests/test_end2end_one_client.py -v`
- [ ] Aucun appel réseau (vérifier logs pytest : aucun appel HTTP)
- [ ] Cohérence status ↔ métriques vérifiée
- [ ] Temps d'exécution < 3s pour l'ensemble

---

## 📚 Références

- **Validation Profiles** : [src/rhpro/validation_profiles.py](../src/rhpro/validation_profiles.py)
- **Batch Report** : [src/rhpro/batch_report.py](../src/rhpro/batch_report.py)
- **Critical Fields** : [docs/CRITICAL_FIELDS_RHPRO.md](./CRITICAL_FIELDS_RHPRO.md)
- **UI Batch Validation** : [pages_streamlit/batch_validation.py](../pages_streamlit/batch_validation.py)

---

## 🚀 Intégration CI/CD (Futur)

Pour intégration dans GitHub Actions / GitLab CI :

```yaml
# .github/workflows/tests.yml
name: Tests DoD

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pytest pytest-mock python-docx
          pip install -e .
      
      - name: Run DoD Tests
        run: |
          pytest tests/test_validation_profiles.py -v --tb=short
          pytest tests/test_end2end_one_client.py -v --tb=short
```

---

**Date de création** : 27 décembre 2025  
**Auteur** : GitHub Copilot  
**Version** : 1.0
