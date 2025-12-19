# 🚀 Guide de Démarrage Rapide

## En 3 Étapes Simples

### 1️⃣ Démarrer le Système

Ouvrez un terminal et exécutez :

```bash
cd "/Users/malik/Documents/Espace de travail/SCRIPT.IA"
./scripts/start-all.sh
```

**Résultat attendu :**
```
🎉 Tous les services sont démarrés !

📱 Frontend:  http://localhost:5173
🔧 Backend:   http://localhost:8000/api/health
📚 API Docs:  http://localhost:8000/api/docs
🔐 Login:     admin / admin123
```

Le navigateur s'ouvre automatiquement sur http://localhost:5173

---

### 2️⃣ Générer un Rapport

**Dans l'interface web :**

1. **Sélectionnez un client** dans la liste déroulante
   - Exemple : "KARAOUI Malik"

2. **Cliquez sur "Générer le Rapport"** 
   - Un seul clic !

3. **Suivez la progression** :
   ```
   ⏳ En attente...
   📂 Extraction des données... (2-5s)
   🤖 Génération par l'IA... (~1m30s)
   📝 Création du DOCX... (1-2s)
   ✅ Terminé !
   ```

4. **Téléchargez le rapport**
   - Cliquez sur "Télécharger DOCX"
   - Le fichier se trouve dans : `CLIENTS/KARAOUI Malik/06 Rapport final/`

---

### 3️⃣ Arrêter le Système

Quand vous avez terminé :

```bash
./scripts/stop.sh
```

**Résultat :**
```
✅ Tous les services sont arrêtés
```

---

## 🎯 Workflow Complet Détaillé

### Étape 1 : Extraction des Données

Le système scanne automatiquement :

```
CLIENTS/KARAOUI Malik/
├── 01 Dossier personnel/     → Informations personnelles
├── 02 Devis/                  → Contrats et devis
├── 03 Tests et bilans/        → Tests psychométriques
├── 04 Stages/                 → Expériences professionnelles
└── 05 Mesures AI/             → Documents administratifs
```

**Fichiers supportés :**
- 📧 `.msg` (emails Outlook)
- 📄 `.docx` (Word)
- 📊 `.pdf` (PDFs)
- 📝 `.txt` (texte brut)

**Extraction typique :** ~68KB de données textuelles

---

### Étape 2 : Génération IA

L'IA (Ollama avec Mistral) génère :

1. **Synthèse biographique** : Parcours et situation actuelle
2. **Compétences transférables** : Liste détaillée des aptitudes
3. **Projet professionnel** : Objectifs et aspirations
4. **Plan d'action** : Étapes concrètes et recommandations
5. **Conclusion** : Synthèse et perspectives

**Durée moyenne :** ~1 minute 35 secondes

---

### Étape 3 : Rendu DOCX

Le système :

1. Charge le template : `CLIENTS/templates/template_rapport.docx`
2. Remplace tous les marqueurs `{{champ}}` 
3. Insère les sections générées
4. Sauvegarde le DOCX final (~37KB)

**Sortie :**
```
CLIENTS/KARAOUI Malik/06 Rapport final/
└── Rapport_KARAOUI_Malik_2025-12-16.docx
```

---

## 🔍 Vérifications Rapides

### Vérifier que tout fonctionne

```bash
# Backend
curl http://localhost:8000/api/health
# Attendu: {"status":"healthy","version":"2.0.1"}

# Frontend
curl http://localhost:5173 | grep "<title>"
# Attendu: <title>frontend</title>

# Redis
redis-cli ping
# Attendu: PONG

# Ollama
curl http://localhost:11434/api/version
# Attendu: {"version":"..."}
```

### Consulter les Logs en Direct

```bash
# Ouvrez 3 terminaux et lancez :

# Terminal 1 - Worker
tail -f /tmp/worker.log

# Terminal 2 - Backend
tail -f /tmp/backend.log

# Terminal 3 - Frontend
tail -f /tmp/frontend.log
```

---

## 🎨 Captures d'Écran du Workflow

### 1. Page d'Accueil
```
┌──────────────────────────────────────────┐
│  SCRIPT.IA - Générateur de Rapports      │
├──────────────────────────────────────────┤
│                                          │
│  Sélectionnez un client :                │
│  ┌────────────────────────────────┐      │
│  │ KARAOUI Malik              ▼  │      │
│  └────────────────────────────────┘      │
│                                          │
│  [Générer le Rapport]                    │
│                                          │
└──────────────────────────────────────────┘
```

### 2. Génération en Cours
```
┌──────────────────────────────────────────┐
│  📊 Génération en cours...               │
├──────────────────────────────────────────┤
│                                          │
│  Client: KARAOUI Malik                   │
│  Statut: running                         │
│                                          │
│  ✅ Extraction terminée (3.2s)           │
│  🤖 Génération IA en cours... (1m12s)    │
│  ⏳ Rendu DOCX...                        │
│                                          │
│  [Rafraîchir le statut]                  │
│                                          │
└──────────────────────────────────────────┘
```

### 3. Rapport Terminé
```
┌──────────────────────────────────────────┐
│  ✅ Rapport généré avec succès !         │
├──────────────────────────────────────────┤
│                                          │
│  Client: KARAOUI Malik                   │
│  Durée totale: 1m58s                     │
│                                          │
│  Fichier:                                │
│  Rapport_KARAOUI_Malik_2025-12-16.docx   │
│                                          │
│  [Télécharger DOCX]  [Nouveau Rapport]   │
│                                          │
└──────────────────────────────────────────┘
```

---

## 📞 Besoin d'Aide ?

### Problème : Le navigateur ne s'ouvre pas

**Solution :**
```bash
# Ouvrez manuellement
open http://localhost:5173
```

### Problème : "Redis n'est pas actif"

**Solution :**
```bash
# Démarrer Redis
brew services start redis

# Ou manuellement
redis-server &
```

### Problème : "Ollama non accessible"

**Solution :**
```bash
# Démarrer Ollama
ollama serve &

# Télécharger Mistral si absent
ollama pull mistral
```

### Problème : Le rapport ne se génère pas

**Solutions :**

1. **Vérifier les logs du worker**
   ```bash
   tail -f /tmp/worker.log
   ```

2. **Vérifier les données client**
   ```bash
   ls -R "CLIENTS/KARAOUI Malik/"
   ```

3. **Relancer le worker**
   ```bash
   pkill -f start_worker.py
   .venv/bin/python scripts/start_worker.py &
   ```

---

## 🎓 Utilisation Avancée

### Changer le Modèle IA

Dans [backend/core/config.py](backend/core/config.py), modifiez :

```python
DEFAULT_MODEL = "llama3.1:8b"  # Plus rapide
# ou
DEFAULT_MODEL = "mixtral:8x7b"  # Plus performant
```

### Personnaliser le Template

1. Ouvrez `CLIENTS/templates/template_rapport.docx`
2. Modifiez le contenu
3. Ajoutez des marqueurs : `{{nouveau_champ}}`
4. Mettez à jour `CLIENTS/generate_fields.py`

### Ajouter un Nouveau Client

```bash
# Créer la structure de dossiers
mkdir -p "CLIENTS/NOUVEAU Client/"{01\ Dossier\ personnel,02\ Devis,03\ Tests\ et\ bilans,04\ Stages,05\ Mesures\ AI,06\ Rapport\ final}

# Ajouter des fichiers dans les dossiers
# Le système détectera automatiquement le nouveau client
```

---

## ✅ Checklist Avant de Commencer

- [ ] Python 3.13+ installé : `python3 --version`
- [ ] Node.js installé : `node --version`
- [ ] Redis démarré : `redis-cli ping`
- [ ] Ollama avec Mistral : `ollama list | grep mistral`
- [ ] Dépendances Python : `pip install -r requirements.txt`
- [ ] Dépendances Node : `cd frontend && npm install`
- [ ] Template présent : `ls CLIENTS/templates/template_rapport.docx`
- [ ] Au moins un client : `ls CLIENTS/ | grep -v templates`

**Tout est OK ?** → Lancez `./scripts/start-all.sh` 🚀
