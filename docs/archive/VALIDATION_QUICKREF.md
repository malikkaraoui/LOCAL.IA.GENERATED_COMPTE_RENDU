# Validation GO/NO-GO - Référence Rapide

## Import

```python
from src.rhpro.validation_profiles import validate_report, ValidationProfile
```

## Profils

| Profil | Coverage | Quality | Champs critiques | Sources |
|--------|----------|---------|------------------|---------|
| **STRICT** | ≥85% | ≥0.75 | 0 manquants | ≥3 |
| **STANDARD** | ≥75% | ≥0.65 | ≤1 manquant | ≥2 |
| **DRAFT** | Aucune limite | Toujours DRAFT | - | - |

## Usage

```python
# Valider un rapport
result = validate_report(
    metrics_path=Path("output/client_metrics.json"),
    debug_path=Path("output/client_debug.json"),
    profile=ValidationProfile.STRICT,
)

# Statut
print(result.status)  # "GO" | "NO_GO" | "DRAFT"

# Raisons
if result.status == "NO_GO":
    print(result.reasons)  # ["low_coverage: 0.72 < 0.85", ...]
    print(result.actions)  # ["add_sources", "confirm_identity", ...]

# Scores
print(result.scores["quality_score"])  # 0.0-1.0
print(result.scores["required_coverage"])  # 0.0-1.0
```

## CLI

```bash
python src/rhpro/validation_profiles.py output/client_metrics.json strict
```

## Intégration Report Generator

```python
generator.generate_from_client(
    sources_folder="...",
    validation_profile=ValidationProfile.STRICT,  # Nouveau !
)
```

## UI Streamlit

```python
if validation["status"] == "GO":
    st.success("✅ Validé")
elif validation["status"] == "NO_GO":
    st.error("❌ Refusé")
    st.write(validation["reasons"])
else:
    st.warning("📝 Brouillon")
```

## Actions

- `add_identity_sources` : Ajouter CV, pièce d'identité
- `add_sources` : Plus de documents RAG
- `select_gold_candidate` : Choisir rapport GOLD
- `confirm_identity` : Confirmer nom/prénom/date
- `review_and_complete` : Réviser brouillon

## Points Clés

✅ **DOCX toujours généré** (même en NO_GO)  
✅ **Validation indépendante** de la génération  
✅ **Statut clair** : GO | NO_GO | DRAFT  
✅ **Actions guidées** pour améliorer
