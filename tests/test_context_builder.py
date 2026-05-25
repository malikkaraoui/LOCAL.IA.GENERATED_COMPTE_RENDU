"""Tests pour core/context_builder.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.context_builder import (
    _load_qmd_template,
    _render_qmd,
    _select_notes,
    _trim_to_max_chars,
    build_flat_context,
    build_section_context,
)
from core.knowledge_builder import build_client_knowledge


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_payload(docs: list[dict]) -> dict:
    return {
        "root": "/fake/client",
        "generated_at": "2026-05-25T10:00:00",
        "counts": {"ok": len(docs)},
        "documents": docs,
    }


def _doc(path: str, text: str, sha256: str = "abc123") -> dict:
    ext = Path(path).suffix.lower()
    return {
        "path": path,
        "ext": ext,
        "text": text,
        "text_sha256": sha256,
        "mtime_iso": "2026-05-25T09:00:00",
        "size_bytes": len(text.encode()),
        "extractor": "test",
        "pages": None,
        "error": None,
    }


def _build_kdir(tmp_path: Path, docs: list[dict]) -> Path:
    """Construit un _knowledge/ dans tmp_path et retourne son chemin."""
    payload = _make_payload(docs)
    return build_client_knowledge(tmp_path, payload)


# ---------------------------------------------------------------------------
# Tests _render_qmd
# ---------------------------------------------------------------------------

class TestRenderQmd:
    def test_remplace_variable_simple(self):
        tpl = "Section : {{section_key}}"
        result = _render_qmd(tpl, {"section_key": "PROFESSION"})
        assert result == "Section : PROFESSION"

    def test_remplace_plusieurs_variables(self):
        tpl = "{{a}} et {{b}}"
        result = _render_qmd(tpl, {"a": "un", "b": "deux"})
        assert result == "un et deux"

    def test_variable_absente_reste_intact(self):
        tpl = "{{inconnu}}"
        result = _render_qmd(tpl, {})
        assert result == "{{inconnu}}"

    def test_variable_vide(self):
        tpl = "X{{v}}Y"
        result = _render_qmd(tpl, {"v": ""})
        assert result == "XY"


# ---------------------------------------------------------------------------
# Tests _trim_to_max_chars
# ---------------------------------------------------------------------------

class TestTrimToMaxChars:
    def test_sans_troncature_si_sous_limite(self):
        text = "Court texte."
        assert _trim_to_max_chars(text, 1000) == "Court texte."

    def test_coupe_a_la_limite(self):
        text = "A" * 500
        result = _trim_to_max_chars(text, 100)
        assert len(result) <= 100

    def test_vide_retourne_vide(self):
        assert _trim_to_max_chars("", 100) == ""


# ---------------------------------------------------------------------------
# Tests _load_qmd_template
# ---------------------------------------------------------------------------

class TestLoadQmdTemplate:
    def test_charge_template_section_specifique(self):
        tpl = _load_qmd_template("PROFESSION")
        assert "PROFESSION" in tpl

    def test_fallback_base_si_section_inconnue(self):
        tpl = _load_qmd_template("SECTION_INEXISTANTE_XYZ")
        # Doit retourner quelque chose (base ou inline fallback)
        assert len(tpl) > 0

    def test_template_contient_placeholder_notes_content(self):
        tpl = _load_qmd_template("PROFESSION")
        assert "{{notes_content}}" in tpl


# ---------------------------------------------------------------------------
# Tests _select_notes
# ---------------------------------------------------------------------------

class TestSelectNotes:
    def test_retourne_notes_dans_ordre_priorite(self, tmp_path):
        docs = [
            _doc(str(tmp_path / "CV.pdf"), "CV contenu"),
            _doc(str(tmp_path / "entretien.msg"), "Email contenu"),
        ]
        kdir = _build_kdir(tmp_path, docs)
        notes = _select_notes(kdir, "PROFESSION")
        names = [n.name for n in notes]
        # CV (01-cv.md) doit être avant msg (05-messages.md) pour PROFESSION
        assert names.index("01-cv.md") < names.index("05-messages.md")

    def test_retourne_toutes_notes_si_section_inconnue(self, tmp_path):
        docs = [
            _doc(str(tmp_path / "CV.pdf"), "CV"),
            _doc(str(tmp_path / "Lettre.docx"), "Lettre", sha256="l1"),
        ]
        kdir = _build_kdir(tmp_path, docs)
        notes = _select_notes(kdir, "SECTION_INCONNUE")
        assert len(notes) == 2

    def test_knowledge_dir_absent_retourne_liste_vide(self, tmp_path):
        absent = tmp_path / "absent_kdir"
        notes = _select_notes(absent, "PROFESSION")
        assert notes == []


# ---------------------------------------------------------------------------
# Tests build_section_context
# ---------------------------------------------------------------------------

class TestBuildSectionContext:
    def test_retourne_chaine_non_vide_si_notes_presentes(self, tmp_path):
        docs = [_doc(str(tmp_path / "CV.pdf"), "Ingénieur logiciel 10 ans expérience")]
        kdir = _build_kdir(tmp_path, docs)
        ctx = build_section_context(kdir, "PROFESSION")
        assert len(ctx) > 0

    def test_contenu_note_present_dans_contexte(self, tmp_path):
        docs = [_doc(str(tmp_path / "CV.pdf"), "Ingénieur logiciel 10 ans expérience")]
        kdir = _build_kdir(tmp_path, docs)
        ctx = build_section_context(kdir, "PROFESSION")
        assert "Ingénieur logiciel" in ctx

    def test_retourne_vide_si_knowledge_dir_absent(self, tmp_path):
        absent = tmp_path / "absent"
        ctx = build_section_context(absent, "PROFESSION")
        assert ctx == ""

    def test_respecte_max_chars(self, tmp_path):
        long_text = "X" * 10000
        docs = [_doc(str(tmp_path / "CV.pdf"), long_text)]
        kdir = _build_kdir(tmp_path, docs)
        ctx = build_section_context(kdir, "PROFESSION", max_chars=500)
        assert len(ctx) <= 500

    def test_section_key_dans_contexte(self, tmp_path):
        docs = [_doc(str(tmp_path / "CV.pdf"), "Contenu CV")]
        kdir = _build_kdir(tmp_path, docs)
        ctx = build_section_context(kdir, "FORMATION", client_name="Jean Dupont")
        assert "FORMATION" in ctx

    def test_retourne_vide_si_aucune_note(self, tmp_path):
        kdir = tmp_path / "_knowledge"
        kdir.mkdir()
        ctx = build_section_context(kdir, "PROFESSION")
        assert ctx == ""


# ---------------------------------------------------------------------------
# Tests build_flat_context
# ---------------------------------------------------------------------------

class TestBuildFlatContext:
    def test_concatène_toutes_notes(self, tmp_path):
        docs = [
            _doc(str(tmp_path / "CV.pdf"), "CV contenu unique"),
            _doc(str(tmp_path / "Lettre.docx"), "Lettre contenu unique", sha256="l1"),
        ]
        kdir = _build_kdir(tmp_path, docs)
        ctx = build_flat_context(kdir)
        assert "CV contenu unique" in ctx
        assert "Lettre contenu unique" in ctx

    def test_retourne_vide_si_knowledge_dir_absent(self, tmp_path):
        ctx = build_flat_context(tmp_path / "absent")
        assert ctx == ""
