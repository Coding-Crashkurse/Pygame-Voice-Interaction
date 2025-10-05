from __future__ import annotations

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH, SCENE_WILDERNESS
from entities.enemies import BOSS_TEMPLATE, clone_enemy
from scenes.base import BaseScene


class BossScene(BaseScene):
    def __init__(self, app: "GameApp") -> None:
        super().__init__(app)
        self.font = pygame.font.SysFont("arial", 24)
        self.warning_font = pygame.font.SysFont("arial", 28, bold=True)
        self.boss_rect = pygame.Rect(SCREEN_WIDTH // 2 - 40, SCREEN_HEIGHT // 2 - 120, 80, 120)
        self.bounds = pygame.Rect(120, 120, SCREEN_WIDTH - 240, SCREEN_HEIGHT - 240)
        self._footstep_timer = 0.0

    def on_enter(self, **kwargs) -> None:
        spawn = kwargs.get("spawn")
        if spawn is None:
            spawn = (self.bounds.right - 60, self.bounds.centery)
        self.app.player.rect.center = spawn

    def handle_events(self, events):
        overlay = self.app.inventory_overlay
        overlay.handle_events(events)
        if overlay.active:
            return
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_i:
                overlay.toggle()

    def update(self, dt: float) -> None:
        overlay = self.app.inventory_overlay
        if overlay.active:
            return
        player = self.app.player
        moved = player.handle_movement(dt, tuple())
        if moved:
            self._footstep_timer += dt
            if self._footstep_timer >= 0.3:
                self._footstep_timer = 0.0
                self.app.assets.play_sound("footsteps", volume=0.2)
        else:
            self._footstep_timer = 0.0

        if player.rect.top < self.bounds.top:
            player.rect.top = self.bounds.top
        if player.rect.bottom > self.bounds.bottom:
            player.rect.bottom = self.bounds.bottom
        if player.rect.right > self.bounds.right:
            player.rect.right = self.bounds.right

        if player.rect.colliderect(self.boss_rect):
            self.app.start_battle(clone_enemy(BOSS_TEMPLATE), return_scene=SCENE_WILDERNESS, is_boss=True, sprite_key="boss")

        if player.rect.left <= 0:
            spawn = (SCREEN_WIDTH - 100, player.rect.centery)
            self.app.change_scene(SCENE_WILDERNESS, spawn=spawn)

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((60, 40, 80))
        pygame.draw.rect(surface, (40, 20, 60), self.bounds)
        pygame.draw.rect(surface, (150, 100, 180), self.bounds, 4)

        boss_img = self.app.assets.get_image("boss", (180, 220))
        boss_draw = boss_img.get_rect(midbottom=self.boss_rect.midbottom)
        surface.blit(boss_img, boss_draw.topleft)

        torch_img = self.app.assets.get_image("lantern", (60, 160))
        surface.blit(torch_img, (self.bounds.left + 20, self.bounds.top - 40))
        surface.blit(torch_img, (self.bounds.right - 80, self.bounds.top - 40))

        statue_img = self.app.assets.get_image("forge", (200, 200))
        surface.blit(statue_img, (self.bounds.centerx - 100, self.bounds.top - 220))

        player_sprite_key = "warrior" if self.app.player.player_class == "Fighter" else "sorcerer"
        player_img = self.app.assets.get_image(player_sprite_key, (64, 96))
        player_draw_rect = player_img.get_rect(midbottom=self.app.player.rect.midbottom)
        surface.blit(player_img, player_draw_rect.topleft)

        hud_text = self.font.render(f"Gold: {self.app.player.gold}", True, pygame.Color("white"))
        hud_rect = hud_text.get_rect(topleft=(24, SCREEN_HEIGHT - 56))
        badge = pygame.Surface((hud_rect.width + 20, hud_rect.height + 12), pygame.SRCALPHA)
        badge.fill((0, 0, 0, 170))
        surface.blit(badge, (hud_rect.left - 10, hud_rect.top - 6))
        surface.blit(hud_text, hud_rect.topleft)
        warning = self.warning_font.render("You feel undergeared...", True, pygame.Color("#ffab40"))
        surface.blit(warning, (self.bounds.left + 40, self.bounds.top + self.bounds.height + 10))

        self.app.inventory_overlay.render(surface)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import GameApp

