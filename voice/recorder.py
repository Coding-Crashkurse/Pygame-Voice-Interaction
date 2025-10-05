from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable


class RecordingError(RuntimeError):
    pass


class MicrophoneRecorder:
    """Basic microphone recorder built on top of sounddevice."""

    def __init__(self, samplerate: int = 16000, channels: int = 1) -> None:
        self.samplerate = samplerate
        self.channels = channels
        self._lock = threading.Lock()
        self._recording = False

    def _ensure_dependencies(self) -> tuple[object, object, object]:
        try:
            import numpy as np  # type: ignore
            import sounddevice as sd  # type: ignore
            import soundfile as sf  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional deps
            raise RecordingError(
                "Recording requires numpy, sounddevice, and soundfile to be installed"
            ) from exc
        return np, sd, sf

    def record(
        self,
        destination: Path,
        duration: float,
        on_state_change: Callable[[str], None] | None = None,
    ) -> None:
        """Record audio synchronously for the provided duration (seconds)."""
        if duration <= 0:
            raise ValueError("duration must be positive")

        np, sd, sf = self._ensure_dependencies()

        destination.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if self._recording:
                raise RecordingError("Recorder is already active")
            self._recording = True
        try:
            if on_state_change:
                on_state_change("recording")
            frames = int(duration * self.samplerate)
            audio = sd.rec(
                frames,
                samplerate=self.samplerate,
                channels=self.channels,
                dtype="float32",
            )
            sd.wait()
            if on_state_change:
                on_state_change("saving")
            sf.write(destination, audio, self.samplerate)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            destination.unlink(missing_ok=True)
            raise RecordingError("Failed to capture audio") from exc
        finally:
            with self._lock:
                self._recording = False
            if on_state_change:
                on_state_change("idle")

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._recording
