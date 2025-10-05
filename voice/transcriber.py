from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI


class SpeechToText:
    """Wrapper around OpenAI transcription APIs."""

    def __init__(self, client: OpenAI, model_name: str | None = None) -> None:
        self._client = client
        self._model = model_name or os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1")

    def transcribe(self, audio_path: Path) -> str:
        if not audio_path.exists():
            raise FileNotFoundError(audio_path)
        with audio_path.open("rb") as audio_file:
            response = self._client.audio.transcriptions.create(
                model=self._model,
                file=audio_file,
            )
        text = getattr(response, "text", "")
        return text.strip()
