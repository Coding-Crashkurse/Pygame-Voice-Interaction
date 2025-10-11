from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence

import pygame


if TYPE_CHECKING:
    from main import GameApp


class BaseScene:
    def __init__(self, app: "GameApp") -> None:
        self.app = app

    def on_enter(self, **kwargs) -> None:
        pass

    def on_exit(self) -> None:
        pass

    def handle_events(self, events: Sequence[pygame.event.Event]) -> None:
        pass

    def update(self, dt: float) -> Optional[str]:
        return None

    def render(self, surface: pygame.Surface) -> None:
        raise NotImplementedError
