# SCHEMA V2 - Refactor Anti-Hallucination

## 🎯 OBJECTIF

**Problème initial:**
- ~25 sections canoniques mal définies
- Overlap entre sections (SCOLARITÉ vs FORMATION)
- Hallucinations LLM (invention de contenu)
- `unknown_titles=245` sur ESSAI 100
- Trop de sections narratives longues

**Solution Schema V2:**
- **39 champs bien définis** (au lieu de ~25 sections)
- **Typologie stricte**: deterministic | narrative | list | enum
- **Anti-hallucination**: extraction first, LLM avec gardes-fous
- **Title mapping**: 34 patterns + 17 titres admin ignorés

---

## 📊 ARCHITECTURE V2

### A) Distribution des 39 champs

```
Déterministes:  5 (config values, pas de LLM)
Narratives:    13 (LLM avec max 3000 chars)
Listes:        10 (LLM avec max 2000 chars, 2-4 items)
Enums:         11 (extraction regex, pas d'inférence)
───────────────────
TOTAL:         39 champs
```

### B) Champs Déterministes (5)

| Champ | Source | Exemple |
|-------|--------|---------|
| `MONSIEUR_OU_MADAME` | Config | "Madame" |
| `NAME` | Config | "SILVA" |
| `SURNAME` | Config | "Maria" |
| `LIEU_ET_DATE` | Config | "Genève, le 1 mars 2024" |
| `NUMERO_AVS` | Config | "756.1234.5678.97" |

**Politique:** `extraction_policy = "deterministic"`  
**LLM:** Non utilisé

### C) Champs Narratives (13)

| Champ | Max chars | Description |
|-------|-----------|-------------|
| `PROFESSION` | 3000 | Situation professionnelle actuelle |
| `FORMATION` | 3000 | Formation et diplômes |
| `DISCUSSION_ASSURE` | 3000 | Discussion avec l'assuré |
| `COMPETENCES_PROFESSIONNELLES` | 3000 | Compétences techniques |
| `PARCOURS_PROFESSIONNEL` | 3000 | Historique professionnel |
| `CONTEXTE_SOCIAL_FAMILIAL` | 3000 | Contexte social/familial |
| `RAPPORT_AU_TRAVAIL` | 3000 | Motivation et rapport au travail |
| `MARCHE_DU_TRAVAIL` | 3000 | Analyse du marché |
| `CV` | 3000 | Extrait du CV |
| `LETTRE_DE_MOTIVATION` | 3000 | Extrait de la lettre |
| `RIASEC` | 3000 | Résultats RIASEC détaillés |
| `VOCATIO` | 3000 | Profil Vocatio |
| `PRECONISATIONS_ET_PLACEMENT` | 3000 | Préconisations ORP |

**Politique:** `extraction_policy = "llm_with_guardrails"`  
**Gardes-fous:**
- Max 3000 caractères (hard cap)
- Prompt: "Interdit d'inventer des faits non présents dans les sources"
- Pas de "..." à la fin
- CV + LETTRE: `require_sources=True` (skip si pas de sources)

### D) Champs Listes (10)

| Champ | Max chars | Items |
|-------|-----------|-------|
| `RESSOURCES_COMPORTEMENTALES` | 2000 | 2-4 |
| `SECTEURS_PRIVILEGIES` | 2000 | 2-4 |
| `DOMAINES_PROFESSIONNELS_EXEMPLES` | 2000 | 2-4 |
| `RIASEC_CORRESPONDANCE_SCORE` | 2000 | 2-4 |
| `CONTRAINTES_ET_LIMITES` | 2000 | 2-4 |
| `CONTRAINTES_MEDICALES` | 2000 | 2-4 |
| `PRECONISATIONS_ET_SYNTHESE` | 2000 | 2-4 |
| `FORMATIONS_TESTS` | 2000 | 2-4 |
| `EVALUATION_SITUATION` | 2000 | 2-4 |
| `LIMITES_ET_INTERROGATIONS` | 2000 | 2-4 |

**Politique:** `extraction_policy = "llm_with_guardrails"`  
**Gardes-fous:**
- Max 2000 caractères
- **2 à 4 items MAXIMUM** (PAS PLUS)
- Prompt: "Formater sous forme de bullet points"
- FORMATIONS_TESTS: `require_sources=True`

### E) Champs Enum - Langues (3)

| Champ | Valeurs autorisées |
|-------|--------------------|
| `FRANCAIS_POSITIONNEMENT_DE_NIVEAU` | A1, A2, B1, B2, C1, C2, Non évalué |
| `ANGLAIS_POSITIONNEMENT_DE_NIVEAU` | A1, A2, B1, B2, C1, C2, Non évalué |
| `ALLEMAND_POSITIONNEMENT_DE_NIVEAU` | A1, A2, B1, B2, C1, C2, Non évalué |

**Politique:** `extraction_policy = "extract_only"`  
**Extraction:**
```python
def extract_cecrl_level(text: str) -> str:
    """Regex: \b(A1|A2|B1|B2|C1|C2)\b"""
    # Si trouvé → retour niveau
    # Si pas trouvé → "Non évalué"
    # JAMAIS d'inférence
```

**Exemples:**
- "Niveau B2 en français" → `"B2"`
- "Bon niveau de français" → `"Non évalué"` (pas de preuve)
- "Compétent à l'oral" → `"Non évalué"` (pas de preuve)

### F) Champs Enum - Bureautique (1)

| Champ | Valeurs autorisées |
|-------|--------------------|
| `BUREAUTIQUE_POSITIONNEMENT_DE_NIVEAU` | Faible, Moyen, Bon, Très bon, Non évalué |

**Politique:** `extraction_policy = "extract_only"`  
**Extraction:**
```python
def extract_bureautique_level(text: str) -> str:
    """Keywords: word, excel, powerpoint + qualifiers"""
    # "Bonne maîtrise d'Excel" → "Bon"
    # "Expert Word" → "Très bon"
    # "Notions de base" → "Moyen"
    # "Compétences informatiques" → "Non évalué"
```

### G) Champs Enum - Tests (7)

| Champ | Valeurs autorisées |
|-------|--------------------|
| `TEST_ATTENTION_ADMINISTRATIF` | OK, Moyen, À renforcer, Non évalué |
| `TEST_ATTENTION_SOUTENUE` | OK, Moyen, À renforcer, Non évalué |
| `TEST_VIGILANCE` | OK, Moyen, À renforcer, Non évalué |
| `CALCUL_ET_FRACTION` | OK, Moyen, À renforcer, Non évalué |
| `COMPREHENSION_LECTURE` | OK, Moyen, À renforcer, Non évalué |
| `COMPREHENSION_ORALE` | OK, Moyen, À renforcer, Non évalué |
| `COMPREHENSION_ECRITE` | OK, Moyen, À renforcer, Non évalué |

**Politique:** `extraction_policy = "extract_only"`  
**Extraction:**
```python
def extract_test_result(text: str) -> str:
    """Patterns pour OK/Moyen/À renforcer"""
    # "Test: OK" → "OK"
    # "Difficultés observées" → "À renforcer"
    # "Résultat moyen" → "Moyen"
    # "Aucun test passé" → "Non évalué"
```

---

## 🔒 ANTI-HALLUCINATION

### Règle 1: Enum = Extract Only

```python
# AVANT (V1): LLM invente si pas de données
llm("Quel est le niveau de français?")
# → hallucine "B1" même si aucune preuve

# APRÈS (V2): Extraction regex first
level = extract_cecrl_level(context)
if level != "Non évalué":
    return level  # preuve trouvée
else:
    return "Non évalué"  # PAS de call LLM
```

**Impact:**
- 0 hallucinations sur enums
- 11 champs enum = 11 champs fiables

### Règle 2: require_sources

```python
# Champs concernés:
- CV
- LETTRE_DE_MOTIVATION
- FORMATIONS_TESTS
- DOMAINES_PROFESSIONNELS_EXEMPLES
- RIASEC_CORRESPONDANCE_SCORE
- Tous les 11 champs enum

# Si pas de sources → skip LLM
if spec.require_sources and not has_sources:
    return ""  # Ne pas inventer
```

### Règle 3: Liste max 4 items

```python
# Prompt LLM:
"Extraire 2 à 4 items MAXIMUM (PAS PLUS)"

# Post-validation:
items = extract_bullet_points(llm_output)
if len(items) > 4:
    items = items[:4]  # Hard cap
```

### Règle 4: max_chars enforced

```python
# Narrative: 3000 chars max
# Liste: 2000 chars max

if len(text) > spec.max_chars:
    text = text[:spec.max_chars]
```

---

## 🗺️ TITLE MAPPING V2

### Patterns (34 champs mappés)

Exemples:
```python
"SITUATION PROFESSIONNELLE" → PROFESSION
"Formation et diplômes" → FORMATION
"Français - Positionnement de niveau" → FRANCAIS_POSITIONNEMENT_DE_NIVEAU
"Test d'attention administratif" → TEST_ATTENTION_ADMINISTRATIF
"RIASEC - Correspondance score" → RIASEC_CORRESPONDANCE_SCORE
```

### Titres Ignorés (17 admin)

```python
IGNORED_TITLES_V2 = [
    "SOMMAIRE",
    "A L'ATTENTION DE",
    "OFFICE CANTONAL DES ASSURANCES SOCIALES",
    "PARTICIPATION AU PROGRAMME",
    "VOTRE CONSEILLER",
    "BUREAU DES MESURES D'INTEGRATION",
    "SECTEUR ORIENTATION ET PLACEMENT",
    "PROCEDURE",
    "OBJECTIFS",
    "INFORMATIONS COMPLEMENTAIRES",
    "ADRESSE",
    "MAIL",
    "TELEPHONE",
    "SERVICE DES ASSURANCES SOCIALES",
    "SECTEUR PMI",
    "DATE",
    "SIGNATURE",
]
```

**Impact:**
- `unknown_titles` passe de 245 → ~100-150
- Réduction bruit admin: -17 titres parasites

---

## 📦 MODULES CRÉÉS

### 1. `core/field_specs_v2.py` (500+ lignes)

```python
from dataclasses import dataclass

@dataclass
class FieldSpecV2:
    field_key: str
    field_type: str  # deterministic | narrative | list | enum
    extraction_policy: str  # deterministic | extract_only | llm_with_guardrails
    max_chars: int
    enum_values: list[str] | None
    require_sources: bool
    skip_llm_if_no_sources: bool
    instructions: str

# Registry
FIELD_SPECS_V2: dict[str, FieldSpecV2] = {...}

# API
get_field_spec_v2(key: str) -> FieldSpecV2
list_fields_by_type(field_type: str) -> list[str]
get_schema_stats() -> dict
```

**Tests:** ✅ 39 champs, distribution correcte

### 2. `core/enum_extractors_v2.py` (270+ lignes)

```python
def extract_cecrl_level(text: str) -> str:
    """Regex \b(A1|A2|B1|B2|C1|C2)\b"""

def extract_bureautique_level(text: str) -> str:
    """Keywords + qualifiers → Faible/Moyen/Bon/Très bon"""

def extract_test_result(text: str, field_key: str) -> str:
    """Patterns pour OK/Moyen/À renforcer"""

def extract_enum_from_context(text: str, field_key: str) -> str:
    """Router basé sur field_key"""

def validate_enum_value(value: str, allowed: list[str], strict: bool) -> str:
    """Validation avec fallback "Non évalué" """
```

**Tests:** ✅ B2, Bon, OK extraits correctement

### 3. `core/title_mapping_v2.py` (350+ lignes)

```python
IGNORED_TITLES_V2: list[str] = [...]
TITLE_TO_FIELD_PATTERNS_V2: dict[str, str] = {...}

def normalize_title_v2(title: str) -> str:
    """Normalise titre (accents, espaces)"""

def is_ignored_title_v2(title: str) -> bool:
    """Vérifie si titre admin"""

def map_title_to_field_v2(title: str) -> str | None:
    """Map titre → field_key"""

def get_mapping_stats() -> dict:
    """Stats: 34 fields, 17 ignored"""
```

**Tests:** ✅ 11/11 mappings corrects, 34 champs uniques

### 4. `tests/test_schema_v2_anti_hallucination.py` (550+ lignes)

**32 tests passés:**
- Structure du schéma (7 tests)
- Extraction enum (9 tests)
- Title mapping (7 tests)
- Anti-hallucination (4 tests)
- Non-régression deterministic (2 tests)
- Collision FORMATION vs FORMATIONS_TESTS (3 tests)

---

## 🚀 INTÉGRATION (Phase 2 - À FAIRE)

### Étape 1: Modifier `core/generate.py`

```python
from core.field_specs_v2 import get_field_spec_v2
from core.enum_extractors_v2 import extract_enum_from_context

def generate_field_value(field_key: str, context: dict) -> str:
    spec = get_field_spec_v2(field_key)
    
    # A) Enum: extract only
    if spec.extraction_policy == "extract_only":
        value = extract_enum_from_context(context["text"], field_key)
        return value  # "B2" ou "Non évalué"
    
    # B) require_sources
    if spec.require_sources and not context.get("sources"):
        return ""  # Ne pas appeler LLM
    
    # C) LLM avec gardes-fous
    prompt = spec.instructions.format(**context)
    llm_output = llm_call(prompt)
    
    # D) Post-validation
    if spec.field_type == "list":
        llm_output = validate_list_max_4_items(llm_output)
    
    if len(llm_output) > spec.max_chars:
        llm_output = llm_output[:spec.max_chars]
    
    return llm_output
```

### Étape 2: Mettre à jour `src/rhpro/dataset_training.py`

```python
# Remplacer CANONICAL_SECTIONS par FIELD_SPECS_V2
from core.field_specs_v2 import FIELD_SPECS_V2

expected_fields = list(FIELD_SPECS_V2.keys())
filled_fields = [k for k, v in fields.items() if v]
coverage = len(filled_fields) / len(expected_fields)
```

### Étape 3: Créer tests d'intégration

```bash
tests/test_generate_v2.py
tests/test_dataset_training_v2.py
```

### Étape 4: Validation sur ESSAI 100

```bash
python src/rhpro/dataset_training.py \
    --clients-dir data/CLIENTS \
    --limit 571 \
    --use-schema-v2
```

**Métriques attendues:**
- `unknown_titles`: 245 → 100-150
- Enum hallucinations: > 0 → 0
- ready_strict_rate: +5-10% (moins d'inventions)

---

## 📝 MIGRATION V1 → V2

### Correspondances de champs

| V1 Section | V2 Field |
|------------|----------|
| SCOLARITÉ + FORMATION | FORMATION (fusionné) |
| Formation (titre dans doc) | FORMATIONS_TESTS (renommé) |
| CV | CV (identique) |
| Lettre de motivation | LETTRE_DE_MOTIVATION |
| RIASEC résultats | RIASEC |
| Français eval | FRANCAIS_POSITIONNEMENT_DE_NIVEAU |

### Breaking changes

1. **FORMATIONS_TESTS** renommé (était "Formation(s)" dans doc)
   - Raison: collision avec FORMATION narrative
   - Migration: mettre à jour title_mapping

2. **Enum values**: maintenant strictes
   - V1: LLM pouvait retourner "Niveau intermédiaire"
   - V2: Seulement ["A1", "A2", ..., "Non évalué"]

3. **Liste max 4 items**: hard cap
   - V1: LLM pouvait retourner 8-10 items
   - V2: Tronqué à 4 automatiquement

### Rollback

Si V2 pose problème:
```python
# core/generate.py
USE_SCHEMA_V2 = False  # Revenir à V1

if USE_SCHEMA_V2:
    from core.field_specs_v2 import get_field_spec_v2
else:
    from core.field_specs import get_field_spec  # V1
```

---

## ✅ STATUS

### ✅ Complété (Phase 1: Foundation)

- [x] `core/field_specs_v2.py`: 39 champs définis
- [x] `core/enum_extractors_v2.py`: Extracteurs CECRL/bureautique/tests
- [x] `core/title_mapping_v2.py`: 34 patterns + 17 ignored
- [x] `tests/test_schema_v2_anti_hallucination.py`: 32/32 tests
- [x] Documentation: SCHEMA_V2_REFACTOR.md

### ⏳ En Attente (Phase 2: Integration)

- [ ] Intégrer V2 dans `core/generate.py`
- [ ] Mettre à jour validation (enum strict)
- [ ] Modifier `dataset_training.py` pour V2
- [ ] Tests d'intégration pipeline complet
- [ ] Validation sur ESSAI 100 avec V2
- [ ] UI: affichage couverture par type de champ

---

## 🎯 OBJECTIFS MESURABLES

| Métrique | V1 | V2 (cible) |
|----------|----|-----------| 
| **unknown_titles** | 245 | < 150 |
| **Hallucinations enum** | > 0 | 0 |
| **Items dans listes** | 8-10 | ≤ 4 |
| **ready_strict_rate** | 85.9% | > 90% |
| **Chars narratives** | > 5000 | ≤ 3000 |

---

## 💡 DÉCISIONS CRITIQUES

### 1. FORMATIONS_TESTS vs FORMATION

**Problème:** Dans les documents, on voit "Formation(s)" comme titre de section tests.  
**Solution:** Renommé en `FORMATIONS_TESTS` pour éviter collision avec `FORMATION` narrative.  
**Impact:** Mapping mis à jour, tests validés.

### 2. Enum = Extract Only (NO LLM)

**Problème:** LLM invente des niveaux CECRL même sans preuve.  
**Solution:** Extraction regex uniquement, fallback "Non évalué".  
**Impact:** 0 hallucinations, mais possiblement plus de "Non évalué".

### 3. Liste max 4 items (Hard Cap)

**Problème:** LLM retourne des listes de 8-10 items (trop long).  
**Solution:** Hard cap à 4 items + prompt strict.  
**Impact:** Perte d'info possible, mais uniformité garantie.

### 4. require_sources sur CV/LETTRE

**Problème:** LLM invente du contenu si pas de CV/lettre.  
**Solution:** `skip_llm_if_no_sources=True` → retour vide.  
**Impact:** Champs vides visibles, mais honnêteté.

---

## 📊 COMMANDE SUIVANTE

```bash
# Tester les modules V2
pytest tests/test_schema_v2_anti_hallucination.py -v

# Output:
# 32 passed ✅
```

**Prochaine étape:** Intégrer V2 dans `core/generate.py` 🚀
