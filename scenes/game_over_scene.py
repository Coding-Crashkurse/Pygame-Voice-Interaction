from __future__ import annotations

from typing import Sequence

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH, SCENE_START
from scenes.base import BaseScene
from ui.components import Button


class GameOverScene(BaseScene):
    def __init__(self, app: "GameApp") -> None:
        super().__init__(app)
        self.title_font = pygame.font.SysFont("arial", 72)
        self.body_font = pygame.font.SysFont("arial", 28)
        self.retry_button = Button(
            pygame.Rect(SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2 + 60, 240, 60),
            "Retry",
            self.body_font,
            self._retry,
        )
        self.retry_button.is_focused = True

    def on_enter(self, **kwargs) -> None:
        pass

    def _retry(self) -> None:
        self.app.reset_game()
        self.app.change_scene(SCENE_START)

    def handle_events(self, events: Sequence[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN,
                pygame.K_SPACE,
            ):
                self._retry()
        self.retry_button.handle_events(events)

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((10, 0, 0))
        title = self.title_font.render("Game Over", True, pygame.Color("#ff5252"))
        surface.blit(
            title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60))
        )
        subtitle = self.body_font.render(
            "Your journey ends here...", True, pygame.Color("white")
        )
        surface.blit(
            subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        )
        self.retry_button.render(surface)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import GameApp
