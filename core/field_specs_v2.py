"""
Field Specifications V2 - Schéma simplifié avec anti-hallucination

OBJECTIF: 
- Schéma simplifié à ~27 champs essentiels
- Typologie stricte: deterministic | narrative | list | enum
- Anti-hallucination: extraction prioritaire, fallback "Non évalué"
- Prompt wrapper unique et versionné avec marqueur sentinel

STRUCTURE:
A) INFORMATIONS PERSONNELLES (5 déterministes)
B) SECTIONS NARRATIVES/LISTES (19 champs: 12 narratifs + 7 listes)
C) NIVEAUX LINGUISTIQUES ET BUREAUTIQUE (3 enum)

PROMPT SYSTEM:
- Marqueur sentinel: [[FIELD_SPECS_V2_PROMPT_V1]]
- Règles anti-hallucination strictes
- Format validation par type de champ
"""

from dataclasses import dataclass
from typing import Optional, List, Dict

# Marqueur sentinel obligatoire pour validation runtime
PROMPT_SENTINEL = "[[FIELD_SPECS_V2_PROMPT_V1]]"
PROMPT_VERSION = "V1"

# Valeurs enum autorisées
CECRL_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2", "Non évalué"]
BUREAUTIQUE_LEVELS = ["Faible", "Moyen", "Bon", "Très bon", "Non évalué"]


@dataclass(frozen=True)
class FieldSpecV2:
    """Spécification d'un champ V2"""
    key: str
    field_type: str  # deterministic | narrative | list | enum
    query: str
    instructions: str
    max_chars: int
    max_lines: int
    require_sources: bool = False
    skip_llm_if_no_sources: bool = False
    enum_values: Optional[List[str]] = None
    extraction_policy: str = "llm_with_guardrails"  # deterministic | extract_only | llm_with_guardrails


def build_system_prompt() -> str:
    """
    Construit le SYSTEM PROMPT global (règles non négociables).
    Conforme à prompt.md section 3.
    """
    return f"""Tu es un assistant de rédaction de rapports d'orientation professionnelle.
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
    Conforme à prompt.md section 4.
    
    Args:
        field_spec: Spécification du champ
        sources: Contenu RAG extrait (texte brut)
        sources_count: Nombre de sources utilisées
    
    Returns:
        Prompt USER formaté avec délimiteurs
    """
    enum_values_str = ", ".join(field_spec.enum_values) if field_spec.enum_values else ""
    
    # En-tête FieldSpec (section 4.1)
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
    
    # Bloc SOURCES délimité (section 4.2)
    sources_block = f"""
<SOURCES>
{sources if sources else "(Aucune source disponible)"}
</SOURCES>
"""
    
    # Règles de réponse par type (sections 4.3 et 5)
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
    Conforme à prompt.md section 2.1 (fail fast).
    
    Args:
        prompt: Prompt à valider
    
    Returns:
        True si le sentinel est présent, False sinon
    
    Raises:
        ValueError: Si le sentinel est absent (fail fast)
    """
    if PROMPT_SENTINEL not in prompt:
        raise ValueError(
            f"ERREUR CRITIQUE: Le prompt ne contient pas le marqueur sentinel '{PROMPT_SENTINEL}'. "
            "Le prompt ne peut pas être envoyé au LLM sans ce marqueur de validation."
        )
    return True


def _build_narrative_instructions(field_key: str) -> str:
    """Instructions détaillées pour champs narratifs selon spécifications"""
    
    instructions = {
        "PROFESSION": """
But : donner une photo claire et factuelle de la situation pro actuelle (ou la dernière connue).

Attendu :
- Statut : en poste / en recherche / en arrêt / en transition.
- Poste actuel (ou dernier poste), secteur, type de contrat si connu, rythme (temps plein/partiel).
- Missions principales (3–6 points implicites dans un texte fluide), responsabilités, niveau d'autonomie.
- Environnement : équipe, terrain/bureau, contraintes physiques/horaires si mentionnées.

Contraintes :
- Ne jamais inventer employeur, dates, intitulés précis si absents.
- Si info manquante : l'indiquer ("non renseigné") plutôt que combler.

Format conseillé : 6–10 lignes, pro, sans liste longue.
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

Format conseillé : 6–12 lignes, lisible, éventuellement 2 mini-paragraphes.
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

Format conseillé : 6–10 lignes, 2 paragraphes.
""",
        "DISCUSSION_ASSURE": """
But : synthétiser la discussion en 3 sous-parties courtes.

Attendu : 3 sous-parties courtes : 
1) Motivations (ce qui tire la personne)
2) Freins (obstacles identifiés)
3) Points d'appui (ressources, atouts)

Contraintes : 
- Pas de diagnostic inventé.
- Basé uniquement sur ce qui est exprimé.

Format : 3 mini-paragraphes ou 3 puces + 1 phrase chacune.
""",
        "COMPETENCES_SOCIALES": """
But : décrire les compétences sociales observées.

Attendu : 
- Compétences sociales observées + 1–2 axes à renforcer.
- Éléments concrets : communication, écoute, coopération, adaptation, posture pro.

Format : 6–10 lignes max.
""",
        "COMPETENCES_PRO": """
But : décrire les compétences professionnelles clés.

Attendu : 
- 5–8 compétences clés, regroupées si besoin par familles.
- Savoir-faire techniques, outils, méthodes, qualités opérationnelles.

Format : paragraphe structuré ou 5–8 puces courtes.
""",
        "OBSTACLES": """
But : identifier les obstacles de manière neutre et orientée solution.

Attendu : 
- Obstacles neutres (santé, mobilité, langue, disponibilité, lacunes techniques, confiance).
- Formulation orientée solution (ex : "nécessite un aménagement / accompagnement").

Contraintes :
- Ne pas inventer.
- Formulation neutre et professionnelle.

Format : 5–10 lignes max.
""",
        "ORIENTATION": """
But : proposer des pistes cohérentes et crédibles.

Attendu : 
- 2–4 pistes cohérentes, chacune justifiée.
- Mention formation/validation si nécessaire.
- Cohérence avec contraintes, compétences, projet, niveau.

Format : 2–4 puces, 2 phrases par puce max.
""",
        "STAGE": """
But : synthétiser le stage si présent.

Attendu : 
- Objectifs, activités, résultats/retours, points forts, axes d'amélioration, auto-évaluation si présente.
- Si absent : "Non renseigné".

Format : 8–12 lignes ou 2 paragraphes.
""",
        "LETTRE_DE_MOTIVATION": """
But : synthétiser la lettre de motivation si elle existe (require_sources=True).

Attendu : 
- Synthèse fidèle (poste visé, arguments, motivation, dispo).
- Si aucune source : "Non renseigné".

Contraintes :
- Interdit d'inventer.

Format : 6–10 lignes max.
""",
        "CV": """
But : synthétiser le CV si il existe (require_sources=True).

Attendu : 
- Synthèse structurée (expériences, formations, compétences).
- Si aucune source : "Non renseigné".

Contraintes :
- Interdit d'inventer.

Format : 10–15 lignes max.
""",
        "CONCLUSION": """
But : conclure et donner les prochaines étapes concrètes.

Attendu : 3 parties courtes :
1) Synthèse profil (forces + contexte)
2) État du projet
3) 3–5 prochaines étapes concrètes

Contraintes :
- Ne pas ajouter de nouvelles infos non présentes.

Format : 3 mini-paragraphes.
"""
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
        "RESSOURCES_MOTIVATIONNELLES": """
But : identifier 3–6 ressources motivationnelles principales.

Attendu : 
- Types : intérêts, motivations, valeurs, leviers d'engagement.
- Formulation courte par item (5–10 mots).

Exemples : 
- "Sécurité de l'emploi et stabilité financière"
- "Besoin d'autonomie et de créativité"
- "Transmission de compétences et utilité sociale"

Contraintes :
- Basé uniquement sur sources.
- Pas de généralités ou répétitions.

Format : liste de 3–6 puces courtes.
""",
        "RELATION_AU_MARCHE_DE_LEMPLOI": """
But : identifier 3–6 représentations ou postures face au marché.

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

Format : liste de 3–6 puces courtes.
""",
        "STRATEGIES_COMPORTEMENTALES": """
But : identifier 3–6 stratégies comportementales d'adaptation.

Attendu : 
- Manières de faire face (résilience, évitement, anticipation, organisation, délégation, demande d'aide…).
- Exemples concrets si possibles.

Exemples : 
- "Organisation méthodique avec listes et plannings"
- "Recherche d'aide auprès de pair·es ou de structures"
- "Évitement des contextes anxiogènes"

Contraintes :
- Basé uniquement sur sources.
- Formulation neutre.

Format : liste de 3–6 puces courtes.
""",
        "CONTEXTE_ORGANISATION_ET_ROLE_PRIVILEGIE": """
But : identifier 3–6 environnements ou rôles privilégiés.

Attendu : 
- Type de structure, taille, ambiance, horaires, équipe, positionnement hiérarchique.
- Rôle privilégié : autonome, encadré, terrain, bureau, équipe, solo, etc.

Exemples : 
- "PME avec équipe réduite et ambiance familiale"
- "Rôle opérationnel avec autonomie et responsabilités"
- "Horaires décalés ou flexibles privilégiés"

Contraintes :
- Basé uniquement sur sources.

Format : liste de 3–6 puces courtes.
""",
        "SECTEURS_PRIVILEGIES": """
But : identifier 3–6 secteurs d'activité privilégiés (domaines/industries).

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

Format : liste de 3–6 puces courtes.
""",
        "METIERS_PRIVILEGIES_ENVISAGEABLES": """
But : identifier 3–6 métiers privilégiés ou envisageables.

Attendu : 
- Métiers précis (pas secteurs) avec justification si possible.
- Cohérence avec compétences, projet, contraintes.

Exemples : 
- "Agent·e administratif·ve (expérience + compétences bureautiques)"
- "Aide-soignant·e (intérêt + formation en cours)"
- "Conducteur·trice de ligne (expérience industrielle)"

Contraintes :
- Basé uniquement sur sources.
- Ne pas inventer de métier non mentionné.

Format : liste de 3–6 puces courtes avec justification implicite.
""",
        "FORMATIONS_HAUTES_ECOLES": """
But : identifier formations supérieures envisagées ou souhaitées.

Attendu : 
- Formations post-obligatoires (HES, université, formations longues certifiantes).
- Si rien de ce type : retourner liste vide [].

Contraintes :
- Ne pas confondre avec formations courtes/certifs.
- Si absent : [] (liste vide).

Format : liste de 1–3 puces courtes si présent, sinon [].
"""
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
    """Instructions pour champs enum (extraction stricte, valeurs CECRL)"""
    values_str = ", ".join(enum_values)
    
    if "FRANCAIS" in field_key or "ANGLAIS" in field_key:
        instruction_type = "niveau linguistique"
    elif "WORD_EXCEL_POWERPOINT_OUTLOOK" in field_key:
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


def _register_specs_v2() -> dict[str, FieldSpecV2]:
    """Enregistre tous les champs V2 - Version simplifiée"""
    specs: dict[str, FieldSpecV2] = {}
    
    # ========================================================================
    # A) INFORMATIONS PERSONNELLES (5 déterministes, inchangés)
    # ========================================================================
    deterministic = {
        "MONSIEUR_OU_MADAME": ("civility", "Civilité du client"),
        "NAME": ("name", "Prénom du client"),
        "SURNAME": ("surname", "Nom du client"),
        "LIEU_ET_DATE": ("location_date", "Lieu et date du rapport"),
        "NUMERO_AVS": ("avs", "Numéro AVS"),
    }
    
    for key, (source, query) in deterministic.items():
        specs[key] = FieldSpecV2(
            key=key,
            field_type="deterministic",
            query=query,
            instructions=f"Valeur déterministe depuis {source}",
            max_chars=50 if key == "NUMERO_AVS" else 100,
            max_lines=1,
            require_sources=False,
            extraction_policy="deterministic",
        )
    
    # ========================================================================
    # B) SECTIONS NARRATIVES ET LISTES (16 champs essentiels)
    # ========================================================================
    
    # Narratives (max 3000 chars)
    narrative_fields = [
        ("PROFESSION", "Situation professionnelle actuelle"),
        ("FORMATION", "Formations, diplômes, certifications"),
        ("RELATION_A_LA_CARRIERE", "Relation à la carrière et au projet professionnel"),
        ("DISCUSSION_ASSURE", "Motivations, freins, points d'appui"),
        ("COMPETENCES_SOCIALES", "Compétences sociales observées"),
        ("COMPETENCES_PRO", "Compétences professionnelles clés"),
        ("OBSTACLES", "Obstacles identifiés dans le parcours"),
        ("ORIENTATION", "Orientations ou pistes métiers"),
        ("STAGE", "Stage (objectifs, résultats, auto-évaluation)"),
        ("LETTRE_DE_MOTIVATION", "Synthèse lettre motivation"),
        ("CV", "Synthèse CV"),
        ("CONCLUSION", "Conclusion globale et prochaines étapes"),
    ]
    
    for key, query in narrative_fields:
        # CV et LETTRE_DE_MOTIVATION requièrent sources
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
    
    # Listes (max 2000 chars, 2-4 items)
    list_fields = [
        ("RESSOURCES_MOTIVATIONNELLES", "Ressources motivationnelles"),
        ("RELATION_AU_MARCHE_DE_LEMPLOI", "Relation au marché de l'emploi"),
        ("STRATEGIES_COMPORTEMENTALES", "Stratégies comportementales"),
        ("CONTEXTE_ORGANISATION_ET_ROLE_PRIVILEGIE", "Contexte organisation et rôle privilégié"),
        ("SECTEURS_PRIVILEGIES", "Secteurs privilégiés"),
        ("METIERS_PRIVILEGIES_ENVISAGEABLES", "Métiers privilégiés qui pourraient être envisagés"),
        ("FORMATIONS_HAUTES_ECOLES", "Formations hautes écoles"),
    ]
    
    for key, query in list_fields:
        specs[key] = FieldSpecV2(
            key=key,
            field_type="list",
            query=query,
            instructions=_build_list_instructions(key),
            max_chars=2000,
            max_lines=10,
            require_sources=False,
            skip_llm_if_no_sources=False,
            extraction_policy="llm_with_guardrails",
        )
    
    # ========================================================================
    # C) NIVEAUX LINGUISTIQUES ET BUREAUTIQUE (3 enum - Valeurs contraintes)
    # ========================================================================
    
    # Langues (CECRL)
    language_fields = [
        ("FRANCAIS_POSITIONNEMENT_DE_NIVEAU", "Français positionnement de niveau", CECRL_LEVELS),
        ("ANGLAIS_POSITIONNEMENT_DE_NIVEAU", "Anglais positionnement de niveau", CECRL_LEVELS),
    ]
    
    for key, query, enum_vals in language_fields:
        specs[key] = FieldSpecV2(
            key=key,
            field_type="enum",
            query=query,
            instructions=_build_enum_instructions(key, enum_vals),
            max_chars=20,
            max_lines=1,
            require_sources=False,
            skip_llm_if_no_sources=False,
            enum_values=enum_vals,
            extraction_policy="extract_only",
        )
    
    # Bureautique (Valeurs spécifiques)
    specs["WORD_EXCEL_POWERPOINT_OUTLOOK_POSITIONNEMENT_DE_NIVEAU"] = FieldSpecV2(
        key="WORD_EXCEL_POWERPOINT_OUTLOOK_POSITIONNEMENT_DE_NIVEAU",
        field_type="enum",
        query="WORD EXCEL POWERPOINT OUTLOOK positionnement de niveau",
        instructions=_build_enum_instructions(
            "WORD_EXCEL_POWERPOINT_OUTLOOK_POSITIONNEMENT_DE_NIVEAU", 
            BUREAUTIQUE_LEVELS
        ),
        max_chars=20,
        max_lines=1,
        require_sources=False,
        skip_llm_if_no_sources=False,
        enum_values=BUREAUTIQUE_LEVELS,
        extraction_policy="extract_only",
    )
    
    return specs


# Registre global
FIELD_SPECS_V2 = _register_specs_v2()


def get_field_spec_v2(key: str) -> FieldSpecV2:
    """Récupère une spec V2 par clé"""
    if key in FIELD_SPECS_V2:
        return FIELD_SPECS_V2[key]
    
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
    }


if __name__ == "__main__":
    import json
    stats = get_schema_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
