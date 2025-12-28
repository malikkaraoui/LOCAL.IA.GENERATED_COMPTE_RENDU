# Production Gate - Système de Scoring v2 (Durci)

## 🎯 Objectif du durcissement

Éliminer les faux positifs et rendre le système de sélection de profil plus robuste et explicable via un scoring déterministe.

## 📊 Changements majeurs

### 1. Calcul des signaux UNIQUEMENT depuis les titres (headings)

**Avant** : Les signaux étaient calculés depuis tous les titres normalisés ET le texte des paragraphes.

**Après** : Les signaux sont calculés **UNIQUEMENT** depuis :
- Les titres détectés (`segment.normalized_title`)
- Les `section_id` mappés (source fiable)

**Avantage** : Évite les faux positifs quand "stage" apparaît dans le contenu mais pas dans les titres.

```python
# Collecter UNIQUEMENT les titres normalisés (headings détectés)
# PAS le contenu des paragraphes pour éviter faux positifs
heading_titles = []
for segment in segments:
    if segment.normalized_title:
        heading_titles.append(segment.normalized_title.lower())
```

### 2. Remplacement de l'heuristique if/elif par un scoring

**Avant** : Ordre fixe avec priorités en dur
```python
if has_stage:
    return 'stage'
elif bilan_complet_sections >= 2:
    return 'bilan_complet'
elif has_lai15 or has_lai18:
    return 'placement_suivi'
else:
    return default_profile
```

**Après** : Scoring déterministe par profil
```python
scores = {
    'stage': 0,
    'bilan_complet': 0,
    'placement_suivi': 0
}

# Profil STAGE: signaux forts
if signals['has_stage']:
    scores['stage'] += 100  # Signal fort exclusif

# Profil BILAN_COMPLET: sections spécifiques
scores['bilan_complet'] += signals['bilan_complet_sections_count'] * 30
if signals['has_lai15'] or signals['has_lai18']:
    scores['bilan_complet'] += 25

# Profil PLACEMENT_SUIVI: tolérant par défaut
scores['placement_suivi'] += 10  # Score de base
if signals['bilan_complet_sections_count'] == 0:
    scores['placement_suivi'] += 20  # Bonus si document léger
```

### 3. Enrichissement du retour avec scoring info

**Ajouts dans `signals`** :
- `scores` : Dict avec le score de chaque profil
- `selection_confidence` : Delta entre top1 et top2 (mesure de certitude)
- `profile_ranking` : Liste ordonnée des profils par score décroissant
- `matched_titles` : Titres matchés (tronqués à 40 chars pour lisibilité)

**Exemple de sortie** :
```json
{
  "profile_id": "stage",
  "signals": {
    "has_stage": true,
    "has_tests": false,
    "bilan_complet_sections_count": 0,
    "matched_titles": ["stage:bilan de stage - mars 2024"],
    "scores": {
      "stage": 120,
      "bilan_complet": -20,
      "placement_suivi": 30
    },
    "selection_confidence": 90,
    "profile_ranking": ["stage", "placement_suivi", "bilan_complet"]
  }
}
```

## 🧪 Tests ajoutés (5 nouveaux)

### Test 1: Faux positif "stage" dans contenu
```python
def test_false_positive_stage_in_content_not_title():
    """'stage' dans contenu mais pas dans les titres
    Le système NE doit PAS détecter 'stage'"""
```

### Test 2: Cas ambigu avec scoring
```python
def test_ambiguous_case_with_scoring():
    """Document avec signaux mixtes
    Le scoring doit trancher de manière déterministe"""
```

### Test 3: Haute confidence pour signal fort
```python
def test_high_confidence_stage_detection():
    """Signal fort 'stage' doit donner une haute confidence
    confidence >= 50"""
```

### Test 4: Troncation des matched_titles
```python
def test_matched_titles_truncation():
    """Les matched_titles doivent être tronqués à 40 chars
    pour lisibilité"""
```

### Test 5: Fallback si tous scores nuls
```python
def test_scoring_all_zeros_fallback_to_default():
    """Si tous scores <= 0, fallback sur profil par défaut"""
```

## 📈 Résultats

**Tests** : 23/23 passent ✅ (18 anciens + 5 nouveaux)

**Exemples de scores** :

| Scénario | Profil sélectionné | Scores | Confidence |
|----------|-------------------|---------|------------|
| Bilan de stage | stage | stage:120, bc:-20, ps:30 | 90 |
| LAI 15 + tests | bilan_complet | stage:0, bc:85, ps:25 | 60 |
| Document léger | placement_suivi | stage:0, bc:-20, ps:30 | 30 |
| Tests + vocation | bilan_complet | stage:0, bc:90, ps:10 | 80 |

## 🎛️ Poids du scoring (ajustables)

### Profil STAGE
- Signal `has_stage` : **+100** (signal fort exclusif)
- Section `orientation_formation` présente : **+20**

### Profil BILAN_COMPLET
- Chaque section spécifique (tests/vocation/profil_emploi) : **+30**
- LAI 15/18 détecté : **+25**
- Pénalité si < 2 sections : **-20**

### Profil PLACEMENT_SUIVI
- Score de base (défaut tolérant) : **+10**
- LAI 15/18 détecté : **+15**
- Bonus si aucune section spécifique : **+20**

## 🔧 Ajustements possibles

Pour affiner le comportement selon les retours terrain :

1. **Augmenter la sensibilité au LAI** : Modifier les poids LAI (actuellement +25 pour bc, +15 pour ps)
2. **Favoriser/pénaliser un profil** : Ajuster les scores de base
3. **Ajouter de nouveaux signaux** : Par ex. détecter "reconversion", "bilan express", etc.
4. **Modifier les seuils de confidence** : Pour alerter si sélection incertaine

## 📊 Affichage dans le rapport

Le rapport inclut maintenant :

```json
{
  "production_gate": {
    "status": "GO",
    "profile": "stage",
    "signals": {
      "has_stage": true,
      "scores": {"stage": 120, "bilan_complet": -20, "placement_suivi": 30},
      "selection_confidence": 90,
      "profile_ranking": ["stage", "placement_suivi", "bilan_complet"],
      "matched_titles": ["stage:bilan de stage"]
    },
    "criteria": {...},
    "metrics": {
      "required_coverage_ratio": 0.75,
      "required_coverage_ratio_effective": 0.85
    }
  }
}
```

## 🚀 Migration

**Backward compatible** : Les anciens tests passent toujours car le comportement est cohérent.

**Override CLI inchangé** :
```bash
python demo_rhpro_parse.py doc.docx --gate-profile stage
```

## 📝 Références

- Code : [src/rhpro/normalizer.py](../src/rhpro/normalizer.py) - Méthode `_choose_gate_profile()`
- Tests : [tests/test_production_gate_profiles.py](../tests/test_production_gate_profiles.py)
- Démo : [demo_production_gate.py](../demo_production_gate.py)
