# ✅ Support .msg - Référence Express

**Date** : 28 décembre 2025

---

## Installation

```bash
pip install extract-msg>=0.48.0
```

---

## Utilisation (automatique)

```python
from core.extract import extract_sources

# ✅ .msg supportés automatiquement
result = extract_sources(client_dir)
```

---

## Fichiers

| Type | Fichier | Lignes |
|------|---------|--------|
| 🆕 Code | [core/extractors/msg_extractor.py](core/extractors/msg_extractor.py) | 242 |
| ✏️ Modif | [core/extract.py](core/extract.py) | +100 |
| ✏️ Modif | [dataset_training.py](src/rhpro/dataset_training.py) | +10 |
| 🧪 Tests | [test_msg_extraction.py](tests/test_msg_extraction.py) | 7 tests |
| 📖 Docs | MSG_SUPPORT_*.md | 4 fichiers |

---

## Tests

```bash
pytest tests/test_msg_extraction.py -v  # ✅ 6 passed
python demo_msg_support.py              # ✅ OK
```

---

## Ce qui est extrait

```
[EMAIL_MSG]
Subject: ...
From: ...
To: ...
Body: ...
```

+ Pièces jointes PDF/DOCX/DOC/TXT

---

## Critères validés

- ✅ Extraction fonctionne
- ✅ Recherche RAG OK
- ✅ Pas de crash si extract-msg absent
- ✅ Pas de données nominatives

---

## Warnings

### Sans extract-msg
```
⚠️ MSG_EXTRACTOR_MISSING
```

### Avec extract-msg
```
✅ Aucun warning
```

---

## Monitoring

```python
from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE
print(MSG_SUPPORT_AVAILABLE)  # True/False
```

---

## Docs complètes

1. [MSG_SUPPORT_SUMMARY.md](MSG_SUPPORT_SUMMARY.md) - Synthèse
2. [MSG_SUPPORT_COMPLETE.md](MSG_SUPPORT_COMPLETE.md) - Doc complète
3. [MSG_SUPPORT_QUICKSTART.md](MSG_SUPPORT_QUICKSTART.md) - Guide rapide
4. [MSG_SUPPORT_INTEGRATION.md](MSG_SUPPORT_INTEGRATION.md) - Intégration système

---

**Status : ✅ TERMINÉ**
