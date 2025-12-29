# PATCH 9 : Priorité GOLD pour bilan_complet

**Date**: 29 décembre 2025  
**Objectif**: Corriger la sélection automatique du GOLD pour éviter de choisir "Journal" et "Evaluation de stage" comme document structurant.

## Contexte

**Problème observé**: Dans les screenshots utilisateurs, des documents comme "Journal de bilan" et "Evaluation de stage" étaient sélectionnés automatiquement comme GOLD (document structurant), causant des NO-GO ou des extractions de mauvaise qualité.

**Impact**: Taux élevé de NO-GO car ces documents ne contiennent pas la structure RH-Pro attendue (sections identity, profession, orientation, etc.).

## Solution Implémentée

### Hiérarchie de Priorité

**Priorité HAUTE** (score 50 points) :
- "Bilan final"
- "Rapport final"
- "Bilan général"
- "Bilan d'orientation"
- "Synthèse finale"

**Priorité MOYENNE** (score 30 points) :
- "Rapport RH-Pro"
- "Rapport RHPRO"

**Priorité BASSE** (score 8 points par keyword) :
- Mots-clés simples : "bilan", "rapport", "orientation", "synthèse", "final", "lai"

**EXCLUSIONS STRICTES** (score 0, rejet total) :
- "journal"
- "evaluation de stage" / "évaluation de stage"
- "test"
- "contrat"
- "devis"
- "facture"
- "attestation"
- "certificat"
- "cv"

### Modifications Techniques

#### 1. `client_scanner.py` - Scoring GOLD

```python
# PATCH 9: Nouvelles listes de keywords avec priorités
GOLD_KEYWORDS_HIGH_PRIORITY = [
    "bilan final",
    "rapport final",
    "bilan général",
    # ...
]

GOLD_KEYWORDS_MEDIUM_PRIORITY = [
    "rapport", "bilan", "orientation", # ...
]

GOLD_EXCLUDE_PATTERNS = [
    "journal",
    "evaluation de stage",
    # ...
]

def score_gold_candidate(file_path: Path, profile: str = "bilan_complet") -> float:
    """Score avec exclusions strictes et priorités différenciées."""
    
    # EXCLUSION stricte AVANT scoring
    if any(pattern in filename for pattern in GOLD_EXCLUDE_PATTERNS):
        return 0.0
    
    # Priorité haute : +0.5 pour keywords composés
    if any(kw in filename for kw in GOLD_KEYWORDS_HIGH_PRIORITY):
        score += 0.5
    
    # Priorité moyenne : +0.3 max pour keywords simples
    # ...
```

#### 2. `client_finder.py` - Sélection automatique

```python
# Keywords par niveau de priorité
COMPOSITE_KEYWORDS_HIGH = [
    'bilan final', 'rapport final', 'bilan général', 
    'bilan d\'orientation', 'synthèse finale'
]

COMPOSITE_KEYWORDS_MEDIUM = [
    'rapport rh-pro', 'rapport rhpro'
]

# Scoring avec réduction de l'impact de la structure
def select_best_source_docx(docx_paths, profile="bilan_complet"):
    for docx_path in docx_paths:
        # Exclusion stricte
        if any(keyword in filename for keyword in REJECT_KEYWORDS):
            continue
        
        # Priorité HAUTE : +50 points
        if any(composite in filename for composite in COMPOSITE_KEYWORDS_HIGH):
            score += 50.0
        
        # Priorité MOYENNE : +30 points
        elif any(composite in filename for composite in COMPOSITE_KEYWORDS_MEDIUM):
            score += 30.0
        
        # Analyse structure avec poids réduit si HIGH priority
        # (pour éviter qu'un "Rapport RH-Pro" bien structuré surpasse un "Bilan final")
        if high_composite_match:
            structure_bonus *= 0.5  # Diviser par 2
```

### Réduction du Poids de la Structure

Pour garantir que les keywords HIGH ont toujours priorité, même face à un document bien structuré :

- **Headings** : Max 3 points (au lieu de 5), divisé par 2 si HIGH match
- **Anchors RH-Pro** : 2 points par anchor (au lieu de 3), divisé par 2 si HIGH match
- **Taille** : Max 3 points (au lieu de 5), divisé par 2 si HIGH match

**Résultat** : Un "Bilan final" avec structure minimale (score ~50) battra toujours un "Rapport RH-Pro" bien structuré (score ~40 max).

## Tests

**Fichier** : `tests/test_gold_priority_patch9.py`

### Tests Unitaires (14 tests)

1. ✅ `test_exclude_journal_from_gold` - Journal score = 0
2. ✅ `test_exclude_evaluation_stage_from_gold` - Evaluation stage score = 0
3. ✅ `test_bilan_final_high_priority` - Bilan final score > 0.5
4. ✅ `test_rapport_final_high_priority` - Rapport final score > 0.5
5. ✅ `test_bilan_orientation_high_priority` - Bilan orientation score > 0.5
6. ✅ `test_rapport_rhpro_medium_priority` - Rapport RH-Pro score > 0.3
7. ✅ `test_priority_order_bilan_final_vs_journal` - Bilan final > Journal
8. ✅ `test_priority_order_bilan_final_vs_evaluation` - Bilan final > Evaluation
9. ✅ `test_priority_order_rapport_final_vs_journal` - Rapport final > Journal
10. ✅ `test_priority_order_bilan_general_vs_journal` - Bilan général > Journal
11. ✅ `test_priority_order_rapport_rhpro_vs_journal` - Rapport RH-Pro > Journal
12. ✅ `test_only_journal_returns_none` - Si seul Journal → None
13. ✅ `test_only_evaluation_returns_none` - Si seule Evaluation → None
14. ✅ `test_complete_priority_cascade` - Cascade complète (Bilan final gagne)

**Résultat** : ✅ **14/14 tests passent**

### Tests de Régression

Tests Patch 4 (`test_exclude_devis.py`) : ✅ **13/13 tests passent**

## Impact Attendu

### Réduction des NO-GO

**Avant PATCH 9** :
- Journal/Evaluation de stage sélectionnés comme GOLD
- Sections RH-Pro non détectées
- NO-GO production gate

**Après PATCH 9** :
- Vrais bilans/rapports finaux priorisés
- Structure RH-Pro correctement extraite
- Réduction estimée : **30-50% des NO-GO** causés par mauvais choix de GOLD

### Ordre de Priorité Final

Dans un dossier avec plusieurs documents, l'ordre de sélection est :

1. **Bilan final** (score ~50-55)
2. **Rapport final** (score ~50-55)
3. **Bilan général** (score ~50-55)
4. **Bilan d'orientation** (score ~50-55)
5. **Synthèse finale** (score ~50-55)
6. **Rapport RH-Pro** (score ~30-40)
7. **Rapport** (score ~20-30)
8. ~~Journal~~ (EXCLU, score 0)
9. ~~Evaluation de stage~~ (EXCLU, score 0)

## Cas Limites

### Journal avec "Bilan" dans le nom

**Exemple** : `Journal de bilan.docx`

**Comportement** : EXCLU car "journal" matche avant le scoring

### Rapport bien structuré vs Bilan final minimal

**Exemple** :
- `Rapport RH-Pro.docx` : 50 paragraphes, 10 headings, 5 anchors → score ~40
- `Bilan final.docx` : 5 paragraphes, 0 headings → score ~50

**Comportement** : Bilan final gagne car priorité HIGH (50 > 40)

### Aucun document valide

**Exemple** : Seuls `Journal.docx` et `Evaluation de stage.docx` disponibles

**Comportement** : `select_best_source_docx()` retourne `(None, "NONE")`

## Compatibilité

- ✅ Compatible avec Patches 1-4 (file filtering, devis exclusion)
- ✅ Compatible avec Patches 6-7 (identity extraction globale)
- ✅ Compatible avec DRAFT mode (Patches A-C)
- ✅ Compatible avec Quick Win (folder name fallback)
- ✅ Pas de breaking change

## Migration

### Pour les utilisateurs

**Aucune action requise**. Le PATCH 9 s'active automatiquement :
- Dans `client_report_generator.py` (UI Streamlit)
- Dans `dataset_training.py` (pipeline training)
- Dans tous les appels à `select_best_source_docx()`

### Pour les développeurs

Si vous appelez `score_gold_candidate()` manuellement, le paramètre `profile` est optionnel :

```python
# Avant (toujours valide)
score = score_gold_candidate(file_path)

# Après (optionnel, pour futurs profils spécifiques)
score = score_gold_candidate(file_path, profile="bilan_complet")
```

## Prochaines Étapes

### Améliorations futures (optionnel)

1. **Scoring adaptatif par profil** :
   - Pour `placement_suivi` : privilégier "Rapport de suivi", "Grille d'évaluation"
   - Pour `stage` : autoriser "Evaluation de stage" comme GOLD valide

2. **Détection de sous-types** :
   - "Bilan intermédiaire" vs "Bilan final"
   - "Rapport provisoire" vs "Rapport final"

3. **ML model pour scoring** :
   - Apprendre les patterns depuis le dataset
   - Prédire la qualité du GOLD sans keywords

## Conclusion

PATCH 9 apporte une **correction critique** pour la robustesse du système :

- **Priorité claire** : Bilan final > Rapport RH-Pro > Journal (exclu)
- **Tests complets** : 14/14 nouveaux tests + régression
- **Impact immédiat** : Réduction estimée de 30-50% des NO-GO
- **Backward compatible** : Aucune migration requise

**Statut** : ✅ **READY FOR PRODUCTION**

---

**Fichiers modifiés** :
- [src/rhpro/client_scanner.py](../src/rhpro/client_scanner.py) : +40 lignes
- [src/rhpro/client_finder.py](../src/rhpro/client_finder.py) : +30 lignes
- [tests/test_gold_priority_patch9.py](../tests/test_gold_priority_patch9.py) : 270 lignes (nouveau)

**Commits** :
- PATCH 9: Priorité GOLD pour bilan_complet (exclure journal/evaluation stage)
