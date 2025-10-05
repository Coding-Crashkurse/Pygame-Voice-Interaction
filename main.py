from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional

import pygame

from constants import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SCENE_BATTLE,
    SCENE_BOSS,
    SCENE_CITY,
    SCENE_GAME_OVER,
    SCENE_SHOP,
    SCENE_START,
    SCENE_WILDERNESS,
    TARGET_FPS,
    GAME_TITLE,
)
from inventory.overlay import InventoryOverlay
from scenes.battle_scene import BattleScene
from scenes.boss_scene import BossScene
from scenes.city_scene import CityScene
from scenes.game_over_scene import GameOverScene
from scenes.shop_scene import ShopScene
from scenes.start_scene import StartScene
from scenes.wilderness_scene import FieldEnemy, WildernessScene
from utils.assets import AssetManager
from voice.service import VoiceEngine


class GameApp:
    def __init__(self) -> None:
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            print("Warning: Audio device not available, continuing without sound.")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()

        self.assets = AssetManager(Path(__file__).resolve().parent)
        self.assets.load_all()

        self.player = None
        self.voice_enabled = False
        self.voice_engine: VoiceEngine | None = None
        self.inventory_overlay = InventoryOverlay(self)
        self.merchant_stock: Dict[str, int] = {"Heal Potion": 3}

        self.scenes = {
            SCENE_START: StartScene(self),
            SCENE_CITY: CityScene(self),
            SCENE_WILDERNESS: WildernessScene(self),
            SCENE_BOSS: BossScene(self),
            SCENE_SHOP: ShopScene(self),
            SCENE_BATTLE: BattleScene(self),
            SCENE_GAME_OVER: GameOverScene(self),
        }
        self.current_scene_key = SCENE_START
        self.current_scene = self.scenes[self.current_scene_key]
        self._next_scene_key: Optional[str] = None
        self._next_scene_kwargs: Dict | None = None
        self.current_scene.on_enter()

    def change_scene(self, scene_key: str, **kwargs) -> None:
        self._next_scene_key = scene_key
        self._next_scene_kwargs = kwargs

    def start_battle(
        self,
        enemy,
        return_scene: str,
        field_enemy: Optional[FieldEnemy] = None,
        is_boss: bool = False,
        sprite_key: str = "skeleton",
    ) -> None:
        self.inventory_overlay.active = False
        self.change_scene(
            SCENE_BATTLE,
            enemy=enemy,
            return_scene=return_scene,
            field_enemy=field_enemy,
            is_boss=is_boss,
            sprite_key=sprite_key,
        )

    def end_battle(
        self, victory: bool, return_scene: str, field_enemy: Optional[FieldEnemy] = None
    ) -> None:
        if victory:
            if field_enemy is not None:
                wilderness = self.scenes.get(SCENE_WILDERNESS)
                if isinstance(wilderness, WildernessScene):
                    field_enemy.reset(wilderness.bounds)
            spawn = (
                self.player.rect.center
                if self.player
                else (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            )
            self.change_scene(return_scene, spawn=spawn)
        else:
            self.change_scene(SCENE_GAME_OVER)

    def ensure_voice_engine(self) -> VoiceEngine:
        if self.voice_engine is None:
            self.voice_engine = VoiceEngine()
        return self.voice_engine

    def reset_game(self) -> None:
        self.player = None
        self.inventory_overlay.active = False
        self.merchant_stock = {"Heal Potion": 3}

    def _process_scene_change(self) -> None:
        if self._next_scene_key is None:
            return
        self.current_scene.on_exit()
        self.current_scene_key = self._next_scene_key
        self.current_scene = self.scenes[self.current_scene_key]
        kwargs = self._next_scene_kwargs or {}
        self.current_scene.on_enter(**kwargs)
        self._next_scene_key = None
        self._next_scene_kwargs = None

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(TARGET_FPS) / 1000.0
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
            self.current_scene.handle_events(events)
            if hasattr(self.current_scene, "update"):
                self.current_scene.update(dt)
            self.current_scene.render(self.screen)
            pygame.display.flip()
            self._process_scene_change()
        if self.voice_engine:
            self.voice_engine.cleanup()
        pygame.quit()
        sys.exit()


def main() -> None:
    app = GameApp()
    app.run()


if __name__ == "__main__":
    main()
