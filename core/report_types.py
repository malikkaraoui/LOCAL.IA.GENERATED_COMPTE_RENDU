# core/report_types.py
"""Registry of report types and their section mappings.

Each report type defines which sections (from field_specs_v3) are included.
Standby types have empty sections until specs are provided.
"""

from __future__ import annotations
from typing import Optional

REPORT_TYPES: dict[str, dict] = {
    "rapport_initial": {
        "label": "Rapport Initial",
        "description": "Bilan initial du parcours professionnel et orientation",
        "sections": [
            "PROFESSION",
            "FORMATION",
            "INCERTITUDE_ET_OBSTACLE",
            "ORIENTATION",
            "FORMATION_DURANT_MESURE",
            "STAGE",
            "CONCLUSION",
        ],
    },
    "rapport_intermediaire": {
        "label": "Rapport Intermédiaire",
        "description": "Point d'étape en cours de mesure",
        "sections": [],  # Standby
    },
    "rapport_stage": {
        "label": "Rapport de Stage",
        "description": "Évaluation suite à un stage",
        "sections": [],  # Standby
    },
    "rapport_final": {
        "label": "Rapport Final / Complet",
        "description": "Bilan complet de fin de mesure",
        "sections": [],  # Standby
    },
}


def get_report_type(key: str) -> Optional[dict]:
    """Return report type definition or None if unknown."""
    return REPORT_TYPES.get(key)


def list_report_types() -> list[dict]:
    """Return all report types as a list with keys."""
    return [{"key": k, **v} for k, v in REPORT_TYPES.items()]
