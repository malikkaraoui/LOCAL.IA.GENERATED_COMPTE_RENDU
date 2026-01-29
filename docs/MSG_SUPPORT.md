# Support des fichiers .msg - Documentation

## 📋 Résumé

Les fichiers `.msg` (emails Outlook) sont maintenant **pleinement supportés** dans SCRIPT.IA :
- ✅ Détection et énumération au même titre que PDF/DOCX
- ✅ Extraction du contenu (sujet, corps, métadonnées)
- ✅ Indexation dans le RAG
- ✅ Affichage dans les statistiques

## 🔧 Modifications apportées

### 1. Scanner Client (`src/rhpro/client_scanner.py`)

**Changement :** `index_msg=True` par défaut

```python
def scan_client_folder(client_folder_path: str, index_msg: bool = True)
```

**Impact :**
- Les fichiers `.msg` sont maintenant inclus par défaut dans `rag_sources`
- Ils apparaissent dans les statistiques `extensions`
- Compatibilité ascendante : possibilité de désactiver avec `index_msg=False`

### 2. Extracteur Legacy (`core/extract_sources.py`)

**Ajouts :**
- Import du module `msg_extractor`
- Ajout de `.msg` dans `SUPPORTED_DIRECT`
- Gestion de l'extraction dans `extract_one()`

```python
SUPPORTED_DIRECT = {".pdf", ".docx", ".txt", ".msg"}

# Lazy import du module .msg
try:
    from core.extractors.msg_extractor import extract_msg_to_text
    MSG_SUPPORT_AVAILABLE = True
except ImportError:
    MSG_SUPPORT_AVAILABLE = False
```

### 3. Orchestrateur (`backend/workers/orchestrator.py`)

**Changement :** Ajout de `.msg` dans les logs de détection

```python
msg_n = ext_counts.get(".msg", 0)
# ...
f"(pdf={pdf_n}, docx={docx_n}, txt={txt_n}, msg={msg_n}, ...)"
```

### 4. Frontend React (`frontend/src/pages/Progress.jsx`)

**Changement :** Ajout de `.msg` dans la liste des extensions affichées

```javascript
const keys = ['.pdf', '.docx', '.txt', '.msg', '.m4a', '.mp3', '.wav'];
```

## 📊 Exemple de résultat

### Avant (sans .msg) :
```
📄 Types de documents détectés
.docx  56
.pdf   75
.doc    2
```

### Après (avec .msg) :
```
📄 Types de documents détectés
.docx  56
.pdf   75
.msg   11   ← NOUVEAU
.doc    2
```

## 🧪 Tests

### Test automatique
```bash
python test_msg_support.py
```

**Résultat attendu :**
```
✅ PASS - msg_extractor
✅ PASS - scanner
✅ PASS - extract_sources
✅ PASS - core_extract

✅ Tous les tests sont passés !
```

### Test d'extraction
```bash
python demo_msg_extraction.py
```

**Résultat :** Affiche le contenu extrait d'un fichier .msg

### Test sur un dossier client
```python
from src.rhpro.client_scanner import scan_client_folder

result = scan_client_folder('CLIENTS/KARAOUI Malik')
print(result['stats']['extensions'])
# Output: {'.msg': 2, '.pdf': 5, '.docx': 5, '.txt': 2}
```

## 📦 Dépendances

**Requis :** `extract-msg >= 0.48.0`

```bash
pip install "extract-msg>=0.48.0"
```

**Déjà installé dans le projet** (voir historique terminal)

## 🎯 Fonctionnalités

### Extraction complète
- **Métadonnées** : De, À, Sujet, Date, CC
- **Corps du message** : Texte brut ou HTML converti
- **Pièces jointes** : Liste + extraction optionnelle (PDF, DOCX, TXT, DOC)
- **Formatage RAG** : Structure `[EMAIL_MSG]` avec métadonnées + body

### Exemple de contenu extrait :
```
[EMAIL_MSG]
Subject: Conseil d'orientation
From: contact@rh-pro.ch
To: malik.karaoui@example.com
Date: 2024-10-21 09:38:47+02:00
---
Body:
Bonjour Malik,

Suite à notre entretien...

[Corps du message...]
```

## 🔄 Rétrocompatibilité

- **Scanner** : `index_msg=False` désactive l'indexation (mode ancien)
- **Extraction** : Détection automatique de `extract-msg` (graceful degradation)
- **Stats** : Nouveaux champs ajoutés sans casser l'existant

## 📝 Points d'attention

1. **Performance** : L'extraction de `.msg` peut être plus lente que PDF/DOCX
2. **Taille** : Le corps des emails est limité à 200 000 caractères
3. **HTML** : Les emails HTML sont automatiquement convertis en texte
4. **Pièces jointes** : Nécessite un dossier de sortie pour l'extraction

## 🚀 Utilisation dans le pipeline

### 1. Training Dataset
```python
from src.rhpro.dataset_training import analyze_dataset

# Les .msg sont automatiquement inclus
result = analyze_dataset("data/samples/BATCH_20")
print(result.stats['extensions_distribution'])
# {'.pdf': 75, '.docx': 56, '.msg': 11, ...}
```

### 2. Génération de rapport
```python
from backend.workers.orchestrator import ReportOrchestrator

# Les .msg seront extraits et indexés automatiquement
orchestrator = ReportOrchestrator(...)
result = orchestrator.run()
```

### 3. Interface Streamlit
Les fichiers `.msg` apparaissent maintenant automatiquement dans :
- La section "Types de documents détectés"
- Les statistiques de sources
- Le comptage total de fichiers

## ✅ Checklist de validation

- [x] Module `msg_extractor` créé et fonctionnel
- [x] Scanner inclut `.msg` par défaut (`index_msg=True`)
- [x] Extracteur legacy supporte `.msg`
- [x] Orchestrateur log les `.msg`
- [x] Frontend affiche les `.msg`
- [x] Tests automatiques passent
- [x] Extraction testée sur vrais fichiers
- [x] Documentation créée

## 📚 Fichiers modifiés

1. `src/rhpro/client_scanner.py` - Scanner avec index_msg=True
2. `core/extract_sources.py` - Support .msg dans extracteur legacy
3. `backend/workers/orchestrator.py` - Logs incluant .msg
4. `frontend/src/pages/Progress.jsx` - Affichage .msg
5. `test_msg_support.py` - Tests automatiques (nouveau)
6. `demo_msg_extraction.py` - Démo extraction (nouveau)

## 🎓 Pour aller plus loin

### Extraction avancée de pièces jointes
```python
from core.extractors.msg_extractor import extract_msg_to_text

# Extraire avec pièces jointes
text, meta = extract_msg_to_text(
    msg_path=Path("email.msg"),
    output_dir=Path("attachments/")
)

# Vérifier les PJ extraites
if meta.get('extracted_attachments_paths'):
    for att_path in meta['extracted_attachments_paths']:
        print(f"Extrait : {att_path}")
```

### Filtrage personnalisé
```python
# Exclure les .msg lors du scan
result = scan_client_folder(client_path, index_msg=False)

# Compter les .msg non indexés
msg_count = result.get('msg_files_count', 0)
print(f"{msg_count} fichiers .msg exclus")
```

## 🐛 Dépannage

### Erreur : "extract-msg non installé"
```bash
pip install "extract-msg>=0.48.0"
```

### Les .msg n'apparaissent pas
1. Vérifier que `index_msg=True` (défaut depuis cette mise à jour)
2. Vérifier que `extract-msg` est installé
3. Tester avec `python test_msg_support.py`

### Erreur lors de l'extraction
- Certains .msg corrompus peuvent échouer (non bloquant)
- Les emails très lourds (>10MB) peuvent être lents
- Les pièces jointes nécessitent des droits en écriture

## 📞 Support

Pour toute question ou problème :
1. Exécuter `python test_msg_support.py`
2. Vérifier les logs dans `core.extractors.msg`
3. Tester avec `python demo_msg_extraction.py`
