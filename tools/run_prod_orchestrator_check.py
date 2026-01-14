from __future__ import annotations

import json
import logging
import re
from pathlib import Path
import sys

# Permet d'exécuter ce script depuis tools/ (sys.path[0]=tools) tout en important backend/core.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def mask_avs(value: str) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if len(digits) == 13 and digits.startswith("756"):
        return f"{digits[:3]}.XXXX.XXXX.XX"
    return "<NOT_AN_AVS>"


def find_avs_value(obj):
    """Return the first value associated with NUMERO_AVS in common JSON shapes."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k)
            if key in {"NUMERO_AVS", "{{NUMERO_AVS}}"} or key.strip("{} ") == "NUMERO_AVS":
                # Shape A: direct string value
                if isinstance(v, str) and v:
                    return v
                # Shape B: nested object with common fields
                if isinstance(v, dict):
                    for subkey in ("value", "text", "answer", "output", "result"):
                        sv = v.get(subkey)
                        if isinstance(sv, str) and sv:
                            return sv
            found = find_avs_value(v)
            if found:
                return found
    elif isinstance(obj, list):
        for it in obj:
            found = find_avs_value(it)
            if found:
                return found
    return None


def main() -> int:
    # Afficher une progression utile sans exposer de PII
    logging.basicConfig(level=logging.INFO)

    from backend.workers.orchestrator import ReportOrchestrator, ReportGenerationParams
    from core.llm_router import LLMConfig

    root = Path.cwd()
    client_dir = root / "CLIENTS" / "KARAOUI Malik"
    template_path = root / "uploaded_templates" / "TEMPLATE_SIMPLE_BASE1.docx"
    output_path = client_dir / "output_final" / "rapport_prod_check.docx"

    if not client_dir.exists():
        print("client_dir missing:", client_dir)
        return 2
    if not template_path.exists():
        print("template missing:", template_path)
        return 2

    params = ReportGenerationParams(
        client_dir=client_dir,
        template_path=template_path,
        output_path=output_path,
        llm_host="http://localhost:11434",
        llm_model="qwen3:8b",
        temperature=0.2,
        topk=10,
        top_p=0.9,
        # Réduire la quantité de contexte injectée pour accélérer (sans changer la logique AVS)
        max_chars_multiplier=0.7,
        auto_ingest_audio=False,
        # Config unifiée (prioritaire) pour limiter la génération et accélérer
        llm_config=LLMConfig.from_legacy(
            model="qwen3:8b",
            host="http://localhost:11434",
            temperature=0.2,
            top_p=0.9,
            max_tokens=512,
            timeout=900.0,
        ),
    )

    def progress_cb(payload: dict) -> None:
        # Payload typique: {status,message,progress,...}
        status = payload.get("status")
        msg = payload.get("message")
        prog = payload.get("progress")
        if prog is None:
            print(f"[{status}] {msg}")
        else:
            try:
                pct = int(float(prog) * 100)
                print(f"[{status} {pct:02d}%] {msg}")
            except Exception:
                print(f"[{status}] {msg}")

    orch = ReportOrchestrator(params, progress_callback=progress_cb)
    res = orch.run()

    print("status:", res.get("status"))
    print("output_path:", res.get("output_path"))

    if res.get("status") != "success":
        print("error:", res.get("error"))
        return 1

    answers_path = Path(res["temp_files"]["answers"])
    answers = json.loads(answers_path.read_text(encoding="utf-8"))

    avs_in_answers = find_avs_value(answers)
    print("answers.NUMERO_AVS:", "<FOUND>" if avs_in_answers else "<NOT FOUND>")
    if avs_in_answers:
        print("answers.NUMERO_AVS (masked):", mask_avs(avs_in_answers))

    # Vérif dans le docx final (sans afficher le numéro)
    from docx import Document

    doc = Document(str(output_path))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    pattern = re.compile(r"756(?:[ .\-]?\d){10}")
    m = pattern.search(full_text)
    print("docx contains AVS pattern:", bool(m))
    if m:
        print("docx AVS (masked):", mask_avs(m.group(0)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
