# SCRIPT.IA — Copilot Instructions — Étape 2 (Training Async via RQ + Redis)

## Objectif
Transformer le module `training` d’un stub synchrone (réponse immédiate `done`) vers un pipeline **asynchrone** :
- POST `/api/training/start` : crée un `job_id`, enregistre statut `queued`, enfile un job RQ, répond immédiatement.
- GET `/api/training/{job_id}/status` : renvoie le statut courant depuis Redis (queued/running/done/error) + message + progress.
- Worker RQ : exécute le job et met à jour les statuts pendant l’exécution.
- Frontend `/training` : déclenche start puis **poll** status jusqu’à `done`/`error`, affiche logs.

## Contraintes & principes
- Réutiliser les patterns existants du projet (ex: `reports.py`, `rag_audio.py`) : mêmes conventions de routes, services, gestion d’erreur.
- Ne pas ajouter de complexité inutile : **Redis comme source de vérité** pour les statuts, RQ pour l’exécution.
- Pas de “vrai entraînement LLM” : on simule une analyse (sleep + étapes) pour valider l’architecture.
- Le code doit être modulaire :
  - `routes` = HTTP
  - `jobs`/`workers` = exécution background
  - `services` = logique partagée
  - `storage`/`redis` = accès Redis
- Gestion d’erreurs propre : si exception dans le worker → statut `error` + message.

## Backend — Modifs attendues

### 1) Statuts en Redis
Créer une petite couche utilitaire (si non existante) :
- clé : `training:{job_id}`
- valeur JSON : `{ "job_id": str, "status": "queued|running|done|error", "message": str, "progress": int, "updated_at": iso }`

Fonctions minimales :
- `set_training_status(job_id, status, message=None, progress=None)`
- `get_training_status(job_id) -> dict|None`

Utiliser le client Redis déjà présent dans le projet (ne pas dupliquer 10 connexions).

### 2) POST `/api/training/start`
Comportement voulu :
- Valider payload (pydantic déjà en place).
- Générer `job_id` (uuid ou hex).
- `set_training_status(job_id, "queued", "Job queued", progress=0)`
- Enqueue via RQ : `training_job(job_id, payload_dict)`
- Répondre `{"job_id": job_id, "status": "queued"}`

Important :
- Ne pas renvoyer `done` immédiatement.
- Retour HTTP 200 OK (ou 202 Accepted si le projet préfère, mais rester cohérent).

### 3) GET `/api/training/{job_id}/status`
- Lire Redis.
- Si absent → 404 JSON `{"detail":"job_id not found"}`
- Sinon renvoyer : `{"job_id":..., "status":..., "message":..., "progress":...}`

### 4) Worker / Job RQ
Créer un job exécutable par le worker RQ (ex: `backend/api/jobs/training_job.py`) :

Pseudo-logique (simulation) :
- set status running progress 5 message "Starting analysis"
- étapes simulées (ex: copy sandbox, scan files, compute stats)
- à chaque étape : update progress + message
- fin : set done progress 100 message "Training analysis complete (stub)"

Gestion d’erreur :
- try/except : set status error message=str(e)

RQ :
- Utiliser la même queue/connexion que le projet (ne pas en créer une nouvelle si déjà en place).
- Le job doit être importable sans effets de bord.

## Frontend — Modifs attendues

### 1) API client `trainingAPI`
- `start(payload)` → POST `/api/training/start` → retourne `job_id` + `status`
- `getStatus(job_id)` → GET `/api/training/{job_id}/status`

### 2) Polling
Dans `frontend/src/pages/Training.jsx` :
- Après `start` :
  - afficher `Job créé: <job_id>`
  - setStatus("queued")
  - démarrer polling (ex: every 800ms–1500ms)
- À chaque réponse status :
  - afficher `Statut: <status>`
  - afficher `Message: <message>`
  - éventuellement `Progress: <n>%`
- Stop polling si `done` ou `error`.
- Désactiver bouton pendant `queued/running`.
- Nettoyer l’interval au unmount.

### 3) Vérification URL / proxy
- Garder cohérence avec ce qui marche déjà : les requêtes doivent partir vers `http://localhost:8000/api/...` (ou via proxy Vite si configuré).
- Ne pas casser les autres pages.

## Definition of Done (DoD) — critères de validation
1) Depuis le front `/training` :
- clic “Lancer analyse”
- logs affichent : “Job créé …”
- puis status évolue : queued → running → done (pas instantané)
2) Dans l’onglet Réseau (DevTools) :
- `POST http://localhost:8000/api/training/start` = 200
- ensuite `GET http://localhost:8000/api/training/<job_id>/status` appelé plusieurs fois
3) Si on force une erreur dans le job (optionnel) :
- status devient `error` + message visible côté UI

## Fichiers probables à créer / modifier (adapter à l’arbo actuelle)
Backend :
- `backend/api/routes/training.py` (modif routes start/status)
- `backend/api/jobs/training_job.py` (nouveau)
- `backend/api/services/training_status.py` ou `backend/api/storage/redis_training.py` (nouveau util Redis)

Frontend :
- `frontend/src/services/api.js` (ou `trainingAPI` existant)
- `frontend/src/pages/Training.jsx` (polling + UI)

## Notes
- Rester minimal : d’abord simulation (sleep), ensuite seulement on branchera la vraie analyse.
- Ne pas introduire Celery, APScheduler, etc. : RQ + Redis suffisent.



# SCRIPT.IA — Fix Step2 (RQ training queue + signature job)

## Constat
Le worker consomme la queue "training" mais crash:
TypeError: training_analysis_job() missing 1 required positional argument: 'job_id'

## Règle
Ne PAS demander `job_id` dans la signature du job.
Récupérer job_id via `rq.get_current_job()` dans le worker.

## Modifs à faire (backend)

### 1) Worker job: signature + job_id interne
- Fichier: backend/api/jobs/training_job.py (ou backend/api/jobs/training_worker.py)
- Remplacer:
  def training_analysis_job(job_id, payload): ...
- Par:
  from rq import get_current_job

  def training_analysis_job(payload: dict):
      job = get_current_job()
      job_id = job.id

      # set_status(job_id, "running", 0, "Démarrage")
      # ... étapes + progress
      # set_status(job_id, "done", 100, "OK")

- Ajouter try/except:
  - en cas d'exception: set_status(job_id, "failed", progress, f"Erreur: {e}") puis raise

### 2) Route POST /api/training/start: enqueue correct
- Fichier: backend/api/routes/training.py
- Le enqueue DOIT passer uniquement payload (pas job_id).
- Exemple:
  job_id = uuid4().hex
  set_status(job_id, "queued", 0, "Job en file d'attente")
  q = Queue("training", connection=redis)
  q.enqueue(training_analysis_job, payload_dict, job_id=job_id)
  return {"job_id": job_id, "status": "queued"}

### 3) Status endpoint
- S'assurer que GET /api/training/{job_id}/status lit bien Redis status.
- Si pas trouvé: status="not_found".
- Si job failed: renvoyer status="failed" + message.

## Modifs à faire (worker start)
- Le worker DOIT écouter "training" (en plus de reports/rag si besoin).
- Exemple: rq worker reports rag training
- Vérifier /tmp/worker.log bouge pendant un job.

## Critères d’acceptation (un seul test)
Depuis le front:
- POST /start → 200 + status "queued"
- GET /status → passe à "running" (progress bouge), puis "done" (progress=100)
- /tmp/worker.log montre exécution du job sans TypeError



 26 DECEMBRE 2025 - FIX STEP2   

 # Copilot Instructions — RH-Pro ruleset v1 (DOCX -> normalized JSON)

## ✅ IMPLEMENTATION COMPLETE — 26 DEC 2025

### Status: Pipeline v1 opérationnel
- ✅ Tous les modules créés et testés
- ✅ 7/7 tests unitaires passent
- ✅ Document sample parsé avec succès (19% coverage)
- ✅ Documentation complète disponible

### Fichiers créés
Voir: `docs/RHPRO_IMPLEMENTATION_SUMMARY.md` pour la liste complète.

### Usage rapide
```bash
# CLI
python demo_rhpro_parse.py path/to/bilan.docx

# Python
from src.rhpro.parse_bilan import parse_bilan_from_paths
result = parse_bilan_from_paths('bilan.docx')

# Tests
pytest tests/test_rhpro_parse.py -v
```

### Prochaines étapes (v2)
1. Fix sections imbriquées dans normalizer
2. Extraction identité depuis header/tableau Word
3. Parser bullets (Points d'appui → arrays)
4. Endpoint FastAPI (déjà créé: backend/api/routes/rhpro_parser.py)

---

## Goal
Implement a deterministic pipeline to parse messy RH-Pro DOCX reports and map them to a canonical schema using a YAML ruleset.

Inputs:
- config/rulesets/rhpro_v1.yaml
- a DOCX file (Word)
Output:
- normalized dict matching schemas/normalized.rhpro_v1.json
- report dict with coverage + unknown titles + warnings

## Non-goals (IMPORTANT)
- Do NOT generate or invent missing content.
- For fields with fill_strategy=source_only: if not found, keep empty string.
- Summarization is NOT mandatory in v1. Prefer storing raw text and mark sections "to_summarize".

## Required modules (Python)
Create:
- src/rhpro/ruleset_loader.py  (load + validate YAML)
- src/rhpro/docx_structure.py  (extract paragraphs with metadata via python-docx)
- src/rhpro/segmenter.py       (heading detection + segment building)
- src/rhpro/mapper.py          (map headings to canonical section ids using anchors exact/contains/regex/fuzzy)
- src/rhpro/normalizer.py      (build normalized output dict)
- src/rhpro/parse_bilan.py     (public function parse_bilan_docx_to_normalized)

## Data model (suggested)
Paragraph:
- text, style_name, is_bold, font_size, is_all_caps, numbering_prefix

Segment:
- raw_title, normalized_title, level, paragraphs[], mapped_section_id(optional), confidence

Report:
- found_sections[], missing_required_sections[], unknown_titles[], coverage_ratio, warnings[]

## Heading detection order
1) by_style (from ruleset.heading_detection.by_style.styles)
2) by_regex (numbered, uppercase patterns)
3) heuristics (short + bold)

## Mapping order
ruleset.title_matching.method_order:
- exact -> contains -> regex -> fuzzy (threshold)

## Tests
Add a minimal test in tests/test_rhpro_parse.py:
- loads sample DOCX if available
- checks output keys exist and report contains arrays
- checks no invented content for source_only fields
