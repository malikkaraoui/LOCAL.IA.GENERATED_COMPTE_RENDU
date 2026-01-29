# Diagnostic GOLD Missing — PRIORITÉ 5

## Objectif

Investiguer pourquoi certains clients n'ont pas de GOLD détecté, sans modifier l'algorithme de détection existant.

**But final** : Comprendre rapidement si les 9 cas "GOLD missing" sont :
- Hors-scope (ancien template)
- Filtrés par naming
- Ou rejetés par heuristique (ancres/score)

Pour ensuite décider un correctif ciblé (Priorité suivante), sans casser le reste.

---

## Fichiers Créés

### 1. `src/rhpro/gold_diagnostics.py` (368 lignes)

Module de diagnostic avec les fonctions principales :

- **`diagnose_gold_missing(client_folder, gold_result)`** : Collecte les diagnostics pour un client
  - Liste tous les fichiers DOCX candidats
  - Calcule le score GOLD de chaque fichier
  - Identifie les raisons de rejet
  - Extrait 3 snippets de texte par fichier

- **`extract_text_snippets(file_path, max_snippets=3)`** : Extraction légère de snippets
  - DOCX : premiers paragraphes non-vides
  - TXT/MD : premières lignes non-vides
  - PDF : placeholder (évite extraction lourde)

- **`analyze_candidate_rejection(file_path, score)`** : Analyse des raisons de rejet
  - Extension non supportée
  - Patterns d'exclusion (brouillon, copie, temp, etc.)
  - Mots-clés GOLD manquants
  - Score en dessous du seuil
  - Fichier vide ou trop petit

- **`write_diagnostics_jsonl(diagnostics, output_path)`** : Écriture JSONL (machine-readable)
- **`write_diagnostics_summary(diagnostics, output_path)`** : Écriture Markdown (human-readable)

### 2. `src/rhpro/dataset_training.py` (modifié)

Intégration dans le pipeline d'analyse :

- Import du module `gold_diagnostics`
- Collecteur `gold_missing_diagnostics = []` dans la boucle d'analyse
- Appel `diagnose_gold_missing()` pour chaque client sans GOLD
- Écriture automatique des fichiers JSONL et Markdown en fin d'analyse
- Ajout de champs dans `DatasetTrainingResult` :
  - `gold_missing_diagnostics_path` : chemin du fichier JSONL
  - `gold_missing_count` : nombre de clients sans GOLD

### 3. `tests/test_gold_diagnostics.py` (270 lignes)

**8 tests** couvrant :
- Émission de diagnostic pour clients sans GOLD
- Pas de diagnostic inutile pour clients avec GOLD
- Extraction de snippets depuis DOCX
- Analyse des raisons de rejet
- Écriture JSONL et Markdown
- Structure complète du diagnostic
- Tri des candidats par score

**Résultat** : 8/8 tests ✅

### 4. `demo_gold_diagnostics.py` (script d'exemple)

Script pour lancer l'analyse avec diagnostic :

```bash
python demo_gold_diagnostics.py /path/to/CLIENTS_FOLDER
```

---

## Format de Sortie

### Fichier JSONL : `output/training/gold_missing_debug.jsonl`

Un objet JSON par client, exemple :

```json
{
  "client_id": "CLIENT_XX",
  "client_path": "/path/to/CLIENT_XX",
  "gold_detected": false,
  "timestamp": "2025-12-29T...",
  "candidates": [
    {
      "path": "rapport/notes_diverses.docx",
      "absolute_path": "/path/to/CLIENT_XX/rapport/notes_diverses.docx",
      "type": ".docx",
      "size_bytes": 12345,
      "is_ignored": false,
      "gold_score": 0.15,
      "gold_pass": false,
      "reject_reasons": [
        "no_high_priority_keywords",
        "below_threshold:0.15<0.5"
      ],
      "snippets": [
        "EXTRAIT 1: Notes de réunion du 12/03...",
        "EXTRAIT 2: Synthèse partielle...",
        "EXTRAIT 3: ..."
      ]
    },
    {
      "path": "bilan_intermediaire.docx",
      "gold_score": 0.42,
      "gold_pass": false,
      "reject_reasons": ["below_threshold:0.42<0.5"],
      "snippets": ["BILAN INTERMÉDIAIRE..."]
    }
  ],
  "notes": [
    "2_docx_files_scanned",
    "max_score_below_threshold:0.42"
  ]
}
```

### Fichier Markdown : `output/training/gold_missing_debug.md`

Résumé lisible avec :
- Nombre de clients analysés
- Détails par client :
  - Liste des candidats avec score/pass/raisons
  - Détails du meilleur candidat
  - Snippets extraits

---

## Usage

### 1. Lancer l'analyse training avec diagnostic

```python
from src.rhpro.dataset_training import analyze_dataset

result = analyze_dataset(
    root_dir="/path/to/CLIENTS",
    out_dir="output/training",
    limit=None,  # Analyser tous les clients
    index_msg=False,  # Exclure .msg pour performance
)

# Afficher résultats
print(f"GOLD missing: {result.gold_missing_count}")
print(f"Diagnostics: {result.gold_missing_diagnostics_path}")
```

### 2. Script de démo rapide

```bash
python demo_gold_diagnostics.py /path/to/CLIENTS_FOLDER
```

Output :
```
📊 Statistiques:
   - Total clients: 50
   - GOLD détectés: 41
   - GOLD missing: 9

🔍 Fichiers de diagnostic créés:
   - JSONL: output/training/gold_missing_debug.jsonl
   - Markdown: output/training/gold_missing_debug.md
```

### 3. Analyser les diagnostics

**Lire le Markdown** (human-readable) :

```bash
cat output/training/gold_missing_debug.md
```

**Parser le JSONL** (machine-readable) :

```bash
# Compter par raison de rejet
cat output/training/gold_missing_debug.jsonl | \
  jq -r '.candidates[].reject_reasons[]' | \
  sort | uniq -c | sort -rn

# Top 5 clients avec le meilleur score
cat output/training/gold_missing_debug.jsonl | \
  jq -r '[.client_id, .candidates[0].gold_score] | @tsv' | \
  sort -k2 -rn | head -5
```

---

## Informations Collectées

### Par Client (si gold_detected == False)

1. **Liste des fichiers candidats**
   - Chemins relatifs et absolus
   - Extension
   - Taille en bytes
   - Si ignoré par filtres

2. **Score + raison du rejet** (par candidat)
   - `gold_score` : score calculé (0.0 à 1.0)
   - `gold_pass` : si score >= 0.5 (seuil de décision)
   - `reject_reasons` : liste des raisons
     - `unsupported_extension:<ext>`
     - `excluded_pattern:<pattern>`
     - `no_gold_keywords_found`
     - `no_high_priority_keywords`
     - `below_threshold:<score><0.5`
     - `empty_file`
     - `too_small:<bytes>bytes`

3. **3 premiers snippets** (150 chars chacun)
   - Extraits du contenu du fichier
   - Permet de voir rapidement le type de contenu
   - Évite l'extraction lourde (OCR, etc.)

4. **Notes de diagnostic**
   - `no_docx_files_found`
   - `X_docx_files_scanned`
   - `all_files_ignored_by_filters`
   - `all_scores_very_low`
   - `max_score_below_threshold:<score>`

---

## Tests

**Lancer les tests** :

```bash
# Tests diagnostic GOLD uniquement
pytest tests/test_gold_diagnostics.py -v

# Tests combinés (priorités 3, 4, 5)
pytest tests/test_gold_diagnostics.py \
       tests/test_meta_headers.py \
       tests/test_sources_count_exclusion.py -v
```

**Résultats** :
- 8 tests diagnostic GOLD : ✅
- 20 tests combinés (3 priorités) : ✅
- 53 tests non-régression : ✅

---

## Contraintes Respectées

✅ **Pas de modification de l'algorithme GOLD** : Le scoring et la détection restent inchangés

✅ **Diagnostic peu coûteux** :
- Pas d'OCR
- Pas d'embeddings
- Extraction légère de snippets (premiers paragraphes uniquement)
- Exécuté uniquement si `gold_detected == False`

✅ **Logs lisibles et exploitables** :
- Format JSONL pour parsing automatique
- Format Markdown pour lecture humaine
- Un bloc par client
- Tri des candidats par score décroissant

✅ **Normalisation existante respectée** :
- Utilise `score_gold_candidate()` existant
- Utilise `GOLD_KEYWORDS_*` et `GOLD_EXCLUDE_PATTERNS` existants
- Aucun "fix" introduit, seulement observation

---

## Prochaines Étapes

Après analyse des diagnostics :

1. **Identifier les patterns récurrents** :
   - Noms de fichiers non détectés → ajouter keywords
   - Ancien template → documenter hors-scope
   - Score limite (0.4-0.5) → ajuster seuil ou keywords

2. **Décider des correctifs ciblés** (Priorité 6+) :
   - Ajouter keywords GOLD si patterns clairs
   - Exclure certains patterns si bruit détecté
   - Ajuster seuil si trop de faux négatifs

3. **Non-régression** :
   - Toujours valider avec tests existants
   - Documenter les changements
   - Mesurer l'impact sur gold_detection_rate

---

## Modification Summary

**Fichiers créés** :
- `src/rhpro/gold_diagnostics.py` (368 lignes)
- `tests/test_gold_diagnostics.py` (270 lignes)
- `demo_gold_diagnostics.py` (65 lignes)
- `GOLD_DIAGNOSTICS_README.md` (ce fichier)

**Fichiers modifiés** :
- `src/rhpro/dataset_training.py` :
  - Import `gold_diagnostics`
  - Collecteur `gold_missing_diagnostics`
  - Appel diagnostic dans boucle d'analyse
  - Écriture JSONL/MD en fin d'analyse
  - Ajout champs `gold_missing_diagnostics_path` et `gold_missing_count`

**Tests** : 8 nouveaux tests, tous ✅

**Non-régression** : 53 tests existants, tous ✅
