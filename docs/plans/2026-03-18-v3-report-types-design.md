# Design V3 — Types de rapports + Quality Gate + Page de revue

> Date: 2026-03-18
> Statut: Approuve
> Approche: Refactor progressif (pipeline existant intact, nouvelles couches par-dessus)

---

## 1. Probleme

Le systeme actuel genere 54 champs generiques sans notion de type de rapport.
Les specs des champs ne correspondent pas a ce que RH PRO attend.
Il n'y a pas de revue qualite avant export DOCX.

## 2. Solution

### 2.1 Types de rapports (`core/report_types.py`)

Chaque type de rapport mappe vers un sous-ensemble de sections:

```
rapport_initial       → 7 sections (PROFESSION, FORMATION, INCERTITUDE_ET_OBSTACLE,
                         ORIENTATION, FORMATION_DURANT_MESURE, STAGE, CONCLUSION)
rapport_intermediaire → a definir
rapport_stage         → a definir
rapport_final         → a definir
```

Les 54 champs V2 restent disponibles en standby. Chaque type de rapport pioche dedans.

### 2.2 Field Specs V3 (`core/field_specs_v3.py`)

Nouveau fichier. Chaque section contient les specs RH PRO mot pour mot:

```python
@dataclass
class FieldSpecV3:
    key: str
    query: str                    # Question RAG
    instructions: str             # Prompt LLM (But + Attendu + Contraintes + Format)
    max_chars: int
    min_lines: int
    max_lines: int
    sources: list[str]            # Types de sources attendues: ["journal", "cv", "msg"]
    immutable: bool               # True = ne change plus une fois edite (ex: PROFESSION)
    required_elements: list[str]  # Checklist quality gate
    element_keywords: dict        # {element: [keywords]} pour evaluation heuristique
    evaluation_prompt: str        # Description lisible pour le panneau droit
```

V2 reste intact. `generate.py` detecte V3 quand un report_type est fourni.

### 2.3 Quality Gate (`core/section_evaluator.py`)

Apres generation, chaque section est evaluee par heuristique (pas de 2e appel LLM):

- Pour chaque `required_element`, on cherche des mots-cles dans le texte genere
- Score = nombre d'elements trouves / total
- Status:
  - **VIDE**: texte vide ou "Non renseigne"
  - **BON**: >= 75% elements trouves
  - **A_REVOIR**: < 75% elements trouves

Donnees retournees:

```python
@dataclass
class SectionCheck:
    element: str          # Label lisible: "Raison de l'arret professionnel"
    found: bool
    keywords_matched: list[str]

@dataclass
class SectionEvaluation:
    status: str           # "BON" | "A_REVOIR" | "VIDE"
    score: float          # 0.0 -> 1.0
    checks: list[SectionCheck]
    comment: str          # "Il manque: raison de l'arret, missions principales"
```

### 2.4 Frontend — Page de revue

Nouvelle page apres la generation. Layout 3 colonnes:

**Gauche** — Sidebar sections
- Bulles colorees (vert/orange/rouge) avec nom de section
- Clic = selectionne la section

**Centre** — Contenu
- Texte editable de la section selectionnee
- Champ "Indication supplementaire" (optionnel) pour relance guidee
- Boutons: Relancer / Sauvegarder

**Droite** — Criteres RH PRO
- Checklist auto-evaluee (check/cross par element)
- Score et status
- Sources attendues

**Barre du bas**
- Score global (X/Y sections BON)
- Bouton "Exporter DOCX"

### 2.5 Flow utilisateur

```
Page 1: Selection client + type de rapport (dropdown)
  → Bouton "Generer"
Page 2: Progression (barre existante)
Page 3: Revue du rapport (NOUVELLE)
  → Editer / Relancer / Sauvegarder par section
  → Bouton "Exporter DOCX"
```

### 2.6 Regeneration guidee

Quand l'utilisateur clique "Relancer":
1. Champ texte optionnel "Indication supplementaire"
2. Si rempli: injecte dans le prompt comme instruction complementaire
3. Rappel LLM avec memes sources RAG + indication
4. Remplace le texte, recalcule le quality gate

### 2.7 API Backend

Nouveaux endpoints:

```
POST /api/reports/generate       — lance la generation (ajoute report_type)
GET  /api/reports/{id}/review    — retourne sections + evaluations
PUT  /api/reports/{id}/sections/{key}  — sauvegarde edition manuelle
POST /api/reports/{id}/sections/{key}/regenerate  — relance une section
POST /api/reports/{id}/export    — genere le DOCX final
GET  /api/report-types           — liste les types disponibles
```

## 3. Ce qui ne change PAS

- Pipeline extraction (`extract.py`, `extract_sources.py`)
- RAG / BM25 (`context.py`)
- LLM router (`llm_router.py`)
- Render DOCX (`render.py`)
- Anti-hallucination (sanitize, forbidden tokens)
- `field_specs_v2.py` (reste intact, standby)
- `src/rhpro/` (reste intact, standby)

## 4. Nouveaux fichiers

| Fichier | Role |
|---------|------|
| `core/report_types.py` | Types de rapports + mapping sections |
| `core/field_specs_v3.py` | Specs V3 avec criteres RH PRO |
| `core/section_evaluator.py` | Quality gate heuristique |
| `backend/api/routes/review.py` | Endpoints revue/edition/regeneration |
| `frontend/src/pages/ReportReview.jsx` | Page de revue 3 colonnes |

## 5. Fichiers modifies

| Fichier | Modification |
|---------|-------------|
| `core/generate.py` | Detecter V3, utiliser field_specs_v3 quand report_type fourni |
| `backend/workers/orchestrator.py` | Ajouter report_type, stocker evaluations |
| `backend/workers/report_worker.py` | Passer report_type |
| `backend/api/routes/reports.py` | Ajouter report_type au payload |
| `frontend/src/pages/ClientSelection.jsx` | Dropdown type de rapport |
| `frontend/src/App.jsx` | Route vers ReportReview |
