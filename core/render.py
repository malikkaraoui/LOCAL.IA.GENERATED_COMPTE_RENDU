"""Rendu du rapport DOCX à partir d'un template."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph


LOGGER = logging.getLogger(__name__)


def _norm(text: str) -> str:
    text = (text or "").replace("\u00a0", " ").strip().lower()
    text = text.replace(":", "")
    text = " ".join(text.split())
    return text


def _style_ok(paragraph: Paragraph, prefixes: Optional[List[str]]) -> bool:
    name = getattr(getattr(paragraph, "style", None), "name", "") or ""
    if name.startswith("TOC"):
        return False
    if not prefixes:
        return True
    return any(name.startswith(prefix) for prefix in prefixes)


def find_paragraph(
    doc: Document,
    text: str,
    *,
    after: int = 0,
    style_prefixes: Optional[List[str]] = None,
) -> tuple[Optional[int], Optional[Paragraph]]:
    target = _norm(text)
    for idx in range(after, len(doc.paragraphs)):
        p = doc.paragraphs[idx]
        if not _style_ok(p, style_prefixes):
            continue
        if _norm(p.text) == target:
            return idx, p
    return None, None


def delete_paragraph(paragraph: Paragraph) -> None:
    el = paragraph._element
    el.getparent().remove(el)


def insert_paragraph_after(paragraph: Paragraph, text: str, style_name: Optional[str]) -> Paragraph:
    new_element = OxmlElement("w:p")
    paragraph._element.addnext(new_element)
    para = Paragraph(new_element, paragraph._parent)
    if style_name:
        try:
            para.style = style_name
        except Exception:
            pass
    if text is not None:
        para.add_run(text)
    return para


def replace_text_everywhere(doc: Document, mapping: Dict[str, str]) -> None:
    def replace_in_par(par: Paragraph):
        if not mapping:
            return
        text = "".join(run.text for run in par.runs) if par.runs else par.text
        replaced = False
        for old, new in mapping.items():
            if not old or old not in text:
                continue
            text = text.replace(old, new)
            replaced = True
        if replaced:
            if par.runs:
                par.runs[0].text = text
                for r in par.runs[1:]:
                    r.text = ""
            else:
                par.text = text

    for paragraph in doc.paragraphs:
        replace_in_par(paragraph)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_in_par(paragraph)


def _stringify_answer(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        answer = value.get("value")
        if isinstance(answer, str):
            return answer.strip()
        answer = value.get("answer")
        if isinstance(answer, str):
            return answer.strip()
        if answer is None:
            return ""
        return json.dumps(answer, ensure_ascii=False)
    if value is None:
        return ""
    return str(value).strip()


def build_moustache_mapping(answers: Dict[str, Any]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for key, value in answers.items():
        text = _stringify_answer(value)
        if not text:
            continue
        placeholder = f"{{{{{key}}}}}"
        mapping[placeholder] = text
        mapping.setdefault(f"{{{{{key.lower()}}}}}", text)
    return mapping


def replace_section(
    doc: Document,
    *,
    start_text: str,
    end_text: str,
    answer_text: str,
    start_style_prefixes: Optional[List[str]] = None,
    end_style_prefixes: Optional[List[str]] = None,
) -> None:
    start_idx, start_par = find_paragraph(doc, start_text, style_prefixes=start_style_prefixes)
    if start_par is None or start_idx is None:
        raise RuntimeError(f"Section '{start_text}' introuvable")
    end_idx, end_par = find_paragraph(doc, end_text, after=start_idx + 1, style_prefixes=end_style_prefixes)
    if end_par is None or end_idx is None:
        LOGGER.warning(
            "Section fin '%s' introuvable après '%s' – insertion en fin de document.", end_text, start_text
        )
        end_idx = len(doc.paragraphs)
    between = doc.paragraphs[start_idx + 1 : end_idx]
    base_style = None
    for paragraph in between:
        if paragraph.text.strip():
            base_style = getattr(getattr(paragraph, "style", None), "name", None)
            break
    if not base_style and between:
        base_style = getattr(getattr(between[0], "style", None), "name", None)
    if not base_style:
        base_style = "Corps"
    for paragraph in list(between):
        delete_paragraph(paragraph)
    text = (answer_text or "").strip()
    if not text:
        insert_paragraph_after(start_par, "", base_style)
        return
    cursor = start_par
    for line in [ln.strip() for ln in text.splitlines() if ln.strip()]:
        if line.startswith(("- ", "* ")):
            line = "• " + line[2:].strip()
        cursor = insert_paragraph_after(cursor, line, base_style)


def render_report(
    template: Union[str, Path],
    answers: Union[Dict[str, Any], str, Path],
    output: Union[str, Path],
    *,
    name: str = "",
    surname: str = "",
    civility: str = "Monsieur",
    location_date: str = "",
) -> Path:
    template_path = Path(template).expanduser().resolve()
    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document(str(template_path))

    if isinstance(answers, (str, Path)):
        answers_dict: Dict[str, Any] = json.loads(Path(answers).expanduser().read_text(encoding="utf-8"))
    else:
        answers_dict = answers

    simple_mapping = {}
    if name:
        simple_mapping["{NAME}"] = name
        simple_mapping["{{NAME}}"] = name
        simple_mapping["{monsieur ou madame NAME}"] = f"{civility} {name}".strip()
    if surname:
        simple_mapping["{surname}"] = surname
        simple_mapping["{{SURNAME}}"] = surname
        simple_mapping["XX"] = f"{civility} {surname}".strip()
    simple_mapping["{{MONSIEUR_OU_MADAME}}"] = civility
    if location_date:
        simple_mapping["{LIEU_ET_DATE}"] = location_date
        simple_mapping["{{LIEU_ET_DATE}}"] = location_date
    if simple_mapping:
        replace_text_everywhere(doc, simple_mapping)

    moustache_mapping = build_moustache_mapping(answers_dict)
    if moustache_mapping:
        replace_text_everywhere(doc, moustache_mapping)

    def get_answer(key: str) -> str:
        value = answers_dict.get(key)
        return _stringify_answer(value)

    replace_section(
        doc,
        start_text="Profession",
        end_text="Formation",
        answer_text=get_answer("PROFESSION"),
        start_style_prefixes=["TITRE", "Heading"],
        end_style_prefixes=["TITRE", "Heading"],
    )
    replace_section(
        doc,
        start_text="Formation",
        end_text="Tests",
        answer_text=get_answer("FORMATION"),
        start_style_prefixes=["TITRE", "Heading"],
        end_style_prefixes=["Heading"],
    )
    replace_section(
        doc,
        start_text="RÉSULTATS DE LA DISCUSSION AVEC L’ASSURÉ",
        end_text="Compétences Professionnelles & Sociales",
        answer_text=get_answer("DISCUSSION_ASSURE"),
        start_style_prefixes=["TITRE", "Heading"],
        end_style_prefixes=["Heading"],
    )
    replace_section(
        doc,
        start_text="Orientation",
        end_text="Stage",
        answer_text=get_answer("ORIENTATION"),
        start_style_prefixes=["TITRE", "Heading"],
        end_style_prefixes=["TITRE", "Heading"],
    )
    replace_section(
        doc,
        start_text="Stage",
        end_text="Formation",
        answer_text=get_answer("STAGE"),
        start_style_prefixes=["TITRE", "Heading"],
        end_style_prefixes=["TITRE", "Heading"],
    )
    replace_section(
        doc,
        start_text="Conclusion",
        end_text="Lieu & Date",
        answer_text=get_answer("CONCLUSION"),
        start_style_prefixes=["Heading"],
        end_style_prefixes=None,
    )

    doc.save(str(output_path))
    return output_path
