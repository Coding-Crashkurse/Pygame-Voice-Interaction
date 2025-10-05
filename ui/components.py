from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

import pygame


Color = pygame.Color


@dataclass
class Button:
    rect: pygame.Rect
    text: str
    font: pygame.font.Font
    callback: Callable[[], None]
    is_focused: bool = False
    padding: int = 8
    enabled: bool = True

    def render(self, surface: pygame.Surface) -> None:
        if self.enabled:
            base_color = Color("#2e7d32") if self.is_focused else Color("#1b5e20")
            border_color = Color("white")
            text_color = Color("white")
        else:
            base_color = Color("#424242")
            border_color = Color("#9e9e9e")
            text_color = Color("#bdbdbd")
        pygame.draw.rect(surface, base_color, self.rect, border_radius=6)
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=6)
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_events(self, events: Sequence[pygame.event.Event]) -> None:
        if not self.enabled:
            return
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.rect.collidepoint(event.pos):
                    self.callback()
            elif event.type == pygame.KEYDOWN and self.is_focused:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    self.callback()


class TextInput:
    def __init__(self, rect: pygame.Rect, font: pygame.font.Font, placeholder: str = "") -> None:
        self.rect = rect
        self.font = font
        self.placeholder = placeholder
        self.text = ""
        self.is_active = False
        self.caret_visible = True
        self._caret_timer = 0.0

    def set_active(self, active: bool) -> None:
        self.is_active = active
        if not active:
            self.caret_visible = False

    def handle_events(self, events: Sequence[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.set_active(self.rect.collidepoint(event.pos))
            elif event.type == pygame.KEYDOWN and self.is_active:
                if event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                elif event.key == pygame.K_RETURN:
                    self.set_active(False)
                elif event.key == pygame.K_ESCAPE:
                    self.set_active(False)
                else:
                    if event.unicode.isprintable() and len(self.text) < 20:
                        self.text += event.unicode

    def update(self, dt: float) -> None:
        if self.is_active:
            self._caret_timer += dt
            if self._caret_timer >= 0.5:
                self._caret_timer = 0.0
                self.caret_visible = not self.caret_visible
        else:
            self.caret_visible = False

    def render(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, Color("#212121"), self.rect, border_radius=4)
        pygame.draw.rect(surface, Color("white"), self.rect, 2, border_radius=4)
        display_text = self.text or self.placeholder
        text_color = Color("white") if self.text else Color("#9e9e9e")
        text_surface = self.font.render(display_text, True, text_color)
        text_rect = text_surface.get_rect(left=self.rect.left + 10, centery=self.rect.centery)
        surface.blit(text_surface, text_rect)

        if self.is_active and self.caret_visible:
            caret_x = text_rect.right + 3
            caret_rect = pygame.Rect(caret_x, self.rect.top + 5, 2, self.rect.height - 10)
            pygame.draw.rect(surface, Color("white"), caret_rect)


class OptionSelector:
    def __init__(self, rect: pygame.Rect, font: pygame.font.Font, options: Sequence[str]) -> None:
        if not options:
            raise ValueError("OptionSelector requires at least one option")
        self.rect = rect
        self.font = font
        self.options: List[str] = list(options)
        self.index = 0
        self.is_focused = False

    @property
    def selected(self) -> str:
        return self.options[self.index]

    def set_focused(self, focused: bool) -> None:
        self.is_focused = focused

    def handle_events(self, events: Sequence[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.rect.collidepoint(event.pos):
                    self.index = (self.index + 1) % len(self.options)
            elif event.type == pygame.KEYDOWN and self.is_focused:
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.index = (self.index + 1) % len(self.options)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.index = (self.index - 1) % len(self.options)

    def render(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, Color("#004d40"), self.rect, border_radius=6)
        border_color = Color("#00bfa5") if self.is_focused else Color("white")
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=6)
        text_surface = self.font.render(self.selected, True, Color("white"))
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
