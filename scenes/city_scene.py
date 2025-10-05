from __future__ import annotations

from typing import List, Tuple

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH, SCENE_SHOP, SCENE_WILDERNESS, TILE_SIZE
from scenes.base import BaseScene
from utils.helpers import build_blocking_rects


class CityScene(BaseScene):
    def __init__(self, app: "GameApp") -> None:
        super().__init__(app)
        self.font = pygame.font.SysFont("arial", 24)
        self.background_color = (34, 90, 60)
        self.cols = SCREEN_WIDTH // TILE_SIZE
        self.rows = SCREEN_HEIGHT // TILE_SIZE
        gate_height_tiles = 5
        gate_center_row = self.rows // 2
        self.gate_top_row = max(1, gate_center_row - gate_height_tiles // 2)
        self.gate_bottom_row = self.gate_top_row + gate_height_tiles
        self.gate_tiles = {(0, y) for y in range(self.gate_top_row, self.gate_bottom_row)}
        gate_center_y = (self.gate_top_row + self.gate_bottom_row) / 2 * TILE_SIZE
        self.player_spawn = (TILE_SIZE * 6, int(gate_center_y))
        self.left_exit_rect = pygame.Rect(
            0,
            self.gate_top_row * TILE_SIZE,
            TILE_SIZE,
            (self.gate_bottom_row - self.gate_top_row) * TILE_SIZE,
        )
        self.blocking_rects: List[pygame.Rect] = []
        self.decor_drawables: List[Tuple[pygame.Surface, pygame.Rect]] = []
        self.merchant_pos = (SCREEN_WIDTH // 2 + 240, SCREEN_HEIGHT // 2 - 30)
        self.merchant_rect = pygame.Rect(self.merchant_pos[0], self.merchant_pos[1], 48, 64)
        self._footstep_timer = 0.0
        self._setup_environment()

    def _setup_environment(self) -> None:
        wall_blocks: List[Tuple[int, int]] = []
        for x in range(self.cols):
            wall_blocks.append((x, 0))
            wall_blocks.append((x, self.rows - 1))
        for y in range(self.rows):
            if (0, y) not in self.gate_tiles:
                wall_blocks.append((0, y))
            wall_blocks.append((self.cols - 1, y))
        self.blocking_rects.extend(build_blocking_rects(wall_blocks))

        self.decor_specs = [
            ("house_1", (240, 140), True),
            ("house_2", (520, 140), True),
            ("forge", (800, 150), True),
            ("door", (290, 260), False),
            ("door", (570, 260), False),
            ("door", (850, 260), False),
            ("lantern", (240, 400), False),
            ("lantern", (880, 400), False),
            ("barrel", (360, 420), True),
            ("barrel", (720, 420), True),
            ("chest", (600, 420), True),
            ("tree", (1040, 420), True),
            ("tree_2", (320, 420), True),
            ("bush", (1020, 320), True),
            ("rock", (1040, 520), True),
            ("rock", (120, 520), True),
        ]

        for key, pos, blocking in self.decor_specs:
            image = self.app.assets.get_image(key, self._decoration_size(key))
            draw_rect = image.get_rect(topleft=pos)
            self.decor_drawables.append((image, draw_rect))
            if blocking:
                self.blocking_rects.append(self._blocking_rect_for(key, draw_rect))

    def _decoration_size(self, key: str) -> Tuple[int, int]:
        if key in {"house_1", "house_2", "forge"}:
            return (256, 256)
        if key == "door":
            return (48, 96)
        if key == "lantern":
            return (40, 120)
        if key == "barrel":
            return (48, 64)
        if key == "chest":
            return (64, 64)
        if key in {"tree", "tree_2"}:
            return (120, 160)
        if key == "bush":
            return (96, 64)
        if key == "rock":
            return (80, 80)
        return (TILE_SIZE, TILE_SIZE)

    def _blocking_rect_for(self, key: str, draw_rect: pygame.Rect) -> pygame.Rect:
        rect = draw_rect.copy()
        if key in {"house_1", "house_2", "forge"}:
            rect = pygame.Rect(
                draw_rect.left + 20,
                draw_rect.top + draw_rect.height // 2,
                draw_rect.width - 40,
                draw_rect.height // 2,
            )
        elif key in {"tree", "tree_2"}:
            rect = pygame.Rect(
                draw_rect.left + 25,
                draw_rect.top + draw_rect.height // 2,
                draw_rect.width - 50,
                draw_rect.height // 2,
            )
        elif key == "bush":
            rect = pygame.Rect(
                draw_rect.left + 10,
                draw_rect.top + draw_rect.height // 2,
                draw_rect.width - 20,
                draw_rect.height // 2,
            )
        elif key == "rock":
            rect = draw_rect.inflate(-10, -10)
        elif key == "chest":
            rect = draw_rect.inflate(-12, -12)
        else:
            rect = draw_rect
        return rect

    def on_enter(self, **kwargs) -> None:
        spawn = kwargs.get("spawn")
        if spawn is None:
            spawn = self.player_spawn
        self.app.player.rect.center = spawn

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        overlay = self.app.inventory_overlay
        overlay.handle_events(events)
        if overlay.active:
            return
        near_merchant = self._player_near_merchant()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_i:
                    overlay.toggle()
                elif event.key == pygame.K_e:
                    if near_merchant:
                        self.app.change_scene(SCENE_SHOP)

    def _player_near_merchant(self) -> bool:
        player_center = self.app.player.rect.center
        merchant_center = self.merchant_rect.center
        return pygame.Vector2(player_center).distance_to(merchant_center) <= 80

    def update(self, dt: float) -> None:
        overlay = self.app.inventory_overlay
        if overlay.active:
            return
        player = self.app.player
        moved = player.handle_movement(dt, tuple(self.blocking_rects))
        if moved:
            self._footstep_timer += dt
            if self._footstep_timer >= 0.3:
                self._footstep_timer = 0.0
                self.app.assets.play_sound("footsteps", volume=0.2)
        else:
            self._footstep_timer = 0.0

        if player.rect.colliderect(self.left_exit_rect):
            spawn = (SCREEN_WIDTH - 80, player.rect.centery)
            self.app.change_scene(SCENE_WILDERNESS, spawn=spawn)

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(self.background_color)
        self._draw_ground(surface)

        for image, draw_rect in self.decor_drawables:
            surface.blit(image, draw_rect.topleft)

        gate_post = self.app.assets.get_image("door", (60, 120))
        upper_rect = gate_post.get_rect(midleft=(TILE_SIZE, self.gate_top_row * TILE_SIZE + 40))
        lower_rect = gate_post.get_rect(midleft=(TILE_SIZE, self.gate_bottom_row * TILE_SIZE - 40))
        surface.blit(gate_post, upper_rect.topleft)
        surface.blit(gate_post, lower_rect.topleft)

        near_merchant = self._player_near_merchant()
        if near_merchant:
            self._draw_merchant_glow(surface)

        merchant_img = self.app.assets.get_image("merchant", (64, 96))
        merchant_draw_rect = merchant_img.get_rect(midbottom=self.merchant_rect.midbottom)
        surface.blit(merchant_img, merchant_draw_rect.topleft)

        player_sprite_key = "warrior" if self.app.player.player_class == "Fighter" else "sorcerer"
        player_img = self.app.assets.get_image(player_sprite_key, (64, 96))
        player_draw_rect = player_img.get_rect(midbottom=self.app.player.rect.midbottom)
        surface.blit(player_img, player_draw_rect.topleft)

        hud_text = self.font.render(f"Gold: {self.app.player.gold}", True, pygame.Color("white"))
        hud_rect = hud_text.get_rect(topleft=(24, SCREEN_HEIGHT - 56))
        badge = pygame.Surface((hud_rect.width + 20, hud_rect.height + 12), pygame.SRCALPHA)
        badge.fill((0, 0, 0, 150))
        surface.blit(badge, (hud_rect.left - 10, hud_rect.top - 6))
        surface.blit(hud_text, hud_rect.topleft)

        if near_merchant:
            prompt = self.font.render("Press E to Trade", True, pygame.Color("#ffeb3b"))
            surface.blit(prompt, (self.merchant_rect.left - 40, self.merchant_rect.top - 32))

        self.app.inventory_overlay.render(surface)

    def _draw_merchant_glow(self, surface: pygame.Surface) -> None:
        glow_radius = 90
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (255, 240, 120, 110), (glow_radius, glow_radius), glow_radius)
        pygame.draw.circle(glow_surface, (255, 255, 200, 180), (glow_radius, glow_radius), glow_radius // 2)
        glow_rect = glow_surface.get_rect(center=self.merchant_rect.center)
        surface.blit(glow_surface, glow_rect.topleft, special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_ground(self, surface: pygame.Surface) -> None:
        wall_tile = self.app.assets.get_image("wall", (TILE_SIZE, TILE_SIZE))
        for x in range(self.cols):
            surface.blit(wall_tile, (x * TILE_SIZE, 0))
            surface.blit(wall_tile, (x * TILE_SIZE, (self.rows - 1) * TILE_SIZE))
        for y in range(self.rows):
            if (0, y) not in self.gate_tiles:
                surface.blit(wall_tile, (0, y * TILE_SIZE))
            surface.blit(wall_tile, ((self.cols - 1) * TILE_SIZE, y * TILE_SIZE))

        inner_rect = pygame.Rect(TILE_SIZE, TILE_SIZE, SCREEN_WIDTH - 2 * TILE_SIZE, SCREEN_HEIGHT - 2 * TILE_SIZE)
        pygame.draw.rect(surface, (44, 110, 70), inner_rect)

        gate_path_rect = pygame.Rect(
            0,
            self.gate_top_row * TILE_SIZE + 6,
            TILE_SIZE * 6,
            (self.gate_bottom_row - self.gate_top_row) * TILE_SIZE - 12,
        )
        pygame.draw.rect(surface, (94, 74, 42), gate_path_rect)

        plaza_rect = pygame.Rect(TILE_SIZE * 6, TILE_SIZE * 7, TILE_SIZE * 20, TILE_SIZE * 8)
        pygame.draw.rect(surface, (52, 130, 90), plaza_rect)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import GameApp
















