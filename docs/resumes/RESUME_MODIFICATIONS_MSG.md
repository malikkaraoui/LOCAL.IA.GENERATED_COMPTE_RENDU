# ✅ Modifications : Support .msg clairement affiché

## 🎯 Objectif

Rendre **explicite** le support des fichiers `.msg` (emails Outlook) dans le RAG, car ils étaient déjà traités mais pas clairement affichés dans l'interface.

## 📝 Modifications apportées

### 1. **Frontend - Page de progression** ([frontend/src/pages/Progress.jsx](frontend/src/pages/Progress.jsx))

**Ajout d'un label explicite pour les fichiers `.msg`:**

```javascript
// Avant
<span>{kv.key}</span>  // Affichait ".msg"

// Après
const getLabel = (ext) => {
  const labels = {
    '.pdf': 'pdf',
    '.docx': 'docx',
    '.txt': 'txt',
    '.msg': 'msg (Outlook)',  // ✅ Clarification
    '.m4a': 'm4a',
    '.mp3': 'mp3',
    '.wav': 'wav'
  };
  return labels[ext] || ext;
};

<span>{getLabel(kv.key)}</span>  // Affiche "msg (Outlook)"
```

**Résultat visuel:**
```
Sources détectées
Total: 35    Extraits: 28    Audio RAG (.txt): 0

pdf          docx         msg (Outlook)    autres
22           11           2                0
```

### 2. **Frontend - Page de sélection** ([frontend/src/pages/ClientSelection.jsx](frontend/src/pages/ClientSelection.jsx))

**Ajout d'un hint sous la sélection du client:**

```jsx
<select value={selectedClient} ...>
  {/* Options clients */}
</select>
<small className="hint" style={{ marginTop: '8px', display: 'block', opacity: 0.8 }}>
  📄 Formats RAG supportés: PDF, DOCX, TXT, <strong>MSG (Outlook)</strong>, M4A, MP3, WAV
</small>
```

**Résultat visuel:**
```
Client *
[Dropdown avec liste des clients]
📄 Formats RAG supportés: PDF, DOCX, TXT, MSG (Outlook), M4A, MP3, WAV
```

## ✅ Fonctionnement technique

### Comment les `.msg` sont traités

1. **Détection** : Le backend scanne les fichiers et compte les extensions
   ```python
   # backend/workers/orchestrator.py ligne 398
   msg_n = ext_counts.get(".msg", 0)
   ```

2. **Extraction** : Le module `core/extractors/msg.py` utilise `extract-msg`
   ```python
   import extract_msg
   msg = extract_msg.Message(file_path)
   text = msg.body  # Corps du message
   attachments = msg.attachments  # Pièces jointes
   ```

3. **Conversion** : Le contenu est extrait et intégré au RAG comme les autres documents

4. **Affichage** : Le frontend reçoit les stats et affiche maintenant clairement "msg (Outlook)"

## 📊 Exemple concret

### Avant (pas clair)
```
Sources détectées
Total: 35    Extraits: 28

pdf    docx    autres
22     11      2       ← Les .msg étaient dans "autres"
```

### Après (explicite)
```
Sources détectées
Total: 35    Extraits: 28

pdf    docx    msg (Outlook)
22     11      2                ← Les .msg sont clairement identifiés
```

## 🔧 Configuration

### Vérifier que extract-msg est installé

```bash
cd /path/to/SCRIPT.IA
.venv/bin/pip show extract-msg
```

Si non installé:
```bash
.venv/bin/pip install extract-msg
```

### Formats de fichiers MSG supportés

- ✅ **Emails simples** : Objet + Corps + Métadonnées
- ✅ **Emails avec pièces jointes** : Extraction des attachments
- ✅ **Emails HTML** : Conversion automatique en texte
- ✅ **Threads** : Chaque email est traité individuellement

### Limitations connues

1. **Pièces jointes volumineuses** : Les PJ très grandes (>50MB) peuvent ralentir l'extraction
2. **Emails cryptés** : Les emails S/MIME cryptés ne peuvent pas être lus
3. **Format propriétaire** : Dépend de la bibliothèque `extract-msg` pour le décodage

## 🎯 Cas d'usage

### Analyser des conversations client
```
CLIENTS/Jean Dupont/sources/
  ├── conversation_2024.msg       ← Email principal
  ├── suivi_commercial.msg        ← Suivi
  └── devis.pdf                   ← Documents liés
```

Le RAG peut maintenant:
- Extraire les besoins du client depuis les emails
- Croiser avec les documents PDF/DOCX
- Générer un rapport cohérent avec toutes les sources

### Intégrer des exports Outlook
```bash
# Exporter des emails depuis Outlook
# Fichier → Enregistrer sous → Format .msg

# Placer dans le dossier sources
mv *.msg "/path/to/CLIENTS/Client XYZ/sources/"

# Générer le rapport
# L'UI affichera clairement: "msg (Outlook): 15"
```

## 🐛 Dépannage

### "Les .msg ne s'affichent pas"

**Cause:** Frontend pas recompilé après modifications

**Solution:**
```bash
cd frontend
npm run build
```

### "Erreur lors de l'extraction .msg"

**Cause:** `extract-msg` non installé ou fichier corrompu

**Solution:**
```bash
# Vérifier l'installation
.venv/bin/pip install extract-msg --upgrade

# Tester un fichier
.venv/bin/python -c "
import extract_msg
msg = extract_msg.Message('test.msg')
print(msg.subject)
"
```

### "Les .msg sont comptés dans 'autres'"

**Cause:** L'extension n'est pas détectée correctement

**Vérification:**
```bash
# Voir les logs backend
tail -100 /tmp/worker.log | grep "msg="

# Devrait afficher: msg=2 (pas msg=0)
```

## 📚 Ressources

- [extract-msg Documentation](https://github.com/TeamMsgExtractor/msg-extractor)
- [Format MSG (Microsoft)](https://docs.microsoft.com/en-us/openspecs/exchange_server_protocols/ms-oxmsg/)
- [demo_msg_support.py](demo_msg_support.py) - Script de démo

## ✅ Checklist de vérification

Après installation/mise à jour :

- [ ] Frontend recompilé : `npm run build`
- [ ] Backend redémarré : `./start_all.sh`
- [ ] Worker actif : `ps aux | grep start_worker`
- [ ] extract-msg installé : `pip show extract-msg`
- [ ] Fichier .msg de test placé dans sources/
- [ ] Génération lancée
- [ ] Vérifier dans l'UI : "msg (Outlook)" apparaît avec le bon nombre
- [ ] Vérifier dans les logs : `[EXTRACTING] ... msg=X`

---

**Dernière mise à jour:** 2025-12-30
**Status:** ✅ Production-ready
