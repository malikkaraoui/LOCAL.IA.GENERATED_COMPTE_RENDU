# SCRIPT.IA — Architecture, Pipeline et Evolution

## 1. Vue d'ensemble du projet

SCRIPT.IA est un système de génération automatique de bilans professionnels pour l'Office Cantonal des Assurances Sociales (OCAS) à Genève. Il prend en entrée un dossier client (PDF, DOCX, MSG, audio) et produit un rapport DOCX structuré de 53 sections, en utilisant un LLM local (Ollama) guidé par un système RAG (Retrieval-Augmented Generation).

Le problème résolu : les conseillers ORP passaient plusieurs heures à rédiger manuellement chaque bilan. SCRIPT.IA automatise l'extraction d'information depuis les documents sources et la rédaction de chaque section, tout en garantissant qu'aucun contenu n'est inventé.

---

## 2. Stack technique

### Backend
- **Python 3.11+** avec **FastAPI** comme framework API REST
- **Ollama** (LLM local, modèle Mistral/Llama) — aucune donnée ne quitte le réseau local
- **Redis + RQ** (Redis Queue) pour le traitement asynchrone des rapports
- **python-docx** pour la manipulation de documents Word
- **PyMuPDF** pour l'extraction PDF
- **extract-msg** pour les fichiers Outlook .msg
- **faster-whisper** pour la transcription audio (STT)
- **BM25** (implémentation custom) pour le retrieval RAG

### Frontend
- **React 19** avec **Vite** comme bundler
- **Tailwind CSS** pour le design
- **React Router** pour la navigation SPA
- **Axios** pour les appels API

### Infrastructure
- Pas de cloud : tout tourne en local (contrainte OCAS — données sensibles assurés)
- Redis comme broker de jobs
- Ollama comme serveur LLM local

---

## 3. Architecture du pipeline

Le traitement d'un dossier client suit 3 étapes séquentielles orchestrées par `backend/workers/orchestrator.py` :

### Etape 1 : Extraction (`core/extract.py`)

Chaque fichier du dossier client est parsé selon son type :
- **PDF** → PyMuPDF (texte + structure)
- **DOCX** → python-docx (paragraphes + styles)
- **MSG** → extract-msg (corps de mail)
- **Audio** → faster-whisper (transcription)

Le texte extrait est découpé en **chunks de 1200 caractères** avec un **overlap de 200 caractères**, puis indexé dans un store BM25 avec stopwords français. Ce store RAG sert ensuite de mémoire pour le LLM.

### Etape 2 : Génération (`core/generate.py`)

Pour chaque champ du schéma (53 champs), le système :

1. **Récupère le contexte pertinent** via BM25 (top-K chunks les plus proches de la question)
2. **Construit un prompt structuré** avec :
   - Les instructions spécifiques au champ (ton, longueur, contraintes)
   - Le contexte RAG extrait des documents
   - Les garde-fous anti-hallucination
3. **Appelle le LLM** (Ollama) avec ce prompt
4. **Valide la sortie** : détection de contenu interdit, vérification des contraintes (max chars, enum valides, max items pour les listes)

Le traitement varie selon le type de champ :
- **Déterministe** (5 champs) : extraction directe par regex, pas de LLM (nom, prénom, AVS, civilité, lieu/date)
- **Narratif** (26 champs) : rédaction libre par le LLM, max 2000-3000 caractères
- **Liste** (8 champs) : liste à puces, max 4 items, max 2000 caractères
- **Enum** (7 champs) : extraction stricte parmi valeurs autorisées (CECRL A1-C2, Faible/Moyen/Bon/Très bon, OK/Moyen/À renforcer), jamais d'invention
- **Test narratif** (7 champs) : paragraphe court (max 1000 chars, 5 lignes) pour résultats de tests psychométriques

### Etape 3 : Rendu (`core/render.py`)

Le système ouvre le template DOCX et :
1. Remplace les **placeholders moustache** (`{{NOM}}`, `{{PROFESSION}}`, etc.)
2. Remplace le **contenu des sections** entre les titres (supprime l'ancien texte, insère le nouveau)
3. **Supprime les sections vides** : si le LLM n'a pas trouvé d'information ou retourne "Non renseigné", la section entière (titre inclus) est retirée du document final

---

## 4. Le schéma V2 : 53 champs

Le schéma de champs (`core/field_specs_v2.py`) définit pour chaque section :
- Le **type** (deterministic, narrative, list, enum, test_narrative)
- Les **instructions LLM** (ton, contenu attendu, ce qu'il faut éviter)
- Les **contraintes** (max_chars, max_items, max_lines)
- La **politique d'extraction** (extract_only, deterministic, llm_with_context)
- Si des **sources sont requises** (require_sources, skip_llm_if_no_sources)
- Les **valeurs autorisées** pour les enums

Organisation des 53 champs :

| Catégorie | Champs | Type |
|-----------|--------|------|
| Identité | Civilité, Nom, Prénom, Lieu/Date, N° AVS | Déterministe |
| Parcours | Profession, Formation, Expérience pro, Formations sup., Formations hautes écoles | Narratif/Liste |
| Langues | Français, Anglais, Allemand (niveau CECRL) | Enum |
| Bureautique | Word, Excel, PowerPoint, Outlook (niveau) | Enum |
| Ressources | Motivationnelles, Comportementales (appui + vigilance), Interpersonnelles, Conditions de succès | Narratif |
| Orientation | Contexte organisation, Rôle, Activités, Activités/Fonctions privilégiées | Narratif |
| RIASEC/Vocatio | Vocatio, Domaines pro, Correspondance RIASEC, Rôles, Professions | Narratif |
| Tests psycho | Tri/classement, Attention admin, Calcul, Dimensions/volumes, Comptabilité, Compréhension consignes, Saisie commandes | Test narratif |
| Synthèse | Discussion assuré, Compétences sociales, Stage, Orientation, Conclusion, CV, Lettre motivation | Narratif |

---

## 5. Système anti-hallucination

C'est le coeur de la qualité. Plusieurs mécanismes empêchent le LLM d'inventer :

### Extraction stricte pour les enums
Les champs enum (langues, bureautique, tests) ne passent **jamais** par le LLM. Un extracteur déterministe (`core/enum_extractors_v2.py`) utilise des regex et mots-clés pour trouver la valeur exacte. Si rien n'est trouvé → "Non évalué". Jamais d'inférence.

Pour la bureautique, l'extraction est **scopée par phrase** : quand on cherche le niveau Excel, on ne regarde que les phrases qui mentionnent "Excel" ou "tableur". Cela évite qu'une mention "bonne maîtrise de Word" dans la même section ne contamine le score Excel.

### Garde-fous dans le prompt
Chaque prompt LLM contient :
- Un marqueur sentinelle `[[FIELD_SPECS_V2_PROMPT_V1]]` qui identifie la version du prompt
- Des instructions explicites : "Ne jamais inventer", "S'appuyer uniquement sur les extraits fournis"
- La détection de phrases interdites ("je n'ai pas d'information", "aucune donnée disponible") qui déclenchent un retry ou un abandon propre

### Validation post-génération
- Les listes sont tronquées à 4 items max
- Les narratifs sont coupés à leur max_chars
- Les enums invalides sont remplacés par "Non évalué"
- Les champs avec `require_sources=True` (CV, Lettre de motivation) sautent le LLM si aucun document source n'est trouvé

### Suppression des sections vides
Plutôt que laisser une section avec un titre sans contenu, le rendu supprime entièrement la section. Les valeurs "Non renseigné", "Non évalué", et "[]" sont traitées comme vides.

---

## 6. L'entraînement sur ~580 clients

### A quoi ça a servi

Le dossier `src/rhpro/` contient un pipeline complet de traitement de données d'entraînement basé sur ~580 dossiers clients réels de l'OCAS.

### Ce qu'on en a tiré

1. **Calibration des instructions LLM** : En analysant les bilans GOLD (rapports de référence rédigés par des humains), on a pu déterminer le ton, la longueur, le style attendu pour chaque section. Les instructions dans `field_specs_v2.py` sont directement dérivées de cette analyse.

2. **Construction du RAG** : Les documents clients (580 dossiers × ~5-15 documents chacun) ont permis de tester et optimiser les paramètres du chunking BM25 (taille de chunk 1200, overlap 200, stopwords français).

3. **Validation et normalisation** : `normalizer.py` (40KB) et `dataset_training.py` (96KB) transforment les dossiers bruts en datasets structurés. Chaque client est scanné (`client_scanner.py`), ses documents sont segmentés (`segmenter.py`), les champs sont mappés (`mapper.py`), et le tout est normalisé.

4. **Détection des patterns** : L'analyse de masse a révélé :
   - Quels champs sont systématiquement remplis vs souvent vides
   - Les formulations récurrentes par section
   - Les pièges d'extraction (sections similaires, titres ambigus)
   - La nécessité de séparer bureautique en 4 champs distincts

5. **Règles de validation** : `config/rulesets/rhpro_v1.yaml` définit des règles de validation dérivées de l'analyse statistique des 580 dossiers.

### Pipeline d'entraînement

```
Dossiers clients (580)
    → client_scanner.py (scan filesystem)
    → identity_extractor.py (extraction identité)
    → positionnement_extractor.py (extraction niveaux)
    → segmenter.py (découpage en sections)
    → normalizer.py (normalisation)
    → dataset_training.py (construction dataset)
    → gold_diagnostics.py (comparaison avec GOLD)
    → validation_profiles.py (règles de qualité)
```

---

## 7. Evolution : scaler et augmenter la qualité

### Court terme : améliorations immédiates

**Prompt engineering avancé**
- Few-shot examples par section (injecter 2-3 exemples GOLD dans le prompt)
- Chain-of-thought pour les sections complexes (orientation, conclusion)
- Self-consistency : générer 3 variantes et prendre le consensus

**RAG amélioré**
- Passer de BM25 pur à un **hybrid retrieval** (BM25 + embeddings sémantiques via sentence-transformers, déjà dans les dépendances)
- Reranking des chunks avec un cross-encoder
- Metadata-aware retrieval : taguer les chunks par type de document source (CV, entretien, test) pour prioriser les bonnes sources par section

**Validation renforcée**
- Score de confiance par section (le LLM auto-évalue sa certitude)
- Détection de contradictions inter-sections
- Comparaison automatique avec les bilans GOLD similaires

### Moyen terme : scaling

**Multi-tenancy**
- Actuellement single-user, évoluer vers un système multi-conseillers avec files d'attente Redis séparées
- Dashboard de suivi des générations en cours
- Historique et versioning des rapports

**Modèle LLM**
- Passer d'Ollama local à un cluster GPU dédié pour traiter plusieurs rapports en parallèle
- Fine-tuning d'un modèle spécialisé sur les bilans OCAS (les 580 dossiers GOLD comme training set)
- Evaluation automatique (ROUGE, BERTScore) contre les GOLD pour mesurer la qualité objectivement

**Pipeline batch**
- Traitement de lots de dossiers en mode batch (nuit/weekend)
- Pré-extraction et indexation RAG des nouveaux documents dès leur arrivée
- Cache intelligent : si un document a déjà été extrait, ne pas le re-traiter

### Long terme : qualité maximale

**Human-in-the-loop**
- Interface de révision où le conseiller valide/corrige chaque section
- Les corrections alimentent un dataset de feedback pour améliorer le modèle
- Apprentissage continu : chaque rapport validé améliore le système

**Evaluation continue**
- Suite de tests automatisés comparant chaque génération aux GOLD
- Métriques de qualité par section (précision, rappel, cohérence)
- Alertes si la qualité baisse sur un type de section

**Architecture microservices**
- Séparer extraction, génération et rendu en services indépendants
- Chaque service peut scaler indépendamment
- API Gateway pour router les requêtes
- Event-driven : chaque étape publie un événement, le suivant consomme

---

## 8. Résumé technique

| Composant | Technologie | Rôle |
|-----------|-------------|------|
| API | FastAPI + Uvicorn | Endpoints REST |
| Queue | Redis + RQ | Jobs asynchrones |
| LLM | Ollama (local) | Génération de texte |
| RAG | BM25 custom | Retrieval de contexte |
| Extraction | PyMuPDF, python-docx, extract-msg | Parsing documents |
| STT | faster-whisper | Transcription audio |
| Rendu | python-docx | Génération DOCX |
| Frontend | React + Vite + Tailwind | Interface utilisateur |
| Training | 22 scripts Python (src/rhpro/) | Pipeline données |

**Chiffres clés :**
- 53 champs dans le schéma V2
- 5 types de champs (deterministic, narrative, list, enum, test_narrative)
- ~580 dossiers clients analysés pour l'entraînement
- 1200 chars par chunk RAG, overlap 200
- 0 donnée envoyée au cloud (LLM local)
- 702 tests passants, 0 régression
