import os
import wave
from pathlib import Path

import pytest


def test_import_stt_module():
    # Le module doit être importable sans exécuter de transcription.
    from script_ai.audio import stt_faster_whisper  # noqa: F401


def test_transcribe_audio_missing_file(tmp_path: Path):
    from script_ai.audio.stt_faster_whisper import AudioFileNotFoundError, transcribe_audio

    missing = tmp_path / "missing.wav"
    with pytest.raises(AudioFileNotFoundError):
        transcribe_audio(str(missing))


@pytest.mark.integration
def test_transcribe_audio_returns_list_when_enabled(tmp_path: Path):
    """Test d'intégration optionnel.

    Ce test est **désactivé par défaut** pour éviter:
    - un téléchargement de modèle en CI
    - une dépendance forte à ffmpeg

    Pour l'activer:
      RUN_AUDIO_STT_TESTS=1 pytest -m integration
    """

    if os.getenv("RUN_AUDIO_STT_TESTS") != "1":
        pytest.skip("RUN_AUDIO_STT_TESTS != 1")

    # Générer un wav très court (silence) pour valider le plumbing.
    wav_path = tmp_path / "silence.wav"
    framerate = 16000
    duration_s = 1
    nframes = framerate * duration_s

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(framerate)
        wf.writeframes(b"\x00\x00" * nframes)

    from script_ai.audio.stt_faster_whisper import transcribe_audio

    segments = transcribe_audio(str(wav_path))
    assert isinstance(segments, list)
