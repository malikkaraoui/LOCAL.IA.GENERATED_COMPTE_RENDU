# Production Gate Profiles - Documentation Complète

## Vue d'ensemble

Le système de **Production Gate** permet une validation GO/NO-GO sophistiquée des documents RH-Pro selon leur type et leur complétude. Il implémente une sélection automatique de profils basée sur des signaux détectés dans le document.

## Architecture

### 1. Configuration (YAML)

Les profils sont définis dans `config/rulesets/rhpro_v1.yaml` :

```yaml
production_gate:
  enabled: true
  default_profile: placement_suivi
  
  profiles:
    bilan_complet:
      description: "Profil strict pour bilans complets"
      thresholds:
        max_missing_required: 0
        min_required_coverage_ratio: 0.95
        max_unknown_titles: 3
        max_placeholders: 2
      ignore_required_prefixes: []
    
    placement_suivi:
      description: "Profil tolérant pour placement/suivi"
      thresholds:
        max_missing_required: 2
        min_required_coverage_ratio: 0.85
        max_unknown_titles: 10
        max_placeholders: 5
      ignore_required_prefixes:
        - tests
        - vocation
        - profil_emploi
        - dossier_presentation
    
    stage:
      description: "Profil spécifique pour bilans de stage"
      thresholds:
        max_missing_required: 1
        min_required_coverage_ratio: 0.70
        max_unknown_titles: 10
        max_placeholders: 5
      ignore_required_prefixes:
        - tests
        - vocation
        - profil_emploi
```

### 2. Détection automatique

La méthode `_choose_gate_profile()` dans `src/rhpro/normalizer.py` détecte automatiquement le profil approprié selon un ordre hiérarchique :

#### Ordre de détection :

1. **Profil `stage`** - Si détection de :
   - Mots-clés "stage" dans les titres OU
   - Section `orientation_formation.stage` présente

2. **Profil `bilan_complet`** - Si détection de ≥2 parmi :
   - Section `tests` présente
   - Section `vocation` présente
   - Section `profil_emploi` présente
   - Section `dossier_presentation.ressources_professionnelles` présente

3. **Profil `bilan_complet`** - Si détection de "LAI 15" ou "LAI 18" dans les titres

4. **Profil `placement_suivi`** (par défaut) - Si aucun des critères précédents

#### Signaux retournés :

```python
signals = {
    'has_stage': bool,
    'has_tests': bool,
    'has_vocation': bool,
    'has_profil_emploi': bool,
    'has_ressources_professionnelles': bool,
    'has_lai15': bool,
    'has_lai18': bool,
    'matched_titles': List[str],
    'bilan_complet_sections_count': int
}
```

### 3. Évaluation GO/NO-GO

La méthode `_evaluate_production_gate()` évalue si un document est prêt pour la production :

#### Filtrage avec `ignore_required_prefixes`

Chaque profil peut ignorer certaines sections requises via des préfixes :
- Obtient tous les chemins `required` du ruleset
- Filtre ceux commençant par les préfixes ignorés
- Recalcule le `required_coverage_ratio_effective` sur les sections non-ignorées

#### Critères d'évaluation

1. **Sections requises manquantes** : 
   - Compte les sections `required` manquantes (après filtrage)
   - Comparaison : `missing_required_effective <= max_missing_required`

2. **Couverture des sections requises** :
   - Calcule : `(required_filled / required_total) >= min_required_coverage_ratio`
   - Utilise les valeurs effectives après filtrage

3. **Titres inconnus** :
   - Comparaison : `unknown_titles_count <= max_unknown_titles`

4. **Placeholders** :
   - Comparaison : `placeholders_count <= max_placeholders`

#### Sortie

```python
{
    'status': 'GO' | 'NO-GO',
    'profile': 'placement_suivi',
    'signals': { ... },  # Signaux de détection
    'reasons': [...],    # Raisons du NO-GO
    'criteria': {
        'required_sections_ok': bool,
        'required_coverage_ok': bool,
        'unknown_titles_ok': bool,
        'placeholders_ok': bool
    },
    'metrics': {
        'required_coverage_ratio': 0.87,          # Global
        'required_coverage_ratio_effective': 0.92, # Après filtrage
        'unknown_titles_count': 3,
        'placeholders_count': 1,
        'missing_required_sections_count': 2,
        'missing_required_effective': 1
    },
    'missing_required_effective': ['identity']
}
```

## Utilisation

### CLI

```bash
# Auto-détection du profil
python demo_rhpro_parse.py data/samples/document.docx

# Forcer un profil spécifique
python demo_rhpro_parse.py data/samples/document.docx --gate-profile stage
python demo_rhpro_parse.py data/samples/document.docx --gate-profile bilan_complet
python demo_rhpro_parse.py data/samples/document.docx --gate-profile placement_suivi
```

### API Python

```python
from src.rhpro.normalizer import Normalizer
from src.rhpro.ruleset_loader import RulesetLoader

# Initialisation
ruleset = RulesetLoader('config/rulesets/rhpro_v1.yaml')
normalizer = Normalizer(ruleset)

# Parse avec auto-détection
result = normalizer.parse_docx('document.docx')

# Parse avec profil forcé
result = normalizer.parse_docx('document.docx', gate_profile='stage')

# Accès aux résultats
print(f"Profil détecté : {result['production_gate']['profile']}")
print(f"Status : {result['production_gate']['status']}")
print(f"Signaux : {result['production_gate']['signals']}")
```

## Tests

Suite de tests complète dans `tests/test_production_gate_profiles.py` :

```bash
# Exécuter tous les tests
pytest tests/test_production_gate_profiles.py -v

# Tests de sélection de profil
pytest tests/test_production_gate_profiles.py::TestGateProfileSelection -v

# Tests d'évaluation GO/NO-GO
pytest tests/test_production_gate_profiles.py::TestGateProfileEvaluation -v

# Tests d'intégration
pytest tests/test_production_gate_profiles.py::TestGateProfileIntegration -v
```

### Couverture des tests

- ✅ 18 tests unitaires
- ✅ Détection automatique par mots-clés
- ✅ Détection par sections présentes
- ✅ Priorité entre profils
- ✅ Évaluation GO/NO-GO selon seuils
- ✅ Filtrage avec `ignore_required_prefixes`
- ✅ Override CLI
- ✅ Métriques globales vs effectives

## Sections Required du Ruleset

Le ruleset définit actuellement **4 sections required** :

1. `identity` - Identité du bénéficiaire
2. `profession_formation` - Profession & Formation
3. `orientation_formation` - Orientation & Formation
4. `orientation_formation.orientation` - Sous-section Orientation

Les profils `placement_suivi` et `stage` ignorent certaines sections via `ignore_required_prefixes`, mais aucune des 4 sections ci-dessus n'est ignorée.

## Exemples

### Exemple 1 : Bilan de stage

**Document** : Contient le titre "Bilan de stage - Mars 2024"

**Détection** :
- Signal `has_stage = True`
- Profil sélectionné : `stage`

**Évaluation** :
- 3/4 sections required présentes → coverage = 75% > 70% ✓
- 1 section manquante ≤ 1 max ✓
- 5 titres inconnus ≤ 10 max ✓
- 2 placeholders ≤ 5 max ✓
- **Résultat : GO**

### Exemple 2 : Bilan complet LAI 15

**Document** : Contient le titre "Bilan de compétences LAI 15"

**Détection** :
- Signal `has_lai15 = True`
- Profil sélectionné : `bilan_complet`

**Évaluation** :
- 2/4 sections required présentes → coverage = 50% < 95% ✗
- **Résultat : NO-GO**
- Raison : "Required coverage too low: 50% < 95%"

### Exemple 3 : Document de placement

**Document** : Titre standard sans mots-clés spécifiques

**Détection** :
- Aucun signal spécifique
- Profil sélectionné : `placement_suivi` (par défaut)

**Évaluation** :
- 3/4 sections required présentes → coverage_effective = 75% < 85% ✗
- Mais profil tolérant : max_missing_required = 2, 1 section manquante ✓
- **Résultat : NO-GO**
- Raison : "Required coverage too low: 75% < 85%"

## Backward Compatibility

- ✅ Si `production_gate.enabled = false` → pas de validation
- ✅ Si profil invalide/inconnu → fallback sur `placement_suivi`
- ✅ Si profil non spécifié → auto-détection
- ✅ Métriques globales toujours présentes dans l'output

## Évolutions futures

Possibilités d'extension :

1. **Nouveaux profils** : Ajouter d'autres profils dans le YAML
2. **Signaux supplémentaires** : Enrichir la détection (nombre de pages, présence d'annexes, etc.)
3. **Scoring pondéré** : Remplacer la logique hiérarchique par un système de scores
4. **Machine Learning** : Classifier automatiquement les documents
5. **Validation personnalisée** : Permettre aux clients de définir leurs propres seuils

## Références

- Configuration : [config/rulesets/rhpro_v1.yaml](../config/rulesets/rhpro_v1.yaml)
- Code principal : [src/rhpro/normalizer.py](../src/rhpro/normalizer.py)
- Loader : [src/rhpro/ruleset_loader.py](../src/rhpro/ruleset_loader.py)
- Tests : [tests/test_production_gate_profiles.py](../tests/test_production_gate_profiles.py)
- Démo CLI : [demo_rhpro_parse.py](../demo_rhpro_parse.py)
