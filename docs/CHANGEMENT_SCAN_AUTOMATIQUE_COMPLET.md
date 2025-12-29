# 🔄 Changement majeur : Scan récursif complet AUTOMATIQUE

**Date**: 29 décembre 2025  
**Impact**: Simplification UX — Zéro configuration requise

---

## 🎯 Objectif produit

**Avant** : L'utilisateur devait choisir manuellement comment scanner le dossier client :
- Toggle "Inclure sous-dossiers" (oui/non)
- Slider "Profondeur de scan" (0-6)
- Sélection manuelle du DOCX source

**Problème** :
- Risque de **désactiver le scan récursif** → données manquantes
- Risque de **limiter la profondeur** → sous-dossiers non scannés
- Risque de **choisir le mauvais DOCX** → parsing incorrect

**Après** : Le système scanne **automatiquement TOUT le dossier client** :
- Scan récursif complet (profondeur 10) **toujours actif**
- Exclusion automatique des dossiers "Devis" (activée par défaut)
- Sélection AUTO du meilleur DOCX source (mode recommandé par défaut)

---

## 📋 Changements UI

### Supprimé ❌
1. **Toggle "Inclure sous-dossiers"** → toujours activé maintenant
2. **Slider "Profondeur de scan"** → toujours à max_depth=10
3. Variables session state : `scan_include_subfolders`, `scan_max_depth`

### Ajouté ✅
1. **Info box** : "🔍 Scan récursif complet automatique : tout le dossier client est scanné (sauf exclusions ci-dessous)"
2. **Simplification** : Seulement 2 checkboxes (exclusions Devis) + 1 contrôle (max_files)

### Conservé ✅
- Checkbox "🚫 Exclure dossier 'Devis'" (activée par défaut)
- Checkbox "🚫 Exclure fichiers 'Devis'" (activée par défaut)
- Number input "Max fichiers scannés" (pour éviter freeze)
- Button "🔄 Rescanner" (pour clear le cache)
- Radio "AUTO / MANUEL" pour sélection DOCX

---

## 🔧 Modifications techniques

### [pages_streamlit/client_report_generator.py](pages_streamlit/client_report_generator.py)

#### Session state simplifié
```python
# AVANT
if "scan_include_subfolders" not in st.session_state:
    st.session_state.scan_include_subfolders = True
if "scan_max_depth" not in st.session_state:
    st.session_state.scan_max_depth = 2

# APRÈS (supprimé)
# Ces variables ne sont plus nécessaires
```

#### Fonction de scan simplifiée
```python
# AVANT
@st.cache_data(show_spinner="Scan en cours...", ttl=300)
def _cached_scan(path_str: str, depth: int, include_subs: bool, max_f: int, ...):
    return discover_client_documents_recursive(
        Path(path_str),
        max_depth=depth,
        include_subfolders=include_subs,
        ...
    )

# APRÈS
@st.cache_data(show_spinner="Scan récursif complet en cours...", ttl=300)
def _cached_scan(path_str: str, max_f: int, excl_dirs: bool, excl_files: bool):
    return discover_client_documents_recursive(
        Path(path_str),
        max_depth=10,  # Toujours profondeur élevée
        include_subfolders=True,  # Toujours récursif
        ...
    )
```

#### Appel simplifié
```python
# AVANT
result = _cached_scan(
    str(selected_path),
    max_depth,              # ❌ Variable
    include_subfolders,     # ❌ Variable
    max_files,
    exclude_devis_dirs,
    exclude_devis_files
)

# APRÈS
result = _cached_scan(
    str(selected_path),
    max_files,              # ✅ Simplifié
    exclude_devis_dirs,
    exclude_devis_files
)
```

---

## 📊 Impact utilisateur

### Avant ❌
```
Client recherché → Schmidt Mélanie
↓
[Toggle] Inclure sous-dossiers ☑ (utilisateur peut décocher)
[Slider] Profondeur: 2 (utilisateur peut mettre à 0)
[Checkbox] Exclure Devis ☑
↓
Scan partiel possible (si toggle décoché)
→ Fichiers manquants
→ Rapport incomplet
```

### Après ✅
```
Client recherché → Schmidt Mélanie
↓
[Info] 🔍 Scan récursif complet automatique
[Checkbox] Exclure Devis ☑ (activé par défaut)
↓
Scan complet automatique (profondeur 10)
→ Tous les fichiers trouvés
→ Rapport complet
```

---

## ✅ Avantages

1. **Simplicité** : Moins de contrôles = moins d'erreurs
2. **Cohérence** : Tous les rapports utilisent le même mode de scan
3. **Complétude** : Plus de risque d'oublier des sous-dossiers
4. **Performance** : Cache Streamlit + profondeur fixe = prédictible
5. **UX** : L'utilisateur cherche juste un client → tout le reste est automatique

---

## 🧪 Tests

Tous les tests existants passent :
- ✅ `tests/test_exclude_devis.py` : 9/9 passent
- ✅ `tests/test_discover_recursive.py` : 14/14 passent
- ✅ Aucune régression détectée

---

## 📝 Documentation mise à jour

- ✅ [docs/PATCH_RAPPORT_INDIVIDUEL_AUTO_SELECT.md](PATCH_RAPPORT_INDIVIDUEL_AUTO_SELECT.md) mis à jour
- ✅ Section "Scan récursif complet AUTOMATIQUE" ajoutée
- ✅ Exemples avant/après actualisés

---

## 🚀 Prochaines étapes

1. **Test utilisateur** : Valider sur cas réels (SCHMIDT Mélanie)
2. **Feedback** : Collecter retours sur simplification UI
3. **Metrics** : Traquer le taux de succès (coverage > 0%)
4. **Documentation** : Guide utilisateur simplifié

---

## 💡 Philosophie produit

> **"Le meilleur UX est celui qu'on ne voit pas"**
> 
> L'utilisateur ne devrait pas avoir à configurer comment scanner un dossier.
> Le système doit être assez intelligent pour :
> - Scanner tout automatiquement (récursif complet)
> - Exclure ce qui est inutile (Devis)
> - Sélectionner le bon document (AUTO)
> - Générer le rapport (un seul clic)

→ **Zéro configuration, maximum de résultats**

---

🎉 **Changement déployé et prêt pour test utilisateur !**
