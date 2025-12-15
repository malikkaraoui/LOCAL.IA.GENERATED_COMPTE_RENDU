# réglages.md — Règles & paramètres (RAG → LLM → Template DOCX)

Objectif : générer un rapport **en français**, fiable, **sans invention**, en remplissant un template DOCX contenant des variables `{{CHAMP}}`.

Ce fichier sert de “source de vérité” pour :
- moi (compréhension fonctionnelle)
- Copilot (implémentation dans `generate_fields.py`, `render_docx.py`, UI Streamlit)

---

## 1) Pipeline cible

1) **extract_sources.py**
   - Parcourt le dossier client (PDF/DOCX/TXT)
   - Extrait **texte brut**
   - Produit `out/<client>_extracted.json` + `out/<client>_corpus.txt`

2) **build_context.py (optionnel / recommandé)**
   - Transforme `extracted.json` en passages “RAG” (chunks + index)
   - Produit `out/context_*.json` (ou stock interne)

3) **generate_fields.py**
   - Pour chaque champ `{{...}}` :
     - récupère Top-K passages
     - décide si LLM nécessaire (selon règles)
     - interroge Ollama
     - nettoie, valide, tronque
   - Produit `out/answers.json`

4) **render_docx.py**
   - Ouvre le template DOCX
   - Remplace les `{{CHAMP}}` par `answers.json`
   - Produit `out/rapport_final.docx` (puis PDF si demandé)

---

## 2) Règles globales (NON négociables)

### 2.1 Langue
- **FR uniquement**
- Interdire anglais, interdire “Here is…”.

### 2.2 Format de sortie LLM
- Le LLM doit répondre en **texte brut**.
- Interdit : JSON, YAML, Markdown, code fences (```), listes JSON `[{...}]`.
- Si le LLM ne sait pas : il doit répondre **exactement** `__VIDE__`.

### 2.3 Zéro hallucination (pas d’invention)
- Si la donnée n’est pas dans les sources (ex: AVS, CV, lettre), on laisse vide.
- Le LLM **n’invente jamais** un numéro / une date / une info admin.

### 2.4 Contrôle par le script (pas par le LLM)
Le script Python doit :
- nettoyer la sortie (retirer ``` / “json” / préambules)
- détecter JSON/markdown → **retry** 1 fois avec prompt anti-JSON
- tronquer (caractères + lignes)
- valider sur liste autorisée quand nécessaire
- si 0 source pertinente et champ factuel → **skip LLM** → vide

---

## 3) Paramètres LLM (Ollama) — réglages recommandés

### 3.1 Temperature
- Par défaut : **0.1 à 0.2**
- Champs factuels : **0.0** (ou skip LLM)

### 3.2 Top-p
- Par défaut : **0.9**
- Si hallucinations → baisser à **0.7–0.8**

### 3.3 Top-K passages (RAG)
- Par défaut : **10**
- Si réponses hors sujet → descendre à **5–7**
- Si manque d’info → monter à **12–15** (attention au temps)

⚠️ Le Top-K ici est **le nombre de passages** envoyés dans le contexte, pas le top-k de sampling du modèle.

---

## 4) Limites de longueur (troncature côté script)

### 4.1 Champs “courts” (1 ligne, 50 caractères max)
- 1 ligne
- `max_chars = 50`
- Si pas d’info → vide

### 4.2 Champs “moyens” (3–4 lignes)
- `max_lines = 4`
- `max_chars = 500` (ajustable)
- Style : phrases courtes / pro / sans blabla

### 4.3 Champs “tests / niveaux”
- 1 ligne
- Valeurs contraintes (liste autorisée)
- Si valeur hors liste → vide

---

## 5) Stratégie anti-erreurs “JSON_INVALID”

### 5.1 Détection (côté script)
Si la réponse contient :
- `[` ou `{` en début
- ` ``` `
- `json` (ex: “Here is JSON…”)
→ considérer **invalid**.

### 5.2 Retry unique
Renvoyer au LLM un prompt “anti-JSON” :
- “Réponds uniquement par du texte brut, sans JSON, sans markdown.”
- “Si tu ne sais pas : __VIDE__”

Si après retry c’est encore invalide → réponse vide.

### 5.3 Logs
- Le doc final ne doit pas contenir d’explication.
- Les raisons (missing) restent dans logs/debug : `missing_reason`.

---

## 6) Règles par champ (spécification)

### 6.1 Champs identité / administratifs (FACTUELS, jamais inventés)
Règles :
- `require_sources = True`
- si `sources_used == []` → vide (skip LLM)
- 1 ligne, 50 char max
- format strict

Champs :
- `{{MONSIEUR_OU_MADAME}}` (valeurs autorisées : `Monsieur`, `Madame`)
- `{{NAME}}`
- `{{SURNAME}}`
- `{{NUMERO_AVS}}` (jamais généré)

### 6.2 Champs narratifs (3–4 lignes max)
Règles :
- `max_lines = 4`, `max_chars = 500`
- pas de dates/entreprises/écoles inventées
- si contexte insuffisant → `__VIDE__` → script remplace par vide

Champs :
- `{{PROFESSION}}`
- `{{FORMATION}}`
- `{{DISCUSSION_ASSURE}}`
- `{{COMPETENCES_SOCIALES}}`
- `{{COMPETENCES_PRO}}`
- `{{OBSTACLES}}`
- `{{ORIENTATION}}`
- `{{STAGE}}`
- `{{PRESENTATION}}`
- `{{ENTRETIEN}}`
- `{{CONCLUSION}}`

### 6.3 Champs ressources / contexte / activités (liste courte)
Règles :
- 2 à 4 lignes max (une idée par ligne)
- pas de roman

Champs :
- `{{Ressources_comportementales_Points_d’appui}}`
- `{{Ressources_comportementales_Points_de_vigilance}}`
- `{{Ressources_motivationnelles_PRINCIPAUX}}`
- `{{Ressources_interpersonnelles_principales}}`
- `{{Relation_au_marché_de_l_emploi}}`
- `{{Stratégies_comportementales}}`
- `{{Conditions_de_succès}}`
- `{{Contexte_Organisation_privilégiée}}`
- `{{Contexte_Rôle_privilégié}}`
- `{{Activités}}`
- `{{Activités_privilégiées}}`
- `{{Secteurs_privilégiés}}`
- `{{Fonctions_privilégiées}}`
- `{{métiers_privilégiés_qui_pourraient_etre_envisagé}}`
- `{{Vocatio}}`
- `{{Domaines_professionnels_EXEMPLES}}`
- `{{RIASEC_CORRESPONDANCE_SCORE}}` (⚠️ plutôt “tests/niveaux” si format contraint)
- `{{Rôles_professionnels}}`
- `{{professions}}`
- `{{Formations_supérieures}}`
- `{{Formations_hautes écoles}}`

### 6.4 Champs tests / niveaux (valeurs contraintes)
Règles :
- 1 ligne, 50 char max
- valeur doit appartenir à une liste autorisée
- si hors liste → vide

Valeurs autorisées (à valider/adapter) :
- Langues : `A1`, `A2`, `B1`, `B2`, `C1`, `C2`, `Non évalué`
- Outils bureautique : `Faible`, `Moyen`, `Bon`, `Très bon`, `Non évalué`
- Tests : `OK`, `Moyen`, `À renforcer`, `Non évalué`

Champs :
- `{{Français_positionnement_de_niveau}}`
- `{{Français_niveau_1}}`
- `{{Français_niveau_2}}`
- `{{Français_niveaU_3}}`
- `{{Tri_ET_classement}}`
- `{{TesT_d_attentiON_ADMINISTRATIF}}`
- `{{Anglais_positionnement_de_niveau_CECRL_ET_TOEIC}}`
- `{{ALLEMAND_positionnement_de_niveau}}`
- `{{Word_positionnement_de_niveau}}`
- `{{EXCEL_positionnement_de_niveau}}`
- `{{POWERPOINT_positionnement_de_niveau}}`
- `{{OUTLOOK_positionnement_de_niveau}}`
- `{{CALCUL_niveau_1}}`
- `{{CALCUL_niveau_2}}`
- `{{CALCUL_niveau_3}}`
- `{{CALCUL_ET_FRACTION}}`
- `{{DimensionS_volumes_et_mesures}}`
- `{{Test_de_niveau_en_comptabilité}}`
- `{{Test_de_Compréhension_de_consigneS}}`
- `{{Test_de_Saisie_de_commandes}}`

### 6.5 CV / Lettre de motivation (extraction, zéro invention)
Règles :
- `require_sources = True`
- si pas de doc CV/LM → vide
- 3–4 lignes max de synthèse (ou extrait court)

Champs :
- `{{Lettre_de_motivation}}`
- `{{CV}}`

### 6.6 Champ “LIEU_ET_DATE” (déterministe, pas de LLM)
Règles :
- fourni par UI / config
- exemple : `"Genève, le 15/12/2025"`

Champ :
- `{{LIEU_ET_DATE}}`

---

## 7) Prompt standard recommandé (copier-coller dans generate_fields.py)

### 7.1 Système / consignes
- Tu es un assistant RH.
- Tu réponds uniquement en français.
- Tu ne produis jamais de JSON, jamais de markdown.
- Si tu ne peux pas répondre avec les sources : réponds `__VIDE__`.

### 7.2 Instruction “format”
- Réponds en **1 ligne** (si champ court) OU **max 4 lignes** (si champ narratif).
- Pas de titre, pas de liste longue, pas de blabla.

### 7.3 Contexte (Top-K passages)
Inclure :
- passages numérotés
- nom du fichier source si possible

---

## 8) Implémentation Copilot — modifications attendues

### 8.1 Dans `generate_fields.py`
Créer une table `FIELD_SPECS` :
- `type`: `short | narrative | list | constrained | deterministic`
- `max_chars`, `max_lines`
- `require_sources`
- `allowed_values` (optionnel)
- `skip_llm_if_no_sources` (True pour champs factuels)

### 8.2 Post-traitement obligatoire
Fonctions attendues :
- `sanitize_output(text) -> text`
- `looks_like_json_or_markdown(text) -> bool`
- `truncate_lines(text, max_lines)`
- `truncate_chars(text, max_chars)`
- `validate_allowed_values(text, allowed_values)`

### 8.3 Debug
Écrire un fichier debug par champ :
- `out/debug/debug_<FIELD>.json`
Contient :
- prompt envoyé (ou hash)
- sources utilisées
- réponse brute
- réponse nettoyée
- raison si vide

---

## 9) Pourquoi certains champs restent vides ?
Ca peut venir de :
- 0 sources pertinentes (Top-K ne trouve rien)
- champ trop “spécifique” vs contenu réel (pas présent dans les documents)
- LLM répond en JSON → invalid → vide
- validation “allowed_values” rejette la réponse

➡️ Solution : mieux scorer les passages (BM25 + filtres), ajuster Top-K, et renforcer les prompts + règles.

---

## 10) Checklist avant génération
- [ ] extraction OK (`extracted.json` non vide)
- [ ] contexte OK (chunks)
- [ ] modèle Ollama dispo (`mistral:latest`)
- [ ] prompt FR + anti-JSON actif
- [ ] troncature active
- [ ] skip LLM si no-sources sur champs factuels
- [ ] render_docx remplace bien `{{CHAMP}}`

---

## 11) Champs listés (référence)
(la liste officielle des variables du template)
{{MONSIEUR_OU_MADAME}}
{{NAME}} {{SURNAME}}
{{NUMERO_AVS}}
{{PROFESSION}}
{{FORMATION}}
{{Ressources_comportementales_Points_d’appui}}
{{Ressources_comportementales_Points_de_vigilance}}
{{Ressources_motivationnelles_PRINCIPAUX}}
{{Ressources_interpersonnelles_principales}}
{{Relation_au_marché_de_l_emploi}}
{{Stratégies_comportementales}}
{{Conditions_de_succès}}
{{Contexte_Organisation_privilégiée}}
{{Contexte_Rôle_privilégié}}
{{Activités}}
{{Activités_privilégiées}}
{{Secteurs_privilégiés}}
{{Fonctions_privilégiées}}
{{métiers_privilégiés_qui_pourraient_etre_envisagé}}
{{Vocatio}}
{{Domaines_professionnels_EXEMPLES}}
{{RIASEC_CORRESPONDANCE_SCORE}}
{{Rôles_professionnels}}
{{professions}}
{{Formations_supérieures}}
{{Formations_hautes écoles}}
{{Français_positionnement_de_niveau}}
{{Français_niveau_1}}
{{Français_niveau_2}}
{{Français_niveaU_3}}
{{Tri_ET_classement}}
{{TesT_d_attentiON_ADMINISTRATIF}}
{{Anglais_positionnement_de_niveau_CECRL_ET_TOEIC}}
{{ALLEMAND_positionnement_de_niveau}}
{{Word_positionnement_de_niveau}}
{{EXCEL_positionnement_de_niveau}}
{{POWERPOINT_positionnement_de_niveau}}
{{OUTLOOK_positionnement_de_niveau}}
{{CALCUL_niveau_1}}
{{CALCUL_niveau_2}}
{{CALCUL_niveau_3}}
{{CALCUL_ET_FRACTION}}
{{DimensionS_volumes_et_mesures}}
{{Test_de_niveau_en_comptabilité}}
{{Test_de_Compréhension_de_consigneS}}
{{Test_de_Saisie_de_commandes}}
{{DISCUSSION_ASSURE}}
{{COMPETENCES_SOCIALES}}
{{COMPETENCES_PRO}}
{{OBSTACLES}}
{{ORIENTATION}}
{{STAGE}}
{{Formation}}
{{Lettre_de_motivation}}
{{CV}}
{{PRESENTATION}}
{{ENTRETIEN}}
{{CONCLUSION}}
{{LIEU_ET_DATE}}

---

Fin.
