from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import Callable

from openai import OpenAI

from voice.recorder import MicrophoneRecorder, RecordingError
from voice.transcriber import SpeechToText
from voice.tts import TextToSpeechProvider, build_tts_provider


class VoiceEngine:
    """High level helper bundling recording, transcription and speech synthesis."""

    def __init__(
        self,
        *,
        recorder: MicrophoneRecorder | None = None,
        client: OpenAI | None = None,
        on_recording_state: Callable[[str], None] | None = None,
    ) -> None:
        self._client = client or OpenAI()
        self._tts_model_name = os.getenv("TTS_MODEL", "legacy")
        self._tts: TextToSpeechProvider = build_tts_provider(
            self._tts_model_name, self._client
        )
        self._recorder = recorder or MicrophoneRecorder()
        self._transcriber = SpeechToText(self._client)
        self._temp_dir = Path(tempfile.gettempdir()) / "pygame_ai_voice"
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._on_recording_state = on_recording_state

    def record(self, duration: float = 4.0) -> Path:
        audio_path = self._temp_dir / f"recording_{uuid.uuid4().hex}.wav"
        self._recorder.record(audio_path, duration, self._on_recording_state)
        return audio_path

    def transcribe(self, audio_path: Path) -> str:
        return self._transcriber.transcribe(audio_path)

    def record_and_transcribe(self, duration: float = 4.0) -> str:
        audio_path = self.record(duration)
        try:
            return self.transcribe(audio_path)
        finally:
            audio_path.unlink(missing_ok=True)

    def synthesize(self, text: str) -> Path:
        if not text.strip():
            raise ValueError("Cannot synthesize empty text")
        output_path = self._temp_dir / f"tts_{uuid.uuid4().hex}.mp3"
        self._tts.synthesize(text, output_path)
        return output_path

    def cleanup(self) -> None:
        for file in self._temp_dir.glob("*.mp3"):
            file.unlink(missing_ok=True)
        for file in self._temp_dir.glob("*.wav"):
            file.unlink(missing_ok=True)

    @property
    def recorder(self) -> MicrophoneRecorder:
        return self._recorder

    @property
    def client(self) -> OpenAI:
        return self._client

    @property
    def tts_model(self) -> str:
        return self._tts_model_name


__all__ = ["VoiceEngine", "RecordingError"]
