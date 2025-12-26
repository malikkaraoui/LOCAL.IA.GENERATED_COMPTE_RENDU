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



## SUITE du 26 DECEMBRE 2025

OBJECTIF
On a déjà un Production Gate GO/NO-GO (missing_required_sections, required_coverage_ratio, unknown_titles, placeholders).
Sur 20 dossiers hétérogènes, je veux 2–3 PROFILS de gate avec des seuils/attendus différents, et une sélection automatique du profil via 2–3 signaux.

CONTRAINTES
- Ne pas “inventer” de contenu : on reste déterministe.
- Ne pas modifier le parsing/anchors pour ce besoin.
- Backward compatible : si aucun profil n’est trouvé/configuré => on retombe sur le gate actuel (profil “default”).
- Le choix du profil + les raisons doivent être tracées dans la sortie (report).

PROPOSITION TECHNIQUE (simple, robuste)
1) Ajouter une config "production_gate.profiles" dans le YAML ruleset (config/rulesets/rhpro_v1.yaml)
   - Chaque profil définit :
     - max_missing_required
     - min_required_coverage_ratio
     - max_unknown_titles
     - max_placeholders
     - ignore_required_prefixes (liste de préfixes de sections requises à ignorer pour ce profil)
       Exemple: ["tests", "dossier_presentation"] etc.
   - Conserver les "required" actuels du ruleset comme superset (bilan complet).
   - Pour les profils “placement/stage”, on ne change pas le ruleset : on filtre juste les required au moment du gate via ignore_required_prefixes.

2) Implémenter une sélection automatique du profil à partir de signaux (2–3 signaux)
   - Signaux à extraire depuis report.found_sections + leurs titres, et éventuellement report.unknown_titles
   - Utiliser la normalisation de titre robuste déjà en place (mapper._normalize_title_robust)
   - Heuristique proposée (ordre important) :
     a) Si “stage” détecté (titre contient stage / ou found_sections contient orientation_formation.stage) => profile="stage"
     b) Sinon si présence de sections “tests / vocation / profil_emploi / ressources_professionnelles” (>=2) => profile="bilan_complet"
     c) Sinon si “lai 15” ou “lai 18” détecté (titre) => profile="placement_suivi"
     d) Sinon => profile="placement_suivi" (profil tolérant par défaut)
   - Retourner aussi un petit objet "signals" (ex: {has_stage:true, has_tests:true, has_lai18:false, matched_titles:[...]})

3) Adapter evaluate_production_gate() pour prendre un profile_id (ou le sélectionner automatiquement)
   - Entrées: report + ruleset + (optionnel) profile_id
   - Étapes:
     - choisir profile_id si absent
     - calculer missing_required_effective:
       -> partir de report.missing_required_sections
       -> filtrer tout ce qui commence par un des ignore_required_prefixes du profil
     - recalculer required_coverage_ratio_effective:
       -> on a besoin du “required_total” après filtrage
       -> ajoute une méthode utilitaire dans ruleset_loader (ou ruleset object) pour retourner la liste complète des required_paths
       -> appliquer le même filtrage (ignore_required_prefixes) sur required_paths
       -> ratio_effective = 1 - len(missing_effective)/len(required_paths_effective) (si len>0)
     - unknown_titles_count = len(report.unknown_titles)
     - placeholders_count = len(report.placeholders_detected) (ou ce que vous avez déjà)
     - critères booléens par profil + status GO/NO-GO + reasons

4) Sortie / traçabilité
   - Ajouter dans report un bloc :
     report.production_gate = {
       "status": "GO|NO-GO",
       "profile_id": "...",
       "signals": {...},
       "criteria": { ... valeurs + seuils ... },
       "reasons": [ ... ],
       "missing_required_effective": [...]
     }
   - Dans demo_rhpro_parse.py (ou batch), afficher :
     - profil choisi
     - signaux
     - critères (valeur vs seuil)
     - reasons

5) Profils recommandés (valeurs initiales, ajustables après client_03–05)
   - bilan_complet:
     max_missing_required=0
     min_required_coverage_ratio=0.90
     max_unknown_titles=5
     max_placeholders=0..1 (selon exigence)
     ignore_required_prefixes=[]
   - placement_suivi:
     max_missing_required=1 (ou 2)
     min_required_coverage_ratio=0.60
     max_unknown_titles=10
     max_placeholders=5
     ignore_required_prefixes=["tests", "vocation", "profil_emploi", "dossier_presentation"]
   - stage:
     max_missing_required=0..1
     min_required_coverage_ratio=0.70
     max_unknown_titles=10
     max_placeholders=5
     ignore_required_prefixes=["tests", "vocation", "profil_emploi", "dossier_presentation"]
     (option: exiger orientation_formation + stage si dispo)

6) FICHIERS / EMPLACEMENTS
- config/rulesets/rhpro_v1.yaml : ajouter production_gate.profiles (+ éventuellement profile_selection keywords)
- src/rhpro/normalizer.py : garder evaluate_production_gate mais le rendre profile-aware
  OU créer src/rhpro/production_gate.py et appeler depuis normalizer (plus propre)
- src/rhpro/ruleset_loader.py : exposer required_paths (liste de tous les champs/sections marqués required=true)
- demo_rhpro_parse.py : print du profile + détails

ACCEPTANCE CRITERIA
- Sur client_02 : gate reste GO (comme aujourd’hui), profil choisi de manière cohérente (probablement “bilan_complet” si tests détectés).
- Sur un doc sans sections “tests” mais avec “LAI 15/18” : profil “placement_suivi”.
- Sur un doc avec “stage” : profil “stage”.
- Backward compatible : si profiles absents => comportement actuel inchangé.
- report JSON contient status + profile_id + signals + criteria + reasons.


## SUITE 

Objectif : remplacer le Production Gate “seuil unique” par 3 profils (bilan_complet / suivi_leger / stage)
et sélectionner automatiquement le bon profil selon quelques signaux déterministes.

Contraintes :
- Parser déterministe (pas de LLM)
- Ne pas bloquer l’extraction : le Gate ne fait que décider GO/NO-GO + raisons
- Backward compatible : si aucun profil détecté => profil par défaut (bilan_complet) + raisons
- Output explicable : toujours afficher le profil choisi + les signaux ayant mené au choix
- Pas de commandes terminal dans ta réponse : je veux uniquement les diffs / fichiers modifiés.

1) Config YAML (config/rulesets/rhpro_v1.yaml)
Ajouter une section production_gate_profiles :
- bilan_complet : thresholds stricts + required_sections larges
- suivi_leger : thresholds plus tolérants + required_sections réduites (ex: identity, conclusion)
- stage : thresholds intermédiaires + required_sections (ex: identity, orientation_formation, conclusion)
Chaque profil contient :
- min_required_coverage_ratio
- max_unknown_titles
- max_placeholders
- required_sections (liste de section_id)

2) Auto-sélection du profil (src/rhpro/normalizer.py ou module dédié)
Créer choose_gate_profile(...) -> {profile_id, reasons[], confidence(optional)}
Signaux à utiliser (2–3 max, simples et robustes) :
- titres normalisés (ex: contient “stage” => stage)
- présence de “LAI 15/18” (ex: “conclusion_lai_15/18” détecté)
- nombre/type de sections détectées : si beaucoup de sections “tests/vocation/profil_emploi” => bilan_complet,
  sinon => suivi_leger
Toujours retourner reasons (ex: ["keyword:stage", "found_sections:conclusion_lai_15", "few_sections=>suivi_leger"]).

3) Gate par profil
Modifier evaluate_production_gate(...) pour accepter un profile_id (ou profile config) :
- calculer missing_required_sections selon required_sections du profil
- appliquer thresholds du profil
- retourner un objet report complet : status GO/NO-GO, profile_id, reasons, criteria(detail),
  missing_required_sections_for_profile, unknown_titles_count, placeholders_count, required_coverage_ratio

4) Override manuel (CLI)
Ajouter --gate-profile <bilan_complet|suivi_leger|stage> sur demo_rhpro_parse.py
Si fourni : bypass auto-detection mais log “forced”.

5) Tests
Ajouter tests unitaires :
- test auto-detection (stage vs suivi_leger vs bilan_complet)
- test gate thresholds par profil (GO/NO-GO attendus)
- test override CLI (si applicable)
+ garder les tests existants verts.

6) Doc
Créer/mettre à jour un doc court : docs/PRODUCTION_GATE_PROFILES.md
- tableau profils / seuils / sections requises
- règles de détection
- exemples d’output (profil choisi + raisons)
