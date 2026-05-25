"""Context builder orienté rapport (Beyond-RAG / SKI).

Assemble un contexte structuré par section de rapport à partir de la base de
connaissance client générée par knowledge_builder.py.

Remplace la concaténation BM25 brute par une injection ciblée, tracée et
versionnée : chaque contexte produit est dérivé des notes Markdown structurées.

Pas de dépendance Obsidian, pas de base de données externe.
"""

from __future__ import annotations

from pathlib import Path

from .knowledge_builder import list_knowledge_notes, read_knowledge_note
from .logger import get_logger

LOG = get_logger("core.context_builder")

# ---------------------------------------------------------------------------
# Chemins templates
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "qmd"

# ---------------------------------------------------------------------------
# Mapping section → types de notes prioritaires
# Les types correspondent aux slugs définis dans knowledge_builder.NOTE_FILENAMES.
# ---------------------------------------------------------------------------

_SECTION_NOTE_PRIORITY: dict[str, list[str]] = {
    "PROFESSION":               ["cv", "msg", "entretien_audio", "autre"],
    "FORMATION":                ["formation", "cv", "autre"],
    "INCERTITUDE_ET_OBSTACLE":  ["msg", "entretien_audio", "cv"],
    "ORIENTATION":              ["msg", "entretien_audio", "lettre", "cv"],
    "FORMATION_DURANT_MESURE":  ["msg", "formation", "entretien_audio"],
    "STAGE":                    ["msg", "cv", "entretien_audio"],
    "CONCLUSION":               ["msg", "entretien_audio", "cv", "lettre"],
}

# Fallback : tous les types dans l'ordre par défaut
_DEFAULT_NOTE_ORDER = ["cv", "lettre", "formation", "entretien_audio", "msg", "autre"]

# Note slug → nom de fichier dans _knowledge/
_NOTE_TYPE_TO_FILE = {
    "cv":              "01-cv.md",
    "lettre":          "02-lettre.md",
    "formation":       "03-formations.md",
    "entretien_audio": "04-entretien-audio.md",
    "msg":             "05-messages.md",
    "autre":           "06-autres.md",
}


# ---------------------------------------------------------------------------
# Helpers privés
# ---------------------------------------------------------------------------

def _load_qmd_template(section_key: str) -> str:
    """Charge le template QMD pour une section donnée, avec fallback sur base."""
    specific = _TEMPLATES_DIR / f"section_{section_key}.qmd"
    if specific.exists():
        return specific.read_text(encoding="utf-8")
    base = _TEMPLATES_DIR / "base_context.qmd"
    if base.exists():
        return base.read_text(encoding="utf-8")
    # Fallback inline minimal si aucun template n'existe sur disque
    return (
        "---\nsection: \"{{section_key}}\"\nclient: \"{{client_name}}\"\n---\n\n"
        "# Contexte — {{section_key}}\n\n{{notes_content}}\n"
    )


def _render_qmd(template: str, variables: dict[str, str]) -> str:
    """Remplace les placeholders {{key}} dans le template par les valeurs du dict."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def _select_notes(knowledge_dir: Path, section_key: str) -> list[Path]:
    """Sélectionne et ordonne les notes pertinentes pour une section."""
    priority = _SECTION_NOTE_PRIORITY.get(section_key, _DEFAULT_NOTE_ORDER)
    available = {p.name: p for p in list_knowledge_notes(knowledge_dir)}

    ordered: list[Path] = []
    seen: set[str] = set()

    # 1. Ajouter dans l'ordre de priorité pour la section
    for note_type in priority:
        filename = _NOTE_TYPE_TO_FILE.get(note_type)
        if filename and filename in available and filename not in seen:
            ordered.append(available[filename])
            seen.add(filename)

    # 2. Ajouter les notes restantes non encore incluses
    for filename, path in sorted(available.items()):
        if filename not in seen:
            ordered.append(path)

    return ordered


def _trim_to_max_chars(text: str, max_chars: int) -> str:
    """Coupe à max_chars en préservant les fins de section (## ou fin de phrase)."""
    if not text or len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # Préférer couper à un header de section
    last_header = cut.rfind("\n##")
    if last_header > max_chars * 0.5:
        return cut[:last_header].rstrip()
    # Sinon couper à une fin de phrase
    last_period = max(cut.rfind(".\n"), cut.rfind(". "))
    if last_period > max_chars * 0.6:
        return cut[:last_period + 1].rstrip()
    return cut.rstrip()


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def build_section_context(
    knowledge_dir: Path,
    section_key: str,
    *,
    client_name: str = "",
    max_chars: int = 3000,
) -> str:
    """Construit le contexte structuré pour une section de rapport.

    Charge les notes Markdown de la base de connaissance client, les assemble
    dans l'ordre de pertinence pour la section demandée, applique le template
    QMD et retourne le contexte rendu en texte pur.

    Args:
        knowledge_dir: Chemin du répertoire _knowledge/ du client
        section_key: Clé de section V3 (ex: "PROFESSION", "FORMATION")
        client_name: Nom du client pour le frontmatter (optionnel)
        max_chars: Taille max du contexte retourné

    Returns:
        str: Contexte structuré prêt à être injecté dans le prompt LLM.
             Chaîne vide si aucune note disponible.
    """
    knowledge_dir = Path(knowledge_dir)
    if not knowledge_dir.exists():
        LOG.warning("context_builder: knowledge_dir inexistant: %s", knowledge_dir)
        return ""

    notes = _select_notes(knowledge_dir, section_key)
    if not notes:
        LOG.info("context_builder [%s]: aucune note disponible", section_key)
        return ""

    # Assembler le contenu des notes
    parts: list[str] = []
    for note_path in notes:
        content = read_knowledge_note(note_path, strip_frontmatter=True)
        if content:
            parts.append(content)

    if not parts:
        return ""

    notes_content = "\n\n---\n\n".join(parts)

    from datetime import datetime
    template = _load_qmd_template(section_key)
    rendered = _render_qmd(template, {
        "section_key": section_key,
        "client_name": client_name or "client",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "notes_content": notes_content,
    })

    result = _trim_to_max_chars(rendered, max_chars)

    LOG.info(
        "context_builder [%s]: %d notes, %d→%d chars",
        section_key,
        len(notes),
        len(rendered),
        len(result),
    )
    return result


def build_flat_context(
    knowledge_dir: Path,
    *,
    max_chars: int = 5000,
) -> str:
    """Retourne le contenu brut de toutes les notes, pour usage générique.

    Utile pour les sections sans template spécifique ou pour les Q&R futures.
    """
    knowledge_dir = Path(knowledge_dir)
    if not knowledge_dir.exists():
        return ""

    notes = list_knowledge_notes(knowledge_dir)
    parts: list[str] = []
    for note_path in notes:
        content = read_knowledge_note(note_path, strip_frontmatter=True)
        if content:
            parts.append(content)

    if not parts:
        return ""

    combined = "\n\n---\n\n".join(parts)
    return _trim_to_max_chars(combined, max_chars)
