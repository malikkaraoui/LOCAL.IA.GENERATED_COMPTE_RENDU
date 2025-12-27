# Batch Parser — Quick Start

## 🚀 Démarrage rapide

### CLI : Parser plusieurs dossiers

```bash
# 1. Découvrir les dossiers
python demo_batch.py data/samples --list-only

# 2. Lancer le batch
python demo_batch.py data/samples --output out/batch

# 3. Consulter les rapports
cat out/batch/batch_report.md
```

### UI Streamlit : Interface graphique

```bash
# 1. Lancer Streamlit
streamlit run streamlit_app.py

# 2. Naviguer vers "Batch Parser RH-Pro" (sidebar)

# 3. Browse → Découvrir → Sélectionner → Lancer
```

## 📊 Exemple de sortie

```
============================================================
📊 RÉSUMÉ DU BATCH
============================================================
Total traité       : 2
Succès             : 2
Erreurs            : 0
Production Gate GO : 2
Production Gate NO : 0
Coverage moyen     : 87.5%

✅ client_01            | stage                | GO      | 75.0%
✅ client_02            | stage                | GO      | 100.0%
```

## 📁 Fichiers générés

- `batch_report.json` : Données structurées
- `batch_report.md` : Rapport lisible
- `client_XX/normalized.json` : Données normalisées par client
- `client_XX/report.json` : Rapport détaillé par client

## 🧪 Tests

```bash
pytest tests/test_batch_samples.py -v
# 11 passed ✅
```

## 📚 Documentation complète

Voir [`docs/BATCH_PARSER_GUIDE.md`](docs/BATCH_PARSER_GUIDE.md)

## ✨ Fonctionnalités

- ✅ Découverte automatique dossiers
- ✅ Parsing batch parallélisable
- ✅ Profil auto-détecté ou forcé
- ✅ Rapports JSON + Markdown
- ✅ UI Streamlit avec browse dialog
- ✅ Tests d'intégration complets
- ✅ Backward compatible

---

**Version** : 1.0.0 | **Date** : 27 déc 2025 | **Statut** : ✅ Ready
