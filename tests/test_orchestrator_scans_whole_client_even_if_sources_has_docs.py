from __future__ import annotations

import json
from pathlib import Path

from core.avs import detect_avs_number


def test_orchestrator_scans_whole_client_even_if_sources_has_docs(tmp_path: Path):
    """Non-régression: toujours scanner tout le dossier client.

    Contexte: si `CLIENTS/<client>/sources` existe et contient des fichiers,
    l'ancienne logique privilégiait `sources/` et ignorait des docs rangés
    ailleurs (01/03/04/05/...), ce qui pouvait faire louper l'AVS.

    Attendu: `source_dir` == dossier client et AVS détectable depuis un fichier
    hors `sources/`.
    """

    from backend.workers.orchestrator import ReportOrchestrator, ReportGenerationParams

    client_dir = tmp_path / "CLIENTS" / "DEMO"
    (client_dir / "sources").mkdir(parents=True, exist_ok=True)

    # Un "vrai" document dans sources/
    (client_dir / "sources" / "note.txt").write_text(
        "Note dans sources (ne doit pas empêcher de scanner le reste).\n",
        encoding="utf-8",
    )

    # Document critique (AVS) ailleurs dans l'arborescence
    real_docs_dir = client_dir / "03 Tests et bilans"
    real_docs_dir.mkdir(parents=True, exist_ok=True)
    (real_docs_dir / "bilan.txt").write_text(
        "Le numéro AVS du candidat est 756 1234 5678 90\n",
        encoding="utf-8",
    )

    params = ReportGenerationParams(
        client_dir=client_dir,
        template_path=tmp_path / "tpl.docx",
        output_path=tmp_path / "out.docx",
        auto_ingest_audio=False,
    )

    orch = ReportOrchestrator(params, progress_callback=None)
    orch.temp_dir = tmp_path / "tmp"
    orch.temp_dir.mkdir(parents=True, exist_ok=True)

    extracted_path = orch._extract_sources()
    payload = json.loads(extracted_path.read_text(encoding="utf-8"))

    assert payload["metadata"]["source_dir"] == str(client_dir)
    assert detect_avs_number(payload) == "756.1234.5678.90"
