"""Ingestion RAG d'un fichier audio (STT local -> chunks -> pipeline).

Contrat demandé:
- ingest_audio_file(audio_path, source_id, extra_metadata={})

Stratégie d'intégration avec le projet actuel:
- Le pipeline de génération construit son contexte RAG depuis les fichiers présents
  sous `CLIENTS/<client>/sources/` (si ce dossier existe) ou directement dans le dossier
  client.
- Donc, on "ingère" l'audio en produisant un fichier .txt (transcription chunkée)
  + un manifest .json (segments, timestamps) dans:
    CLIENTS/<source_id>/sources/ingested_audio/
  (si ce client existe), sinon dans `data/rag_audio/<source_id>/`.

Ainsi, aucune dépendance cloud, et la transcription devient une source RAG comme les autres.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from script_ai.audio.stt_faster_whisper import concat_segments, transcribe_audio

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioChunk:
    start: float
    end: float
    text: str


def _safe_stem(name: str, default: str = "audio") -> str:
    raw = (name or "").strip()
    if not raw:
        return default
    raw = Path(raw).stem
    raw = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw).strip("_")
    return raw or default


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _coerce_metadata(extra_metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return dict(extra_metadata or {})


def _default_clients_dir() -> Path:
    try:
        from backend.config import settings  # type: ignore

        return Path(settings.CLIENTS_DIR).expanduser().resolve()
    except Exception:
        return (Path(__file__).resolve().parents[2] / "CLIENTS").resolve()


def _fallback_ingest_root() -> Path:
    try:
        from backend.config import PROJECT_ROOT  # type: ignore

        return (Path(PROJECT_ROOT) / "data" / "rag_audio").resolve()
    except Exception:
        return (Path(__file__).resolve().parents[2] / "data" / "rag_audio").resolve()


def _window_segments(
    segments: List[Dict[str, Any]],
    *,
    target_seconds: float = 40.0,
    max_seconds: float = 45.0,
    gap_split_seconds: float = 2.0,
) -> List[AudioChunk]:
    """Regroupe des segments Whisper en fenêtres ~30-45s (préféré).

    Heuristique:
    - On accumule jusqu'à atteindre target_seconds.
    - On coupe si on dépasse max_seconds.
    - On coupe aussi si un grand silence/gap est détecté.
    """

    chunks: List[AudioChunk] = []
    cur_text: List[str] = []
    win_start: Optional[float] = None
    win_end: Optional[float] = None
    last_end: Optional[float] = None

    def flush() -> None:
        nonlocal cur_text, win_start, win_end, last_end
        if win_start is None or win_end is None:
            cur_text = []
            win_start = None
            win_end = None
            last_end = None
            return
        text = " ".join(t.strip() for t in cur_text if t.strip()).strip()
        if text:
            chunks.append(AudioChunk(start=float(win_start), end=float(win_end), text=text))
        cur_text = []
        win_start = None
        win_end = None
        last_end = None

    for seg in segments:
        start = float(seg.get("start") or 0.0)
        end = float(seg.get("end") or 0.0)
        text = str(seg.get("text") or "").strip()
        if not text:
            continue

        if win_start is None:
            win_start = start
            win_end = end
            cur_text = [text]
            last_end = end
            continue

        # Gap (silence) important -> flush
        if last_end is not None and start - last_end >= gap_split_seconds:
            flush()
            win_start = start
            win_end = end
            cur_text = [text]
            last_end = end
            continue

        # Ajouter segment
        cur_text.append(text)
        win_end = max(win_end or end, end)
        last_end = end

        # Décider coupe
        win_len = float((win_end or 0.0) - (win_start or 0.0))
        if win_len >= max_seconds:
            flush()
        elif win_len >= target_seconds:
            flush()

    flush()
    return chunks


def _format_chunk_line(chunk: AudioChunk) -> str:
    # Éviter les ':' dans les sources (le prompt LLM impose 1 ':'/ligne et on veut éviter de perturber).
    # On utilise un format sans colon: [t=12s-40s]
    s = int(round(chunk.start))
    e = int(round(chunk.end))
    return f"[t={s}s-{e}s] {chunk.text}".strip()


def ingest_audio_file(
    audio_path: str,
    source_id: str,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Transcrit et ingère un fichier audio dans les sources RAG du projet.

    Args:
        audio_path: chemin vers le fichier audio
        source_id: identifiant de la source (dans ce repo: typiquement le nom du client)
        extra_metadata: métadonnées additionnelles (ex: tags, auteur, etc.)

    Returns:
        dict: résumé (chemins écrits, stats)
    """

    source_id = (source_id or "").strip()
    if not source_id:
        raise ValueError("source_id manquant")

    p = Path(audio_path).expanduser().resolve()

    segments = transcribe_audio(str(p))
    full_text = concat_segments(segments)

    # Fenêtres préférées ~30-45s
    chunks = _window_segments(segments)

    original_name = p.name
    safe = _safe_stem(original_name)
    ts = _now_tag()

    clients_dir = _default_clients_dir()
    client_dir = clients_dir / source_id

    extra = _coerce_metadata(extra_metadata)

    if client_dir.exists() and client_dir.is_dir():
        out_dir = client_dir / "sources" / "ingested_audio"
    else:
        out_dir = _fallback_ingest_root() / source_id

    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Fichier texte (consommable par l'extracteur)
    txt_path = out_dir / f"{safe}_{ts}.txt"
    lines: List[str] = []
    lines.append(f"Transcription audio (local) — {original_name}")
    lines.append(f"Date: {datetime.now().isoformat()}")
    lines.append(f"SourceId: {source_id}")
    lines.append("")

    if chunks:
        for ch in chunks:
            lines.append(_format_chunk_line(ch))
    else:
        # fallback: texte complet
        if full_text:
            lines.append(full_text)

    txt_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    # 2) Manifest JSON (métadonnées + segments)
    manifest_path = out_dir / f"{safe}_{ts}.json"

    payload: Dict[str, Any] = {
        "type": "audio",
        "source_id": source_id,
        "original_filename": original_name,
        "created_at": datetime.now().isoformat(),
        "audio_path": str(p),
        "transcript_text": full_text,
        "segments": segments,
        "chunks": [
            {"start": c.start, "end": c.end, "text": c.text}
            for c in chunks
        ],
        "extra_metadata": extra,
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(
        "Audio ingéré: source_id=%s audio=%s segments=%d chunks=%d out=%s",
        source_id,
        original_name,
        len(segments),
        len(chunks),
        out_dir,
    )

    return {
        "status": "success",
        "source_id": source_id,
        "original_filename": original_name,
        "segments": len(segments),
        "chunks": len(chunks),
        "output_dir": str(out_dir),
        "transcript_txt": str(txt_path),
        "manifest_json": str(manifest_path),
    }
