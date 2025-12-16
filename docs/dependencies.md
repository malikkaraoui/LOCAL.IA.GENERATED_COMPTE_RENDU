# Dépendances applicatives

Ce document récapitule les bibliothèques Python nécessaires au projet ainsi que leur rôle fonctionnel. Les versions minimales proviennent de `requirements.txt`. Mettez ce fichier à jour dès qu'une dépendance évolue afin de garder une traçabilité similaire au projet Cookie.

| Package        | Version min. | Rôle principal |
|----------------|--------------|----------------|
| `streamlit`    | 1.38         | Interface utilisateur pour piloter l'orchestrateur de rapports. |
| `python-docx`  | 0.8.11       | Lecture/écriture du template DOCX et génération du rapport final. |
| `PyMuPDF`      | 1.24         | Extraction du texte et des pages lors de l'étape d'ingestion des PDF. |

> ℹ️  Les dépendances optionnelles (LibreOffice `soffice`, Ollama, etc.) sont documentées dans le README. Pensez à synchroniser ce tableau lorsque `requirements.txt` change.
