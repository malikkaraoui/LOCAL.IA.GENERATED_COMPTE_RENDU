"""STT local via faster-whisper.

Objectif:
- Charger le modèle Whisper une seule fois (cache/singleton)
- Transcrire un fichier audio en français (sans traduction, sans diarization)
- Retourner des segments {start,end,text}

Notes:
- faster-whisper peut télécharger le modèle au premier lancement.
- On force un dossier de cache contrôlé via `download_root`.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AudioTranscriptionError(RuntimeError):
    """Erreur générique de transcription audio."""


class AudioFileNotFoundError(AudioTranscriptionError):
    """Fichier audio introuvable."""


class FFmpegNotFoundError(AudioTranscriptionError):
    """ffmpeg/ffprobe manquant (décodage/probing audio)."""


class AudioTooLongError(AudioTranscriptionError):
    """Audio trop long selon la configuration."""


class AudioDecodeError(AudioTranscriptionError):
    """Audio illisible/corrompu/format non supporté."""


def _project_root() -> Path:
    # Ancrage au root du projet (même logique que backend/config.py).
    try:
        from backend.config import PROJECT_ROOT  # type: ignore

        return PROJECT_ROOT
    except Exception:
        return Path(__file__).resolve().parents[2]


def _default_model_cache_dir() -> Path:
    env = (os.getenv("AUDIO_MODEL_CACHE_DIR") or "").strip()
    if env:
        return Path(env).expanduser().resolve()

    # Fallback contrôlé dans le repo.
    try:
        from backend.config import settings  # type: ignore

        return Path(settings.AUDIO_MODEL_CACHE_DIR).expanduser().resolve()
    except Exception:
        return (_project_root() / "data" / "models" / "whisper").resolve()


def _max_seconds() -> int:
    try:
        from backend.config import settings  # type: ignore

        return int(settings.AUDIO_MAX_SECONDS)
    except Exception:
        raw = (os.getenv("AUDIO_MAX_SECONDS") or "300").strip()
        try:
            return int(raw)
        except Exception:
            return 300


def _ensure_ffmpeg_available() -> None:
    # faster-whisper s'appuie généralement sur ffmpeg/ffprobe pour gérer les formats.
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise FFmpegNotFoundError(
            "ffmpeg/ffprobe introuvable. Sur macOS: `brew install ffmpeg` (inclut ffprobe)."
        )


def _probe_duration_seconds(audio_path: Path) -> Optional[float]:
    """Retourne la durée en secondes via ffprobe (ou None si indéterminable)."""
    _ensure_ffmpeg_available()

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(audio_path),
    ]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise FFmpegNotFoundError("ffprobe introuvable") from exc

    if proc.returncode != 0:
        # Audio illisible ou format non supporté
        err = (proc.stderr or "").strip()
        raise AudioDecodeError(f"Audio illisible (ffprobe): {err or 'erreur inconnue'}")

    try:
        payload = json.loads(proc.stdout or "{}")
        dur = payload.get("format", {}).get("duration")
        if dur is None:
            return None
        return float(dur)
    except Exception:
        return None


@lru_cache(maxsize=4)
def _get_whisper_model(model_name: str) -> Any:
    """Charge le modèle faster-whisper une seule fois (cache processus)."""
    cache_dir = _default_model_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Import lazy: évite de charger des libs lourdes au démarrage du worker.
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as exc:
        raise AudioTranscriptionError(
            "faster-whisper n'est pas disponible. Installez-le via requirements (backend/requirements.txt)."
        ) from exc

    logger.info(
        "Chargement WhisperModel: model=%s device=cpu compute_type=int8 cache_dir=%s",
        model_name,
        cache_dir,
    )

    return WhisperModel(
        model_name,
        device="cpu",
        compute_type="int8",
        download_root=str(cache_dir),
    )


def concat_segments(segments: List[Dict[str, Any]]) -> str:
    parts: list[str] = []
    for seg in segments:
        txt = str(seg.get("text") or "").strip()
        if txt:
            parts.append(txt)
    return " ".join(parts).strip()


def transcribe_audio(audio_path: str) -> List[Dict[str, Any]]:
    """Transcrit un audio en segments {start,end,text}.

    Paramètres imposés:
    - language="fr"
    - vad_filter=True
    - beam_size=5
    - device="cpu"
    - compute_type="int8"

    Raises:
        AudioFileNotFoundError, FFmpegNotFoundError, AudioTooLongError, AudioDecodeError
    """

    p = Path(audio_path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise AudioFileNotFoundError(f"Fichier audio introuvable: {p}")

    # Durée max
    max_s = _max_seconds()
    dur = _probe_duration_seconds(p)
    if dur is not None and dur > float(max_s):
        raise AudioTooLongError(f"Audio trop long: {dur:.1f}s (max {max_s}s)")

    # Modèle
    try:
        from backend.config import settings  # type: ignore

        model_name = (getattr(settings, "AUDIO_WHISPER_MODEL", None) or "small").strip() or "small"
    except Exception:
        model_name = (os.getenv("AUDIO_WHISPER_MODEL") or "small").strip() or "small"

    model = _get_whisper_model(model_name)

    try:
        segments_iter, info = model.transcribe(
            str(p),
            task="transcribe",
            language="fr",
            vad_filter=True,
            beam_size=5,
        )
        out: List[Dict[str, Any]] = []
        for seg in segments_iter:
            # seg: faster_whisper.transcribe.Segment
            text = (getattr(seg, "text", "") or "").strip()
            if not text:
                continue
            out.append(
                {
                    "start": float(getattr(seg, "start", 0.0) or 0.0),
                    "end": float(getattr(seg, "end", 0.0) or 0.0),
                    "text": text,
                }
            )
        logger.info(
            "Transcription terminée: file=%s segments=%d language=%s duration=%s",
            p.name,
            len(out),
            getattr(info, "language", "fr"),
            getattr(info, "duration", None),
        )
        return out
    except AudioTranscriptionError:
        raise
    except Exception as exc:
        # Regrouper les erreurs de décodage/transcription
        raise AudioTranscriptionError(f"Échec transcription audio: {exc}") from exc
