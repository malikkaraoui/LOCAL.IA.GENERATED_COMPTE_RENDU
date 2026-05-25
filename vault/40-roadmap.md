# Roadmap vivante

> Géré automatiquement par Claude. Markdown vivant, pas document gravé.

## Livré ✅

*(basé sur git log — branch dev, commits visibles au 2026-05-22)*

- ✅ **V3 field specs rapport_initial** (7 sections, required_elements, keywords) — commit `4d1c571`
- ✅ **Registry report types** (rapport_initial + 3 standby) — commit `3d712fe`
- ✅ **Section evaluator** (quality gate BON/A_REVOIR/VIDE) — commit `d7088fd`
- ✅ **Wire V3 field specs via report_type param** dans generate_fields — commit `941e92d`
- ✅ **Review API endpoints** (report-types, review, edit, regenerate, export) — commit `3544d89`
- ✅ **Report type dropdown + redirect review page** — commit `895ae11`
- ✅ **ReportReview page** (layout 3 colonnes) — commit `93f75f0`
- ✅ **Pipeline LLM robuste + UI Swiss Style + transparence review** — commit `c8d6bca`
- ✅ **Test intégration V3 rapport initial pipeline** — commit `a89eab6`
- ✅ **Bouton nuke agressif** (kill workers, LLM, flush Redis, relance propre) — commit `37de57d`
- ✅ **Fix evaluation accent-insensitive + keywords enrichis + layout 2 colonnes** — commit `f4c2050`
- ✅ **Fix remplissage placeholders DOCX export + doc config LLM** — commit `0d272e6` *(dernier commit)*
- ✅ **Schema V2 (53 champs) + anti-hallucination + nettoyage rendu DOCX** — commit `b5fab57`
- ✅ **Nettoyage documentation** (suppression 45 fichiers obsolètes) — commit `b5fab57`
- ✅ **pyproject.toml editable install + suppression sys.path.insert** — commit `b8fd1a2`
- ✅ **Audio RAG via faster-whisper** — intégré dans requirements + routes backend
- ✅ **Branding DOCX par client** (logo + couleurs) — module core + route backend
- ✅ **Authentification JWT** (admin/admin123 par défaut) — backend/auth
- ✅ **FileBrowser React** — composant de navigation fichiers clients
- ✅ **Script start-all.sh** — démarrage orchestré de tous les services
- ✅ **Socle SKI / Beyond-RAG** — `knowledge_builder.py` + `context_builder.py` + templates QMD + feature flag `knowledge_layer_enabled` + tests ciblés

## Sur le feu 🔥

*(pas de branche WIP visible hormis `dev` — basé sur les indices dans les commits récents)*

- Stabilisation du remplissage placeholders DOCX (dernier commit fix) — potentiellement incomplet
- Vérifier la cohérence port frontend 5173 vs 5174 (CORS config vs README)
- Couverture de tests — 77 fichiers, mais CI non configurée
- Activer `knowledge_layer_enabled=True` sur 1 client réel et mesurer le delta quality gate BON/A_REVOIR avant vs après

## Ensuite 📋

*(non planifié formellement — inférences prudentes à partir du code existant)*

- CI/CD : aucun pipeline configuré — mise en place GitHub Actions ou équivalent
- Complétion du support multi-report-types (3 types en standby non implémentés)
- Gestion multi-utilisateurs (auth multi-comptes, pas seulement admin)
- Documentation utilisateur finale (guides `docs/guides/` partiels)

## Architecture future 🔭

**Beyond-RAG — couche de connaissance compatible Obsidian + QMD** *(étude complète → `docs/plans/2026-05-25-beyond-rag-obsidian-qmd.md`)*

Remplacement du RAG naïf (dump texte brut) par un système de connaissance structurée :

- **Format compatible Obsidian** : chaque dossier client devient une base de connaissance en `.md` + YAML + manifests JSON ; Obsidian reste interne et optionnel
- **QMD (Quarto Markdown)** : templates de contexte par section de rapport → contexte ciblé 1500-2500 tokens
- **SKI (Structured Knowledge Injection)** : remplace la recherche aléatoire par une injection de contexte structuré
- Objectif produit : données amont plus fiables, plus résistantes, plus rapides à exploiter et plus pertinentes
- Réutilisation future : rapport aujourd'hui, questions ciblées sur un client et compte rendu à la volée demain
- Gain estimé : -50 % de tokens, +30 % de pertinence, traçabilité complète des contextes

Phases : Phase 0 (templates QMD) → Phase 1 (indexation client) → Phase 2 (context_builder) → Phase 3 (réutilisation des données) → Phase 4 (graphe optionnel)
Décision active : construire d'abord le socle utile d'indexation client ; enrichissement graphe seulement après validation du ROI

Hors scope du lot livré : `graph_builder.py`, UI/frontend, fine-tuning, questions/réponses client et compte rendu à la volée

## Parking 🅿️

*(idées non planifiées — à challenger)*

- Docker / docker-compose pour simplifier l'installation
- Export PDF via service cloud (alternative LibreOffice système)
- Interface mobile (Streamlit ou React responsive)
- Déploiement cloud (Fly.io, Render, etc.) — actuellement 100% local
