"""Utilitaires pour détecter les champs {{...}} d'un template DOCX."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from docx import Document

PLACEHOLDER_RE = re.compile(r"\{\{([^{}]+)\}\}")


def extract_placeholders_from_docx(template_path: Path) -> List[str]:
    """Retourne les placeholders uniques trouvés dans un template DOCX."""

    doc = Document(str(Path(template_path).expanduser().resolve()))
    placeholders: List[str] = []

    def register(text: str) -> None:
        if not text:
            return
        for match in PLACEHOLDER_RE.findall(text):
            key = match.strip()
            if key and key not in placeholders:
                placeholders.append(key)

    for paragraph in doc.paragraphs:
        register(paragraph.text)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    register(paragraph.text)

    return placeholders


def build_field_specs(
    placeholders: Sequence[str],
    fallback_defs: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Construit les spécifications de champs à partir des placeholders."""

    fallback_lookup = {item["key"]: item for item in (fallback_defs or []) if item.get("key")}
    specs: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for raw in placeholders:
        key = raw.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        base = fallback_lookup.get(key)
        query = base.get("query") if base else key.replace("_", " ")
        instructions = base.get("instructions") if base else f"Synthétise les informations pertinentes pour « {key} »"
        specs.append({
            "key": key,
            "query": query,
            "instructions": instructions,
        })

    return specs
