# Artifacts - Artefacts de Training

Ce dossier contient les artefacts générés automatiquement à chaque run training pour faciliter l'analyse et l'évolution du ruleset.

## Fichiers Générés

### `unknown_titles_YYYYMMDD_HHMMSS.csv`

**Format** :
```csv
title_raw,title_norm,count,suggested_action,suggested_target,notes
```

**Colonnes** :
- `title_raw` : Titre original (non normalisé, pour lisibilité)
- `title_norm` : Titre normalisé (clé unique, sans accents/ponctuation)
- `count` : Nombre d'occurrences dans le dataset
- `suggested_action` : Action suggérée (`MAP_TO_SECTION` | `MAP_TO_TESTS` | `SUBHEADING_POLICY` | `IGNORE`)
- `suggested_target` : Section cible suggérée (ex: `formation`, `tests`, `À déterminer`)
- `notes` : Commentaires/contexte (ex: "Keywords tests détectés", "Fréquence élevée")

**Utilisation** :
1. Trier par `count` décroissant → prioriser titres fréquents
2. Filtrer `suggested_action != IGNORE` → éliminer one-shots
3. Analyser `suggested_target` → décider mapping ou améliorer subheading policy

**Exemple** :
```csv
title_raw,title_norm,count,suggested_action,suggested_target,notes
"DATE : 15/01/2025","DATE 15 01 2025",5,SUBHEADING_POLICY,"","Pattern subheading détecté, améliorer règles (count=5)"
"EVALUATIONS FRANCAIS","EVALUATIONS FRANCAIS",12,MAP_TO_TESTS,tests,"Keywords tests détectés (count=12)"
"OBJECTIFS PERSONNELS","OBJECTIFS PERSONNELS",2,MAP_TO_SECTION,"À déterminer","Fréquence moyenne (count=2), évaluer au cas par cas"
```

## Workflow Scalable

### Après chaque run training :

1. **Ouvrir le CSV** (Excel, Google Sheets, Python pandas)
2. **Trier par `count`** (décroissant)
3. **Filtrer `suggested_action`** :
   - `MAP_TO_SECTION` (count ≥ 2) → Ajouter mapping dans `SEED_SECTION_TITLE_MAP`
   - `MAP_TO_TESTS` → Ajouter mapping vers section `tests`
   - `SUBHEADING_POLICY` → Améliorer règles `is_subheading()` si pattern récurrent
   - `IGNORE` (count = 1) → Ne rien faire sauf cas critique

4. **Documenter** dans `docs/ruleset/CHANGELOG_RULESET.md`
5. **Tester** (ajouter tests unitaires)
6. **Commit + Push**

### Avantages :

- ✅ **Zéro parsing manuel** de `training_report.md`
- ✅ **Priorisation automatique** (fréquence + keywords)
- ✅ **Scalable** : fonctionne sur 10 dossiers comme sur 1000
- ✅ **Traçabilité** : CSV versionné = snapshot état ruleset

## Règles de Gestion

**Ne jamais mapper** un titre `count=1` sauf :
- Contient données PII (déjà filtré automatiquement)
- Correspond à section canonique critique manquante

**Prioriser** les titres `count ≥ 3` pour mappings.

**Améliorer subheading policy** si patterns récurrents (ex: nouvelles variantes de questions, emojis, etc.).

---

**Note** : Ce dossier est gitignored (fichiers CSV volumineux et générés automatiquement). Seul le dernier snapshot est conservé localement pour analyse.
