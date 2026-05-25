# Découvertes projet

> ⛔ **RÈGLE 1 — ANTI-HALLUCINATION ABSOLUE**
> Une découverte non vérifiée n'est pas une découverte. Pas d'entrée sans source factuelle.

> Géré automatiquement par Claude. Markdown vivant, pas document gravé.

## Découvertes

### Architecture & Structure

**2026-05-22 · Double point d'entrée Streamlit — piège connu**
- **Découverte :** Il existe deux façons de lancer Streamlit : `streamlit run streamlit_app.py` (correct, avec menu sidebar) vs `streamlit run pages_streamlit/training_and_test.py` (incorrect, page isolée sans nav).
- **Impact :** Erreur fréquente des utilisateurs — guide dédié dans `docs/guides/ACCES_MENU.md`
- **Source :** `docs/guides/ACCES_MENU.md`, `streamlit_app.py`

**2026-05-22 · Frontend port instable : 5173 vs 5174**
- **Découverte :** La config CORS backend (`backend/config.py`) liste localhost:3000 et localhost:5174. Le README mentionne 5173. La config startup (`start-all.sh`) attend le port 5174. Légère incohérence documentaire.
- **Impact :** Potentiel bug CORS si Vite démarre sur 5173 au lieu de 5174
- **Source :** `backend/config.py`, `README.md`, `scripts/start-all.sh`

**2026-05-22 · 31 modules Python dans core/ — séparation claire des responsabilités**
- **Découverte :** `core/` contient l'ensemble du pipeline métier découplé du backend HTTP. Chaque étape est un module distinct (extract, generate, render, export, field_specs, instructions, etc.). Testable indépendamment.
- **Impact :** Architecture saine pour les tests unitaires — 77 fichiers de tests couvrent core/ + backend/
- **Source :** listing `core/*.py`

**2026-05-22 · `rapport_orchestrator.py` à la racine — point d'entrée principal du pipeline**
- **Découverte :** Le fichier `rapport_orchestrator.py` (racine) orchestre tout : PipelineConfig, PipelineResult, résolution chemins, slugify filenames. C'est lui que les workers RQ appellent.
- **Impact :** Toute modification du workflow de génération passe par ce fichier
- **Source :** `rapport_orchestrator.py`

### LLM & Génération

**2026-05-22 · llm_router.py — abstraction LLM unifiée**
- **Découverte :** `core/generate.py` utilise `llm_router.py` comme couche d'abstraction (Ollama vs OpenAI). `ollama_generate()` appelle le router, pas directement l'API Ollama.
- **Impact :** Changement de provider LLM sans modifier le pipeline — mais router.py non exploré dans ce scan
- **Source :** `core/generate.py` (import lazy de llm_router)

**2026-05-22 · Temperature 0.1–0.2 par défaut, 0.0 pour champs factuels**
- **Découverte :** Les paramètres LLM sont définis dans `core/instructions.md` (spec) et `PipelineConfig` (runtime). Température basse imposée pour réduire la variance/hallucination.
- **Impact :** Rapports reproductibles et cohérents entre runs
- **Source :** `core/instructions.md`, `rapport_orchestrator.py`

**2026-05-22 · PROFESSION — champ immutable après première génération**
- **Découverte :** Dans `field_specs_v3.py`, le champ PROFESSION a `immutable=True`. Une fois généré, il ne doit plus changer lors des regénérations partielles.
- **Impact :** Logique de skip à implémenter côté orchestrator si non déjà présente
- **Source :** `core/field_specs_v3.py`

**2026-05-22 · Validation accent-insensitive des keywords (fix récent)**
- **Découverte :** Commit `f4c2050` — fix de l'évaluation : les keywords de détection des required_elements sont maintenant comparés sans accents (ex : "compétences" = "competences").
- **Impact :** Réduction des faux négatifs dans les quality gates
- **Source :** commit `f4c2050`

### Données & Clients

**2026-05-22 · 26 répertoires CLIENTS/ dans le repo**
- **Découverte :** `CLIENTS/` contient les dossiers de 26 clients. Ces données (PDF, DOCX, MSG) sont potentiellement sensibles. `.gitignore` gère l'exclusion des fichiers de données client — à vérifier.
- **Impact :** Risque de fuite accidentelle si `.gitignore` mal configuré
- **Source :** listing du répertoire CLIENTS/

**2026-05-22 · Métadonnées par document : mtime ISO + SHA256**
- **Découverte :** `core/extract.py` génère pour chaque fichier extrait un SHA256 + timestamp mtime ISO. Permet de détecter les changements entre runs.
- **Impact :** Fondement pour un cache d'extraction incrémentiel si implémenté
- **Source :** `core/extract.py`

### Tests & Qualité

**2026-05-22 · 77 fichiers de tests — coverage tests/integration inclus**
- **Découverte :** Le répertoire `tests/` contient 77 fichiers de tests couvrant : API, audio RAG, batch, DOCX, validation, end-to-end, field specs V3, quality gates, training state.
- **Impact :** Base solide pour le CI — mais aucun pipeline CI configuré (déploiement 100% manuel)
- **Source :** listing `tests/`

**2026-05-22 · Ruff + Black + MyPy configurés dans pyproject.toml**
- **Découverte :** Outils de qualité de code configurés : Black (line-length 120), Ruff (linting), MyPy (types). Pre-commit hooks présents (`.pre-commit-config.yaml`).
- **Impact :** Code style homogène ; hooks actifs si installés (`pre-commit install`)
- **Source :** `pyproject.toml`

### Fonctionnalités Avancées

**2026-05-22 · faster-whisper intégré pour RAG audio**
- **Découverte :** `faster-whisper>=1.0.3` dans requirements.txt. Routes `rag_audio` dans le backend. Transcription audio locale (modèle Whisper small par défaut, max 300s).
- **Impact :** Fonctionnalité avancée — audio d'entretiens transformé en sources pour le pipeline RAG
- **Source :** `requirements.txt`, `backend/config.py` (AUDIO_WHISPER_MODEL), `backend/main.py`

**2026-05-22 · src/rhpro/ — 15 modules spécialisés RH Pro**
- **Découverte :** `src/rhpro/` contient batch_runner, identity_extractor, docx_structure, mapper, ruleset_loader et 10+ autres modules dédiés à l'analyse RH Pro. Distinct de `core/`.
- **Impact :** Pipeline RH Pro parallèle au pipeline principal — formation, analyse batch, règles métier
- **Source :** listing `src/rhpro/`

**2026-05-22 · Bouton "nuke" — reset agressif de l'environnement**
- **Découverte :** Commit `37de57d` — un bouton "nuke" a été ajouté : kill workers, LLM, flush Redis, relance propre. Route admin dédiée dans le backend.
- **Impact :** Outil de debug/reset pour état bloqué — usage prod à encadrer
- **Source :** commit `37de57d`, `backend/api/routes/admin.py` (présumé)

**2026-05-22 · Branding DOCX — remplacement logo + couleurs par client**
- **Découverte :** Module `docx_branding.py` dans core + route `/branding` dans le backend. Pillow utilisé pour le traitement d'images (logos). Page "Branding" dans le frontend React.
- **Impact :** Personnalisation visuelle du rapport par client sans retouche manuelle du template
- **Source :** `requirements.txt` (pillow), `backend/main.py` (router branding), `frontend/src/pages/`

### Beyond-RAG / SKI — Couche de connaissance structurée

#### 2026-05-25 · Socle SKI implémenté — knowledge_builder + context_builder + templates QMD

- **Découverte :** Implémentation complète du socle Beyond-RAG (Structured Knowledge Injection). Deux nouveaux modules dans `core/` + 8 templates QMD + intégration dans l'orchestrateur + feature flag.
- **Architecture :** `extract.py` → `knowledge_builder.py` → `_knowledge/*.md` (Markdown+YAML) → `context_builder.py` → contexte structuré → `generate.py` (prompt LLM amélioré)
- **Impact :** Contexte LLM ciblé par section (~3000 chars) au lieu du dump BM25 brut (4000-8000 chars). Cache incrémentiel SHA256 : rebuild uniquement si fichier source modifié. Feature flag `KNOWLEDGE_LAYER_ENABLED=False` par défaut — pipeline existant inchangé quand désactivé.
- **Tests :** 55 tests verts (25 knowledge_builder + 21 context_builder + 9 non-régression) — 0.92s
- **Source :** `core/knowledge_builder.py`, `core/context_builder.py`, `templates/qmd/`, `backend/config.py`, `rapport_orchestrator.py`, `core/generate.py`

#### 2026-05-25 · Format de stockage `_knowledge/` — compatible Obsidian, non dépendant

- **Découverte :** Les notes générées par `knowledge_builder.py` sont stockées dans `CLIENTS/<client>/_knowledge/` au format Markdown + YAML frontmatter. Fichier `_meta.json` pour le cache SHA256. Structure compatible avec l'app Obsidian mais exploitable sans elle.
- **Impact :** Types de notes identifiés : `01-cv.md`, `02-lettre.md`, `03-formations.md`, `04-entretien-audio.md`, `05-messages.md`, `06-autres.md`. Classification par patterns regex sur le nom de fichier + extension `.msg` + chemin `ingested_audio/`.
- **Source :** `core/knowledge_builder.py` (`NOTE_FILENAMES`, `_TYPE_PATTERNS`)
