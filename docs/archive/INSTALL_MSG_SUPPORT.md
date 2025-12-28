# 🚀 Installation Support .msg

**Date** : 28 décembre 2025

---

## Installation rapide (1 commande)

```bash
pip install extract-msg>=0.48.0
```

---

## Vérification

```bash
# Vérifier installation
python -c "from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE; print('✅ Support .msg:', MSG_SUPPORT_AVAILABLE)"
```

**Résultat attendu** :
```
✅ Support .msg: True
```

---

## Tests

```bash
# Tests .msg
pytest tests/test_msg_extraction.py -v

# Résultat attendu :
# ✅ 7 passed
```

---

## Démo

```bash
python demo_msg_support.py
```

---

## Si erreur "Impossible de résoudre l'importation"

C'est **NORMAL** avant installation. Cette erreur disparaît après :

```bash
pip install extract-msg>=0.48.0
```

---

## Support

Si problème : consulter [MSG_SUPPORT_QUICKSTART.md](MSG_SUPPORT_QUICKSTART.md)
