"""
Field Specifications V2 - Schéma complet aligné sur le template DOCX

OBJECTIF:
- Schéma complet à ~54 champs alignés sur le template réel
- Typologie stricte: deterministic | narrative | list | enum | test_narrative
- Anti-hallucination: extraction prioritaire, fallback "Non évalué"/"Non renseigné"
- Prompt wrapper unique et versionné avec marqueur sentinel
- Suppression automatique des sections vides dans le DOCX

STRUCTURE:
A) INFORMATIONS PERSONNELLES (4 déterministes + 1 extraction AVS)
B) PROFIL (4 narratifs)
C) RESSOURCES (5 narratifs/listes)
D) MARCHÉ & COMPORTEMENT (6 narratifs)
E) ORIENTATION & MÉTIERS (8 narratifs/listes)
F) RIASEC / VOCATIO (5 extraction PDF + fallback LLM)
G) NIVEAUX LANGUES (3 enum CECRL)
H) NIVEAUX BUREAUTIQUE (4 enum séparés)
I) TESTS PSYCHOMÉTRIQUES (7 narratifs courts)
J) FORMATIONS SUPÉRIEURES (2 listes)
K) FINAL (5 narratifs)

PROMPT SYSTEM:
- Marqueur sentinel: [[FIELD_SPECS_V2_PROMPT_V1]]
- Règles anti-hallucination strictes
- Format validation par type de champ
"""

from dataclasses import dataclass
from typing import Optional, List

# Marqueur sentinel obligatoire pour validation runtime
PROMPT_SENTINEL = "[[FIELD_SPECS_V2_PROMPT_V1]]"
PROMPT_VERSION = "V1"

# Valeurs enum autorisées
CECRL_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2", "Non évalué"]
BUREAUTIQUE_LEVELS = ["Faible", "Moyen", "Bon", "Très bon", "Non évalué"]

# Alias de compatibilité (certains tests/imports historiques attendent TOOL_LEVELS)
TOOL_LEVELS = BUREAUTIQUE_LEVELS

# Alias de compatibilité (tests/anciens schémas): niveaux de tests/évaluations
TEST_LEVELS = ["OK", "Moyen", "À renforcer", "Non évalué"]


@dataclass(frozen=True)
class FieldSpecV2:
    """Spécification d'un champ V2"""
    key: str
    field_type: str  # deterministic | narrative | list | enum | test_narrative
    query: str
    instructions: str
    max_chars: int
    max_lines: int
    require_sources: bool = False
    skip_llm_if_no_sources: bool = False
    enum_values: Optional[List[str]] = None
    extraction_policy: str = "llm_with_guardrails"  # deterministic | extract_only | llm_with_guardrails
    remove_if_empty: bool = True  # Supprimer la section du DOCX si vide


def build_system_prompt() -> str:
    """
    Construit le SYSTEM PROMPT global (règles non négociables).
    Conforme à prompt.md section 3.
    """
    return f"""Tu es un assistant de rédaction de rapports d'orientation professionnelle pour un office cantonal (service public suisse).

### CADRE LÉGAL ET AUTORISATIONS
- Ce traitement est **100% local** (aucune donnée ne quitte le réseau interne).
- L'assuré a **consenti** au traitement de ses données dans le cadre de son bilan professionnel.
- Tu es **autorisé et obligé** de traiter toutes les informations personnelles fournies dans les SOURCES (nom, prénom, parcours, compétences, résultats de tests, etc.).
- Tu ne dois **JAMAIS refuser** de traiter les données fournies. Ton rôle est de rédiger le rapport, pas de juger la pertinence des données.
- **INTERDIT** de répondre par des excuses, des refus ou des messages du type "je ne peux pas", "je suis désolé", "informations personnelles". Tu DOIS rédiger le contenu demandé.

Tu dois produire une sortie **strictement conforme** aux instructions ci-dessous.

{PROMPT_SENTINEL}

### RÈGLES ANTI-HALLUCINATION (CRITIQUES)
1) **Tu n'inventes jamais** de faits (employeurs, dates, diplômes, scores, niveaux, métiers précis, lieux, événements).
2) Tu t'appuies **uniquement** sur les éléments présents dans les **SOURCES** fournies.
3) Si une information n'est pas trouvée dans les SOURCES :
   - pour un champ narratif : écrire "Non renseigné" sur l'élément manquant (ou rester général sans créer de fait)
   - pour un champ enum : retourner **exactement** "Non évalué"
   - pour un champ list : retourner `[]`
4) Tu ne déduis pas un niveau (langues/bureautique) "par bon sens". Il faut une **preuve explicite** dans les sources.
5) Tu ne mentionnes **jamais** les sources dans la réponse (pas de "selon le document…", pas de citations).

### STYLE ET FORME
- Langue : **français** professionnel, neutre, sans jugement.
- Interdit : "…" (points de suspension), emojis, ton familier.
- Pas de titres inutiles. Pas de bavardage.
- Pas de contenu médical/diagnostic (sauf si explicitement écrit dans les sources, et alors rester descriptif).

### RESPECT STRICT DES FORMATS (selon field_type)
- `narrative` : texte fluide, pro, longueur limitée (voir max_chars), sans liste longue.
- `list` : **UNIQUEMENT** un JSON array valide `["item1", "item2"]` (sans texte autour).
- `enum` : **UNIQUEMENT** une valeur exacte parmi enum_values (un seul mot/ligne).
- `test_narrative` : paragraphe court (score + interprétation), extrait fidèlement du PDF de test.
- `deterministic` : ne doit pas être traité par le LLM.

### CONTRÔLE QUALITÉ INTERNE (checklist avant de répondre)
Avant d'envoyer ta réponse :
- Ai-je inventé un fait (date, employeur, diplôme, score) ? → si oui, supprimer.
- Ai-je respecté le format attendu (JSON array / valeur seule / texte narratif) ?
- Ai-je respecté la limite max_chars ?
- Ai-je évité "…" ?

### PÉRIMÈTRE DE VÉRITÉ
Tu ne dois JAMAIS créer :
- noms d'employeurs (si absents)
- dates (si absentes)
- intitulés de diplômes/certifs (si absents)
- scores/niveaux (si absents)
- métiers trop spécifiques (si absents)

Tu peux uniquement :
- reformuler et synthétiser des éléments présents
- rester général en indiquant "Non renseigné" sur les manques
"""


def build_user_prompt(
    field_spec: 'FieldSpecV2',
    sources: str = "",
    sources_count: int = 0
) -> str:
    """
    Construit le USER PROMPT pour un champ spécifique.
    """
    enum_values_str = ", ".join(field_spec.enum_values) if field_spec.enum_values else ""

    header = f"""FIELD_KEY: {field_spec.key}
FIELD_TYPE: {field_spec.field_type}
QUERY: {field_spec.query}
MAX_CHARS: {field_spec.max_chars}
MAX_LINES: {field_spec.max_lines}
REQUIRE_SOURCES: {field_spec.require_sources}
ENUM_VALUES: {enum_values_str}

INSTRUCTIONS:
{field_spec.instructions}
"""

    sources_block = f"""
<SOURCES>
{sources if sources else "(Aucune source disponible)"}
</SOURCES>
"""

    if field_spec.field_type == "narrative":
        response_rules = """
RÈGLES DE RÉPONSE:
- Respecte strictement FIELD_TYPE (narrative = texte professionnel).
- N'invente aucun fait.
- Ne mentionne jamais les sources.
- Si une info manque : indique "Non renseigné" sur l'élément manquant.
- Interdit d'utiliser "...".
- Éviter les listes longues. Préférer 2 paragraphes courts si besoin.
- Si require_sources=True et sources absentes : répondre exactement "Non renseigné".
"""
    elif field_spec.field_type == "test_narrative":
        response_rules = """
RÈGLES DE RÉPONSE:
- Paragraphe court : score/résultat + interprétation brève.
- Extraire fidèlement le score ou résultat du PDF de test.
- Ne pas inventer de score ou de résultat.
- Si aucun résultat trouvé dans les sources : répondre "Non renseigné".
- Maximum 5 lignes.
"""
    elif field_spec.field_type == "list":
        response_rules = """
RÈGLES DE RÉPONSE:
- Sortie **UNIQUEMENT** : un tableau JSON valide, ex: ["item 1", "item 2", "item 3"]
- Pas de texte avant/après. Pas de markdown.
- Items courts : 5-14 mots, neutres, pro.
- Si aucune info : []
- RETOURNE UNIQUEMENT UN TABLEAU JSON VALIDE.
"""
    elif field_spec.field_type == "enum":
        response_rules = f"""
RÈGLES DE RÉPONSE:
- Sortie **UNIQUEMENT** : une valeur exacte parmi : {enum_values_str}
- Si pas de preuve explicite dans les sources : "Non évalué"
- Jamais d'explication, jamais de phrase.
- Ne JAMAIS déduire à partir du fait que la personne "parle bien" ou "utilise l'outil".
- Il faut une **preuve explicite** dans les sources (test, évaluation, certification).
"""
    else:
        response_rules = """
RÈGLES DE RÉPONSE:
- Respecte le format attendu selon FIELD_TYPE.
- Ne mentionne pas les sources.
"""

    return header + sources_block + response_rules


def validate_prompt_has_sentinel(prompt: str) -> bool:
    """
    Valide que le prompt contient le marqueur sentinel.
    """
    if PROMPT_SENTINEL not in prompt:
        raise ValueError(
            f"ERREUR CRITIQUE: Le prompt ne contient pas le marqueur sentinel '{PROMPT_SENTINEL}'. "
            "Le prompt ne peut pas être envoyé au LLM sans ce marqueur de validation."
        )
    return True


# ============================================================================
# INSTRUCTIONS PAR TYPE DE CHAMP
# ============================================================================

def _build_narrative_instructions(field_key: str) -> str:
    """Instructions détaillées pour champs narratifs selon spécifications"""

    instructions = {
        "PROFESSION": """
But : donner une photo claire et factuelle de la situation pro actuelle (ou la dernière connue).

Attendu :
- Statut : en poste / en recherche / en arrêt / en transition.
- Poste actuel (ou dernier poste), secteur, type de contrat si connu, rythme (temps plein/partiel).
- Missions principales (3-6 points implicites dans un texte fluide), responsabilités, niveau d'autonomie.
- Environnement : équipe, terrain/bureau, contraintes physiques/horaires si mentionnées.

Contraintes :
- Ne jamais inventer employeur, dates, intitulés précis si absents.
- Si info manquante : l'indiquer ("non renseigné") plutôt que combler.

Format : 6-10 lignes, pro, sans liste longue.
""",
        "FORMATION": """
But : synthétiser les acquis académiques et certifs utiles au projet.

Attendu :
- Diplômes et formations structurés (du plus récent/élevé vers l'ancien).
- Domaine + nature (diplôme/certificat/formation courte) + date/durée si disponible.
- Si parcours hétérogène : regrouper par thème (ex : technique / administratif / sécurité).
- Mentionner les formations en cours si présentes.

Contraintes :
- Zéro invention d'école, de date, de certification.
- Ne pas transformer une "intention de formation" en formation "faite".

Format : 6-12 lignes, lisible, éventuellement 2 mini-paragraphes.
""",
        "PRESENTATION": """
But : dresser un portrait synthétique de la personne (première impression professionnelle).

Attendu :
- Profil général : âge approximatif si mentionné, situation (en emploi/recherche/transition).
- Parcours résumé en 2-3 phrases (secteurs, expérience, niveau de formation).
- Dynamique actuelle : ce qui amène la personne dans ce bilan/accompagnement.
- Posture observée si mentionnée dans les sources (motivée, réservée, proactive...).

Contraintes :
- Ne pas inventer de traits de personnalité.
- Rester factuel et bienveillant.

Format : 5-8 lignes, un paragraphe fluide.
""",
        "RELATION_A_LA_CARRIERE": """
But : décrire la relation de la personne à sa carrière/son projet professionnel.

Attendu :
- Rapport au travail : stabilité recherchée, envie de changement, rapport au statut.
- Perception de son parcours : linéaire, éclaté, en construction, satisfait/insatisfait.
- Niveau d'engagement dans le projet : actif, en réflexion, contraint, volontaire.
- Rapport au temps : urgence, patience, projection court/moyen/long terme.

Contraintes :
- Ne pas psychologiser.
- Basé uniquement sur ce qui est dit ou observable dans les sources.

Format : 6-10 lignes, 2 paragraphes.
""",
        "RESSOURCES_COMPORTEMENTALES_POINTS_APPUI": """
But : identifier les points d'appui comportementaux (forces, stratégies qui fonctionnent).

Attendu :
- Comportements efficaces observés ou rapportés : rigueur, organisation, persévérance, adaptation.
- Stratégies qui aident la personne à réussir (ex : planification, demande d'aide, routines).
- Qualités comportementales concrètes et observables.

Contraintes :
- Basé uniquement sur les sources.
- Pas de psychologie de comptoir.

Format : 4-8 lignes, factuel.
""",
        "RESSOURCES_COMPORTEMENTALES_POINTS_VIGILANCE": """
But : identifier les points de vigilance comportementaux (axes à surveiller).

Attendu :
- Comportements qui peuvent poser problème : impulsivité, évitement, difficulté de concentration, gestion du stress.
- Formuler de manière neutre et constructive ("à renforcer", "nécessite un cadre").
- Ne pas dramatiser ni diagnostiquer.

Contraintes :
- Basé uniquement sur les sources.
- Ton neutre, orienté solution.

Format : 4-8 lignes, factuel.
""",
        "RESSOURCES_INTERPERSONNELLES_PRINCIPALES": """
But : identifier les ressources interpersonnelles (réseau, appuis, relationnel).

Attendu :
- Qualité du réseau : familial, professionnel, associatif, institutionnel.
- Capacité à mobiliser de l'aide et du soutien.
- Points forts relationnels : communication, écoute, coopération.
- Appuis concrets si mentionnés (famille, conseiller, association).

Contraintes :
- Basé uniquement sur les sources.
- Ne pas inventer de réseau.

Format : 4-8 lignes.
""",
        "CONDITIONS_DE_SUCCES": """
But : identifier les conditions nécessaires pour que le projet professionnel réussisse.

Attendu :
- Conditions matérielles : mobilité, garde d'enfants, accès voiture/transports, santé.
- Conditions professionnelles : formation complémentaire, stage, accompagnement.
- Conditions psychologiques : confiance, motivation, soutien.
- Formuler en "pour réussir, il faudrait que..." plutôt qu'en obstacles.

Contraintes :
- Basé uniquement sur les sources.
- Constructif et orienté action.

Format : 4-8 lignes.
""",
        "DISCUSSION_ASSURE": """
But : synthétiser la discussion en 3 sous-parties courtes.

Attendu : 3 sous-parties :
1) Motivations (ce qui tire la personne en avant)
2) Freins (obstacles identifiés dans la discussion)
3) Points d'appui (ressources, atouts mentionnés)

Contraintes :
- Pas de diagnostic inventé.
- Basé uniquement sur ce qui est exprimé.

Format : 3 mini-paragraphes ou 3 puces + 1 phrase chacune.
""",
        "COMPETENCES_SOCIALES": """
But : décrire les compétences sociales observées.

Attendu :
- Compétences sociales observées + 1-2 axes à renforcer.
- Éléments concrets : communication, écoute, coopération, adaptation, posture pro.

Format : 6-10 lignes max.
""",
        "COMPETENCES_PRO": """
But : décrire les compétences professionnelles clés.

Attendu :
- 5-8 compétences clés, regroupées si besoin par familles.
- Savoir-faire techniques, outils, méthodes, qualités opérationnelles.

Format : paragraphe structuré ou 5-8 puces courtes.
""",
        "OBSTACLES": """
But : identifier les obstacles de manière neutre et orientée solution.

Attendu :
- Obstacles neutres (santé, mobilité, langue, disponibilité, lacunes techniques, confiance).
- Formulation orientée solution (ex : "nécessite un aménagement / accompagnement").

Contraintes :
- Ne pas inventer.
- Formulation neutre et professionnelle.

Format : 5-10 lignes max.
""",
        "CONTEXTE_ORGANISATION_PRIVILEGIEE": """
But : décrire le type d'organisation/environnement de travail le plus adapté.

Attendu :
- Taille de structure préférée (PME, grande entreprise, indépendant).
- Ambiance (familiale, structurée, dynamique).
- Cadre (stable/variable), horaires, flexibilité.
- Travail seul/en équipe, relation client/interne.

Contraintes :
- Basé sur les sources. Si incertain : "semble s'orienter vers...".

Format : 4-8 lignes.
""",
        "CONTEXTE_ROLE_PRIVILEGIE": """
But : décrire le rôle professionnel privilégié.

Attendu :
- Type de rôle : exécution, coordination, support, technique, encadrement.
- Niveau d'autonomie souhaité.
- Préférence terrain/bureau/mixte.
- Positionnement hiérarchique si indices dans les sources.

Contraintes :
- Basé sur les sources. Si incertain : proposer 1-2 options.

Format : 4-8 lignes.
""",
        "ACTIVITES": """
But : décrire les activités professionnelles exercées ou en cours.

Attendu :
- Activités principales du parcours professionnel.
- Types de tâches récurrentes.
- Domaines d'intervention.

Contraintes :
- Basé sur les sources (CV, entretiens, fiches de poste).
- Ne pas inventer d'activités.

Format : 5-10 lignes.
""",
        "ACTIVITES_PRIVILEGIEES": """
But : identifier les activités préférées ou vers lesquelles la personne souhaite s'orienter.

Attendu :
- Activités que la personne aime ou recherche.
- Ce qui lui donne de l'énergie au travail.
- Cohérence avec le profil et les compétences.

Contraintes :
- Basé sur les sources (discussion, tests, questionnaires).

Format : 4-8 lignes.
""",
        "ORIENTATION": """
But : proposer des pistes cohérentes et crédibles.

Attendu :
- 2-4 pistes cohérentes, chacune justifiée.
- Mention formation/validation si nécessaire.
- Cohérence avec contraintes, compétences, projet, niveau.

Format : 2-4 puces, 2 phrases par puce max.
""",
        "VOCATIO": """
But : restituer le profil Vocatio (test d'orientation) si présent dans les sources.

Attendu :
- Profil Vocatio tel qu'il apparaît dans le rapport de test.
- Description des intérêts professionnels identifiés.
- Si absent des sources : "Non renseigné".

Contraintes :
- Extraction fidèle du PDF de test.
- Ne pas inventer de profil.

Format : 4-8 lignes.
""",
        "DOMAINES_PROFESSIONNELS_EXEMPLES": """
But : lister les domaines professionnels identifiés (issus du test ou de l'analyse).

Attendu :
- Domaines professionnels avec exemples concrets.
- Issus du test RIASEC/Vocatio ou de l'analyse du conseiller.
- Si absent : "Non renseigné".

Format : 4-8 lignes ou liste courte.
""",
        "RIASEC_CORRESPONDANCE_SCORE": """
But : restituer le score RIASEC (Holland) si présent dans les sources.

Attendu :
- Code RIASEC (ex : RIA, SEC, AIS) et scores associés.
- Correspondance avec les domaines professionnels.
- Extraction fidèle du PDF de test.
- Si absent : "Non renseigné".

Contraintes :
- Ne pas inventer de score.
- Restituer tel quel.

Format : 3-6 lignes.
""",
        "ROLES_PROFESSIONNELS": """
But : identifier les rôles professionnels correspondant au profil.

Attendu :
- Rôles identifiés via tests ou analyse (ex : coordinateur, technicien, formateur).
- Cohérence avec le profil RIASEC si disponible.
- Si issu d'un test : le préciser.

Format : 4-8 lignes ou liste courte.
""",
        "PROFESSIONS": """
But : lister les professions identifiées comme pertinentes pour le profil.

Attendu :
- Professions concrètes issues des tests, de l'analyse ou de la discussion.
- Cohérence avec compétences, intérêts et contraintes.
- Si issu d'un test : restituer fidèlement.

Format : 4-8 lignes ou liste courte.
""",
        "STAGE": """
But : synthétiser le stage si présent.

Attendu :
- Objectifs, activités, résultats/retours, points forts, axes d'amélioration, auto-évaluation si présente.
- Si absent : "Non renseigné".

Format : 8-12 lignes ou 2 paragraphes.
""",
        "LETTRE_DE_MOTIVATION": """
But : synthétiser la lettre de motivation si elle existe (require_sources=True).

Attendu :
- Synthèse fidèle (poste visé, arguments, motivation, dispo).
- Si aucune source : "Non renseigné".

Contraintes :
- Interdit d'inventer.

Format : 6-10 lignes max.
""",
        "CV": """
But : synthétiser le CV si il existe (require_sources=True).

Attendu :
- Synthèse structurée (expériences, formations, compétences).
- Si aucune source : "Non renseigné".

Contraintes :
- Interdit d'inventer.

Format : 10-15 lignes max.
""",
        "CONCLUSION": """
But : conclure et donner les prochaines étapes concrètes.

Attendu : 3 parties courtes :
1) Synthèse profil (forces + contexte)
2) État du projet
3) 3-5 prochaines étapes concrètes

Contraintes :
- Ne pas ajouter de nouvelles infos non présentes.

Format : 3 mini-paragraphes.
""",
    }

    return instructions.get(field_key, f"""
Rédige une synthèse professionnelle pour {field_key}.

RÈGLES STRICTES:
- Texte professionnel, phrases complètes
- Max 3000 caractères
- Interdit d'inventer des faits
- Si une info n'est pas dans les sources, écrire "Non renseigné"
- PAS de points de suspension "..."
- PAS de listes à puces longues (utiliser des phrases)

ÉCRIS TOUT LE CONTENU en français professionnel.
""")


def _build_list_instructions(field_key: str) -> str:
    """Instructions détaillées pour champs listes"""

    instructions = {
        "RESSOURCES_MOTIVATIONNELLES_PRINCIPAUX": """
But : identifier 3-6 ressources motivationnelles principales.

Attendu :
- Types : intérêts, motivations, valeurs, leviers d'engagement.
- Formulation courte par item (5-10 mots).

Exemples :
- "Sécurité de l'emploi et stabilité financière"
- "Besoin d'autonomie et de créativité"
- "Transmission de compétences et utilité sociale"

Contraintes :
- Basé uniquement sur sources.
- Pas de généralités ou répétitions.

Format : liste de 3-6 puces courtes.
""",
        "RELATION_AU_MARCHE_DE_LEMPLOI": """
But : identifier 3-6 représentations ou postures face au marché.

Attendu :
- Attitude face à la recherche : passive, active, découragée, réaliste, stratégique, optimiste, etc.
- Perceptions (ex : "sentiment de saturation du marché").

Exemples :
- "Posture proactive avec candidatures ciblées"
- "Inquiétude face à l'âge et discrimination perçue"
- "Recherche large dans plusieurs secteurs"

Contraintes :
- Basé uniquement sur sources.
- Formulation neutre et professionnelle.

Format : liste de 3-6 puces courtes.
""",
        "STRATEGIES_COMPORTEMENTALES": """
But : identifier 3-6 stratégies comportementales d'adaptation.

Attendu :
- Manières de faire face (résilience, évitement, anticipation, organisation, délégation, demande d'aide).
- Exemples concrets si possibles.

Exemples :
- "Organisation méthodique avec listes et plannings"
- "Recherche d'aide auprès de pairs ou de structures"
- "Évitement des contextes anxiogènes"

Contraintes :
- Basé uniquement sur sources.
- Formulation neutre.

Format : liste de 3-6 puces courtes.
""",
        "SECTEURS_PRIVILEGIES": """
But : identifier 3-6 secteurs d'activité privilégiés (domaines/industries).

Attendu :
- Secteurs d'activité (pas métiers) : santé, social, industrie, logistique, éducation, commerce, etc.
- Justification implicite si mentionnée dans les sources.

Exemples :
- "Santé et action sociale"
- "Industrie manufacturière et production"
- "Services administratifs et gestion"

Contraintes :
- Basé uniquement sur sources.
- Ne pas confondre secteur et métier.

Format : liste de 3-6 puces courtes.
""",
        "FONCTIONS_PRIVILEGIEES": """
But : identifier 3-6 types de fonctions privilégiées.

Attendu :
- Fonctions (pas métiers précis) : administration, support technique, coordination, vente, production.
- Cohérence avec le profil et les compétences.

Exemples :
- "Fonctions administratives et de gestion"
- "Support technique et maintenance"
- "Coordination d'équipe ou de projet"

Contraintes :
- Basé uniquement sur sources.

Format : liste de 3-6 puces courtes.
""",
        "METIERS_PRIVILEGIES_ENVISAGEABLES": """
But : identifier 3-6 métiers privilégiés ou envisageables.

Attendu :
- Métiers précis (pas secteurs) avec justification si possible.
- Cohérence avec compétences, projet, contraintes.

Exemples :
- "Agent administratif (expérience + compétences bureautiques)"
- "Aide-soignant (intérêt + formation en cours)"
- "Conducteur de ligne (expérience industrielle)"

Contraintes :
- Basé uniquement sur sources.
- Ne pas inventer de métier non mentionné.

Format : liste de 3-6 puces courtes avec justification implicite.
""",
        "FORMATIONS_SUPERIEURES": """
But : identifier formations supérieures envisagées ou pertinentes.

Attendu :
- Formations post-obligatoires (brevets fédéraux, diplômes ES, certifications longues).
- Si rien de ce type : retourner liste vide [].

Contraintes :
- Ne pas confondre avec formations hautes écoles (HES/UNI).
- Si absent : [] (liste vide).

Format : liste de 1-4 puces courtes si présent, sinon [].
""",
        "FORMATIONS_HAUTES_ECOLES": """
But : identifier formations hautes écoles envisagées ou souhaitées.

Attendu :
- Formations HES, université, CAS/DAS, bachelor, passerelles.
- Si rien de ce type : retourner liste vide [].

Contraintes :
- Ne pas confondre avec formations supérieures (brevets, ES).
- Si absent : [] (liste vide).

Format : liste de 1-3 puces courtes si présent, sinon [].
""",
    }

    return instructions.get(field_key, f"""
Génère une liste de 3 à 6 éléments pour {field_key}.

RÈGLES STRICTES:
- Retourner uniquement des ITEMS COURTS (une ligne chacun)
- 3 à 6 items maximum
- Format JSON: ["item 1", "item 2", "item 3"]
- Basé UNIQUEMENT sur ce qui est écrit dans les sources
- Si aucune info : retourner []
- PAS d'invention
- PAS de listes vides avec texte explicatif

RETOURNE UNIQUEMENT UN TABLEAU JSON VALIDE.
""")


def _build_enum_instructions(field_key: str, enum_values: List[str]) -> str:
    """Instructions pour champs enum (extraction stricte)"""
    values_str = ", ".join(enum_values)

    if "FRANCAIS" in field_key or "ANGLAIS" in field_key or "ALLEMAND" in field_key:
        instruction_type = "niveau linguistique"
    elif any(tool in field_key for tool in ["WORD", "EXCEL", "POWERPOINT", "OUTLOOK"]):
        instruction_type = "niveau bureautique"
    else:
        instruction_type = "valeur"

    return f"""
Extrais le {instruction_type} pour {field_key}.

VALEURS AUTORISÉES (exactes uniquement):
{values_str}

RÈGLE CRITIQUE:
- Retourner UNE SEULE valeur parmi la liste ci-dessus
- Choix uniquement si EXPLICITEMENT présent dans un test/évaluation/source
- Ne JAMAIS déduire à partir du fait que la personne "parle bien" ou "utilise l'outil"
- Si aucune preuve explicite dans les sources → "{enum_values[-1]}"
- NE JAMAIS inventer, déduire ou retourner une autre valeur
- Pas de texte libre, pas de paragraphes

Réponds UNIQUEMENT avec la valeur exacte (ex: "B2" ou "Non évalué").
"""


def _build_test_narrative_instructions(field_key: str) -> str:
    """Instructions pour champs test_narrative (résultats de tests psychométriques)"""

    test_names = {
        "TRI_ET_CLASSEMENT": "tri et classement",
        "TEST_ATTENTION_ADMINISTRATIF": "attention administrative",
        "CALCUL_NIVEAU": "calcul",
        "DIMENSIONS_VOLUMES_ET_MESURES": "dimensions, volumes et mesures",
        "TEST_NIVEAU_COMPTABILITE": "comptabilité",
        "TEST_COMPREHENSION_CONSIGNES": "compréhension de consignes",
        "TEST_SAISIE_COMMANDES": "saisie de commandes",
    }

    test_name = test_names.get(field_key, field_key.replace("_", " ").lower())

    return f"""
But : restituer le résultat du test de {test_name}.

Attendu :
- Score ou résultat tel qu'il apparaît dans le document de test.
- Interprétation brève si présente dans les sources (1-2 phrases).
- Mentionner le type de test et le contexte si disponible.

Contraintes :
- Extraction FIDÈLE du PDF de test. Ne pas inventer de score.
- Si aucun résultat trouvé dans les sources : "Non renseigné".
- Ne pas interpréter au-delà de ce qui est écrit.

Format : 2-5 lignes maximum (score + interprétation courte).
"""


# ============================================================================
# ENREGISTREMENT DES CHAMPS
# ============================================================================

def _register_specs_v2() -> dict[str, FieldSpecV2]:
    """Enregistre tous les champs V2 - Schéma complet aligné sur le template"""
    specs: dict[str, FieldSpecV2] = {}

    # ========================================================================
    # A) INFORMATIONS PERSONNELLES (4 déterministes + 1 AVS)
    # ========================================================================
    deterministic = {
        "MONSIEUR_OU_MADAME": ("civility", "Civilité du client"),
        "NAME": ("name", "Prénom du client"),
        "SURNAME": ("surname", "Nom du client"),
        "LIEU_ET_DATE": ("location_date", "Lieu et date du rapport"),
    }

    for key, (source, query) in deterministic.items():
        specs[key] = FieldSpecV2(
            key=key,
            field_type="deterministic",
            query=query,
            instructions=f"Valeur déterministe depuis {source}",
            max_chars=100,
            max_lines=1,
            extraction_policy="deterministic",
            remove_if_empty=False,
        )

    # AVS: déterministe mais avec extraction regex
    specs["NUMERO_AVS"] = FieldSpecV2(
        key="NUMERO_AVS",
        field_type="deterministic",
        query="Numéro AVS",
        instructions="Valeur déterministe depuis avs",
        max_chars=50,
        max_lines=1,
        extraction_policy="deterministic",
        remove_if_empty=False,
    )

    # ========================================================================
    # B) PROFIL (4 narratifs)
    # ========================================================================
    profile_fields = [
        ("PROFESSION", "Situation professionnelle actuelle"),
        ("FORMATION", "Formations, diplômes, certifications"),
        ("PRESENTATION", "Présentation générale de la personne"),
        ("RELATION_A_LA_CARRIERE", "Relation à la carrière et au projet professionnel"),
    ]

    for key, query in profile_fields:
        specs[key] = FieldSpecV2(
            key=key,
            field_type="narrative",
            query=query,
            instructions=_build_narrative_instructions(key),
            max_chars=3000,
            max_lines=15,
            extraction_policy="llm_with_guardrails",
        )

    # ========================================================================
    # C) RESSOURCES (3 narratifs + 2 listes)
    # ========================================================================
    resource_narratives = [
        ("RESSOURCES_COMPORTEMENTALES_POINTS_APPUI", "Points d'appui comportementaux"),
        ("RESSOURCES_COMPORTEMENTALES_POINTS_VIGILANCE", "Points de vigilance comportementaux"),
        ("RESSOURCES_INTERPERSONNELLES_PRINCIPALES", "Ressources interpersonnelles principales"),
    ]

    for key, query in resource_narratives:
        specs[key] = FieldSpecV2(
            key=key,
            field_type="narrative",
            query=query,
            instructions=_build_narrative_instructions(key),
            max_chars=2000,
            max_lines=10,
            extraction_policy="llm_with_guardrails",
        )

    # Ressources motivationnelles (liste)
    specs["RESSOURCES_MOTIVATIONNELLES_PRINCIPAUX"] = FieldSpecV2(
        key="RESSOURCES_MOTIVATIONNELLES_PRINCIPAUX",
        field_type="list",
        query="Ressources motivationnelles principales",
        instructions=_build_list_instructions("RESSOURCES_MOTIVATIONNELLES_PRINCIPAUX"),
        max_chars=2000,
        max_lines=10,
        extraction_policy="llm_with_guardrails",
    )

    # Conditions de succès (narratif)
    specs["CONDITIONS_DE_SUCCES"] = FieldSpecV2(
        key="CONDITIONS_DE_SUCCES",
        field_type="narrative",
        query="Conditions de succès pour le projet professionnel",
        instructions=_build_narrative_instructions("CONDITIONS_DE_SUCCES"),
        max_chars=2000,
        max_lines=10,
        extraction_policy="llm_with_guardrails",
    )

    # ========================================================================
    # D) MARCHÉ & COMPORTEMENT (6 champs)
    # ========================================================================
    specs["RELATION_AU_MARCHE_DE_LEMPLOI"] = FieldSpecV2(
        key="RELATION_AU_MARCHE_DE_LEMPLOI",
        field_type="list",
        query="Relation au marché de l'emploi",
        instructions=_build_list_instructions("RELATION_AU_MARCHE_DE_LEMPLOI"),
        max_chars=2000,
        max_lines=10,
        extraction_policy="llm_with_guardrails",
    )

    specs["STRATEGIES_COMPORTEMENTALES"] = FieldSpecV2(
        key="STRATEGIES_COMPORTEMENTALES",
        field_type="list",
        query="Stratégies comportementales",
        instructions=_build_list_instructions("STRATEGIES_COMPORTEMENTALES"),
        max_chars=2000,
        max_lines=10,
        extraction_policy="llm_with_guardrails",
    )

    discussion_fields = [
        ("DISCUSSION_ASSURE", "Motivations, freins, points d'appui"),
        ("COMPETENCES_SOCIALES", "Compétences sociales observées"),
        ("COMPETENCES_PRO", "Compétences professionnelles clés"),
        ("OBSTACLES", "Obstacles identifiés dans le parcours"),
    ]

    for key, query in discussion_fields:
        specs[key] = FieldSpecV2(
            key=key,
            field_type="narrative",
            query=query,
            instructions=_build_narrative_instructions(key),
            max_chars=3000,
            max_lines=15,
            extraction_policy="llm_with_guardrails",
        )

    # ========================================================================
    # E) ORIENTATION & MÉTIERS (8 champs)
    # ========================================================================
    orientation_narratives = [
        ("CONTEXTE_ORGANISATION_PRIVILEGIEE", "Organisation et environnement de travail privilégié"),
        ("CONTEXTE_ROLE_PRIVILEGIE", "Rôle professionnel privilégié"),
        ("ACTIVITES", "Activités professionnelles exercées"),
        ("ACTIVITES_PRIVILEGIEES", "Activités privilégiées"),
        ("ORIENTATION", "Orientations ou pistes métiers"),
    ]

    for key, query in orientation_narratives:
        specs[key] = FieldSpecV2(
            key=key,
            field_type="narrative",
            query=query,
            instructions=_build_narrative_instructions(key),
            max_chars=3000,
            max_lines=15,
            extraction_policy="llm_with_guardrails",
        )

    orientation_lists = [
        ("SECTEURS_PRIVILEGIES", "Secteurs privilégiés"),
        ("FONCTIONS_PRIVILEGIEES", "Fonctions privilégiées"),
        ("METIERS_PRIVILEGIES_ENVISAGEABLES", "Métiers privilégiés qui pourraient être envisagés"),
    ]

    for key, query in orientation_lists:
        specs[key] = FieldSpecV2(
            key=key,
            field_type="list",
            query=query,
            instructions=_build_list_instructions(key),
            max_chars=2000,
            max_lines=10,
            extraction_policy="llm_with_guardrails",
        )

    # ========================================================================
    # F) RIASEC / VOCATIO (5 champs - extraction PDF + fallback LLM)
    # ========================================================================
    riasec_fields = [
        ("VOCATIO", "Profil Vocatio (test d'orientation)"),
        ("DOMAINES_PROFESSIONNELS_EXEMPLES", "Domaines professionnels avec exemples"),
        ("RIASEC_CORRESPONDANCE_SCORE", "Score RIASEC et correspondances"),
        ("ROLES_PROFESSIONNELS", "Rôles professionnels identifiés"),
        ("PROFESSIONS", "Professions identifiées pour le profil"),
    ]

    for key, query in riasec_fields:
        specs[key] = FieldSpecV2(
            key=key,
            field_type="narrative",
            query=query,
            instructions=_build_narrative_instructions(key),
            max_chars=2000,
            max_lines=10,
            extraction_policy="llm_with_guardrails",
        )

    # ========================================================================
    # G) NIVEAUX LANGUES (3 enum CECRL)
    # ========================================================================
    language_fields = [
        ("FRANCAIS_POSITIONNEMENT_DE_NIVEAU", "Français positionnement de niveau"),
        ("ALLEMAND_POSITIONNEMENT_DE_NIVEAU", "Allemand positionnement de niveau"),
        ("ANGLAIS_POSITIONNEMENT_DE_NIVEAU", "Anglais positionnement de niveau"),
    ]

    for key, query in language_fields:
        specs[key] = FieldSpecV2(
            key=key,
            field_type="enum",
            query=query,
            instructions=_build_enum_instructions(key, CECRL_LEVELS),
            max_chars=20,
            max_lines=1,
            enum_values=CECRL_LEVELS,
            extraction_policy="extract_only",
        )

    # ========================================================================
    # H) NIVEAUX BUREAUTIQUE (4 enum séparés)
    # ========================================================================
    bureautique_fields = [
        ("WORD_POSITIONNEMENT_DE_NIVEAU", "Word positionnement de niveau"),
        ("EXCEL_POSITIONNEMENT_DE_NIVEAU", "Excel positionnement de niveau"),
        ("POWERPOINT_POSITIONNEMENT_DE_NIVEAU", "PowerPoint positionnement de niveau"),
        ("OUTLOOK_POSITIONNEMENT_DE_NIVEAU", "Outlook positionnement de niveau"),
    ]

    for key, query in bureautique_fields:
        specs[key] = FieldSpecV2(
            key=key,
            field_type="enum",
            query=query,
            instructions=_build_enum_instructions(key, BUREAUTIQUE_LEVELS),
            max_chars=20,
            max_lines=1,
            enum_values=BUREAUTIQUE_LEVELS,
            extraction_policy="extract_only",
        )

    # ========================================================================
    # I) TESTS PSYCHOMÉTRIQUES (7 narratifs courts)
    # ========================================================================
    test_fields = [
        ("TRI_ET_CLASSEMENT", "Test de tri et classement"),
        ("TEST_ATTENTION_ADMINISTRATIF", "Test d'attention administratif"),
        ("CALCUL_NIVEAU", "Test de calcul niveau"),
        ("DIMENSIONS_VOLUMES_ET_MESURES", "Test dimensions volumes et mesures"),
        ("TEST_NIVEAU_COMPTABILITE", "Test de niveau en comptabilité"),
        ("TEST_COMPREHENSION_CONSIGNES", "Test de compréhension de consignes"),
        ("TEST_SAISIE_COMMANDES", "Test de saisie de commandes"),
    ]

    for key, query in test_fields:
        specs[key] = FieldSpecV2(
            key=key,
            field_type="test_narrative",
            query=query,
            instructions=_build_test_narrative_instructions(key),
            max_chars=1000,
            max_lines=5,
            extraction_policy="llm_with_guardrails",
        )

    # ========================================================================
    # J) FORMATIONS SUPÉRIEURES (2 listes)
    # ========================================================================
    formation_lists = [
        ("FORMATIONS_SUPERIEURES", "Formations supérieures envisagées"),
        ("FORMATIONS_HAUTES_ECOLES", "Formations hautes écoles"),
    ]

    for key, query in formation_lists:
        specs[key] = FieldSpecV2(
            key=key,
            field_type="list",
            query=query,
            instructions=_build_list_instructions(key),
            max_chars=2000,
            max_lines=10,
            extraction_policy="llm_with_guardrails",
        )

    # ========================================================================
    # K) FINAL (5 narratifs)
    # ========================================================================
    final_fields = [
        ("STAGE", "Stage (objectifs, résultats, auto-évaluation)"),
        ("LETTRE_DE_MOTIVATION", "Synthèse lettre motivation"),
        ("CV", "Synthèse CV"),
        ("CONCLUSION", "Conclusion globale et prochaines étapes"),
    ]

    for key, query in final_fields:
        require_sources = key in ["LETTRE_DE_MOTIVATION", "CV"]
        specs[key] = FieldSpecV2(
            key=key,
            field_type="narrative",
            query=query,
            instructions=_build_narrative_instructions(key),
            max_chars=3000,
            max_lines=15,
            require_sources=require_sources,
            skip_llm_if_no_sources=require_sources,
            extraction_policy="llm_with_guardrails",
        )

    return specs


# Registre global
FIELD_SPECS_V2 = _register_specs_v2()

# ============================================================================
# Mapping de compatibilité: ancien nom → nouveau nom
# ============================================================================
FIELD_KEY_ALIASES = {
    # Ancien champ fusionné → éclater en 2
    "CONTEXTE_ORGANISATION_ET_ROLE_PRIVILEGIE": "CONTEXTE_ORGANISATION_PRIVILEGIEE",
    # Ancien RESSOURCES_MOTIVATIONNELLES → nouveau nom
    "RESSOURCES_MOTIVATIONNELLES": "RESSOURCES_MOTIVATIONNELLES_PRINCIPAUX",
    # Ancien WORD_EXCEL_POWERPOINT_OUTLOOK fusionné → Word par défaut
    "WORD_EXCEL_POWERPOINT_OUTLOOK_POSITIONNEMENT_DE_NIVEAU": "WORD_POSITIONNEMENT_DE_NIVEAU",
}


def get_field_spec_v2(key: str) -> FieldSpecV2:
    """Récupère une spec V2 par clé, avec résolution d'alias"""
    if key in FIELD_SPECS_V2:
        return FIELD_SPECS_V2[key]

    # Résolution d'alias (compatibilité)
    resolved = FIELD_KEY_ALIASES.get(key)
    if resolved and resolved in FIELD_SPECS_V2:
        return FIELD_SPECS_V2[resolved]

    # Fallback: créer une spec générique
    return FieldSpecV2(
        key=key,
        field_type="narrative",
        query=f"Champ {key}",
        instructions=_build_narrative_instructions(key),
        max_chars=2000,
        max_lines=10,
        extraction_policy="llm_with_guardrails",
    )


def list_fields_by_type(field_type: str) -> List[str]:
    """Liste les champs d'un type donné"""
    return [
        key for key, spec in FIELD_SPECS_V2.items()
        if spec.field_type == field_type
    ]


def get_all_enum_values() -> dict[str, List[str]]:
    """Retourne toutes les valeurs enum par champ"""
    return {
        key: spec.enum_values
        for key, spec in FIELD_SPECS_V2.items()
        if spec.enum_values is not None
    }


def get_all_field_keys() -> List[str]:
    """Retourne toutes les clés de champs dans l'ordre d'enregistrement"""
    return list(FIELD_SPECS_V2.keys())


# Stats pour reporting
def get_schema_stats() -> dict:
    """Statistiques du schéma V2"""
    by_type = {}
    for spec in FIELD_SPECS_V2.values():
        by_type[spec.field_type] = by_type.get(spec.field_type, 0) + 1

    return {
        "total_fields": len(FIELD_SPECS_V2),
        "by_type": by_type,
        "deterministic": list_fields_by_type("deterministic"),
        "narrative": list_fields_by_type("narrative"),
        "list": list_fields_by_type("list"),
        "enum": list_fields_by_type("enum"),
        "test_narrative": list_fields_by_type("test_narrative"),
    }


if __name__ == "__main__":
    import json
    stats = get_schema_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
