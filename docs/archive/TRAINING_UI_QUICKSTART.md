# 🚀 Training & Test UI - Guide Démarrage Rapide

## Objectif

Piloter l'entraînement dataset et le test de clients RH-Pro **depuis le navigateur** (sans terminal).

---

## Démarrage en 3 étapes

### 1. Lancer l'interface Streamlit

```bash
cd "/Users/malik/Documents/Espace de travail/SCRIPT.IA"
streamlit run streamlit_app.py
```

→ Navigateur s'ouvre sur `http://localhost:8501`

### 2. Navigation

Dans le menu latéral, cliquer sur **🎓 Training & Test**

### 3. Choisir l'onglet

- **📚 Entraîner Dataset** : analyser un dataset complet
- **🧪 Test Client** : tester un client individuel

---

## 📚 Onglet "Entraîner Dataset"

### Workflow en 4 clics

1. **Sélectionner dataset racine**
   - Cliquer "📁 Browse" ou coller le chemin
   - Exemples :
     - `CLIENTS` (1 client test)
     - `DATASET TRAINING/BATCH 20` (20 clients organisés)
     - `/path/to/580_dossiers` (structure hétérogène)

2. **Configurer** (optionnel)
   - **Profondeur scan** : 3 (défaut, augmenter si dossiers profonds)
   - **Limite clients** : 0 = tous, ou 5 pour test rapide
   - **Merge existant** : fusionner avec training précédent (incrémental)
   - **Dossier sortie** : `output/training` (défaut)

3. **Cliquer "🚀 Lancer Entraînement"**
   - ⏳ Analyse en cours (2-10 min selon nb clients)
   - 3 étapes : Découverte → Analyse → Export

4. **Consulter résultats**
   - **Métriques** : clients analysés, GOLD détectés, pipeline ready
   - **Sections** : FORMATION, PROFESSION, etc. (coverage % + lignes avg/p50/p90)
   - **Profils** : STRICT/STANDARD/DRAFT (seuils)
   - **Warnings** : .msg non indexés, etc.
   - **📥 Télécharger** : `training_state.json` + `training_report.md`

### Résultat attendu

✅ Fichier **training_state.json v1.0** prêt à utiliser pour améliorer la génération RAG

---

## 🧪 Onglet "Test Client"

### Workflow en 6 clics

1. **Sélectionner dataset racine**
   - Même dataset que pour l'entraînement
   - Exemples : `CLIENTS`, `DATASET TRAINING/BATCH 20`, `/path/to/580_dossiers`

2. **Rechercher un client**
   - 🔎 Barre de recherche : taper "AYNE" ou "KARAOUI" ou "Michael"
   - Liste filtrée alphabétiquement
   - Sélectionner le client dans la liste déroulante

3. **Charger training_state.json** (optionnel mais recommandé)
   - Cliquer "📁 Browse" ou coller le chemin
   - Utilise le dernier généré (onglet Entraînement)
   - Si absent : utilise defaults basiques

4. **Choisir profil de validation**
   - **STRICT** : production RH-Pro (coverage ≥ 85%, quality ≥ 0.75)
   - **STANDARD** : acceptable (coverage ≥ 75%, quality ≥ 0.65) ⭐ recommandé
   - **DRAFT** : brouillon (aucun seuil)

5. **Cliquer "▶️ Run Pipeline Complet"**
   - ⏳ 4 étapes automatiques :
     1. **Scan** : détection sources + GOLD
     2. **Normalisation** : copie vers sandbox
     3. **Génération** : RAG + DOCX (LLM Claude)
     4. **Validation** : calcul GO/NO_GO/DRAFT

6. **Consulter résultats**
   - **Status** : GO ✅ / NO_GO ❌ / DRAFT ⚠️
   - **Scores** : Coverage, Quality, Confidence
   - **Raisons** : pourquoi GO/NO_GO
   - **Actions** : recommandations d'amélioration
   - **📥 Télécharger** : DOCX + Metrics + Debug + Validation (JSON)

### Résultat attendu

✅ Rapport DOCX généré + Validation GO/NO_GO/DRAFT + Fichiers JSON pour analyse

---

## 🎯 Cas d'usage typiques

### Cas 1 : Entraîner sur BATCH 20 (20 clients organisés)

```
1. Onglet "📚 Entraîner Dataset"
2. Dataset racine: DATASET TRAINING/BATCH 20
3. Limite clients: 0 (tous)
4. 🚀 Lancer
5. ⏳ ~2-5 min
6. 📥 Télécharger training_state.json
```

→ **Résultat** : training_state.json avec patterns de 20 clients

### Cas 2 : Entraîner sur 580 dossiers non rangés

```
1. Onglet "📚 Entraîner Dataset"
2. Dataset racine: /path/to/580_dossiers
3. Profondeur scan: 5 (structure profonde)
4. Limite clients: 0 (tous)
5. 🚀 Lancer
6. ⏳ ~10-20 min
7. 📥 Télécharger training_state.json
```

→ **Résultat** : training_state.json avec patterns de 580 clients

### Cas 3 : Test rapide sur client "AYNE Michael"

```
1. Onglet "🧪 Test Client"
2. Dataset racine: CLIENTS (ou autre)
3. 🔎 Rechercher: "AYNE"
4. Sélectionner: AYNE Michael
5. Training state: (utiliser le dernier généré)
6. Profil: STANDARD
7. ▶️ Run Pipeline
8. ⏳ ~30-60 sec
9. ✅ Consulter status GO/NO_GO
10. 📥 Télécharger DOCX + JSON
```

→ **Résultat** : Rapport DOCX + Status validation

### Cas 4 : Tester tous les clients d'un BATCH (validation batch)

Répéter Cas 3 pour chaque client, ou utiliser l'onglet **📊 Validation Batch** (déjà existant dans le menu).

---

## ⚡ Tips & Astuces

### Performance

- **Test rapide** : limiter à 5 clients (`limit=5`)
- **Production** : laisser `limit=0` pour analyser tous les clients
- **Scan profond** : augmenter `scan_depth` si dossiers très imbriqués (max 5)

### Recherche de clients

- **Par nom** : "AYNE", "KARAOUI", "Michael"
- **Sensibilité** : insensible à la casse
- **Tri** : liste alphabétique automatique

### Training state

- **Réutilisable** : un training_state.json peut servir pour plusieurs tests
- **Incrémental** : option "Merge existant" pour enrichir un training existant
- **Versioning** : run_id unique par run (ex: `BATCH20_2025-12-27T19:32:37Z_ab12cd`)

### Profils de validation

| Profil     | Coverage min | Quality min | Confidence min | Usage                          |
|------------|--------------|-------------|----------------|--------------------------------|
| **STRICT** | 85%          | 0.75        | 0.70           | Production RH-Pro (exigeant)   |
| **STANDARD** | 75%        | 0.65        | 0.60           | Acceptable (recommandé ⭐)     |
| **DRAFT**  | 0%           | 0.0         | 0.0            | Brouillon (pas de seuil)       |

---

## 🐛 Dépannage

### "Aucun client détecté"

**Problème** : Le dataset ne contient pas de dossiers exploitables.

**Solutions** :
- Augmenter `scan_depth` (3 → 5)
- Vérifier que les dossiers contiennent au moins 2 fichiers .docx/.pdf/.txt/.doc
- Vérifier le chemin absolu du dataset

### "Erreur génération DOCX"

**Problème** : RapportOrchestrator n'a pas réussi à générer le rapport.

**Solutions** :
- Vérifier que le template DOCX existe
- Vérifier la clé API Claude (Anthropic)
- Consulter `*_debug.json` pour détails
- Vérifier les logs Streamlit dans le terminal

### "Training state non valide"

**Problème** : Le fichier training_state.json est corrompu ou incomplet.

**Solutions** :
- Régénérer depuis l'onglet "Entraîner Dataset"
- Vérifier le schéma JSON (voir `docs/TRAINING_UI_IMPLEMENTATION.md`)
- Vérifier que le fichier n'a pas été édité manuellement

### "Status NO_GO alors que le rapport semble bon"

**Problème** : Le profil de validation est trop strict.

**Solutions** :
- Utiliser profil **STANDARD** au lieu de STRICT
- Consulter les "Raisons" et "Actions recommandées" dans les résultats
- Vérifier les champs critiques manquants (nom, prénom, profession/formation)

---

## 📞 Support

Pour toute question ou problème :

1. **Consulter la doc complète** : `docs/TRAINING_UI_IMPLEMENTATION.md`
2. **Consulter les logs** :
   - Terminal Streamlit : logs en temps réel
   - `output/training/*/training_report.md` : rapport d'entraînement
   - `output/test_client/*_debug.json` : logs de génération
   - `output/test_client/*_validation.json` : détails validation

---

## 🎉 C'est parti !

```bash
streamlit run streamlit_app.py
```

→ Menu **🎓 Training & Test**

→ Onglet **📚 Entraîner Dataset** ou **🧪 Test Client**

→ Suivre les workflows ci-dessus

**Bon entraînement et bon test ! 🚀**
