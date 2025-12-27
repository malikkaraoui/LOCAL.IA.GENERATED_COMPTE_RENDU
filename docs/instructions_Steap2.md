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

## SAMEDI 27 DECEMBRE 2025 - ✅ TERMINÉ

Objectif: ajouter un mode "Batch samples" + une sélection par UI (browse) pour parser/valider plusieurs dossiers clients.

### ✅ Implémentation complète

**A) Batch runner** ✅
- `src/rhpro/batch_runner.py` créé avec :
  - `discover_sources(root_dir)` : scan récursif → trouve tous dossiers avec `source.docx`
  - `run_batch()` : exécute pipeline sur N dossiers + agrège résultats
  - `generate_batch_report_markdown()` : génère rapport lisible
- Outputs dans `output_dir/` : `batch_report.json`, `batch_report.md`, `client_XX/normalized.json`
- Option `write_normalized_in_source` pour écrire dans dossiers sources

**B) Tests automatisés** ✅
- `tests/test_batch_samples.py` : 11 tests d'intégration
  - Découverte, parsing batch, rapports JSON/MD
  - Validation golden samples (client_01, client_02)
  - Override profil, write_in_source
  - **Tous les tests passent** : `11 passed`

**C) Browse/UI** ✅
- `pages_streamlit/batch_parser.py` : page Streamlit dédiée
  - Browse dialog (tkinter.filedialog)
  - Fallback : saisie manuelle + dropdown
  - Multiselect dossiers découverts
  - Bouton "Lancer batch"
  - Tableau résultats interactif (pandas DataFrame)
  - Téléchargement `batch_report.json` / `batch_report.md`
- Navigation ajoutée dans `streamlit_app.py` (sidebar radio)

**CLI** ✅
- `demo_batch.py` créé avec options :
  - `--list-only` : liste dossiers découverts
  - `--output` : dossier de sortie
  - `--profile` : force profil (stage/bilan_complet/placement_suivi)
  - `--write-in-source` : écrit `source_normalized.json` dans dossiers clients
  - Affichage résumé formaté avec emojis (✅/⚠️/❌)

**Documentation** ✅
- `docs/BATCH_PARSER_GUIDE.md` : guide complet (architecture, API, troubleshooting)
- `BATCH_QUICKSTART.md` : démarrage rapide CLI + UI

**Validation** ✅
- CLI testé : découverte, parsing, override profil → OK
- Tests pytest : 11/11 passed
- Existant préservé : `demo_rhpro_parse.py` fonctionne toujours
- Backward compatible : API `parse_bilan_docx_to_normalized()` inchangée

### Exemple d'utilisation

```bash
# CLI
python demo_batch.py data/samples --output out/batch --profile stage

# Tests
pytest tests/test_batch_samples.py -v

# UI
streamlit run streamlit_app.py  # → Sidebar "Batch Parser RH-Pro"
```

### Résultats

```
Total traité       : 2
Succès             : 2
Production Gate GO : 2
Coverage moyen     : 87.5%

✅ client_01  | stage  | GO   | 75.0%
✅ client_02  | stage  | GO   | 100.0%
```

---
## SAMEDI 27 DECEMBRE 2025 - 

Objectif: ajouter un mode “Batch samples” + une sélection par UI (browse) pour parser/valider plusieurs dossiers clients.

Contexte:
- Les docs de test sont rangés comme: data/samples/client_01..client_05/
- Chaque dossier contient au minimum un source.docx (et parfois source_normalized.json pour les golden samples client_01 et client_02).
- On veut exécuter le pipeline complet (parse -> normalize -> signals -> choix profil -> production gate) sur N dossiers et produire un rapport agrégé.

Tâches demandées:

A) Batch runner (sans saisie clavier de chemin)
- Implémenter une fonction “discover_sources(root_dir)” qui scanne récursivement root_dir et retourne tous les dossiers contenant “source.docx”.
- Ajouter un runner batch (script ou fonction réutilisable) qui:
  - boucle sur chaque dossier découvert
  - exécute la pipeline existante
  - écrit les outputs dans le dossier (ex: source_normalized.json si absent) ou dans out/batch/
  - agrège un report global: [{client_dir, profile, gate_status, required_coverage_ratio, missing_required_sections, unknown_titles_count, placeholders_count, reasons, warnings}]
  - exporte aussi un résumé lisible (markdown) + un JSON machine-readable.

B) Tests automatisés sur les 5 dossiers existants
- Ajouter un test pytest d’intégration qui lance le batch sur data/samples/ et vérifie:
  - pas d’exception sur client_01..client_05
  - pour client_01 et client_02 (golden): production gate = GO et missing_required_sections=0 (ou thresholds attendus)
  - pour client_03..05: au minimum “report généré” + profil choisi non vide + status ∈ {GO, NO_GO}
- Le test ne doit pas dépendre d’un chemin absolu; utiliser Path(__file__) / racine repo.

C) “Browse”/sélection dossiers via UI
- Dans streamlit_app.py (ou UI existante), ajouter une page “Batch parser”:
  - un bouton “Choisir un dossier racine” (browse) si possible en local (tkinter.filedialog.askdirectory)
  - sinon fallback: dropdown des racines connues + bouton “Rafraîchir”
  - une liste/multiselect des dossiers clients découverts
  - un bouton “Lancer batch”
  - afficher le tableau des résultats + possibilité de télécharger report.json / report.md

Contraintes:
- Ne pas ajouter de dépendances lourdes.
- Garder le scoring/détection déterministes (basés sur titres/headings).
- Compatible si le dataset est déplacé: root_dir paramétrable + discovery automatique.
- Garder l’existant (CLI actuelle) fonctionnel.
