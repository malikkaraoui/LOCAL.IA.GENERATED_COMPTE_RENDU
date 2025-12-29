# Quick Win: Fallback Identity depuis Folder Name

**Date**: 2025-01-XX  
**Objectif**: Réduire le taux de NO-GO en extrayant l'identité depuis le nom du dossier client quand aucune autre source ne fournit les données.

## Contexte

**Problème identifié**: Dans ~46% des dossiers clients, aucune identité (name/surname) n'est trouvée dans les documents DOCX ou les fichiers RAG, causant des NO-GO bloquants.

**Observation**: Les dossiers clients suivent une convention de nommage avec le nom du client (ex: `SCHMIDT Mélanie`, `CAMPOS DA COSTA Paula`).

## Solution Implémentée

### Architecture en Cascade (3 niveaux)

1. **Niveau 1**: Extraction depuis sections DOCX (existant)
2. **Niveau 2**: Extraction depuis RAG sources - tous fichiers (.txt, .docx, .pdf)
3. **Niveau 3**: **NOUVEAU** Fallback depuis le nom du dossier client

### Fonction d'Extraction

**Fichier**: `src/rhpro/identity_extractor.py`

```python
def extract_identity_from_folder_name(folder_name: str) -> dict
```

**Patterns supportés**:
- `SCHMIDT Mélanie` → surname: SCHMIDT, name: Mélanie
- `CAMPOS DA COSTA Paula` → surname: CAMPOS DA COSTA, name: Paula
- `VAN DEN BERG Jan` → surname: VAN DEN BERG, name: Jan
- `Jean Dupont` → surname: Dupont, name: Jean (fallback si pas de majuscules)
- `001_MARTIN Sophie` → surname: MARTIN, name: Sophie (ignore préfixes numériques)

**Logique**:
1. Nettoyer le nom: retirer préfixes numériques (`^\d+[_\-\s]*`), extensions
2. Remplacer underscores/tirets par espaces
3. Identifier les mots en MAJUSCULES (>50% de lettres majuscules) comme nom de famille
4. Grouper les mots MAJUSCULES consécutifs (pour noms composés)
5. Les autres mots = prénom

### Intégration dans le Pipeline

**Fichier**: `src/rhpro/normalizer.py`

```python
def normalize(segments, gate_profile_override=None, rag_sources=None, client_name=None):
    # ... extraction sections DOCX ...
    
    # PATCH 6: Extraction depuis RAG sources
    if rag_sources and not self._is_identity_filled(normalized):
        # ... extraction RAG ...
    
    # QUICK WIN: Fallback depuis folder name
    if client_name and not self._is_identity_filled(normalized):
        folder_identity = extract_identity_from_folder_name(client_name)
        if folder_identity.get('name') or folder_identity.get('surname'):
            normalized['identity'] = merge_identity_results(
                normalized.get('identity', {}),
                folder_identity,
                prefer_existing=True  # Ne pas écraser données existantes
            )
            self.inline_warnings.append(
                f"⚠ Identity inferred from folder name: {client_name}"
            )
```

**Propagation du `client_name`**:
- UI (`pages_streamlit/client_report_generator.py`): extrait `client_path.name`
- Parser (`src/rhpro/parse_bilan.py`): ajoute paramètre `client_name`
- Normalizer: reçoit et utilise `client_name` pour fallback

### Traçabilité

Un warning est ajouté dans le rapport quand l'identité est inférée depuis le folder name :

```
⚠ Identity inferred from folder name: SCHMIDT Mélanie
```

Cela permet :
- De distinguer les sources d'extraction
- D'auditer la qualité des données
- De prioriser les améliorations (renforcer extraction DOCX/RAG)

## Tests

**Fichier**: `tests/test_folder_name_fallback.py`

### Tests Unitaires (9 tests)

1. **Pattern classique**: `SCHMIDT Mélanie`
2. **Nom composé**: `CAMPOS DA COSTA Paula`
3. **Mixed case**: `Jean Dupont`
4. **Nom avec tiret**: `Dupont-Martin Sophie`
5. **Préfixe numérique**: `001_SCHMIDT Mélanie`
6. **Underscores**: `MARTIN_Sophie`
7. **Mot unique**: `DUPONT`
8. **String vide**: ` `
9. **Exemples réels**: KARAOUI, DA SILVA, VAN DEN BERG, O'CONNOR

### Tests d'Intégration (3 tests)

1. **Fallback activé**: Quand aucune identity dans document/RAG
2. **Fallback NON activé**: Quand identity déjà présente dans document
3. **Priorité RAG**: RAG sources ont priorité sur folder name

**Résultat**: ✅ **12/12 tests passent**

## Impact Attendu

### Réduction des NO-GO

**Avant**:
- ~46% de clients sans identity
- Cause principale de NO-GO

**Après (estimation)**:
- Réduction de 30-40% des NO-GO liés à identity manquante
- Hypothèse: La majorité des dossiers suivent la convention de nommage

### Qualité des Données

- **Priorité préservée**: DOCX > RAG > Folder Name
- **Pas d'écrasement**: `merge_identity_results(prefer_existing=True)`
- **Traçabilité**: Warning explicite dans le rapport

### Cas Non Couverts

Le fallback échouera si :
- Le dossier a un nom générique : `Dossier 1`, `Client A`
- Le nom ne suit pas la convention : `rapport_final_2024`
- Le nom est mal structuré : `Mélanie`, `SCHMIDT`

Pour ces cas, un NO-GO sera toujours généré (comportement attendu).

## Améliorations Futures (Optionnel)

1. **Extraction AVS depuis folder name**: Pattern `SCHMIDT_Mélanie_756.1234.5678.90`
2. **Détection de préfixes/suffixes**: `Mr_SCHMIDT_Mélanie`, `SCHMIDT_Mélanie_v2`
3. **Normalisation des noms**: `Mc Donald` → `McDonald`, `Van der Berg` → `VAN DER BERG`
4. **ML model**: Apprendre les patterns de nommage depuis le dataset

## Documentation Technique

### Commits

- Quick Win: Folder name identity fallback
- Fichiers modifiés: 5 (identity_extractor, normalizer, parse_bilan, UI, tests)
- Tests ajoutés: 12

### Compatibilité

- ✅ Compatible avec PATCH 6 (RAG sources)
- ✅ Compatible avec PATCH 7 (Heading policy)
- ✅ Compatible avec DRAFT mode (Patches A-C)
- ✅ Pas de breaking change

### Configuration

Aucune configuration requise. Le fallback s'active automatiquement si :
- `client_name` est fourni au parser
- L'identity n'est pas trouvée dans DOCX/RAG

## Conclusion

Ce Quick Win apporte un **impact immédiat** sur la robustesse du système avec :
- **Implémentation simple**: ~150 lignes de code
- **Tests complets**: 12/12 passent
- **Impact mesurable**: Réduction estimée de 30-40% des NO-GO identity
- **Traçabilité**: Warnings explicites pour audit

**Statut**: ✅ **READY FOR PRODUCTION**
