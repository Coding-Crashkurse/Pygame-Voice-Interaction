from __future__ import annotations

from typing import Dict, List, Optional

import pygame

from constants import GAME_TITLE, SCREEN_WIDTH, SCENE_CITY
from entities.player import Player
from scenes.base import BaseScene
from ui.components import Button, OptionSelector, TextInput


class StartScene(BaseScene):
    CLASS_SPRITES: Dict[str, str] = {
        "Fighter": "warrior",
        "Sorcerer": "sorcerer",
    }

    def __init__(self, app: "GameApp") -> None:
        super().__init__(app)
        self.title_font = pygame.font.SysFont("arial", 64)
        self.body_font = pygame.font.SysFont("arial", 28)
        self.small_font = pygame.font.SysFont("arial", 22)
        self.input = TextInput(
            pygame.Rect(SCREEN_WIDTH // 2 - 240, 240, 480, 56),
            self.body_font,
            "Enter Name",
        )
        self.start_button = Button(
            pygame.Rect(SCREEN_WIDTH // 2 - 150, 540, 300, 70),
            "Begin Journey",
            self.body_font,
            self._start_game,
        )
        selector_rect = pygame.Rect(40, 220, 260, 56)
        self.voice_selector = OptionSelector(
            selector_rect, self.body_font, ["Buttons", "Voice"]
        )
        self.focus_order: List[str] = ["input", "voice", "start"]
        self.focus_index = 0
        self.input.set_active(True)
        self.start_button.is_focused = False
        self.selected_class: Optional[str] = None
        self.class_cards = self._build_class_cards()
        self.instructions = [
            "Controls:",
            "WASD / Arrows to move",
            "E to interact",
            "I for inventory",
            "Esc to back/close",
        ]

    def _build_class_cards(self) -> Dict[str, Dict[str, pygame.Rect | pygame.Surface]]:
        cards: Dict[str, Dict[str, pygame.Rect | pygame.Surface]] = {}
        center_y = 400
        offset = 240
        positions = {
            "Fighter": (SCREEN_WIDTH // 2 - offset, center_y),
            "Sorcerer": (SCREEN_WIDTH // 2 + offset, center_y),
        }
        for class_name, sprite_key in self.CLASS_SPRITES.items():
            image = self.app.assets.get_image(sprite_key, (96, 128))
            image_rect = image.get_rect(center=positions[class_name])
            card_rect = image_rect.inflate(40, 40)
            cards[class_name] = {
                "image": image,
                "image_rect": image_rect,
                "card_rect": card_rect,
            }
        return cards

    @property
    def can_start(self) -> bool:
        return bool(self.selected_class) and bool(self.input.text.strip())

    def _start_game(self) -> None:
        if not self.can_start:
            self.app.assets.play_sound("error", volume=0.5)
            return
        player = Player(self.input.text.strip(), self.selected_class or "Fighter")
        self.app.player = player
        self.app.voice_enabled = self.voice_selector.selected.lower() == "voice"
        self.app.change_scene(SCENE_CITY)

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    self.focus_index = (self.focus_index + 1) % len(self.focus_order)
                    self._apply_focus()
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if self.voice_selector.is_focused:
                        continue
                    if not self.input.is_active:
                        self._cycle_class(-1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if self.voice_selector.is_focused:
                        continue
                    if not self.input.is_active:
                        self._cycle_class(1)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if self.input.is_active and self.can_start:
                        self._start_game()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for class_name, data in self.class_cards.items():
                    if data["card_rect"].collidepoint(event.pos) or data[
                        "image_rect"
                    ].collidepoint(event.pos):
                        self.selected_class = class_name
                        break
        self.input.handle_events(events)
        self.start_button.enabled = self.can_start
        self.start_button.handle_events(events)
        self.voice_selector.handle_events(events)

    def _cycle_class(self, direction: int) -> None:
        class_names = list(self.CLASS_SPRITES.keys())
        if self.selected_class is None:
            if direction != 0:
                self.selected_class = class_names[0]
            return
        index = class_names.index(self.selected_class)
        index = (index + direction) % len(class_names)
        self.selected_class = class_names[index]

    def _apply_focus(self) -> None:
        focus_target = self.focus_order[self.focus_index]
        self.voice_selector.set_focused(focus_target == "voice")
        self.input.set_active(focus_target == "input")
        self.start_button.is_focused = focus_target == "start"

    def update(self, dt: float) -> None:
        self.input.update(dt)
        self.start_button.enabled = self.can_start

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((15, 20, 30))
        title = self.title_font.render(GAME_TITLE, True, pygame.Color("white"))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        surface.blit(title, title_rect)

        label_name = self.body_font.render("Enter Name", True, pygame.Color("white"))
        surface.blit(label_name, (self.input.rect.left, self.input.rect.top - 42))
        label_class = self.body_font.render(
            "Choose Your Path", True, pygame.Color("white")
        )
        surface.blit(
            label_class, (SCREEN_WIDTH // 2 - label_class.get_width() // 2, 340)
        )

        for class_name, data in self.class_cards.items():
            selected = self.selected_class == class_name
            self._draw_class_card(surface, class_name, data, selected)

        self.input.render(surface)
        self.start_button.render(surface)

        mode_label = self.small_font.render(
            "Interaction Mode", True, pygame.Color("white")
        )
        surface.blit(
            mode_label,
            (self.voice_selector.rect.left, self.voice_selector.rect.top - 32),
        )
        self.voice_selector.render(surface)
        self._draw_instructions(surface)
        self._draw_selection_hint(surface)

    def _draw_class_card(
        self,
        surface: pygame.Surface,
        class_name: str,
        data: Dict[str, pygame.Rect | pygame.Surface],
        selected: bool,
    ) -> None:
        card_rect: pygame.Rect = data["card_rect"]  # type: ignore[assignment]
        image_rect: pygame.Rect = data["image_rect"]  # type: ignore[assignment]
        image: pygame.Surface = data["image"]  # type: ignore[assignment]
        base_color = pygame.Color("#004d40") if selected else pygame.Color("#1a1f2b")
        pygame.draw.rect(surface, base_color, card_rect, border_radius=12)
        border_color = pygame.Color("#00e676") if selected else pygame.Color("#455a64")
        pygame.draw.rect(surface, border_color, card_rect, 3, border_radius=12)
        surface.blit(image, image_rect)
        label = self.small_font.render(class_name, True, pygame.Color("white"))
        label_rect = label.get_rect(midtop=(card_rect.centerx, card_rect.bottom - 30))
        surface.blit(label, label_rect)
        prompt = self.small_font.render(
            "Click to select", True, pygame.Color("#b0bec5")
        )
        prompt_rect = prompt.get_rect(midtop=(card_rect.centerx, label_rect.bottom + 4))
        surface.blit(prompt, prompt_rect)

    def _draw_selection_hint(self, surface: pygame.Surface) -> None:
        if not self.selected_class:
            hint = self.small_font.render(
                "Click a class card to choose", True, pygame.Color("#b0bec5")
            )
        else:
            hint = self.small_font.render(
                f"{self.selected_class} selected", True, pygame.Color("#c5e1a5")
            )
        surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 360))

    def _draw_instructions(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(40, 40, 260, 150)
        pygame.draw.rect(surface, (18, 24, 34), panel, border_radius=8)
        pygame.draw.rect(surface, (90, 130, 180), panel, 2, border_radius=8)
        for index, line in enumerate(self.instructions):
            color = pygame.Color("#ffcc80") if index == 0 else pygame.Color("white")
            text = self.small_font.render(line, True, color)
            surface.blit(text, (panel.left + 16, panel.top + 18 + index * 26))


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import GameApp
