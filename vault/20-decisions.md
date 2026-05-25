# Décisions projet

> ⛔ **RÈGLE 1 — ANTI-HALLUCINATION ABSOLUE**
> Une décision non vérifiée n'est pas une décision. Pas d'entrée sans source factuelle.

> Géré automatiquement par Claude. Markdown vivant, pas document gravé.

## Décisions durables

### Architecture & Pipeline

**2025 (visible dans git log) · Architecture pipeline**
- **Décision :** Pipeline en 4 étapes séquentielles : extract → build_context (RAG) → generate_fields (LLM) → render_docx
- **Conséquence :** Chaque étape est découplée, testable indépendamment ; les erreurs LLM n'impactent pas l'extraction
- **Source :** `core/instructions.md`, `rapport_orchestrator.py`
- **À revalider si :** changement de paradigme LLM (streaming temps réel, agents)

**2025 · Traitement asynchrone via RQ + Redis**
- **Décision :** Tout job de génération passe par Redis Queue (RQ workers), pas d'appel LLM synchrone côté API
- **Conséquence :** L'UI peut se connecter par SSE pour suivre la progression ; tolérance aux timeouts LLM (120s+)
- **Source :** `backend/api/routes/reports.py`, `scripts/start_worker.py`, `scripts/start-all.sh`
- **À revalider si :** migration vers Celery ou streaming natif FastAPI

**2025 · Double UI : React + Streamlit**
- **Décision :** Maintien des deux interfaces — React (frontend moderne, prod) + Streamlit (legacy multi-pages, exploration)
- **Conséquence :** Deux ports différents (5173/5174 vs 8501), risque de confusion ; Streamlit = entrée via `streamlit_app.py` (pas les pages isolées)
- **Source :** `docs/guides/ACCES_MENU.md`, `streamlit_app.py`, `frontend/`
- **À revalider si :** abandon Streamlit décidé

### LLM & Qualité

**2025 · Anti-hallucination stricte — champ vide plutôt qu'inventé**
- **Décision :** Si le LLM produit du JSON, des placeholders `{{...}}`, des tokens `XX`/`NAME`, ou invente des données → champ vide + log. Un seul retry avec prompt "text-only, no JSON".
- **Conséquence :** Rapports plus courts mais fiables ; debug JSON per-field systématique
- **Source :** `core/generate.py` (RE_JSON, RE_FORBIDDEN_PLACEHOLDERS, RE_FORBIDDEN_TOKENS), `core/instructions.md`
- **À revalider si :** modèle LLM plus fiable adopté

**2025 · LLM local Ollama (qwen3-next:latest) comme défaut**
- **Décision :** Ollama local, modèle qwen3-next:latest par défaut. Support OpenAI via llm_router.py mais pas le chemin principal.
- **Conséquence :** Confidentialité des données clients garantie (pas de cloud) ; dépendance Ollama installé localement
- **Source :** `backend/config.py` (OLLAMA_MODEL=qwen3-next:latest), `core/generate.py`
- **À revalider si :** migration vers un modèle cloud décidée

**commit d7088fd · V3 field specs — 7 sections avec required_elements**
- **Décision :** Passage à field_specs_v3 avec sections structurées, required_elements validés par keywords, immutabilité PROFESSION après première génération
- **Conséquence :** Quality gate per-section possible (BON/A_REVOIR/VIDE) ; specs plus lourdes mais traçables
- **Source :** `core/field_specs_v3.py`, `core/report_types.py`
- **À revalider si :** nouveau type de rapport ajouté

**commit d7088fd · Quality gate : section_evaluator**
- **Décision :** Évaluation automatique par section (BON/A_REVOIR/VIDE) via détection de keywords accent-insensitive
- **Conséquence :** UI review en 3 colonnes (liste sections / texte / évaluation + actions) ; transparence sur la qualité
- **Source :** `backend/api/routes/review.py`, commits `f4c2050`, `93f75f0`
- **À revalider si :** critères d'évaluation affinés ou modèle de scoring LLM adopté

### Extraction & Sources

**2026-05-25 · Couche de connaissance client compatible Obsidian, mais non dépendante**
- **Décision :** La future brique d'indexation client repose sur des fichiers Markdown + YAML frontmatter + manifests JSON compatibles Obsidian. Obsidian n'est ni le cœur runtime du système, ni un outil destiné au client final.
- **Conséquence :** Le pipeline doit fonctionner sans Obsidian installé. Cette base de connaissance amont sert d'abord à améliorer la fiabilité, la robustesse, la vitesse et la pertinence du traitement des données, puis pourra être réutilisée pour plusieurs usages : rapports, questions ciblées sur un client, comptes rendus à la volée.
- **Source :** `docs/plans/2026-05-25-beyond-rag-obsidian-qmd.md`, demande utilisateur du 2026-05-25
- **À revalider si :** un autre contrat de stockage plus simple ou plus robuste remplace le couple Markdown/YAML/JSON

#### 2026-05-25 · Beyond-RAG — Socle SKI livré, feature flag désactivé par défaut

- **Décision :** Le socle SKI (Structured Knowledge Injection) est implémenté dans `core/knowledge_builder.py` + `core/context_builder.py` + `templates/qmd/`. Il est désactivé par défaut (`KNOWLEDGE_LAYER_ENABLED=False`) pour ne pas impacter le pipeline existant. Activation via `PipelineConfig.knowledge_layer_enabled=True` ou variable d'env.
- **Conséquence :** Quand activé : chaque dossier client génère un `_knowledge/` avec des notes Markdown+YAML structurées par type (cv, lettre, formation, entretien, msg). `generate.py` reçoit un contexte structuré ciblé par section en plus des chunks BM25. 55 tests verts couvrent la couche.
- **Source :** `core/knowledge_builder.py`, `core/context_builder.py`, `rapport_orchestrator.py`, `backend/config.py`, `tests/test_knowledge_builder.py`, `tests/test_context_builder.py`, `tests/test_beyond_rag_nonregression.py`
- **À revalider si :** mesures A/B montrent gain insuffisant, ou si le format Markdown+YAML est remplacé par un autre contrat de stockage

**2025 · Extraction multi-format : PDF/DOCX/TXT/MSG + LibreOffice pour legacy**
- **Décision :** Support natif PDF (PyMuPDF), DOCX (python-docx), TXT, MSG (extract-msg). Formats legacy (.doc, .rtf, .odt) via LibreOffice système.
- **Conséquence :** LibreOffice = dépendance système non gérée par pip ; extraction MSG optionnelle (graceful degradation)
- **Source :** `core/extract.py`, `core/extractors/msg_extractor.py`
- **À revalider si :** ajout format XLSX, HTML ou audio sans Whisper

### Sécurité

**2025 · JWT HS256 — auth locale simple**
- **Décision :** Authentification JWT HS256, 60 minutes d'expiration, login admin/admin123 par défaut
- **Conséquence :** Suffisant pour usage local/interne ; insécurisé pour exposition internet sans changement SECRET_KEY
- **Source :** `backend/config.py`, `backend/api/routes/auth.py`
- **À revalider si :** déploiement externe ou multi-utilisateurs réels
