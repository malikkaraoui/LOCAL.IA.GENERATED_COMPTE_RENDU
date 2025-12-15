"""Field specifications and validation helpers for LLM generation."""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata
from typing import Dict, List, Optional


LANGUAGE_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2", "Non évalué"]
TOOL_LEVELS = ["Faible", "Moyen", "Bon", "Très bon", "Non évalué"]
TEST_LEVELS = ["OK", "Moyen", "À renforcer", "Non évalué"]


@dataclass(frozen=True)
class FieldSpec:
    key: str
    field_type: str  # short | narrative | list | constrained | deterministic
    query: str
    instructions: str
    max_chars: int
    max_lines: int
    require_sources: bool = False
    skip_llm_if_no_sources: bool = False
    allowed_values: Optional[List[str]] = None
    deterministic_source: Optional[str] = None  # e.g. config.name


def _slug_to_sentence(key: str) -> str:
    text = key.replace("_", " ")
    text = text.replace("d’appui", "d'appui")
    text = text.replace("ET", "et")
    return text.strip().capitalize()


def _default_instructions(key: str, field_type: str) -> str:
    if field_type == "short":
        return f"Réponds en une seule ligne claire pour {key}."
    if field_type == "narrative":
        return (
            "Synthétise les éléments clés en français professionnel, 3 à 4 phrases courtes max."
        )
    if field_type == "list":
        return "Liste 2 à 4 idées courtes (une par ligne) basées sur les sources."
    if field_type == "constrained":
        return "Choisis uniquement une valeur autorisée selon les résultats présentés."
    if field_type == "deterministic":
        return "Valeur fournie par la configuration, sans appel LLM."
    return "Réponds brièvement en français."


def _register_specs() -> Dict[str, FieldSpec]:
    specs: Dict[str, FieldSpec] = {}

    deterministic = {
        "MONSIEUR_OU_MADAME": "civility",
        "NAME": "name",
        "SURNAME": "surname",
        "LIEU_ET_DATE": "location_date",
    }

    narrative = {
        "PROFESSION": "Synthétise la situation professionnelle actuelle (missions, responsabilités).",
        "FORMATION": "Présente les formations, diplômes, certifications mentionnés.",
        "DISCUSSION_ASSURE": "Résumé structuré des motivations, freins, points d'appui issus de la discussion.",
        "COMPETENCES_SOCIALES": "Synthétise les compétences sociales observées.",
        "COMPETENCES_PRO": "Synthétise les compétences professionnelles clés.",
        "OBSTACLES": "Décris les obstacles identifiés dans le parcours.",
        "ORIENTATION": "Propose les orientations ou pistes métiers évoquées.",
        "STAGE": "Résume le stage (objectifs, résultats).",
        "PRESENTATION": "Courte présentation du profil.",
        "ENTRETIEN": "Synthèse de la préparation aux entretiens.",
        "CONCLUSION": "Conclusion globale et prochaines étapes.",
        "Lettre_de_motivation": "Synthèse de la lettre de motivation fournie (pas d'invention).",
        "CV": "Synthèse du CV (formations, expériences).",
    }

    list_fields = {
        "Ressources_comportementales_Points_d’appui",
        "Ressources_comportementales_Points_de_vigilance",
        "Ressources_motivationnelles_PRINCIPAUX",
        "Ressources_interpersonnelles_principales",
        "Relation_au_marché_de_l_emploi",
        "Stratégies_comportementales",
        "Conditions_de_succès",
        "Contexte_Organisation_privilégiée",
        "Contexte_Rôle_privilégié",
        "Activités",
        "Activités_privilégiées",
        "Secteurs_privilégiés",
        "Fonctions_privilégiées",
        "métiers_privilégiés_qui_pourraient_etre_envisagé",
        "Vocatio",
        "Domaines_professionnels_EXEMPLES",
        "RIASEC_CORRESPONDANCE_SCORE",
        "Rôles_professionnels",
        "professions",
        "Formations_supérieures",
        "Formations_hautes écoles",
    }

    constrained_language = {
        "Français_positionnement_de_niveau",
        "Français_niveau_1",
        "Français_niveau_2",
        "Français_niveaU_3",
        "Anglais_positionnement_de_niveau_CECRL_ET_TOEIC",
        "ALLEMAND_positionnement_de_niveau",
    }

    constrained_tools = {
        "Word_positionnement_de_niveau",
        "EXCEL_positionnement_de_niveau",
        "POWERPOINT_positionnement_de_niveau",
        "OUTLOOK_positionnement_de_niveau",
    }

    constrained_tests = {
        "Tri_ET_classement",
        "TesT_d_attentiON_ADMINISTRATIF",
        "CALCUL_niveau_1",
        "CALCUL_niveau_2",
        "CALCUL_niveau_3",
        "CALCUL_ET_FRACTION",
        "DimensionS_volumes_et_mesures",
        "Test_de_niveau_en_comptabilité",
        "Test_de_Compréhension_de_consigneS",
        "Test_de_Saisie_de_commandes",
    }

    for key, source in deterministic.items():
        specs[key] = FieldSpec(
            key=key,
            field_type="deterministic",
            query=_slug_to_sentence(key),
            instructions=_default_instructions(key, "deterministic"),
            max_chars=100,
            max_lines=1,
            require_sources=False,
            skip_llm_if_no_sources=True,
            deterministic_source=source,
        )

    specs["NUMERO_AVS"] = FieldSpec(
        key="NUMERO_AVS",
        field_type="deterministic",
        query=_slug_to_sentence("NUMERO_AVS"),
        instructions="Numéro AVS fourni manuellement (jamais généré).",
        max_chars=50,
        max_lines=1,
        require_sources=False,
        skip_llm_if_no_sources=True,
        deterministic_source="avs_number",
    )

    for key, instr in narrative.items():
        specs[key] = FieldSpec(
            key=key,
            field_type="narrative",
            query=_slug_to_sentence(key),
            instructions=instr,
            max_chars=500,
            max_lines=4,
            require_sources=False,
            skip_llm_if_no_sources=False,
        )

    for key in list_fields:
        specs[key] = FieldSpec(
            key=key,
            field_type="list",
            query=_slug_to_sentence(key),
            instructions=_default_instructions(key, "list"),
            max_chars=400,
            max_lines=4,
            require_sources=False,
            skip_llm_if_no_sources=False,
        )

    for key in constrained_language:
        specs[key] = FieldSpec(
            key=key,
            field_type="constrained",
            query=_slug_to_sentence(key),
            instructions="Indique le niveau linguistique exact observé (A1->C2).",
            max_chars=20,
            max_lines=1,
            require_sources=True,
            skip_llm_if_no_sources=True,
            allowed_values=LANGUAGE_LEVELS,
        )

    for key in constrained_tools:
        specs[key] = FieldSpec(
            key=key,
            field_type="constrained",
            query=_slug_to_sentence(key),
            instructions="Choisis parmi les niveaux d'outils bureautiques listés.",
            max_chars=20,
            max_lines=1,
            require_sources=True,
            skip_llm_if_no_sources=True,
            allowed_values=TOOL_LEVELS,
        )

    for key in constrained_tests:
        specs[key] = FieldSpec(
            key=key,
            field_type="constrained",
            query=_slug_to_sentence(key),
            instructions="Choisis une valeur parmi OK / Moyen / À renforcer / Non évalué.",
            max_chars=20,
            max_lines=1,
            require_sources=True,
            skip_llm_if_no_sources=True,
            allowed_values=TEST_LEVELS,
        )

    # Fields explicitly factuels (non deterministic) requiring sources
    fact_fields = {
        "CV": narrative.get("CV"),
        "Lettre_de_motivation": narrative.get("Lettre_de_motivation"),
    }
    for key, instr in fact_fields.items():
        specs[key] = FieldSpec(
            key=key,
            field_type="short" if key == "NUMERO_AVS" else "narrative",
            query=_slug_to_sentence(key),
            instructions=instr or _default_instructions(key, "short"),
            max_chars=50 if key == "NUMERO_AVS" else 500,
            max_lines=1 if key == "NUMERO_AVS" else 4,
            require_sources=True,
            skip_llm_if_no_sources=True,
        )

    # Generic fallback for any other placeholder
    specs["DEFAULT"] = FieldSpec(
        key="DEFAULT",
        field_type="narrative",
        query="Champ du rapport",
        instructions=_default_instructions("champ", "narrative"),
        max_chars=400,
        max_lines=4,
    )

    return specs


FIELD_SPECS = _register_specs()


def get_field_spec(key: str) -> FieldSpec:
    if key in FIELD_SPECS:
        return FIELD_SPECS[key]
    upper_key = key.upper()
    if upper_key in FIELD_SPECS:
        return FIELD_SPECS[upper_key]
    default = FIELD_SPECS["DEFAULT"]
    return FieldSpec(
        key=key,
        field_type=default.field_type,
        query=_slug_to_sentence(key),
        instructions=_default_instructions(key, default.field_type),
        max_chars=default.max_chars,
        max_lines=default.max_lines,
        require_sources=default.require_sources,
        skip_llm_if_no_sources=default.skip_llm_if_no_sources,
        allowed_values=None,
        deterministic_source=None,
    )


def normalize_allowed_value(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").strip().lower()
    return "".join(ch for ch in text if not unicodedata.combining(ch))
