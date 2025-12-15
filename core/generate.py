"""Génération des sections du rapport via Ollama."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib import request

from .context import build_index

StatusCallback = Optional[Callable[[str], None]]
FieldProgressCallback = Optional[Callable[[str, str, str], None]]

DEFAULT_FIELDS = [
    {
        "key": "PROFESSION",
        "query": "Profession actuelle, expériences, postes occupés, responsabilités",
        "instructions": "Rédige une synthèse courte et factuelle sur la profession/expériences.",
    },
    {
        "key": "FORMATION",
        "query": "Formations, diplômes, certifications, parcours scolaire",
        "instructions": "Rédige une synthèse claire des formations et diplômes.",
    },
    {
        "key": "DISCUSSION_ASSURE",
        "query": "Résultats de la discussion avec l’assuré, motivations, freins, points d'appui",
        "instructions": "Synthèse structurée (motivations / freins / points d'appui).",
    },
    {
        "key": "ORIENTATION",
        "query": "Orientation, pistes métier, projet professionnel, recommandations",
        "instructions": "Propose une orientation cohérente, basée uniquement sur les sources.",
    },
    {
        "key": "STAGE",
        "query": "Stage, immersion, objectifs, retour, résultats, suite recommandée",
        "instructions": "Décris le stage s’il existe, sinon indique qu’il manque l’info.",
    },
    {
        "key": "CONCLUSION",
        "query": "Conclusion globale, résumé final, prochaines étapes",
        "instructions": "Conclusion courte + prochaines étapes.",
    },
]


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


def extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("Réponse LLM non-JSON")
    return json.loads(match.group(0))


def attempt_json_repair(
    field_key: str,
    raw_response: str,
    *,
    model: str,
    host: str,
    temperature: float,
    top_p: float,
    status_callback: StatusCallback = None,
) -> Optional[Dict[str, Any]]:
    """Tente de corriger une réponse LLM en demandant une reformulation stricte JSON."""

    snippet = raw_response.strip()
    if len(snippet) > 4000:
        snippet = snippet[:4000] + "\n… (troncature)"
        repair_prompt = f"""
Tu as tenté de répondre au champ {field_key} mais le JSON est invalide.
Réponse initiale (entre triples backticks) :
```
{snippet}
```
Corrige uniquement la syntaxe en respectant STRICTEMENT le schéma suivant :
{{
    "field": "{field_key}",
    "answer": "texte rédigé",
    "missing_info": [],
    "sources_used": []
}}
Ne rajoute aucun texte hors de l'objet JSON.
""".strip()
    try:
        if status_callback:
            status_callback(f"LLM [{field_key}] tentative de correction JSON...")
        fixed = ollama_generate(model, repair_prompt, host, temperature=max(0.0, temperature / 2), top_p=top_p)
    except Exception as exc:  # pragma: no cover - dépend du LLM
        if status_callback:
            status_callback(f"LLM [{field_key}] correction impossible : {exc}")
        return None
    try:
        return extract_json_object(fixed)
    except Exception:
        if status_callback:
            status_callback(f"LLM [{field_key}] correction JSON toujours invalide")
        return None


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


def build_prompt(field_key: str, instructions: str, context_blocks: List[Dict[str, Any]]) -> str:
    context_txt = []
    for i, block in enumerate(context_blocks, start=1):
        where = Path(block["source_path"]).name
        if block.get("page") is not None:
            where += f" (page {block['page']})"
        context_txt.append(f"[SOURCE {i}] {where}\n{block['text']}\n")
    return f"""
Tu es un assistant qui remplit un rapport à partir de sources.
Tu DOIS respecter les règles suivantes :
- Utilise UNIQUEMENT les informations présentes dans les SOURCES.
- Si une information manque, tu dois l'indiquer dans missing_info.
- Ne fabrique rien. Pas d'invention.
- Réponds STRICTEMENT en JSON (un objet), sans texte autour.

Champ à remplir: {field_key}
Consigne de rédaction: {instructions}

SOURCES :
{chr(10).join(context_txt)}

Format JSON attendu (exemple) :
{{
  "field": "{field_key}",
  "answer": "texte rédigé pour ce champ",
  "missing_info": [],
  "sources_used": [1,2]
}}
""".strip()


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
    status_callback: StatusCallback = None,
    progress_callback: FieldProgressCallback = None,
) -> Dict[str, Any]:
    fields = fields or DEFAULT_FIELDS
    chunks, index = build_index(
        payload,
        chunk_size=chunk_size,
        overlap=overlap,
        include=include_filters,
        exclude=exclude_filters,
    )
    debug_path = debug_dir.expanduser().resolve() if debug_dir else None
    if debug_path:
        debug_path.mkdir(parents=True, exist_ok=True)

    answers: Dict[str, Any] = {}
    for field in fields:
        key = field["key"]
        query = field["query"]
        instructions = field.get("instructions", "")
        if progress_callback:
            progress_callback(key, "start", "Préparation du contexte")
        if status_callback:
            status_callback(f"LLM [{key}] préparation du contexte...")
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
        if debug_path:
            (debug_path / f"debug_{key}.json").write_text(
                json.dumps({"field": key, "query": query, "context": context_blocks}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if progress_callback:
            progress_callback(key, "context", f"{len(context_blocks)} passages sélectionnés")
        prompt = build_prompt(key, instructions, context_blocks)
        if status_callback:
            status_callback(
                f"LLM [{key}] envoi du prompt ({len(context_blocks)} sources, {len(prompt)} caractères)..."
            )
        if progress_callback:
            progress_callback(key, "prompt", f"Envoi ({len(context_blocks)} sources, {len(prompt)} caractères)")
        try:
            raw = ollama_generate(model, prompt, host, temperature, top_p)
        except Exception as exc:
            if status_callback:
                status_callback(f"LLM [{key}] échec : {exc}")
            if progress_callback:
                progress_callback(key, "error", f"Erreur LLM : {exc}")
            raise
        if status_callback:
            status_callback(f"LLM [{key}] réponse reçue ({len(raw)} caractères)")
        if progress_callback:
            progress_callback(key, "response", f"Réponse ({len(raw)} caractères)")
        had_error = False
        json_repaired = False
        try:
            obj = extract_json_object(raw)
        except Exception:
            if status_callback:
                status_callback(f"LLM [{key}] réponse non conforme, JSON invalide")
            if progress_callback:
                progress_callback(key, "retry", "JSON invalide, tentative de correction")
            repaired = attempt_json_repair(
                key,
                raw,
                model=model,
                host=host,
                temperature=temperature,
                top_p=top_p,
                status_callback=status_callback,
            )
            if repaired is not None:
                obj = repaired
                json_repaired = True
            else:
                if progress_callback:
                    progress_callback(key, "error", "Réponse non conforme (JSON)")
                raw_text = raw.strip()
                if len(raw_text) > 2000:
                    raw_text = raw_text[:2000] + "…"
                if raw_text:
                    fallback_answer = f"Réponse LLM (JSON invalide) :\n{raw_text}"
                else:
                    fallback_answer = "Information indisponible (JSON invalide)."
                obj = {
                    "field": key,
                    "answer": fallback_answer,
                    "missing_info": ["JSON_INVALID"],
                    "sources_used": [],
                }
                had_error = True
        if "field" not in obj:
            obj["field"] = key
        answers[key] = obj
        if progress_callback:
            if had_error:
                summary = "Réponse marquée JSON_INVALID (texte brut)"
                progress_callback(key, "error", summary)
            elif json_repaired:
                progress_callback(key, "done", "Réponse corrigée automatiquement")
            else:
                summary = "Réponse structurée" if obj.get("answer") else "Réponse vide"
                final_status = "done" if obj.get("answer") else "warning"
                progress_callback(key, final_status, summary)
    return answers
