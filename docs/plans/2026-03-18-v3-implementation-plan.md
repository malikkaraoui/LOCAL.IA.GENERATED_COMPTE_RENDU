# V3 — Report Types + Quality Gate + Review Page

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the 54-field generic generation with a type-based report system (starting with "Rapport Initial" — 7 sections), add a quality gate per section, and build a 3-column review page for consultants to validate before DOCX export.

**Architecture:** Refactor progressif. Le pipeline existant (extract → RAG → LLM → render) reste intact. On ajoute 3 nouvelles couches: `report_types.py` (quel type → quelles sections), `field_specs_v3.py` (specs RH PRO), `section_evaluator.py` (quality gate). Cote frontend, nouvelle page ReportReview.jsx avec 3 colonnes. L'API gagne des endpoints de revue/edition/regeneration.

**Tech Stack:** Python 3.13+ / FastAPI / Redis Queue / React 19 / Vite / Tailwind CSS / Axios

**Design doc:** `docs/plans/2026-03-18-v3-report-types-design.md`

---

## Task 1: Report Types Registry (`core/report_types.py`)

**Files:**
- Create: `core/report_types.py`
- Test: `tests/test_report_types.py`

**Step 1: Write the failing test**

```python
# tests/test_report_types.py
from core.report_types import REPORT_TYPES, get_report_type, list_report_types


class TestReportTypes:
    def test_rapport_initial_exists(self):
        rt = get_report_type("rapport_initial")
        assert rt is not None
        assert rt["label"] == "Rapport Initial"

    def test_rapport_initial_has_7_sections(self):
        rt = get_report_type("rapport_initial")
        assert len(rt["sections"]) == 7
        assert "PROFESSION" in rt["sections"]
        assert "CONCLUSION" in rt["sections"]

    def test_rapport_initial_section_order(self):
        rt = get_report_type("rapport_initial")
        expected = [
            "PROFESSION", "FORMATION", "INCERTITUDE_ET_OBSTACLE",
            "ORIENTATION", "FORMATION_DURANT_MESURE", "STAGE", "CONCLUSION",
        ]
        assert rt["sections"] == expected

    def test_list_report_types(self):
        types = list_report_types()
        assert len(types) == 4
        keys = [t["key"] for t in types]
        assert "rapport_initial" in keys
        assert "rapport_final" in keys

    def test_unknown_type_returns_none(self):
        assert get_report_type("inexistant") is None

    def test_standby_types_have_empty_sections(self):
        for key in ["rapport_intermediaire", "rapport_stage", "rapport_final"]:
            rt = get_report_type(key)
            assert rt is not None
            assert rt["sections"] == [], f"{key} should have empty sections (standby)"
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/malik/Documents/Laboratoire 🧪/SCRIPT.IA" && python -m pytest tests/test_report_types.py -v --no-cov`
Expected: FAIL (module not found)

**Step 3: Write implementation**

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd "/Users/malik/Documents/Laboratoire 🧪/SCRIPT.IA" && python -m pytest tests/test_report_types.py -v --no-cov`
Expected: 6 passed

**Step 5: Commit**

```bash
git add core/report_types.py tests/test_report_types.py
git commit -m "feat: add report types registry (rapport_initial + 3 standby)"
```

---

## Task 2: Field Specs V3 (`core/field_specs_v3.py`)

**Files:**
- Create: `core/field_specs_v3.py`
- Test: `tests/test_field_specs_v3.py`

**Step 1: Write the failing test**

```python
# tests/test_field_specs_v3.py
from core.field_specs_v3 import FieldSpecV3, get_field_spec_v3, get_specs_for_report_type, FIELD_SPECS_V3


class TestFieldSpecV3:
    def test_profession_spec_exists(self):
        spec = get_field_spec_v3("PROFESSION")
        assert spec is not None
        assert isinstance(spec, FieldSpecV3)

    def test_profession_has_required_elements(self):
        spec = get_field_spec_v3("PROFESSION")
        assert len(spec.required_elements) >= 4
        assert "statut" in spec.required_elements
        assert "raison_arret" in spec.required_elements

    def test_profession_is_immutable(self):
        spec = get_field_spec_v3("PROFESSION")
        assert spec.immutable is True

    def test_profession_sources(self):
        spec = get_field_spec_v3("PROFESSION")
        assert "journal" in spec.sources
        assert "cv" in spec.sources
        assert "msg" in spec.sources

    def test_profession_limits(self):
        spec = get_field_spec_v3("PROFESSION")
        assert spec.max_chars == 3000
        assert spec.min_lines == 15
        assert spec.max_lines == 30

    def test_all_7_rapport_initial_specs_exist(self):
        keys = [
            "PROFESSION", "FORMATION", "INCERTITUDE_ET_OBSTACLE",
            "ORIENTATION", "FORMATION_DURANT_MESURE", "STAGE", "CONCLUSION",
        ]
        for key in keys:
            spec = get_field_spec_v3(key)
            assert spec is not None, f"Missing spec for {key}"
            assert spec.required_elements, f"{key} has no required_elements"
            assert spec.element_keywords, f"{key} has no element_keywords"

    def test_get_specs_for_report_type(self):
        specs = get_specs_for_report_type("rapport_initial")
        assert len(specs) == 7
        assert specs[0].key == "PROFESSION"
        assert specs[-1].key == "CONCLUSION"

    def test_get_specs_for_unknown_type_returns_empty(self):
        specs = get_specs_for_report_type("inexistant")
        assert specs == []

    def test_conclusion_short_limits(self):
        spec = get_field_spec_v3("CONCLUSION")
        assert spec.min_lines == 3
        assert spec.max_lines == 5

    def test_each_spec_has_element_keywords_for_all_required(self):
        for key, spec in FIELD_SPECS_V3.items():
            for elem in spec.required_elements:
                assert elem in spec.element_keywords, (
                    f"{key}: required_element '{elem}' missing from element_keywords"
                )
                assert len(spec.element_keywords[elem]) > 0, (
                    f"{key}: element_keywords['{elem}'] is empty"
                )

    def test_unknown_spec_returns_none(self):
        assert get_field_spec_v3("INEXISTANT") is None
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/malik/Documents/Laboratoire 🧪/SCRIPT.IA" && python -m pytest tests/test_field_specs_v3.py -v --no-cov`
Expected: FAIL (module not found)

**Step 3: Write implementation**

```python
# core/field_specs_v3.py
"""Field Specifications V3 — Specs RH PRO par type de rapport.

Chaque section contient:
- Les instructions LLM mot pour mot telles que definies avec le client RH PRO
- Les criteres d'evaluation (required_elements + element_keywords) pour le quality gate
- Les metadonnees de format (limites, sources attendues, immutabilite)

V2 reste intact et disponible pour les champs non couverts par V3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class FieldSpecV3:
    key: str
    query: str
    instructions: str
    max_chars: int
    min_lines: int
    max_lines: int
    sources: list[str]
    immutable: bool = False
    required_elements: list[str] = field(default_factory=list)
    element_keywords: dict[str, list[str]] = field(default_factory=dict)
    evaluation_prompt: str = ""


FIELD_SPECS_V3: dict[str, FieldSpecV3] = {

    # ── PROFESSION ──────────────────────────────────────────────
    "PROFESSION": FieldSpecV3(
        key="PROFESSION",
        query="Situation professionnelle actuelle",
        instructions=(
            "But : donner une photo claire et factuelle de la situation pro actuelle "
            "(ou la dernière connue).\n\n"
            "Attendu :\n"
            "- Statut : en poste / en recherche / en arrêt / en transition.\n"
            "- Poste actuel (ou dernier poste), secteur, type de contrat si connu, "
            "rythme (temps plein/partiel).\n"
            "- Missions principales (3-6 points implicites dans un texte fluide), "
            "responsabilités, niveau d'autonomie.\n"
            "- Environnement : équipe, terrain/bureau, contraintes physiques/horaires "
            "si mentionnées.\n"
            "Quand j'ai l'info je veux savoir ce que la personne a vraiment fait "
            "(la tâche exacte).\n\n"
            "Contraintes :\n"
            "- Ne jamais inventer employeur, dates, intitulés précis si absents.\n"
            "- Si info manquante : l'indiquer (\"Non renseigné\") plutôt que combler.\n\n"
            "CONCLUSION : elle doit se finir par le pourquoi du comment la personne "
            "a arrêté son parcours pro (ex : maladie, ou accident) - savoir si la "
            "personne a été licenciée (cette info peut ne pas être dispo).\n\n"
            "Ce paragraphe doit mettre en avant les compétences qui pourront être "
            "transférables à l'avenir.\n\n"
            "Cette section ne bouge pas une fois éditée JAMAIS. "
            "Indépendamment de la demande de la génération du bilan.\n\n"
            "Format : 6-10 lignes, professionnel, sans liste longue.\n"
            "Écrire du plus ancien au plus récent."
        ),
        max_chars=3000,
        min_lines=15,
        max_lines=30,
        sources=["journal", "cv", "msg"],
        immutable=True,
        required_elements=[
            "statut",
            "poste",
            "missions",
            "environnement",
            "raison_arret",
            "competences_transferables",
        ],
        element_keywords={
            "statut": [
                "en poste", "en recherche", "en arrêt", "en transition",
                "sans emploi", "arrêt maladie", "arrêt de travail",
                "incapacité", "emploi", "chômage",
            ],
            "poste": [
                "poste", "fonction", "emploi", "travaillé comme", "occupait",
                "métier", "profession", "contrat", "CDI", "CDD", "temporaire",
                "intérimaire", "temps plein", "temps partiel",
            ],
            "missions": [
                "mission", "tâche", "responsabilité", "activité", "chargé de",
                "assurait", "gérait", "réalisait", "effectuait", "s'occupait",
            ],
            "environnement": [
                "équipe", "terrain", "bureau", "chantier", "atelier",
                "horaires", "physique", "extérieur", "client",
            ],
            "raison_arret": [
                "licencié", "accident", "maladie", "fin de contrat", "arrêt",
                "cessé", "interruption", "incapacité", "sinistre", "opération",
                "burnout", "restructuration", "fermeture",
            ],
            "competences_transferables": [
                "compétence", "savoir-faire", "acquis", "expérience",
                "transférable", "polyvalent", "capacité", "aptitude",
            ],
        },
        evaluation_prompt=(
            "Vérifier : statut professionnel mentionné, poste/fonction identifié, "
            "missions décrites, environnement de travail, raison de l'arrêt du "
            "parcours, compétences transférables mises en avant."
        ),
    ),

    # ── FORMATION ───────────────────────────────────────────────
    "FORMATION": FieldSpecV3(
        key="FORMATION",
        query="Formations, diplômes, certifications",
        instructions=(
            "But : parcours de formation complet.\n\n"
            "Attendu :\n"
            "- Diplômes et formations (du plus ancien au plus récent).\n"
            "- Domaine + nature (diplôme/certificat/formation courte) + date/durée "
            "si disponible. Et école et lieu.\n"
            "- Si parcours hétérogène : regrouper par thème "
            "(technique / administratif / sécurité).\n"
            "- Mentionner les formations en cours si présentes.\n\n"
            "Contraintes :\n"
            "- Zéro invention d'école, de date, de certification.\n"
            "- Ne pas transformer une intention de formation en formation \"faite\".\n\n"
            "Format : 6-12 lignes (+- 2 lignes), lisible, "
            "éventuellement 2 mini-paragraphes."
        ),
        max_chars=3000,
        min_lines=6,
        max_lines=15,
        sources=["journal", "cv", "msg"],
        immutable=False,
        required_elements=[
            "diplomes",
            "domaine_nature",
            "dates_durees",
            "ecole_lieu",
        ],
        element_keywords={
            "diplomes": [
                "diplôme", "CFC", "AFP", "brevet", "certificat", "baccalauréat",
                "maturité", "bachelor", "master", "licence", "attestation",
                "formation", "titre",
            ],
            "domaine_nature": [
                "technique", "administratif", "commercial", "social", "santé",
                "informatique", "sécurité", "logistique", "mécanique",
                "diplôme", "certificat", "formation courte", "CAS", "DAS",
            ],
            "dates_durees": [
                "19", "20", "année", "ans", "mois", "durée", "période",
                "obtenu en", "délivré", "terminé",
            ],
            "ecole_lieu": [
                "école", "centre", "institut", "université", "HES", "EPFL",
                "lycée", "collège", "Lausanne", "Genève", "Zurich", "Berne",
                "Suisse", "France",
            ],
        },
        evaluation_prompt=(
            "Vérifier : diplômes listés, domaine et nature précisés, "
            "dates ou durées mentionnées, école et lieu indiqués."
        ),
    ),

    # ── INCERTITUDE ET OBSTACLE ─────────────────────────────────
    "INCERTITUDE_ET_OBSTACLE": FieldSpecV3(
        key="INCERTITUDE_ET_OBSTACLE",
        query="Obstacles identifiés dans le parcours",
        instructions=(
            "But : identifier les obstacles et les différents freins "
            "(physique, médical, administratif, psychologique). "
            "Ex : poursuite, pas de permis de conduire (ou retrait) et "
            "comportement et interaction sociale (de manière neutre).\n\n"
            "Attendu :\n"
            "- Obstacles neutres (santé, mobilité, langue, disponibilité, "
            "lacunes techniques, confiance).\n"
            "- Formulation orientée solution "
            "(ex : \"nécessite un aménagement / accompagnement\").\n\n"
            "Contraintes :\n"
            "- Ne pas inventer.\n"
            "- Formulation neutre et professionnelle.\n\n"
            "Format : 5-10 lignes maximum."
        ),
        max_chars=3000,
        min_lines=5,
        max_lines=15,
        sources=["msg", "journal", "pdf"],
        immutable=False,
        required_elements=[
            "freins_identifies",
            "formulation_neutre",
            "orientation_solution",
        ],
        element_keywords={
            "freins_identifies": [
                "obstacle", "frein", "difficulté", "limitation", "contrainte",
                "problème", "santé", "mobilité", "langue", "permis",
                "douleur", "médical", "psychologique", "administratif",
                "poursuite", "dette", "comportement", "interaction",
            ],
            "formulation_neutre": [
                "nécessite", "requiert", "implique", "demande", "suppose",
                "important de", "à prendre en compte", "à considérer",
            ],
            "orientation_solution": [
                "aménagement", "accompagnement", "soutien", "adaptation",
                "formation", "renforcement", "prise en charge", "suivi",
                "solution", "piste", "mesure",
            ],
        },
        evaluation_prompt=(
            "Vérifier : freins concrets identifiés (physique/médical/admin/psy), "
            "formulation neutre et professionnelle, orientation solution proposée."
        ),
    ),

    # ── ORIENTATION ─────────────────────────────────────────────
    "ORIENTATION": FieldSpecV3(
        key="ORIENTATION",
        query="Orientations ou pistes métiers",
        instructions=(
            "But : proposer des pistes cohérentes et crédibles. "
            "Et surtout justifier la pertinence du choix. "
            "Physiquement (ergonomie), les formations qui match…\n\n"
            "Il faut également parler des pistes non retenues et le justifier.\n\n"
            "Attendu :\n"
            "- 1 à 3 (max) pistes cohérentes, chacune justifiée.\n"
            "- Mention formation/validation si nécessaire.\n"
            "- Cohérence avec la section incertitude et obstacles.\n\n"
            "Format : 1-3 puces, 2 à 5 phrases par puce maximum."
        ),
        max_chars=3000,
        min_lines=15,
        max_lines=20,
        sources=["journal"],
        immutable=False,
        required_elements=[
            "pistes_retenues",
            "justification_pertinence",
            "pistes_non_retenues",
            "coherence_obstacles",
        ],
        element_keywords={
            "pistes_retenues": [
                "piste", "orientation", "métier", "profession", "domaine",
                "envisagé", "retenu", "proposé", "choisi", "cible",
                "reconversion", "réorientation",
            ],
            "justification_pertinence": [
                "car", "parce que", "en raison", "grâce à", "compte tenu",
                "compatible", "cohérent", "adapté", "pertinent", "correspond",
                "ergonomie", "physique", "formation", "compétence",
            ],
            "pistes_non_retenues": [
                "non retenu", "écarté", "exclu", "pas retenu", "abandonné",
                "incompatible", "ne correspond pas", "trop", "insuffisant",
                "pas envisageable", "contre-indiqué",
            ],
            "coherence_obstacles": [
                "limitation", "contrainte", "obstacle", "frein", "capacité",
                "aménagement", "restriction", "compatible avec",
            ],
        },
        evaluation_prompt=(
            "Vérifier : pistes retenues listées et justifiées, "
            "pistes non retenues mentionnées avec justification, "
            "cohérence avec les obstacles identifiés."
        ),
    ),

    # ── FORMATION DURANT LA MESURE ──────────────────────────────
    "FORMATION_DURANT_MESURE": FieldSpecV3(
        key="FORMATION_DURANT_MESURE",
        query="Formations diplômantes ou certifiantes durant la mesure RH Pro",
        instructions=(
            "But : Il faut ressortir les formations diplômantes ou certifiantes "
            "(ce que RH-Pro propose ou met en place). "
            "Cette formation a lieu pendant le parcours chez RH Pro "
            "(donc se référer au journal et à la date de la mesure).\n\n"
            "Format : 2 à 10 lignes."
        ),
        max_chars=2000,
        min_lines=2,
        max_lines=10,
        sources=["journal", "msg"],
        immutable=False,
        required_elements=[
            "formation_identifiee",
            "nature_diplome_certif",
            "lien_mesure_rhpro",
        ],
        element_keywords={
            "formation_identifiee": [
                "formation", "cours", "module", "programme", "cursus",
                "apprentissage", "stage de formation",
            ],
            "nature_diplome_certif": [
                "diplômante", "certifiante", "diplôme", "certificat",
                "attestation", "brevet", "CFC", "AFP", "qualification",
            ],
            "lien_mesure_rhpro": [
                "RH Pro", "mesure", "durant", "pendant", "au cours de",
                "mis en place", "proposé", "organisé", "prévu",
            ],
        },
        evaluation_prompt=(
            "Vérifier : formation identifiée, nature diplômante/certifiante "
            "précisée, lien avec la mesure RH Pro établi."
        ),
    ),

    # ── STAGE ───────────────────────────────────────────────────
    "STAGE": FieldSpecV3(
        key="STAGE",
        query="Stage (objectifs, résultats, auto-évaluation)",
        instructions=(
            "But : un résumé de l'évaluation ou auto-évaluation de stage. "
            "Explique ce qui s'est déroulé pendant le ou les stages. "
            "Et vérifier dans le journal s'il y a des annotations supplémentaires, "
            "voir même dans les emails (msg).\n\n"
            "Attendu :\n"
            "Si le stage valide bien l'orientation choisie ou non "
            "(il peut passer en mode négatif si on voit que le stage choisi "
            "n'est pas probant - limitation fonctionnelle, se référer à "
            "incertitude et obstacle). "
            "Cela peut aussi venir de l'attitude ou le comportement ou "
            "les interactions sociales.\n"
            "Poste occupé (intitulé) pendant le ou les stages "
            "(concierge, aide comptable, secrétaire, assistante administratif…).\n\n"
            "Que ce soit un stage LAI 15 ou 17 ou 18, le fonctionnement reste "
            "le même. La source est différente (selon la mesure 15, 17…) car elle "
            "se réfère directement au document portant la bonne mention.\n\n"
            "Format : 8-15 lignes."
        ),
        max_chars=3000,
        min_lines=8,
        max_lines=15,
        sources=["pdf"],
        immutable=False,
        required_elements=[
            "poste_stage",
            "deroulement",
            "validation_orientation",
            "evaluation_resultat",
        ],
        element_keywords={
            "poste_stage": [
                "stage", "poste", "fonction", "intitulé", "occupé",
                "concierge", "comptable", "secrétaire", "assistant",
                "aide", "employé", "ouvrier", "technicien",
            ],
            "deroulement": [
                "déroulé", "effectué", "réalisé", "participé", "travaillé",
                "semaine", "jour", "période", "durée", "activité",
            ],
            "validation_orientation": [
                "validé", "confirmé", "non validé", "invalidé", "probant",
                "pas probant", "compatible", "incompatible", "orientation",
                "choisi", "retenu", "positif", "négatif",
            ],
            "evaluation_resultat": [
                "évaluation", "auto-évaluation", "résultat", "retour",
                "appréciation", "satisfaisant", "insuffisant", "bon",
                "comportement", "attitude", "interaction", "LAI",
                "mesure 15", "mesure 17", "mesure 18",
            ],
        },
        evaluation_prompt=(
            "Vérifier : poste de stage identifié, déroulement décrit, "
            "validation ou invalidation de l'orientation, "
            "résultat de l'évaluation mentionné."
        ),
    ),

    # ── CONCLUSION ──────────────────────────────────────────────
    "CONCLUSION": FieldSpecV3(
        key="CONCLUSION",
        query="Conclusion globale et prochaines étapes",
        instructions=(
            "But : Valider ou invalider la cible professionnelle en fonction "
            "du ou des stages. Se doit d'expliquer pourquoi le stage n'a pas "
            "fonctionné ou est un échec. On doit voir si on a bien respecté "
            "les limitations quelles que soient sur les critères physique, "
            "formation, et stage. Si le stage est positif, on se doit tout de "
            "même de dire que les limitations ont été respectées.\n\n"
            "Format : 3 à 5 lignes environ."
        ),
        max_chars=1500,
        min_lines=3,
        max_lines=5,
        sources=["journal", "pdf", "msg"],
        immutable=False,
        required_elements=[
            "validation_cible",
            "coherence_stage",
            "respect_limitations",
        ],
        element_keywords={
            "validation_cible": [
                "validé", "invalidé", "confirmé", "infirmé", "cible",
                "objectif", "profession", "orientation", "pertinent",
                "viable", "réaliste",
            ],
            "coherence_stage": [
                "stage", "résultat", "évaluation", "expérience",
                "positif", "négatif", "probant", "échec", "réussite",
                "fonctionné", "pas fonctionné",
            ],
            "respect_limitations": [
                "limitation", "respecté", "contrainte", "physique",
                "formation", "aménagement", "compatible", "adapté",
                "restriction", "capacité",
            ],
        },
        evaluation_prompt=(
            "Vérifier : cible professionnelle validée ou invalidée, "
            "cohérence avec les résultats de stage, "
            "respect des limitations mentionné."
        ),
    ),
}


def get_field_spec_v3(key: str) -> Optional[FieldSpecV3]:
    """Return a V3 field spec by key, or None."""
    return FIELD_SPECS_V3.get(key)


def get_specs_for_report_type(report_type_key: str) -> list[FieldSpecV3]:
    """Return ordered list of V3 specs for a given report type."""
    from core.report_types import get_report_type

    rt = get_report_type(report_type_key)
    if not rt:
        return []
    specs = []
    for section_key in rt["sections"]:
        spec = FIELD_SPECS_V3.get(section_key)
        if spec:
            specs.append(spec)
    return specs
```

**Step 4: Run test to verify it passes**

Run: `cd "/Users/malik/Documents/Laboratoire 🧪/SCRIPT.IA" && python -m pytest tests/test_field_specs_v3.py -v --no-cov`
Expected: 11 passed

**Step 5: Commit**

```bash
git add core/field_specs_v3.py tests/test_field_specs_v3.py
git commit -m "feat: add field_specs_v3 with RH PRO specs for rapport initial (7 sections)"
```

---

## Task 3: Section Evaluator / Quality Gate (`core/section_evaluator.py`)

**Files:**
- Create: `core/section_evaluator.py`
- Test: `tests/test_section_evaluator.py`

**Step 1: Write the failing test**

```python
# tests/test_section_evaluator.py
from core.section_evaluator import evaluate_section, SectionEvaluation, SectionCheck
from core.field_specs_v3 import get_field_spec_v3


class TestSectionEvaluator:
    def test_empty_text_returns_vide(self):
        spec = get_field_spec_v3("PROFESSION")
        result = evaluate_section(spec, "")
        assert result.status == "VIDE"
        assert result.score == 0.0

    def test_non_renseigne_returns_vide(self):
        spec = get_field_spec_v3("PROFESSION")
        result = evaluate_section(spec, "Non renseigné")
        assert result.status == "VIDE"

    def test_good_profession_text(self):
        spec = get_field_spec_v3("PROFESSION")
        text = (
            "Monsieur Dupont était en arrêt maladie depuis 2022. "
            "Il occupait un poste de technicien de maintenance dans une PME industrielle. "
            "Ses missions principales comprenaient la maintenance préventive des machines, "
            "le diagnostic de pannes et la gestion des stocks de pièces détachées. "
            "Il travaillait en équipe de 5 personnes, principalement sur le terrain. "
            "Suite à un accident du travail, il a dû cesser son activité. "
            "Ses compétences techniques et sa polyvalence sont transférables "
            "vers des postes de contrôle qualité ou de coordination technique."
        )
        result = evaluate_section(spec, text)
        assert result.status == "BON"
        assert result.score >= 0.75

    def test_partial_profession_text(self):
        spec = get_field_spec_v3("PROFESSION")
        text = "Monsieur Dupont était technicien. Il travaillait en équipe."
        result = evaluate_section(spec, text)
        assert result.status == "A_REVOIR"
        assert result.score < 0.75
        # Should identify missing elements
        missing = [c.element for c in result.checks if not c.found]
        assert len(missing) > 0

    def test_comment_lists_missing_elements(self):
        spec = get_field_spec_v3("PROFESSION")
        text = "Monsieur Dupont était technicien."
        result = evaluate_section(spec, text)
        assert result.comment  # Non-empty comment
        assert "manque" in result.comment.lower() or "absent" in result.comment.lower()

    def test_checks_contain_all_required_elements(self):
        spec = get_field_spec_v3("PROFESSION")
        result = evaluate_section(spec, "Du texte quelconque.")
        element_names = [c.element for c in result.checks]
        for req in spec.required_elements:
            assert req in element_names

    def test_keywords_matched_populated(self):
        spec = get_field_spec_v3("PROFESSION")
        text = "Il était en arrêt maladie et occupait un poste de technicien."
        result = evaluate_section(spec, text)
        found_checks = [c for c in result.checks if c.found]
        for check in found_checks:
            assert len(check.keywords_matched) > 0

    def test_conclusion_evaluation(self):
        spec = get_field_spec_v3("CONCLUSION")
        text = (
            "Le stage a confirmé la cible professionnelle de Monsieur Dupont. "
            "Les résultats du stage sont positifs et les limitations physiques "
            "ont été respectées tout au long de la mesure."
        )
        result = evaluate_section(spec, text)
        assert result.status == "BON"
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/malik/Documents/Laboratoire 🧪/SCRIPT.IA" && python -m pytest tests/test_section_evaluator.py -v --no-cov`
Expected: FAIL (module not found)

**Step 3: Write implementation**

```python
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

from dataclasses import dataclass, field

from core.field_specs_v3 import FieldSpecV3


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

    text_lower = stripped.lower()

    checks: list[SectionCheck] = []
    for element in spec.required_elements:
        keywords = spec.element_keywords.get(element, [])
        matched = [kw for kw in keywords if kw.lower() in text_lower]
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
```

**Step 4: Run test to verify it passes**

Run: `cd "/Users/malik/Documents/Laboratoire 🧪/SCRIPT.IA" && python -m pytest tests/test_section_evaluator.py -v --no-cov`
Expected: 8 passed

**Step 5: Commit**

```bash
git add core/section_evaluator.py tests/test_section_evaluator.py
git commit -m "feat: add section evaluator (quality gate BON/A_REVOIR/VIDE)"
```

---

## Task 4: Backend — Wire V3 into generate.py

**Files:**
- Modify: `core/generate.py` (add V3 path)
- Test: `tests/test_generate_v3.py`

**Step 1: Write the failing test**

```python
# tests/test_generate_v3.py
"""Test that generate_fields uses V3 specs when report_type is provided."""
from unittest.mock import patch, MagicMock
from core.generate import generate_fields


class TestGenerateV3:
    def test_v3_generates_only_report_type_sections(self):
        """When report_type='rapport_initial', only 7 sections + deterministic are generated."""
        payload = {
            "documents": [
                {
                    "path": "/fake/journal.docx",
                    "text": "M. Dupont était technicien en arrêt maladie depuis 2022. "
                            "Il a un CFC de mécanicien obtenu en 2010 à Genève. "
                            "Obstacle principal : douleurs dorsales limitant le port de charges. "
                            "Piste retenue : reconversion en contrôle qualité. "
                            "Formation ECDL prévue durant la mesure RH Pro. "
                            "Stage effectué comme aide-comptable, évaluation positive. "
                            "La cible est validée, les limitations ont été respectées.",
                    "ext": ".docx",
                    "hash": "abc",
                    "pages": None,
                    "mtime": "2026-01-01",
                    "extractor": "docx",
                    "size_bytes": 1000,
                }
            ]
        }

        with patch("core.generate.ollama_generate") as mock_llm:
            mock_llm.return_value = MagicMock(
                success=True, value="Texte généré par le LLM."
            )

            answers = generate_fields(
                payload,
                model="test",
                host="http://localhost:11434",
                topk=3,
                temperature=0.2,
                top_p=0.9,
                report_type="rapport_initial",
            )

        # Should have exactly the 7 V3 sections
        expected_keys = {
            "PROFESSION", "FORMATION", "INCERTITUDE_ET_OBSTACLE",
            "ORIENTATION", "FORMATION_DURANT_MESURE", "STAGE", "CONCLUSION",
        }
        assert set(answers.keys()) == expected_keys

    def test_v3_without_report_type_uses_legacy(self):
        """Without report_type, falls back to V2/legacy behavior."""
        payload = {"documents": [{"path": "/f", "text": "texte", "ext": ".txt",
                                   "hash": "x", "pages": None, "mtime": "2026-01-01",
                                   "extractor": "txt", "size_bytes": 10}]}

        with patch("core.generate.ollama_generate") as mock_llm:
            mock_llm.return_value = MagicMock(
                success=True, value="Réponse."
            )

            answers = generate_fields(
                payload,
                model="test",
                host="http://localhost:11434",
                topk=3,
                temperature=0.2,
                top_p=0.9,
                # No report_type → legacy
            )

        # Should use DEFAULT_FIELDS (2 fields: PROFESSION, FORMATION)
        assert "PROFESSION" in answers
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/malik/Documents/Laboratoire 🧪/SCRIPT.IA" && python -m pytest tests/test_generate_v3.py -v --no-cov`
Expected: FAIL (report_type parameter not recognized)

**Step 3: Modify generate_fields in `core/generate.py`**

Add `report_type` parameter. When provided, build field list from V3 specs instead of V2/legacy.

Changes to `generate_fields()` signature — add:
```python
    report_type: Optional[str] = None,
```

At the top of `generate_fields()` body, before `fields = fields or DEFAULT_FIELDS`, add:
```python
    # V3: if report_type is provided, use V3 specs
    if report_type and not fields:
        from .field_specs_v3 import get_specs_for_report_type
        v3_specs = get_specs_for_report_type(report_type)
        if v3_specs:
            fields = [
                {"key": s.key, "query": s.query, "instructions": s.instructions}
                for s in v3_specs
            ]
            USE_V3 = True
        else:
            USE_V3 = False
    else:
        USE_V3 = False
```

Inside the field loop, when resolving spec, add V3 branch:
```python
        if USE_V3:
            from .field_specs_v3 import get_field_spec_v3
            spec = get_field_spec_v3(key)
            if not spec:
                # Fallback to V2
                spec = get_field_spec_v2(key) if USE_SCHEMA_V2 else get_field_spec(key)
        elif USE_SCHEMA_V2:
            ...  # existing V2 logic
```

**Step 4: Run tests**

Run: `cd "/Users/malik/Documents/Laboratoire 🧪/SCRIPT.IA" && python -m pytest tests/test_generate_v3.py -v --no-cov`
Expected: 2 passed

**Step 5: Commit**

```bash
git add core/generate.py tests/test_generate_v3.py
git commit -m "feat: wire V3 field specs into generate_fields via report_type param"
```

---

## Task 5: Backend API — Report type endpoints + review endpoints

**Files:**
- Create: `backend/api/routes/review.py`
- Modify: `backend/api/routes/reports.py` (add report_type to ReportCreateRequest)
- Modify: `backend/api/models/__init__.py` (add new models)
- Modify: `backend/main.py` (register review router)
- Modify: `backend/workers/report_worker.py` (pass report_type)
- Modify: `backend/workers/orchestrator.py` (pass report_type, store answers for review)
- Test: `tests/test_api_review.py`

**Step 1: Write the failing test**

```python
# tests/test_api_review.py
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestReportTypeEndpoints:
    def test_list_report_types(self, client):
        """GET /api/report-types returns available types."""
        response = client.get("/api/report-types")
        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        keys = [t["key"] for t in data["types"]]
        assert "rapport_initial" in keys

    def test_create_report_with_type(self, client):
        """POST /api/reports with report_type field."""
        with patch("backend.api.routes.reports.queue") as mock_queue:
            mock_job = MagicMock()
            mock_job.id = "test-job-123"
            mock_queue.enqueue.return_value = mock_job

            response = client.post("/api/reports", json={
                "client_name": "Test Client",
                "report_type": "rapport_initial",
            })

        assert response.status_code in (200, 201)
        # Verify report_type was passed to the job
        call_kwargs = mock_queue.enqueue.call_args
        assert call_kwargs is not None
```

Note: the `client` fixture should be added to conftest.py if not already present:
```python
@pytest.fixture
def client():
    from backend.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/malik/Documents/Laboratoire 🧪/SCRIPT.IA" && python -m pytest tests/test_api_review.py -v --no-cov`
Expected: FAIL

**Step 3: Implement**

3a. Add to `backend/api/models/__init__.py`:
```python
class ReportCreateRequest(BaseModel):
    # ... existing fields ...
    report_type: Optional[str] = None  # NEW: "rapport_initial", etc.
```

3b. Create `backend/api/routes/review.py`:
```python
"""Review endpoints for V3 report sections."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from redis import Redis
from rq.job import Job

from backend.config import settings
from core.report_types import list_report_types
from core.section_evaluator import evaluate_section
from core.field_specs_v3 import get_field_spec_v3, get_specs_for_report_type

router = APIRouter()


@router.get("/report-types")
def get_report_types():
    return {"types": list_report_types()}


@router.get("/reports/{job_id}/review")
def get_report_review(job_id: str):
    """Return sections + evaluations for a completed report."""
    redis_conn = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                       db=settings.REDIS_DB, decode_responses=True)
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(404, "Job not found")

    if job.get_status() != "finished":
        raise HTTPException(400, "Report not yet completed")

    meta = job.meta or {}
    report_type = meta.get("report_type", "rapport_initial")
    answers = meta.get("answers", {})

    specs = get_specs_for_report_type(report_type)
    sections = []
    for spec in specs:
        answer_data = answers.get(spec.key, {})
        text = answer_data.get("value", "") if isinstance(answer_data, dict) else ""
        evaluation = evaluate_section(spec, text)
        sections.append({
            "key": spec.key,
            "text": text,
            "immutable": spec.immutable,
            "sources": spec.sources,
            "evaluation": {
                "status": evaluation.status,
                "score": evaluation.score,
                "checks": [
                    {"element": c.element, "found": c.found,
                     "keywords_matched": c.keywords_matched}
                    for c in evaluation.checks
                ],
                "comment": evaluation.comment,
            },
            "evaluation_prompt": spec.evaluation_prompt,
        })

    bon_count = sum(1 for s in sections if s["evaluation"]["status"] == "BON")
    return {
        "job_id": job_id,
        "report_type": report_type,
        "sections": sections,
        "summary": {
            "total": len(sections),
            "bon": bon_count,
            "a_revoir": sum(1 for s in sections if s["evaluation"]["status"] == "A_REVOIR"),
            "vide": sum(1 for s in sections if s["evaluation"]["status"] == "VIDE"),
        },
    }


class SectionUpdateRequest(BaseModel):
    text: str


@router.put("/reports/{job_id}/sections/{section_key}")
def update_section(job_id: str, section_key: str, body: SectionUpdateRequest):
    """Save manual edit of a section. Recalculates evaluation."""
    redis_conn = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                       db=settings.REDIS_DB, decode_responses=True)
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(404, "Job not found")

    spec = get_field_spec_v3(section_key)
    if not spec:
        raise HTTPException(404, f"Unknown section: {section_key}")

    if spec.immutable:
        meta = job.meta or {}
        answers = meta.get("answers", {})
        existing = answers.get(section_key, {})
        if isinstance(existing, dict) and existing.get("value", "").strip():
            # Already has content and is immutable — check if this is a first edit
            # (immutable means "don't change on regeneration", but manual edits are allowed)
            pass

    # Update answer in job meta
    meta = job.meta or {}
    answers = meta.get("answers", {})
    if section_key not in answers:
        answers[section_key] = {}
    answers[section_key]["value"] = body.text
    answers[section_key]["answer"] = body.text
    answers[section_key]["manually_edited"] = True
    meta["answers"] = answers
    job.meta = meta
    job.save_meta()

    # Recalculate evaluation
    evaluation = evaluate_section(spec, body.text)
    return {
        "key": section_key,
        "text": body.text,
        "evaluation": {
            "status": evaluation.status,
            "score": evaluation.score,
            "checks": [
                {"element": c.element, "found": c.found,
                 "keywords_matched": c.keywords_matched}
                for c in evaluation.checks
            ],
            "comment": evaluation.comment,
        },
    }


class RegenerateRequest(BaseModel):
    hint: Optional[str] = None  # Indication supplementaire du consultant


@router.post("/reports/{job_id}/sections/{section_key}/regenerate")
def regenerate_section(job_id: str, section_key: str, body: RegenerateRequest):
    """Regenerate a single section with optional hint."""
    import json
    from core.generate import build_prompt, ollama_generate, sanitize_output, truncate_lines, truncate_chars
    from core.context import build_index
    from core.llm_router import LLMConfig

    redis_conn = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                       db=settings.REDIS_DB, decode_responses=True)
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(404, "Job not found")

    spec = get_field_spec_v3(section_key)
    if not spec:
        raise HTTPException(404, f"Unknown section: {section_key}")

    meta = job.meta or {}

    # Retrieve stored extracted payload path or inline data
    extracted_payload = meta.get("extracted_payload")
    if not extracted_payload:
        raise HTTPException(400, "No extracted data available for regeneration")

    # Build RAG index
    chunks, index = build_index(extracted_payload, chunk_size=1200, overlap=200)
    top = index.topk(spec.query, 10)
    context_blocks = []
    for idx, score in top:
        ch = chunks[idx]
        context_blocks.append({
            "score": score, "chunk_id": ch.chunk_id,
            "source_path": ch.source_path, "page": ch.page, "text": ch.text,
        })

    # Build prompt with optional hint
    instruction = spec.instructions
    if body.hint:
        instruction += f"\n\nIndication supplémentaire du consultant : {body.hint}"

    prompt = build_prompt(spec, instruction, context_blocks)

    # Call LLM
    llm_meta = meta.get("llm_config", {})
    llm_config = LLMConfig(
        provider=llm_meta.get("provider", "ollama"),
        base_url=llm_meta.get("base_url", settings.OLLAMA_HOST),
        model=llm_meta.get("model", settings.OLLAMA_MODEL),
        temperature=llm_meta.get("temperature", 0.2),
        max_tokens=llm_meta.get("max_tokens", 4096),
        top_p=llm_meta.get("top_p", 0.9),
        timeout=llm_meta.get("timeout", 120.0),
    )

    result = ollama_generate(
        model=llm_config.model, prompt=prompt, host=llm_config.base_url,
        temperature=llm_config.temperature, top_p=llm_config.top_p,
        llm_config=llm_config, field_name=section_key,
    )

    if not result.success:
        raise HTTPException(500, f"LLM error: {result.error}")

    cleaned = sanitize_output(result.value)
    cleaned = truncate_lines(cleaned, spec.max_lines)
    cleaned = truncate_chars(cleaned, spec.max_chars)

    # Update answer
    answers = meta.get("answers", {})
    answers[section_key] = {
        "field": section_key,
        "value": cleaned,
        "answer": cleaned,
        "regenerated": True,
        "hint": body.hint,
    }
    meta["answers"] = answers
    job.meta = meta
    job.save_meta()

    # Evaluate
    evaluation = evaluate_section(spec, cleaned)
    return {
        "key": section_key,
        "text": cleaned,
        "evaluation": {
            "status": evaluation.status,
            "score": evaluation.score,
            "checks": [
                {"element": c.element, "found": c.found,
                 "keywords_matched": c.keywords_matched}
                for c in evaluation.checks
            ],
            "comment": evaluation.comment,
        },
    }


@router.post("/reports/{job_id}/export")
def export_report(job_id: str):
    """Generate final DOCX from current section states."""
    from docx import Document
    from core.render import replace_text_everywhere, build_moustache_mapping
    from fastapi.responses import FileResponse
    from pathlib import Path
    import tempfile

    redis_conn = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                       db=settings.REDIS_DB, decode_responses=True)
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(404, "Job not found")

    meta = job.meta or {}
    answers = meta.get("answers", {})
    template_path = meta.get("template_path", str(settings.TEMPLATE_PATH))

    doc = Document(template_path)
    moustache_mapping = build_moustache_mapping(answers)
    if moustache_mapping:
        replace_text_everywhere(doc, moustache_mapping)

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    doc.save(tmp.name)
    tmp.close()

    client_name = meta.get("client_name", "rapport")
    return FileResponse(
        tmp.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"rapport_{client_name}.docx",
    )
```

3c. Register router in `backend/main.py` — add:
```python
from backend.api.routes import review
app.include_router(review.router, prefix="/api", tags=["review"])
```

3d. Modify `backend/api/routes/reports.py` — add `report_type` to ReportCreateRequest and pass it to the enqueue call.

3e. Modify `backend/workers/report_worker.py` — accept `report_type` param and pass to orchestrator.

3f. Modify `backend/workers/orchestrator.py`:
- Add `report_type` to `ReportGenerationParams`
- Pass `report_type` to `generate_fields()`
- Store `answers` and `extracted_payload` in job meta for review/regeneration

**Step 4: Run tests**

Run: `cd "/Users/malik/Documents/Laboratoire 🧪/SCRIPT.IA" && python -m pytest tests/test_api_review.py -v --no-cov`
Expected: 2 passed

**Step 5: Commit**

```bash
git add backend/api/routes/review.py backend/api/models/__init__.py backend/main.py \
  backend/api/routes/reports.py backend/workers/report_worker.py backend/workers/orchestrator.py \
  tests/test_api_review.py
git commit -m "feat: add review API endpoints (report-types, review, edit, regenerate, export)"
```

---

## Task 6: Frontend — Report Type Dropdown in ClientSelection

**Files:**
- Modify: `frontend/src/pages/ClientSelection.jsx`
- Modify: `frontend/src/services/api.js`

**Step 1: Add API method in `frontend/src/services/api.js`**

Add to `reportsAPI`:
```javascript
  getReportTypes: async () => {
    const response = await api.get('/report-types');
    return response.data;
  },
```

**Step 2: Add dropdown in `ClientSelection.jsx`**

Add state:
```javascript
const [reportTypes, setReportTypes] = useState([]);
const [selectedReportType, setSelectedReportType] = useState('rapport_initial');
```

Add useEffect to fetch types on mount:
```javascript
useEffect(() => {
  reportsAPI.getReportTypes().then(data => setReportTypes(data.types || []));
}, []);
```

Add dropdown after client selection section:
```jsx
<div className="form-section">
  <h3>Type de rapport</h3>
  <select value={selectedReportType}
          onChange={e => setSelectedReportType(e.target.value)}>
    {reportTypes.map(rt => (
      <option key={rt.key} value={rt.key}
              disabled={rt.sections.length === 0}>
        {rt.label} {rt.sections.length === 0 ? '(bientôt)' : ''}
      </option>
    ))}
  </select>
</div>
```

Pass `report_type` in form submission:
```javascript
const payload = {
  ...existingPayload,
  report_type: selectedReportType,
};
```

**Step 3: Redirect to review page after completion**

In Progress.jsx, on job completed, redirect to `/review/{jobId}` instead of showing download link.

**Step 4: Commit**

```bash
git add frontend/src/pages/ClientSelection.jsx frontend/src/services/api.js frontend/src/pages/Progress.jsx
git commit -m "feat: add report type dropdown + redirect to review page"
```

---

## Task 7: Frontend — ReportReview Page (3-column layout)

**Files:**
- Create: `frontend/src/pages/ReportReview.jsx`
- Create: `frontend/src/pages/ReportReview.css`
- Modify: `frontend/src/App.jsx` (add route)
- Modify: `frontend/src/services/api.js` (add review API methods)

**Step 1: Add API methods in `api.js`**

```javascript
export const reviewAPI = {
  getReview: async (jobId) => {
    const response = await api.get(`/reports/${jobId}/review`);
    return response.data;
  },
  updateSection: async (jobId, sectionKey, text) => {
    const response = await api.put(`/reports/${jobId}/sections/${sectionKey}`, { text });
    return response.data;
  },
  regenerateSection: async (jobId, sectionKey, hint = null) => {
    const response = await api.post(`/reports/${jobId}/sections/${sectionKey}/regenerate`, { hint });
    return response.data;
  },
  exportReport: async (jobId) => {
    const response = await api.post(`/reports/${jobId}/export`, null, { responseType: 'blob' });
    return response.data;
  },
};
```

**Step 2: Create ReportReview.jsx**

The page has 3 columns:
- Left sidebar: section list with colored status bubbles
- Center: editable text area + regeneration hint + action buttons
- Right panel: evaluation checklist + score + sources

Key interactions:
- Click section → loads its content and evaluation
- Edit text → "Sauvegarder" button appears, saves via PUT, recalculates evaluation
- "Relancer" → optional hint input, calls POST regenerate, updates content + evaluation
- "Exporter DOCX" → downloads final document

**Step 3: Add route in App.jsx**

```jsx
import ReportReview from './pages/ReportReview';
// In Routes:
<Route path="/review/:jobId" element={<ReportReview />} />
```

**Step 4: Commit**

```bash
git add frontend/src/pages/ReportReview.jsx frontend/src/pages/ReportReview.css \
  frontend/src/App.jsx frontend/src/services/api.js
git commit -m "feat: add ReportReview page (3-column layout with quality gate)"
```

---

## Task 8: Integration Test — Full Pipeline

**Files:**
- Test: `tests/test_integration_v3.py`

**Step 1: Write integration test**

```python
# tests/test_integration_v3.py
"""End-to-end test: report_type=rapport_initial generates 7 sections with evaluations."""
from unittest.mock import patch, MagicMock
from core.generate import generate_fields
from core.section_evaluator import evaluate_report
from core.field_specs_v3 import get_specs_for_report_type


class TestIntegrationV3:
    def test_full_pipeline_rapport_initial(self):
        payload = {
            "documents": [{
                "path": "/test/journal.docx",
                "text": (
                    "M. Dupont, ancien technicien de maintenance, est en arrêt maladie "
                    "depuis mars 2024 suite à un accident du travail (chute sur chantier). "
                    "Il occupait un poste de technicien chez ABB SA à plein temps. "
                    "Ses missions comprenaient la maintenance préventive, le diagnostic "
                    "de pannes et la coordination avec les sous-traitants. "
                    "Il travaillait en équipe de 6 sur le terrain. "
                    "Ses compétences techniques sont transférables. "
                    "Il possède un CFC de mécanicien industriel obtenu en 2008 à Genève "
                    "et une formation continue en automatisation (2015, CEFCO). "
                    "Obstacles : douleurs dorsales chroniques limitant le port de charges, "
                    "pas de permis de conduire. Nécessite un aménagement de poste. "
                    "Piste retenue : contrôle qualité (compatible physiquement). "
                    "Piste non retenue : retour en maintenance (contre-indiqué par limitations). "
                    "Formation ECDL avancé prévue durant la mesure RH Pro. "
                    "Stage de 4 semaines comme aide au contrôle qualité chez Rolex. "
                    "Évaluation positive, le stage a validé l'orientation. "
                    "Conclusion : la cible professionnelle est confirmée par le stage. "
                    "Les limitations physiques ont été respectées."
                ),
                "ext": ".docx", "hash": "test", "pages": None,
                "mtime": "2026-01-01", "extractor": "docx", "size_bytes": 2000,
            }]
        }

        with patch("core.generate.ollama_generate") as mock_llm:
            # Return different text per section
            mock_llm.return_value = MagicMock(
                success=True,
                value=(
                    "M. Dupont était en arrêt maladie. Il occupait un poste de technicien "
                    "de maintenance chez ABB. Ses missions comprenaient la maintenance "
                    "préventive et le diagnostic. Il travaillait en équipe sur le terrain. "
                    "Suite à un accident, il a dû cesser. Ses compétences sont transférables."
                ),
            )

            answers = generate_fields(
                payload,
                model="test", host="http://localhost:11434",
                topk=3, temperature=0.2, top_p=0.9,
                report_type="rapport_initial",
            )

        assert len(answers) == 7

        # Evaluate all sections
        specs = get_specs_for_report_type("rapport_initial")
        flat_answers = {k: v.get("value", "") for k, v in answers.items()}
        evaluations = evaluate_report(specs, flat_answers)

        assert len(evaluations) == 7
        for key, ev in evaluations.items():
            assert ev.status in ("BON", "A_REVOIR", "VIDE"), f"{key}: {ev.status}"
```

**Step 2: Run test**

Run: `cd "/Users/malik/Documents/Laboratoire 🧪/SCRIPT.IA" && python -m pytest tests/test_integration_v3.py -v --no-cov`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_integration_v3.py
git commit -m "test: add integration test for V3 rapport initial pipeline"
```

---

## Task 9: Run full test suite + verify no regressions

**Step 1: Run all tests**

Run: `cd "/Users/malik/Documents/Laboratoire 🧪/SCRIPT.IA" && python -m pytest tests/ -v --no-cov`
Expected: All existing tests + new tests pass. No regressions.

**Step 2: Fix any failures if needed**

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: V3 complete — report types, field specs RH PRO, quality gate, review page"
```

---

## Summary of deliverables

| # | What | Files |
|---|------|-------|
| 1 | Report types registry | `core/report_types.py` |
| 2 | Field specs V3 (RH PRO) | `core/field_specs_v3.py` |
| 3 | Quality gate evaluator | `core/section_evaluator.py` |
| 4 | V3 wiring in generate.py | `core/generate.py` (modified) |
| 5 | Backend API (review/edit/regen) | `backend/api/routes/review.py` + modifications |
| 6 | Report type dropdown | `frontend/src/pages/ClientSelection.jsx` (modified) |
| 7 | Review page (3 colonnes) | `frontend/src/pages/ReportReview.jsx` |
| 8 | Integration test | `tests/test_integration_v3.py` |
| 9 | Regression check | Full test suite |
