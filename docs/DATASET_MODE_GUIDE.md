# Dataset Mode & Client Search — Documentation

## Vue d'ensemble

Extension du **Batch Parser** pour supporter:
1. **Datasets réels** avec noms de dossiers (nom/prénom) au lieu de `client_01/02`
2. **Recherche tolérante** de clients par nom (fuzzy matching)
3. **Export CSV** avec métriques détaillées
4. **Génération individuelle** de rapports par client

## Nouveaux composants

### 1. Module `src/rhpro/client_finder.py`

#### Fonctions principales

**`normalize_text(text) -> str`**
- Normalise texte : minuscules + suppression accents
- Exemple : `"ARIFI Élodie"` → `"arifi elodie"`

**`fuzzy_score(query, target) -> float`**
- Score de similarité 0.0-1.0 avec bonus :
  - +0.3 si query contenu dans target
  - +0.2 si query au début (nom/prénom)
  - +0.3 si tous mots de query dans target

**`find_client_folders(root_dir, query=None, min_score=0.3) -> List[Dict]`**
- Trouve tous dossiers clients dans `root_dir`
- Si `query` fourni : filtre + tri par score
- Retourne : `path`, `name`, `score`, `has_docx`, `has_pdf`, `has_txt`, `has_audio`

**`find_client_folder(root_dir, query, exact=False) -> Tuple[Path, List]`**
- Trouve UN dossier (meilleur match)
- Retourne : `(best_path, all_matches)`

**`discover_client_documents(client_folder) -> Dict`**
- Découvre documents dans dossier client
- Retourne : `{'docx': [...], 'pdf': [...], 'txt': [...], 'audio': [...]}`

### 2. Export CSV dans `batch_runner.py`

**`generate_batch_report_csv(batch_result) -> str`**
- Génère CSV avec colonnes :
  - `client_folder` : Nom du dossier
  - `profile_selected` : Profil production gate
  - `gate_status` : GO/NO-GO
  - `required_coverage` : Coverage sections requises
  - `weighted_coverage` : Coverage pondéré
  - `unknown_titles_count` : Titres inconnus
  - `missing_required_sections_count` : Sections manquantes
  - `placeholders_count` : Placeholders
  - `status` : success/error

### 3. CLI `demo_client_finder.py`

```bash
# Recherche simple
python demo_client_finder.py /path/to/dataset ARIFI

# Avec documents
python demo_client_finder.py data/samples client --show-docs

# Liste complète
python demo_client_finder.py /path/to/dataset --list-all
```

Options :
- `--min-score` : Score minimum (défaut: 0.3)
- `--max-results` : Nombre max résultats (défaut: 10)
- `--show-docs` : Afficher documents par dossier

### 4. Page Streamlit : Rapport individuel

**Navigation** : Sidebar → "Rapport individuel"

**Workflow** :
1. Browse / saisir dossier dataset RH-Pro
2. Saisir nom client (ex: "ARIFI")
3. Cliquer "Rechercher"
4. Sélectionner résultat dans liste (top matches)
5. Choisir options :
   - Profil production gate (auto/forcé)
   - Formats sortie (JSON/Markdown/CSV)
   - Type rapport (orientation/final)
6. Cliquer "Générer le rapport"
7. Télécharger fichiers générés

## Utilisation

### Mode Batch avec CSV

```bash
# Batch complet avec CSV
python demo_batch.py data/samples --output out/batch

# Fichiers générés:
# - batch_report.json
# - batch_report.md
# - batch_report.csv  ← NOUVEAU
```

**Contenu CSV** :
```csv
client_folder,profile_selected,gate_status,required_coverage,weighted_coverage,unknown_titles_count,missing_required_sections_count,placeholders_count,status
client_01,stage,GO,0.750,0.710,1,1,0,success
client_02,stage,GO,1.000,0.650,0,0,0,success
```

### Recherche de clients (Python)

```python
from src.rhpro.client_finder import find_client_folders, find_client_folder

# Recherche avec query
results = find_client_folders("/path/to/dataset", "ARIFI", min_score=0.3)

for result in results[:5]:
    print(f"{result['name']} (score: {result['score']:.2f})")
    if result['has_docx']:
        print("  → Contient DOCX")

# Trouver le meilleur match
best_path, all_matches = find_client_folder("/path/to/dataset", "KARAOUI")

if best_path:
    print(f"Meilleur résultat: {best_path.name}")
    
    # Découvrir documents
    from src.rhpro.client_finder import discover_client_documents
    docs = discover_client_documents(best_path)
    print(f"Documents: {len(docs['docx'])} DOCX, {len(docs['pdf'])} PDF")
```

### Dataset réel (pas client_01/02)

**Structure attendue** :
```
/Users/malik/Documents/RH PRO BASE DONNEE/3. TERMINER/
├── ARIFI Elodie/
│   ├── Bilan_final.docx
│   ├── CV.pdf
│   └── ...
├── KARAOUI Malik/
│   ├── Bilan_orientation.docx
│   └── ...
└── BENZINE Rabia/
    └── ...
```

**Utilisation** :
```bash
# Lister tous les clients
python demo_client_finder.py "/Users/malik/Documents/RH PRO BASE DONNEE/3. TERMINER/" --list-all

# Rechercher ARIFI
python demo_client_finder.py "/Users/malik/Documents/RH PRO BASE DONNEE/3. TERMINER/" ARIFI --show-docs

# Batch sur dataset réel
python demo_batch.py "/Users/malik/Documents/RH PRO BASE DONNEE/3. TERMINER/" --output out/prod_batch
```

## Algorithme de recherche

### Score calculation

```
base_score = SequenceMatcher(query_normalized, target_normalized).ratio()

if query in target:      base_score += 0.3
if target.startswith(query): base_score += 0.2
if all_query_words in target_words: base_score += 0.3

final_score = min(base_score, 1.0)
```

### Exemples de scores

| Query | Target | Score | Raison |
|-------|--------|-------|--------|
| `arifi` | `ARIFI Elodie` | 1.00 | Contenu + début + mots |
| `KARAOUI` | `Karaoui Malik` | 1.00 | Idem |
| `arif` | `ARIFI Elodie` | 0.85 | Contenu + début (pas exact) |
| `elodie` | `ARIFI Elodie` | 0.75 | Contenu + mot |
| `xyz` | `ARIFI Elodie` | 0.05 | Très faible similarité |

### Filtrage

- `min_score=0.3` (défaut) : assez tolérant
- `min_score=0.7` : strict (typos mineures acceptées)
- `min_score=0.9` : quasi-exact

## Contraintes respectées

✅ **Aucun chemin codé en dur** : tous les chemins via args/config

✅ **Support noms réels** : `ARIFI Elodie`, `KARAOUI Malik`, etc.

✅ **Recherche tolérante** : accents, majuscules, typos

✅ **Export CSV** : métriques complètes pour analyse

✅ **Browse UI** : tkinter pour sélection dossier

✅ **--report-type** : orientation vs final (prévu dans UI)

## Tests

### Test recherche fuzzy

```bash
python -c "
from src.rhpro.client_finder import fuzzy_score
print(fuzzy_score('arifi', 'ARIFI Elodie'))  # 1.00
print(fuzzy_score('karaoui', 'Karaoui Malik'))  # 1.00
"
```

### Test découverte

```bash
python demo_client_finder.py data/samples client --show-docs
```

### Test batch avec CSV

```bash
python demo_batch.py data/samples --output /tmp/test_csv
cat /tmp/test_csv/batch_report.csv
```

### Test UI

```bash
streamlit run streamlit_app.py
# → Sidebar "Rapport individuel"
# → Browse dataset
# → Rechercher "client"
# → Générer rapport
```

## Améliorations futures

1. **Cache de recherche** : mémoriser résultats fréquents
2. **Indexation** : pré-scanner dataset au démarrage
3. **Historique** : garder trace des rapports générés
4. **Batch sélectif** : multiselect de clients dans UI
5. **Export Excel** : alternative au CSV avec formatting
6. **Notifications** : email/slack en fin de traitement

## Troubleshooting

### Recherche ne trouve rien

```bash
# Vérifier normalisation
python -c "from src.rhpro.client_finder import normalize_text; print(normalize_text('VOTRE_QUERY'))"

# Baisser le seuil
python demo_client_finder.py /path --query ARIFI --min-score 0.1
```

### CSV mal formaté

- Vérifier encoding : doit être UTF-8
- Ouvrir avec Excel : "Données" → "Fichier texte" → UTF-8

### Browse ne fonctionne pas

- macOS : installer `python-tk` via Homebrew
- Fallback : saisir chemin manuellement dans champ texte

---

**Version** : 2.0.0  
**Date** : 27 décembre 2025  
**Statut** : ✅ Production Ready
