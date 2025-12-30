# SCHEMA V2 - INTÉGRATION GENERATE.PY ✅

**Date:** 29 décembre 2024  
**Status:** Phase 2 complète - Intégration terminée  
**Tests:** 23/23 ✅ (test_generate_v2.py) + 32/32 ✅ (test_schema_v2_anti_hallucination.py)

---

## 📋 RÉSUMÉ

**Objectif:** Intégrer Schema V2 dans [core/generate.py](core/generate.py) pour remplacer l'ancien système de génération des champs.

**Résultat:** Intégration réussie avec flag `USE_SCHEMA_V2` pour basculer entre V1 et V2.

---

## 🔧 MODIFICATIONS APPORTÉES

### 1. [core/generate.py](core/generate.py)

#### A) Ajout flag USE_SCHEMA_V2

```python
# SCHEMA V2: imports conditionnels (lazy loading pour éviter circular imports)
USE_SCHEMA_V2 = False  # Flag pour activer Schema V2
```

**Usage:**
```python
# Pour activer V2
import core.generate as generate_module
generate_module.USE_SCHEMA_V2 = True

# Puis utiliser generate_fields normalement
answers = generate_fields(payload, model="llama3", ...)
```

#### B) Nouvelles fonctions utilitaires

**1. `extract_bullet_points(text: str) -> list[str]`**
```python
# Extrait les bullet points d'un texte
items = extract_bullet_points("- Item 1\n- Item 2")
# → ['Item 1', 'Item 2']
```

**2. `validate_list_v2(text: str, max_items=4, max_chars=2000) -> str`**
```python
# Valide et tronque une liste selon règles V2
result = validate_list_v2("- A\n- B\n- C\n- D\n- E", max_items=4)
# → '- A\n- B\n- C\n- D' (tronqué à 4 items)
```

**3. `extract_enum_field_v2(context_blocks, field_key, allowed_values) -> str`**
```python
# Extraction enum sans LLM (extraction_policy=extract_only)
context = [{"text": "Niveau B2 en français"}]
level = extract_enum_field_v2(context, "FRANCAIS_POSITIONNEMENT_DE_NIVEAU", CECRL_LEVELS)
# → "B2"
```

#### C) Modification generate_fields()

**Ligne 453-462:** Choix spec V2 ou V1
```python
# Schema V2 ou V1
if USE_SCHEMA_V2:
    from .field_specs_v2 import get_field_spec_v2
    spec = get_field_spec_v2(key)
    # V2: pas de multiplicateur (limites strictes)
else:
    spec = get_field_spec(key)
    # PATCH 11: Appliquer le multiplicateur aux limites (V1 seulement)
    if max_chars_multiplier != 1.0:
        from core.field_specs import apply_max_chars_multiplier
        spec = apply_max_chars_multiplier(spec, max_chars_multiplier)
```

**Ligne 495-512:** Extraction enum V2
```python
# SCHEMA V2: extraction_policy = "extract_only" (champs enum)
elif USE_SCHEMA_V2 and hasattr(spec, 'extraction_policy') and spec.extraction_policy == "extract_only":
    # Enum: extraction sans LLM
    if not context_blocks:
        cleaned_value = "Non évalué"
        missing_info.append("NO_CONTEXT")
    else:
        cleaned_value = extract_enum_field_v2(context_blocks, key, spec.enum_values or [])
        
        if cleaned_value == "Non évalué":
            missing_info.append("NO_ENUM_FOUND")
        
        if status_callback:
            status_callback(f"EXTRACT_V2 [{key}] extraction enum : {cleaned_value}")
        if progress_callback:
            progress_callback(key, "extract_v2", f"Extrait : {cleaned_value}")
```

**Ligne 687-691:** Validation liste V2
```python
# SCHEMA V2: Validation spécifique pour listes (max 4 items)
if USE_SCHEMA_V2 and hasattr(spec, 'field_type') and spec.field_type == "list":
    cleaned_value = validate_list_v2(cleaned_value, max_items=4, max_chars=spec.max_chars)
```

**Ligne 693-698:** Validation enum_values
```python
# Validation allowed_values (V1) ou enum_values (V2)
allowed = getattr(spec, 'allowed_values', None) or getattr(spec, 'enum_values', None)
cleaned_value, invalid_reason = validate_allowed_value(cleaned_value, allowed)
```

#### D) Modification build_prompt()

**Ligne 378-398:** Adaptation prompt pour V2
```python
# V2: field_type pour instructions adaptées
max_lines = getattr(spec, 'max_lines', 0)
field_type = getattr(spec, 'field_type', None)

if max_lines == 1:
    format_rule = "Réponds en 1 ligne."
elif field_type == "list":
    format_rule = "Format liste: maximum 4 items. Écris UNIQUEMENT 2 à 4 items sous forme de bullet points (- item)."
elif max_lines:
    format_rule = f"Maximum {max_lines} lignes. Écris tout le contenu sans abréviation ni '...'."
else:
    format_rule = "Écris tout le contenu sans abréviation ni '...'."

lines.append(format_rule)

# allowed_values (V1) ou enum_values (V2)
allowed = getattr(spec, 'allowed_values', None) or getattr(spec, 'enum_values', None)
if allowed:
    allowed_str = ", ".join(allowed)
    lines.append(f"Choisis uniquement parmi : {allowed_str}.")
```

---

## ✅ TESTS CRÉÉS

### [tests/test_generate_v2.py](tests/test_generate_v2.py)

**23 tests / 23 passés ✅**

#### TestExtractBulletPoints (4 tests)
- `test_extract_dash_bullets`: Extraction avec tirets `-`
- `test_extract_bullet_symbol`: Extraction avec symbole `•`
- `test_extract_star_bullets`: Extraction avec étoiles `*`
- `test_mixed_bullets`: Mix de différents symboles

#### TestValidateListV2 (4 tests)
- `test_truncate_to_4_items`: Tronquer 6 items → 4
- `test_keep_3_items`: Garder 3 items (< 4)
- `test_truncate_chars`: Tronquer à max_chars
- `test_no_bullets_passthrough`: Texte sans bullets (passthrough)

#### TestExtractEnumFieldV2 (6 tests)
- `test_extract_francais_b2`: CECRL français B2 ✅
- `test_extract_anglais_c1`: CECRL anglais C1 ✅
- `test_no_context_returns_non_evalue`: Pas de contexte → "Non évalué"
- `test_no_level_found_returns_non_evalue`: Pas de niveau trouvé → "Non évalué"
- `test_bureautique_bon`: Bureautique "Bon" ✅
- `test_test_ok`: Test "OK" ✅

#### TestBuildPromptV2 (3 tests)
- `test_narrative_prompt`: Prompt pour champ narrative
- `test_list_prompt_max_4_items`: Prompt avec "maximum 4 items" ✅
- `test_enum_prompt`: Prompt avec valeurs enum autorisées

#### TestGenerateFieldsV2Integration (3 tests)
- `test_enum_field_no_llm_call`: Enum extraction SANS appel LLM ✅
- `test_list_field_max_4_items`: Liste tronquée à 4 items ✅
- `test_require_sources_no_context`: require_sources=True → pas de LLM si pas de contexte ✅

#### TestSchemaV2FlagToggle (3 tests)
- `test_v2_flag_is_true`: Flag activé pour tests
- `test_get_field_spec_v2_available`: get_field_spec_v2 disponible
- `test_enum_field_has_extract_only_policy`: Enum a extraction_policy=extract_only

---

## 🐛 CORRECTIONS

### 1. Bug imports circulaires
**Problème:** Imports V2 chargés à l'import du module → circular dependency  
**Solution:** Imports lazy dans les fonctions

```python
# Avant
if USE_SCHEMA_V2:
    from .field_specs_v2 import get_field_spec_v2  # Import top-level

# Après  
def generate_fields(...):
    if USE_SCHEMA_V2:
        from .field_specs_v2 import get_field_spec_v2  # Import local
```

### 2. Bug ordre conditions bureautique
**Problème:** `"BUREAUTIQUE_POSITIONNEMENT_DE_NIVEAU"` matche d'abord `"POSITIONNEMENT_DE_NIVEAU"` (langues) avant `"BUREAUTIQUE"`  
**Solution:** Inverser l'ordre des conditions dans `extract_enum_from_context()`

```python
# Avant
if "POSITIONNEMENT_DE_NIVEAU" in field_key:  # Match AVANT bureautique!
    return extract_cecrl_level(text)
if "BUREAUTIQUE" in field_key:
    return extract_bureautique_level(text)

# Après
if "BUREAUTIQUE" in field_key:  # Bureautique EN PREMIER
    return extract_bureautique_level(text)
if "POSITIONNEMENT_DE_NIVEAU" in field_key:
    return extract_cecrl_level(text)
```

**Test:** `test_bureautique_bon` ✅ passe maintenant

### 3. Indentation elif dupliqué
**Problème:** Ligne `elif key.upper().startswith("POSITIONNEMENT")` dupliquée  
**Solution:** Supprimé la ligne en double  
**Fichier:** [core/generate.py](core/generate.py) ligne 514

---

## 📊 COMPORTEMENT V2 vs V1

| Feature | V1 | V2 |
|---------|----|----|
| **Enum extraction** | LLM (peut halluciner) | Regex uniquement (0 hallucination) |
| **Liste items** | Illimité (parfois 8-10) | Hard cap à 4 items |
| **Narrative chars** | Flexible avec multiplier | Strict 3000 chars |
| **Liste chars** | Flexible | Strict 2000 chars |
| **require_sources** | Supporte | Supporte (identique) |
| **Prompt** | Generic | Adapté au field_type |
| **Enum fallback** | Vide ou erreur | "Non évalué" |

---

## 🚀 ACTIVATION V2

### En Production

```python
# core/generate.py
USE_SCHEMA_V2 = True  # Activer V2 globalement
```

### En Tests

```python
# tests/test_*.py
import core.generate as generate_module
generate_module.USE_SCHEMA_V2 = True

# Puis utiliser generate_fields normalement
```

### Via Config

```python
# config/settings.py
SCHEMA_VERSION = "v2"  # ou "v1"

# core/generate.py
from config.settings import SCHEMA_VERSION
USE_SCHEMA_V2 = (SCHEMA_VERSION == "v2")
```

---

## 📈 MÉTRIQUES ATTENDUES (après activation V2)

| Métrique | V1 (actuel) | V2 (cible) | Delta |
|----------|-------------|------------|-------|
| **Enum hallucinations** | > 0 | 0 | ✅ -100% |
| **Liste > 4 items** | ~30% | 0% | ✅ -100% |
| **unknown_titles** | 245 | < 150 | ✅ -38% |
| **ready_strict_rate** | 85.9% | > 90% | ✅ +4.1% |
| **Chars narratives > 3000** | ~15% | 0% | ✅ -100% |

---

## 🔜 PROCHAINES ÉTAPES

1. **Mettre à jour dataset_training.py pour V2**
   - Remplacer `CANONICAL_SECTIONS` par `FIELD_SPECS_V2`
   - Calcul coverage par field_type

2. **Validation ESSAI 100 avec V2**
   ```bash
   # Activer V2 dans generate.py
   USE_SCHEMA_V2 = True
   
   # Puis lancer
   python src/rhpro/dataset_training.py --clients-dir data/CLIENTS --limit 571
   ```

3. **Comparaison V1 vs V2**
   - Mesurer unknown_titles
   - Vérifier 0 hallucinations enum
   - Valider toutes listes ≤ 4 items

4. **Migration guide**
   - Documenter breaking changes
   - Procédure rollback
   - Mapping V1→V2 fields

5. **UI Updates**
   - Afficher couverture par field_type
   - Indicateur "Non évalué" pour enums
   - Highlight listes avec 4 items

---

## 📝 FICHIERS MODIFIÉS

### Créés (Phase 2)
- `tests/test_generate_v2.py` (500+ lignes, 23 tests)
- `SCHEMA_V2_INTEGRATION_GENERATE.md` (ce fichier)

### Modifiés
- `core/generate.py` (+150 lignes)
  * Flag USE_SCHEMA_V2
  * extract_bullet_points()
  * validate_list_v2()
  * extract_enum_field_v2()
  * generate_fields() adapté V2
  * build_prompt() adapté V2

- `core/enum_extractors_v2.py` (1 ligne)
  * Fix ordre conditions bureautique/langues

### Existants (Phase 1)
- `core/field_specs_v2.py` (335 lignes, 39 champs)
- `core/enum_extractors_v2.py` (271 lignes)
- `core/title_mapping_v2.py` (233 lignes)
- `tests/test_schema_v2_anti_hallucination.py` (550 lignes, 32 tests)

---

## ✅ VALIDATION COMPLÈTE

### Tests Phase 1
```bash
pytest tests/test_schema_v2_anti_hallucination.py -v
# 32 passed ✅
```

### Tests Phase 2
```bash
pytest tests/test_generate_v2.py -v
# 23 passed ✅
```

### Tests Combinés
```bash
pytest tests/test_schema_v2_anti_hallucination.py tests/test_generate_v2.py -v
# 55 passed ✅
```

**Status:** Phase 2 COMPLÈTE ✅  
**Prochaine étape:** Validation sur données réelles (ESSAI 100)

---

## 💡 DÉCISIONS TECHNIQUES

### 1. Lazy imports pour éviter circular dependencies
Choix de charger les modules V2 uniquement quand nécessaire pour éviter problèmes d'imports circulaires.

### 2. Getattr pour compatibilité V1/V2
Utilisation de `getattr()` pour accéder aux attributs qui peuvent différer entre FieldSpec et FieldSpecV2.

### 3. Hard cap sur listes (4 items)
Décision stricte: toutes les listes sont tronquées à 4 items, même si LLM retourne plus.

### 4. "Non évalué" comme fallback standard
Tous les enums sans extraction retournent "Non évalué" (jamais vide ou erreur).

### 5. Flag global USE_SCHEMA_V2
Permet toggle facile V1↔V2 sans refactor complet, utile pour migration progressive.

---

**Date de finalisation:** 29 décembre 2024  
**Auteur:** Integration V2 - Phase 2  
**Version:** 2.0.0
