"""Génération des sections du rapport via Ollama (format texte brut)."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Optional
from urllib import request
from urllib.error import URLError, HTTPError

from .context import build_index
from .errors import Result, GenerationError, OllamaError
from .field_specs import FieldSpec, get_field_spec, normalize_allowed_value
from .logger import get_logger
from .llm_router import LLMConfig, call_llm  # ✅ Nouveau router LLM unifié

# SCHEMA V2: imports conditionnels (lazy loading pour éviter circular imports)
USE_SCHEMA_V2 = True  # ✅ Schema V2 ACTIVÉ avec instructions détaillées

LOG = get_logger("core.generate")

StatusCallback = Optional[Callable[[str], None]]
FieldProgressCallback = Optional[Callable[[str, str, str], None]]

DEFAULT_FIELDS = [
    {"key": "PROFESSION", "query": "Profession actuelle", "instructions": "Synthèse pro"},
    {"key": "FORMATION", "query": "Parcours de formation", "instructions": "Formations"},
]

RE_JSON = re.compile(r"\A\s*[{[]")
RE_CODEBLOCK = re.compile(r"```|\bjson\b", re.IGNORECASE)

# Sorties interdites: placeholders, traces de sources, etc.
RE_FORBIDDEN_PLACEHOLDERS = re.compile(r"\{\{|\}\}")
RE_FORBIDDEN_SOURCE_REF = re.compile(r"\bsource\s*\d+\b|\(\s*source\b", re.IGNORECASE)
RE_FORBIDDEN_TOKENS = re.compile(r"\bXX\b|\bNAME\b|\bsurname\b", re.IGNORECASE)



def ollama_generate(
    model: str,
    prompt: str,
    host: str,
    temperature: float,
    top_p: float,
    timeout: float = 120.0,
    *,
    llm_config: Optional[LLMConfig] = None,
    field_name: Optional[str] = None,
    max_tokens: Optional[int] = None,
) -> Result[str]:
    """Génère une réponse via l'API Ollama.

    LEGACY WRAPPER: Utilise le nouveau router LLM si llm_config fourni,
    sinon utilise les anciens paramètres pour rétrocompatibilité.

    Args:
        model: Nom du modèle Ollama
        prompt: Prompt à envoyer
        host: URL du serveur Ollama
        temperature: Température (0-1)
        top_p: Paramètre top_p (0-1)
        timeout: Timeout en secondes (défaut 120)
        llm_config: Config LLM moderne (prioritaire si fourni)
        field_name: Nom du champ (pour logs)
        max_tokens: Limite de tokens générés (override la config)

    Returns:
        Result[str]: Succès avec la réponse générée ou échec avec OllamaError
    """
    # ✅ Nouveau chemin: utiliser le router LLM unifié
    if llm_config:
        # Appliquer max_tokens si spécifié (override par champ)
        effective_config = llm_config
        if max_tokens and max_tokens != llm_config.max_tokens:
            effective_config = llm_config.model_copy(update={"max_tokens": max_tokens, "timeout": min(llm_config.timeout, 120.0)})
        result = call_llm(effective_config, prompt, field_name=field_name)
        if result.success:
            return Result.ok(result.value.text)
        else:
            return Result.fail(result.error)

    # ⚠️ Ancien chemin (legacy): créer une config à la volée
    legacy_config = LLMConfig.from_legacy(
        model=model,
        host=host,
        temperature=temperature,
        top_p=top_p,
        timeout=min(timeout, 120.0),
        max_tokens=max_tokens or 1024,
    )

    result = call_llm(legacy_config, prompt, field_name=field_name)
    if result.success:
        return Result.ok(result.value.text)
    else:
        return Result.fail(result.error)


def check_llm_status(host: str, model: Optional[str] = None, timeout: float = 3.0) -> Result[str]:
    """Vérifie la disponibilité du serveur Ollama et du modèle.
    
    LEGACY WRAPPER: Utilise check_ollama_health du nouveau router.
    
    Args:
        host: URL du serveur Ollama
        model: Nom du modèle à vérifier (optionnel)
        timeout: Timeout en secondes
        
    Returns:
        Result[str]: Succès avec message de statut ou échec avec OllamaError
    """
    from .llm_router import check_ollama_health
    
    LOG.info("Vérification serveur Ollama: %s", host)
    
    result = check_ollama_health(base_url=host, model=model, timeout=timeout)
    
    if not result.success:
        return result
    
    data = result.value
    version = data.get("version", "unknown")
    message = f"Serveur accessible ({version})"
    
    if model:
        model_available = data.get("model_available")
        if model_available:
            message += f" — modèle '{model}' disponible"
            LOG.info("Modèle '%s' disponible", model)
        else:
            error = OllamaError(message + f" — modèle '{model}' introuvable")
            LOG.warning("Modèle '%s' introuvable", model)
            return Result.fail(error)
    
    return Result.ok(message)


def sanitize_output(text: str) -> str:
    text = text.replace("```", " ")
    text = text.replace("\u200b", " ")
    text = re.sub(r"(?i)^json[:\s]+", "", text.strip())
    
    # Convertir les listes à puces markdown (* item, - item) en bullet propre
    lines = text.split("\n")
    cleaned_lines = []
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("* "):
            stripped = "- " + stripped[2:]
        cleaned_lines.append(stripped)
    text = "\n".join(cleaned_lines)

    # Supprimer les points de suspension "..." que le LLM pourrait ajouter à la fin
    # pour indiquer une troncature (interdits par les instructions mais parfois présents)
    text = text.strip()
    if text.endswith("..."):
        text = text[:-3].rstrip()
    if text.endswith("…"):  # Version Unicode du caractère points de suspension
        text = text[:-1].rstrip()

    # Filet de sécurité: vider tout texte contenant un refus LLM ou une explication méthodologique
    _kill_markers = [
        # Refus
        "je suis désolé",
        "je ne peux pas",
        "je ne suis pas en mesure",
        "il m'est impossible",
        "impossible pour moi de",
        "pas disponible dans les sources",
        "informations personnelles et privées",
        # Explications méthodologiques (interdit: le LLM doit donner les RÉSULTATS, pas expliquer le test)
        "le modèle riasec",
        "le test riasec permet",
        "john holland",
        "cet outil d'orientation",
        "il repose sur six dimensions",
        "les six types de personnalité",
        "six types de personnalités",
        "recherche (r), intervention (i)",
        "recherche (r), intervention",
        "il identifie six types",
        "les seuils définis en pourcentage",
        "est évalué à l'aide d'un test qui consiste",
        "le positionnement de niveau est évalué",
        "ce test mesure",
        "l'évaluation repose sur",
        "les seuils sont",
        "le taux de réussite global",
        "ce modèle est souvent utilisé",
        "outil d'orientation professionnel",
        "comprendre les motivations et les préférences",
    ]
    text_lower = text.lower()
    if any(marker in text_lower for marker in _kill_markers):
        return ""

    return text.strip()


def looks_like_json_or_markdown(text: str) -> bool:
    stripped = text.strip()
    return bool(RE_JSON.match(stripped) or RE_CODEBLOCK.search(stripped))


def find_forbidden_output_reasons(text: str) -> list[str]:
    """Retourne la liste des raisons pour lesquelles le texte ne doit pas être accepté."""
    reasons: list[str] = []
    if not text:
        return reasons

    if RE_FORBIDDEN_PLACEHOLDERS.search(text):
        reasons.append("PLACEHOLDER")
    if RE_FORBIDDEN_TOKENS.search(text):
        reasons.append("TOKENS")
    if RE_FORBIDDEN_SOURCE_REF.search(text):
        reasons.append("SOURCE_REF")

    # Détection de refus LLM (excuses, refus de traiter données personnelles)
    refusal_patterns = [
        "je suis désolé",
        "je ne peux pas",
        "je ne suis pas en mesure",
        "informations personnelles et privées",
        "ne correspond pas aux consignes",
        "la réponse est bien __vide__",
        "il n'y a donc rien",
        "passage pertinent n'a pas été trouvé",
        "rien à ajouter ou à résumer",
        "si vous avez besoin d'aide",
        "je serais ravi de vous aider",
        # Détection d'explications méthodologiques (LLM qui fait cours au lieu de restituer)
        "le modèle riasec",
        "le test riasec permet",
        "john holland",
        "cet outil d'orientation",
        "il repose sur six dimensions",
        "les six types de personnalité",
        "les seuils définis en pourcentage",
        "est évalué à l'aide d'un test qui consiste",
        "le positionnement de niveau est évalué",
        "ce test mesure",
        "l'évaluation repose sur",
        "les seuils sont",
        "le taux de réussite global",
    ]
    text_lower = text.lower()
    if any(p in text_lower for p in refusal_patterns):
        reasons.append("LLM_REFUSAL")

    # Ponctuation: interdiction de "::" et au plus un ":" par ligne
    if "::" in text:
        reasons.append("MULTI_COLON")
    else:
        for ln in text.splitlines():
            if ln.count(":") > 1:
                reasons.append("MULTI_COLON")
                break

    return reasons


def truncate_lines(text: str, max_lines: int) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
    return "\n".join(lines)


def truncate_chars(text: str, max_chars: int, smart: bool = True) -> str:
    """
    Tronque le texte à max_chars caractères.
    
    Args:
        text: Texte à tronquer
        max_chars: Limite de caractères (0 = pas de limite)
        smart: Si True, coupe à la fin d'une phrase (. ou ;) plutôt qu'au milieu d'un mot
        
    Returns:
        Texte tronqué SANS "..." ajouté automatiquement
        
    Examples:
        >>> truncate_chars("Hello world. How are you?", 15, smart=False)
        'Hello world. Ho'
        >>> truncate_chars("Hello world. How are you?", 15, smart=True)
        'Hello world.'
    """
    if not max_chars or len(text) <= max_chars:
        return text.rstrip()  # Toujours strip trailing spaces
    
    if not smart:
        # Troncature brutale
        return text[:max_chars].rstrip()
    
    # Troncature intelligente : chercher le dernier . ou ; avant la limite
    truncated = text[:max_chars]
    
    # Chercher le dernier séparateur de phrase
    last_period = truncated.rfind('.')
    last_semicolon = truncated.rfind(';')
    last_separator = max(last_period, last_semicolon)
    
    if last_separator > max_chars * 0.5:  # Au moins 50% de la limite utilisée
        # Couper après le séparateur
        return truncated[:last_separator + 1].rstrip()
    else:
        # Pas de séparateur trouvé ou trop court : chercher le dernier espace
        last_space = truncated.rfind(' ')
        if last_space > max_chars * 0.7:  # Au moins 70% de la limite
            return truncated[:last_space].rstrip()
        else:
            # Dernier recours : troncature brutale
            return truncated.rstrip()


def extract_bullet_points(text: str) -> list[str]:
    """Extrait les bullet points d'un texte.
    
    Args:
        text: Texte contenant des bullet points
        
    Returns:
        Liste des items extraits
        
    Examples:
        >>> extract_bullet_points("- Item 1\n- Item 2")
        ['Item 1', 'Item 2']
    """
    # Regex: chercher lignes commençant par - ou • ou *
    items = re.findall(r'^\s*[-•*]\s+(.+)$', text, re.MULTILINE)
    return [item.strip() for item in items if item.strip()]


def validate_list_v2(text: str, max_items: int = 4, max_chars: int = 2000) -> str:
    """Valide et tronque une liste selon les règles V2.
    
    Args:
        text: Texte contenant une liste
        max_items: Nombre max d'items (défaut 4)
        max_chars: Limite de caractères (défaut 2000)
        
    Returns:
        Liste validée et tronquée
        
    Examples:
        >>> validate_list_v2("- A\n- B\n- C\n- D\n- E", max_items=4)
        '- A\n- B\n- C\n- D'
    """
    # 1. Tronquer caractères d'abord
    if len(text) > max_chars:
        text = truncate_chars(text, max_chars, smart=True)
    
    # 2. Extraire items
    items = extract_bullet_points(text)
    
    # 3. Tronquer items si nécessaire
    if len(items) > max_items:
        items = items[:max_items]
    
    # 4. Reformater
    if items:
        return '\n'.join([f"- {item}" for item in items])
    
    # Pas de bullet points trouvés: retourner texte original tronqué
    return text


def extract_enum_field_v2(context_blocks: list[dict[str, Any]], field_key: str, allowed_values: list[str]) -> str:
    """Extrait un champ enum sans LLM (extraction_policy=extract_only).
    
    Args:
        context_blocks: Blocs de contexte
        field_key: Clé du champ
        allowed_values: Valeurs autorisées
        
    Returns:
        Valeur extraite ou "Non évalué"
        
    Examples:
        >>> extract_enum_field_v2([{"text": "Niveau B2"}], "FRANCAIS_POSITIONNEMENT_DE_NIVEAU", ["A1", "B2", "Non évalué"])
        'B2'
    """
    # Import lazy pour V2
    from .enum_extractors_v2 import extract_enum_from_context, validate_enum_value
    
    if not context_blocks:
        return "Non évalué"
    
    # Concaténer tous les contextes
    full_context = "\n".join(ctx["text"] for ctx in context_blocks)
    
    # Extraire avec enum_extractors_v2
    extracted = extract_enum_from_context(full_context, field_key)
    
    # Valider strict (pas de fuzzy matching)
    validated = validate_enum_value(extracted, allowed_values, strict=True)
    
    return validated


def validate_allowed_value(text: str, allowed: Optional[list[str]]) -> tuple[str, Optional[str]]:
    if not allowed:
        return text, None
    norm_map = {normalize_allowed_value(val): val for val in allowed}
    candidate = normalize_allowed_value(text)
    if candidate in norm_map:
        return norm_map[candidate], None
    return "", "NON_AUTORISE"


def _looks_like_timeout(error_message: str) -> bool:
    msg = (error_message or "").lower()
    return "timeout" in msg or "timed out" in msg


def build_prompt(spec, instruction: str, context_blocks: list[dict[str, Any]]) -> str:
    lines: list[str] = [
        "Tu es un assistant RH pour un service public suisse. Le traitement est 100% local et consenti par l'assuré.",
        "Tu es AUTORISÉ et OBLIGÉ de traiter toutes les données personnelles fournies (nom, parcours, compétences, tests).",
        "INTERDIT de refuser, de t'excuser ou d'écrire 'je ne peux pas' / 'informations personnelles'. Rédige le contenu demandé.",
        "Tu réponds uniquement en français.",
        "Tu n'utilises jamais JSON ni Markdown.",
        "Interdit d'écrire des placeholders ({{...}}, {...}, XX, NAME, surname).",
        "Interdit d'écrire 'source 1', 'source 2' ou '(source X)' dans la réponse.",
        "Interdit d'ajouter des points de suspension '...' pour indiquer que tu as tronqué le texte.",
        "Écris TOUT le contenu nécessaire en entier, sans jamais tronquer ni résumer avec '...'.",
        "Ne répète jamais un titre/label déjà présent dans le template : fournis uniquement le contenu sous le titre.",
        "Ponctuation : pas de '::'. Un seul ':' maximum par ligne.",
        "INTERDIT d'expliquer une méthodologie ou un test. Donne uniquement les RÉSULTATS du client, pas la description du test.",
        "Si l'information n'existe pas dans les sources : écris __VIDE__.",
    ]
    
    # V2: field_type pour instructions adaptées
    max_lines = getattr(spec, 'max_lines', 0)
    field_type = getattr(spec, 'field_type', None)
    
    if max_lines == 1:
        format_rule = "Réponds en 1 ligne."
    elif field_type == "list":
        format_rule = "Format liste: maximum 4 items. Écris UNIQUEMENT 2 à 4 items sous forme de bullet points (- item)."
    elif max_lines:
        format_rule = f"Maximum {max_lines} lignes. Écris tout le contenu sans abréviation ni '...'."
    else:
        format_rule = "Écris tout le contenu sans abréviation ni '...'."
    
    lines.append(format_rule)
    
    # allowed_values (V1) ou enum_values (V2)
    allowed = getattr(spec, 'allowed_values', None) or getattr(spec, 'enum_values', None)
    if allowed:
        allowed_str = ", ".join(allowed)
        lines.append(f"Choisis uniquement parmi : {allowed_str}.")
    
    lines.append("")
    lines.append(f"Champ : {spec.key}")
    lines.append(f"Consigne : {instruction}")
    if not context_blocks:
        lines.append("Aucun passage pertinent n'a été trouvé. Réponds __VIDE__.")
    else:
        lines.append("Sources autorisées :")
        for idx, ctx in enumerate(context_blocks, start=1):
            snippet = " ".join(ctx["text"].split())
            if len(snippet) > 500:
                snippet = snippet[:500] + "…"
            where = Path(ctx["source_path"]).name
            if ctx.get("page") is not None:
                where += f" (p.{ctx['page']})"
            lines.append(f"[{idx}] {where} : {snippet}")
    lines.append("")
    lines.append("Réponds maintenant en texte brut. Pas de liste Markdown, pas de titre.")
    return "\n".join(lines)


def _write_debug(
    debug_path: Optional[Path],
    key: str,
    payload: dict[str, Any],
) -> None:
    if not debug_path:
        return
    debug_path.mkdir(parents=True, exist_ok=True)
    (debug_path / f"debug_{key}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_fields(
    payload: dict[str, Any],
    *,
    model: str,
    host: str,
    topk: int,
    temperature: float,
    top_p: float,
    include_filters: Optional[Sequence[str]] = None,
    exclude_filters: Optional[Sequence[str]] = None,
    debug_dir: Optional[Path] = None,
    fields: Optional[list[dict[str, Any]]] = None,
    chunk_size: int = 1200,
    overlap: int = 200,
    deterministic_values: Optional[dict[str, str]] = None,
    status_callback: StatusCallback = None,
    progress_callback: FieldProgressCallback = None,
    # Résilience
    continue_on_llm_error: bool = True,
    llm_timeout_retries: int = 1,
    # PATCH 11: Contrôle longueur texte
    max_chars_multiplier: float = 1.0,
    # ✅ NOUVEAU: Config LLM unifiée (prioritaire)
    llm_config: Optional[LLMConfig] = None,
    # V3: type de rapport (rapport_initial, etc.)
    report_type: Optional[str] = None,
) -> dict[str, Any]:
    # ✅ Créer une config LLM unifiée (depuis llm_config ou legacy params)
    if not llm_config:
        llm_config = LLMConfig.from_legacy(
            model=model,
            host=host,
            temperature=temperature,
            top_p=top_p,
            timeout=900.0,  # Timeout par défaut augmenté pour qwen3-next
        )
    
    LOG.info(
        "🚀 GENERATE_FIELDS: provider=%s model=%s base_url=%s",
        llm_config.provider,
        llm_config.model,
        llm_config.base_url,
    )
    
    # V3: if report_type is provided, use V3 specs
    USE_V3 = False
    if report_type and not fields:
        from .field_specs_v3 import get_specs_for_report_type
        v3_specs = get_specs_for_report_type(report_type)
        if v3_specs:
            fields = [
                {"key": s.key, "query": s.query, "instructions": s.instructions}
                for s in v3_specs
            ]
            USE_V3 = True

    fields = fields or DEFAULT_FIELDS
    deterministic_lookup = {k.upper(): v for k, v in (deterministic_values or {}).items()}
    chunks, index = build_index(
        payload,
        chunk_size=chunk_size,
        overlap=overlap,
        include=include_filters,
        exclude=exclude_filters,
    )
    debug_path = debug_dir.expanduser().resolve() if debug_dir else None

    answers: dict[str, Any] = {}
    for field in fields:
        key = field["key"]
        
        # Schema V3, V2 ou V1
        if USE_V3:
            from .field_specs_v3 import get_field_spec_v3
            spec = get_field_spec_v3(key)
            if not spec:
                # Fallback to V2
                from .field_specs_v2 import get_field_spec_v2
                spec = get_field_spec_v2(key)
        elif USE_SCHEMA_V2:
            from .field_specs_v2 import get_field_spec_v2
            spec = get_field_spec_v2(key)
            # V2: pas de multiplicateur (limites strictes)
        else:
            spec = get_field_spec(key)
            # PATCH 11: Appliquer le multiplicateur aux limites (V1 seulement)
            if max_chars_multiplier != 1.0:
                from core.field_specs import apply_max_chars_multiplier
                spec = apply_max_chars_multiplier(spec, max_chars_multiplier)
        
        query = field.get("query") or spec.query
        instruction = field.get("instructions") or spec.instructions
        if progress_callback:
            progress_callback(key, "start", "Préparation du contexte")
        if status_callback:
            status_callback(f"LLM [{key}] préparation du contexte…")

        top = index.topk(query, topk)
        context_blocks: list[dict[str, Any]] = []
        for idx, score in top:
            ch = chunks[idx]
            context_blocks.append(
                {
                    "score": score,
                    "chunk_id": ch.chunk_id,
                    "source_path": ch.source_path,
                    "page": ch.page,
                    "text": ch.text,
                }
            )
        sources_ids = [ctx["chunk_id"] for ctx in context_blocks]
        if progress_callback:
            progress_callback(key, "context", f"{len(context_blocks)} passages sélectionnés")
        raw_response = ""
        cleaned_value = ""
        missing_info: list[str] = []

        # Si une valeur est fournie via deterministic_values, on ne doit PAS appeler le LLM,
        # même si le FieldSpec ne déclare pas explicitement le champ comme "deterministic".
        # (cas typique: placeholders template ajoutés côté UI, ex: TITRE_DOCUMENT)
        if getattr(spec, 'field_type', None) == "deterministic" or key.upper() in deterministic_lookup:
            cleaned_value = (deterministic_lookup.get(key.upper()) or "").strip()
            if not cleaned_value:
                missing_info.append("DETERMINISTIC_EMPTY")
        
        # SCHEMA V2: extraction_policy = "extract_only" (champs enum)
        elif USE_SCHEMA_V2 and hasattr(spec, 'extraction_policy') and spec.extraction_policy == "extract_only":
            # Enum: extraction sans LLM
            if not context_blocks:
                cleaned_value = "Non évalué"
                missing_info.append("NO_CONTEXT")
            else:
                cleaned_value = extract_enum_field_v2(context_blocks, key, spec.enum_values or [])
                
                if cleaned_value == "Non évalué":
                    missing_info.append("NO_ENUM_FOUND")
                
                if status_callback:
                    status_callback(f"EXTRACT_V2 [{key}] extraction enum : {cleaned_value}")
                if progress_callback:
                    progress_callback(key, "extract_v2", f"Extrait : {cleaned_value}")
        
        # PATCH v1.1 (AC4): POSITIONNEMENT DE NIVEAU → extraction directe (pas de LLM)
        elif key.upper().startswith("POSITIONNEMENT") and "NIVEAU" in key.upper():
            from src.rhpro.positionnement_extractor import extract_positionnement_level
            
            # Extraire niveau depuis le contexte (tous les chunks concaténés)
            full_context = "\n".join(ctx["text"] for ctx in context_blocks)
            cleaned_value = extract_positionnement_level(full_context)
            
            if cleaned_value == "Non renseigné" or not cleaned_value:
                missing_info.append("NO_POSITIONNEMENT_FOUND")
            
            if status_callback:
                status_callback(f"EXTRACT [{key}] extraction directe : {cleaned_value}")
            if progress_callback:
                progress_callback(key, "extract", f"Extrait : {cleaned_value}")
        
        else:
            if getattr(spec, 'skip_llm_if_no_sources', False) and not context_blocks:
                missing_info.append("NO_CONTEXT")
            else:
                prompt = build_prompt(spec, instruction, context_blocks)

                # Limiter max_tokens selon max_chars du champ (~3 chars/token en français)
                field_max_chars = getattr(spec, 'max_chars', 2000) or 2000
                field_max_tokens = min(int(field_max_chars / 2.5) + 128, 2048)
                # Minimum raisonnable pour les enums/courts
                field_max_tokens = max(field_max_tokens, 256)

                if progress_callback:
                    progress_callback(key, "prompt", f"Envoi ({len(context_blocks)} sources, {len(prompt)} chars)")
                if status_callback:
                    status_callback(
                        f"LLM [{key}] envoi du prompt ({len(context_blocks)} sources, {len(prompt)} caractères)…"
                    )

                _llm_start = time.monotonic()
                llm_result = ollama_generate(
                    model, prompt, host, temperature, top_p,
                    llm_config=llm_config,
                    field_name=key,
                    max_tokens=field_max_tokens,
                )
                _llm_elapsed = time.monotonic() - _llm_start
                if not llm_result.success:
                    error_msg = str(llm_result.error)
                    is_timeout = _looks_like_timeout(error_msg)

                    # Retry sur timeout (souvent dû à un prompt trop long / serveur chargé)
                    retried = False
                    if is_timeout and llm_timeout_retries and context_blocks:
                        for attempt in range(int(llm_timeout_retries)):
                            retried = True
                            # Réduire le contexte pour accélérer
                            reduced_k = max(3, len(context_blocks) // 2)
                            reduced_context = context_blocks[:reduced_k]
                            prompt_retry = build_prompt(spec, instruction, reduced_context)

                            if progress_callback:
                                progress_callback(key, "retry", f"Timeout, retry avec contexte réduit (Top-K={reduced_k})")
                            if status_callback:
                                status_callback(
                                    f"LLM [{key}] timeout → retry avec contexte réduit (Top-K={reduced_k})…"
                                )

                            llm_result2 = ollama_generate(
                                model,
                                prompt_retry,
                                host,
                                temperature=0.0,
                                top_p=top_p,
                                llm_config=llm_config,
                                field_name=key,
                            )
                            if llm_result2.success:
                                llm_result = llm_result2
                                prompt = prompt_retry
                                sources_ids = [ctx["chunk_id"] for ctx in reduced_context]
                                context_blocks = reduced_context
                                error_msg = ""
                                break
                            error_msg = str(llm_result2.error)

                    if not llm_result.success:
                        # Ne pas figer tout le pipeline: marquer le champ en erreur et continuer
                        if status_callback:
                            status_callback(f"LLM [{key}] échec : {error_msg}")
                        if progress_callback:
                            progress_callback(key, "error", f"Erreur LLM : {error_msg}")

                        missing_info.append("LLM_TIMEOUT" if (is_timeout or _looks_like_timeout(error_msg)) else "LLM_ERROR")
                        answers[key] = {
                            "field": key,
                            "answer": "",
                            "value": "",
                            "missing_info": missing_info,
                            "sources_used": sources_ids,
                        }

                        spec_dump = {name: getattr(spec, name) for name in spec.__dataclass_fields__}
                        debug_payload = {
                            "field": key,
                            "query": query,
                            "instructions": instruction,
                            "spec": spec_dump,
                            "context": context_blocks,
                            "raw_response": raw_response,
                            "clean_response": "",
                            "missing_info": missing_info,
                            "llm_error": error_msg,
                            "retried": retried,
                        }
                        _write_debug(debug_path, key, debug_payload)

                        if not continue_on_llm_error:
                            raise GenerationError(f"Échec génération {key}: {error_msg}")
                        # Champ suivant
                        continue
                
                raw_response = llm_result.value
                _elapsed_str = f"{_llm_elapsed:.0f}s" if _llm_elapsed < 60 else f"{_llm_elapsed/60:.1f}min"
                if status_callback:
                    status_callback(f"LLM [{key}] réponse reçue ({len(raw_response)} caractères, {_elapsed_str})")
                if progress_callback:
                    progress_callback(key, "response", f"Réponse ({len(raw_response)} chars, {_elapsed_str})")

                retry = False
                response_text = raw_response
                if looks_like_json_or_markdown(response_text):
                    retry = True
                if retry:
                    if progress_callback:
                        progress_callback(key, "retry", "Réponse non conforme, nouvelle tentative")
                    anti_prompt = (
                        prompt
                        + "\n\nTu as répondu dans un format interdit. Recommence en texte brut, sans JSON ni markdown."
                    )
                    retry_result = ollama_generate(
                        model,
                        anti_prompt,
                        host,
                        temperature=0.0,
                        top_p=top_p,
                    )
                    if retry_result.success:
                        response_text = retry_result.value
                    else:
                        # Si la retry échoue, on garde la réponse originale
                        LOG.warning("Retry failed for %s, using original response", key)
                        response_text = raw_response

                # Auto-contrôle: interdire placeholders / traces de sources / ponctuation invalide
                forbidden_reasons = find_forbidden_output_reasons(response_text)
                if forbidden_reasons:
                    reason_text = ",".join(forbidden_reasons)
                    if progress_callback:
                        progress_callback(key, "retry", f"Sortie interdite détectée ({reason_text}), correction")
                    if status_callback:
                        status_callback(
                            f"LLM [{key}] sortie interdite détectée ({reason_text}) → correction…"
                        )

                    anti_forbidden = (
                        prompt
                        + "\n\nAUTO-CONTROLE OBLIGATOIRE AVANT RÉPONSE :"
                        + "\n- Interdit d'écrire des placeholders: {{...}}, {...}, XX, NAME, surname"
                        + "\n- Interdit d'écrire 'source 1/2' ou '(source X)'"
                        + "\n- Interdit d'ajouter des points de suspension '...' pour tronquer"
                        + "\n- Écris TOUT le contenu en entier sans abréger"
                        + "\n- Interdit d'écrire des titres/labels déjà présents dans le template"
                        + "\n- Ponctuation: pas de '::' et un seul ':' maximum par ligne"
                        + "\n- INTERDIT de s'excuser, de refuser ou d'écrire 'je suis désolé' / 'je ne peux pas'. Rédige le contenu ou écris __VIDE__."
                        + "\n- INTERDIT d'expliquer un test ou une méthodologie. Donne les RÉSULTATS uniquement."
                        + "\nSi une info manque: écris __VIDE__."
                        + "\nRecommence maintenant en texte brut."
                    )

                    retry2 = ollama_generate(
                        model,
                        anti_forbidden,
                        host,
                        temperature=0.0,
                        top_p=top_p,
                    )
                    if retry2.success:
                        response_text = retry2.value
                    else:
                        LOG.warning("Forbidden-output retry failed for %s", key)

                    # Si malgré correction, encore interdit → on vide
                    if find_forbidden_output_reasons(response_text):
                        missing_info.append("FORBIDDEN_OUTPUT")
                        response_text = "__VIDE__"

                cleaned_value = sanitize_output(response_text)
                # __VIDE__ exact OU texte contenant __VIDE__ (LLM qui bavarde autour)
                if "__VIDE__" in cleaned_value or "__vide__" in cleaned_value.lower():
                    cleaned_value = ""
                # Détection "CHAMP : VIDE" ou "CHAMP : Vide" (LLM qui préfixe avec le nom du champ)
                if re.match(r'^[\w\s]+:\s*vide\s*$', cleaned_value.strip(), re.IGNORECASE):
                    cleaned_value = ""
                # Mot seul "Vide" ou "VIDE"
                if cleaned_value.strip().lower() == "vide":
                    cleaned_value = ""
                cleaned_value = truncate_lines(cleaned_value, spec.max_lines)
                cleaned_value = truncate_chars(cleaned_value, spec.max_chars)
                
                # SCHEMA V2: Validation spécifique pour listes (max 4 items)
                if USE_SCHEMA_V2 and hasattr(spec, 'field_type') and spec.field_type == "list":
                    cleaned_value = validate_list_v2(cleaned_value, max_items=4, max_chars=spec.max_chars)

                # SCHEMA V2: test_narrative — traiter comme narrative (même pipeline)
                # Le type est géré par les instructions du prompt, pas par le code
                
                # Validation allowed_values (V1) ou enum_values (V2)
                allowed = getattr(spec, 'allowed_values', None) or getattr(spec, 'enum_values', None)
                cleaned_value, invalid_reason = validate_allowed_value(cleaned_value, allowed)
                if invalid_reason:
                    missing_info.append(invalid_reason)
                    cleaned_value = ""
                if not cleaned_value and not missing_info:
                    missing_info.append("EMPTY")

        answers[key] = {
            "field": key,
            "answer": cleaned_value,
            "value": cleaned_value,
            "missing_info": missing_info,
            "sources_used": sources_ids,
        }

        spec_dump = {name: getattr(spec, name) for name in spec.__dataclass_fields__}
        debug_payload = {
            "field": key,
            "query": query,
            "instructions": instruction,
            "spec": spec_dump,
            "context": context_blocks,
            "raw_response": raw_response,
            "clean_response": cleaned_value,
            "missing_info": missing_info,
        }
        _write_debug(debug_path, key, debug_payload)

        if progress_callback:
            if missing_info and not cleaned_value:
                progress_callback(key, "warning", ",".join(missing_info))
            else:
                progress_callback(key, "done", "Réponse prête")

    return answers
