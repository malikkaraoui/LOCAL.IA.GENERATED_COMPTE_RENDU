from __future__ import annotations

import json
from pathlib import Path

from core.avs import detect_avs_number


def test_orchestrator_falls_back_when_sources_only_has_ingested_audio(tmp_path: Path):
    """Non-régression: ne pas ignorer les vrais documents du client.

    Contexte bug: si CLIENTS/<client>/sources existe mais ne contient que
    sources/ingested_audio (transcriptions), l'orchestrateur scannait uniquement
    sources/ et passait à côté des PDF/DOCX/TXT rangés dans 01/03/04/05…

    Attendu: fallback immédiat vers le dossier client + AVS détectable.
    """

    # Import local pour éviter les effets de bord au chargement du module
    from backend.workers.orchestrator import ReportOrchestrator, ReportGenerationParams

    client_dir = tmp_path / "CLIENTS" / "DEMO"

    # Créer sources/ingested_audio avec une transcription (mais aucune source "principale")
    ingested_dir = client_dir / "sources" / "ingested_audio"
    ingested_dir.mkdir(parents=True, exist_ok=True)
    (ingested_dir / "t1.txt").write_text("transcript only", encoding="utf-8")

    # Le vrai document contenant l'AVS est ailleurs dans l'arborescence client
    real_docs_dir = client_dir / "03 Tests et bilans"
    real_docs_dir.mkdir(parents=True, exist_ok=True)
    (real_docs_dir / "bilan.txt").write_text(
        "Le numéro AVS du candidat est 756.1234.5678.90\n",
        encoding="utf-8",
    )

    params = ReportGenerationParams(
        client_dir=client_dir,
        template_path=tmp_path / "tpl.docx",
        output_path=tmp_path / "out.docx",
        auto_ingest_audio=False,  # pas besoin ici
    )

    orch = ReportOrchestrator(params, progress_callback=None)
    orch.temp_dir = tmp_path / "tmp"
    orch.temp_dir.mkdir(parents=True, exist_ok=True)

    extracted_path = orch._extract_sources()

    payload = json.loads(extracted_path.read_text(encoding="utf-8"))

    # ✅ Le dossier scanné doit être le dossier client (pas sources/)
    assert payload["metadata"]["source_dir"] == str(client_dir)

    # ✅ Et l'AVS doit être détectable dans le payload extrait
    assert detect_avs_number(payload) == "756.1234.5678.90"
