from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

from openai import OpenAI

try:
    from elevenlabs.client import ElevenLabs  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    ElevenLabs = None


class TextToSpeechProvider(ABC):
    """Simple interface for pluggable TTS backends."""

    @abstractmethod
    def synthesize(self, text: str, destination: Path) -> None:
        """Generate speech audio for the given text."""


class LegacyOpenAITTS(TextToSpeechProvider):
    """Uses the legacy OpenAI text-to-speech endpoint."""

    def __init__(self, client: OpenAI) -> None:
        self._client = client
        self._model = os.getenv("OPENAI_TTS_MODEL", "tts-1")
        self._voice = os.getenv("OPENAI_TTS_VOICE", "nova")

    def synthesize(self, text: str, destination: Path) -> None:
        response = self._client.audio.speech.create(
            model=self._model,
            voice=self._voice,
            input=text,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        response.stream_to_file(str(destination))


class ElevenLabsTTS(TextToSpeechProvider):
    """Thin wrapper around the ElevenLabs TTS API."""

    def __init__(self) -> None:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ELEVENLABS_API_KEY is not set. Provide it in the environment or .env file."
            )

        voice_id = os.getenv("ELEVENLABS_VOICE_ID")
        if not voice_id:
            raise EnvironmentError(
                "ELEVENLABS_VOICE_ID is required when using the ElevenLabs TTS model."
            )

        if ElevenLabs is None:
            raise ImportError("The 'elevenlabs' package is required for ElevenLabs TTS support.")

        self._model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
        self._output_format = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
        self._voice_id = voice_id
        self._client = ElevenLabs(api_key=api_key)

    def synthesize(self, text: str, destination: Path) -> None:
        audio_stream: Iterable[bytes] = self._client.text_to_speech.convert(
            text=text,
            voice_id=self._voice_id,
            model_id=self._model_id,
            output_format=self._output_format,
        )

        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as audio_file:
            for chunk in audio_stream:
                if isinstance(chunk, bytes):
                    audio_file.write(chunk)
                else:
                    audio_file.write(chunk.encode("utf-8"))


def build_tts_provider(model_name: str, client: OpenAI) -> TextToSpeechProvider:
    normalized = model_name.strip().lower()
    if normalized == "legacy":
        return LegacyOpenAITTS(client)
    if normalized == "elevenlabs":
        return ElevenLabsTTS()
    raise ValueError(
        "Unsupported TTS_MODEL '{model_name}'. Choose 'legacy' or 'elevenlabs'.".format(
            model_name=model_name
        )
    )
