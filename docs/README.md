# 📚 Documentation SCRIPT.IA - Consolidée

**Date consolidation** : 28 décembre 2025  
**Structure finale** : 4 documents principaux

---

## 🎯 Organisation

Cette documentation est maintenant structurée en **4 fichiers principaux** :

### 1. [HISTORIQUE_IMPLEMENTATION.md](HISTORIQUE_IMPLEMENTATION.md)
**Objectif** : Historique chronologique de toutes les implémentations

**Contenu** :
- Session 28 déc 2025 : Fix 5, 6, 7 + Support .msg
- Versions antérieures (V4.1, V4.0, V3.0, V2.0, V1.0)
- Patch notes détaillés
- Roadmap futur
- Statistiques globales

**Usage** : Consulter pour comprendre l'évolution du projet, tracer les décisions architecturales

---

### 2. [GUIDE_TRAINING.md](GUIDE_TRAINING.md)
**Objectif** : Guide complet module Training (analyse dataset clients)

**Contenu** :
- Quickstart (Mode Test / Mode Batch)
- Concepts clés (scan_depth, limite, merge)
- Structure training_state.json (schéma v1.0)
- Détection GOLD (AVS, structure)
- Analyse stats (coverage, p90)
- Workflow recommandé
- Métriques succès

**Usage** : Pour tout ce qui concerne l'analyse de dataset et la génération de patterns

---

### 3. [GUIDE_GENERATION.md](GUIDE_GENERATION.md)
**Objectif** : Guide pipeline complète génération bilans

**Contenu** :
- Extraction multi-format (PDF/DOCX/TXT/DOC/MSG)
- Indexation RAG (LlamaIndex)
- Génération LLM (prompt engineering)
- Validation (champs, formats, longueurs)
- Rendu DOCX (branding, placeholders)
- Configuration avancée
- Optimisations performance
- Troubleshooting

**Usage** : Pour comprendre la pipeline end-to-end de génération

---

### 4. [API_REFERENCE.md](API_REFERENCE.md)
**Objectif** : Documentation technique complète API Python

**Contenu** :
- Architecture modules (core/, src/rhpro/, backend/)
- API core.extract (extract_sources, extract_msg, etc.)
- API core.generate (generate_bilan, generate_field)
- API core.context (build_rag_index, RAG)
- API src.rhpro.dataset_training (analyze_client_dataset, merge)
- API src.rhpro.production_gate (ProductionGate, scoring)
- Backend API REST (FastAPI endpoints)
- Configuration & variables env
- Tests & fixtures
- Types & schemas

**Usage** : Référence technique pour développeurs, intégration API

---

## 📊 Statistiques Consolidation

### Avant
- **Total fichiers .md** : 68 dans docs/ + 7 à la racine = **75 fichiers**
- **Problèmes** : 
  - Duplication (QUICKSTART x5, SUMMARY x8)
  - Fragmentation (BATCH_*, TRAINING_*, MSG_*)
  - Maintenance complexe
  - Navigation difficile

### Après
- **Total fichiers .md actifs** : **4 fichiers** dans docs/
- **Fichiers archivés** : 69 dans docs/archive/
- **Gain** :
  - ✅ 94% réduction (75 → 4)
  - ✅ Structure claire par thématique
  - ✅ Pas de duplication
  - ✅ Maintenance simplifiée

### Contenu
- **Lignes totales** : 2376 lignes (consolidées, sans duplication)
- **HISTORIQUE_IMPLEMENTATION.md** : 284 lignes
- **GUIDE_TRAINING.md** : 513 lignes
- **GUIDE_GENERATION.md** : 653 lignes
- **API_REFERENCE.md** : 926 lignes

---

## 🔍 Trouver l'Information

### "Comment utiliser le Training ?"
→ [GUIDE_TRAINING.md](GUIDE_TRAINING.md)

### "Comment extraire des emails .msg ?"
→ [GUIDE_GENERATION.md](GUIDE_GENERATION.md) (section Extraction MSG)

### "Quelle API pour merge_training_states() ?"
→ [API_REFERENCE.md](API_REFERENCE.md) (section src.rhpro.dataset_training)

### "Quand le support .msg a-t-il été ajouté ?"
→ [HISTORIQUE_IMPLEMENTATION.md](HISTORIQUE_IMPLEMENTATION.md) (session 28 déc 2025)

### "Comment configurer LLM temperature ?"
→ [GUIDE_GENERATION.md](GUIDE_GENERATION.md) (section Configuration Avancée)  
ou [API_REFERENCE.md](API_REFERENCE.md) (section Configuration)

---

## 📁 Archive

Les 69 anciens fichiers markdown sont dans **docs/archive/** :

```
docs/archive/
├── BATCH_*.md (10 fichiers)
├── TRAINING_*.md (8 fichiers)
├── MSG_SUPPORT_*.md (5 fichiers)
├── FIX_*.md (4 fichiers)
├── PRODUCTION_GATE_*.md (6 fichiers)
├── REAL_TRAINING_*.md (3 fichiers)
├── DATASET_*.md (4 fichiers)
├── LIVRAISON_*.md (3 fichiers)
└── ... (26 autres fichiers)
```

**Conservation** : Archivés pour historique, mais **ne plus maintenir**.

**Si besoin** : Le contenu pertinent a été migré dans les 4 docs principaux.

---

## 🔄 Maintenance

### Mise à jour Documentation

**Règle** : Toujours mettre à jour **1 seul fichier** parmi les 4.

**Exemples** :

| Changement | Fichier à éditer |
|------------|-----------------|
| Nouveau fix/patch | HISTORIQUE_IMPLEMENTATION.md |
| Nouveau paramètre training | GUIDE_TRAINING.md |
| Nouveau format extraction | GUIDE_GENERATION.md |
| Nouvelle API/fonction | API_REFERENCE.md |

**Interdiction** : Ne PAS créer de nouveaux .md fragmentés (BATCH_QUICKSTART_V2.md, etc.)

### Versioning

- **Version** : Synchronisée avec version projet (actuellement v4.1)
- **Dernière mise à jour** : Indiquer date en haut de chaque fichier
- **Changelog** : Ajouter entrée dans HISTORIQUE_IMPLEMENTATION.md

---

## ✅ Validation

### Checklist avant commit

- [ ] Les 4 fichiers principaux existent
- [ ] Pas de duplication entre fichiers
- [ ] Chaque fichier a une version + date à jour
- [ ] Les liens internes fonctionnent
- [ ] Contenu archivé non modifié

### Tests rapides

```bash
# Vérifier structure
ls -lh docs/*.md

# Compter lignes
wc -l docs/*.md

# Vérifier pas de nouveaux .md fragmentés
find docs/ -maxdepth 1 -name "*.md" | wc -l  # Doit être 4 (+1 ce README)

# Vérifier archive
ls docs/archive/ | wc -l  # Doit être 69
```

---

## 🎯 Principes

### 1. Un seul point d'entrée par thématique
- Training → GUIDE_TRAINING.md
- Génération → GUIDE_GENERATION.md
- API → API_REFERENCE.md
- Historique → HISTORIQUE_IMPLEMENTATION.md

### 2. Pas de fragmentation
- ❌ BATCH_QUICKSTART.md + BATCH_SUMMARY.md + BATCH_GUIDE.md
- ✅ GUIDE_TRAINING.md (section Batch)

### 3. Liens internes
- Utiliser liens relatifs entre docs
- Exemple : `[GUIDE_TRAINING.md](GUIDE_TRAINING.md)`

### 4. Contenu actionnable
- Exemples code concrets
- Commandes exécutables
- Troubleshooting pratique

---

**Maintenu par** : Équipe SCRIPT.IA  
**Dernière revue** : 28 décembre 2025
