from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame

SPRITE_FILES: Dict[str, str] = {
    "warrior": "warrior.png",
    "sorcerer": "sorcerer.png",
    "merchant": "trader.png",
    "skeleton": "skeleton_enemy.png",
    "blob": "slime_enemy.png",
    "boss": "end_boss.png",
    "short_sword": "cheap_sword.png",
    "steel_sword": "expensive_sword.png",
    "wooden_shield": "cheap_shield.png",
    "iron_shield": "expensive_shield.png",
    "heal_potion": "healpotion.png",
    "mana_potion": "manapotion.png",
    "house_1": "house_1.png",
    "house_2": "house_2.png",
    "forge": "schmiede.png",
    "tree": "tree.png",
    "tree_2": "tree_2.png",
    "bush": "kleiner_busch.png",
    "rock": "rock.png",
    "wall": "wall.png",
    "door": "door.png",
    "lantern": "lantern.png",
    "barrel": "fass.png",
    "chest": "schatztruhe.png",
}

SOUND_FILES: Dict[str, str] = {
    "monster_death": "epic_monster_death.mp3",
    "error": "error.mp3",
    "footsteps": "footsteps.mp3",
    "player_hit": "get_hit_grunt.mp3",
    "gold": "gold_coins_clinking.mp3",
    "heavy_hit": "heavy_hit_sound.mp3",
    "level_up": "levelup.mp3",
    "drink": "liquid_glug_and_swal.mp3",
    "mana_drink": "magical_shimmering_drink_sound.mp3",
    "collapse": "short_collapse_sound.mp3",
    "slime_hit": "slimey_splat_mixed.mp3",
}


class AssetManager:
    """Loads and caches sprite and sound assets."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.sprite_dir = self.root / "sprites"
        self.sound_dir = self.root / "sounds"
        self._image_cache: Dict[str, pygame.Surface] = {}
        self._scaled_cache: Dict[Tuple[str, Tuple[int, int]], pygame.Surface] = {}
        self._sound_cache: Dict[str, Optional[pygame.mixer.Sound]] = {}

    def load_all(self) -> None:
        for key, filename in SPRITE_FILES.items():
            path = self.sprite_dir / filename
            image = pygame.image.load(str(path)).convert_alpha()
            self._image_cache[key] = image
        mixer_ready = pygame.mixer.get_init() is not None
        for key, filename in SOUND_FILES.items():
            path = self.sound_dir / filename
            if mixer_ready:
                self._sound_cache[key] = pygame.mixer.Sound(str(path))
            else:
                self._sound_cache[key] = None

    def get_image(self, key: str, size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
        if key not in self._image_cache:
            raise KeyError(f"Unknown sprite key: {key}")
        image = self._image_cache[key]
        if size is None:
            return image
        cache_key = (key, size)
        if cache_key not in self._scaled_cache:
            self._scaled_cache[cache_key] = pygame.transform.smoothscale(image, size)
        return self._scaled_cache[cache_key]

    def play_sound(self, key: str, volume: float = 1.0) -> None:
        if not pygame.mixer.get_init():
            return
        sound = self._sound_cache.get(key)
        if sound is None:
            return
        sound.set_volume(max(0.0, min(volume, 1.0)))
        sound.play()
