"""Détection utilitaire du numéro AVS dans les sources extraites."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

AVS_PATTERN = re.compile(r"756(?:[ .\-]?\d){10}")


def _normalize_avs(raw: str) -> Optional[str]:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) != 13 or not digits.startswith("756"):
        return None
    return f"{digits[:3]}.{digits[3:7]}.{digits[7:11]}.{digits[11:]}"


def detect_avs_in_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    for match in AVS_PATTERN.finditer(text):
        normalized = _normalize_avs(match.group(0))
        if normalized:
            return normalized
    return None


def detect_avs_number(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    if not payload:
        return None
    documents = payload.get("documents") or []
    for doc in documents:
        text = doc.get("text") if isinstance(doc, dict) else None
        candidate = detect_avs_in_text(text)
        if candidate:
            return candidate
        pages = doc.get("pages") if isinstance(doc, dict) else None
        if isinstance(pages, list):
            for page in pages:
                if not isinstance(page, dict):
                    continue
                candidate = detect_avs_in_text(page.get("text"))
                if candidate:
                    return candidate
    return None
