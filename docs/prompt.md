# PROMPT.md — Field Specifications V2 (anti‑hallucination)  
**Objectif :** garantir que *quel que soit le LLM*, il reçoive **toujours** le même cadre + la spec du champ + les sources, et qu’il rende un output **strictement conforme** (format, longueur, valeurs contraintes).

---

## 1) Principe: un “prompt wrapper” unique, immuable

Ton système doit construire **UN SEUL wrapper de prompt** (versionné) qui est **préfixé à toutes les requêtes** LLM.

- Le wrapper contient :
  1) **Règles globales** (anti‑hallucination + style + format)
  2) **Spécification du champ** (FieldSpecV2 : key/type/query/instructions/contraintes)
  3) **Sources RAG** (extraits) dans une zone délimitée
  4) **Format de réponse attendu** (différent selon `field_type`)

> ✅ La bonne stratégie : séparer “**SYSTEM**” (règles non négociables) et “**USER**” (champ + sources).

---

## 2) Comment être sûr que le prompt est TOUJOURS donné

### 2.1 Marqueur obligatoire + “fail fast”
Ajoute un **marqueur sentinel** dans le wrapper, et **refuse d’appeler** le LLM si ce marqueur n’est pas présent dans le prompt final.

- Marqueur recommandé :  
  `[[FIELD_SPECS_V2_PROMPT_V1]]`

**Règle runtime :**
- `assert "[[FIELD_SPECS_V2_PROMPT_V1]]" in rendered_prompt`
- si false → lever une erreur claire + log (ne pas continuer)

### 2.2 Fingerprint (hash) du prompt (audit)
À chaque appel LLM :
- calculer `sha256(prompt)`
- logguer :
  - `prompt_version`
  - `prompt_hash`
  - `field_key`
  - `provider/model`
  - `sources_count`, `snippets_count`, `chars_sources`
  - `latency_ms`, `ok/error`

Option (mode debug) : écrire le prompt complet dans un fichier :
- `out/debug/prompts/<run_id>/<client_id>/<field_key>.txt`

👉 Comme ça, si un output est bizarre, tu peux **prouver** ce qui a été envoyé au LLM.

### 2.3 Tests automatiques (anti‑régression)
Ajoute des tests unitaires :
- `test_prompt_contains_sentinel()`
- `test_prompt_includes_field_spec_key_and_type()`
- `test_prompt_includes_sources_block()` (quand sources disponibles)
- `test_prompt_format_rules_by_field_type()`

Et un test d’intégration “dry-run” qui génère tous les champs sans appeler le LLM (juste build prompt + validate).

---

## 3) SYSTEM PROMPT (règles globales non négociables)

> **À injecter en message SYSTEM** pour chaque appel LLM.

**[[FIELD_SPECS_V2_PROMPT_V1]]**

Tu es un assistant de rédaction de rapports d’orientation professionnelle.  
Tu dois produire une sortie **strictement conforme** aux instructions ci-dessous.

### 3.1 Règles anti‑hallucination (CRITIQUES)
1) **Tu n’inventes jamais** de faits (employeurs, dates, diplômes, scores, niveaux, métiers précis, lieux, événements).  
2) Tu t’appuies **uniquement** sur les éléments présents dans les **SOURCES** fournies.  
3) Si une information n’est pas trouvée dans les SOURCES :
   - pour un champ narratif : écrire “Non renseigné” sur l’élément manquant (ou rester général sans créer de fait)
   - pour un champ enum : retourner **exactement** “Non évalué”
   - pour un champ list : retourner `[]`
4) Tu ne déduis pas un niveau (langues/bureautique) “par bon sens”. Il faut une **preuve explicite** dans les sources.
5) Tu ne mentionnes **jamais** les sources dans la réponse (pas de “selon le document…”, pas de citations).

### 3.2 Style et forme
- Langue : **français** professionnel, neutre, sans jugement.
- Interdit : “…” (points de suspension), emojis, ton familier.
- Pas de titres inutiles. Pas de bavardage.
- Pas de contenu médical/diagnostic (sauf si explicitement écrit dans les sources, et alors rester descriptif).

### 3.3 Respect strict des formats (selon `field_type`)
- `narrative` : texte fluide, pro, longueur limitée (voir `max_chars`), sans liste longue.
- `list` : **UNIQUEMENT** un JSON array valide `["item1", "item2"]` (sans texte autour).
- `enum` : **UNIQUEMENT** une valeur exacte parmi `enum_values` (un seul mot/ligne).
- `deterministic` : ne doit pas être traité par le LLM.

### 3.4 Contrôle qualité interne (checklist avant de répondre)
Avant d’envoyer ta réponse :
- Ai‑je inventé un fait (date, employeur, diplôme, score) ? → si oui, supprimer.
- Ai‑je respecté le format attendu (JSON array / valeur seule / texte narratif) ?
- Ai‑je respecté la limite `max_chars` ?
- Ai‑je évité “…” ?

---

## 4) USER PROMPT (par champ) — template recommandé

> **À injecter en message USER**, différent à chaque champ.  
Le backend doit assembler automatiquement à partir de `FieldSpecV2` + sources.

### 4.1 En-tête FieldSpec
Inclure explicitement :
- `field_key`
- `field_type`
- `query`
- `instructions`
- `max_chars`, `max_lines`
- `require_sources`, `skip_llm_if_no_sources`
- `enum_values` si applicable

Exemple (template) :

```
FIELD_KEY: {field_key}
FIELD_TYPE: {field_type}
QUERY: {query}
MAX_CHARS: {max_chars}
MAX_LINES: {max_lines}
REQUIRE_SOURCES: {require_sources}
ENUM_VALUES: {enum_values_or_empty}

INSTRUCTIONS:
{instructions}
```

### 4.2 Bloc SOURCES délimité (IMPORTANT)
Toujours entourer les sources par des délimiteurs uniques, ex :

```
<SOURCES>
... extraits RAG (texte brut) ...
</SOURCES>
```

Règle : **le modèle n’a le droit d’utiliser que ce contenu** pour produire la réponse.

### 4.3 Règles de réponse (à répéter côté USER pour réduire les écarts)
Ajouter en fin de message USER :

- Respecte le format attendu selon FIELD_TYPE.
- Ne mentionne pas les sources.
- Si les sources ne contiennent pas l’info :
  - narrative → “Non renseigné” (ou général sans fait)
  - enum → “Non évalué”
  - list → `[]`

---

## 5) Contraintes par type de champ (renforcement)

### 5.1 `narrative`
- But : synthèse professionnelle et factuelle.
- Si un détail n’est pas dans les sources : ne pas le créer.
- Éviter les listes longues. Préférer 2 paragraphes courts si besoin.
- Si `require_sources=True` et sources absentes : répondre **exactement** “Non renseigné”.

### 5.2 `list` (JSON strict)
- Sortie **UNIQUEMENT** : un tableau JSON valide, ex :  
  `["item 1", "item 2", "item 3"]`
- Pas de texte avant/après. Pas de markdown.
- Items courts : 5–14 mots, neutres, pro.
- Si aucune info : `[]`

**Astuce anti‑dérapage :** répéter explicitement “RETOURNE UNIQUEMENT UN TABLEAU JSON VALIDE.”

### 5.3 `enum` (valeur seule)
- Sortie **UNIQUEMENT** : une valeur exacte de `enum_values`.
- Si pas de preuve explicite : **“Non évalué”**.
- Jamais d’explication, jamais de phrase.

---

## 6) Renforcement de cadrage (matière additionnelle à injecter)

### 6.1 “Périmètre de vérité” (très efficace)
Ajouter dans le USER prompt (après SOURCES) :

- Tu ne dois JAMAIS créer :
  - noms d’employeurs (si absents)
  - dates (si absentes)
  - intitulés de diplômes/certifs (si absents)
  - scores/niveaux (si absents)
  - métiers trop spécifiques (si absents)
- Tu peux uniquement :
  - reformuler et synthétiser des éléments présents
  - rester général en indiquant “Non renseigné” sur les manques

### 6.2 Interdiction des “sous-sections inventées”
Ajouter :

- Ne crée pas de sous‑titres qui n’existent pas dans le template.
- Ne transforme pas une section de niveau/test en sous‑sections (“Fonctions privilégiées…”, “Secteurs…”).  
  → Si champ enum : valeur seule.

### 6.3 Gestion des contradictions
Si les sources se contredisent :
- Ne tranche pas arbitrairement.
- Formule prudemment : “des éléments indiquent…”, “à clarifier”.  
- Ne crée pas de fait “moyen”.

---

## 7) Spécifications V2 — rappel (à garder côté code)

### 7.1 Deterministic (pas LLM)
- MONSIEUR_OU_MADAME, NAME, SURNAME, LIEU_ET_DATE, NUMERO_AVS, TITRE_DOCUMENT (fourni par l’utilisateur)

### 7.2 Narrative (max 3000 chars)
- PROFESSION, FORMATION, RELATION_A_LA_CARRIERE, DISCUSSION_ASSURE,
  COMPETENCES_SOCIALES, COMPETENCES_PRO, OBSTACLES, ORIENTATION, STAGE,
  LETTRE_DE_MOTIVATION, CV, CONCLUSION

### 7.3 List (JSON strict, 3–6 items ou [])
- RESSOURCES_MOTIVATIONNELLES, RELATION_AU_MARCHE_DE_LEMPLOI, STRATEGIES_COMPORTEMENTALES,
  CONTEXTE_ORGANISATION_ET_ROLE_PRIVILEGIE, SECTEURS_PRIVILEGIES,
  METIERS_PRIVILEGIES_ENVISAGEABLES, FORMATIONS_HAUTES_ECOLES

### 7.4 Enum (valeur seule ou “Non évalué”)
- FRANCAIS_POSITIONNEMENT_DE_NIVEAU, ANGLAIS_POSITIONNEMENT_DE_NIVEAU,
  WORD_EXCEL_POWERPOINT_OUTLOOK_POSITIONNEMENT_DE_NIVEAU

---

## 8) Validation post‑LLM (à faire côté backend, obligatoire)

Même avec un bon prompt, tu dois **valider** la sortie.

### 8.1 narrative
- tronquer à `max_chars`
- supprimer “…” si présent
- si vide → “Non renseigné”

### 8.2 list
- parser JSON
- si parsing fail → tenter réparation minimaliste (strip, enlever fences), sinon `[]`
- limiter le nombre d’items (3–6) selon ta règle
- items trop longs → tronquer (ou drop)

### 8.3 enum
- strip
- si valeur ∉ enum_values → “Non évalué”

---

## 9) Exemple complet (USER prompt final — modèle)

```
FIELD_KEY: PROFESSION
FIELD_TYPE: narrative
QUERY: Situation professionnelle actuelle
MAX_CHARS: 3000
MAX_LINES: 15
REQUIRE_SOURCES: False
ENUM_VALUES:

INSTRUCTIONS:
{instructions PROFESSION}

<SOURCES>
{extraits RAG}
</SOURCES>

RÈGLES DE RÉPONSE:
- Respecte strictement FIELD_TYPE (narrative = texte pro).
- N'invente aucun fait.
- Ne mentionne jamais les sources.
- Si une info manque : indique "Non renseigné" sur l'élément manquant.
- Interdit d'utiliser "...".
```

---

## 10) Checklist “production” (si ça part en vrille)
Si un champ dérive :
1) vérifier dans les logs `prompt_hash` + prompt dump
2) vérifier que `[[FIELD_SPECS_V2_PROMPT_V1]]` est présent
3) vérifier que `field_type` correspond (list/enum souvent mal routé)
4) vérifier que la validation backend corrige bien (enum/list)
5) si besoin : renforcer la consigne locale dans `FieldSpecV2.instructions` (pas global)

