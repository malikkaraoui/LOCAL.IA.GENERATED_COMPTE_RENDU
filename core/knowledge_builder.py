"""Couche de connaissance client structurée (Beyond-RAG / SKI).

Convertit les documents extraits d'un dossier client en notes Markdown avec
frontmatter YAML, stockées dans <client_dir>/_knowledge/.

Contrat de données : Markdown + YAML frontmatter + JSON manifest.
Compatible Obsidian (ouverture directe dans l'app) mais non dépendant d'Obsidian
comme runtime — les fichiers .md sont lisibles par n'importe quel outil ou LLM.

Hors scope de ce module : graphe relationnel (graph_builder), UI, dépendance cloud.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .logger import get_logger

LOG = get_logger("core.knowledge_builder")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

KNOWLEDGE_DIR_NAME = "_knowledge"
META_FILENAME = "_meta.json"

# Mapping : slug de type → nom de fichier note
NOTE_FILENAMES: dict[str, str] = {
    "cv":              "01-cv.md",
    "lettre":          "02-lettre.md",
    "formation":       "03-formations.md",
    "entretien_audio": "04-entretien-audio.md",
    "msg":             "05-messages.md",
    "autre":           "06-autres.md",
}

# Patterns de détection du type depuis le nom de fichier (insensible à la casse)
_TYPE_PATTERNS: list[tuple[str, str]] = [
    ("cv",        r"cv|curriculum.vitae|lebenslauf"),
    ("lettre",    r"lettre|motivation|cover.?letter|candidature"),
    ("formation", r"formation|diplom|certif|attestat|brevet|bilan"),
    ("msg",       r"\.msg$"),  # extension
]

# Détection des transcriptions audio ingérées (chemin contient ingested_audio)
_AUDIO_TRANSCRIPT_PATH_PATTERN = re.compile(r"ingested_audio", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class NoteEntry:
    note_type: str
    source_path: str
    text_sha256: str
    mtime_iso: str
    size_bytes: int


@dataclass
class KnowledgeMeta:
    generated_at: str
    client_root: str
    notes: list[dict[str, Any]]  # serialized NoteEntry list


# ---------------------------------------------------------------------------
# Helpers privés
# ---------------------------------------------------------------------------

def _classify_document(path: str, ext: str) -> str:
    """Retourne le slug du type de note pour un document donné."""
    name_lower = Path(path).name.lower()
    path_lower = path.lower()

    if _AUDIO_TRANSCRIPT_PATH_PATTERN.search(path_lower):
        return "entretien_audio"

    if ext == ".msg":
        return "msg"

    for note_type, pattern in _TYPE_PATTERNS:
        if re.search(pattern, name_lower, re.IGNORECASE):
            return note_type

    return "autre"


def _yaml_str(value: Any) -> str:
    """Sérialise une valeur simple en YAML inline (sans dépendance PyYAML)."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list):
        items = ", ".join(_yaml_str(v) for v in value)
        return f"[{items}]"
    # Chaîne : échapper les guillemets doubles
    escaped = str(value).replace('"', '\\"')
    return f'"{escaped}"'


def _build_frontmatter(note_type: str, sources: list[str], sha256s: dict[str, str], generated_at: str) -> str:
    lines = ["---"]
    lines.append(f"type: {_yaml_str(note_type)}")
    lines.append(f"sources: {_yaml_str(sources)}")
    sha256_inline = "{" + ", ".join(f'"{k}": "{v}"' for k, v in sha256s.items()) + "}"
    lines.append(f"sha256s: {sha256_inline}")
    lines.append(f"generated_at: {_yaml_str(generated_at)}")
    lines.append("---")
    return "\n".join(lines)


def _section_header(filename: str, mtime_iso: str, size_bytes: int) -> str:
    return (
        f"\n## {Path(filename).name}\n"
        f"*Source : {Path(filename).name} · {mtime_iso} · {size_bytes} octets*\n"
    )


def _trim_text(text: str, max_chars: int = 8000) -> str:
    """Coupe le texte à max_chars en préservant les fins de phrase."""
    if not text or len(text) <= max_chars:
        return text.strip()
    cut = text[:max_chars]
    last_period = max(cut.rfind("."), cut.rfind("\n"))
    if last_period > max_chars * 0.7:
        return cut[:last_period + 1].strip()
    return cut.rstrip()


def _docs_to_note(docs: list[dict[str, Any]], note_type: str) -> str:
    """Assemble plusieurs documents en une note Markdown structurée."""
    sources = [d["path"] for d in docs]
    sha256s = {Path(d["path"]).name: d.get("text_sha256", "") for d in docs}
    now = datetime.now().isoformat(timespec="seconds")

    frontmatter = _build_frontmatter(note_type, [Path(s).name for s in sources], sha256s, now)

    title_map = {
        "cv":              "CV — Parcours professionnel",
        "lettre":          "Lettre de motivation",
        "formation":       "Formations et diplômes",
        "entretien_audio": "Transcription d'entretien (audio)",
        "msg":             "Correspondances et emails",
        "autre":           "Documents complémentaires",
    }
    title = title_map.get(note_type, note_type.replace("_", " ").title())

    lines = [frontmatter, "", f"# {title}", ""]

    if len(sources) > 1:
        links = " · ".join(f"[[{Path(s).name}]]" for s in sources)
        lines.append(f"Sources : {links}")
        lines.append("")

    for doc in docs:
        text = (doc.get("text") or "").strip()
        if not text:
            continue
        lines.append(_section_header(doc["path"], doc.get("mtime_iso", ""), doc.get("size_bytes", 0)))
        lines.append(_trim_text(text))
        lines.append("")

    return "\n".join(lines)


def _load_meta(knowledge_dir: Path) -> dict[str, Any]:
    meta_path = knowledge_dir / META_FILENAME
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"notes": []}


def _save_meta(knowledge_dir: Path, meta: dict[str, Any]) -> None:
    meta_path = knowledge_dir / META_FILENAME
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256_changed(doc: dict[str, Any], meta_notes: dict[str, str]) -> bool:
    """Retourne True si le SHA256 du doc a changé depuis la dernière indexation."""
    filename = Path(doc["path"]).name
    current = doc.get("text_sha256", "")
    return meta_notes.get(filename) != current


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def build_client_knowledge(
    client_dir: Path,
    payload: dict[str, Any],
    *,
    force_rebuild: bool = False,
) -> Path:
    """Construit ou met à jour la base de connaissance structurée d'un dossier client.

    Lit les documents du payload (issu de extract_sources), les classe par type
    et génère une note Markdown avec frontmatter YAML dans <client_dir>/_knowledge/.
    Le cache SHA256 évite les recalculs si les fichiers sources n'ont pas changé.

    Args:
        client_dir: Dossier racine du client (ex: CLIENTS/Nom Prénom/)
        payload: Dict retourné par extract_sources (clé "documents")
        force_rebuild: Reconstruire toutes les notes même si rien n'a changé

    Returns:
        Path: Chemin du répertoire _knowledge/ créé ou mis à jour
    """
    client_dir = Path(client_dir).expanduser().resolve()
    knowledge_dir = client_dir / KNOWLEDGE_DIR_NAME
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    documents: list[dict[str, Any]] = payload.get("documents", [])
    if not documents:
        LOG.warning("knowledge_builder: aucun document dans le payload pour %s", client_dir.name)
        return knowledge_dir

    meta = _load_meta(knowledge_dir)
    # Index SHA256 par filename pour la détection incrémentielle
    meta_sha256s: dict[str, str] = {
        n["filename"]: n["sha256"]
        for n in meta.get("notes", [])
        if isinstance(n, dict) and "filename" in n
    }

    # Grouper les documents par type de note
    groups: dict[str, list[dict[str, Any]]] = {}
    for doc in documents:
        if doc.get("error") or not doc.get("text"):
            continue
        note_type = _classify_document(doc["path"], doc.get("ext", ""))
        groups.setdefault(note_type, []).append(doc)

    if not groups:
        LOG.warning("knowledge_builder: aucun document exploitable dans %s", client_dir.name)
        return knowledge_dir

    rebuilt: list[str] = []
    skipped: list[str] = []
    updated_meta_notes: list[dict[str, Any]] = []

    for note_type, docs in groups.items():
        note_filename = NOTE_FILENAMES.get(note_type, f"_{note_type}.md")
        note_path = knowledge_dir / note_filename

        # Vérification incrémentielle : reconstruire seulement si un doc a changé
        any_changed = force_rebuild or not note_path.exists() or any(
            _sha256_changed(d, meta_sha256s) for d in docs
        )

        if not any_changed:
            skipped.append(note_filename)
            # Maintenir les entrées meta existantes
            for doc in docs:
                fname = Path(doc["path"]).name
                updated_meta_notes.append({
                    "filename": fname,
                    "sha256": doc.get("text_sha256", ""),
                    "note_type": note_type,
                    "note_file": note_filename,
                })
            continue

        # Construire la note
        note_content = _docs_to_note(docs, note_type)
        note_path.write_text(note_content, encoding="utf-8")
        rebuilt.append(note_filename)

        for doc in docs:
            fname = Path(doc["path"]).name
            updated_meta_notes.append({
                "filename": fname,
                "sha256": doc.get("text_sha256", ""),
                "note_type": note_type,
                "note_file": note_filename,
                "rebuilt_at": datetime.now().isoformat(timespec="seconds"),
            })

    # Sauvegarder le manifest
    _save_meta(knowledge_dir, {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "client_root": str(client_dir),
        "notes": updated_meta_notes,
    })

    LOG.info(
        "knowledge_builder [%s]: %d notes reconstruites, %d ignorées (cache valide)",
        client_dir.name,
        len(rebuilt),
        len(skipped),
    )
    return knowledge_dir


def list_knowledge_notes(knowledge_dir: Path) -> list[Path]:
    """Retourne les notes Markdown disponibles dans le répertoire knowledge."""
    if not knowledge_dir.exists():
        return []
    return sorted(
        p for p in knowledge_dir.glob("*.md")
        if not p.name.startswith("_")
    )


def read_knowledge_note(note_path: Path, strip_frontmatter: bool = True) -> str:
    """Lit le contenu d'une note, optionnellement sans le bloc frontmatter YAML."""
    if not note_path.exists():
        return ""
    content = note_path.read_text(encoding="utf-8")
    if strip_frontmatter and content.startswith("---"):
        # Sauter le bloc frontmatter délimité par ---
        end = content.find("\n---", 3)
        if end != -1:
            return content[end + 4:].strip()
    return content.strip()
