# Guide : Utilisation .msg dans le système RH-Pro

**Date** : 28 décembre 2025

---

## 🎯 Vue d'ensemble

Le support .msg est **automatiquement activé** dans toutes les parties du système :
- ✅ Pipeline extraction (core/extract.py)
- ✅ Orchestrateur (rapport_orchestrator.py)
- ✅ Training (dataset_training.py)
- ✅ API Backend (si utilisé)

**Pas besoin de configuration** : tout fonctionne "out of the box" après `pip install extract-msg` !

---

## 📦 Composants concernés

### 1. core/extract.py (Pipeline d'extraction)

**Fonction principale** : `extract_sources()`

```python
from core.extract import extract_sources
from pathlib import Path

# ✅ Support .msg activé par défaut
result = extract_sources(
    root=Path("client/sources"),
    enable_msg=True,  # ✅ Activé par défaut
    msg_attachments_dir=Path("sandbox/msg_attachments")  # Optionnel
)

# Résultat
print(result["counts"]["ok"])  # Nombre sources extraites (inclut .msg)
print(result["enable_msg"])  # True
print(result["msg_attachments_extracted"])  # Nombre pièces jointes
```

**Paramètres** :
- `enable_msg` (bool) : Activer extraction .msg (défaut: True)
- `msg_attachments_dir` (Path) : Dossier pour pièces jointes (optionnel)

**Retour** :
```python
{
    "counts": {
        "ok": 15,  # Inclut .msg
        "errors": 2,
        "skipped": 5
    },
    "enable_msg": True,
    "msg_attachments_extracted": 3,  # Nombre pièces jointes
    "documents": [
        {
            "path": "email.msg",
            "ext": ".msg",
            "extractor": "extract-msg",
            "text": "[EMAIL_MSG] Subject: ... Body: ...",
            ...
        }
    ]
}
```

---

### 2. rapport_orchestrator.py (Orchestrateur)

**Utilisation** : Transparente, rien à changer !

```python
# Dans extract_sources() ligne 201
payload = extract_sources(
    config.client_dir,
    enable_soffice=config.enable_soffice,
    # ✅ enable_msg=True automatique
)
```

**Comportement** :
- Les .msg sont automatiquement détectés et extraits
- Pièces jointes ajoutées aux sources RAG
- Pas de configuration supplémentaire

**Si extract-msg absent** :
- Warning dans logs : "extract-msg non installé"
- .msg marqués en erreur
- Pipeline continue (pas de crash)

---

### 3. dataset_training.py (Training)

**Fonction** : `discover_client_folders()`

```python
# Extensions exploitables (ligne 846)
exploitable_extensions = {".docx", ".pdf", ".txt", ".doc", ".msg"}
# ✅ .msg ajouté automatiquement
```

**Comportement** :
- Dossiers avec .msg détectés comme clients exploitables
- .msg comptés dans stats
- Warning `MSG_EXTRACTOR_MISSING` si extract-msg absent

**Dans training_state.json** :
```json
{
  "warnings": [
    {
      "code": "MSG_EXTRACTOR_MISSING",
      "message": "Des fichiers .msg sont présents mais extract-msg n'est pas installé",
      "count": 5
    }
  ],
  "dataset": {
    "doc_types_stats": {
      ".msg": 5  // Uniquement compteur, pas de contenu
    }
  }
}
```

---

### 4. API Backend (si utilisé)

**Fichier** : `backend/workers/orchestrator.py`

Si le backend utilise `extract_sources()` via import, le support .msg est automatique :

```python
from core.extract import extract_sources

# ✅ Fonctionne automatiquement
result = extract_sources(client_dir)
```

**Note** : Vérifier que extract-msg est dans `backend/requirements.txt` si environnement séparé.

---

## 🔧 Configuration avancée

### Désactiver .msg temporairement

```python
from core.extract import extract_sources

# Désactiver support .msg
result = extract_sources(
    root=client_dir,
    enable_msg=False  # ❌ .msg ignorés
)
```

### Personnaliser dossier pièces jointes

```python
from core.extract import extract_sources
from pathlib import Path

# Dossier personnalisé pour pièces jointes
result = extract_sources(
    root=client_dir,
    msg_attachments_dir=Path("/custom/sandbox/attachments")
)
```

### Filtrer extensions (inclure .msg uniquement)

```python
result = extract_sources(
    root=client_dir,
    include_extensions=[".msg"]  # Seulement .msg
)
```

---

## 🧪 Tests d'intégration

### Test pipeline complète

```python
from core.extract import extract_sources
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    # Créer structure test
    client_dir = Path(tmpdir) / "client"
    client_dir.mkdir()
    
    # Copier fichiers test
    (client_dir / "test.txt").write_text("Test")
    (client_dir / "email.msg").write_bytes(b"...")  # Vrai .msg
    
    # Extraire
    result = extract_sources(client_dir, enable_msg=True)
    
    # Vérifier
    assert result["counts"]["ok"] >= 1  # Au moins .txt
    assert any(doc["ext"] == ".msg" for doc in result["documents"])
```

### Test orchestrator

```python
from rapport_orchestrator import PipelineOrchestrator
from core.models import PipelineConfig

config = PipelineConfig(
    client_dir="test_client/",
    template_path="template.docx",
    # ... autres params
)

orch = PipelineOrchestrator(config)
extracted_path, payload, reused = orch.extract_sources(config)

# Vérifier .msg traités
docs = payload["documents"]
msg_docs = [d for d in docs if d["ext"] == ".msg"]
print(f"{len(msg_docs)} emails extraits")
```

---

## 📊 Monitoring

### Logs à surveiller

```python
# Succès
2025-12-28 10:00:00 - core.extract - INFO - Extraction MSG: email.msg
2025-12-28 10:00:00 - core.extract - DEBUG - MSG extrait: 1234 caractères, 2 pièces jointes

# Warning (extract-msg absent)
2025-12-28 10:00:00 - core.extractors.msg - WARNING - extract-msg non installé : les fichiers .msg ne seront pas indexés

# Erreur (fichier corrompu)
2025-12-28 10:00:00 - core.extract - ERROR - Erreur extraction MSG email.msg: ...
```

### Métriques

```python
result = extract_sources(client_dir)

# Taux succès .msg
msg_total = sum(1 for d in result["documents"] if d["ext"] == ".msg")
msg_ok = sum(1 for d in result["documents"] if d["ext"] == ".msg" and not d.get("error"))
msg_success_rate = msg_ok / msg_total if msg_total > 0 else 0

print(f"Taux succès .msg : {msg_success_rate:.1%}")
```

---

## 🐛 Debugging

### Vérifier support .msg

```python
from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE
print(f"Support .msg : {MSG_SUPPORT_AVAILABLE}")
```

### Tester extraction manuelle

```python
from core.extractors.msg_extractor import extract_msg_safe
from pathlib import Path

msg_path = Path("test.msg")
text, meta, error = extract_msg_safe(msg_path)

if error:
    print(f"Erreur : {error}")
else:
    print(f"Subject : {meta['subject']}")
    print(f"Texte : {text[:200]}...")
```

### Activer logs détaillés

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Logs détaillés pour extraction .msg
from core.extract import extract_sources
result = extract_sources(client_dir)
```

---

## 🚀 Déploiement

### Environnement production

```bash
# requirements.txt (déjà ajouté)
extract-msg>=0.48.0

# Installation
pip install -r requirements.txt

# Vérification
python -c "from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE; print('OK' if MSG_SUPPORT_AVAILABLE else 'KO')"
```

### Docker

```dockerfile
# Dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
# ✅ extract-msg installé automatiquement
```

### CI/CD

```yaml
# .github/workflows/test.yml
- name: Test .msg support
  run: |
    pip install extract-msg
    pytest tests/test_msg_extraction.py -v
```

---

## ⚠️ Points d'attention

### Performance

- **.msg volumineux** : Limite 200k caractères (déjà implémentée)
- **Pièces jointes** : Seulement PDF/DOCX/DOC/TXT (pas d'images)
- **Concurrence** : extraction-msg n'est pas thread-safe (utiliser ProcessPoolExecutor si parallélisme)

### Sécurité

- **Fichiers malveillants** : extract-msg peut crash sur .msg malformés (déjà géré en erreur individuelle)
- **Données sensibles** : AUCUN contenu email dans training_state.json (vérifié)
- **Sandbox** : Pièces jointes extraites dans dossier isolé

### Compatibilité

- **extract-msg versions** : Testé avec >=0.48.0
- **Python versions** : 3.8+
- **OS** : Windows/Linux/macOS

---

## ✅ Checklist intégration

- [ ] extract-msg installé (`pip install extract-msg>=0.48.0`)
- [ ] Tests passent (`pytest tests/test_msg_extraction.py`)
- [ ] Démo fonctionne (`python demo_msg_support.py`)
- [ ] Logs ne montrent pas d'erreur .msg
- [ ] Training UI ne montre plus `MSG_EXTRACTOR_MISSING`
- [ ] Recherche RAG trouve contenu .msg

---

## 📞 Support

### Problèmes fréquents

1. **"MSG_EXTRACTOR_MISSING"** → `pip install extract-msg`
2. **".msg pas indexés"** → Vérifier `MSG_SUPPORT_AVAILABLE`
3. **"Erreur extraction"** → Vérifier logs, fichier corrompu ?

### Ressources

- [MSG_SUPPORT_COMPLETE.md](MSG_SUPPORT_COMPLETE.md) : Doc technique
- [MSG_SUPPORT_QUICKSTART.md](MSG_SUPPORT_QUICKSTART.md) : Guide rapide
- [demo_msg_support.py](demo_msg_support.py) : Démo interactive

---

**TL;DR** : `pip install extract-msg` + ça marche partout automatiquement ! 🎉
