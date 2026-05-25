# Mailbox projet

> Géré automatiquement par Claude. Markdown vivant, pas document gravé.

## Courrier entrant

### 2026-05-25 — Livraison socle SKI + prochaine mesure terrain [auto]

- Source : Claude Code — synthèse de livraison relayée par Malik
- Statut : traité
- Résumé : Le socle SKI est livré : `knowledge_builder` classe et indexe les documents client en notes Markdown + YAML, `context_builder` assemble un contexte ciblé par section V3 via templates QMD, le tout injecté dans `generate.py` derrière feature flag `knowledge_layer_enabled=False` par défaut. Hors scope volontaire du lot : `graph_builder.py`, UI/frontend, fine-tuning et Q/R client.
- Prochaine action : activer le flag sur 1 client réel et mesurer le delta quality gate BON/A_REVOIR avant vs après pour valider le gain empirique

### 2026-05-25 — Relecture Beyond-RAG + avis stratégique [auto]

- Source : Claude Code — relecture demandée par Malik
- Statut : traité
- Résumé : Correction ciblée des fautes et formulations maladroites dans `docs/plans/2026-05-25-beyond-rag-obsidian-qmd.md` et `vault/40-roadmap.md`. Avis de fond : la restructuration de l'indexation client est pertinente si elle reste incrémentale ; la bonne séquence est notes structurées → context_builder → mesures A/B, puis graphe relationnel seulement si le gain est réel.
- Prochaine action : lancer un prototype Phase 1 + Phase 2 sur 1 à 3 dossiers clients avant toute généralisation

### 2026-05-25 — Clarification stratégique Beyond-RAG [auto]

- Source : Claude Code — clarification demandée par Malik
- Statut : traité
- Résumé : Documentation mise à jour pour poser explicitement qu'Obsidian est un pilier structurel interne, jamais le cœur runtime ni un outil client. Le socle visé est une base de connaissance Markdown/YAML/JSON plus fiable, plus résistante, plus rapide et plus pertinente, réutilisable ensuite pour les rapports, les questions ciblées sur un client et les comptes rendus à la volée.
- Prochaine action : reboucler avec Claude Code sur l'implémentation du socle utile (indexation + context_builder)

### 2026-05-22 — Session initialisation vault [auto]

- Source : Claude Code — exploration complète à la demande de Malik
- Statut : traité
- Résumé : Projet SCRIPT.IA v2.0.1 — générateur de rapports RH automatisé. Stack Python/FastAPI/Redis/RQ/Ollama + React/Vite + Streamlit. Pipeline V3 opérationnel (extract → RAG → LLM → render DOCX). Quality gates actifs (BON/A_REVOIR/VIDE). 77 fichiers de tests. Dernier commit fix : remplissage placeholders DOCX export + doc config LLM. Vault vide au démarrage — initialisation complète effectuée.
- Prochaine action : continuer le développement sur branch `dev` — voir vault/40-roadmap.md

### 2026-05-22 — Vault initialisé [auto]

- Source : setup-project-vaults.py
- Statut : archivé
- Résumé : Vault créé pour le projet SCRIPT.IA. Les sessions futures doivent alimenter ce fichier à chaque clôture significative.
- Prochaine action : première session → compléter vault/00-brief.md + vault/40-roadmap.md
