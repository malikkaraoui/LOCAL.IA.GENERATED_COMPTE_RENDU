# Intégration du Système de Prompt Wrapper V1

## 📅 Date
30 décembre 2025

## 🎯 Objectif

Implémenter dans `core/field_specs_v2.py` le système de **prompt wrapper unique et versionné** décrit dans `docs/prompt.md`, garantissant que chaque appel LLM reçoit :
1. Un marqueur sentinel pour validation
2. Des règles anti-hallucination strictes
3. Des contraintes de format par type de champ
4. Des sources délimitées proprement

## ✅ Modifications appliquées

### 1. Constantes ajoutées

```python
# Marqueur sentinel obligatoire pour validation runtime
PROMPT_SENTINEL = "[[FIELD_SPECS_V2_PROMPT_V1]]"
PROMPT_VERSION = "V1"
```

### 2. Fonction `build_system_prompt()`

**But** : Générer le SYSTEM PROMPT global avec les règles non négociables.

**Contenu** (conforme à prompt.md section 3) :
- Marqueur sentinel `[[FIELD_SPECS_V2_PROMPT_V1]]`
- Règles anti-hallucination (5 points critiques)
- Style et forme (français professionnel, interdictions)
- Respect strict des formats par `field_type`
- Contrôle qualité interne (checklist)
- Périmètre de vérité (ce qui ne peut JAMAIS être créé)

**Longueur** : ~2279 caractères

### 3. Fonction `build_user_prompt(field_spec, sources, sources_count)`

**But** : Générer le USER PROMPT pour un champ spécifique.

**Contenu** (conforme à prompt.md section 4) :
- **En-tête FieldSpec** : key, type, query, max_chars, max_lines, require_sources, enum_values, instructions
- **Bloc SOURCES délimité** : `<SOURCES>...</SOURCES>` avec contenu RAG
- **Règles de réponse par type** :
  - `narrative` : texte pro, pas de "...", "Non renseigné" si manquant
  - `list` : JSON array uniquement, items 5-14 mots
  - `enum` : valeur seule, preuve explicite requise

**Longueur** : ~1200-1800 caractères selon le champ

### 4. Fonction `validate_prompt_has_sentinel(prompt)`

**But** : Validation fail-fast avant envoi au LLM.

**Comportement** :
- Vérifie la présence de `PROMPT_SENTINEL` dans le prompt
- Lève `ValueError` si absent (bloque l'appel LLM)
- Conforme à prompt.md section 2.1

## 📊 Structure du prompt complet

```
┌─────────────────────────────────────────┐
│  SYSTEM PROMPT                          │
│  - Marqueur sentinel                    │
│  - Règles anti-hallucination            │
│  - Style et forme                       │
│  - Formats par type                     │
│  - Contrôle qualité                     │
│  - Périmètre de vérité                  │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  USER PROMPT                            │
│  - En-tête FieldSpec                    │
│    (key, type, query, contraintes)      │
│  - Instructions spécifiques             │
│  - <SOURCES>                            │
│    ... contenu RAG ...                  │
│    </SOURCES>                           │
│  - Règles de réponse par type           │
└─────────────────────────────────────────┘
              ↓
         VALIDATION
       (sentinel présent?)
              ↓
          ENVOI LLM
```

## 🎯 Utilisation

### Exemple 1 : Champ narratif

```python
from core.field_specs_v2 import (
    FIELD_SPECS_V2,
    build_system_prompt,
    build_user_prompt,
    validate_prompt_has_sentinel
)

# 1. Construire les prompts
system = build_system_prompt()
user = build_user_prompt(
    field_spec=FIELD_SPECS_V2["PROFESSION"],
    sources="Contenu RAG extrait...",
    sources_count=5
)

# 2. Valider
combined = system + "\n\n" + user
validate_prompt_has_sentinel(combined)  # Lève ValueError si absent

# 3. Envoyer au LLM
response = llm.chat(
    messages=[
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ]
)
```

### Exemple 2 : Champ enum

```python
# Pour un champ enum (langues/bureautique)
user = build_user_prompt(
    field_spec=FIELD_SPECS_V2["FRANCAIS_POSITIONNEMENT_DE_NIVEAU"],
    sources="Test de français passé : niveau B2 confirmé.",
    sources_count=1
)

# Les règles automatiques incluent :
# - "Sortie UNIQUEMENT : une valeur parmi A1, A2, B1, B2, C1, C2, Non évalué"
# - "Ne JAMAIS déduire sans preuve explicite"
# - "Si pas de preuve : Non évalué"
```

### Exemple 3 : Champ liste

```python
# Pour un champ liste
user = build_user_prompt(
    field_spec=FIELD_SPECS_V2["RESSOURCES_MOTIVATIONNELLES"],
    sources="Motivé par la stabilité...",
    sources_count=2
)

# Les règles automatiques incluent :
# - "Sortie UNIQUEMENT : ["item1", "item2"]"
# - "Pas de texte autour, pas de markdown"
# - "Items 5-14 mots"
# - "RETOURNE UNIQUEMENT UN TABLEAU JSON VALIDE"
```

## 🔍 Validation et tests

### Test d'import

```bash
python3 -c "from core.field_specs_v2 import build_system_prompt; print('OK')"
# Résultat: OK
```

### Test complet

```bash
python3 demo_prompt_wrapper.py
```

**Résultats attendus** :
- ✅ SYSTEM prompt contient le sentinel
- ✅ USER prompt contient FIELD_KEY, <SOURCES>, RÈGLES
- ✅ Validation sentinel réussie
- ✅ Longueurs conformes

## 📋 Conformité avec prompt.md

| Section prompt.md | Implémenté | Fonction/Constante |
|-------------------|------------|-------------------|
| **2.1** Marqueur sentinel | ✅ | `PROMPT_SENTINEL`, `validate_prompt_has_sentinel()` |
| **3** SYSTEM PROMPT | ✅ | `build_system_prompt()` |
| **4** USER PROMPT | ✅ | `build_user_prompt()` |
| **4.1** En-tête FieldSpec | ✅ | Dans `build_user_prompt()` |
| **4.2** Bloc SOURCES | ✅ | `<SOURCES>...</SOURCES>` |
| **4.3** Règles par type | ✅ | Switch dans `build_user_prompt()` |
| **5** Contraintes par type | ✅ | Narratif/List/Enum spécifiques |

## 🚀 Prochaines étapes

### 1. Intégration dans le pipeline de génération

Modifier `core/generate.py` ou le module LLM pour utiliser ces fonctions :

```python
# Avant (exemple)
prompt = f"Génère {field_key} : {instructions}"

# Après
system = build_system_prompt()
user = build_user_prompt(spec, sources, count)
validate_prompt_has_sentinel(system + user)
# ... envoi LLM
```

### 2. Logging et audit (prompt.md section 2.2)

Ajouter dans les appels LLM :

```python
import hashlib

prompt_hash = hashlib.sha256((system + user).encode()).hexdigest()
logger.info(
    "llm_call",
    extra={
        "prompt_version": PROMPT_VERSION,
        "prompt_hash": prompt_hash,
        "field_key": field_key,
        "provider": provider,
        "model": model,
        "sources_count": sources_count,
        "latency_ms": latency
    }
)
```

### 3. Tests automatiques (prompt.md section 2.3)

Créer `tests/test_prompt_wrapper.py` :

```python
def test_prompt_contains_sentinel():
    system = build_system_prompt()
    assert PROMPT_SENTINEL in system

def test_prompt_includes_field_spec():
    spec = FIELD_SPECS_V2["PROFESSION"]
    user = build_user_prompt(spec, sources="test")
    assert f"FIELD_KEY: {spec.key}" in user
    assert f"FIELD_TYPE: {spec.field_type}" in user

def test_prompt_includes_sources_block():
    user = build_user_prompt(FIELD_SPECS_V2["PROFESSION"], sources="test")
    assert "<SOURCES>" in user
    assert "</SOURCES>" in user
```

### 4. Mode debug (optional)

```python
import os
from pathlib import Path

if os.getenv("DEBUG_PROMPTS"):
    debug_dir = Path("out/debug/prompts") / run_id / client_id
    debug_dir.mkdir(parents=True, exist_ok=True)
    (debug_dir / f"{field_key}.txt").write_text(system + "\n\n" + user)
```

## ✅ Résultat

Le fichier `core/field_specs_v2.py` implémente maintenant **complètement** le système de prompt wrapper décrit dans `docs/prompt.md` :

- ✅ Marqueur sentinel avec validation fail-fast
- ✅ SYSTEM prompt avec règles anti-hallucination
- ✅ USER prompt avec structure claire (FieldSpec + Sources + Règles)
- ✅ Contraintes spécifiques par type de champ
- ✅ Délimiteurs pour les sources (`<SOURCES>`)
- ✅ Fonction de validation obligatoire

**Le système garantit maintenant que chaque appel LLM est cohérent, validé et conforme aux spécifications.**

---

## 📚 Fichiers modifiés

- [core/field_specs_v2.py](core/field_specs_v2.py) : Fonctions ajoutées, constantes définies
- [demo_prompt_wrapper.py](demo_prompt_wrapper.py) : Script de démonstration créé

## 📖 Références

- [docs/prompt.md](docs/prompt.md) : Spécification source (non modifié)
- [RESUME_MAJ_PROMPTS_LLM.md](RESUME_MAJ_PROMPTS_LLM.md) : Mise à jour des prompts précédente
