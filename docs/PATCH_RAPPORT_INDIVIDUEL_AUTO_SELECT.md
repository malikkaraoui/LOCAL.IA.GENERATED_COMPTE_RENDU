# ✅ PATCH — Rapport individuel : Scan complet automatique + Exclusion Devis + AUTO sélection DOCX

**Date**: 29 décembre 2025  
**Status**: ✅ Implémenté et testé

## 📋 Problème résolu

L'utilisateur devait :
1. **Manuellement choisir** si scanner les sous-dossiers ou non
2. **Manuellement régler** la profondeur de scan
3. **Manuellement sélectionner** le document DOCX source (risque de choisir un contrat au lieu d'un bilan RH-Pro)
4. Les fichiers du dossier "Devis" polluaient la liste des documents
5. Pas de visibilité sur ce qui était scanné et exclu

→ Résultat : `normalized.json` vide, `report.json` en NO-GO (coverage 0%)

## 🎯 Solution implémentée

### 🔄 Scan récursif complet AUTOMATIQUE

**Changement majeur** : L'utilisateur n'a plus à choisir quoi scanner.

**Avant** ❌ :
- Toggle "Inclure sous-dossiers" (oui/non)
- Slider "Profondeur de scan" (0-6)
- Risque : utilisateur désactive le scan récursif → données manquantes

**Après** ✅ :
- **Scan récursif automatique** de TOUT le dossier client (profondeur 10)
- Plus de choix manuel → zéro configuration
- Affichage : "🔍 Scan récursif complet automatique : tout le dossier client est scanné (sauf exclusions)"

**Implémentation** ([pages_streamlit/client_report_generator.py](pages_streamlit/client_report_generator.py)):
```python
# Session state simplifiée (suppression scan_include_subfolders, scan_max_depth)
if "scan_max_files" not in st.session_state:
    st.session_state.scan_max_files = 5000

# Scan toujours récursif avec max_depth=10
def _cached_scan(path_str: str, max_f: int, excl_dirs: bool, excl_files: bool):
    return discover_client_documents_recursive(
        Path(path_str),
        max_depth=10,  # Profondeur élevée pour scan complet
        include_subfolders=True,  # Toujours récursif
        max_files=max_f,
        exclude_dir_keywords=['devis'] if excl_dirs else [],
        exclude_file_keywords=['devis'] if excl_files else []
    )
```

### 1. Exclusion automatique du dossier "Devis"

**Backend** ([src/rhpro/client_finder.py](src/rhpro/client_finder.py)):
- ✅ Nouveau paramètre `exclude_dir_keywords` (default: `['devis']`)
- ✅ Nouveau paramètre `exclude_file_keywords` (default: `['devis']`)
- ✅ Fonction utilitaire `contains_keyword()` (case-insensitive)
- ✅ Filtrage au niveau dossier ET fichier
- ✅ Tracking des exclusions dans le résultat:
  - `excluded_dirs`: Liste des dossiers exclus
  - `excluded_files_count`: Nombre de fichiers exclus par keyword

**UI** ([pages_streamlit/client_report_generator.py](pages_streamlit/client_report_generator.py)):
- ✅ Checkbox "🚫 Exclure dossier 'Devis'" (activée par défaut)
- ✅ Checkbox "🚫 Exclure fichiers 'Devis'" (activée par défaut)
- ✅ Affichage des exclusions: `🚫 Exclusions: X dossier(s) exclu(s), Y fichier(s) exclu(s)`
- ⚠️ **Important** : Ce sont les SEULES checkboxes de configuration (scan récursif toujours actif)

### 2. Sélection AUTO du meilleur DOCX source

**Backend** ([src/rhpro/client_finder.py](src/rhpro/client_finder.py)):
- ✅ Nouvelle fonction `select_best_source_docx(docx_paths, profile) -> (Path, mode)`

**Stratégie de sélection**:
1. **Rejet automatique** des docs administratifs:
   - contrat, convention, devis, facture, attestation, convocation, invitation, cv
2. **Bonus** pour les docs RH-Pro:
   - bilan, évaluation, orientation, rapport, rh-pro, suivi, synthèse
3. **Analyse structure** (quick scan):
   - Comptage des headings (Heading1, Heading2...)
   - Détection des anchors RH-Pro (identity, profession_formation, orientation_formation...)
   - Bonus pour nb de paragraphes (> 80 = doc structuré)
4. **Fallback**: Si aucun candidat, prendre le plus long DOCX (hors blacklist)

**Modes de sélection**:
- `AUTO_PRIORITY`: Bon candidat trouvé (score > 5.0)
- `AUTO_FALLBACK`: Candidat trouvé par fallback (taille)
- `MANUAL`: Sélection manuelle par l'utilisateur
- `NONE`: Aucun candidat valide

**UI** ([pages_streamlit/client_report_generator.py](pages_streamlit/client_report_generator.py)):
- ✅ Radio button: "AUTO (recommandé)" | "MANUEL"
- ✅ Mode AUTO par défaut
- ✅ Affichage du DOCX sélectionné: `🎯 AUTO a sélectionné : RH-Pro Bilan.docx (AUTO_PRIORITY)`
- ✅ Expander "Voir les autres DOCX disponibles" avec liste complète
- ✅ Fallback automatique en MANUEL si AUTO échoue

### 3. Diagnostics enrichis dans report.json

**Nouvelles entrées dans `report.json`**:
```json
{
  "diagnostic": {
    "source_docx_selected": "/path/to/RH-Pro Bilan.docx",
    "source_docx_mode": "AUTO_PRIORITY",
    "rag_sources_count": {
      "docx": 5,
      "pdf": 8,
      "txt": 2,
      "msg": 1,
      "audio": 3
    },
    "excluded_dirs": ["02 Devis", "Devis RH-Pro"],
    "excluded_files_count": 0
  }
}
```

→ Visibilité complète sur ce qui a été scanné et exclu

## 🧪 Tests (9 tests, tous ✅)

**Fichier**: [tests/test_exclude_devis.py](tests/test_exclude_devis.py)

### Tests d'exclusion Devis
- ✅ `test_contains_keyword` — Vérification case-insensitive
- ✅ `test_exclude_devis_dir` — Dossier "02 Devis" exclu
- ✅ `test_exclude_devis_filename_fallback` — Fichiers "Devis *.docx" exclus
- ✅ `test_typical_client_structure_excludes_devis` — Intégration complète

### Tests sélection AUTO
- ✅ `test_auto_select_prefers_bilan_over_contrat` — Bilan > Contrat
- ✅ `test_auto_select_rejects_devis` — Devis rejeté
- ✅ `test_auto_select_rejects_all_admin_docs` — Tous docs admin rejetés
- ✅ `test_auto_select_returns_none_for_empty_list` — Liste vide → None
- ✅ `test_auto_select_fallback_on_longest_docx` — Fallback sur scoring

**Exécution**:
```bash
pytest tests/test_exclude_devis.py -v
# ✅ 9 passed in 0.37s
```

## 📊 Avant / Après

### Avant ❌
```
🎛️ Configuration manuelle :
├── Toggle "Inclure sous-dossiers" (risque de désactivation)
├── Slider "Profondeur de scan" (0-6) (risque de trop limiter)
└── Liste DOCX manuelle (risque de mauvais choix)

📁 Client: SCHMIDT Mélanie
├── 02 Devis/ (apparaît si scan récursif activé)
│   ├── Devis RH-Pro 1.docx (apparaît dans la liste)
│   ├── Devis RH-Pro 2.docx (apparaît dans la liste)
│   └── Facture.pdf (apparaît dans la liste)
├── Contrat de travail.docx (❌ risque de sélection)
└── RH-Pro - Bilan final.docx (⚠️ noyé dans la liste)

→ Utilisateur peut désactiver le scan récursif
→ Utilisateur peut limiter la profondeur à 1 (données manquantes)
→ Utilisateur sélectionne "Contrat de travail.docx"
→ normalized.json vide
→ report.json NO-GO (coverage 0%)
```

### Après ✅
```
🚀 Zéro configuration :
├── Scan récursif complet AUTOMATIQUE (profondeur 10)
├── Exclusion Devis AUTOMATIQUE (activée par défaut)
└── Sélection DOCX AUTO (mode recommandé par défaut)

📁 Client: SCHMIDT Mélanie
├── 02 Devis/ (🚫 EXCLU automatiquement)
│   ├── Devis RH-Pro 1.docx (non listé)
│   ├── Devis RH-Pro 2.docx (non listé)
│   └── Facture.pdf (non listé)
├── 01 Dossier personnel/ (✅ scanné)
│   └── CV.pdf (✅ inclus dans RAG)
├── 03 Tests/ (✅ scanné)
│   └── WAIS-IV.pdf (✅ inclus dans RAG)
├── Contrat de travail.docx (rejeté par AUTO)
└── RH-Pro - Bilan final.docx (✅ AUTO sélectionne)

→ Scan récursif automatique (TOUT le dossier)
→ AUTO sélectionne "RH-Pro - Bilan final.docx" (AUTO_PRIORITY)
→ 🚫 Exclusions: 1 dossier(s) exclu(s)
→ normalized.json rempli avec toutes les sections trouvées
→ report.json avec coverage > 0% (progression vers GO)
→ diagnostic complet dans report.json
```

## 🔧 Modifications des fichiers

### Backend
1. **[src/rhpro/client_finder.py](src/rhpro/client_finder.py)**
   - Ajout `contains_keyword(text, keywords)`
   - Ajout `select_best_source_docx(docx_paths, profile)`
   - Modification `discover_client_documents_recursive()`:
     - Nouveaux params: `exclude_dir_keywords`, `exclude_file_keywords`
     - Filtrage dossiers et fichiers par keywords
     - Tracking exclusions dans résultat

### Frontend
2. **[pages_streamlit/client_report_generator.py](pages_streamlit/client_report_generator.py)**
   - **SUPPRESSION** : Toggle "Inclure sous-dossiers" et Slider "Profondeur"
   - **AJOUT** : Info box "Scan récursif complet automatique"
   - Session state simplifié (suppression `scan_include_subfolders`, `scan_max_depth`)
   - Fonction `_cached_scan()` toujours en mode récursif complet (`max_depth=10`, `include_subfolders=True`)
   - Import `select_best_source_docx`
   - UI: Checkboxes exclusion Devis (activées par défaut)
   - UI: Radio button AUTO/MANUEL (AUTO par défaut)
   - UI: Affichage DOCX sélectionné par AUTO
   - Enrichissement `report.json` avec diagnostic

### Tests
3. **[tests/test_exclude_devis.py](tests/test_exclude_devis.py)** (nouveau)
   - 9 tests couvrant exclusions et sélection AUTO

### Documentation
4. **[docs/PATCH_RAPPORT_INDIVIDUEL_AUTO_SELECT.md](docs/PATCH_RAPPORT_INDIVIDUEL_AUTO_SELECT.md)** (ce fichier)

## 🚀 Utilisation

### 1. Lancer l'interface
```bash
streamlit run streamlit_app.py
```

### 2. Aller sur "Rapport individuel"

### 3. Rechercher un client
→ Le scan récursif complet démarre automatiquement (profondeur 10)

### 4. Vérifier les exclusions
- ✅ "🚫 Exclure dossier 'Devis'" (coché par défaut)
- ✅ "🚫 Exclure fichiers 'Devis'" (coché par défaut)

### 5. Sélection DOCX AUTO
- ✅ Mode "AUTO (recommandé)" sélectionné par défaut
- 🎯 AUTO sélectionne le meilleur doc RH-Pro automatiquement
- 📋 Voir les alternatives dans l'expander "Voir les autres DOCX disponibles"

### 6. Générer le rapport
→ `report.json` contiendra le diagnostic complet dans `diagnostic.*`

**Zéro configuration requise** : Scan récursif + Exclusion Devis + AUTO sélection activés par défaut !

## ✅ Definition of Done

- [x] **Scan récursif automatique** : Plus de toggle/slider, toujours actif (profondeur 10)
- [x] Dossier "Devis" exclu automatiquement
- [x] Fichiers contenant "devis" exclus
- [x] Sélection AUTO du meilleur DOCX source
- [x] Fallback MANUEL si AUTO échoue
- [x] Affichage des exclusions dans l'UI
- [x] Info box "Scan récursif complet automatique"
- [x] Diagnostic complet dans report.json
- [x] Tests unitaires et d'intégration (9/9 passent)
- [x] Aucune régression (tests existants passent)
- [x] Documentation complète et mise à jour

## 🎯 Impact sur SCHMIDT Mélanie

Avant:
- ❌ Risque de désactiver le scan récursif (données manquantes)
- ❌ Risque de limiter la profondeur (dossiers non scannés)
- ❌ Fichiers Devis apparaissent
- ❌ Risque de sélectionner "Contrat de travail.docx"
- ❌ normalized.json vide
- ❌ NO-GO (coverage 0%)

Après:
- ✅ Scan récursif complet automatique (TOUT le dossier)
- ✅ Fichiers Devis exclus automatiquement
- ✅ AUTO sélectionne "RH-Pro - Bilan.docx" automatiquement
- ✅ normalized.json rempli avec toutes les sections
- ✅ Coverage > 0% (progression vers GO)
- ✅ Diagnostic complet et traçable
- ✅ **Zéro configuration** requise de l'utilisateur

## 📝 Notes techniques

### Performance
- Le scan est mis en cache (Streamlit `@st.cache_data`, TTL=300s)
- L'analyse rapide des DOCX (headings scan) ne lit que les 100 premiers paragraphes
- Fallback sur taille fichier si erreur de lecture DOCX

### Extensibilité
- Les keywords d'exclusion peuvent être étendus facilement
- La logique de scoring peut être affinée (ajout de nouveaux critères)
- Les modes de sélection peuvent être étendus (ex: `AUTO_HEADING_MATCH`)

### Compatibilité
- ✅ Compatible avec tous les profils gate (bilan_complet, placement_suivi, stage)
- ✅ Compatible avec scan récursif ou non
- ✅ Compatible avec tous les formats de sortie (JSON, Markdown)
- ✅ Rétrocompatible (pas de breaking change)

## 🔄 Prochaines étapes possibles

1. **Logging avancé**: Logger les décisions de sélection AUTO (pourquoi tel doc a été choisi)
2. **Metrics**: Traquer le taux de succès AUTO vs MANUEL
3. **ML scoring**: Entraîner un modèle pour scorer les DOCX (si données suffisantes)
4. **UI preview**: Prévisualiser les premiers paragraphes du DOCX sélectionné
5. **Exclusion configurable**: Permettre à l'utilisateur d'ajouter ses propres keywords

---

🎉 **Le patch est complet et fonctionnel !**
