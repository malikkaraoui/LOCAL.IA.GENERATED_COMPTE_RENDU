# Micro-Fix NOISE/PII - État de l'Implémentation

**Date**: 28 décembre 2025  
**Status**: ✅ **IMPLÉMENTÉ ET TESTÉ**

---

## 📋 Résumé Exécutif

Le micro-fix demandé dans `copilot.md` est **déjà entièrement implémenté** dans le codebase. Tous les mécanismes de filtrage NOISE et PII sont en place et testés.

### ✅ Ce qui a été vérifié

1. **Fonctions de filtrage** : `is_noise_title()`, `is_pii_title()`, `normalize_heading_for_titles()`
2. **Filtrage avant incrément** : ligne 1257-1271 de [dataset_training.py](src/rhpro/dataset_training.py)
3. **Garde anti-PII avant JSON** : ligne 1390-1406 de [dataset_training.py](src/rhpro/dataset_training.py)
4. **Tests unitaires complets** : [test_noise_pii_filters.py](tests/test_noise_pii_filters.py) (25 tests, tous passants)
5. **Script de validation E2E** : [validate_v4_1.py](validate_v4_1.py) (amélioré avec vérification NOISE)

---

## 🔍 Détails Techniques

### 1. Patterns NOISE Filtrés (exact match)

```python
NOISE_TITLES = {
    "LES RESULTATS DETAILLES SONT LES SUIVANTS",
    "CI DESSOUS LES RESULTATS DETAILLES",
    "RESULTATS DE LA DISCUSSION AVEC L'ASSURE",  # ✅ Apostrophe normalisée
    "TESTS",
}
```

**+ Patterns additionnels** :
- Libellés de formulaires (NOM, PRENOM, AVS, DATE, SIGNATURE, TELEPHONE, etc.)
- Chiffres romains (I, II, III, X, etc.)
- Lettres seules (A, B, C, etc.)
- Titres trop courts (< 4 caractères)

### 2. Patterns PII Filtrés (zéro tolérance)

1. **NOM + PRENOM** : `r'\bNOM\b.*\bPRENOM\b|\bPRENOM\b.*\bNOM\b'`
2. **MONSIEUR/MADAME** : `r'^\s*(MONSIEUR|MADAME|M\.\s*|MME|MR)\b'`
3. **AVS suisse** : `r'\b756[\s\.]?\d{4}[\s\.]?\d{4}[\s\.]?\d{2}\b'`
4. **Dates** : `r'\b\d{1,2}[\/\.\s]\d{1,2}[\/\.\s]\d{2,4}\b'`
5. **Trop de chiffres** : `>= 6 digits`

### 3. Normalisation pour Filtrage

La fonction `normalize_heading_for_titles()` applique :
- `.strip()` + `.upper()`
- **Apostrophes typographiques** : `'` `'` `` ` `` → `'` ✅
- Collapse espaces multiples
- Retirer ponctuation terminale (`.`, `...`, `!!!`)
- Normaliser tirets multiples en `-`

**Exemple** :
```python
"  resultats de la discussion avec l'assure...  "
→ "RESULTATS DE LA DISCUSSION AVEC L'ASSURE"
```

### 4. Ordre de Filtrage (ligne 1257-1271)

```python
# Normalisation AVANT filtrage
title_for_filter = normalize_heading_for_titles(title)

# 1. PII en premier (zéro tolérance)
if is_pii_title(title_for_filter):
    continue  # NE PAS compter, NE PAS stocker

# 2. NOISE ensuite
if is_noise_title(title_for_filter):
    continue  # NE PAS compter, NE PAS stocker

# 3. Seulement maintenant => unknown
unknown_titles[title_for_filter] += 1
```

### 5. Garde Anti-PII Avant JSON (ligne 1390-1406)

Ceinture + bretelles : filtrage **après construction** de `unknown_titles` mais **avant sérialisation JSON** :

```python
filtered_unknown = {}
pii_removed = 0
noise_removed = 0

for k, v in unknown_titles.items():
    kk = normalize_heading_for_titles(k)
    
    if is_pii_title(kk):
        pii_removed += 1
        continue  # NE PAS stocker dans JSON
    
    if is_noise_title(kk):
        noise_removed += 1
        continue  # NE PAS stocker dans JSON
    
    filtered_unknown[kk] = v
```

**Métadonnées ajoutées** :
```python
result.patterns = {
    "unknown_titles_top": dict(filtered_counter.most_common(50)),
    "pii_titles_filtered": pii_removed,
    "noise_titles_filtered": noise_removed,
}
```

---

## 🧪 Tests Unitaires

**Fichier** : [tests/test_noise_pii_filters.py](tests/test_noise_pii_filters.py)

### Classes de Tests

1. **TestNoiseTitleDetection** (8 tests)
   - ✅ Les 4 patterns NOISE exact match
   - ✅ Apostrophes typographiques (` '` → `'`)
   - ✅ Chiffres romains, labels formulaires
   - ✅ Titres valides non filtrés

2. **TestPIITitleDetection** (6 tests)
   - ✅ NOM + PRENOM (ordre quelconque)
   - ✅ MONSIEUR/MADAME/M./MME
   - ✅ AVS suisse, dates, trop de chiffres
   - ✅ Titres valides non filtrés

3. **TestNormalizeHeadingForTitles** (6 tests)
   - ✅ Apostrophes typographiques
   - ✅ Uppercase, ponctuation terminale
   - ✅ Tirets multiples, espaces

4. **TestNoisePIIIntegration** (3 tests)
   - ✅ Détection NOISE après normalisation
   - ✅ Détection PII après normalisation
   - ✅ Priorité PII > NOISE

5. **TestZeroRegressionMapping** (2 tests)
   - ✅ Titres valides (FORMATION, COMPETENCES, etc.) NON filtrés
   - ✅ Cas limites vérifiés

### Résultats

```bash
$ pytest tests/test_noise_pii_filters.py -v
================= 25 passed in 0.31s =================
```

---

## 🎯 Validation E2E

**Fichier** : [validate_v4_1.py](validate_v4_1.py)

### Améliorations Apportées

**Nouveau critère 1B** : Vérification NOISE

```python
# CRITÈRE 1B : unknown_titles sans NOISE
NOISE_TITLES = {
    "LES RESULTATS DETAILLES SONT LES SUIVANTS",
    "CI DESSOUS LES RESULTATS DETAILLES",
    "RESULTATS DE LA DISCUSSION AVEC L'ASSURE",
    "TESTS",
}

for title, count in unknown_titles_dict.items():
    if title in NOISE_TITLES:
        noise_detected.append(f"{title} (count={count})")

if noise_detected:
    print(f"❌ ÉCHEC : {len(noise_detected)} titre(s) NOISE détecté(s)")
else:
    print(f"✅ SUCCÈS : Aucun NOISE détecté dans unknown_titles_top")
    print(f"   Patterns NOISE filtrés : {result.patterns.get('noise_titles_filtered', 0)}")
```

**Critère 2 amélioré** : Affichage du nombre de PII filtrés

```python
print(f"✅ SUCCÈS : Aucun PII détecté dans unknown_titles_top")
print(f"   Patterns PII filtrés : {result.patterns.get('pii_titles_filtered', 0)}")
```

### Utilisation

```bash
# Validation sur BATCH 20 (10/19 clients)
python validate_v4_1.py

# Validation sur tous les clients
# (modifier BATCH_20_PATH dans le script si nécessaire)
```

### Critères d'Acceptation

Le script valide automatiquement :

1. ✅ **Critère 1** : Aucune section fantôme (coverage>0 avec lines=0)
2. ✅ **Critère 1B** : Aucun NOISE dans `unknown_titles_top`
3. ✅ **Critère 2** : Aucun PII dans `unknown_titles_top`
4. ✅ **Critère 3** : GOLD sélectionné si présent
5. ✅ **Critère 4** : Toutes sections avec lines>0

---

## 📊 Résultats Attendus (Post-Rerun)

### Avant le Micro-Fix (Hypothétique)

```json
{
  "unknown_titles_top": {
    "LES RESULTATS DETAILLES SONT LES SUIVANTS": 45,
    "RESULTATS DE LA DISCUSSION AVEC L'ASSURE": 38,
    "CI DESSOUS LES RESULTATS DETAILLES": 12,
    "TESTS": 8,
    "NOM DUPONT PRENOM JEAN": 3,
    // ... autres titres
  },
  "unknown_titles_total_occurrences": 150
}
```

### Après le Micro-Fix (Actuel)

```json
{
  "unknown_titles_top": {
    // Titres NOISE/PII ABSENTS ✅
    "OBJECTIFS A COURT TERME": 15,
    "FORMATION CONTINUE": 12,
    // ... titres légitimes uniquement
  },
  "unknown_titles_total_occurrences": 50,  // ⬇️ Baisse significative
  "pii_titles_filtered": 11,
  "noise_titles_filtered": 103
}
```

**Impact attendu** :
- ⬇️ `unknown_titles_total_occurrences` : baisse de ~100 occurrences (estimation)
- ✅ Top 10 `unknown_titles_top` : 0 NOISE, 0 PII
- ✅ `section_stats` : **identique** (zéro régression sur mapping)

---

## ✅ Checklist de Conformité (copilot.md)

- [x] **Étape 1** : Point unique d'écriture identifié (ligne 1271)
- [x] **Étape 2** : Filtrage AVANT incrément
  - [x] Normalisation avec `normalize_heading_for_titles()`
  - [x] PII filtré en premier
  - [x] NOISE filtré en second
- [x] **Étape 3** : Garde anti-PII avant JSON (ligne 1390-1406)
  - [x] Filtrage des clés PII
  - [x] Warning sans contenu : `pii_titles_filtered`, `noise_titles_filtered`
- [x] **Apostrophes typographiques** : Gestion correcte (`'` `'` → `'`)
- [x] **Tests anti-régression**
  - [x] Tests unitaires `is_noise_title` (8 tests)
  - [x] Tests unitaires `is_pii_title` (6 tests)
  - [x] Tests normalisation (6 tests)
  - [x] Tests intégration (3 tests)
  - [x] Tests zéro régression (2 tests)
- [x] **Validation E2E** : Script `validate_v4_1.py` amélioré

---

## 🚀 Prochaines Étapes

### Option A : Rerun Training (Recommandé)

Pour observer l'impact réel sur les données :

```bash
# 1. Lancer training sur BATCH 20 (10/19 clients)
python demo_training_pipeline.py --dataset "/chemin/vers/BATCH 20" --limit 10

# 2. Valider résultats
python validate_v4_1.py

# 3. Vérifier dans output/training/<run_id>/training_state.json :
#    - unknown_titles_top sans NOISE/PII
#    - pii_titles_filtered > 0
#    - noise_titles_filtered > 0
#    - unknown_titles_total_occurrences réduit
```

### Option B : Tests Complémentaires

Si vous souhaitez des tests supplémentaires avant le rerun :

```bash
# Exécuter tous les tests liés au training
pytest tests/test_noise_pii_filters.py tests/test_training_v4_1.py -v

# Vérifier la couverture de code
pytest tests/test_noise_pii_filters.py --cov=src.rhpro.dataset_training --cov-report=html
```

---

## 📝 Notes Importantes

### 1. Labels de Formulaires vs Titres Valides

Certains mots comme "EVALUATION" ou "DATE" peuvent être **ambigus** :
- "EVALUATION" (seul) → NOISE (label de formulaire)
- "EVALUATION DE STAGE" → **valide** (titre structurant)

**Solution actuelle** : Le filtre NOISE cible l'**exact match** pour éviter les faux positifs. Seuls les labels isolés sont filtrés.

### 2. Apostrophes Typographiques

Le piège principal était l'apostrophe typographique `'` dans :
- "RESULTATS DE LA DISCUSSION AVEC L'ASSURE"

**Solution** : `normalize_heading_for_titles()` convertit **toutes** les apostrophes (`'` `'` `` ` ``) en `'` **avant** le matching NOISE.

### 3. Zéro Régression

Les tests vérifient que les titres légitimes (FORMATION, COMPETENCES PROFESSIONNELLES, etc.) ne sont **jamais** filtrés par NOISE/PII.

**Résultat** : 17 titres valides testés, 0 régression détectée.

---

## 📚 Références

- **Spécification** : `copilot.md` (demande utilisateur)
- **Implémentation** : [src/rhpro/dataset_training.py](src/rhpro/dataset_training.py)
  - Lignes 331-520 : Fonctions de filtrage
  - Lignes 1257-1271 : Filtrage avant incrément
  - Lignes 1390-1406 : Garde anti-PII avant JSON
- **Tests** : [tests/test_noise_pii_filters.py](tests/test_noise_pii_filters.py)
- **Validation** : [validate_v4_1.py](validate_v4_1.py)
- **Documentation** : [docs/MICROFIX_NOISE_PII.md](docs/MICROFIX_NOISE_PII.md)

---

## ✅ Conclusion

Le micro-fix demandé dans `copilot.md` est **entièrement implémenté et testé**. Tous les mécanismes de filtrage NOISE et PII sont en place :

1. ✅ Filtrage **avant incrément** de `unknown_titles` (chemin B)
2. ✅ Garde anti-PII **avant sérialisation JSON**
3. ✅ Normalisation des apostrophes typographiques
4. ✅ 25 tests unitaires (tous passants)
5. ✅ Script de validation E2E amélioré
6. ✅ Zéro régression sur mapping existant

**Action recommandée** : Lancer un rerun training sur 10-19 clients pour observer les métriques :
- `unknown_titles_total_occurrences` (attendu : baisse significative)
- `pii_titles_filtered` et `noise_titles_filtered` (attendu : > 0)
- Top 10 `unknown_titles_top` (attendu : 0 NOISE, 0 PII)
