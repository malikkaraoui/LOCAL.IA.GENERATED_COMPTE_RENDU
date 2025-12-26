# 🎯 RH-Pro Parser — Step 6 Improvements

**Date:** 26 décembre 2025  
**Status:** ✅ Implémenté et testé

---

## 📋 Objectif Step 6

Corriger les problèmes de qualité identifiés en v1:
1. Faux mapping du titre global "BILAN D'ORIENTATION..."
2. Sections imbriquées non séparées (profession/formation fusionnés)
3. Absence d'indicateurs de qualité réalistes

---

## ✅ Corrections implémentées

### Fix #1: Ruleset strict pour `orientation_formation`

**Problème:** Le titre "BILAN D'ORIENTATION PROFESSIONNELLE" était mappé à `orientation_formation` (confidence 0.9)

**Solution:** 
- Modifié [config/rulesets/rhpro_v1.yaml](config/rulesets/rhpro_v1.yaml)
- Anchors plus stricts:
  ```yaml
  anchors:
    any:
      - exact: "Orientation & Formation"
      - contains: "ORIENTATION & FORMATION"  # Majuscules strictes
  ```

**Résultat:** Le titre global n'est plus mappé ✅

---

### Fix #2: Ignore list pour titres génériques

**Problème:** Les titres de document type "BILAN D'ORIENTATION..." polluent les mappings

**Solution:**
- Ajouté dans [src/rhpro/mapper.py](src/rhpro/mapper.py):
  ```python
  IGNORE_PATTERNS = [
      r"^BILAN\s+D['']ORIENTATION",
      r"^RAPPORT\s+D['']ORIENTATION",
      r"^DOCUMENT\s+D['']ORIENTATION",
      r"^BILAN\s+PROFESSIONNEL",
  ]
  ```

**Résultat:** Titres génériques ignorés automatiquement ✅

---

### Fix #3: Inline Extractor pour sous-sections

**Problème:** 
- `profession_formation` était une string contenant "Profession\n...\nFormation\n..."
- Impossible de remplir séparément `profession` et `formation`

**Solution:**
- Créé [src/rhpro/inline_extractor.py](src/rhpro/inline_extractor.py)
- Patterns regex robustes pour extraire:
  - `profession_formation` → `{profession: "...", formation: "..."}`
  - `orientation_formation` → `{orientation: "...", stage: "..."}`
  - `competences` → `{sociales: "...", professionnelles: "..."}`

**Exemple extraction:**
```python
content = """Profession
Le bénéficiaire a travaillé 15 ans en informatique.

Formation
CFC obtenu en 2005."""

result = extractor.extract_subsections('profession_formation', content)
# → {'profession': '...15 ans...', 'formation': 'CFC...'}
```

**Résultat:** Sous-sections correctement séparées ✅

---

### Fix #4: Normalizer amélioré

**Modifications dans [src/rhpro/normalizer.py](src/rhpro/normalizer.py):**

1. **Post-traitement automatique:**
   - Après remplissage initial, détecte les sections parents encore en string
   - Applique l'inline extraction
   - Remplace la string par un objet structuré

2. **Warnings si échec:**
   ```python
   if inline_split_fails:
       warnings.append("Inline split failed for profession_formation.profession")
   ```

3. **Pas d'invention:**
   - Si extraction échoue → créer objet vide avec bonnes clés
   - Ne jamais inventer de contenu

**Résultat:** Structure normalisée correcte ✅

---

### Bonus: Indicateurs de qualité

**Ajoutés au rapport:**

#### 1. `required_coverage_ratio`
- Couverture uniquement des sections **required**
- Plus pertinent que la couverture globale
- **Sample: 1.0 (100%)** ✅

#### 2. `weighted_coverage`
- Pondération par importance des sections:
  - `identity`: 2x
  - `profession_formation`: 3x
  - `orientation_formation`: 3x
  - `tests`: 2x
  - `competences`: 1.5x
  - `conclusion`: 1.5x
  - autres: 1x
- **Sample: 0.82 (82%)** ✅

**Résultat:** Indicateurs réalistes de qualité ✅

---

## 📊 Résultats avant/après

### Avant Step 6

```json
{
  "profession_formation": "Profession\nLe bénéficiaire...\nFormation\nCFC...",
  "orientation_formation": "Orientation\nOrientation vers...\nStage\nStage de 3 mois..."
}
```

**Rapport:**
- `missing_required_sections`: ["profession_formation.profession", "profession_formation.formation", ...]
- `coverage_ratio`: 0.19
- `warnings`: ["Required section missing: ..."]

### Après Step 6

```json
{
  "profession_formation": {
    "profession": "Le bénéficiaire a travaillé 15 ans...",
    "formation": "CFC obtenu en 2005..."
  },
  "orientation_formation": {
    "orientation": "Orientation vers la cybersécurité...",
    "stage": "Stage de 3 mois recommandé..."
  }
}
```

**Rapport:**
- `missing_required_sections`: [] ✅
- `coverage_ratio`: 0.17
- `required_coverage_ratio`: 1.0 ✅
- `weighted_coverage`: 0.82 ✅
- `warnings`: []

---

## 🧪 Tests Step 6

**Nouveaux tests:** [tests/test_rhpro_step6.py](tests/test_rhpro_step6.py)

### Test suite (12 tests)

**Ignore list:**
- ✅ Titres "BILAN D'ORIENTATION..." ignorés
- ✅ Vrais titres non ignorés

**Inline Extractor:**
- ✅ Extraction `profession_formation`
- ✅ Extraction `orientation_formation`
- ✅ Extraction `competences`

**Améliorations complètes:**
- ✅ BILAN... non mappé à orientation_formation
- ✅ `profession_formation` est un objet
- ✅ `orientation_formation` est un objet
- ✅ `competences` est un objet
- ✅ `missing_required_sections` = []
- ✅ `required_coverage_ratio` = 1.0
- ✅ `weighted_coverage` > `coverage_ratio`

**Résultat:** 12/12 tests passent ✅

---

## 📁 Fichiers modifiés/créés

**Modifiés:**
- `config/rulesets/rhpro_v1.yaml` — Anchors orientation_formation strictes
- `src/rhpro/mapper.py` — Ignore list + méthode `_should_ignore_title()`
- `src/rhpro/normalizer.py` — Post-traitement inline + nouveaux indicateurs

**Créés:**
- `src/rhpro/inline_extractor.py` — Extraction sous-sections (70 lignes)
- `tests/test_rhpro_step6.py` — Tests Step 6 (180 lignes, 12 tests)

---

## 🎯 Impact sur la qualité

### Métriques clés

| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| Sections requises manquantes | 3 | 0 | ✅ 100% |
| Required coverage | N/A | 100% | ✅ |
| Weighted coverage | N/A | 82% | ✅ |
| Faux positifs | 1 | 0 | ✅ |
| Structure normalisée | ❌ Strings | ✅ Objets | ✅ |

### Prêt pour batch

Avec `required_coverage_ratio = 1.0` et `weighted_coverage = 0.82`:
- ✅ Toutes les sections clés sont extraites
- ✅ Structure conforme au schéma attendu
- ✅ Pas d'invention de contenu
- ✅ Indicateurs fiables pour décider "OK pour batch sur 20 docs"

---

## 🚀 Usage

### CLI (inchangé)
```bash
python demo_rhpro_parse.py path/to/bilan.docx
```

### Python (même API)
```python
from src.rhpro.parse_bilan import parse_bilan_from_paths

result = parse_bilan_from_paths('bilan.docx')

# Nouvelles métriques disponibles
print(f"Required coverage: {result['report']['required_coverage_ratio']}")
print(f"Weighted coverage: {result['report']['weighted_coverage']}")

# Structure normalisée améliorée
assert isinstance(result['normalized']['profession_formation'], dict)
assert 'profession' in result['normalized']['profession_formation']
```

### Tests
```bash
# Tous les tests (19 au total)
pytest tests/test_rhpro_*.py -v

# Seulement Step 6
pytest tests/test_rhpro_step6.py -v
```

---

## 📝 Notes d'implémentation

### Patterns regex utilisés

**Profession/Formation:**
```python
'profession': r'(?ims)\bProfession\b\s*(?:\n|:)\s*(.+?)(?=\n\s*\bFormation\b\s*(?:\n|:)|\Z)'
'formation': r'(?ims)\bFormation\b\s*(?:\n|:)\s*(.+?)(?=\n\s*\b[A-ZÀ-ÖØ-Þ].{2,}|\Z)'
```

**Orientation/Stage:**
```python
'orientation': r'(?ims)\bOrientation\b\s*(?:\n|:)\s*(.+?)(?=\n\s*\bStage\b\s*(?:\n|:)|\Z)'
'stage': r'(?ims)\bStage\b\s*(?:\n|:)\s*(.+?)\Z'
```

### Gestion des échecs

Si l'extraction inline échoue:
1. Créer un dict vide avec les clés attendues
2. Ajouter un warning dans le rapport
3. Ne jamais inventer de contenu

---

## ✅ Definition of Done Step 6

- [x] BILAN D'ORIENTATION... non mappé
- [x] `missing_required_sections` = []
- [x] Structure normalisée avec objets (pas strings)
- [x] `required_coverage_ratio` ajouté
- [x] `weighted_coverage` ajouté
- [x] Warnings si inline split échoue
- [x] Aucune invention de contenu
- [x] 12 tests Step 6 passent
- [x] Tests v1 toujours OK (7/7)
- [x] Documentation complète

---

## 🎉 Prêt pour production !

Le parser est maintenant capable de:
- ✅ Ignorer les titres de document génériques
- ✅ Extraire les sous-sections correctement
- ✅ Fournir des indicateurs de qualité réalistes
- ✅ Produire une structure normalisée exploitable

**Qualité validée sur sample: 100% required coverage + 82% weighted coverage**
