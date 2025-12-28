# Training UI - Aperçu Rapide ⚡

## 🎯 En bref

**UI Training RH-Pro** : Interface complète pour scanner, analyser et générer des comptes-rendus automatiquement avec RAG + garde-fous.

## 🚀 Démarrage 30 secondes

```bash
# 1. Installer
pip install llama-index llama-index-embeddings-openai llama-index-llms-openai pandas

# 2. Configurer
export OPENAI_API_KEY="sk-..."

# 3. Lancer
streamlit run streamlit_app.py

# 4. Utiliser
# → 🎓 Entraînement Pipeline RH-Pro → 📦 Batch → Browse BATCH_XX → Scanner → Sélectionner → Run
```

## 📊 Ce que ça fait

1. **Scan Batch** : Analyse tous les clients d'un batch
2. **Table Interactive** : Sélection multiple avec scoring compatibilité
3. **Analyse 4 Sections** : Trouvé / Exploitable / Manquant / GOLD choisi
4. **Génération RAG** : Extraction champs avec LLM + garde-fous
5. **Outputs** : generated.docx + debug.json + metrics.json

## 🛡️ Garde-fous

- ❌ **Interdiction d'inventer** : Si non trouvé → "Non renseigné"
- ✅ **Citations obligatoires** : Source + snippet + confiance
- ✅ **Traçabilité** : debug.json avec preuves

## 📁 Fichiers Clés

```
src/rhpro/
├── batch_analyzer.py       # Scan batch + scoring
├── rag_generator.py        # RAG + LLM extraction
└── report_generator.py     # Génération DOCX

pages_streamlit/training.py # UI complète

docs/
├── TRAINING_QUICKSTART.md  # Guide rapide
└── TRAINING_UI_GUIDE.md    # Guide complet
```

## 💡 Usage Code

```python
# Scanner batch
from src.rhpro.batch_analyzer import scan_batch_clients
batch = scan_batch_clients("data/samples/BATCH_20")

# Générer rapport
from src.rhpro.report_generator import generate_report_from_normalized
result = generate_report_from_normalized(
    "sandbox/BATCH_20/client_01",
    output_dir="output",
    strict_mode=True,
)

print(f"Qualité: {result['metrics']['quality_score']:.2f}")
```

## 📊 Métriques Exemple

```json
{
  "required_coverage": 85.0,    // % champs obligatoires
  "quality_score": 0.78,        // Score global
  "avg_confidence": 0.81        // Confiance moyenne
}
```

## 📚 Documentation Complète

- [TRAINING_QUICKSTART.md](TRAINING_QUICKSTART.md) : Guide démarrage
- [docs/TRAINING_UI_GUIDE.md](docs/TRAINING_UI_GUIDE.md) : Guide complet
- [examples_training_ui.py](examples_training_ui.py) : 10 exemples
- [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) : Détails implémentation

## ✅ Status

**IMPLÉMENTATION TERMINÉE** ✨

- 3 modules core (1,197 lignes)
- UI Streamlit complète (+400 lignes)
- 4 guides documentation (~1,500 lignes)
- 10 exemples + tests

---

**Prêt à l'emploi** 🚀
