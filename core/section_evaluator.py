# core/section_evaluator.py
"""Quality gate: evaluate generated sections against RH PRO criteria.

Uses keyword heuristics (no LLM call) for instant evaluation.
Each required_element is checked against its keyword list.

Status:
- VIDE: empty text or "Non renseigné"
- BON: >= 75% required elements found
- A_REVOIR: < 75% required elements found
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from core.field_specs_v3 import FieldSpecV3


def _normalize(text: str) -> str:
    """Lowercase + strip accents for fuzzy keyword matching."""
    text = text.lower()
    # NFD decomposition then strip combining marks (accents)
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


@dataclass
class SectionCheck:
    element: str
    found: bool
    keywords_matched: list[str] = field(default_factory=list)


@dataclass
class SectionEvaluation:
    status: str  # "BON" | "A_REVOIR" | "VIDE"
    score: float  # 0.0 → 1.0
    checks: list[SectionCheck] = field(default_factory=list)
    comment: str = ""


_VIDE_MARKERS = {"", "non renseigné", "non évalué", "non renseigne", "non evalue"}

BON_THRESHOLD = 0.75


def evaluate_section(spec: FieldSpecV3, text: str) -> SectionEvaluation:
    """Evaluate a generated section against its V3 spec criteria."""
    stripped = (text or "").strip()

    # Empty / placeholder
    if stripped.lower() in _VIDE_MARKERS or not stripped:
        return SectionEvaluation(
            status="VIDE",
            score=0.0,
            checks=[
                SectionCheck(element=e, found=False) for e in spec.required_elements
            ],
            comment="Aucun contenu généré pour cette section.",
        )

    text_norm = _normalize(stripped)

    checks: list[SectionCheck] = []
    for element in spec.required_elements:
        keywords = spec.element_keywords.get(element, [])
        matched = [kw for kw in keywords if _normalize(kw) in text_norm]
        checks.append(
            SectionCheck(
                element=element,
                found=len(matched) > 0,
                keywords_matched=matched,
            )
        )

    found_count = sum(1 for c in checks if c.found)
    total = max(len(checks), 1)
    score = found_count / total

    if score >= BON_THRESHOLD:
        status = "BON"
        comment = ""
    else:
        status = "A_REVOIR"
        missing = [c.element for c in checks if not c.found]
        missing_labels = [e.replace("_", " ") for e in missing]
        comment = f"Il manque : {', '.join(missing_labels)}."

    return SectionEvaluation(
        status=status,
        score=round(score, 2),
        checks=checks,
        comment=comment,
    )


def evaluate_report(
    specs: list[FieldSpecV3], answers: dict[str, str]
) -> dict[str, SectionEvaluation]:
    """Evaluate all sections of a report. Returns {section_key: evaluation}."""
    results = {}
    for spec in specs:
        text = answers.get(spec.key, "")
        results[spec.key] = evaluate_section(spec, text)
    return results
