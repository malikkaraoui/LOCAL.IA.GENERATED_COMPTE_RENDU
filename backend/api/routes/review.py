"""Review endpoints for V3 report sections."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from redis import Redis
from rq.job import Job

from backend.config import settings
from core.report_types import list_report_types
from core.section_evaluator import evaluate_section
from core.field_specs_v3 import get_field_spec_v3, get_specs_for_report_type

router = APIRouter()
logger = logging.getLogger(__name__)

redis_conn = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=False,
)


@router.get("/report-types")
def get_report_types():
    """Return available report types."""
    return {"types": list_report_types()}


@router.get("/reports/{job_id}/review")
def get_report_review(job_id: str):
    """Return sections + evaluations for a completed report."""
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
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(404, "Job not found")

    spec = get_field_spec_v3(section_key)
    if not spec:
        raise HTTPException(404, f"Unknown section: {section_key}")

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
    hint: Optional[str] = None


@router.post("/reports/{job_id}/sections/{section_key}/regenerate")
def regenerate_section(job_id: str, section_key: str, body: RegenerateRequest):
    """Regenerate a single section with optional hint."""
    from core.generate import build_prompt, ollama_generate, sanitize_output, truncate_lines, truncate_chars
    from core.context import build_index
    from core.llm_router import LLMConfig

    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(404, "Job not found")

    spec = get_field_spec_v3(section_key)
    if not spec:
        raise HTTPException(404, f"Unknown section: {section_key}")

    meta = job.meta or {}

    # Retrieve stored extracted payload
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
    import tempfile

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
