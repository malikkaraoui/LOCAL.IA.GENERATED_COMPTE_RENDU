# LOCAL.IA – Generated Compte Rendu

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)
![Version](https://img.shields.io/badge/Version-V00.00.01-0A0A0A)
![Status](https://img.shields.io/badge/LLM-ready-brightgreen)

Application locale permettant d’orchestrer l’extraction de documents clients, la génération de champs via Ollama et le rendu automatique en DOCX/PDF. L’objectif est de produire des comptes rendus fiables en gardant toutes les données sensibles sur votre machine.

## 🚀 Fonctionnalités principales

- **Extraction unifiée** : ingestion PDF/DOCX/TXT (et DOC/RTF via LibreOffice) avec historisation des sources.
- **Recherche contextuelle** : découpage intelligent + index BM25 pour envoyer au LLM uniquement les passages pertinents.
- **Génération contrôlée** : prompts stricts (format `CHAMP=VALEUR`) avec batchs, suivi temps réel et journalisation `WHY`.
- **Rendu DOCX/PDF** : remplacement automatique des placeholders `{{CHAMP}}`, insertion des sections clés et export PDF optionnel.
- **Interface Streamlit** : pipeline guidé en 4 étapes + logs live LLM.

## 🧱 Architecture

```
app.py (UI Streamlit)
├── rapport_orchestrator.py (pipeline)
├── core/
│   ├── extract.py / context.py / generate.py / render.py
│   └── template_fields.py (détection des placeholders)
└── CLIENTS/ (données locales ignorées par Git)
```

La version courante de la pile est stockée dans `VERSION` (`V00.00.01`).

## 📦 Prérequis

- Python 3.13 (ou ≥3.10 recommandé)
- [Ollama](https://ollama.com/) avec le modèle `mistral:latest` (modifiable dans l’UI)
- LibreOffice (`soffice`) si vous souhaitez convertir les fichiers DOC/RTF.

## ⚙️ Installation

```bash
# Cloner le dépôt
git clone https://github.com/malikkaraoui/LOCAL.IA.GENERATED_COMPTE_RENDU.git
cd LOCAL.IA.GENERATED_COMPTE_RENDU

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # sous Windows: .venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

## ▶️ Lancer l’application

```bash
streamlit run app.py --server.port 8590
```

1. Indique le dossier client (non versionné) et le template DOCX local.
2. Clique sur **Extraire** pour générer `extracted.json`.
3. Clique sur **Générer les champs** : suis la progression champ par champ.
4. Termine avec **Rendre le DOCX** puis **Export PDF** si nécessaire.

Les sorties (`out/`, `uploaded_templates/`, `CLIENTS/`, etc.) restent sur ta machine et sont ignorées par Git.

## 🧪 Scripts CLI utiles

- `CLIENTS/generate_fields.py` : génération autonome des champs depuis un payload + template.
- `CLIENTS/render_docx.py` : rendu DOCX sans passer par l’UI.

Chaque script expose `--help` pour détailler les options (batch size, modèle, filtres include/exclude…).

## 📝 Versioning

La version applicative est centralisée dans le fichier `VERSION`. Mets‑le à jour (par ex. `V00.00.02`) avant de livrer une nouvelle release.

## 🔒 Licence

Projet interne / propriétaire. Merci de ne pas diffuser les données client : elles restent dans des dossiers ignorés (`CLIENTS/`, `out/`, etc.).
