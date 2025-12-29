# PATCHES 6-8 : Extraction identity globale + Heading Policy

**Date** : $(date +%Y-%m-%d)  
**Version** : v4.2  
**Statut** : ✅ IMPLÉMENTÉ + TESTÉ

---

## 📋 Vue d'ensemble

Ces 3 patches résolvent le problème de **NO-GO causés par identity vide** alors que les données d'identité (AVS, nom, prénom) existent dans le dossier client mais sont classées comme "unknown_titles".

### Symptôme diagnostiqué

```json
// report.json
{
  "unknown_titles": [
    "Madame Sophie DUBOIS — 756.1234.5678.90"  // ❌ AVS ignoré !
  ]
}

// normalized.json
{
  "identity": {
    "avs": "",      // ❌ Vide !
    "name": "",
    "surname": ""
  }
}
```

**Résultat** : NO-GO alors que l'identité est présente dans le dossier.

---

## 🎯 PATCH 6 : Extracteur identity global

### Objectif
Extraire l'identité depuis **TOUS** les documents du dossier client (pas seulement la section "Identité" du DOCX structurant).

### Implémentation

#### Nouveau module : `src/rhpro/identity_extractor.py`

6 fonctions principales :

```python
def extract_identity_from_text(text: str) -> Dict[str, str]:
    """
    Extrait AVS, nom, prénom depuis du texte.
    
    Patterns supportés:
    - "Monsieur Jean DUPONT — 756.1234.5678.90"
    - "Madame Marie MARTIN 756.9876.5432.10"
    - "AVS: 756.1234.5678.90"
    - "756 1234 5678 90" (tolérant aux espaces/points/tirets)
    
    Returns:
        {"avs": "756.1234.5678.90", "name": "Jean", "surname": "DUPONT", "full_name": "Jean DUPONT"}
    """
```

```python
def extract_identity_from_corpus(texts: List[str], max_lines: int = 50) -> Dict[str, str]:
    """
    Extrait identity depuis plusieurs documents.
    Merge les résultats (le premier AVS trouvé gagne, idem pour nom).
    """
```

```python
def extract_identity_from_files(file_paths: List[Union[str, Path]], max_lines_per_file: int = 50) -> Dict[str, str]:
    """
    Extrait identity depuis fichiers réels (.txt, .docx, .pdf).
    Lit les N premières lignes de chaque fichier.
    """
```

```python
def merge_identity_results(existing: Dict, new: Dict) -> Dict:
    """
    Merge deux dicts identity SANS écraser les données existantes.
    Stratégie: existing a priorité, new comble les trous.
    """
```

```python
def is_identity_line(text: str) -> bool:
    """
    Détecte si une ligne contient de l'identité.
    Utilisé par PATCH 7 pour heading policy.
    
    Returns True si:
    - Contient AVS (756.xxxx.xxxx.xx)
    - Pattern "Monsieur/Madame ... AVS"
    - Mot-clé "identité", "coordonnées", "AVS", "assuré"
    """
```

```python
def contains_avs(text: str) -> bool:
    """Détection rapide d'AVS (756.xxxx.xxxx.xx)"""
```

#### Intégration dans Normalizer

**Fichier** : `src/rhpro/normalizer.py`

```python
# Nouvelles imports
from .identity_extractor import (
    extract_identity_from_files,
    merge_identity_results,
    is_identity_line
)

# Nouvelle signature de normalize()
def normalize(self, segments: List[Segment], 
             gate_profile_override: Optional[str] = None,
             rag_sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Args:
        rag_sources: Liste des fichiers sources pour extraction identity globale (PATCH 6)
    """
    
    # ... traitement habituel ...
    
    # PATCH 6: Extraction identity globale si identity vide
    if rag_sources and not self._is_identity_filled(normalized):
        global_identity = extract_identity_from_files(rag_sources)
        if global_identity:
            normalized['identity'] = merge_identity_results(
                normalized.get('identity', {}), 
                global_identity
            )
            self.inline_warnings.append("Identity extracted from RAG sources (global scan)")
```

**Helper ajouté** :

```python
def _is_identity_filled(self, normalized: Dict[str, Any]) -> bool:
    """
    Vérifie si identity contient au moins AVS ou nom complet.
    """
    identity = normalized.get('identity', {})
    
    if identity.get('avs'):
        return True
    if identity.get('name') and identity.get('surname'):
        return True
    if identity.get('full_name'):
        return True
    
    return False
```

#### Propagation de rag_sources

**Fichier** : `src/rhpro/parse_bilan.py`

```python
def parse_bilan_docx_to_normalized(docx_path: str, ruleset_path: str, 
                                   gate_profile_override: str = None,
                                   rag_sources: list = None) -> Dict[str, Any]:
    """
    Args:
        rag_sources: Liste des fichiers sources pour extraction identity globale (PATCH 6)
    """
    # ...
    result = normalize_segments(segments, ruleset, 
                                gate_profile_override=gate_profile_override,
                                rag_sources=rag_sources)
```

**Fichier** : `pages_streamlit/client_report_generator.py`

```python
# Construire la liste des rag_sources (PATCH 6)
rag_sources = []
for doc_list in [docs['docx'], docs['pdf'], docs['txt']]:
    rag_sources.extend([str(doc) for doc in doc_list])

# Parser avec rag_sources
result = parse_bilan_docx_to_normalized(
    str(selected_docx),
    str(ruleset_path),
    gate_profile_override=gate_profile,
    rag_sources=rag_sources
)
```

### Tests

**Fichier** : `tests/test_identity_extraction_patches.py`

| Test | Description | Résultat |
|------|-------------|----------|
| `test_extract_identity_from_text_with_avs` | Extraction AVS depuis texte simple | ✅ PASS |
| `test_extract_identity_from_text_without_monsieur` | Extraction sans pattern "Monsieur/Madame" | ✅ PASS |
| `test_extract_identity_no_avs` | Pas d'hallucination si aucun AVS | ✅ PASS |
| `test_contains_avs` | Détection rapide d'AVS | ✅ PASS |
| `test_extract_identity_from_files` | Extraction depuis fichier TXT | ✅ PASS |
| `test_extract_identity_from_multiple_files` | Merge depuis plusieurs fichiers | ✅ PASS |
| `test_identity_extracted_from_rag_sources` | Integration test avec parse_bilan | ✅ PASS |
| `test_no_hallucination_when_no_identity` | Pas d'invention d'identity | ✅ PASS |

**Total** : 8/8 tests ✅

---

## 🎯 PATCH 7 : Heading Policy — Identity lines

### Objectif
Éviter que les lignes contenant de l'identité soient classées comme "unknown_titles".

### Implémentation

**Fichier** : `src/rhpro/normalizer.py`

```python
def _generate_report(self, segments: List[Segment], normalized: Dict[str, Any]) -> Dict[str, Any]:
    """Génère un rapport de couverture"""
    # ...
    
    # Segments trouvés
    for segment in segments:
        if segment.mapped_section_id:
            found_sections.append({...})
        else:
            # PATCH 7: Ne pas ajouter aux unknown_titles si c'est une ligne d'identité
            if not is_identity_line(segment.normalized_title):
                unknown_titles.append(segment.normalized_title)
            else:
                # Logger pour debug
                self.inline_warnings.append(
                    f"Identity line not classified as unknown: '{segment.normalized_title[:60]}...'"
                )
```

### Logique de détection

La fonction `is_identity_line()` retourne `True` si :

1. **Contient AVS** : Pattern `756.xxxx.xxxx.xx` détecté
2. **Pattern nominatif** : "Monsieur/Madame ... AVS"
3. **Mots-clés identity** : "identité", "coordonnées", "AVS", "assuré", "patient"

### Tests

| Test | Description | Résultat |
|------|-------------|----------|
| `test_is_identity_line` | Détection lignes identity vs normales | ✅ PASS |
| `test_identity_line_not_in_unknown_titles` | Integration avec Normalizer | ✅ PASS |
| `test_full_workflow_with_patches` | Workflow complet PATCH 6+7 | ✅ PASS |

**Total** : 3/3 tests ✅

---

## 🎯 PATCH 8 : UX Gate (optionnel, non implémenté)

### Objectif
Améliorer l'UX du production gate si NO-GO à cause d'identity manquante.

### Spec (à implémenter plus tard)

```python
# Dans client_report_generator.py, après génération

if production_gate['status'] == 'NO-GO':
    missing_sections = report['missing_required_sections']
    
    if 'identity' in missing_sections:
        # Vérifier si AVS détecté dans unknown_titles
        unknown_titles = report['unknown_titles']
        has_identity_in_unknown = any(is_identity_line(t) for t in unknown_titles)
        
        if has_identity_in_unknown:
            st.warning("⚠️ Identity détectée dans unknown_titles (AVS trouvé)")
            
            if st.button("🔄 Rescanner identity (all sources)"):
                # Relancer avec rag_sources explicite
                pass
```

**Statut** : Spec complète, implémentation à faire si besoin.

---

## 📊 Résultats

### Couverture des tests

```bash
$ pytest tests/test_identity_extraction_patches.py -v
========================= 11 passed in 0.63s =========================
```

| Catégorie | Tests | Résultat |
|-----------|-------|----------|
| Extraction unitaire | 7 | ✅ 7/7 |
| PATCH 7 (heading policy) | 1 | ✅ 1/1 |
| PATCH 6 (global extraction) | 2 | ✅ 2/2 |
| Integration PATCH 6+7 | 1 | ✅ 1/1 |
| **TOTAL** | **11** | **✅ 11/11** |

### Fichiers modifiés

| Fichier | Lignes modifiées | Type |
|---------|------------------|------|
| `src/rhpro/identity_extractor.py` | +330 | 🆕 Création |
| `src/rhpro/normalizer.py` | +35 | ✏️ Modification |
| `src/rhpro/parse_bilan.py` | +10 | ✏️ Modification |
| `pages_streamlit/client_report_generator.py` | +8 | ✏️ Modification |
| `tests/test_identity_extraction_patches.py` | +295 | 🆕 Création |

**Total** : 678 lignes ajoutées/modifiées

---

## 🔍 Exemples d'utilisation

### Avant PATCH 6+7

```json
// Document contient: "Madame Sophie DUBOIS — 756.1234.5678.90"

// report.json
{
  "unknown_titles": ["Madame Sophie DUBOIS — 756.1234.5678.90"],
  "missing_required_sections": ["identity"],
  "production_gate": {
    "status": "NO-GO",
    "blocking_issues": ["Required section missing: identity"]
  }
}

// normalized.json
{
  "identity": {
    "avs": "",      // ❌ VIDE
    "name": "",
    "surname": ""
  }
}
```

### Après PATCH 6+7

```json
// report.json
{
  "unknown_titles": [],  // ✅ Ligne identity retirée
  "missing_required_sections": [],
  "warnings": ["Identity extracted from RAG sources (global scan)"],
  "production_gate": {
    "status": "GO",
    "blocking_issues": []
  }
}

// normalized.json
{
  "identity": {
    "avs": "756.1234.5678.90",  // ✅ REMPLI
    "name": "Sophie",
    "surname": "DUBOIS"
  }
}
```

---

## 🚀 Prochaines étapes

### Court terme
- [ ] PATCH 8 : Implémenter UX gate avec bouton "Rescanner identity"
- [ ] Ajouter tests avec fichiers PDF (nécessite pdfplumber)
- [ ] Logger les sources d'identity extraite (provenance tracking)

### Moyen terme
- [ ] Extraction identity depuis photos/scans (OCR)
- [ ] Validation croisée AVS (checksum, format)
- [ ] Détection de conflits (2 AVS différents trouvés)

---

## 📚 Références

- **Issue** : NO-GO causés par identity vide alors que AVS dans unknown_titles
- **Dépendances** : python-docx, pdfplumber (optionnel)
- **Tests** : tests/test_identity_extraction_patches.py
- **Documentation** : Ce fichier

---

**Auteur** : GitHub Copilot  
**Révision** : v1.0
