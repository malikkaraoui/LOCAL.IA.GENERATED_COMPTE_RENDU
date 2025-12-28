# Critères d'Acceptation - UI Training RH-Pro

## Definition of Done ✅

### Scénario de Test Complet

**Objectif** : Valider le workflow complet depuis l'UI sur un batch de 5 clients.

---

## 📋 Checklist Validation

### ✅ Étape 1 : Lancement UI

```bash
streamlit run streamlit_app.py
```

**Critères** :
- [ ] Streamlit démarre sans erreur
- [ ] Page "🎓 Entraînement Pipeline RH-Pro" accessible
- [ ] Mode "📦 Batch (plusieurs clients)" sélectionnable

---

### ✅ Étape 2 : Sélection BATCH

**Actions** :
1. Cliquer sur "📁 Browse" pour "Batch racine"
2. Naviguer vers : `DATASET TRAINING/BATCH 20`
3. Valider la sélection

**Critères** :
- [ ] Browse dialog s'ouvre correctement
- [ ] Chemin `BATCH 20` sélectionnable
- [ ] Message : `✅ Batch sélectionné : BATCH_20`

---

### ✅ Étape 3 : Scan du Batch

**Actions** :
1. Cliquer sur "🔍 Scanner le batch"
2. Attendre la fin du scan

**Critères** :
- [ ] Spinner "Scan en cours..." s'affiche
- [ ] Scan se termine sans erreur
- [ ] Table "Clients Détectés" s'affiche

**Vérifications Table** :
- [ ] Colonnes présentes : Sélection | Nom dossier | Compatibilité | GOLD | Sources RAG | Warnings
- [ ] Au moins 5 clients listés
- [ ] Scores de compatibilité affichés (format : `✅ 0.87` ou `⚠️ 0.45`)
- [ ] GOLD détecté : `✅` ou `❌` visible
- [ ] Sources RAG : nombre + détail types (ex: `12 (.docx:8, .pdf:4)`)
- [ ] Warnings : nombre affiché

---

### ✅ Étape 4 : Sélection de 5 Clients

**Actions** :
1. Cocher 5 clients dans la colonne "Sélection"
2. Vérifier le message de sélection

**Critères** :
- [ ] Checkboxes fonctionnelles
- [ ] Message : `💡 5 client(s) sélectionné(s)`
- [ ] Boutons d'action visibles : Analyser | Normaliser | Run (RAG+DOCX)

---

### ✅ Étape 5 : Normalisation en Sandbox

**Actions** :
1. Cliquer sur "🔧 Normaliser"
2. Configurer :
   - Nom du batch : `BATCH_20`
   - Sandbox racine : `./sandbox`
   - Cocher "Créer normalized/source.docx (alias)"
3. Cliquer sur "🚀 Lancer la normalisation"

**Critères** :
- [ ] Progress bar s'affiche (0% → 100%)
- [ ] Status text : "Normalisation de [client]..." pour chaque client
- [ ] Message final : `✅ Normalisation terminée : 5/5 réussis`
- [ ] Pour chaque client : `✅ [nom] → [chemin_sandbox]`

**Vérification Filesystem** :
```bash
ls -la sandbox/BATCH_20/
```
- [ ] 5 dossiers clients créés
- [ ] Chaque dossier contient :
  - [ ] `sources/` avec fichiers copiés
  - [ ] `gold/` avec rapport GOLD
  - [ ] `normalized/source.docx` (si option cochée)
  - [ ] `meta.json` avec métadonnées

---

### ✅ Étape 6 : Détection GOLD

**Pour chaque client, vérifier** :

**Client avec GOLD détecté** :
- [ ] Status : `✅ GOLD détecté`
- [ ] Score GOLD : >= 0.3
- [ ] Fichier présent : `sandbox/BATCH_20/[client]/gold/[rapport].docx`

**Client sans GOLD** :
- [ ] Status : `❌ GOLD non détecté`
- [ ] Warning clair : `⚠️ Aucun document GOLD détecté`
- [ ] Message dans warnings_count

---

### ✅ Étape 7 : Génération RAG + DOCX

**Actions** :
1. Avec les 5 clients toujours sélectionnés
2. Cliquer sur "🚀 Run (RAG+DOCX)"
3. Configurer :
   - Dossier de sortie : `./output`
   - Template DOCX : (laisser vide pour défaut)
   - Mode strict : ✅ (coché)
4. Cliquer sur "🚀 Lancer la génération"

**Critères** :
- [ ] Progress bar s'affiche
- [ ] Status text : "Génération pour [client]..." pour chaque client
- [ ] Message final : `✅ Génération terminée : 5/5 réussis`

**Pour chaque client, vérifier expandable** :
- [ ] Titre : `✅ [nom_client]`
- [ ] Section "Outputs générés" :
  - [ ] DOCX : `output/[client]_generated.docx`
  - [ ] Debug JSON : `output/[client]_debug.json`
  - [ ] Metrics JSON : `output/[client]_metrics.json`
  - [ ] GOLD référence : `output/[client]_gold_reference.docx` (si GOLD détecté)

**Section "Métriques"** :
- [ ] 4 métriques affichées :
  - [ ] Couverture : X%
  - [ ] Couverture requise : Y%
  - [ ] Confiance : Z (0.0-1.0)
  - [ ] Score qualité : W (0.0-1.0)

---

### ✅ Étape 8 : Construction Index RAG

**Pour chaque client, vérifier dans debug.json** :

```bash
cat output/[client]_debug.json | python3 -m json.tool
```

**Critères** :
- [ ] Section `"index"` présente
- [ ] `"sources_count"` : > 0
- [ ] `"chunks_created"` : > 0
- [ ] `"chunks_preview"` : liste avec au moins 1 chunk
- [ ] Chaque chunk contient :
  - [ ] `chunk_id`
  - [ ] `source_file`
  - [ ] `text_preview`
  - [ ] `text_length`

---

### ✅ Étape 9 : Génération DOCX Complète

**Pour chaque client, vérifier** :

**Fichier DOCX** :
```bash
ls -lh output/[client]_generated.docx
```
- [ ] Fichier existe
- [ ] Taille > 0 KB
- [ ] Ouvrable dans Word/LibreOffice

**Contenu DOCX** :
- [ ] En-tête : "Compte-Rendu RH-Pro - [client]"
- [ ] Date de génération présente
- [ ] Champs remplis (au moins 50%)
- [ ] Pas de placeholders vides `{{field}}`
- [ ] "Non renseigné" pour champs non trouvés (mode strict)

---

### ✅ Étape 10 : Validation Métriques

**Pour chaque client, vérifier metrics.json** :

```bash
cat output/[client]_metrics.json
```

**Critères** :
- [ ] `required_coverage` : >= 0 et <= 100
- [ ] `weighted_coverage` : >= 0 et <= 100
- [ ] `quality_score` : >= 0.0 et <= 1.0
- [ ] `avg_confidence` : >= 0.0 et <= 1.0
- [ ] `total_fields` : > 0
- [ ] `filled_fields` : >= 0 et <= total_fields
- [ ] `required_fields` : > 0
- [ ] `required_filled` : >= 0 et <= required_fields

---

### ✅ Étape 11 : Affichage Batch Success

**Dans l'UI Streamlit** :

**Message final** :
- [ ] `✅ Génération terminée : 5/5 réussis`
- [ ] Pas de message d'erreur
- [ ] 5 expandables avec status `✅`

**Résumé visuel** :
- [ ] 5 clients traités
- [ ] 5 succès
- [ ] 0 erreur

---

## 🎯 Récapitulatif Final

### Filesystem attendu après test complet

```
sandbox/BATCH_20/
├── client_01/
│   ├── sources/          ← Fichiers RAG copiés
│   ├── gold/             ← Rapport GOLD copié
│   ├── normalized/       ← source.docx alias
│   └── meta.json         ← Métadonnées
├── client_02/
│   └── ...
├── client_03/
│   └── ...
├── client_04/
│   └── ...
└── client_05/
    └── ...

output/
├── client_01_generated.docx
├── client_01_debug.json
├── client_01_metrics.json
├── client_01_gold_reference.docx
├── client_02_generated.docx
├── client_02_debug.json
├── client_02_metrics.json
├── client_02_gold_reference.docx
├── ...
└── (5 clients × 4 fichiers = 20 fichiers)
```

### Commandes Validation

```bash
# Vérifier sandbox
ls -la sandbox/BATCH_20/ | wc -l
# Attendu : 5 dossiers + . + .. = 7 lignes

# Vérifier outputs
ls -1 output/*.docx | wc -l
# Attendu : 5-10 fichiers DOCX (generated + gold_reference)

ls -1 output/*_debug.json | wc -l
# Attendu : 5 fichiers

ls -1 output/*_metrics.json | wc -l
# Attendu : 5 fichiers

# Vérifier contenu debug.json
for file in output/*_debug.json; do
    echo "=== $file ==="
    python3 -c "import json; data=json.load(open('$file')); print(f\"Chunks: {data['index']['chunks_created']}, Couverture: {data['coverage']['coverage_pct']}%\")"
done

# Vérifier métriques
for file in output/*_metrics.json; do
    echo "=== $file ==="
    python3 -c "import json; data=json.load(open('$file')); print(f\"Qualité: {data['quality_score']}, Couverture: {data['weighted_coverage']}%\")"
done
```

---

## ✅ Critères d'Acceptation Globaux

### MUST HAVE (Obligatoire)

- [x] UI accessible et fonctionnelle
- [x] Browse BATCH_20 fonctionne
- [x] Scan liste les clients avec statut
- [x] Sélection multiple (5 clients) fonctionne
- [x] Normalisation 5/5 succès
- [x] GOLD détecté OU warning clair
- [x] RAG index construit (chunks > 0)
- [x] DOCX généré (5 fichiers)
- [x] Batch affiche 5/5 success
- [x] Outputs structurés (debug.json + metrics.json)

### SHOULD HAVE (Recommandé)

- [ ] Progress bars temps réel
- [ ] Métriques visuelles (st.metric)
- [ ] Expandables détaillés
- [ ] Boutons "Ouvrir debug.json"
- [ ] Citations dans debug.json
- [ ] Confiance >= 0.5 moyenne

### NICE TO HAVE (Bonus)

- [ ] Cache RAG index
- [ ] Comparaison GOLD vs generated
- [ ] Export CSV métriques
- [ ] Visualisations (charts)

---

## 🐛 Cas d'Erreur à Tester

### Client sans GOLD

**Comportement attendu** :
- [ ] Warning : `❌ Aucun document GOLD détecté`
- [ ] Score compatibilité < 0.5
- [ ] Génération continue (pas de blocage)
- [ ] DOCX généré malgré tout
- [ ] Pas de `gold_reference.docx` dans output

### Client avec peu de sources RAG (< 3)

**Comportement attendu** :
- [ ] Warning : `⚠️ Peu de sources RAG (X)`
- [ ] Score compatibilité diminué
- [ ] Génération continue
- [ ] Couverture plus faible
- [ ] Beaucoup de "Non renseigné"

### Erreur OpenAI (pas de clé API)

**Comportement attendu** :
- [ ] Erreur claire : `❌ OpenAI API key not found`
- [ ] Message d'aide : "export OPENAI_API_KEY=..."
- [ ] Pas de crash Streamlit

---

## 📊 Métriques de Succès

### Quantitatives

- **Taux de succès** : 100% (5/5)
- **Couverture moyenne** : >= 60%
- **Qualité moyenne** : >= 0.6
- **Confiance moyenne** : >= 0.7
- **Temps moyen/client** : < 60 secondes

### Qualitatives

- **UX** : Intuitive, pas de blocage
- **Feedback** : Progress bars visibles
- **Erreurs** : Messages clairs et actionnables
- **Outputs** : Structurés et exploitables

---

## ✅ Validation Finale

**Après avoir complété toutes les étapes** :

```bash
# Script de validation automatique
cd "/Users/malik/Documents/Espace de travail/SCRIPT.IA"

echo "🔍 Validation Critères d'Acceptation..."

# 1. Sandbox
echo "\n1️⃣ Sandbox (5 clients normalisés)"
ls -la sandbox/BATCH_20/ | grep "^d" | grep -v "^\." | wc -l

# 2. GOLD détectés
echo "\n2️⃣ GOLD détectés"
ls -1 sandbox/BATCH_20/*/gold/*.docx 2>/dev/null | wc -l

# 3. RAG index (vérifier debug.json)
echo "\n3️⃣ RAG index construit"
python3 -c "
import json
from pathlib import Path
count = 0
for f in Path('output').glob('*_debug.json'):
    data = json.load(open(f))
    if data.get('index', {}).get('chunks_created', 0) > 0:
        count += 1
print(f'{count}/5 index RAG construits')
"

# 4. DOCX générés
echo "\n4️⃣ DOCX générés"
ls -1 output/*_generated.docx 2>/dev/null | wc -l

# 5. Success rate
echo "\n5️⃣ Taux de succès"
python3 -c "
import json
from pathlib import Path
success = sum(1 for f in Path('output').glob('*_metrics.json') if json.load(open(f)).get('quality_score', 0) > 0)
print(f'{success}/5 générations réussies')
"

echo "\n✅ Validation terminée"
```

**Résultat attendu** :
```
🔍 Validation Critères d'Acceptation...

1️⃣ Sandbox (5 clients normalisés)
5

2️⃣ GOLD détectés
4 ou 5

3️⃣ RAG index construit
5/5 index RAG construits

4️⃣ DOCX générés
5

5️⃣ Taux de succès
5/5 générations réussies

✅ Validation terminée
```

---

## 🎉 Definition of Done

**L'implémentation est considérée comme TERMINÉE si** :

✅ **UI fonctionnelle** : Browse → Sélection BATCH_20 → Scan OK  
✅ **Table clients** : Liste affichée avec statut  
✅ **5 clients sélectionnés** : Checkboxes fonctionnelles  
✅ **Normalisation** : 5/5 succès en sandbox  
✅ **GOLD** : Détecté OU warning clair pour chaque client  
✅ **RAG** : Index construit (chunks > 0) pour tous  
✅ **DOCX** : 5 fichiers générés  
✅ **Batch** : Message "5/5 success" affiché  
✅ **Outputs** : debug.json + metrics.json présents  
✅ **Qualité** : Métriques calculées et cohérentes  

---

**Date de validation** : 27 décembre 2025  
**Version** : 2.1.0  
**Status** : ✅ **PRÊT POUR ACCEPTATION**
