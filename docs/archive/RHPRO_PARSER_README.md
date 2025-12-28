# RH-Pro DOCX Parser

Pipeline déterministe pour parser les bilans d'orientation RH-Pro (DOCX) et les normaliser selon un schéma canonique défini par ruleset YAML.

## 📋 Objectif

Transformer des documents Word RH-Pro (souvent désorganisés) en un dictionnaire JSON normalisé, sans inventer de contenu, en suivant un ruleset configurable.

## 🏗️ Architecture

```
src/rhpro/
├── ruleset_loader.py     # Charge et valide le YAML
├── docx_structure.py     # Extrait paragraphes + métadonnées
├── segmenter.py          # Détecte titres et construit segments
├── mapper.py             # Mappe titres → sections canoniques
├── normalizer.py         # Construit le dict normalisé final
└── parse_bilan.py        # Point d'entrée principal
```

## 🚀 Installation

```bash
# Installer les dépendances
pip install -r requirements.txt

# Vérifier l'installation
python -c "import yaml, docx; print('✓ OK')"
```

## 📖 Usage

### En Python

```python
from src.rhpro.parse_bilan import parse_bilan_from_paths

result = parse_bilan_from_paths('bilan.docx')

# Récupérer le dict normalisé
normalized = result['normalized']
print(normalized['identity'])
print(normalized['profession_formation'])

# Récupérer le rapport de parsing
report = result['report']
print(f"Couverture: {report['coverage_ratio'] * 100}%")
print(f"Sections manquantes: {report['missing_required_sections']}")
```

### Avec le script de démo

```bash
python demo_rhpro_parse.py path/to/bilan.docx
```

Génère un fichier `bilan_normalized.json` avec le résultat.

## 📄 Structure du ruleset

Le ruleset (`config/rulesets/rhpro_v1.yaml`) définit :

1. **Normalisation des titres** : trim, collapse whitespace, etc.
2. **Détection des titres** : par style Word, regex, ou heuristiques
3. **Stratégie de mapping** : exact → contains → regex → fuzzy
4. **Sections canoniques** : structure hiérarchique avec anchors
5. **Règles de contenu** : anti-hallucination (never_invent_for)

## 🔍 Détection des titres

Ordre de priorité :

1. **by_style** : Utilise les styles Word (Heading 1, TITRE 2, etc.)
2. **by_regex** : Patterns regex (numérotation, majuscules)
3. **by_heuristics** : Court + gras

## 🎯 Mapping des titres

Méthodes appliquées dans l'ordre :

1. **exact** : Correspondance exacte (case-insensitive)
2. **contains** : Substring match
3. **regex** : Pattern matching
4. **fuzzy** : Similarité de chaînes (seuil configurable)

## 📊 Format de sortie

Le résultat contient deux clés :

### `normalized`

Dict suivant le schéma `schemas/normalized.rhpro_v1.json` :

```json
{
  "identity": {
    "name": "",
    "surname": "",
    "avs": ""
  },
  "profession_formation": {
    "profession": "...",
    "formation": "..."
  },
  "tests": { ... },
  "conclusion": "..."
}
```

### `report`

Métadonnées du parsing :

```json
{
  "found_sections": [
    {"section_id": "identity", "title": "Identité", "confidence": 1.0}
  ],
  "missing_required_sections": ["orientation_formation.orientation"],
  "unknown_titles": ["Titre non reconnu"],
  "coverage_ratio": 0.85,
  "warnings": ["Required section missing: ..."]
}
```

## 🧪 Tests

```bash
# Lancer les tests
pytest tests/test_rhpro_parse.py -v

# Ou avec coverage
pytest tests/test_rhpro_parse.py --cov=src.rhpro --cov-report=html
```

## 🔒 Règles anti-hallucination

- Les champs avec `fill_strategy: source_only` restent vides si non trouvés
- Pas de résumé automatique en v1 (optionnel pour v2)
- Sections listées dans `content_rules.never_invent_for` ne sont jamais générées

## 📝 Prochaines étapes (v2)

- [ ] Extraction de l'identité depuis header/tableau Word
- [ ] Résumés automatiques via LLM (optionnel)
- [ ] Support des bullets imbriqués (Points d'appui / vigilance)
- [ ] API REST endpoint `/parse-bilan` (FastAPI)
- [ ] Worker RQ pour parsing asynchrone

## 📚 Exemples de sections supportées

- Identité (AVS, nom, prénom)
- Profession & Formation
- Tests (Evolution, Ressources, Profil emploi, Vocation)
- Discussion avec l'assuré
- Compétences (Sociales, Professionnelles)
- Incertitudes & Obstacles
- Orientation & Formation (Orientation, Stage)
- Dossier & Présentation (CV, Lettre motivation, Entretien)
- Conclusion

## 🐛 Debugging

Pour debug un parsing :

```python
from src.rhpro.parse_bilan import parse_bilan_from_paths
import json

result = parse_bilan_from_paths('problematic.docx')

# Voir les segments détectés
with open('debug_report.json', 'w') as f:
    json.dump(result['report'], f, indent=2, ensure_ascii=False)
```

## 📞 Support

Pour toute question sur le pipeline RH-Pro, consultez `docs/instructions_Steap2.md`.
