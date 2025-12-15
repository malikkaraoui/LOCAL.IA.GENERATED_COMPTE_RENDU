#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interface Streamlit pour piloter l'orchestrateur de rapports."""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import streamlit as st

from rapport_orchestrator import PipelineConfig, RapportOrchestrator
from core.generate import check_llm_status, DEFAULT_FIELDS
from core.location_date import build_location_date


def _load_version() -> str:
    version_file = Path("VERSION")
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip() or "dev"
    return "dev"


APP_VERSION = _load_version()

st.set_page_config(page_title="Rapports assistés", layout="wide")

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
    "stage_status": None,
    "stage_messages": None,
    "live_llm_logs": None,
    "field_progress": None,
    "field_order": [],
    "location_city": "Genève",
    "location_date_manual": "",
    "auto_location_date": True,
    "location_date": "",
    "avs_number": "",
}
for key, val in SESSION_DEFAULTS.items():
    st.session_state.setdefault(key, val)

render_field_progress = None

STAGES = [
    ("extract", "Extraction"),
    ("generate", "Champs LLM"),
    ("render", "Rendu DOCX"),
    ("pdf", "Export PDF"),
]
STAGE_KEYS = [key for key, _ in STAGES]
STATUS_LABELS = {
    "pending": "En attente",
    "running": "En cours",
    "done": "Terminé",
    "error": "Erreur",
}

FIELD_STAGE_LABELS = {
    "pending": "En attente",
    "start": "Préparation",
    "context": "Contexte prêt",
    "prompt": "Prompt envoyé",
    "response": "Réponse reçue",
    "retry": "Correction",
    "done": "Terminé",
    "warning": "Réponse vide",
    "error": "Erreur",
}
FIELD_STAGE_ICONS = {
    "pending": "⏳",
    "start": "⚙️",
    "context": "📚",
    "prompt": "📤",
    "response": "📥",
    "retry": "♻️",
    "done": "✅",
    "warning": "⚠️",
    "error": "❌",
}
FIELD_STUCK_THRESHOLD = 90  # seconds


def _ensure_stage_states() -> None:
    if st.session_state.stage_status is None:
        st.session_state.stage_status = {k: "pending" for k in STAGE_KEYS}
    if st.session_state.stage_messages is None:
        st.session_state.stage_messages = {k: "" for k in STAGE_KEYS}
    if st.session_state.live_llm_logs is None:
        st.session_state.live_llm_logs = []


_ensure_stage_states()


def set_stage_status(stage: str, status: str, message: str = "") -> None:
    st.session_state.stage_status[stage] = status
    st.session_state.stage_messages[stage] = message


def reset_stages_from(stage: str) -> None:
    start_reset = False
    for key in STAGE_KEYS:
        if key == stage:
            start_reset = True
        if start_reset:
            set_stage_status(key, "pending", "")
    if stage in {"extract", "generate"}:
        reset_field_progress()


def reset_workflow(full: bool = True) -> None:
    st.session_state.history = [] if full else st.session_state.history
    st.session_state.last_logs = []
    st.session_state.live_llm_logs = []
    st.session_state.config_obj = None
    st.session_state.job_dir = None
    st.session_state.extracted_path = None
    st.session_state.payload = None
    st.session_state.answers_path = None
    st.session_state.answers = None
    st.session_state.report_path = None
    st.session_state.pdf_path = None
    st.session_state.progress = 0.0
    st.session_state.stage_status = {k: "pending" for k in STAGE_KEYS}
    st.session_state.stage_messages = {k: "" for k in STAGE_KEYS}
    st.session_state.field_progress = None
    st.session_state.field_order = []


def reset_field_progress() -> None:
    st.session_state.field_progress = None
    st.session_state.field_order = []


def humanize_delta(delta_seconds: float) -> str:
    if delta_seconds < 1:
        return "juste maintenant"
    if delta_seconds < 60:
        return f"{int(delta_seconds)} s"
    minutes, seconds = divmod(int(delta_seconds), 60)
    if minutes < 60:
        return f"{minutes} min {seconds:02d} s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min"


def sanitize_markdown(text: str) -> str:
    return (text or "").replace("|", "\\|")


def make_field_progress_renderer(container):
    def _render() -> None:
        data = st.session_state.field_progress or {}
        if not data:
            container.info("Lance la génération pour suivre les champs ici.")
            return
        now = datetime.now()
        rows = ["| Champ | Statut | Activité | Détails |", "| --- | --- | --- | --- |"]
        for key in st.session_state.field_order or data.keys():
            info = data.get(key)
            if not info:
                continue
            stage = info.get("stage", "pending")
            label = info.get("label") or key
            icon = FIELD_STAGE_ICONS.get(stage, "•")
            stage_label = FIELD_STAGE_LABELS.get(stage, stage)
            updated_at = info.get("updated_at")
            if updated_at:
                age = now - datetime.fromisoformat(updated_at)
                age_seconds = age.total_seconds()
                age_text = humanize_delta(age_seconds)
                warn = " ⚠️" if stage not in {"done", "warning", "error"} and age_seconds > FIELD_STUCK_THRESHOLD else ""
                activity = f"{age_text}{warn}"
            else:
                activity = "—"
            message = sanitize_markdown(info.get("message", "")) or "—"
            rows.append(f"| `{key}` | {icon} {stage_label} | {activity} | {message} |")
        container.markdown("\n".join(rows), unsafe_allow_html=False)

    return _render


def initialize_field_progress(fields_def: List[Dict[str, Any]]) -> None:
    st.session_state.field_progress = {}
    st.session_state.field_order = []
    now_iso = datetime.now().isoformat()
    for field in fields_def:
        key = field.get("key")
        if not key:
            continue
        label = field.get("label") or field.get("title") or key.replace("_", " ").title()
        st.session_state.field_order.append(key)
        st.session_state.field_progress[key] = {
            "label": label,
            "stage": "pending",
            "message": "En attente",
            "updated_at": now_iso,
        }


def field_progress_callback(field_key: str, stage: str, message: str) -> None:
    data = st.session_state.field_progress or {}
    if field_key not in data:
        data[field_key] = {
            "label": field_key.replace("_", " ").title(),
            "stage": "pending",
            "message": "",
            "updated_at": datetime.now().isoformat(),
        }
        st.session_state.field_order.append(field_key)
    data[field_key]["stage"] = stage
    data[field_key]["message"] = message
    data[field_key]["updated_at"] = datetime.now().isoformat()
    st.session_state.field_progress = data
    if render_field_progress:
        render_field_progress()


@st.cache_data(ttl=30)
def cached_llm_status(host: str, model: str):
    return check_llm_status(host, model)

PREREQ_LABELS = {
    "payload": "Extraction",
    "answers": "Génération des champs",
    "report_path": "Rendu DOCX",
    "config_obj": "Configuration",
    "job_dir": "Répertoire de travail",
}


def list_subdirs(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")])


def build_callback(area, live_now=None, llm_box=None):
    logs: List[str] = st.session_state.last_logs.copy()

    def _cb(msg: str) -> None:
        logs.append(msg)
        area.write("\n".join(logs[-200:]))
        st.session_state.last_logs = logs.copy()
        if live_now is not None:
            ts = datetime.now().strftime("%H:%M:%S")
            live_now.info(f"[{ts}] {msg}")
        if llm_box is not None and "LLM" in msg.upper():
            st.session_state.live_llm_logs.append(msg)
            llm_box.code("\n".join(st.session_state.live_llm_logs[-40:]), language="text")

    return _cb


def build_config(
    *,
    clients_root: Path,
    selected_client: str,
    client_dirs: List[Path],
    template_path: Path,
    output_dir_input: str,
    model: str,
    host: str,
    topk: int,
    temperature: float,
    top_p: float,
    include_filters: str,
    exclude_filters: str,
    name: str,
    surname: str,
    civility: str,
    location_city: str,
    location_date_manual: str,
    auto_location_date: bool,
    avs_number: str,
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

    final_location_date = build_location_date(
        location_city,
        location_date_manual,
        auto_date=auto_location_date,
    )

    return PipelineConfig(
        client_dir=clients_root / selected_client,
        template_path=template_path,
        output_dir=Path(output_dir_input),
        model=model,
        host=host,
        topk=topk,
        temperature=temperature,
        top_p=top_p,
        include_filters=[s.strip() for s in include_filters.split(",") if s.strip()],
        exclude_filters=[s.strip() for s in exclude_filters.split(",") if s.strip()],
        name=name,
        surname=surname,
        civility=civility,
        location_city=location_city,
        auto_location_date=auto_location_date,
        location_date_manual=location_date_manual,
        location_date=final_location_date,
        avs_number=avs_number,
        force_reextract=force_reextract,
        enable_soffice=enable_soffice,
        export_pdf=auto_pdf,
    )


def reset_downstream_state(stage_key: str = "generate") -> None:
    st.session_state.answers_path = None
    st.session_state.answers = None
    st.session_state.report_path = None
    st.session_state.pdf_path = None
    if stage_key == "extract":
        st.session_state.config_obj = None
        st.session_state.job_dir = None
        st.session_state.extracted_path = None
        st.session_state.payload = None
    reset_stages_from(stage_key)


def ensure_prereq(keys: List[str]) -> bool:
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
st.caption(f"Version {APP_VERSION}")

st.markdown(
    """
    <style>
    .stage-card {
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.02);
        padding: 0.75rem;
        border-radius: 0.6rem;
        min-height: 6rem;
    }
    .stage-title {
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    .badge {
        display: inline-block;
        padding: 0.15rem 0.7rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-pending { background: #6c757d; }
    .badge-running { background: #0d6efd; }
    .badge-done { background: #198754; }
    .badge-error { background: #d9534f; }
    .stage-message {
        font-size: 0.8rem;
        margin-top: 0.35rem;
        color: rgba(255,255,255,0.7);
        min-height: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.button("🔄 Réinitialiser le workflow", type="secondary"):
    reset_workflow(full=False)
    st.rerun()

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
    location_city = st.text_input(
        "Lieu",
        value=st.session_state.get("location_city", "Genève"),
        placeholder="Genève",
        help="Nom de la ville affichée dans {{LIEU_ET_DATE}}",
    )
    auto_location_date = st.checkbox(
        "Utiliser automatiquement la date du jour",
        value=st.session_state.get("auto_location_date", True),
        help="Si coché, la date sera recalculée à chaque lancement de la génération.",
    )
    manual_location_date = st.text_input(
        "Date / texte manuel",
        value=st.session_state.get("location_date_manual", st.session_state.get("location_date", "")),
        placeholder="15/12/2025 ou Genève, le 15/12/2025",
        disabled=auto_location_date,
        help="Renseigner ici la date complète si tu désactives l'automatisation.",
    )
    location_preview = build_location_date(
        location_city,
        manual_location_date,
        auto_date=auto_location_date,
    )
    st.session_state.location_city = location_city
    st.session_state.auto_location_date = auto_location_date
    st.session_state.location_date_manual = manual_location_date
    st.session_state.location_date = location_preview
    st.caption(f"Prévisualisation {{LIEU_ET_DATE}} : {location_preview or '—'}")
    avs_number = st.text_input(
        "Numéro AVS (jamais généré)",
        value=st.session_state.get("avs_number", ""),
        placeholder="756.XXXX.XXXX.XX",
        help="Saisir manuellement le numéro AVS exact, sans passer par l'IA.",
    )
    st.session_state.avs_number = avs_number
    model = st.text_input("Modèle Ollama", value="mistral:latest")
    llm_host = st.text_input("Serveur Ollama", value=st.session_state.get("llm_host_value", "http://localhost:11434"))
    st.session_state.llm_host_value = llm_host
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

st.subheader("Suivi temps réel")
live_status_placeholder = st.empty()
llm_stream_placeholder = st.empty()
if st.session_state.live_llm_logs:
    llm_stream_placeholder.code("\n".join(st.session_state.live_llm_logs[-40:]), language="text")
else:
    llm_stream_placeholder.info("Lance la génération pour voir le flux LLM ici.")

status_cols = st.columns([4, 1])
with status_cols[0]:
    try:
        llm_ok, llm_message = cached_llm_status(llm_host, model)
    except Exception as exc:
        cached_llm_status.clear()
        llm_ok, llm_message = False, f"Erreur lors de la vérification : {exc}"
    if llm_ok:
        st.success(f"LLM disponible : {llm_message}")
    else:
        st.error(f"LLM indisponible : {llm_message}")
with status_cols[1]:
    if st.button("↻ Rafraîchir LLM", use_container_width=True):
        cached_llm_status.clear()
        st.rerun()

st.subheader("Suivi des étapes")
stage_cols = st.columns(len(STAGES))
for (key, label), col in zip(STAGES, stage_cols):
    status = st.session_state.stage_status.get(key, "pending")
    badge_label = STATUS_LABELS.get(status, status)
    message = st.session_state.stage_messages.get(key, "") or "&nbsp;"
    safe_msg = html.escape(message) if message != "&nbsp;" else message
    col.markdown(
        f"""
        <div class="stage-card">
            <div class="stage-title">{label}</div>
            <div class="badge badge-{status}">{badge_label}</div>
            <div class="stage-message">{safe_msg}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.expander("Règles LLM (instructions.md)"):
    st.markdown(
        """
        - Réponses **100% en français**, sans JSON ni Markdown.
        - Si l'information manque : écrire `__VIDE__` (le script remplace par vide).
        - Champs courts ≤ 1 ligne / 50 caractères ; narratifs ≤ 4 lignes.
        - Valeurs contraintes : niveaux linguistiques (A1→C2), bureautique (Faible→Très bon), tests (OK/Moyen/À renforcer/Non évalué).
        - Aucune invention : seules les sources sélectionnées peuvent être citées.
        """
    )

st.subheader("Progression des champs LLM")
field_progress_placeholder = st.empty()
render_field_progress = make_field_progress_renderer(field_progress_placeholder)
render_field_progress()

extract_disabled = st.session_state.stage_status["extract"] in ("running", "done")
generate_disabled = (
    st.session_state.stage_status["extract"] != "done"
    or st.session_state.stage_status["generate"] in ("running", "done")
)
render_disabled = (
    st.session_state.stage_status["generate"] != "done"
    or st.session_state.stage_status["render"] in ("running", "done")
)
pdf_disabled = (
    st.session_state.stage_status["render"] != "done"
    or st.session_state.stage_status["pdf"] in ("running", "done")
)

step_cols = st.columns(4)
extract_clicked = step_cols[0].button("1) Extraire", use_container_width=True, disabled=extract_disabled)
create_fields_clicked = step_cols[1].button("2) Générer les champs", use_container_width=True, disabled=generate_disabled)
render_clicked = step_cols[2].button("3) Rendre le DOCX", use_container_width=True, disabled=render_disabled)
pdf_clicked = step_cols[3].button("4) Export PDF", use_container_width=True, disabled=pdf_disabled)

if st.session_state.config_obj:
    st.session_state.config_obj.host = llm_host
    st.session_state.config_obj.model = model
    st.session_state.config_obj.location_city = location_city
    st.session_state.config_obj.auto_location_date = auto_location_date
    st.session_state.config_obj.location_date_manual = manual_location_date
    st.session_state.config_obj.location_date = location_preview
    st.session_state.config_obj.avs_number = avs_number

if extract_clicked:
    set_stage_status("extract", "running", "Préparation de l'extraction...")
    config = build_config(
        clients_root=clients_root,
        selected_client=selected_client,
        client_dirs=client_dirs,
        template_path=template_path,
        output_dir_input=output_dir_input,
        model=model,
        host=llm_host,
        topk=topk,
        temperature=temperature,
        top_p=top_p,
        include_filters=include_filters,
        exclude_filters=exclude_filters,
        name=name,
        surname=surname,
        civility=civility,
        location_city=location_city,
        location_date_manual=manual_location_date,
        auto_location_date=auto_location_date,
        avs_number=avs_number,
        force_reextract=force_reextract,
        enable_soffice=enable_soffice,
        auto_pdf=auto_pdf,
    )
    if config:
        callback = build_callback(logs_placeholder, live_status_placeholder, llm_stream_placeholder)
        orchestrator = RapportOrchestrator(status_callback=callback)
        try:
            cfg = orchestrator.resolve_config(config)
            job_dir = orchestrator.ensure_job_dir(cfg)
            extracted_path, payload, reused = orchestrator.extract_sources(
                cfg, job_dir, force=config.force_reextract or False
            )
        except Exception as exc:
            st.error(f"Erreur lors de l'extraction : {exc}")
            set_stage_status("extract", "error", str(exc))
        else:
            st.success("Extraction terminée.")
            st.session_state.config_obj = cfg
            st.session_state.job_dir = str(job_dir)
            st.session_state.extracted_path = str(extracted_path)
            st.session_state.payload = payload
            reset_downstream_state("generate")
            st.session_state.progress = 0.25
            progress_bar.progress(st.session_state.progress)
            set_stage_status("extract", "done", "Extraction terminée")
    else:
        set_stage_status("extract", "pending", "Complète les champs requis")

if create_fields_clicked:
    if ensure_prereq(["payload", "config_obj", "job_dir"]):
        set_stage_status("generate", "running", "Préparation de la requête LLM...")
        st.session_state.live_llm_logs = []
        fields_def = (st.session_state.config_obj.fields or DEFAULT_FIELDS) if st.session_state.config_obj else DEFAULT_FIELDS
        initialize_field_progress(fields_def)
        render_field_progress()
        callback = build_callback(logs_placeholder, live_status_placeholder, llm_stream_placeholder)
        orchestrator = RapportOrchestrator(status_callback=callback)
        try:
            answers_path, answers = orchestrator.generate_fields(
                st.session_state.config_obj,
                Path(st.session_state.job_dir),
                st.session_state.payload,
                progress_callback=field_progress_callback,
            )
        except Exception as exc:
            st.error(f"Erreur lors de la génération des champs : {exc}")
            set_stage_status("generate", "error", str(exc))
        else:
            st.success("Champs générés.")
            st.session_state.answers_path = str(answers_path)
            st.session_state.answers = answers
            st.session_state.report_path = None
            st.session_state.pdf_path = None
            st.session_state.progress = max(st.session_state.progress, 0.5)
            progress_bar.progress(st.session_state.progress)
            set_stage_status("generate", "done", "Champs générés")
            reset_stages_from("render")

if render_clicked:
    if ensure_prereq(["answers", "config_obj", "job_dir"]):
        set_stage_status("render", "running", "Génération du DOCX en cours...")
        callback = build_callback(logs_placeholder, live_status_placeholder, llm_stream_placeholder)
        orchestrator = RapportOrchestrator(status_callback=callback)
        try:
            report_path = orchestrator.render_docx(
                st.session_state.config_obj,
                Path(st.session_state.job_dir),
                st.session_state.answers,
            )
        except Exception as exc:
            st.error(f"Erreur lors du rendu DOCX : {exc}")
            set_stage_status("render", "error", str(exc))
        else:
            st.success("DOCX généré.")
            st.session_state.report_path = str(report_path)
            st.session_state.progress = max(st.session_state.progress, 0.75)
            progress_bar.progress(st.session_state.progress)
            set_stage_status("render", "done", "DOCX généré")

            auto_pdf_path = None
            if st.session_state.config_obj and st.session_state.config_obj.export_pdf:
                set_stage_status("pdf", "running", "Conversion PDF automatique...")
                try:
                    auto_pdf_path = orchestrator.export_pdf(Path(report_path))
                except Exception as exc:
                    st.error(f"Conversion PDF automatique échouée : {exc}")
                    set_stage_status("pdf", "error", str(exc))
                else:
                    st.session_state.pdf_path = str(auto_pdf_path)
                    st.session_state.progress = max(st.session_state.progress, 1.0)
                    progress_bar.progress(st.session_state.progress)
                    set_stage_status("pdf", "done", "PDF généré")

            record_history(
                st.session_state.report_path,
                st.session_state.answers_path,
                st.session_state.extracted_path,
                st.session_state.pdf_path or (str(auto_pdf_path) if auto_pdf_path else None),
            )

if pdf_clicked:
    if ensure_prereq(["report_path"]):
        set_stage_status("pdf", "running", "Conversion PDF en cours...")
        callback = build_callback(logs_placeholder, live_status_placeholder, llm_stream_placeholder)
        orchestrator = RapportOrchestrator(status_callback=callback)
        try:
            pdf_path = orchestrator.export_pdf(Path(st.session_state.report_path))
        except Exception as exc:
            st.error(f"Erreur lors de l'export PDF : {exc}")
            set_stage_status("pdf", "error", str(exc))
        else:
            st.success("PDF généré.")
            st.session_state.pdf_path = str(pdf_path)
            st.session_state.progress = max(st.session_state.progress, 1.0)
            progress_bar.progress(st.session_state.progress)
            set_stage_status("pdf", "done", "PDF généré")

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
