"""Tests pour core/knowledge_builder.py."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.knowledge_builder import (
    META_FILENAME,
    NOTE_FILENAMES,
    _classify_document,
    build_client_knowledge,
    list_knowledge_notes,
    read_knowledge_note,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_payload(docs: list[dict]) -> dict:
    return {
        "root": "/fake/client",
        "generated_at": "2026-05-25T10:00:00",
        "counts": {"ok": len(docs), "errors": 0, "skipped": 0, "total_seen": len(docs)},
        "documents": docs,
    }


def _doc(path: str, text: str, ext: str = ".pdf", sha256: str = "abc123") -> dict:
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


# ---------------------------------------------------------------------------
# Tests classification
# ---------------------------------------------------------------------------

class TestClassifyDocument:
    def test_cv_par_nom(self):
        assert _classify_document("/client/CV_Mohammed.pdf", ".pdf") == "cv"

    def test_cv_curriculum(self):
        assert _classify_document("/client/curriculum_vitae.docx", ".docx") == "cv"

    def test_lettre_motivation(self):
        assert _classify_document("/client/lettre_motivation.docx", ".docx") == "lettre"

    def test_formation(self):
        assert _classify_document("/client/attestation_formation.pdf", ".pdf") == "formation"

    def test_diplome(self):
        assert _classify_document("/client/diplome_bachelor.pdf", ".pdf") == "formation"

    def test_msg_par_extension(self):
        assert _classify_document("/client/entretien.msg", ".msg") == "msg"

    def test_audio_transcript_par_chemin(self):
        path = "/client/sources/ingested_audio/entretien_20260501.txt"
        assert _classify_document(path, ".txt") == "entretien_audio"

    def test_inconnu_retourne_autre(self):
        assert _classify_document("/client/document_divers.pdf", ".pdf") == "autre"


# ---------------------------------------------------------------------------
# Tests build_client_knowledge
# ---------------------------------------------------------------------------

class TestBuildClientKnowledge:
    def test_cree_knowledge_dir(self, tmp_path):
        payload = _make_payload([_doc(str(tmp_path / "CV.pdf"), "Curriculum vitae")])
        kdir = build_client_knowledge(tmp_path, payload)
        assert kdir.exists()
        assert kdir.name == "_knowledge"

    def test_genere_note_cv(self, tmp_path):
        payload = _make_payload([_doc(str(tmp_path / "CV.pdf"), "Expérience prof")])
        kdir = build_client_knowledge(tmp_path, payload)
        note = kdir / NOTE_FILENAMES["cv"]
        assert note.exists()
        content = note.read_text(encoding="utf-8")
        assert "Expérience prof" in content

    def test_genere_note_avec_frontmatter_yaml(self, tmp_path):
        payload = _make_payload([_doc(str(tmp_path / "CV.pdf"), "Contenu CV")])
        kdir = build_client_knowledge(tmp_path, payload)
        note = kdir / NOTE_FILENAMES["cv"]
        content = note.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "type:" in content
        assert "generated_at:" in content

    def test_genere_meta_json(self, tmp_path):
        payload = _make_payload([_doc(str(tmp_path / "CV.pdf"), "Contenu")])
        kdir = build_client_knowledge(tmp_path, payload)
        meta_path = kdir / META_FILENAME
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert "notes" in meta
        assert len(meta["notes"]) > 0

    def test_groupe_multiple_docs_meme_type(self, tmp_path):
        docs = [
            _doc(str(tmp_path / "CV_FR.pdf"), "CV Français", sha256="sha1"),
            _doc(str(tmp_path / "CV_EN.pdf"), "CV English", sha256="sha2"),
        ]
        payload = _make_payload(docs)
        kdir = build_client_knowledge(tmp_path, payload)
        note = kdir / NOTE_FILENAMES["cv"]
        content = note.read_text(encoding="utf-8")
        assert "CV Français" in content
        assert "CV English" in content

    def test_types_multiples_genere_plusieurs_notes(self, tmp_path):
        docs = [
            _doc(str(tmp_path / "CV.pdf"), "CV contenu"),
            _doc(str(tmp_path / "Lettre_motivation.docx"), "Lettre contenu", ext=".docx"),
        ]
        payload = _make_payload(docs)
        kdir = build_client_knowledge(tmp_path, payload)
        assert (kdir / NOTE_FILENAMES["cv"]).exists()
        assert (kdir / NOTE_FILENAMES["lettre"]).exists()

    def test_skip_doc_sans_texte(self, tmp_path):
        docs = [
            _doc(str(tmp_path / "CV.pdf"), "Contenu CV"),
            _doc(str(tmp_path / "vide.pdf"), ""),  # texte vide
        ]
        payload = _make_payload(docs)
        kdir = build_client_knowledge(tmp_path, payload)
        # Note cv doit exister, mais vide.pdf ne génère pas de note
        assert (kdir / NOTE_FILENAMES["cv"]).exists()

    def test_skip_doc_avec_erreur(self, tmp_path):
        docs = [_doc(str(tmp_path / "CV.pdf"), "Contenu", sha256="sha1")]
        docs[0]["error"] = "Échec extraction"
        docs[0]["text"] = ""
        payload = _make_payload(docs)
        kdir = build_client_knowledge(tmp_path, payload)
        # Aucune note ne doit être créée
        notes = list_knowledge_notes(kdir)
        assert len(notes) == 0

    def test_payload_vide_retourne_knowledge_dir(self, tmp_path):
        payload = _make_payload([])
        kdir = build_client_knowledge(tmp_path, payload)
        assert kdir.exists()

    def test_cache_incremental_skip_si_sha256_inchange(self, tmp_path):
        payload = _make_payload([_doc(str(tmp_path / "CV.pdf"), "Contenu original", sha256="fixed_sha")])
        kdir = build_client_knowledge(tmp_path, payload)
        note_path = kdir / NOTE_FILENAMES["cv"]
        mtime_1 = note_path.stat().st_mtime

        # Même SHA256 → ne doit pas réécrire
        import time; time.sleep(0.01)
        build_client_knowledge(tmp_path, payload)
        mtime_2 = note_path.stat().st_mtime
        assert mtime_1 == mtime_2, "Note réécrite alors que SHA256 inchangé"

    def test_force_rebuild_recree_note(self, tmp_path):
        payload = _make_payload([_doc(str(tmp_path / "CV.pdf"), "Contenu original", sha256="fixed_sha")])
        kdir = build_client_knowledge(tmp_path, payload)
        note_path = kdir / NOTE_FILENAMES["cv"]
        mtime_1 = note_path.stat().st_mtime

        import time; time.sleep(0.05)
        build_client_knowledge(tmp_path, payload, force_rebuild=True)
        mtime_2 = note_path.stat().st_mtime
        assert mtime_2 >= mtime_1, "force_rebuild doit toujours réécrire"

    def test_rebuild_si_sha256_change(self, tmp_path):
        payload_v1 = _make_payload([_doc(str(tmp_path / "CV.pdf"), "Contenu V1", sha256="sha_v1")])
        kdir = build_client_knowledge(tmp_path, payload_v1)
        note_path = kdir / NOTE_FILENAMES["cv"]
        assert "Contenu V1" in note_path.read_text(encoding="utf-8")

        payload_v2 = _make_payload([_doc(str(tmp_path / "CV.pdf"), "Contenu V2", sha256="sha_v2")])
        build_client_knowledge(tmp_path, payload_v2)
        assert "Contenu V2" in note_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests list_knowledge_notes / read_knowledge_note
# ---------------------------------------------------------------------------

class TestListAndRead:
    def test_list_retourne_notes_md(self, tmp_path):
        kdir = tmp_path / "_knowledge"
        kdir.mkdir()
        (kdir / "01-cv.md").write_text("# CV", encoding="utf-8")
        (kdir / "02-lettre.md").write_text("# Lettre", encoding="utf-8")
        (kdir / "_meta.json").write_text("{}", encoding="utf-8")
        notes = list_knowledge_notes(kdir)
        assert len(notes) == 2
        assert all(n.suffix == ".md" for n in notes)

    def test_list_exclut_fichiers_underscore(self, tmp_path):
        kdir = tmp_path / "_knowledge"
        kdir.mkdir()
        (kdir / "_meta.json").write_text("{}", encoding="utf-8")
        (kdir / "_index.md").write_text("# Index", encoding="utf-8")
        (kdir / "01-cv.md").write_text("# CV", encoding="utf-8")
        notes = list_knowledge_notes(kdir)
        assert len(notes) == 1

    def test_read_supprime_frontmatter(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text("---\ntype: cv\n---\n\n# Contenu\nTexte ici", encoding="utf-8")
        content = read_knowledge_note(note, strip_frontmatter=True)
        assert "---" not in content
        assert "Contenu" in content

    def test_read_sans_suppression_frontmatter(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text("---\ntype: cv\n---\n\nTexte", encoding="utf-8")
        content = read_knowledge_note(note, strip_frontmatter=False)
        assert "---" in content

    def test_read_fichier_inexistant_retourne_vide(self, tmp_path):
        content = read_knowledge_note(tmp_path / "inexistant.md")
        assert content == ""
