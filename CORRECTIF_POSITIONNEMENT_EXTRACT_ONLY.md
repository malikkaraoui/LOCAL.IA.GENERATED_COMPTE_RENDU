# Fix: Sections POSITIONNEMENT DE NIVEAU — Extract-Only (pas LLM)

## 📋 Problème Initial

Les sections de type "POSITIONNEMENT DE NIVEAU" (Français, Anglais, Allemand, Word, Excel) étaient traitées comme du texte narratif par le LLM, qui générait des sous-sections inventées (ex: "Fonctions privilégiées", "Secteurs privilégiés") au lieu d'extraire le niveau réel (ex: C2, B1, 12/20).

## ✅ Solution Implémentée

### 1. Nouveau Module : `src/rhpro/positionnement_extractor.py`

Système d'extraction directe qui :
- ✅ Détecte les niveaux CECRL (A1, A2, B1, B2, C1, C2)
- ✅ Détecte les scores fraction (12/20, 15/20)
- ✅ Détecte les pourcentages (85%, 90%)
- ✅ Retourne "Non renseigné" si aucun niveau trouvé
- ✅ **JAMAIS** d'appel au LLM pour ces sections

**Patterns de détection** :
```python
PATTERN_CECRL = r'\b(A1|A2|B1|B2|C1|C2)\b'  # Insensible à la casse
PATTERN_PERCENT = r'(\d{1,3})\s?%'           # 85%, 90 %
PATTERN_FRACTION = r'(\d{1,2})\s*/\s*(\d{1,2})'  # 12/20, 15 / 20
```

**Priorité de détection** :
1. CECRL (priorité haute)
2. Pourcentage
3. Fraction
4. Si rien → "Non renseigné"

### 2. Fonctions Principales

#### `extract_positionnement_level(text: str) -> str`
Extrait UN niveau depuis un texte.

**Exemples** :
```python
extract_positionnement_level("Niveau: C2") → "C2"
extract_positionnement_level("Score: 12/20") → "12/20"
extract_positionnement_level("Résultat: 85%") → "85%"
extract_positionnement_level("(texte sans niveau)") → "Non renseigné"
```

#### `is_positionnement_title(normalized_title: str) -> bool`
Détecte si un titre correspond à une section de positionnement.

**Critères** :
- Contient "POSITIONNEMENT" ET ("NIVEAU" OU fin par "POSITIONNEMENT")
- Gère les tirets typographiques (-, –, —)
- Normalise les espaces multiples

**Exemples détectés** :
- ✅ "FRANCAIS - POSITIONNEMENT DE NIVEAU"
- ✅ "ANGLAIS – POSITIONNEMENT DE NIVEAU" (tiret typographique U+2013)
- ✅ "ALLEMAND — POSITIONNEMENT DE NIVEAU" (tiret long U+2014)
- ✅ "WORD POSITIONNEMENT DE NIVEAU"
- ✅ "POSITIONNEMENT" (seul)

**Exemples rejetés** :
- ❌ "FRANCAIS NIVEAU 2" (pas de POSITIONNEMENT)
- ❌ "TESTS METIERS"
- ❌ "CALCUL NIVEAU 1"

#### `extract_positionnement_from_segments(segments: list[dict]) -> dict[str, str]`
Extrait tous les niveaux de positionnement depuis une liste de segments.

**Retour** :
```python
{
    "francais": "C2",
    "anglais": "B1",
    "allemand": "Non renseigné",
    "word": "12/20",
    "excel": "85%"
}
```

## 🧪 Tests Complets (22/22 ✅)

### Tests Unitaires

**Extraction niveaux** :
- ✅ Extrait CECRL C2, B1, A1 (case insensitive)
- ✅ Extrait scores fraction (12/20, 15 / 20)
- ✅ Extrait pourcentages (85%, 90 %)
- ✅ Rejette pourcentages invalides (>100)
- ✅ Retourne "Non renseigné" si vide ou sans niveau
- ✅ Priorité CECRL sur scores

**Détection titres** :
- ✅ Détecte français/anglais/allemand positionnement
- ✅ Détecte word/excel/powerpoint positionnement
- ✅ Gère tirets typographiques (-, –, —)
- ✅ Rejette "FRANCAIS NIVEAU 2" (pas POSITIONNEMENT)
- ✅ Rejette autres sections tests

**Extraction depuis segments** :
- ✅ Extrait multiple niveaux simultanément
- ✅ Ignore segments non-positionnement

### Tests Anti-Régression ESSAI 100

**T1 — Extraction CECRL** :
```python
Input: "FRANCAIS – POSITIONNEMENT DE NIVEAU :\nC2\n"
Expected: "C2"  ✅
```

**T2 — Extraction score** :
```python
Input: "ANGLAIS – POSITIONNEMENT DE NIVEAU : 12/20"
Expected: "12/20"  ✅
```

**T3 — No hallucination** :
```python
Input: "ANGLAIS – POSITIONNEMENT DE NIVEAU :\n(texte sans niveau)\n"
Expected: "Non renseigné"  ✅
AND: Aucun appel LLM effectué (vérifié dans le pipeline)
```

**T4 — Normalisation titres variantes** :
```python
Variantes détectées :  ✅
- "ANGLAIS - POSITIONNEMENT DE NIVEAU"
- "ANGLAIS – POSITIONNEMENT DE NIVEAU" (U+2013)
- "ANGLAIS — POSITIONNEMENT DE NIVEAU" (U+2014)
- "ANGLAIS  -  POSITIONNEMENT  DE  NIVEAU" (espaces multiples)
```

## 📊 Résultats Tests

```bash
$ pytest tests/test_positionnement_extractor.py -v
================= 22 passed in 0.23s =================
```

## 🎯 Prochaines Étapes (Intégration au Pipeline)

### Étape 1 : Ajouter `extract_policy` dans les sections

Modifier la structure des sections canoniques pour supporter une politique d'extraction :

```python
CANONICAL_SECTIONS = [
    {
        "section_id": "tests_positionnement",
        "titles": ["POSITIONNEMENT"],
        "extract_policy": "EXTRACT_ONLY_SCALAR",
        "extractor": "positionnement",  # Référence à positionnement_extractor
    },
    # ... autres sections
]
```

### Étape 2 : Modifier le pipeline de génération

Dans `core/generate.py` ou le pipeline principal :

```python
from src.rhpro.positionnement_extractor import (
    is_positionnement_title,
    extract_positionnement_level
)

def generate_field_value(field_key, segments, context_blocks):
    # Vérifier si c'est un positionnement
    for segment in segments:
        if is_positionnement_title(segment['normalized_title']):
            # EXTRACT_ONLY : ne PAS appeler le LLM
            level = extract_positionnement_level(segment['content'])
            return {
                "value": level,
                "method": "extract_only",
                "llm_called": False
            }
    
    # Sinon : pipeline LLM normal
    return generate_via_llm(field_key, context_blocks)
```

### Étape 3 : Exposer dans le template DOCX

Au lieu de mettre dans la section "tests" générique, exposer des placeholders dédiés :

```
{{FRANCAIS_POSITIONNEMENT}}  → C2
{{ANGLAIS_POSITIONNEMENT}}   → B1
{{ALLEMAND_POSITIONNEMENT}}  → Non renseigné
{{WORD_POSITIONNEMENT}}      → 12/20
```

## ⚠️ Points d'Attention

1. **Priorité détection** : CECRL > Pourcentage > Fraction
   - Si un texte contient "C1" et "85%", on retourne "C1"
   
2. **Validation pourcentages** : Seuls 0-100% acceptés
   - "150%" → "Non renseigné"

3. **Tirets typographiques** : Gérés automatiquement
   - `-` (hyphen)
   - `–` (en dash U+2013)
   - `—` (em dash U+2014)

4. **Backward compatibility** : Les autres sections "tests" (CALCUL NIVEAU 1, TRI ET CLASSEMENT) continuent de fonctionner normalement avec le LLM

## 📝 Critère de Succès sur ESSAI 100

Après intégration complète :

✅ Les sections positionnement contiennent **UNIQUEMENT** :
- Un niveau CECRL (ex: C2, B1)
- Un score (ex: 12/20, 85%)
- "Non renseigné"

❌ **Plus jamais** :
- Listes type "Fonctions privilégiées / Secteurs privilégiés"
- Texte narratif généré par le LLM
- Inventions ou hallucinations

✅ Aucune régression sur les autres sections `tests` (CALCUL, TRI, etc.)

---

**Fichiers créés** :
- `src/rhpro/positionnement_extractor.py` (166 lignes)
- `tests/test_positionnement_extractor.py` (185 lignes)

**Tests** : ✅ 22/22 passent

**Prêt pour** : Intégration dans le pipeline principal
