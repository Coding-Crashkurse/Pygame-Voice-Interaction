from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import pygame

from constants import TILE_SIZE


def tile_to_pixel(tile_pos: Tuple[int, int]) -> Tuple[int, int]:
    x, y = tile_pos
    return x * TILE_SIZE, y * TILE_SIZE


def rect_from_tile(tile_pos: Tuple[int, int], size: Tuple[int, int] | None = None) -> pygame.Rect:
    if size is None:
        size = (TILE_SIZE, TILE_SIZE)
    x, y = tile_to_pixel(tile_pos)
    w, h = size
    return pygame.Rect(x, y, w, h)


def build_blocking_rects(tiles: Sequence[Tuple[int, int]], size: Tuple[int, int] | None = None) -> Tuple[pygame.Rect, ...]:
    rects: List[pygame.Rect] = []
    for tile in tiles:
        rects.append(rect_from_tile(tile, size))
    return tuple(rects)


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str, position: Tuple[int, int], color: str = "white") -> pygame.Rect:
    text_surface = font.render(text, True, color)
    rect = text_surface.get_rect(topleft=position)
    surface.blit(text_surface, rect)
    return rect
