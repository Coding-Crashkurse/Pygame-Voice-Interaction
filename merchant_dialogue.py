from __future__ import annotations

import queue
import threading
import traceback
from abc import ABC, abstractmethod
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Sequence

import pygame

from voice.assistant import AssistantResult, MerchantVoiceAssistant, PurchaseOutcome
from voice.service import RecordingError, VoiceEngine

VOICE_RECORD_SECONDS = 4.0


MAX_LOG_LINES = 10


class DialogueChannel(ABC):
    @abstractmethod
    def render(self, surface: pygame.Surface) -> None:
        raise NotImplementedError

    @abstractmethod
    def handle_input(self, events: Sequence[pygame.event.Event]) -> None:
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - optional override
        """Allow channels to release resources when scenes change."""


class ButtonsChannel(DialogueChannel):
    def __init__(self, render_callback, input_callback) -> None:
        self._render_callback = render_callback

        self._input_callback = input_callback

    def render(self, surface: pygame.Surface) -> None:
        self._render_callback(surface)

    def handle_input(self, events: Sequence[pygame.event.Event]) -> None:
        self._input_callback(events)


@dataclass
class VoiceTaskResult:
    transcript: str | None = None

    assistant: AssistantResult | None = None

    audio_path: Path | None = None

    error: str | None = None


class VoiceChannel(DialogueChannel):
    def __init__(self, scene: "ShopScene", render_callback, input_callback) -> None:
        self._scene = scene

        self._render_callback = render_callback

        self._input_callback = input_callback

        self._engine: VoiceEngine | None = None

        self._assistant: MerchantVoiceAssistant | None = None

        self._executor = ThreadPoolExecutor(max_workers=1)

        self._current_future: Future[VoiceTaskResult] | None = None

        self._purchase_requests: queue.Queue[
            tuple[str | None, threading.Event, dict[str, PurchaseOutcome]]
        ] = queue.Queue()

        self._log: Deque[tuple[str, str]] = deque(maxlen=MAX_LOG_LINES)

        self._state: str = "idle"

        self._status_text: str = "Press Space to talk"

        self._error_message: str | None = None

        self._thread_id = self._make_thread_id()

        self._temp_audio: list[Path] = []

        self._initialise_services()

    def _make_thread_id(self) -> str:
        player = getattr(self._scene.app, "player", None)

        base = getattr(player, "name", "traveler") if player else "traveler"

        return f"shop:{base.lower()}"

    def _initialise_services(self) -> None:
        try:
            self._engine = self._scene.app.ensure_voice_engine()

            visitor = getattr(getattr(self._scene.app, "player", None), "name", None)
            self._assistant = MerchantVoiceAssistant(
                self._scene.items,
                self._purchase_handler,
                thread_namespace="merchant",
                visitor_name=visitor,
            )

            display_name = (visitor or "traveler").strip() or "traveler"
            self._append_log(
                "Mira",
                f"Welcome, {display_name}! Tell me what you need or feel free to chat.",
            )

        except Exception as exc:  # pragma: no cover - defensive
            self._state = "error"

            self._error_message = str(exc)

            self._status_text = "Voice setup failed"

    def close(self) -> None:
        if self._assistant:
            self._assistant.reset_conversation(self._thread_id)

        if self._current_future and not self._current_future.done():
            self._current_future.cancel()

        self._executor.shutdown(wait=False, cancel_futures=True)

        if self._engine:
            self._engine.cleanup()

        for path in self._temp_audio:
            path.unlink(missing_ok=True)

        self._temp_audio.clear()

    # ------------------------------------------------------------------

    # DialogueChannel interface

    # ------------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        self._process_purchase_requests()

        self._poll_future()

        self._render_callback(surface)

        self._render_overlay(surface)

    def handle_input(self, events: Sequence[pygame.event.Event]) -> None:
        self._input_callback(events)

        if self._assistant is None or self._engine is None or self._state == "error":
            return

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if event.key == pygame.K_SPACE:
                self._start_listening()

            elif event.key == pygame.K_r:
                self._reset_conversation()

    # ------------------------------------------------------------------

    # Voice interaction helpers

    # ------------------------------------------------------------------

    def _start_listening(self) -> None:
        if self._current_future and not self._current_future.done():
            print("[VoiceChannel] Ignoring start request; task still running")
            return
        if self._state == "error":
            print("[VoiceChannel] Cannot start listening while in error state")
            return
        if self._engine is None or self._assistant is None:
            print("[VoiceChannel] Engine or assistant not ready")
            return
        self._state = "recording"
        self._status_text = "Listening..."
        self._error_message = None
        print("[VoiceChannel] Starting async capture")
        self._current_future = self._executor.submit(self._capture_and_process)

    def _capture_and_process(self) -> VoiceTaskResult:
        assert self._engine is not None
        assert self._assistant is not None
        try:
            print(f"[VoiceChannel] Recording for {VOICE_RECORD_SECONDS}s")
            transcript = self._engine.record_and_transcribe(VOICE_RECORD_SECONDS)
            print(f"[VoiceChannel] Transcript: {transcript!r}")
            if not transcript.strip():
                print(
                    "[VoiceChannel] Transcript empty after stripping; returning error"
                )
                return VoiceTaskResult(error="I could not hear you.")
            assistant_result = self._assistant.process(transcript, self._thread_id)
            print(
                "[VoiceChannel] Assistant result intent={intent} candidate={candidate} text={text!r}".format(
                    intent=assistant_result.intent,
                    candidate=assistant_result.candidate_item,
                    text=assistant_result.text,
                )
            )
            if assistant_result.trade_result:
                trade = assistant_result.trade_result
                print(
                    "[VoiceChannel] Trade result success={s} item={item} price={price} message={msg!r}".format(
                        s=trade.success,
                        item=trade.item_name,
                        price=trade.price_paid,
                        msg=trade.message,
                    )
                )
            audio_path: Path | None = None
            if assistant_result.text:
                audio_path = self._engine.synthesize(assistant_result.text)
                print(f"[VoiceChannel] Synthesized response audio at {audio_path}")
            return VoiceTaskResult(
                transcript=transcript.strip(),
                assistant=assistant_result,
                audio_path=audio_path,
            )
        except RecordingError as exc:
            print(f"[VoiceChannel] RecordingError: {exc}")
            return VoiceTaskResult(error=str(exc))
        except Exception as exc:
            traceback.print_exc()
            print(f"[VoiceChannel] Unexpected failure: {exc}")
            return VoiceTaskResult(error=f"Voice interaction failed: {exc}")

    def _purchase_handler(self, item_name: str | None) -> PurchaseOutcome:
        print(f"[VoiceChannel] Purchase handler invoked with item_name={item_name!r}")
        event = threading.Event()
        container: dict[str, PurchaseOutcome] = {}
        self._purchase_requests.put((item_name, event, container))
        event.wait()
        outcome = container["outcome"]
        print(
            "[VoiceChannel] Purchase outcome success={s} item={item} message={msg!r}".format(
                s=outcome.success,
                item=outcome.item_name,
                msg=outcome.message,
            )
        )
        return outcome

    def _process_purchase_requests(self) -> None:
        while True:
            try:
                item_name, event, container = self._purchase_requests.get_nowait()
            except queue.Empty:
                break
            print(f"[VoiceChannel] Processing queued purchase for {item_name!r}")
            try:
                outcome = self._scene.attempt_voice_purchase(item_name)
            except Exception as exc:
                print(f"[VoiceChannel] Exception during purchase: {exc}")
                outcome = PurchaseOutcome(
                    False, item_name, f"Trade failed: {exc}", None
                )
            container["outcome"] = outcome
            event.set()

    def _poll_future(self) -> None:
        if not self._current_future:
            return
        if not self._current_future.done():
            return
        try:
            print("[VoiceChannel] Future completed; collecting result")
            result = self._current_future.result()
        except Exception as exc:  # pragma: no cover - defensive
            self._state = "error"
            self._status_text = "Voice error"
            self._error_message = str(exc)
            print(f"[VoiceChannel] Future raised exception: {exc}")
        else:
            self._handle_task_result(result)
        finally:
            self._current_future = None

    def _handle_task_result(self, result: VoiceTaskResult) -> None:
        if result.error:
            print(f"[VoiceChannel] Task returned error: {result.error!r}")
            self._state = "idle"
            self._status_text = "Press Space to talk"
            self._error_message = result.error
            if result.error:
                self._append_log("System", result.error)
            return

        self._state = "idle"
        self._status_text = "Press Space to talk"
        print("[VoiceChannel] Task completed successfully")
        if result.transcript:
            print(f"[VoiceChannel] Logged transcript: {result.transcript!r}")
            self._append_log("You", result.transcript)

        if result.assistant:
            ar = result.assistant
            print(
                "[VoiceChannel] Assistant intent={intent} candidate={candidate} text={text!r}".format(
                    intent=ar.intent,
                    candidate=ar.candidate_item,
                    text=ar.text,
                )
            )
            if ar.trade_result:
                trade = ar.trade_result
                print(
                    "[VoiceChannel] Assistant trade success={s} item={item} price={price} message={msg!r}".format(
                        s=trade.success,
                        item=trade.item_name,
                        price=trade.price_paid,
                        msg=trade.message,
                    )
                )
            if ar.text:
                self._append_log("Mira", ar.text)
        if result.audio_path:
            print(f"[VoiceChannel] Playing synthesized audio from {result.audio_path}")
            self._play_audio(result.audio_path)

    def _play_audio(self, audio_path: Path) -> None:
        try:
            sound = pygame.mixer.Sound(str(audio_path))

        except pygame.error:
            audio_path.unlink(missing_ok=True)

            return

        self._temp_audio.append(audio_path)

        sound.set_volume(0.85)

        sound.play()

    def _reset_conversation(self) -> None:
        if not self._assistant:
            return

        self._assistant.reset_conversation(self._thread_id)

        self._log.clear()

        self._append_log("Mira", "Let's start over. How can I help?")

        self._state = "idle"

        self._status_text = "Press Space to talk"

        self._error_message = None

    # ------------------------------------------------------------------

    # Rendering helpers

    # ------------------------------------------------------------------

    def _wrap_text(
        self, text: str, font: pygame.font.Font, max_width: int
    ) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if (
                font.render(candidate, True, pygame.Color("white")).get_width()
                <= max_width
            ):
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _render_overlay(self, surface: pygame.Surface) -> None:
        font = self._scene.small_font
        title_font = self._scene.small_font

        width, height = surface.get_size()
        panel_width = 420
        max_log_lines = 8
        max_line_width = panel_width - 32

        rendered_lines: list[tuple[str, str]] = []
        for speaker, message in reversed(self._log):
            wrapped = self._wrap_text(f"{speaker}: {message}", font, max_line_width)
            for chunk in reversed(wrapped):
                rendered_lines.append((speaker, chunk))
                if len(rendered_lines) >= max_log_lines:
                    break
            if len(rendered_lines) >= max_log_lines:
                break
        rendered_lines = list(reversed(rendered_lines))

        line_height = font.get_linesize() + 2
        log_height = max(1, len(rendered_lines)) * line_height
        base_height = 148
        panel_height = base_height + log_height
        panel = pygame.Rect(width - panel_width - 32, 32, panel_width, panel_height)

        pygame.draw.rect(surface, (16, 24, 40), panel, border_radius=14)
        pygame.draw.rect(surface, (84, 140, 220), panel, 2, border_radius=14)

        y = panel.top + 14
        title = title_font.render("Voice Assistant", True, pygame.Color("#e3f2fd"))
        surface.blit(title, (panel.left + 18, y))
        y += title_font.get_linesize() + 4

        status_color = (
            pygame.Color("#aed581")
            if self._state != "error"
            else pygame.Color("#ef9a9a")
        )
        status_text = font.render(f"Status: {self._status_text}", True, status_color)
        surface.blit(status_text, (panel.left + 18, y))
        y += line_height

        if self._error_message:
            error_text = font.render(self._error_message, True, pygame.Color("#ef9a9a"))
            surface.blit(error_text, (panel.left + 18, y))
            y += line_height

        y += 6

        for speaker, line_text in rendered_lines:
            if speaker == "System":
                color = pygame.Color("#ef9a9a")
            elif speaker == "Mira":
                color = pygame.Color("#c5e1a5")
            else:
                color = pygame.Color("#eceff1")
            line_surface = font.render(line_text, True, color)
            surface.blit(line_surface, (panel.left + 18, y))
            y += line_height

        instructions = font.render(
            "Space: Talk  |  R: Reset  |  Esc: Back", True, pygame.Color("#90caf9")
        )
        surface.blit(
            instructions,
            (panel.left + 18, panel.bottom - instructions.get_height() - 16),
        )

    def _append_log(self, speaker: str, message: str | None) -> None:
        if message is None:
            return
        clean = str(message).replace("\n", " ").strip()
        if not clean:
            return
        self._log.append((speaker, clean))


def create_channel(
    kind: str, render_callback, input_callback, **kwargs
) -> DialogueChannel:
    if kind == "buttons":
        return ButtonsChannel(render_callback, input_callback)
    if kind == "voice":
        scene = kwargs.get("scene")
        if scene is None:
            raise ValueError("Voice channel requires a scene reference")
        return VoiceChannel(scene, render_callback, input_callback)
    raise ValueError(f"Unknown channel kind: {kind}")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scenes.shop_scene import ShopScene
