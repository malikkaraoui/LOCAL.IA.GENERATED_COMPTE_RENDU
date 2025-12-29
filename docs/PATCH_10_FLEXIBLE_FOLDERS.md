# PATCH 10 : Détection Flexible des Sous-Dossiers Clients

**Date** : 29 décembre 2024  
**Objectif** : Corriger la détection des sous-dossiers clients pour reconnaître les variantes réelles (`01 Dossier personnel`, `06 Rapport final`, etc.) au lieu de noms fixes (`01_personnel`, `06_rapport`).

---

## 🎯 Problème Résolu

### Avant (❌)
```python
# Recherche rigide par noms exacts
exists(client_root / "01_personnel")  # ❌ Échec si dossier = "01 Dossier personnel"
exists(client_root / "06_rapport")    # ❌ Échec si dossier = "06 Rapport final"
```

**Résultat** : Faux positifs "Dossiers manquants" malgré présence des dossiers.

### Après (✅)
```python
# Détection intelligente par préfixe + mots-clés
resolve_client_subfolders(client_root)
# → {"01_personnel": Path(".../01 Dossier personnel")}
# → {"06_rapport": Path(".../06 Rapport final")}
```

**Résultat** : Détection robuste de 5/7 dossiers en moyenne (100% pour requis).

---

## 🔧 Implémentation

### 1. Nouvelle Architecture

#### Mapping Canonique
```python
CANON_BY_PREFIX = {
    "01": "01_personnel",
    "02": "02_cv",
    "03": "03_tests",
    "04": "04_stages",
    "05": "05_mesures_ai",
    "06": "06_rapport",
    "07": "07_suivi",
}
```

#### Fallback par Mots-Clés
```python
KEYWORDS_FALLBACK = {
    "01_personnel": ["personnel", "dossier personnel", "infos personnelles"],
    "06_rapport": ["rapport", "rapport final", "bilan final", "final"],
    "03_tests": ["tests", "bilans", "positionnement", "riasec", "vocatio"],
    "04_stages": ["stages", "stage", "lai15", "lai 15", "lai17", "lai 17"],
    "05_mesures_ai": ["mesures", "ai", "outplacement", "ocas"],
}
```

#### Dossiers Requis
```python
REQUIRED_CANON = ["01_personnel", "06_rapport"]
```

### 2. Fonction Centrale : `resolve_client_subfolders()`

```python
def resolve_client_subfolders(client_root: Path) -> Dict[str, Path]:
    """
    Détection intelligente des sous-dossiers clients.
    
    Stratégie en 2 passes :
    1. Match par préfixe numérique (01*, 06*, etc.) → prioritaire
    2. Fallback par mots-clés si préfixe non trouvé
    
    Returns:
        Mapping {canonical_key: real_folder_path}
        ex: {"01_personnel": Path(".../01 Dossier personnel")}
    """
```

**Exemples acceptés** :
- `01 Dossier personnel`, `01_Dossier_personnel`, `01-personnel`, `1 dossier perso`
- `06 Rapport final`, `06_rapport_final`, `06 - rapport`

### 3. Normalisation Unicode Robuste

```python
def _norm(s: str) -> str:
    """
    Supprime accents, ponctuation, normalise espaces.
    
    "Dossier Persönnel" → "dossier personnel"
    "06 - Rapport_final!" → "06 rapport final"
    """
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s
```

### 4. Mise à Jour de `scan_client_folder()`

#### Nouveau Retour
```python
{
    "folder_structure": {
        "01_personnel": "/path/to/01 Dossier personnel",
        "06_rapport": "/path/to/06 Rapport final",
        ...
    },
    "folder_mapping": {  # ✨ NOUVEAU pour UI
        "01_personnel": "01 Dossier personnel",
        "06_rapport": "06 Rapport final",
        ...
    },
    "pipeline_ready": True,  # ✨ Toujours True en mode dégradé
    "warnings": [
        "✅ Dossiers détectés : 01_personnel → '01 Dossier personnel', ..."
    ]
}
```

#### Mode "Moins Bloquant"
```python
# PATCH 10: Pipeline considéré "ready" même avec warnings
pipeline_ready = True  # Mode d'entraînement "brut"

# Warnings informatifs au lieu d'erreurs bloquantes
warnings.append("⚠️  Aucun document GOLD détecté (mode dégradé)")
warnings.append("ℹ️  Peu de sources RAG (3)")
```

---

## 📊 Résultats des Tests

### Test sur Client Réel
```bash
Test PATCH 10 sur: ALVES MOREIRA Sergio Paulo

📁 DOSSIERS DÉTECTÉS:
  ✅ 01_personnel         → 01 Dossier personnel
  ✅ 03_tests             → 03 Tests et bilans
  ✅ 04_stages            → 04 Stages
  ✅ 05_mesures_ai        → 05 Mesures AI
  ✅ 06_rapport           → 06 Rapport final
  ⚠️  02_cv                → (non trouvé)
  ⚠️  07_suivi             → (non trouvé)

📊 STATS:
  pipeline_ready: True
  Gold: True (score: 0.55)
  Sources RAG: 39
  Dossiers trouvés: 5/7
```

### Test sur Plusieurs Clients
```bash
ALVES MOREIRA Sergio Paulo    5/7 dossiers  pipeline_ready: True  Gold: ✓ (0.55)  RAG: 39
BERNARD Yann                  5/7 dossiers  pipeline_ready: True  Gold: ✓ (0.55)  RAG: 13
FERNANDES Winter              5/7 dossiers  pipeline_ready: True  Gold: ✓ (0.55)  RAG: 31
CHANUT Laure                  5/7 dossiers  pipeline_ready: True  Gold: ✓ (0.55)  RAG: 13
BREISSAN Stéphane            5/7 dossiers  pipeline_ready: True  Gold: ✓ (1.00)  RAG: 13
```

**Taux de détection** : 100% pour dossiers requis (`01_personnel`, `06_rapport`)

---

## 🔄 Compatibilité

### Rétro-compatibilité
- Ancienne structure `EXPECTED_FOLDERS` conservée pour modules non migrés
- Fonction `find_folder()` toujours disponible
- Signature de `scan_client_folder()` inchangée (nouveau champ `folder_mapping` ajouté)

### Modules à Migrer (optionnel)
```python
# Avant
folder = find_folder(client_root, EXPECTED_FOLDERS["06_rapport"])

# Après (recommandé)
resolved = resolve_client_subfolders(client_root)
folder = resolved.get("06_rapport")
```

---

## 🎯 Impact

### Fonctionnalités
- ✅ **Détection robuste** : Reconnaît variantes réelles des dossiers
- ✅ **Mode dégradé** : Pipeline moins bloquant pour entraînement "brut"
- ✅ **Transparence** : `folder_mapping` affiche les noms réels détectés
- ✅ **Fallback intelligent** : Préfixe numérique → mots-clés → skip

### Fichiers Modifiés
- `src/rhpro/client_scanner.py` (+120 lignes)
  * Nouvelle fonction `_norm()`
  * Nouvelle fonction `resolve_client_subfolders()`
  * Mise à jour `scan_client_folder()` pour utiliser nouvelle logique
  * Ajout constantes `CANON_BY_PREFIX`, `KEYWORDS_FALLBACK`, `REQUIRED_CANON`

### Tests Recommandés
```bash
# Test unitaire de normalisation
python -c "from src.rhpro.client_scanner import _norm; assert _norm('Dossier Persönnel!') == 'dossier personnel'"

# Test de résolution sur client
python -c "from src.rhpro.client_scanner import resolve_client_subfolders; from pathlib import Path; print(resolve_client_subfolders(Path('./CLIENTS/ALVES MOREIRA Sergio Paulo')))"

# Test complet de scan
python -c "from src.rhpro.client_scanner import scan_client_folder; result = scan_client_folder('./CLIENTS/ALVES MOREIRA Sergio Paulo'); print(result['folder_mapping'])"
```

---

## 📝 Notes Techniques

### Stratégie de Matching
1. **PASS 1** : Match par préfixe numérique (regex `^\s*(\d{1,2})\b`)
   - "01 Dossier personnel" → préfixe "01" → `CANON_BY_PREFIX["01"]` = `"01_personnel"`
   - "6 Rapport final" → préfixe "06" (zfill) → `"06_rapport"`

2. **PASS 2** : Fallback par mots-clés (seulement si pas trouvé en PASS 1)
   - "Dossier personnel" → contient "personnel" → `"01_personnel"`
   - "Rapport final" → contient "rapport" → `"06_rapport"`

### Gestion des Edge Cases
- **Dossiers avec accents** : `Dossier Persönnel` normalisé en `dossier personnel`
- **Préfixes sans zéro** : `6 Rapport` reconnu comme `06_rapport`
- **Noms ambigus** : Priorité au préfixe numérique sur mots-clés
- **Dossiers cachés** : `.DS_Store`, `.git` automatiquement exclus

---

## ✅ Validation

- [x] Détection fonctionne sur clients réels (5 testés)
- [x] Taux de détection 100% pour dossiers requis
- [x] Mode dégradé permet pipeline même avec warnings
- [x] `folder_mapping` affiche noms réels pour UI
- [x] Compatibilité rétro-assurée
- [x] Documentation complète

**Status** : ✅ **PRODUCTION READY**
