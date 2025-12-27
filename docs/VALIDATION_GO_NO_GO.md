# Guide de Validation GO/NO-GO

## Vue d'ensemble

La couche de validation fournit un système **indépendant** pour évaluer la qualité des rapports RH-Pro générés. Un rapport peut être **généré** mais **refusé** si la qualité est insuffisante.

---

## Concept Clé

```
Génération ≠ Validation
```

- ✅ **DOCX toujours généré** (même en NO_GO)
- 🔍 **Validation indépendante** après génération
- 🎯 **3 profils** selon le niveau d'exigence
- 📊 **Statut clair** : GO | NO_GO | DRAFT

---

## Les 3 Profils de Validation

### 1️⃣ STRICT (Production RH-Pro)

**Cas d'usage** : Rapports destinés aux professionnels RH

**Critères** :
- ✅ **0** champ critique manquant (nom, prénom, date_naissance, situation_pro)
- ✅ Couverture requise : **≥ 85%**
- ✅ Score qualité : **≥ 0.75**
- ✅ Sources RAG : **≥ 3**
- ✅ Confiance moyenne : **≥ 0.7**

**Résultat** :
```json
{
  "status": "GO",
  "profile": "strict",
  "reasons": [],
  "actions": [],
  "scores": {
    "required_coverage": 0.92,
    "weighted_coverage": 0.88,
    "quality_score": 0.85,
    "avg_confidence": 0.82
  }
}
```

---

### 2️⃣ STANDARD (Acceptable)

**Cas d'usage** : Rapports avec quelques tolérances

**Critères** :
- ⚠️ **≤ 1** champ critique manquant (ex: AVS absent toléré)
- ⚠️ Couverture requise : **≥ 75%**
- ⚠️ Score qualité : **≥ 0.65**
- ⚠️ Sources RAG : **≥ 2**
- ⚠️ Confiance moyenne : **≥ 0.6**

**Résultat** :
```json
{
  "status": "GO",
  "profile": "standard",
  "reasons": [
    "missing_fields: date_naissance"
  ],
  "actions": [
    "confirm_identity"
  ],
  "scores": {
    "required_coverage": 0.78,
    "quality_score": 0.68
  }
}
```

---

### 3️⃣ DRAFT (Brouillon)

**Cas d'usage** : Dossier pauvre, génération non bloquée

**Critères** :
- 📝 **Aucune limite** (toujours validé)
- 📝 Status toujours **DRAFT**
- 📝 Liste "à compléter" visible

**Résultat** :
```json
{
  "status": "DRAFT",
  "profile": "draft",
  "reasons": [
    "draft_mode_enabled",
    "missing_critical_fields: 3",
    "low_required_coverage: 0.35 < 0.75"
  ],
  "actions": [
    "add_identity_sources",
    "add_sources",
    "review_and_complete"
  ],
  "scores": {
    "required_coverage": 0.35,
    "quality_score": 0.32
  }
}
```

---

## Utilisation

### 1. Import

```python
from src.rhpro.validation_profiles import (
    validate_report,
    validate_batch,
    ValidationProfile,
)
```

### 2. Validation d'un rapport unique

```python
from pathlib import Path

result = validate_report(
    metrics_path=Path("output/client_metrics.json"),
    debug_path=Path("output/client_debug.json"),
    meta_path=Path("sandbox/BATCH_20/client/meta.json"),  # optionnel
    profile=ValidationProfile.STRICT,
)

print(f"Status: {result.status}")  # GO | NO_GO | DRAFT
print(f"Reasons: {result.reasons}")
print(f"Actions: {result.actions}")
print(f"Quality: {result.scores['quality_score']}")
```

### 3. Validation d'un batch

```python
results = validate_batch(
    output_dir=Path("output"),
    profile=ValidationProfile.STANDARD,
)

for client_name, result in results.items():
    if result.status == "GO":
        print(f"✅ {client_name} validé")
    elif result.status == "NO_GO":
        print(f"❌ {client_name} refusé : {result.reasons}")
    else:
        print(f"📝 {client_name} brouillon")
```

### 4. Intégration dans report_generator

```python
from src.rhpro.report_generator import RHProReportGenerator
from src.rhpro.validation_profiles import ValidationProfile

generator = RHProReportGenerator()

result = generator.generate_from_client(
    sources_folder="sandbox/BATCH_20/client_01/sources",
    gold_path="sandbox/BATCH_20/client_01/gold/rapport.docx",
    output_dir="output",
    client_name="client_01",
    strict_mode=True,
    validation_profile=ValidationProfile.STRICT,  # 👈 Validation automatique
)

# Résultat contient la validation
if result["validation"]:
    print(f"Status: {result['validation']['status']}")
    print(f"Reasons: {result['validation']['reasons']}")
```

---

## Cas d'Usage Typiques

### Cas 1 : Production RH-Pro (STRICT)

```python
# Contexte : rapport pour un conseiller RH
result = validate_report(
    metrics_path=Path("output/client_metrics.json"),
    debug_path=Path("output/client_debug.json"),
    profile=ValidationProfile.STRICT,
)

if result.status == "GO":
    # ✅ Envoyer au conseiller
    send_to_rh_advisor(client_docx)
else:
    # ❌ Demander plus de sources
    print(f"Raisons : {result.reasons}")
    print(f"Actions : {result.actions}")
```

### Cas 2 : Acceptable avec AVS manquant (STANDARD)

```python
# Contexte : rapport acceptable avec 1 champ manquant toléré
result = validate_report(
    metrics_path=Path("output/client_metrics.json"),
    profile=ValidationProfile.STANDARD,
)

if result.status == "GO":
    # ⚠️ Valider mais marquer "AVS à confirmer"
    print("✅ Rapport OK avec note : AVS à confirmer")
```

### Cas 3 : Dossier pauvre (DRAFT)

```python
# Contexte : peu de sources, mais génération souhaitée
result = validate_report(
    metrics_path=Path("output/client_metrics.json"),
    profile=ValidationProfile.DRAFT,
)

# Status toujours DRAFT
print(f"📝 Brouillon généré")
print(f"À compléter : {result.actions}")
```

---

## Workflow Complet

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Scanner Batch → Détecter clients                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Normaliser → sandbox/BATCH_20/                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Générer RAG + DOCX → output/                             │
│    ├─ client_generated.docx                                 │
│    ├─ client_debug.json                                     │
│    └─ client_metrics.json                                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. ⭐ VALIDATION AUTOMATIQUE ⭐                              │
│    validate_report(metrics, debug, profile=STRICT)          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
    ┌────────┐        ┌────────┐
    │   GO   │        │ NO_GO  │
    └────┬───┘        └───┬────┘
         │                │
         ▼                ▼
  ✅ Validé         ❌ Refusé
  Envoi RH         Actions :
                   • add_sources
                   • confirm_identity
                   • select_gold
```

---

## Output : validation.json

Exemple de fichier `client_validation.json` généré :

```json
{
  "status": "NO_GO",
  "profile": "strict",
  "reasons": [
    "missing_critical_fields: 1 (max: 0)",
    "low_required_coverage: 0.72 < 0.85",
    "no_gold_detected"
  ],
  "actions": [
    "add_identity_sources",
    "add_sources",
    "select_gold_candidate",
    "confirm_identity"
  ],
  "scores": {
    "required_coverage": 0.72,
    "weighted_coverage": 0.68,
    "quality_score": 0.64,
    "avg_confidence": 0.58
  }
}
```

---

## Affichage UI (Streamlit)

```python
import streamlit as st

# Charger validation
with open("output/client_validation.json") as f:
    validation = json.load(f)

# Afficher status
if validation["status"] == "GO":
    st.success("✅ Rapport validé pour production")
elif validation["status"] == "NO_GO":
    st.error("❌ Rapport généré mais non validé")
    st.warning("Raisons :")
    for reason in validation["reasons"]:
        st.write(f"• {reason}")
    
    st.info("Actions recommandées :")
    for action in validation["actions"]:
        st.write(f"🔧 {action}")
else:  # DRAFT
    st.warning("📝 Brouillon - À compléter")
    st.info("Ce rapport nécessite des informations supplémentaires")

# Afficher métriques
col1, col2, col3 = st.columns(3)
col1.metric("Qualité", f"{validation['scores']['quality_score']:.2f}")
col2.metric("Couverture", f"{validation['scores']['required_coverage']:.2%}")
col3.metric("Confiance", f"{validation['scores']['avg_confidence']:.2f}")
```

---

## Résumé Batch

```python
from src.rhpro.validation_profiles import get_validation_summary

results = validate_batch(Path("output"), ValidationProfile.STRICT)
summary = get_validation_summary(results)

print(f"Total : {summary['total']}")
print(f"GO : {summary['go_count']} ({summary['go_rate']:.1%})")
print(f"NO_GO : {summary['no_go_count']}")
print(f"DRAFT : {summary['draft_count']}")

print("\nTop reasons :")
for reason, count in summary["top_reasons"]:
    print(f"  • {reason} : {count}x")
```

---

## Export Rapports

```python
from src.rhpro.validation_profiles import export_validation_report

results = validate_batch(Path("output"))

# Export JSON
export_validation_report(
    results,
    Path("validation_report.json"),
    format="json"
)

# Export Markdown
export_validation_report(
    results,
    Path("validation_report.md"),
    format="markdown"
)

# Export CSV
export_validation_report(
    results,
    Path("validation_report.csv"),
    format="csv"
)
```

---

## Actions Recommandées

| Action | Description |
|--------|-------------|
| `add_identity_sources` | Ajouter des documents d'identité (CV, pièce d'identité) |
| `add_sources` | Ajouter plus de documents RAG |
| `improve_source_quality` | Améliorer la qualité des documents |
| `add_rag_sources` | Augmenter le nombre de sources indexées |
| `verify_extracted_fields` | Vérifier les champs extraits manuellement |
| `select_gold_candidate` | Sélectionner un rapport GOLD |
| `confirm_identity` | Confirmer l'identité du client |
| `review_and_complete` | Réviser et compléter le brouillon |

---

## CLI

```bash
# Validation d'un rapport
python src/rhpro/validation_profiles.py output/client_metrics.json strict

# Résultat
Status: GO
Profile: strict
Scores:
  - required_coverage: 0.92
  - weighted_coverage: 0.88
  - quality_score: 0.85
  - avg_confidence: 0.82
✅ Validation exported to: output/client_validation.json
```

---

## Tests

```bash
# Démo complète
python demo_validation.py

# Test unitaire
pytest tests/test_validation_profiles.py
```

---

## Points Clés

### ✅ Toujours Génération

Le DOCX est **TOUJOURS** généré, même en NO_GO. La validation est **indépendante** de la génération.

### 📊 Statut Clair

L'UI doit afficher clairement :
- ✅ **GO** : Rapport validé
- ❌ **NO_GO** : Rapport généré mais non validé
- 📝 **DRAFT** : Brouillon à compléter

### 🔧 Actions Guidées

En cas de NO_GO, les actions recommandées guident l'utilisateur pour améliorer le rapport.

### 🎯 Profils Pragmatiques

- **STRICT** : Production exigeante
- **STANDARD** : Acceptable avec tolérances
- **DRAFT** : Brouillon non bloquant

---

## Exemples Concrets

### Exemple 1 : Batch 5/5 GO (STRICT)

```
✅ client_01 : GO (quality: 0.88)
✅ client_02 : GO (quality: 0.82)
✅ client_03 : GO (quality: 0.85)
✅ client_04 : GO (quality: 0.79)
✅ client_05 : GO (quality: 0.91)

Taux de validation : 100%
```

### Exemple 2 : Batch 3/5 GO (STANDARD)

```
✅ client_01 : GO (quality: 0.78)
❌ client_02 : NO_GO (low_coverage: 0.62 < 0.75)
✅ client_03 : GO (quality: 0.72)
❌ client_04 : NO_GO (missing_critical_fields: 2)
✅ client_05 : GO (quality: 0.81)

Taux de validation : 60%
```

### Exemple 3 : Batch 0/5 GO (STRICT) → 5/5 DRAFT

```
❌ client_01 : NO_GO → 📝 DRAFT
❌ client_02 : NO_GO → 📝 DRAFT
❌ client_03 : NO_GO → 📝 DRAFT
❌ client_04 : NO_GO → 📝 DRAFT
❌ client_05 : NO_GO → 📝 DRAFT

Mode DRAFT : génération OK, à compléter
```

---

## Compatibilité

- ✅ Python 3.8+
- ✅ Indépendant de LlamaIndex (utilise JSON)
- ✅ Compatible avec tous les formats d'output
- ✅ Intégrable dans n'importe quel workflow

---

**Version** : 2.1.0  
**Date** : 27 décembre 2025  
**Status** : ✅ Production Ready
