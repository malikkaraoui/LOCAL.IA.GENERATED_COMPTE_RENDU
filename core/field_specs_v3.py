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
        query="Formations, diplômes, certifications, parcours scolaire, tests de positionnement, évaluations de niveau",
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
        query="Obstacles, freins, difficultés, limitations, santé, mobilité, langue, arrêt de travail, contraintes",
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
