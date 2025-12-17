"""Génération des sections du rapport via Ollama (format texte brut)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Optional
from urllib import request
from urllib.error import URLError, HTTPError

from .context import build_index
from .errors import Result, GenerationError, OllamaError
from .field_specs import FieldSpec, get_field_spec, normalize_allowed_value
from .logger import get_logger

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
    timeout: float = 300.0,
) -> Result[str]:
    """Génère une réponse via l'API Ollama.
    
    Args:
        model: Nom du modèle Ollama
        prompt: Prompt à envoyer
        host: URL du serveur Ollama
        temperature: Température (0-1)
        top_p: Paramètre top_p (0-1)
        timeout: Timeout en secondes (défaut 300)
        
    Returns:
        Result[str]: Succès avec la réponse générée ou échec avec OllamaError
    """
    try:
        LOG.info("Requête Ollama: model=%s, temp=%.2f, top_p=%.2f", model, temperature, top_p)
        url = host.rstrip("/") + "/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "top_p": top_p},
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        with request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        
        response = out.get("response", "")
        LOG.debug("Réponse Ollama: %d caractères", len(response))
        return Result.ok(response)
        
    except (URLError, HTTPError) as exc:
        error = OllamaError(f"Échec connexion Ollama {host}: {exc}")
        LOG.error("Erreur connexion Ollama: %s", exc)
        return Result.fail(error)
    except TimeoutError as exc:
        error = OllamaError(f"Timeout Ollama après {timeout}s: {exc}")
        LOG.error("Timeout Ollama: %s", exc)
        return Result.fail(error)
    except Exception as exc:
        error = OllamaError(f"Erreur Ollama: {exc}")
        LOG.error("Erreur Ollama: %s", exc)
        return Result.fail(error)


def check_llm_status(host: str, model: Optional[str] = None, timeout: float = 3.0) -> Result[str]:
    """Vérifie la disponibilité du serveur Ollama et du modèle.
    
    Args:
        host: URL du serveur Ollama
        model: Nom du modèle à vérifier (optionnel)
        timeout: Timeout en secondes
        
    Returns:
        Result[str]: Succès avec message de statut ou échec avec OllamaError
    """
    LOG.info("Évérification serveur Ollama: %s", host)
    base = host.rstrip("/")
    
    try:
        with request.urlopen(base + "/api/version", timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        version = payload.get("version") or payload.get("name") or "inconnue"
        message = f"Serveur accessible ({version})"
        LOG.info("Serveur Ollama OK: %s", version)
    except Exception as exc:
        error = OllamaError(f"Serveur injoignable : {exc}")
        LOG.error("Échec connexion serveur Ollama: %s", exc)
        return Result.fail(error)

    if not model:
        return Result.ok(message)

    try:
        with request.urlopen(base + "/api/tags", timeout=timeout) as resp:
            tags_payload = json.loads(resp.read().decode("utf-8"))
        models = tags_payload.get("models", []) if isinstance(tags_payload, dict) else []
        names = {m.get("name") for m in models if isinstance(m, dict)}
        if model in names:
            full_message = message + f" — modèle '{model}' disponible"
            LOG.info("Modèle '%s' disponible", model)
            return Result.ok(full_message)
        error = OllamaError(message + f" — modèle '{model}' introuvable")
        LOG.warning("Modèle '%s' introuvable", model)
        return Result.fail(error)
    except Exception as exc:
        error = OllamaError(message + f" — vérification du modèle impossible : {exc}")
        LOG.error("Échec vérification modèle: %s", exc)
        return Result.fail(error)


def sanitize_output(text: str) -> str:
    text = text.replace("```", " ")
    text = text.replace("\u200b", " ")
    text = re.sub(r"(?i)^json[:\s]+", "", text.strip())
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


def truncate_chars(text: str, max_chars: int) -> str:
    if max_chars and len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"
    return text


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


def build_prompt(spec: FieldSpec, instruction: str, context_blocks: list[dict[str, Any]]) -> str:
    lines: list[str] = [
        "Tu es un assistant RH.",
        "Tu réponds uniquement en français.",
        "Tu n'utilises jamais JSON ni Markdown.",
        "Interdit d'écrire des placeholders ({{...}}, {...}, XX, NAME, surname).",
        "Interdit d'écrire 'source 1', 'source 2' ou '(source X)' dans la réponse.",
        "Ne répète jamais un titre/label déjà présent dans le template : fournis uniquement le contenu sous le titre.",
        "Ponctuation : pas de '::'. Un seul ':' maximum par ligne.",
        "Si l'information n'existe pas dans les sources : écris __VIDE__.",
    ]
    format_rule = "Réponds en 1 ligne." if spec.max_lines == 1 else "Maximum 4 lignes courtes."
    lines.append(format_rule)
    if spec.allowed_values:
        allowed = ", ".join(spec.allowed_values)
        lines.append(f"Choisis uniquement parmi : {allowed}.")
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
) -> dict[str, Any]:
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
        spec = get_field_spec(key)
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

        if spec.field_type == "deterministic":
            cleaned_value = (deterministic_lookup.get(key.upper()) or "").strip()
            if not cleaned_value:
                missing_info.append("DETERMINISTIC_EMPTY")
        else:
            if spec.skip_llm_if_no_sources and not context_blocks:
                missing_info.append("NO_CONTEXT")
            else:
                prompt = build_prompt(spec, instruction, context_blocks)
                if progress_callback:
                    progress_callback(key, "prompt", f"Envoi ({len(context_blocks)} sources)")
                if status_callback:
                    status_callback(
                        f"LLM [{key}] envoi du prompt ({len(context_blocks)} sources, {len(prompt)} caractères)…"
                    )
                
                llm_result = ollama_generate(model, prompt, host, temperature, top_p)
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
                if status_callback:
                    status_callback(f"LLM [{key}] réponse reçue ({len(raw_response)} caractères)")
                if progress_callback:
                    progress_callback(key, "response", f"Réponse ({len(raw_response)} caractères)")

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
                        + "\n- Interdit d'écrire des titres/labels déjà présents dans le template"
                        + "\n- Ponctuation: pas de '::' et un seul ':' maximum par ligne"
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
                if cleaned_value == "__VIDE__":
                    cleaned_value = ""
                cleaned_value = truncate_lines(cleaned_value, spec.max_lines)
                cleaned_value = truncate_chars(cleaned_value, spec.max_chars)
                cleaned_value, invalid_reason = validate_allowed_value(cleaned_value, spec.allowed_values)
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
