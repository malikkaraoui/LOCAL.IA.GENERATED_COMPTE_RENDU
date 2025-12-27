#!/usr/bin/env python3
"""Interface Streamlit pour piloter l'orchestrateur de rapports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

from rapport_orchestrator import PipelineConfig, RapportOrchestrator

st.set_page_config(page_title="Rapports assistés", layout="wide")

# Navigation entre pages
if "current_page" not in st.session_state:
    st.session_state.current_page = "Générateur"

# Sidebar pour navigation
with st.sidebar:
    st.title("🧭 Navigation")
    page = st.radio(
        "Choisir une page",
        options=["Générateur", "Batch Parser RH-Pro"],
        index=0 if st.session_state.current_page == "Générateur" else 1
    )
    st.session_state.current_page = page

# Si Batch Parser, afficher la page dédiée
if st.session_state.current_page == "Batch Parser RH-Pro":
    from pages_streamlit.batch_parser import show_batch_parser_page
    show_batch_parser_page()
    st.stop()

# Sinon, continuer avec la page principale (Générateur)

if "history" not in st.session_state:
    st.session_state.history = []
if "last_logs" not in st.session_state:
    st.session_state.last_logs = []

SESSION_DEFAULTS = {
    "config_obj": None,
    "job_dir": None,
    "extracted_path": None,
    "payload": None,
    "answers_path": None,
    "answers": None,
    "report_path": None,
    "pdf_path": None,
    "progress": 0.0,
    "uploaded_template_path": None,
}
for key, val in SESSION_DEFAULTS.items():
    st.session_state.setdefault(key, val)

PREREQ_LABELS = {
    "payload": "Extraction",
    "answers": "Génération des champs",
    "report_path": "Rendu DOCX",
    "config_obj": "Configuration",
    "job_dir": "Répertoire de travail",
}


def list_subdirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")])


def build_callback(area):
    logs: list[str] = []

    def _cb(msg: str) -> None:
        logs.append(msg)
        area.write("\n".join(logs[-200:]))
        st.session_state.last_logs = logs.copy()

    return _cb


def build_config(
    *,
    clients_root: Path,
    selected_client: str,
    client_dirs: list[Path],
    template_path: Path,
    output_dir_input: str,
    model: str,
    topk: int,
    temperature: float,
    top_p: float,
    include_filters: str,
    exclude_filters: str,
    name: str,
    surname: str,
    civility: str,
    force_reextract: bool,
    enable_soffice: bool,
    auto_pdf: bool,
) -> Optional[PipelineConfig]:
    if selected_client == "<Sélectionner>" or not client_dirs:
        st.error("Merci de choisir un dossier client valide.")
        return None
    if not template_path.exists():
        st.error("Template introuvable.")
        return None

    return PipelineConfig(
        client_dir=clients_root / selected_client,
        template_path=template_path,
        output_dir=Path(output_dir_input),
        model=model,
        host="http://localhost:11434",
        topk=topk,
        temperature=temperature,
        top_p=top_p,
        include_filters=[s.strip() for s in include_filters.split(",") if s.strip()],
        exclude_filters=[s.strip() for s in exclude_filters.split(",") if s.strip()],
        name=name,
        surname=surname,
        civility=civility,
        force_reextract=force_reextract,
        enable_soffice=enable_soffice,
        export_pdf=auto_pdf,
    )


def reset_downstream_state() -> None:
    st.session_state.answers_path = None
    st.session_state.answers = None
    st.session_state.report_path = None
    st.session_state.pdf_path = None
    st.session_state.progress = 0.0


def ensure_prereq(keys: list[str]) -> bool:
    missing_labels = []
    for key in keys:
        if not st.session_state.get(key):
            missing_labels.append(PREREQ_LABELS.get(key, key))
    if missing_labels:
        st.error("Étape précédente requise : " + ", ".join(missing_labels))
        return False
    return True


def write_download_button(col, label: str, path: str, mime: str) -> None:
    with open(path, "rb") as fh:
        col.download_button(
            label,
            data=fh.read(),
            file_name=Path(path).name,
            mime=mime,
            use_container_width=True,
        )


def record_history(report_path: Optional[str], answers_path: Optional[str], extracted_path: Optional[str], pdf_path: Optional[str]) -> None:
    st.session_state.history.insert(0, {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "report": report_path,
        "answers": answers_path,
        "extracted": extracted_path,
        "pdf": pdf_path,
        "elapsed": None,
    })


st.title("🧠 Générateur de rapports assisté")

cols = st.columns(2)
with cols[0]:
    clients_root_input = st.text_input(
        "Dossier clients",
        value=str((Path.cwd() / "CLIENTS").resolve()),
        help="Racine contenant les sous-dossiers clients",
    )
    clients_root = Path(clients_root_input).expanduser()
    client_dirs = list_subdirs(clients_root)
    client_names = [p.name for p in client_dirs]
    selected_client = st.selectbox(
        "Client",
        options=["<Sélectionner>"] + client_names,
        index=0,
    )

    template_input = st.text_input(
        "Template DOCX",
        value=str((Path.cwd() / "TemplateRapportStage.docx").resolve()),
        help="Chemin complet vers le template (placeholders {{...}} pris en charge)",
    )
    uploaded_template = st.file_uploader("Téléverser un template (DOCX)", type=["docx"])
    if uploaded_template is not None:
        upload_dir = Path.cwd() / "uploaded_templates"
        upload_dir.mkdir(parents=True, exist_ok=True)
        uploaded_path = upload_dir / uploaded_template.name
        uploaded_path.write_bytes(uploaded_template.getbuffer())
        st.session_state.uploaded_template_path = str(uploaded_path)
    template_path = Path(
        st.session_state.uploaded_template_path or template_input
    ).expanduser()

    output_dir_input = st.text_input(
        "Dossier de sortie",
        value=str((Path.cwd() / "out").resolve()),
        help="Les jobs et artefacts seront stockés ici",
    )
with cols[1]:
    name = st.text_input("Prénom", value="")
    surname = st.text_input("Nom", value="")
    civility = st.selectbox("Civilité", ["Monsieur", "Madame", "Autre"], index=0)
    model = st.text_input("Modèle Ollama", value="mistral:latest")
    topk = st.slider("Top-K passages", min_value=3, max_value=20, value=10)
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.2, step=0.05)
    top_p = st.slider("Top-p", min_value=0.1, max_value=1.0, value=0.9, step=0.05)
    include_filters = st.text_input("Inclure chemins (séparés par ,)", value="")
    exclude_filters = st.text_input("Exclure chemins (séparés par ,)", value="")
    force_reextract = st.checkbox("Forcer la ré-extraction", value=False)
    enable_soffice = st.checkbox("Activer LibreOffice (DOC/RTF)", value=False)
    auto_pdf = st.checkbox("Exporter automatiquement en PDF", value=False)

logs_placeholder = st.empty()
progress_bar = st.progress(st.session_state.progress)

step_cols = st.columns(4)
extract_clicked = step_cols[0].button("1) Extraire", use_container_width=True)
create_fields_clicked = step_cols[1].button("2) Générer les champs", use_container_width=True)
render_clicked = step_cols[2].button("3) Rendre le DOCX", use_container_width=True)
pdf_clicked = step_cols[3].button("4) Export PDF", use_container_width=True)

if extract_clicked:
    config = build_config(
        clients_root=clients_root,
        selected_client=selected_client,
        client_dirs=client_dirs,
        template_path=template_path,
        output_dir_input=output_dir_input,
        model=model,
        topk=topk,
        temperature=temperature,
        top_p=top_p,
        include_filters=include_filters,
        exclude_filters=exclude_filters,
        name=name,
        surname=surname,
        civility=civility,
        force_reextract=force_reextract,
        enable_soffice=enable_soffice,
        auto_pdf=auto_pdf,
    )
    if config:
        callback = build_callback(logs_placeholder)
        orchestrator = RapportOrchestrator(status_callback=callback)
        try:
            cfg = orchestrator.resolve_config(config)
            job_dir = orchestrator.ensure_job_dir(cfg)
            extracted_path, payload, reused = orchestrator.extract_sources(
                cfg, job_dir, force=config.force_reextract or False
            )
        except Exception as exc:
            st.error(f"Erreur lors de l'extraction : {exc}")
        else:
            st.success("Extraction terminée.")
            st.session_state.config_obj = cfg
            st.session_state.job_dir = str(job_dir)
            st.session_state.extracted_path = str(extracted_path)
            st.session_state.payload = payload
            reset_downstream_state()
            st.session_state.progress = 0.25
            progress_bar.progress(st.session_state.progress)

if create_fields_clicked:
    if ensure_prereq(["payload", "config_obj", "job_dir"]):
        callback = build_callback(logs_placeholder)
        orchestrator = RapportOrchestrator(status_callback=callback)
        try:
            answers_path, answers = orchestrator.generate_fields(
                st.session_state.config_obj,
                Path(st.session_state.job_dir),
                st.session_state.payload,
            )
        except Exception as exc:
            st.error(f"Erreur lors de la génération des champs : {exc}")
        else:
            st.success("Champs générés.")
            st.session_state.answers_path = str(answers_path)
            st.session_state.answers = answers
            st.session_state.progress = max(st.session_state.progress, 0.5)
            progress_bar.progress(st.session_state.progress)

if render_clicked:
    if ensure_prereq(["answers", "config_obj", "job_dir"]):
        callback = build_callback(logs_placeholder)
        orchestrator = RapportOrchestrator(status_callback=callback)
        try:
            report_path = orchestrator.render_docx(
                st.session_state.config_obj,
                Path(st.session_state.job_dir),
                st.session_state.answers,
            )
        except Exception as exc:
            st.error(f"Erreur lors du rendu DOCX : {exc}")
        else:
            st.success("DOCX généré.")
            st.session_state.report_path = str(report_path)
            st.session_state.progress = max(st.session_state.progress, 0.75)
            progress_bar.progress(st.session_state.progress)

            auto_pdf_path = None
            if st.session_state.config_obj and st.session_state.config_obj.export_pdf:
                try:
                    auto_pdf_path = orchestrator.export_pdf(Path(report_path))
                except Exception as exc:
                    st.error(f"Conversion PDF automatique échouée : {exc}")
                else:
                    st.session_state.pdf_path = str(auto_pdf_path)
                    st.session_state.progress = max(st.session_state.progress, 1.0)
                    progress_bar.progress(st.session_state.progress)

            record_history(
                st.session_state.report_path,
                st.session_state.answers_path,
                st.session_state.extracted_path,
                st.session_state.pdf_path or (str(auto_pdf_path) if auto_pdf_path else None),
            )

if pdf_clicked:
    if ensure_prereq(["report_path"]):
        callback = build_callback(logs_placeholder)
        orchestrator = RapportOrchestrator(status_callback=callback)
        try:
            pdf_path = orchestrator.export_pdf(Path(st.session_state.report_path))
        except Exception as exc:
            st.error(f"Erreur lors de l'export PDF : {exc}")
        else:
            st.success("PDF généré.")
            st.session_state.pdf_path = str(pdf_path)
            st.session_state.progress = max(st.session_state.progress, 1.0)
            progress_bar.progress(st.session_state.progress)

st.subheader("Téléchargements")
download_cols = st.columns(2)
if st.session_state.report_path and Path(st.session_state.report_path).exists():
    write_download_button(
        download_cols[0],
        "Télécharger le DOCX",
        st.session_state.report_path,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
else:
    download_cols[0].info("Génère le DOCX pour activer le téléchargement.")

if st.session_state.pdf_path and Path(st.session_state.pdf_path).exists():
    write_download_button(
        download_cols[1],
        "Télécharger le PDF",
        st.session_state.pdf_path,
        "application/pdf",
    )
else:
    download_cols[1].info("Lance l’export PDF pour l’obtenir ici.")

st.divider()
st.subheader("Historique des jobs")
if not st.session_state.history:
    st.info("Aucun job exécuté pour l’instant.")
else:
    for job in st.session_state.history[:5]:
        elapsed = job.get("elapsed")
        label = f"Rapport {job['timestamp']}"
        if elapsed:
            label += f" ({elapsed:.1f}s)"
        with st.expander(label):
            st.write(f"**DOCX** : {job.get('report')}")
            st.write(f"**Answers** : {job.get('answers')}")
            st.write(f"**Extraction** : {job.get('extracted')}")
            if job.get("pdf"):
                st.write(f"**PDF** : {job.get('pdf')}")

st.subheader("Logs précédents")
if st.session_state.last_logs:
    st.code("\n".join(st.session_state.last_logs[-200:]), language="text")
else:
    st.info("Lance une étape pour voir les logs ici.")
