# Batch Parser RH-Pro — Documentation

## Vue d'ensemble

Le **Batch Parser** permet de parser et valider automatiquement plusieurs dossiers clients RH-Pro en une seule opération, avec génération de rapports agrégés.

## Architecture

### Composants créés

1. **`src/rhpro/batch_runner.py`** : Module principal
   - `discover_sources(root_dir)` : Découverte récursive des dossiers contenant `source.docx`
   - `run_batch()` : Exécution pipeline sur N dossiers + agrégation résultats
   - `generate_batch_report_markdown()` : Génération rapport lisible

2. **`demo_batch.py`** : Interface CLI
   - Découverte et liste des dossiers
   - Parsing batch avec profil auto/forcé
   - Génération rapports JSON/MD
   - Affichage résumé formaté

3. **`pages_streamlit/batch_parser.py`** : Interface UI
   - Browse dossier racine (tkinter)
   - Multiselect dossiers à parser
   - Tableau résultats interactif
   - Téléchargement rapports

4. **`tests/test_batch_samples.py`** : Tests d'intégration
   - 11 tests couvrant découverte, parsing, rapports
   - Validation golden samples (client_01, client_02)

## Utilisation

### CLI

```bash
# Lister les dossiers découverts
python demo_batch.py data/samples --list-only

# Parser tous les dossiers
python demo_batch.py data/samples --output out/batch

# Forcer un profil spécifique
python demo_batch.py data/samples --output out/batch --profile stage

# Écrire source_normalized.json dans chaque dossier
python demo_batch.py data/samples --write-in-source

# Aide complète
python demo_batch.py --help
```

### UI Streamlit

1. Lancer Streamlit :
   ```bash
   streamlit run streamlit_app.py
   ```

2. Navigation :
   - Sidebar → "Batch Parser RH-Pro"

3. Workflow :
   - Saisir/browse dossier racine
   - Cliquer "Découvrir les dossiers"
   - Sélectionner dossiers à parser (multiselect)
   - Optionnel : forcer profil production gate
   - Cliquer "Lancer le batch"
   - Consulter tableau résultats
   - Télécharger rapports JSON/MD

### Python API

```python
from src.rhpro.batch_runner import discover_sources, run_batch

# Découverte
folders = discover_sources("data/samples")
print(f"Trouvé {len(folders)} dossiers")

# Batch
result = run_batch(
    root_dir="data/samples",
    ruleset_path="config/rulesets/rhpro_v1.yaml",
    output_dir="out/batch",
    gate_profile_override=None  # ou "stage", "bilan_complet", "placement_suivi"
)

# Résumé
summary = result["summary"]
print(f"GO: {summary['gate_go']}, NO-GO: {summary['gate_no_go']}")
```

## Structure des rapports

### Rapport JSON (`batch_report.json`)

```json
{
  "timestamp": "2025-12-27T13:30:12.340758",
  "root_dir": "data/samples",
  "ruleset_path": "config/rulesets/rhpro_v1.yaml",
  "discovered_count": 2,
  "gate_profile_override": null,
  "results": [
    {
      "client_dir": "/path/to/client_01",
      "client_name": "client_01",
      "status": "success",
      "profile": "stage",
      "gate_status": "GO",
      "required_coverage_ratio": 0.75,
      "missing_required_sections": ["identity"],
      "unknown_titles_count": 1,
      "placeholders_count": 0,
      "reasons": [],
      "warnings": [...],
      "signals": {...},
      "criteria": {...}
    }
  ],
  "summary": {
    "total_processed": 2,
    "successful": 2,
    "errors": 0,
    "gate_go": 2,
    "gate_no_go": 0,
    "avg_coverage": 0.875
  }
}
```

### Rapport Markdown (`batch_report.md`)

- **Header** : timestamp, root_dir, ruleset
- **Summary** : métriques agrégées
- **Detailed Results** : section par client avec :
  - Profil détecté
  - Gate status (GO/NO-GO)
  - Coverage
  - Sections manquantes
  - Titres inconnus
  - Raisons du statut
- **Errors** : liste des erreurs si présentes

## Fichiers générés

```
output_dir/
├── batch_report.json      # Rapport machine-readable
├── batch_report.md         # Rapport humain-lisible
├── client_01/
│   ├── normalized.json     # Données normalisées
│   └── report.json         # Rapport détaillé
└── client_02/
    ├── normalized.json
    └── report.json
```

Option `--write-in-source` :
```
data/samples/client_01/
├── source.docx
└── source_normalized.json  # ← Généré
```

## Tests

```bash
# Tous les tests batch
pytest tests/test_batch_samples.py -v

# Test découverte uniquement
pytest tests/test_batch_samples.py::TestDiscoverSources -v

# Test avec coverage
pytest tests/test_batch_samples.py --cov=src.rhpro.batch_runner
```

### Tests inclus

1. **Découverte** :
   - Trouve au moins 2 dossiers clients
   - Gère dossier vide
   - Lève erreur si dossier inexistant

2. **Batch runner** :
   - Parse tous les samples sans exception
   - Golden samples (client_01/02) → GO expected
   - Tous clients → profil valide + status valide
   - Override profil fonctionne
   - Écriture source_normalized.json

3. **Rapports** :
   - JSON structuré correctement
   - Markdown lisible

## Contraintes respectées

✅ **Pas de dépendances lourdes** : uniquement `python-docx`, `pyyaml`, `pandas` (déjà présents)

✅ **Scoring déterministe** : basé sur titres normalisés et headings

✅ **root_dir paramétrable** : discovery automatique, chemins relatifs dans tests

✅ **Existant fonctionnel** : `demo_rhpro_parse.py` reste opérationnel

✅ **Backward compatible** : API parse_bilan_docx_to_normalized() inchangée

## Performance

- **Séquentiel** : parse les dossiers un par un (pas de parallélisation)
- **Temps moyen** : ~1-2s par dossier (selon taille DOCX)
- **Mémoire** : linéaire avec nombre de dossiers

Pour datasets > 50 dossiers, envisager :
- Parallélisation via multiprocessing
- Streaming des résultats
- Pagination UI

## Améliorations futures

1. **Parallélisation** : `concurrent.futures.ProcessPoolExecutor`
2. **Filtrage avancé** : par date, profil, gate status
3. **Export Excel** : tableau résultats en XLSX
4. **Comparaison** : diff entre runs successifs
5. **Notifications** : email/slack en fin de batch
6. **API REST** : endpoint `/api/batch` pour déclencher via HTTP

## Troubleshooting

### Aucun dossier découvert

```bash
# Vérifier structure
ls -R data/samples/
# Chaque dossier client doit contenir source.docx
```

### Erreur parsing d'un client

- Consulter `batch_report.json` → `results[i].error_message`
- Tester le client individuellement :
  ```bash
  python demo_rhpro_parse.py data/samples/client_XX/source.docx
  ```

### Profil "unknown"

- Bug corrigé : utilisez clé `profile` (pas `profile_id`) dans production_gate
- Vérifier que `_choose_gate_profile()` retourne bien un tuple `(profile_id, signals)`

### Browse dialog ne marche pas

- tkinter non disponible → saisir chemin manuellement
- macOS : installer `python-tk` via Homebrew

## Support

Pour questions/bugs :
- Consulter `docs/PRODUCTION_GATE_SCORING_V2.md` (système de scoring)
- Lancer tests : `pytest tests/test_batch_samples.py -v`
- Vérifier logs : `demo_batch.py` affiche détails dans stdout

---

**Dernière mise à jour** : 27 décembre 2025  
**Version** : 1.0.0  
**Statut** : ✅ Production ready
