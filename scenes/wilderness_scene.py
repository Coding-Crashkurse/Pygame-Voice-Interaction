from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

import pygame

from constants import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SCENE_BOSS,
    SCENE_CITY,
    SCENE_WILDERNESS,
    TILE_SIZE,
)
from entities.enemies import (
    BLOB_TEMPLATE,
    SKELETON_TEMPLATE,
    WanderBehaviour,
    clone_enemy,
)
from scenes.base import BaseScene


@dataclass
class FieldEnemy:
    template_key: str
    sprite_key: str
    rect: pygame.Rect
    behaviour: WanderBehaviour
    respawn_timer: float = 0.0

    def reset(self, bounds: pygame.Rect) -> None:
        self.rect.center = (
            random.randint(bounds.left + 50, bounds.right - 50),
            random.randint(bounds.top + 50, bounds.bottom - 50),
        )
        self.behaviour.rect = self.rect
        self.respawn_timer = 0.0


class WildernessScene(BaseScene):
    def __init__(self, app: "GameApp") -> None:
        super().__init__(app)
        self.font = pygame.font.SysFont("arial", 24)
        self.bounds = pygame.Rect(80, 80, SCREEN_WIDTH - 160, SCREEN_HEIGHT - 200)
        self.left_exit = pygame.Rect(0, self.bounds.top, TILE_SIZE, self.bounds.height)
        self.right_exit = pygame.Rect(
            SCREEN_WIDTH - TILE_SIZE, self.bounds.top, TILE_SIZE, self.bounds.height
        )
        self.obstacles: List[pygame.Rect] = self._create_obstacles()
        self.enemies: List[FieldEnemy] = self._create_enemies()
        self._footstep_timer = 0.0

    def _create_obstacles(self) -> List[pygame.Rect]:
        obstacles: List[pygame.Rect] = []
        tree_positions = [
            (220, 200),
            (260, 420),
            (350, 260),
            (600, 180),
            (920, 300),
            (980, 460),
            (760, 360),
        ]
        rock_positions = [(440, 360), (560, 260), (820, 220)]
        bush_positions = [(320, 500), (880, 440), (1040, 360)]
        for pos in tree_positions:
            image = self.app.assets.get_image("tree", (120, 160))
            rect = pygame.Rect(pos, image.get_size())
            obstacles.append(rect)
        for pos in rock_positions:
            image = self.app.assets.get_image("rock", (80, 80))
            rect = pygame.Rect(pos, image.get_size())
            obstacles.append(rect)
        for pos in bush_positions:
            image = self.app.assets.get_image("bush", (96, 64))
            rect = pygame.Rect(pos, image.get_size())
            obstacles.append(rect)
        return obstacles

    def _create_enemies(self) -> List[FieldEnemy]:
        enemies: List[FieldEnemy] = []
        skeleton_positions = [(400, 240), (880, 200)]
        blob_positions = [(520, 420), (760, 260)]
        for pos in skeleton_positions:
            rect = pygame.Rect(pos, (48, 64))
            behaviour = WanderBehaviour(rect, self.bounds, speed=70)
            enemies.append(FieldEnemy("skeleton", "skeleton", rect, behaviour))
        for pos in blob_positions:
            rect = pygame.Rect(pos, (48, 64))
            behaviour = WanderBehaviour(rect, self.bounds, speed=60)
            enemies.append(FieldEnemy("blob", "blob", rect, behaviour))
        return enemies

    def on_enter(self, **kwargs) -> None:
        spawn = kwargs.get("spawn")
        if spawn is None:
            spawn = (self.bounds.centerx, self.bounds.bottom - 50)
        self.app.player.rect.center = spawn

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        overlay = self.app.inventory_overlay
        overlay.handle_events(events)
        if overlay.active:
            return
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_i:
                    overlay.toggle()

    def update(self, dt: float) -> None:
        overlay = self.app.inventory_overlay
        if overlay.active:
            return
        moved = self.app.player.handle_movement(dt, tuple(self.obstacles))
        if moved:
            self._footstep_timer += dt
            if self._footstep_timer >= 0.3:
                self._footstep_timer = 0.0
                self.app.assets.play_sound("footsteps", volume=0.2)
        else:
            self._footstep_timer = 0.0

        for enemy in self.enemies:
            if enemy.respawn_timer > 0:
                enemy.respawn_timer = max(0.0, enemy.respawn_timer - dt)
                continue
            enemy.behaviour.update(dt, self.obstacles)
            if enemy.rect.colliderect(self.app.player.rect):
                template = (
                    SKELETON_TEMPLATE
                    if enemy.template_key == "skeleton"
                    else BLOB_TEMPLATE
                )
                sprite_key = "skeleton" if enemy.template_key == "skeleton" else "blob"
                self.app.start_battle(
                    clone_enemy(template),
                    return_scene=SCENE_WILDERNESS,
                    field_enemy=enemy,
                    sprite_key=sprite_key,
                )
                enemy.respawn_timer = 2.5
                break

        if self.app.player.rect.colliderect(self.left_exit):
            self.app.change_scene(SCENE_BOSS)
        elif self.app.player.rect.colliderect(self.right_exit):
            spawn = (80, self.app.player.rect.centery)
            self.app.change_scene(SCENE_CITY, spawn=spawn)

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((48, 110, 70))
        pygame.draw.rect(surface, (38, 90, 60), self.bounds)
        pygame.draw.rect(surface, (20, 60, 40), self.bounds, 4)

        for obstacle in self.obstacles:
            sprite_key = "tree"
            size = obstacle.width, obstacle.height
            if size == (80, 80):
                sprite_key = "rock"
            elif size == (96, 64):
                sprite_key = "bush"
            image = self.app.assets.get_image(sprite_key, size)
            surface.blit(image, obstacle.topleft)

        for enemy in self.enemies:
            if enemy.respawn_timer > 0:
                continue
            sprite_img = self.app.assets.get_image(enemy.sprite_key, (64, 80))
            enemy_draw = sprite_img.get_rect(midbottom=enemy.rect.midbottom)
            surface.blit(sprite_img, enemy_draw.topleft)

        player_sprite_key = (
            "warrior" if self.app.player.player_class == "Fighter" else "sorcerer"
        )
        player_img = self.app.assets.get_image(player_sprite_key, (64, 96))
        player_draw_rect = player_img.get_rect(midbottom=self.app.player.rect.midbottom)
        surface.blit(player_img, player_draw_rect.topleft)

        hud_text = self.font.render(
            f"Gold: {self.app.player.gold}", True, pygame.Color("white")
        )
        hud_rect = hud_text.get_rect(topleft=(24, SCREEN_HEIGHT - 56))
        badge = pygame.Surface(
            (hud_rect.width + 20, hud_rect.height + 12), pygame.SRCALPHA
        )
        badge.fill((0, 0, 0, 150))
        surface.blit(badge, (hud_rect.left - 10, hud_rect.top - 6))
        surface.blit(hud_text, hud_rect.topleft)

        self.app.inventory_overlay.render(surface)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import GameApp
