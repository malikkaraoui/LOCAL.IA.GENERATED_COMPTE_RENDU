# Champs Critiques RH-Pro - Documentation

## 📋 Vue d'ensemble

Les **champs critiques** sont une liste fixe et non négociable de champs qui DOIVENT être présents et validés pour qu'un rapport RH-Pro soit considéré comme valide en mode `STRICT`.

**Règle fondamentale** : **no-evidence = no-claim**
- Chaque valeur extraite DOIT avoir des preuves traçables dans les sources
- Les preuves sont stockées dans `debug.json` sous `evidence.category.field[]`

---

## 🎯 Champs Critiques Définis

### 1. **Identité** (Obligatoire)
```yaml
identity:
  - nom           # OBLIGATOIRE
  - prenom        # OBLIGATOIRE
  - civilite      # OPTIONNEL mais recommandé
```

**Règle** :
- `nom` et `prenom` DOIVENT être présents et non vides
- Si non trouvés → Statut `NO_GO` en mode STRICT

---

### 2. **AVS** (Extraction conditionnelle)
```yaml
avs:
  - numero_avs    # Si trouvé → extraire, sinon "Non renseigné / à confirmer"
```

**Règle** :
- Si AVS présent dans les sources → DOIT être extrait
- Si AVS absent → Marquer comme `"Non renseigné / à confirmer"` ou `"À confirmer"`
- L'absence d'AVS n'est pas bloquante, mais doit être explicitement documentée

---

### 3. **Profession / Formation** (Au moins l'un des deux)
```yaml
professional:
  - situation_professionnelle  # Profession actuelle
  - niveau_formation           # Formation/études
```

**Règle** :
- **Au moins l'un des deux** DOIT être renseigné OU explicitement marqué `"Non renseigné"`
- Si les deux sont vides ou `"Non renseigné"` → Statut `NO_GO` en mode STRICT
- Exemples valides :
  - Profession renseignée, formation vide : ✅ OK
  - Formation renseignée, profession vide : ✅ OK
  - Les deux vides : ❌ NO_GO

---

### 4. **Sources** (Minimum 1)
```yaml
sources:
  sources_used: >= 1  # Au moins 1 source RAG doit être utilisée
```

**Règle** :
- Un rapport SANS sources est considéré comme du vide
- `sources_used >= 1` est OBLIGATOIRE en mode STRICT
- Vérifié via `debug.json → index.sources_count`

---

## 📊 Structure Evidence dans debug.json

Tous les champs critiques doivent avoir leurs **preuves traçables** dans `debug.json` :

```json
{
  "evidence": {
    "identity": {
      "nom": [
        {
          "source": "CV_2024.pdf",
          "text": "Jean DUPONT - Conseiller en orientation",
          "score": 0.92
        }
      ],
      "prenom": [
        {
          "source": "CV_2024.pdf",
          "text": "Jean DUPONT",
          "score": 0.92
        }
      ],
      "numero_avs": []  // Pas de preuve = valeur non fiable
    },
    "professional": {
      "situation_professionnelle": [
        {
          "source": "Entretien_RH.docx",
          "text": "Actuellement en poste en tant que Conseiller en orientation depuis 2020",
          "score": 0.88
        }
      ],
      "niveau_formation": []
    }
  }
}
```

**Interprétation** :
- `nom` et `prenom` : ✅ Preuves présentes → Valeurs fiables
- `numero_avs` : ⚠️ Aucune preuve → Valeur non renseignée (acceptable si explicite)
- `situation_professionnelle` : ✅ Preuve présente → Valeur fiable
- `niveau_formation` : ⚠️ Aucune preuve → Doit être explicitement marqué "Non renseigné"

---

## ⚙️ Seuils de Validation STRICT

Mis à jour dans [`src/rhpro/validation_profiles.py`](../src/rhpro/validation_profiles.py) :

```python
ValidationProfile.STRICT: {
    "missing_critical_fields_max": 0,    # Aucun champ critique manquant toléré
    "required_coverage_min": 0.85,       # 85% des champs requis
    "quality_score_min": 0.75,           # Score qualité >= 0.75
    "sources_count_min": 1,              # AU MOINS 1 source (sinon vide)
    "confidence_min": 0.7,               # Confiance moyenne >= 0.7
    "profession_or_formation_required": True,  # Au moins l'un des deux
}
```

---

## 🔧 Implémentation

### Fichiers Modifiés

1. **[`src/rhpro/validation_profiles.py`](../src/rhpro/validation_profiles.py)**
   - Définition des `CRITICAL_FIELDS` avec structure hiérarchique
   - Fonction `_get_missing_critical_fields()` avec validation AVS et profession/formation
   - Seuils STRICT mis à jour

2. **[`src/rhpro/rag_generator.py`](../src/rhpro/rag_generator.py)**
   - Extraction des preuves (`evidence`) dans `generate_report()`
   - Nouvelle méthode `_extract_evidence_from_citations()`
   - Ajout de `full_text` dans les citations pour traçabilité

3. **[`src/rhpro/report_generator.py`](../src/rhpro/report_generator.py)**
   - Nouvelle méthode `_structure_evidence()` pour structurer les preuves par catégorie
   - Export structuré dans `debug.json` avec `evidence.identity.*`, `evidence.professional.*`, etc.

---

## 📝 Exemple d'Usage

### Validation d'un Rapport

```python
from pathlib import Path
from src.rhpro.validation_profiles import validate_report, ValidationProfile

# Valider avec profil STRICT
result = validate_report(
    metrics_path=Path("output/client_metrics.json"),
    debug_path=Path("output/client_debug.json"),
    profile=ValidationProfile.STRICT
)

print(f"Status: {result.status}")  # GO / NO_GO / DRAFT
print(f"Reasons: {result.reasons}")
print(f"Actions: {result.actions}")

# Vérifier les champs critiques manquants
if "missing_critical_fields" in str(result.reasons):
    print("⚠️ Champs critiques manquants détectés !")
```

### Exemple de Sortie NO_GO

```json
{
  "status": "NO_GO",
  "profile": "strict",
  "reasons": [
    "missing_critical_fields: 2 (max: 0)",
    "missing_fields: numero_avs_confirmation_needed, profession_or_formation",
    "insufficient_sources: 0 < 1"
  ],
  "actions": [
    "add_identity_sources",
    "add_rag_sources",
    "confirm_identity"
  ],
  "scores": {
    "required_coverage": 0.65,
    "weighted_coverage": 0.58,
    "quality_score": 0.62,
    "avg_confidence": 0.55
  }
}
```

---

## ✅ Checklist de Validation

Pour qu'un rapport passe en `GO` en mode STRICT :

- [ ] `nom` présent avec preuves dans `evidence.identity.nom[]`
- [ ] `prenom` présent avec preuves dans `evidence.identity.prenom[]`
- [ ] `numero_avs` extrait SI présent, sinon marqué "Non renseigné / à confirmer"
- [ ] **Au moins l'un** :
  - [ ] `situation_professionnelle` renseigné avec preuves
  - [ ] `niveau_formation` renseigné avec preuves
- [ ] `sources_count >= 1` dans `debug.json → index.sources_count`
- [ ] Score qualité >= 0.75
- [ ] Couverture requise >= 85%
- [ ] Confiance moyenne >= 0.7

---

## 🚨 Messages d'Erreur Courants

| Message | Signification | Action Recommandée |
|---------|---------------|-------------------|
| `missing_critical_fields: 2 (max: 0)` | Champs critiques manquants | Ajouter sources d'identité |
| `profession_or_formation` | Ni profession ni formation renseignés | Compléter au moins l'un des deux |
| `numero_avs_confirmation_needed` | AVS non extrait | Vérifier si AVS présent dans sources |
| `insufficient_sources: 0 < 1` | Aucune source RAG | Ajouter sources au dossier client |
| `no-evidence for field: nom` | Valeur sans preuve | Vérifier extraction RAG |

---

## 📚 Références

- [Validation Profiles](../src/rhpro/validation_profiles.py)
- [RAG Generator](../src/rhpro/rag_generator.py)
- [Report Generator](../src/rhpro/report_generator.py)
- [Production Gate Profiles](./PRODUCTION_GATE_PROFILES.md)

---

**Dernière mise à jour** : 27 décembre 2025  
**Version** : 1.0 - Implémentation champs critiques RH-Pro
