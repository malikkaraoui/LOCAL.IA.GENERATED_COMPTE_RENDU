# Au-delà du RAG — Architecture de connaissance compatible Obsidian + QMD pour SCRIPT.IA
**Date :** 2026-05-25  
**Auteur :** Étude Claude Code  
**Contexte :** Remplacer le RAG naïf par un socle de connaissance structuré, compatible Obsidian mais indépendant d'Obsidian comme produit, pour alimenter le LLM local (Ollama / qwen3)

---

## 1. Diagnostic — Le RAG actuel dans SCRIPT.IA

### Ce qui existe aujourd'hui

```
CLIENTS/<client>/
  ├── CV.pdf
  ├── lettre.docx
  ├── entretien.msg
  └── sources/ingested_audio/
        ├── entretien_20260501.txt   ← Whisper chunks
        └── entretien_20260501.json  ← manifest segments
```

**Pipeline actuel :**
```
extract.py → texte brut concaténé → generate.py → prompt naïf → LLM → champs
```

### Faiblesses structurelles du RAG actuel

| Problème | Impact sur SCRIPT.IA |
|----------|---------------------|
| **Chunking aveugle** — coupures au caractère/phrase sans logique sémantique | LLM reçoit des demi-phrases, perd le contexte métier |
| **Pas de hiérarchie** — CV, lettre de motivation, entretien ont le même poids | Hallucinations : le LLM confond les sources |
| **Aucune relation inter-documents** — les docs sont des îles | Si le CV dit "5 ans exp." et l'entretien dit "7 ans", le LLM ne réconcilie pas |
| **Recherche par similarité cosinus** — efficace sur Wikipedia, médiocre sur des dossiers RH courts | Les chunks les plus proches ≠ les plus pertinents pour la section COMPÉTENCES |
| **Pas de mémoire entre sessions** — chaque rapport repart de zéro | Même client revisité = même calcul, pas d'apprentissage |
| **Dump textuel comme contexte** — le LLM reçoit 8000 tokens de texte brut | Tokens gaspillés, attention dispersée, qualité aléatoire |

---

## 2. Ce qui change de paradigme — De RAG à SKI

### 2.1 Pourquoi "RAG" est le mauvais modèle pour les dossiers RH

Le RAG a été conçu pour **chercher** dans une base de connaissance large (Wikipedia, documentation technique). Le problème SCRIPT.IA est différent :

- Le corpus par client est **petit** (5–15 documents max)
- Le contexte est **dense et structuré** (données factuelles, dates, noms)
- Les sections du rapport ont des **besoins précis** (COMPÉTENCES ≠ FORMATION ≠ PROJET PRO)
- La précision factuelle prime sur la couverture sémantique

**La solution n'est pas un meilleur RAG — c'est un meilleur contexte.**

### 2.2 SKI — Structured Knowledge Injection

Concept : au lieu de récupérer des chunks et de les jeter dans le prompt, on **construit** un document de contexte structuré, hiérarchisé, annoté — puis on l'injecte en bloc.

```
Avant (RAG) :  [chunk3][chunk17][chunk2][chunk9] → LLM (chaotique)
Après (SKI)  :  [Profil·client·structuré·en·Obsidian] → QMD·rendu → LLM (précis)
```

### 2.3 Ce que cette architecture n'est pas

- **Ce n'est pas une dépendance produit à Obsidian** : le runtime doit fonctionner avec de simples fichiers Markdown/YAML/JSON.
- **Ce n'est pas une interface client** : le client final n'a ni besoin de voir Obsidian, ni besoin de l'utiliser.
- **Ce n'est pas un gadget de visualisation** : la priorité est d'améliorer la qualité du traitement de la donnée en amont.
- **Ce n'est pas limité au remplissage de comptes rendus** : le même socle doit pouvoir alimenter demain des questions ciblées sur un client ou un compte rendu à la volée.

---

## 3. Architecture cible — couche de connaissance compatible Obsidian + QMD

### 3.1 Une couche de connaissance client compatible Obsidian, mais non dépendante

**Principes non négociables :**
- Le **cœur du système** reste un contrat de données simple : Markdown + YAML frontmatter + JSON de métadonnées.
- **Obsidian est un pilier structurel fort**, pas le moteur métier ni la dépendance d'exécution.
- **L'interface client** reste l'application SCRIPT.IA ; Obsidian reste un outil interne d'audit, d'inspection ou d'exploration.
- La brique amont doit avant tout être **plus fiable, plus résistante, plus rapide et plus pertinente** que le RAG actuel.

**Pourquoi viser la compatibilité Obsidian ?**
- Format : Markdown pur + YAML frontmatter → lisible par le LLM nativement
- Backlinks (`[[note]]`) et tags → utiles pour structurer les relations quand on en a besoin
- Dataview → requêtes internes possibles sur les métadonnées
- Pas de base de données externe imposée — juste des fichiers .md et des manifests dans le dossier client
- Réutilisation future du même socle pour plusieurs usages : génération de rapports, Q/R ciblée, synthèse à la demande

**Structure cible par client :**

```
CLIENTS/<client>/
  ├── .obsidian/          ← config optionnelle pour usage interne (ignoré git)
  ├── 00-profil.md        ← fiche synthèse générée (frontmatter riche)
  ├── 01-parcours.md      ← timeline emplois extraite du CV
  ├── 02-formations.md    ← diplômes + certifications
  ├── 03-competences.md   ← inventaire compétences taggées
  ├── 04-entretien.md     ← transcription Whisper structurée
  ├── 05-projet-pro.md    ← objectifs & motivations
  ├── sources/            ← fichiers originaux (PDF, DOCX, MSG)
  └── _meta/
        ├── index.json    ← manifest SHA256 + mtime
        └── graph.json    ← relations inter-notes
```

**Exemple de note Obsidian générée (`00-profil.md`) :**

```markdown
---
nom: "Mohammed Ali"
date_naissance: "1985-03-12"
nationalite: "Marocaine"
situation: "En poste"
disponibilite: "3 mois"
source_cv: "CV_Mohammed_Ali.pdf"
source_entretien: "entretien_20260501.txt"
sha256_cv: "a3f9..."
last_updated: "2026-05-25T14:30:00"
tags: [ingénierie, management, senior]
---

# Profil — Mohammed Ali

Lié à : [[01-parcours]] · [[03-competences]] · [[04-entretien]]

## Synthèse
...
```

> **Important :** ces fichiers doivent rester pleinement exploitables par SCRIPT.IA sans installation d'Obsidian.

### 3.2 QMD — Quarto Markdown pour les templates de contexte

**Pourquoi QMD (Quarto Markdown) ?**
- Format structuré avec métadonnées YAML en tête
- Support natif des blocs de code, des variables, des includes
- Peut être rendu en texte pur (pour le LLM) ou en HTML/PDF (pour l'humain)
- Permet de **composer** le contexte par section de rapport

**Template QMD par section de rapport (`templates/qmd/section_competences.qmd`) :**

```qmd
---
section: COMPÉTENCES
client: "{{client_name}}"
sources: ["{{cv_path}}", "{{entretien_path}}"]
mode: inference
---

# Contexte pour la section COMPÉTENCES

## Données factuelles extraites

{{competences_obsidian_note}}

## Passages sources pertinents

### Depuis le CV
{{cv_competences_extract}}

### Depuis l'entretien ({{entretien_duration}}s transcrit)
{{entretien_competences_extract}}

## Règle d'inférence
Génère la section COMPÉTENCES en te basant UNIQUEMENT sur les données ci-dessus.
Ne pas inventer. Si une compétence n'est pas mentionnée, ne pas la citer.
```

**Le QMD rendu devient le prompt de contexte** — structuré, tracé, versionnable.

### 3.3 Pipeline complet Beyond-RAG

```
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE BEYOND-RAG                          │
└─────────────────────────────────────────────────────────────────┘

Phase 1 — INDEXATION AMONT (une fois par document nouveau)
  Sources (PDF/DOCX/MSG/Audio)
    ↓ extract.py (existant — SHA256 + mtime)
    ↓ obsidian_builder.py (NOUVEAU)
  → Notes Obsidian (.md) avec frontmatter
  → index.json mis à jour (cache incrémentiel)
  → Données plus fiables et plus résistantes qu'un dump brut

Phase 2 — CONSOLIDATION (une fois par client/session)
  Notes Markdown compatibles Obsidian
    ↓ normalisation métier + consolidation profil
  → Fichier 00-profil.md consolidé
  → Tags sémantiques / métadonnées utiles
  → graph.json optionnel si enrichissement activé

Phase 3 — CONTEXT BUILDING (une fois par section de rapport)
  Notes Markdown + index.json (+ graph.json si activé)
    ↓ context_builder.py (NOUVEAU — remplace le dump brut)
    ↓ QMD template (par section)
  → Document de contexte structuré (texte pur ~2000 tokens ciblés)

Phase 4 — USAGES (existant puis futur)
  Contexte QMD structuré
    ↓ generate.py (modifié — prompt reçoit contexte structuré)
    ↓ futurs endpoints de questions/réponses client
  → LLM (Ollama/qwen3) avec contexte de qualité
  → Champs de rapport + quality gate aujourd'hui
  → Questions ciblées / compte rendu à la volée demain
```

---

## 4. Impact sur la structure du code

### 4.1 Fichiers à créer (nouveaux modules)

```
core/
  ├── obsidian_builder.py   ← Convertit extracted docs → notes Obsidian
  ├── graph_builder.py      ← Construit les relations inter-notes
  └── context_builder.py    ← Assemble le contexte QMD par section

templates/
  └── qmd/
        ├── base_context.qmd
        ├── section_competences.qmd
        ├── section_formation.qmd
        ├── section_parcours.qmd
        ├── section_projet_pro.qmd
        ├── section_motivations.qmd
        ├── section_disponibilite.qmd
        └── section_pretentions.qmd
```

### 4.2 Fichiers à modifier (existants)

| Fichier | Modification |
|---------|-------------|
| `core/extract.py` | Appel `obsidian_builder.py` après extraction → génère les .md |
| `core/generate.py` | Remplace la concaténation brute par `context_builder.py` |
| `rapport_orchestrator.py` | Étape de construction de la base de connaissance client avant `generate_fields` ; enrichissement graphe optionnel |
| `backend/config.py` | Feature flags de couche de connaissance (`KNOWLEDGE_LAYER_ENABLED`, export compatible Obsidian optionnel) |
| `core/field_specs_v3.py` | Référencer le template QMD pour chaque section |

### 4.3 Fichiers inchangés

- `core/models.py` — SourceDoc reste la même
- `core/llm_router.py` — abstraction LLM inchangée
- `core/section_evaluator.py` — quality gate inchangé
- `core/docx_render.py` — rendu DOCX inchangé
- `script_ai/rag/ingest_audio.py` — Whisper inchangé (sortie .txt intégrée dans Obsidian)

---

## 5. Détail des nouveaux modules

### 5.1 `core/obsidian_builder.py`

```python
# Responsabilités :
# - Prend le résultat de extract.py (list[SourceDoc])
# - Génère les fichiers .md Obsidian avec frontmatter YAML
# - Identifie la note à créer (CV → 01-parcours.md, entretien → 04-entretien.md)
# - Met à jour _meta/index.json (cache SHA256)
# - Retourne le chemin du vault client

def build_obsidian_vault(
    client_dir: Path,
    source_docs: list[SourceDoc],
    force_rebuild: bool = False,
) -> Path:
    """Construit ou met à jour le vault Obsidian du client."""
    ...

def _doc_to_obsidian_note(doc: SourceDoc, note_type: str) -> str:
    """Convertit un SourceDoc en note Markdown avec frontmatter."""
    ...

def _infer_note_type(doc: SourceDoc) -> str:
    """Détermine le type de note (cv, formation, entretien, etc.) depuis le filename."""
    ...
```

### 5.2 `core/graph_builder.py`

```python
# Responsabilités :
# - Lit toutes les notes Obsidian d'un client
# - Détecte les entités communes (noms d'entreprises, dates, compétences)
# - Crée des backlinks automatiques entre notes
# - Génère graph.json (nœuds + arêtes)
# - Met à jour les sections "Lié à" dans les notes

def build_client_graph(vault_path: Path) -> dict:
    """Construit le graphe de connaissance du client."""
    ...
```

> **Note :** `graph_builder.py` est un enrichissement optionnel. La valeur principale doit déjà être obtenue sans lui via l'indexation structurée et `context_builder.py`.

### 5.3 `core/context_builder.py`

```python
# Responsabilités :
# - Point d'entrée principal pour generate.py
# - Remplace l'ancienne concaténation de texte brut
# - Sélectionne les notes structurées pertinentes par section
# - Applique le template QMD correspondant
# - Retourne un contexte structuré ~1500-2500 tokens (configurable)

def build_section_context(
    vault_path: Path,
    section_name: str,
    field_spec: FieldSpec,
    max_tokens: int = 2000,
) -> str:
    """Construit le contexte structuré pour une section de rapport."""
    ...

def _load_qmd_template(section_name: str) -> str:
    """Charge le template QMD correspondant à la section."""
    ...

def _render_qmd(template: str, context_vars: dict) -> str:
    """Remplace les variables dans le template QMD."""
    ...
```

---

## 6. Gains attendus vs RAG actuel

| Métrique | RAG actuel (dump brut) | Beyond-RAG (Obsidian+QMD) |
|----------|------------------------|--------------------------|
| **Tokens contexte** | 4000–8000 (dump complet) | 1500–2500 (ciblé par section) |
| **Pertinence contexte** | ~60% (chunks bruités) | ~90% (notes structurées) |
| **Hallucinations** | Fréquentes (contexte ambigu) | Réduites (facts taggés + sources) |
| **Temps calcul LLM** | Plus long (plus de tokens) | Plus court (contexte concentré) |
| **Traçabilité** | Nulle (quel chunk a servi ?) | Complète (QMD = prompt auditable) |
| **Cache incrémentiel** | Aucun | SHA256 + mtime → skip si inchangé |
| **Multi-sessions** | Recalcul complet | Notes Obsidian persistantes |

---

## 7. Ce qui devient possible avec cette architecture

### 7.1 Questions ciblées sur un client

Exemples d'usages futurs rendus possibles par la même base de connaissance :

- « Quelles compétences de management sont confirmées à la fois par le CV et l'entretien ? »
- « Quels sont les écarts entre le projet professionnel exprimé en entretien et le parcours passé ? »
- « Résume-moi les points de vigilance sur ce client en 10 lignes. »

Le point clé : **on ne reconstruit pas un nouveau pipeline** ; on réutilise le même socle de données structurées.

### 7.2 Compte rendu à la volée

Au-delà du rapport figé, SCRIPT.IA peut demain composer un compte rendu ciblé sur un sujet, un angle ou une question précise, à partir du même contexte structuré.

Exemples :

- compte rendu « compétences techniques uniquement »
- synthèse « mobilité / disponibilité / prétentions »
- note interne « risques et contradictions détectées »

### 7.3 Requêtes Dataview sur les clients

```dataview
TABLE nom, disponibilite, tags
FROM "CLIENTS"
WHERE contains(tags, "management")
SORT last_updated DESC
```
→ Vue agrégée de tous les candidats "management" disponibles

### 7.4 Détection de contradictions inter-documents

```python
# graph_builder.py peut détecter :
# CV dit : "15 ans expérience"
# Entretien dit : "8 ans d'expérience"
# → Warning dans 00-profil.md → LLM averti
```

### 7.5 Versioning du contexte

Chaque QMD rendu est sauvegardé avec timestamp → on peut rejouer exactement quel contexte a produit quel rapport.

### 7.6 Fine-tuning futur

Les paires (contexte QMD → champ généré + note quality gate) deviennent des datasets d'entraînement pour fine-tuner un modèle local spécialisé RH.

---

## 8. Plan de migration — Phases

### Phase 0 — Prérequis (1 jour)
- [ ] Créer `templates/qmd/` avec les 7 templates de base (un par section)
- [ ] Définir le schéma frontmatter YAML Obsidian par type de document
- [ ] Feature flags de couche de connaissance dans `backend/config.py`

### Phase 1 — Indexation client fiable (3 jours)
- [ ] Écrire `core/obsidian_builder.py`
- [ ] Modifier `core/extract.py` : appeler le builder après extraction
- [ ] Tester sur 3 clients réels de `CLIENTS/`
- [ ] Vérifier que les notes générées sont lisibles dans Obsidian **et** exploitables sans Obsidian
- [ ] Mesurer le gain en stabilité sur des reruns (fichiers inchangés vs modifiés)

### Phase 2 — Context Builder orienté rapport (3 jours)
- [ ] Écrire `core/context_builder.py`
- [ ] Brancher sur `core/generate.py` (derrière feature flag)
- [ ] A/B test : comparer quality gate RAG brut vs contexte structuré
- [ ] Ajuster les templates QMD selon les résultats
- [ ] Mesurer tokens, temps et taux de régénération utile

### Phase 3 — Réutilisation des données (2 jours)
- [ ] Prototyper 3 à 5 questions ciblées sur un client à partir de la même base structurée
- [ ] Définir un format de sortie « compte rendu à la volée »
- [ ] Vérifier que le socle sert plusieurs usages sans duplication de logique

### Phase 4 — Enrichissement relationnel optionnel (2 jours)
- [ ] Écrire `core/graph_builder.py` (entités + backlinks) **seulement si** les mesures montrent un gain attendu
- [ ] Intégrer dans `rapport_orchestrator.py` derrière feature flag
- [ ] Tester la détection de contradictions

### Phase 5 — Stabilisation (2 jours)
- [ ] Tests d'intégration end-to-end sur 5 clients complets
- [ ] Mesure tokens avant/après
- [ ] Documentation `docs/guides/OBSIDIAN_SETUP.md`
- [ ] Mise à jour vault (40-roadmap.md)

**Total estimé : 6 jours pour le socle utile, 10–12 jours avec enrichissements optionnels**

---

## 9. Risques et mitigations

| Risque | Probabilité | Mitigation |
|--------|------------|-----------|
| Notes Obsidian mal classées (CV ≠ lettre de motivation) | Moyen | `_infer_note_type()` avec règles + fallback manuel |
| QMD trop rigide — cas edge non couverts | Faible | Template de fallback (`base_context.qmd`) générique |
| Confusion entre format de données et produit Obsidian | Moyen | Poser un contrat clair : Markdown/YAML/JSON = cœur ; Obsidian = outil interne optionnel |
| Performance dégradée (plus de fichiers à écrire) | Faible | Cache SHA256 — rebuild uniquement si le fichier a changé |
| Compatibilité Obsidian rompue (version app) | Très faible | Format Markdown pur — Obsidian est optionnel |
| LLM ignore la structure QMD | Faible | Tests A/B pour valider les gains avant merge |

---

## 10. Décision à prendre

Trois niveaux d'engagement possibles :

**Option A — Socle utile** : Indexation client structurée (Phase 1) + context_builder ciblé (Phase 2)  
→ Gain immédiat sur la qualité amont, risque faible, 6 jours  
→ Recommandé comme première étape

**Option B — Polyvalent** : Option A + réutilisation des données pour questions ciblées / comptes rendus à la volée  
→ Ouvre les usages futurs sans changer de socle, 8 jours  
→ Recommandé si l'objectif est aussi conversationnel

**Option C — Enrichi** : Option B + graphe relationnel optionnel  
→ Plus puissant, mais complexité supérieure, 10–12 jours  
→ À lancer seulement après validation du ROI

---

*Étude produite le 2026-05-25 — à archiver dans `vault/20-decisions.md` une fois qu'une décision aura été prise.*
