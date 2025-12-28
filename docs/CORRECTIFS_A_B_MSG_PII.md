# 🔧 Correctifs A & B - SCRIPT.IA

**Date** : 28 décembre 2025  
**Status** : ✅ IMPLÉMENTÉ & TESTÉ

---

## 🎯 Objectifs

Deux correctifs critiques pour améliorer la qualité du training et l'indexation RAG :

### Correctif A : Indexation .msg (Emails Outlook)
Support des fichiers .msg dans la pipeline RAG avec option ON/OFF pour contrôle utilisateur.

### Correctif B : Filtrage PII dans unknown_titles
Suppression complète des données nominatives (NOM/PRENOM/AVS/dates) des statistiques training_state.

---

## 📊 Correctif A : Indexation .msg dans RAG

### Problème
Les emails Outlook (.msg) contiennent souvent des informations pertinentes (candidatures, échanges RH) mais n'étaient pas indexés dans le RAG.

### Solution Implémentée

#### 1. Module d'extraction déjà existant
✅ **Fichier** : `core/extractors/msg_extractor.py` (déjà créé précédemment)
- `extract_msg_to_text(msg_path, output_dir)` → extrait subject, from, to, date, body
- Gestion pièces jointes (PDF/DOCX/DOC/TXT)
- Support installé : `extract-msg>=0.48.0`

#### 2. Modification `client_scanner.py`

**Fonction `find_rag_sources()`** :
```python
def find_rag_sources(client_folder: Path, index_msg: bool = False) -> List[Dict[str, Any]]:
    """
    Args:
        index_msg: Si True, inclure .msg dans rag_sources. Si False, les compter séparément.
    """
    extensions_to_index = DOCUMENT_EXTENSIONS if index_msg else DOCUMENT_EXTENSIONS - {".msg"}
    # ...
```

**Fonction `scan_client_folder()`** :
```python
def scan_client_folder(client_folder_path: str, index_msg: bool = False) -> Dict[str, Any]:
    """
    Args:
        index_msg: Si True, inclure .msg dans rag_sources. Si False, les compter dans warnings.
        
    Returns:
        - msg_files_count: Nombre de .msg détectés (si index_msg=False)
    """
    # Compter .msg non indexés si index_msg=False
    if not index_msg:
        all_msg = find_rag_sources(client_folder, index_msg=True)
        msg_files_count = sum(1 for s in all_msg if s["extension"] == ".msg")
    
    # Warning si .msg non indexés
    if not index_msg and msg_files_count > 0:
        warnings.append(f"EXT_NOT_INDEXED: {msg_files_count} fichier(s) .msg non indexés")
```

### Comportement

| Mode | index_msg | Résultat |
|------|-----------|----------|
| **OFF (défaut)** | `False` | .msg non indexés, warning `EXT_NOT_INDEXED` si présents |
| **ON** | `True` | .msg inclus dans `rag_sources`, indexés dans RAG |

### Tests Validés ✅

- ✅ `test_scan_with_index_msg_true` : .msg dans rag_sources
- ✅ `test_scan_with_index_msg_false` : .msg non inclus, warning présent
- ✅ `test_scan_default_index_msg` : comportement par défaut = OFF
- ✅ `test_scan_no_msg_files` : pas de warning si aucun .msg
- ✅ `test_extensions_count_with_index_msg` : comptage correct

### Usage

```python
from src.rhpro.client_scanner import scan_client_folder

# Mode OFF (défaut)
result = scan_client_folder("/path/to/client")
# → .msg non indexés, warning si présents

# Mode ON
result = scan_client_folder("/path/to/client", index_msg=True)
# → .msg indexés dans rag_sources
```

---

## 🔒 Correctif B : Suppression PII des unknown_titles

### Problème
Le fichier `training_state.json` contenait des titres nominatifs dans `unknown_titles_top` :
```json
{
  "unknown_titles_top": {
    "NOM AYNE PRENOM MICKAEL": 2,
    "756.1234.5678.90": 1,
    "DATE 15/03/1985": 1
  }
}
```

**Risque** : Violation RGPD, données nominatives exposées dans artefacts training.

### Solution Implémentée

#### 1. Nouvelle fonction `is_noise_heading()`

**Fichier** : `src/rhpro/dataset_training.py`

```python
def is_noise_heading(text: str) -> bool:
    """
    Détecte si un texte détecté comme heading contient des PII ou libellés de formulaire.
    Plus strict que is_noise_title.
    
    Returns:
        True si le texte contient des données nominatives
    """
    # 1. Patterns nominatifs : "NOM xxx PRENOM yyy"
    if re.search(r'\bNOM\s+\w+\s+PRENOM\s+\w+', text_normalized):
        return True
    
    # 2. AVS suisse : 756.xxxx.xxxx.xx
    if re.search(r'\b756[\s\.]?\d{4}[\s\.]?\d{4}[\s\.]?\d{2}\b', text):
        return True
    
    # 3. Dates : dd/mm/yyyy, dd.mm.yyyy
    if re.search(r'\b\d{1,2}[\/\.\s]\d{1,2}[\/\.\s]\d{2,4}\b', text):
        return True
    
    # 4. Trop de chiffres (>= 8 digits)
    if digit_count >= 8:
        return True
    
    # 5. Libellés formulaire (NOM, PRENOM, AVS, etc.)
    if text_normalized in form_labels:
        return True
    
    return False
```

#### 2. Intégration dans `extract_sections_from_docx()`

**Avant extraction section** :
```python
is_heading = is_probable_heading(text, para_obj)

# ✅ CORRECTIF B: Ignorer si heading contient PII/formulaire
if is_heading and is_noise_heading(text):
    is_heading = False
```

#### 3. Filtrage dans comptage `unknown_titles`

```python
# Comptage unknown titles
if canonical is None and title:
    title_norm = normalize_title(title)
    # ✅ CORRECTIF B: Filtrer avec is_noise_heading (plus strict)
    if not is_noise_title(title_norm) and not is_noise_heading(title):
        unknown_titles[title_norm] += 1
```

### Patterns Filtrés

| Type | Exemples | Regex |
|------|----------|-------|
| **Nom+Prénom** | "NOM AYNE PRENOM MICKAEL" | `\bNOM\s+\w+\s+PRENOM\s+\w+` |
| **AVS** | "756.1234.5678.90" | `\b756[\s\.]?\d{4}[\s\.]?\d{4}[\s\.]?\d{2}\b` |
| **Dates** | "15/03/1985", "15.03.1985" | `\b\d{1,2}[\/\.\s]\d{1,2}[\/\.\s]\d{2,4}\b` |
| **Digits** | "12345678" | `digit_count >= 8` |
| **Labels** | "NOM", "PRENOM", "AVS", "DATE" | Whitelist exacte |

### Tests Validés ✅

- ✅ `test_is_noise_heading_nom_prenom_pattern` : Détecte "NOM xxx PRENOM yyy"
- ✅ `test_is_noise_heading_avs` : Détecte numéros AVS
- ✅ `test_is_noise_heading_dates` : Détecte dates
- ✅ `test_is_noise_heading_form_labels` : Détecte libellés formulaire
- ✅ `test_is_noise_heading_too_many_digits` : Détecte trop de chiffres
- ✅ `test_is_noise_heading_valid_titles` : Ne filtre PAS les titres valides

### Résultat

**Avant** (training_state.json) :
```json
"unknown_titles_top": {
  "NOM AYNE PRENOM MICKAEL": 2,
  "756.1234.5678.90": 1,
  "DATE 15/03/1985": 1,
  "EXPERIENCE PROFESSIONNELLE": 5
}
```

**Après** (training_state.json) :
```json
"unknown_titles_top": {
  "EXPERIENCE PROFESSIONNELLE": 5
}
```

✅ **Aucune donnée nominative dans training_state.json**

---

## 🧪 Tests Complets

### Fichier de test
`tests/test_correctifs_a_b.py`

### Résultats
```
tests/test_correctifs_a_b.py::TestCorrectifB::test_is_noise_heading_nom_prenom_pattern PASSED
tests/test_correctifs_a_b.py::TestCorrectifB::test_is_noise_heading_avs PASSED
tests/test_correctifs_a_b.py::TestCorrectifB::test_is_noise_heading_dates PASSED
tests/test_correctifs_a_b.py::TestCorrectifB::test_is_noise_heading_form_labels PASSED
tests/test_correctifs_a_b.py::TestCorrectifB::test_is_noise_heading_too_many_digits PASSED
tests/test_correctifs_a_b.py::TestCorrectifB::test_is_noise_heading_valid_titles PASSED
tests/test_correctifs_a_b.py::TestCorrectifA::test_scan_with_index_msg_true PASSED
tests/test_correctifs_a_b.py::TestCorrectifA::test_scan_with_index_msg_false PASSED
tests/test_correctifs_a_b.py::TestCorrectifA::test_scan_default_index_msg PASSED
tests/test_correctifs_a_b.py::TestCorrectifA::test_scan_no_msg_files PASSED
tests/test_correctifs_a_b.py::TestCorrectifA::test_extensions_count_with_index_msg PASSED
tests/test_correctifs_a_b.py::TestIntegration::test_integration_with_index_msg_true PASSED
tests/test_correctifs_a_b.py::TestIntegration::test_integration_with_index_msg_false PASSED
tests/test_correctifs_a_b.py::TestIntegration::test_no_regression_on_existing_extensions PASSED

============================== 14 passed in 0.24s ==============================
```

✅ **14/14 tests passés** - Aucune régression sur PDF/DOCX/TXT

---

## 📝 TODO : Intégration UI Streamlit

### Pages à modifier

#### 1. `pages_streamlit/training_and_test.py`

**Ajouter checkbox** :
```python
# Dans la section Configuration
index_msg = st.checkbox(
    "📧 Indexer fichiers .msg (emails Outlook)",
    value=False,
    help="Active l'indexation des emails Outlook dans le RAG. "
         "Déconseillé si les emails contiennent des données sensibles."
)

# Warning si OFF et .msg détectés
if not index_msg:
    st.info("💡 Les fichiers .msg ne seront PAS indexés par défaut. "
            "Activez l'option ci-dessus pour les inclure.")
```

**Passer le paramètre** :
```python
# Lors du scan
result = scan_client_folder(client_path, index_msg=index_msg)

# Afficher warning si présent
for warning in result["warnings"]:
    if "EXT_NOT_INDEXED" in warning:
        st.warning(warning)
```

#### 2. `pages_streamlit/batch_parser.py`

Même logique : ajouter checkbox et passer `index_msg` aux fonctions de scan.

---

## ✅ Critères d'Acceptation

### Correctif A ✅
- [x] Avec `index_msg=True`, .msg inclus dans `rag_sources`
- [x] Avec `index_msg=False`, .msg non inclus, warning `EXT_NOT_INDEXED`
- [x] Comportement par défaut = `index_msg=False`
- [x] Pas de crash si `extract-msg` non installé
- [x] Pas de régression sur PDF/DOCX/TXT/DOC
- [x] 5 tests unitaires passent

### Correctif B ✅
- [x] `unknown_titles_top` ne contient AUCUN NOM/PRENOM/AVS/date
- [x] Les stats `coverage_pct` restent dans [0..100]
- [x] Pas de régression sur sections valides
- [x] Fonction `is_noise_heading()` testée (6 cas)
- [x] Intégration dans `extract_sections_from_docx()`
- [x] Filtrage dans comptage `unknown_titles`

---

## 🔗 Fichiers Modifiés

| Fichier | Changement | Lignes |
|---------|------------|--------|
| `src/rhpro/client_scanner.py` | Ajout param `index_msg` | +40 |
| `src/rhpro/dataset_training.py` | Ajout `is_noise_heading()` | +50 |
| `src/rhpro/dataset_training.py` | Filtrage dans extraction | +5 |
| `tests/test_correctifs_a_b.py` | Tests complets (NOUVEAU) | +350 |

**Total** : ~450 lignes ajoutées, **0 régression**

---

## 🚀 Prochaines Étapes

1. **UI Streamlit** : Ajouter checkbox "Indexer .msg" dans pages Training & Batch Parser
2. **Documentation utilisateur** : Mettre à jour GUIDE_TRAINING.md avec option .msg
3. **Validation production** : Tester sur dataset réel avec .msg
4. **Cache .msg** : Optionnel, éviter ré-extraction (futur)

---

**Statut final** : ✅ **READY FOR PRODUCTION**

**Maintenu par** : Équipe SCRIPT.IA  
**Dernière revue** : 28 décembre 2025
