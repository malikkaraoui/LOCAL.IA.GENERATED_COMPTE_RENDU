# CHANGELOG — Patches 6-8 : Identity Extraction Globale

## v4.2 — 2024-01-XX

### 🎯 Objectif
Stopper les NO-GO causés par `identity` vide alors que les données (AVS, nom) existent dans le dossier client mais sont classées comme "unknown_titles".

---

## ✨ Nouveautés

### PATCH 6 : Extracteur identity global
- **Module** : `src/rhpro/identity_extractor.py` (+330 lignes)
- **Fonctionnalités** :
  - Extraction AVS/nom/prénom depuis texte brut
  - Support multi-formats : .txt, .docx, .pdf (via pdfplumber)
  - Merge intelligent sans écraser données existantes
  - Détection identity dans tous les documents RAG

### PATCH 7 : Heading Policy pour identity
- **Modification** : `src/rhpro/normalizer.py`
- **Comportement** : Les lignes contenant AVS/identity ne sont plus classées comme "unknown_titles"
- **Fonction** : `is_identity_line()` détecte les patterns d'identité

### PATCH 8 : UX Gate (spec, non implémenté)
- **Objectif** : Proposer rescanning identity si NO-GO détecté
- **Statut** : Spécification complète, implémentation différée

---

## 🔧 Modifications techniques

### Fichiers modifiés

| Fichier | Type | Changements |
|---------|------|-------------|
| `src/rhpro/identity_extractor.py` | 🆕 Nouveau | 330 lignes - 6 fonctions d'extraction |
| `src/rhpro/normalizer.py` | ✏️ Modifié | +35 lignes - Integration extraction globale |
| `src/rhpro/parse_bilan.py` | ✏️ Modifié | +10 lignes - Propagation rag_sources |
| `pages_streamlit/client_report_generator.py` | ✏️ Modifié | +8 lignes - Construction rag_sources |
| `tests/test_identity_extraction_patches.py` | 🆕 Nouveau | 295 lignes - 11 tests |

**Total** : 678 lignes ajoutées/modifiées

### Signatures modifiées (backward compatible)

```python
# Normalizer.normalize()
def normalize(
    segments: List[Segment], 
    gate_profile_override: Optional[str] = None,
    rag_sources: Optional[List[str]] = None  # 🆕 NOUVEAU (optionnel)
) -> Dict[str, Any]

# parse_bilan_docx_to_normalized()
def parse_bilan_docx_to_normalized(
    docx_path: str, 
    ruleset_path: str, 
    gate_profile_override: str = None,
    rag_sources: list = None  # 🆕 NOUVEAU (optionnel)
) -> Dict[str, Any]
```

---

## ✅ Tests

### Couverture
```bash
$ pytest tests/test_identity_extraction_patches.py -v
========================= 11 passed in 0.63s =========================
```

### Détail des tests

| Catégorie | Tests | Statut |
|-----------|-------|--------|
| Extraction texte | 3 | ✅ 3/3 |
| Extraction fichiers | 2 | ✅ 2/2 |
| Détection identity line | 2 | ✅ 2/2 |
| PATCH 7 (heading policy) | 1 | ✅ 1/1 |
| PATCH 6 (global extraction) | 2 | ✅ 2/2 |
| Integration | 1 | ✅ 1/1 |
| **TOTAL** | **11** | **✅ 11/11** |

---

## 📈 Impact

### Avant Patches 6-7

```json
{
  "unknown_titles": ["Madame Sophie DUBOIS — 756.1234.5678.90"],
  "normalized": {
    "identity": {"avs": "", "name": "", "surname": ""}  // ❌ VIDE
  },
  "production_gate": {
    "status": "NO-GO",
    "blocking_issues": ["Required section missing: identity"]
  }
}
```

### Après Patches 6-7

```json
{
  "unknown_titles": [],  // ✅ Ligne retirée
  "normalized": {
    "identity": {
      "avs": "756.1234.5678.90",  // ✅ REMPLI
      "name": "Sophie",
      "surname": "DUBOIS"
    }
  },
  "production_gate": {
    "status": "GO",  // ✅ PLUS DE BLOCAGE
    "blocking_issues": []
  }
}
```

---

## 🚀 Utilisation

### Exemple : Client report generator

```python
# Avant (PATCH 6 ignoré, identity peut rester vide)
result = parse_bilan_docx_to_normalized(
    str(selected_docx),
    str(ruleset_path)
)

# Après (PATCH 6 actif, scanne tous les fichiers)
rag_sources = []
for doc_list in [docs['docx'], docs['pdf'], docs['txt']]:
    rag_sources.extend([str(doc) for doc in doc_list])

result = parse_bilan_docx_to_normalized(
    str(selected_docx),
    str(ruleset_path),
    rag_sources=rag_sources  # 🆕 Active l'extraction globale
)
```

### Exemple : Module identity_extractor

```python
from src.rhpro.identity_extractor import extract_identity_from_text

text = "Monsieur Jean DUPONT — 756.1234.5678.90"
identity = extract_identity_from_text(text)

# Résultat:
# {
#   "avs": "756.1234.5678.90",
#   "name": "Jean",
#   "surname": "DUPONT",
#   "full_name": "Jean DUPONT"
# }
```

---

## 🐛 Corrections

### Problème résolu
**Symptôme** : NO-GO production gate alors que l'identity est présente dans le dossier client.

**Cause racine** : 
1. Extraction identity limitée à la section "Identité" du DOCX structurant
2. Lignes avec AVS classées comme "unknown_titles" au lieu d'être parsées

**Solution** :
- PATCH 6 : Scanner TOUS les fichiers du dossier (rag_sources)
- PATCH 7 : Ne pas classer les lignes identity comme unknown

---

## 📚 Documentation

- **Guide complet** : [docs/PATCHES_6_7_8_IDENTITY_GLOBAL.md](PATCHES_6_7_8_IDENTITY_GLOBAL.md)
- **Tests** : [tests/test_identity_extraction_patches.py](../tests/test_identity_extraction_patches.py)
- **Module** : [src/rhpro/identity_extractor.py](../src/rhpro/identity_extractor.py)

---

## ⚠️ Notes de migration

### Rétrocompatibilité
✅ **Changements backward compatible** : Le paramètre `rag_sources` est optionnel.

### Pour activer PATCH 6
Passer la liste des fichiers à scanner via `rag_sources` :

```python
result = parse_bilan_docx_to_normalized(
    docx_path=...,
    ruleset_path=...,
    rag_sources=[...]  # Liste de paths (str ou Path)
)
```

Si `rag_sources` est `None` ou vide, l'extraction globale est ignorée (comportement legacy).

### PATCH 7 toujours actif
La heading policy (ne pas classer identity comme unknown) est **toujours active**, aucune configuration requise.

---

## 🔮 Prochaines étapes

- [ ] PATCH 8 : Implémenter UX gate avec rescanning identity
- [ ] Extraction identity depuis PDF scannés (OCR)
- [ ] Validation croisée AVS (checksum Swiss)
- [ ] Détection conflits (2 AVS différents trouvés)

---

**Version** : 4.2  
**Date** : 2024-01-XX  
**Auteur** : GitHub Copilot
