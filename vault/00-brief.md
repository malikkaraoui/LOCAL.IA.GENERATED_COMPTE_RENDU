# Brief projet

> ⛔ **RÈGLE 1 — ANTI-HALLUCINATION ABSOLUE**
> Interdiction totale d'inventer, de mentir, d'halluciner.
> Si incertain → « Je ne peux pas l'affirmer » + 2-3 hypothèses + comment vérifier.

> Géré automatiquement par Claude. Markdown vivant, pas document gravé.

## État court

- **Projet :** SCRIPT.IA — Générateur automatisé de rapports RH professionnels (bilinguisme FR)
- **Version :** 2.0.1 (pyproject.toml + frontend/package.json)
- **Phase :** Post-livraison V3 — pipeline LLM robuste + qualité gate opérationnel
- **Stack :** Python 3.10+/FastAPI/Redis+RQ/Ollama (LLM local) · React 19+Vite 7+TypeScript · Streamlit 1.38 · python-docx · PyMuPDF
- **Objectif courant :** Validation empirique du socle SKI/Beyond-RAG sur client réel
- **Prochaine action utile :** Activer `knowledge_layer_enabled=True` sur 1 client réel et mesurer le delta quality gate BON/A_REVOIR avant vs après
- **Modèle LLM défaut :** qwen3-next:latest (Ollama local, timeout 120s)

## À lire en priorité

- `vault/30-discoveries.md` — avant toute question sur l'état du projet
- `vault/40-roadmap.md` — prochaines phases
- `core/instructions.md` — règles pipeline (404 lignes, référence technique)
- `core/field_specs_v3.py` — specs V3 des 7 sections rapport_initial

## Décisions actives

- Anti-hallucination stricte : champ vide + log si LLM invente — vérifié `core/generate.py`
- V3 field specs : immutabilité PROFESSION, required_elements par section
- Quality gate par section : BON / A_REVOIR / VIDE (section_evaluator)
- Double UI : React (frontend moderne) + Streamlit (legacy multi-pages)
- Tout passe par RQ workers — pas d'appel LLM synchrone en prod

## Risques / angles morts

- LibreOffice requis pour .doc/.rtf — non inclus dans requirements, dépendance système
- faster-whisper (audio RAG) : fonctionnalité avancée, couverture test partielle
- CI/CD absent — déploiement 100% manuel via scripts bash
- 26 répertoires CLIENTS/ dans le repo — données potentiellement sensibles
- Port Streamlit (8501) vs React (5173/5174) — deux entrées UI distinctes, risque confusion
- Restructuration Beyond-RAG ambitieuse — garder Obsidian comme pilier structurel interne, pas comme dépendance produit ni interface client
- Socle SKI livré mais gain terrain non encore mesuré sur dossier client réel
