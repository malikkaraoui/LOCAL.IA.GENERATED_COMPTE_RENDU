from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def test_orchestrator_auto_ingest_audio_creates_transcripts(monkeypatch, tmp_path: Path):
    """Non-régression: un rapport ne doit pas exiger une ingestion manuelle.

    Si des audios existent et qu'aucun manifest n'existe encore dans
    CLIENTS/<client>/sources/ingested_audio, l'orchestrateur doit appeler
    l'ingestion audio (idempotente) avant l'extraction.
    """

    # Import local pour éviter de charger tout le worker dans le module global
    from backend.workers.orchestrator import ReportOrchestrator, ReportGenerationParams

    client_dir = tmp_path / "CLIENTS" / "DEMO"
    (client_dir / "sources" / "ingested_audio").mkdir(parents=True, exist_ok=True)

    # Audio factice (pas besoin d'un vrai fichier audio: on patch ingest_audio_file)
    audio_path = client_dir / "audios" / "note.m4a"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"FAKEAUDIO")

    # Un document texte exploitable, sinon l'extraction échouerait
    doc_path = client_dir / "doc.txt"
    doc_path.write_text("hello", encoding="utf-8")

    # Patch deps audio -> OK
    monkeypatch.setattr("backend.workers.orchestrator.shutil.which", lambda name: "/usr/bin/" + name)

    # Patch import faster_whisper dans _audio_deps_ok(): on injecte un module factice
    import sys

    class _FakeFW:  # pragma: no cover
        pass

    sys.modules["faster_whisper"] = _FakeFW()  # type: ignore

    calls: list[dict[str, Any]] = []

    def fake_ingest_audio_file(audio_path_str: str, source_id: str, extra_metadata=None):
        calls.append({"audio_path": audio_path_str, "source_id": source_id, "extra_metadata": extra_metadata or {}})
        out_dir = client_dir / "sources" / "ingested_audio"
        # Simuler la production des artefacts attendus
        (out_dir / "note_20250101_000000.txt").write_text("transcript", encoding="utf-8")
        (out_dir / "note_20250101_000000.json").write_text(
            json.dumps({"audio_path": audio_path_str, "source_id": source_id}, ensure_ascii=False),
            encoding="utf-8",
        )
        return {"status": "success"}

    monkeypatch.setattr("script_ai.rag.ingest_audio.ingest_audio_file", fake_ingest_audio_file)

    params = ReportGenerationParams(
        client_dir=client_dir,
        template_path=tmp_path / "tpl.docx",
        output_path=tmp_path / "out.docx",
        auto_ingest_audio=True,
        max_audio_ingest_files=10,
    )

    orch = ReportOrchestrator(params, progress_callback=None)
    orch.temp_dir = tmp_path / "tmp"
    orch.temp_dir.mkdir(parents=True, exist_ok=True)

    extracted_path = orch._extract_sources()

    assert extracted_path.exists()
    assert len(calls) == 1
    assert calls[0]["source_id"] == "DEMO"
    # Artefacts présents
    out_dir = client_dir / "sources" / "ingested_audio"
    assert any(out_dir.glob("*.txt"))
    assert any(out_dir.glob("*.json"))
