"""Génération des sections du rapport via Ollama (format texte brut)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib import request

from .context import build_index
from .field_specs import FieldSpec, get_field_spec, normalize_allowed_value

StatusCallback = Optional[Callable[[str], None]]
FieldProgressCallback = Optional[Callable[[str, str, str], None]]

DEFAULT_FIELDS = [
    {"key": "PROFESSION", "query": "Profession actuelle", "instructions": "Synthèse pro"},
    {"key": "FORMATION", "query": "Parcours de formation", "instructions": "Formations"},
]

RE_JSON = re.compile(r"\A\s*[{[]")
RE_CODEBLOCK = re.compile(r"```|\bjson\b", re.IGNORECASE)


def ollama_generate(model: str, prompt: str, host: str, temperature: float, top_p: float) -> str:
    url = host.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "top_p": top_p},
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=300) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    return out.get("response", "")


def check_llm_status(host: str, model: Optional[str] = None, timeout: float = 3.0) -> Tuple[bool, str]:
    base = host.rstrip("/")
    try:
        with request.urlopen(base + "/api/version", timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        version = payload.get("version") or payload.get("name") or "inconnue"
        message = f"Serveur accessible ({version})"
    except Exception as exc:
        return False, f"Serveur injoignable : {exc}"

    if not model:
        return True, message

    try:
        with request.urlopen(base + "/api/tags", timeout=timeout) as resp:
            tags_payload = json.loads(resp.read().decode("utf-8"))
        models = tags_payload.get("models", []) if isinstance(tags_payload, dict) else []
        names = {m.get("name") for m in models if isinstance(m, dict)}
        if model in names:
            return True, message + f" — modèle '{model}' disponible"
        return False, message + f" — modèle '{model}' introuvable"
    except Exception as exc:
        return False, message + f" — vérification du modèle impossible : {exc}"


def sanitize_output(text: str) -> str:
    text = text.replace("```", " ")
    text = text.replace("\u200b", " ")
    text = re.sub(r"(?i)^json[:\s]+", "", text.strip())
    return text.strip()


def looks_like_json_or_markdown(text: str) -> bool:
    stripped = text.strip()
    return bool(RE_JSON.match(stripped) or RE_CODEBLOCK.search(stripped))


def truncate_lines(text: str, max_lines: int) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
    return "\n".join(lines)


def truncate_chars(text: str, max_chars: int) -> str:
    if max_chars and len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"
    return text


def validate_allowed_value(text: str, allowed: Optional[List[str]]) -> Tuple[str, Optional[str]]:
    if not allowed:
        return text, None
    norm_map = {normalize_allowed_value(val): val for val in allowed}
    candidate = normalize_allowed_value(text)
    if candidate in norm_map:
        return norm_map[candidate], None
    return "", "NON_AUTORISE"


def build_prompt(spec: FieldSpec, instruction: str, context_blocks: List[Dict[str, Any]]) -> str:
    lines: List[str] = [
        "Tu es un assistant RH.",
        "Tu réponds uniquement en français.",
        "Tu n'utilises jamais JSON ni Markdown.",
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
    payload: Dict[str, Any],
) -> None:
    if not debug_path:
        return
    debug_path.mkdir(parents=True, exist_ok=True)
    (debug_path / f"debug_{key}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_fields(
    payload: Dict[str, Any],
    *,
    model: str,
    host: str,
    topk: int,
    temperature: float,
    top_p: float,
    include_filters: Optional[Sequence[str]] = None,
    exclude_filters: Optional[Sequence[str]] = None,
    debug_dir: Optional[Path] = None,
    fields: Optional[List[Dict[str, Any]]] = None,
    chunk_size: int = 1200,
    overlap: int = 200,
    deterministic_values: Optional[Dict[str, str]] = None,
    status_callback: StatusCallback = None,
    progress_callback: FieldProgressCallback = None,
) -> Dict[str, Any]:
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

    answers: Dict[str, Any] = {}
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
        context_blocks: List[Dict[str, Any]] = []
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
        missing_info: List[str] = []

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
                try:
                    raw_response = ollama_generate(model, prompt, host, temperature, top_p)
                except Exception as exc:
                    if status_callback:
                        status_callback(f"LLM [{key}] échec : {exc}")
                    if progress_callback:
                        progress_callback(key, "error", f"Erreur LLM : {exc}")
                    raise
                if status_callback:
                    status_callback(f"LLM [{key}] réponse reçue ({len(raw_response)} caractères)")
                if progress_callback:
                    progress_callback(key, "response", f"Réponse ({len(raw_response)} caractères)")

                retry = False
                response_text = raw_response
                if looks_like_json_or_markdown(response_text):
                    retry = True
                if retry:
                    anti_prompt = (
                        prompt
                        + "\n\nTu as répondu dans un format interdit. Recommence en texte brut, sans JSON ni markdown."
                    )
                    response_text = ollama_generate(
                        model,
                        anti_prompt,
                        host,
                        temperature=0.0,
                        top_p=top_p,
                    )
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
