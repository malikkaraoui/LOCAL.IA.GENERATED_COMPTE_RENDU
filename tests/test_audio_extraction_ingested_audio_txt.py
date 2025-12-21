from pathlib import Path


def test_extractor_supports_txt_in_nested_sources(tmp_path: Path):
    """Valide la promesse: sources/ingested_audio/*.txt est bien extractible.

    Le pipeline backend choisit `client_dir/sources` si présent, et `walk_files` utilise rglob,
    donc les sous-dossiers (dont ingested_audio) sont inclus.
    """

    client_sources = tmp_path / "CLIENTS" / "DEMO" / "sources" / "ingested_audio"
    client_sources.mkdir(parents=True, exist_ok=True)

    p = client_sources / "note.txt"
    p.write_text("Bonjour\n\nCeci est une transcription.", encoding="utf-8")

    from extract_sources import extract_one, walk_files

    files = walk_files(tmp_path / "CLIENTS" / "DEMO" / "sources")
    assert p in files

    doc = extract_one(p, enable_soffice=False)
    assert doc.error is None
    assert doc.ext == ".txt"
    assert "transcription" in doc.text.lower()
