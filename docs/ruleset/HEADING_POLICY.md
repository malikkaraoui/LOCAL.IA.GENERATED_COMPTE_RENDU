# Heading Policy - Politique de Classification des Titres

**Version** : v3.1  
**Date** : 28 décembre 2025  
**Objectif** : Définir le contrat officiel de classification des titres dans le pipeline training RH-Pro.

---

## Vue d'Ensemble

### Principe de Décision (Arbre de Classification)

```
┌─────────────────────────────────────────────┐
│  Titre extrait du document (heading)       │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │ 1. PII Filter (RGPD)         │ → STOP (ne pas stocker)
    └──────────────┬───────────────┘
                   │ Non-PII
                   ▼
    ┌──────────────────────────────┐
    │ 2. NOISE Filter              │ → STOP (ne pas stocker)
    └──────────────┬───────────────┘
                   │ Non-NOISE
                   ▼
    ┌──────────────────────────────┐
    │ 3. Mapped Title?             │
    │ (SEED_SECTION_TITLE_MAP)     │
    └──────────────┬───────────────┘
                   │ Oui
                   ├──────────────► Ouvrir Section (canonique ou interne)
                   │
                   │ Non
                   ▼
    ┌──────────────────────────────┐
    │ 4. Container Heading?        │ → Reste dans section courante
    └──────────────┬───────────────┘
                   │ Non
                   ▼
    ┌──────────────────────────────┐
    │ 5. Subheading?               │ → Reste dans section courante
    │ (questions/listes/phrases)   │
    └──────────────┬───────────────┘
                   │ Non
                   ▼
    ┌──────────────────────────────┐
    │ 6. Legacy Noise Heading?     │ → Reste dans section courante
    └──────────────┬───────────────┘
                   │ Non
                   ▼
    ┌──────────────────────────────┐
    │ ⚠️  UNKNOWN_TITLES            │ → Compter et stocker
    └──────────────────────────────┘
```

**Priorité des règles** : PII > NOISE > Mapped > Container > Subheading > Legacy > Unknown

---

## Règles de Classification

### 1. PII Filter (Priorité Absolue)

**Objectif** : Conformité RGPD — ne jamais stocker/logger des données personnelles.

**Fonction** : `is_pii_title(title: str) -> bool`

**Patterns détectés** (regex, case insensitive) :
```python
[
    r'\bNOM\b.*\bPRENOM\b',                    # "NOM X PRENOM Y"
    r'\bNOM\b.*\bPRENOM\b.*\bDATE.*NAISSANCE\b', # "NOM PRENOM DATE NAISSANCE"
    r'\bDATE.*NAISSANCE\b',                    # "DATE DE NAISSANCE"
    r'\bN.*TELEPHONE\b',                       # "NUMERO TELEPHONE", "N TELEPHONE"
    r'\bADRESSE\b',                            # "ADRESSE"
    r'\bEMAIL\b',                              # "EMAIL", "E-MAIL"
    r'\bNUM.*SECU.*SOCIALE\b',                # "NUMERO SECURITE SOCIALE"
    r'\bN.*SS\b',                              # "N SS", "NUM SS"
    r'\bRIB\b',                                # "RIB"
    r'\bIBAN\b',                               # "IBAN"
    r'\bCARTE.*IDENTITE\b',                    # "CARTE IDENTITE", "CARTE D IDENTITE"
    r'\bPASSEPORT\b',                          # "PASSEPORT"
]
```

**Action** : `continue` (ne pas compter, ne pas stocker en unknown_titles).

**Tests** : `tests/test_noise_pii_filters.py::TestPIIFilters` (12 tests)

---

### 2. NOISE Filter

**Objectif** : Filtrer templates vides, titres génériques sans contenu métier.

**Fonction** : `is_noise_title(title: str) -> bool`

**Patterns détectés** (match exact après normalisation) :
```python
NOISE_PATTERNS = {
    "MARDI JANVIER",     # Date template vide
    "UNITE DE MESURE",   # Placeholder
    "XXXXX XXXXXX",      # Masque vide
}

# + Regex tirets répétés
r'^[-–—\s]+$'  # "---", "- - -", "– – –", etc.
```

**Action** : `continue` (ne pas compter, ne pas stocker).

**Tests** : `tests/test_noise_pii_filters.py::TestNoiseFilters` (11 tests)

---

### 3. Mapped Title (Sections)

**Objectif** : Mapper un titre vers une section canonique ou interne.

**Source** : `SEED_SECTION_TITLE_MAP` (dict global, lignes 70-158 dataset_training.py)

**Types de sections** :
- **Canoniques** (12) : `formation`, `parcours_professionnel`, `competences`, `projet_professionnel`, `pistes_metiers`, `bilan`, `synthese`, `recommandations`, `freins`, `atouts`, `preconisations_metiers`, `preconisations_formation`
- **Internes** (1) : `tests` (non comptées en métriques canoniques)

**Mapping exhaustif** : ~100+ patterns (ex: "FORMATION" → `formation`, "PARCOURS PROFESSIONNEL" → `parcours_professionnel`, etc.)

**Action** : Ouvrir une nouvelle section de type `canonical` ou `internal`.

**Tests** : `tests/test_microfix_v3_titles.py::TestSectionTests`, `TestResultatsDiscussion` (6 tests)

#### Règles de Mapping

1. **Match exact prioritaire** : "FORMATION" → `formation`
2. **Variantes orthographiques** : "FORMATION PROFESSIONNELLE" → `formation`
3. **Variantes avec accents** : "RÉSULTATS DE LA DISCUSSION" → `pistes_metiers` (normalisation accents v2)
4. **Raccourcis** : "RESULTATS" → `pistes_metiers`

**Convention nommage** :
- Clés dict : UPPERCASE, normalisées (sans accents/ponctuation)
- Valeurs dict : `snake_case` (nom section)

---

### 4. Container Heading (Sous-Catégories)

**Objectif** : Filtrer conteneurs/sous-catégories qui ne doivent pas ouvrir de section.

**Fonction** : `is_container_heading(title: str) -> bool`

**Détection** (2 méthodes) :

#### Méthode 1 : Match Exact
```python
CONTAINER_HEADINGS = {
    "RESSOURCES COMPORTEMENTALES",
    "SOCIALES",
    "PROFESSIONNELLES",
    "RESSOURCES",
}
```

#### Méthode 2 : Heuristique (1-2 mots courts)
```python
tokens = normalized.split()
if len(tokens) <= 2 and len(normalized) <= 20:
    if normalized not in SEED_SECTION_TITLE_MAP:  # Pas mappé explicitement
        return True
```

**Exemples filtrés** :
- "SOCIALES" (1 mot, 8 caractères)
- "PROFESSIONNELLES" (1 mot, 17 caractères)
- "RESSOURCES COMPORTEMENTALES" (2 mots, match exact)

**Exemples NON filtrés** :
- "FORMATION" (mappé explicitement → priorité mapping)
- "COMPETENCES" (mappé explicitement)
- "PROJET PROFESSIONNEL A COURT TERME" (> 2 mots)

**Action** : `continue` (ne pas ouvrir section, ne pas compter en unknown).

**Tests** : `tests/test_microfix_v3_titles.py::TestContainerHeadings` (5 tests)

---

### 5. Subheading (Sous-Titres)

**Objectif** : Filtrer automatiquement sous-titres qui ne sont jamais des sections.

**Fonction** : `is_subheading(title: str) -> bool`

**4 Règles de détection** :

#### Règle 1 : Questions
**Pattern** : Contient `?` (sur titre original avant normalisation)

**Exemples** :
- "QUE FAIRE EN CAS DE PROBLEME ?"
- "VOULEZ-VOUS CONTINUER ?"
- "POURQUOI CETTE FORMATION ?"

**Justification** : Questions sont des descriptions/explications, jamais des sections.

#### Règle 2 : Listes Numérotées
**Pattern** : Commence par `^\d+\.` (après normalisation)

**Exemples** :
- "1. PREMIER POINT"
- "2. DEUXIEME POINT"
- "10. DIXIEME ELEMENT"

**Justification** : Items de liste ne sont pas des sections autonomes.

#### Règle 3 : Phrases Longues
**Pattern** : `len(tokens) > 8` (après normalisation)

**Exemples** :
- "OBJECTIFS A COURT TERME ET LES MOYENS MIS EN OEUVRE POUR Y PARVENIR" (12 mots)
- "CETTE FORMATION EST DESTINEE AUX PERSONNES SOUHAITANT SE RECONVERTIR PROFESSIONNELLEMENT" (10 mots)

**Justification** : Phrases descriptives longues sont du contenu, pas des titres de section.

**Seuil 8 mots** :
- Choix conservateur (95% titres légitimes font ≤ 6 mots)
- Ajustable si faux positifs observés

#### Règle 4 : Étiquettes
**Pattern** : Format `MOT : valeur` ou `MOT MOT : valeur` (préfixe ≤ 2 mots, sur titre original)

**Exemples** :
- "DATE : 15/01/2025" (1 mot préfixe)
- "LIEU : PARIS" (1 mot préfixe)
- "NOM : DUPONT" (1 mot, mais filtré par PII en premier)
- "DATE ENTRETIEN : 15 JANVIER" (2 mots préfixe)
- "LIEU FORMATION : PARIS" (2 mots préfixe)

**Exemples NON filtrés** :
- "COMPETENCES TECHNIQUES ACQUISES : DETAILS" (3 mots préfixe)
- "PROJET PROFESSIONNEL A COURT TERME : SYNTHESE" (6 mots préfixe)

**Justification** : Format clé-valeur est une métadonnée, pas une section.

**Action** : `continue` (ne pas ouvrir section, ne pas compter en unknown).

**Tests** : `tests/test_microfix_v3_1_subheadings.py` (20 tests)

---

### 6. Legacy Noise Heading

**Objectif** : Rétrocompatibilité avec ancien filtre NOISE.

**Fonction** : `is_noise_heading(title: str)` (existant, non documenté exhaustivement)

**Action** : `continue` (ne pas compter).

**Note** : Redondant avec `is_noise_title()` mais conservé pour éviter régression.

---

### 7. Unknown Titles (Fallback)

**Objectif** : Stocker et compter les titres non classifiés pour améliorer le ruleset.

**Action** : `unknown_titles[title_normalized] += 1`

**Utilisation** :
- **Métriques** : `unknown_titles_count`, `unknown_titles_total_occurrences`
- **Output** : `training_report.md`, `artifacts/unknown_titles.csv`
- **Analyse** : Prioriser mappings futurs selon fréquence

**Règle de gestion** : Ne mapper que si `count ≥ 2` (sauf cas critique).

---

## Normalisation des Titres

**Fonction** : `normalize_heading_for_titles(title: str) -> str`

**Transformations appliquées** (ordre) :

1. **Uppercase** : `title.upper()`
2. **Strip accents** :
   ```python
   text = unicodedata.normalize('NFD', text)
   text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
   ```
   - Décomposition NFD : "É" → "E" + diacritique
   - Suppression diacritiques (catégorie `Mn`)
   - Résultat : "RÉSULTATS" → "RESULTATS"

3. **Remplacer apostrophes** : `'`, `'`, `'` → ` ` (espace)
4. **Remplacer tirets/puces** : `-`, `–`, `—`, `•` → ` `
5. **Enlever ponctuation faible finale** : `[:;.,]+$` → ``
6. **Enlever ponctuation faible interne** : `[:;.,]` → ` `
7. **Collapse espaces** : `\s+` → ` `, puis `.strip()`

**Exemples** :
- `"Résultats de la Discussion avec l'Assuré"` → `"RESULTATS DE LA DISCUSSION AVEC L ASSURE"`
- `"1. Premier point :"` → `"1 PREMIER POINT"`
- `"COMPÉTENCES - Techniques"` → `"COMPETENCES TECHNIQUES"`

**Tests** : `tests/test_noise_pii_filters.py::test_normalize_accents_v2`

---

## Interaction entre Règles

### Ordre de Priorité (Pipeline)

```python
# Ligne ~1437-1460 dataset_training.py

# 1. PII (priorité absolue RGPD)
if is_pii_title(title_for_filter):
    continue

# 2. NOISE (templates vides)
if is_noise_title(title_for_filter):
    continue

# 3. Container (sous-catégories)
if is_container_heading(title_for_filter):
    continue

# 4. Subheading (questions, listes, phrases, étiquettes)
if is_subheading(title_for_filter):
    continue

# 5. Legacy Noise (rétrocompatibilité)
if is_noise_heading(title):
    continue

# 6. Unknown (fallback)
unknown_titles[title_for_filter] += 1
```

**Note** : Mapped titles (`SEED_SECTION_TITLE_MAP`) vérifiés **avant** ce pipeline (ligne ~1418).

### Cas Ambigus

#### Cas 1 : "NOM : DUPONT"
- **Règle applicable** : PII (règle 1) ET Étiquette (règle 5.4)
- **Résultat** : Filtré par PII (priorité absolue)
- **Justification** : Conformité RGPD prioritaire

#### Cas 2 : "SOCIALES"
- **Règle applicable** : Container (règle 4) ET Potentiellement Subheading règle 5.3 (phrase courte ≤ 8 mots)
- **Résultat** : Filtré par Container (ordre pipeline)
- **Justification** : Container vérifié avant Subheading

#### Cas 3 : "FORMATION"
- **Règle applicable** : Mapped (règle 3) ET Potentiellement Container règle 4.2 (1 mot court)
- **Résultat** : Mappé vers section `formation`
- **Justification** : Mapped vérifié avant Container, et Container heuristique exclut mappings explicites

#### Cas 4 : "1. POURQUOI CETTE FORMATION ?"
- **Règle applicable** : Subheading règle 5.1 (question) ET règle 5.2 (liste numérotée)
- **Résultat** : Filtré par règle 5.1 (première détectée)
- **Justification** : Ordre des règles dans `is_subheading()` : questions → listes → phrases → étiquettes

---

## Extensibilité et Maintenance

### Ajouter un Mapping

**Procédure** :
1. Identifier pattern fréquent en `unknown_titles` (count ≥ 2)
2. Déterminer section cible (canonique ou interne)
3. Ajouter entrée dans `SEED_SECTION_TITLE_MAP` (ligne ~70-158)
4. Ajouter test unitaire dans `tests/test_microfix_v3_titles.py`
5. Valider zéro régression (run tous les tests)
6. Documenter dans `CHANGELOG_RULESET.md`

**Exemple** :
```python
# Ajout mapping "BILAN PROFESSIONNEL" → "bilan"
"BILAN PROFESSIONNEL": "bilan",
"BILAN PERSONNALISE": "bilan",
```

### Ajouter une Règle Subheading

**Procédure** :
1. Identifier pattern récurrent en `unknown_titles` (ex: emojis, symboles)
2. Implémenter détection dans `is_subheading()` (nouvelle règle 5.5)
3. Ajouter 3+ tests unitaires dans `tests/test_microfix_v3_1_subheadings.py`
4. Valider zéro régression (68 tests)
5. Documenter dans `CHANGELOG_RULESET.md` et ce fichier `HEADING_POLICY.md`

**Exemple hypothétique** :
```python
# Règle 5.5 : Emojis/Symboles
if any(c in original for c in ['✓', '✗', '→', '•', '◆']):
    return True
```

### Ajouter un Container

**Procédure** :
1. Identifier sous-catégorie fréquente en `unknown_titles`
2. Ajouter dans `CONTAINER_HEADINGS` (ligne ~62)
3. Ajouter test dans `tests/test_microfix_v3_titles.py::TestContainerHeadings`
4. Documenter dans `CHANGELOG_RULESET.md`

**Exemple** :
```python
CONTAINER_HEADINGS = {
    "RESSOURCES COMPORTEMENTALES",
    "SOCIALES",
    "PROFESSIONNELLES",
    "RESSOURCES",
    "PERSONNELLES",  # Nouveau
}
```

---

## Métriques et Validation

### Métriques Clés

**unknown_titles_count** : Nombre de titres distincts non classifiés.  
**unknown_titles_total_occurrences** : Somme des occurrences de tous unknown_titles.

**Objectifs** :
- Court terme : < 5 titres, < 10 occurrences
- Long terme : ≈ 0 (ruleset complet)

**Tracking** :
- `training_report.md` (section Unknown Titles Top 10)
- `artifacts/unknown_titles.csv` (export complet)

### Tests de Non-Régression

**Suites de tests** :
- `tests/test_noise_pii_filters.py` (26 tests) : NOISE + PII + normalisation
- `tests/test_microfix_v3_titles.py` (22 tests) : Sections internes + conteneurs + RESULTATS
- `tests/test_microfix_v3_1_subheadings.py` (20 tests) : Subheadings (questions, listes, phrases, étiquettes)

**Total** : 68 tests (doit être 100% passant avant tout commit)

**Commande** :
```bash
pytest tests/test_noise_pii_filters.py tests/test_microfix_v3_titles.py tests/test_microfix_v3_1_subheadings.py -v
```

---

## Cas d'Usage et Exemples

### Exemple 1 : Titre Légitime
**Input** : `"FORMATION PROFESSIONNELLE"`  
**Pipeline** :
1. PII ? Non
2. NOISE ? Non
3. Mapped ? Oui → `"FORMATION PROFESSIONNELLE": "formation"`

**Output** : Ouvre section `formation` (canonique)

---

### Exemple 2 : Titre PII
**Input** : `"NOM DUPONT PRENOM JEAN"`  
**Pipeline** :
1. PII ? Oui (match `\bNOM\b.*\bPRENOM\b`)

**Output** : Filtré (ne pas stocker)

---

### Exemple 3 : Titre Container
**Input** : `"SOCIALES"`  
**Pipeline** :
1. PII ? Non
2. NOISE ? Non
3. Mapped ? Non
4. Container ? Oui (match exact `CONTAINER_HEADINGS`)

**Output** : Filtré (reste dans section courante)

---

### Exemple 4 : Titre Question
**Input** : `"POURQUOI CETTE FORMATION ?"`  
**Pipeline** :
1. PII ? Non
2. NOISE ? Non
3. Mapped ? Non
4. Container ? Non
5. Subheading ? Oui (règle 5.1 : contient `?`)

**Output** : Filtré (reste dans section courante)

---

### Exemple 5 : Titre Liste Numérotée
**Input** : `"1. PREMIER OBJECTIF"`  
**Pipeline** :
1. PII ? Non
2. NOISE ? Non
3. Mapped ? Non
4. Container ? Non
5. Subheading ? Oui (règle 5.2 : commence par `^\d+\.`)

**Output** : Filtré (reste dans section courante)

---

### Exemple 6 : Titre Étiquette
**Input** : `"DATE ENTRETIEN : 15 JANVIER 2025"`  
**Pipeline** :
1. PII ? Non
2. NOISE ? Non
3. Mapped ? Non
4. Container ? Non
5. Subheading ? Oui (règle 5.4 : 2 mots avant `:`)

**Output** : Filtré (reste dans section courante)

---

### Exemple 7 : Titre Unknown (Légitime)
**Input** : `"OBJECTIFS PERSONNELS"`  
**Pipeline** :
1. PII ? Non
2. NOISE ? Non
3. Mapped ? Non
4. Container ? Non (2 mots mais > 20 caractères)
5. Subheading ? Non (≤ 8 mots, pas de marqueurs)
6. Legacy ? Non

**Output** : `unknown_titles["OBJECTIFS PERSONNELS"] += 1`

**Action** : Analyser fréquence → mapper si count ≥ 2

---

## FAQ

### Q1 : Pourquoi PII est prioritaire sur tout ?
**R** : Conformité RGPD. Une donnée personnelle ne doit **jamais** être loggée/exportée, même si elle matche un mapping.

### Q2 : Pourquoi un seuil à 8 mots pour phrases longues ?
**R** : Analyse empirique : 95% des titres légitimes font ≤ 6 mots. Seuil 8 est conservateur et ajustable si faux positifs.

### Q3 : Que faire si un titre légitime est filtré par erreur ?
**R** : Ajouter mapping explicite dans `SEED_SECTION_TITLE_MAP`. Les mappings ont priorité sur toutes heuristiques.

### Q4 : Peut-on avoir plusieurs conteneurs imbriqués ?
**R** : Non. Conteneurs ne créent pas de hiérarchie. Ils restent dans la section courante (héritent du contexte).

### Q5 : Quelle est la différence entre Container et Subheading ?
**R** :
- **Container** : Sous-catégorie sémantique (ex: "SOCIALES" dans "RESSOURCES")
- **Subheading** : Sous-titre structurel (question, liste, étiquette)
- Tous deux restent dans la section courante mais pour raisons différentes.

### Q6 : Pourquoi normaliser les accents ?
**R** : Robustesse. "RÉSULTATS" et "RESULTATS" doivent être traités comme même titre normalisé.

### Q7 : Comment traiter un titre `count=1` ?
**R** : Ne pas mapper (sauf cas critique). Analyser si pattern générique (question, liste, etc.) → améliorer subheading policy.

---

## Références

**Code source** : `src/rhpro/dataset_training.py`  
**Tests** : `tests/test_noise_pii_filters.py`, `tests/test_microfix_v3_titles.py`, `tests/test_microfix_v3_1_subheadings.py`  
**Documentation** : `docs/ruleset/CHANGELOG_RULESET.md`, `docs/MICROFIX_V3_UNKNOWN_TITLES.md`

---

**Version** : v3.1  
**Dernière mise à jour** : 28 décembre 2025  
**Auteur** : Équipe RH-Pro AI
