from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import pygame

from inventory.manager import InventoryManager


@dataclass(frozen=True)
class PlayerClassData:
    base_hp: int
    base_mp: int
    base_atk: int
    base_def: int
    hp_per_level: int
    atk_per_level: int
    def_per_level: int
    mp_per_level: int


PLAYER_CLASS_DATA: Dict[str, PlayerClassData] = {
    "Fighter": PlayerClassData(
        base_hp=100,
        base_mp=20,
        base_atk=5,
        base_def=2,
        hp_per_level=15,
        atk_per_level=3,
        def_per_level=2,
        mp_per_level=5,
    ),
    "Sorcerer": PlayerClassData(
        base_hp=70,
        base_mp=60,
        base_atk=4,
        base_def=1,
        hp_per_level=10,
        atk_per_level=2,
        def_per_level=1,
        mp_per_level=10,
    ),
}


def required_xp(level: int) -> int:
    return 100 + 50 * (level - 1)


class Player:
    def __init__(self, name: str, player_class: str) -> None:
        if player_class not in PLAYER_CLASS_DATA:
            raise ValueError(f"Unknown player class: {player_class}")
        self.name = name or "Hero"
        self.player_class = player_class
        self.data = PLAYER_CLASS_DATA[player_class]
        self.level = 1
        self.xp = 0
        self.gold = 100
        self.inventory = InventoryManager()
        self.inventory.equipped_weapon = None
        self.inventory.equipped_shield = None

        self.max_hp = self.data.base_hp
        self.hp = self.max_hp
        self.max_mp = self.data.base_mp
        self.mp = self.max_mp
        self.base_atk = self.data.base_atk
        self.base_def = self.data.base_def

        self.speed = 180  # pixels per second
        self.rect = pygame.Rect(0, 0, 48, 64)
        self.velocity = pygame.Vector2(0, 0)

    def reset_position(self, pos: Tuple[int, int]) -> None:
        self.rect.topleft = pos

    def handle_movement(self, dt: float, blocked_tiles: Tuple[pygame.Rect, ...]) -> bool:
        keys = pygame.key.get_pressed()
        self.velocity.update(0, 0)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.velocity.x = -1
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.velocity.x = 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.velocity.y = -1
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.velocity.y = 1

        moved = False
        if self.velocity.length_squared() > 0:
            self.velocity = self.velocity.normalize()
            delta = self.velocity * self.speed * dt
            new_rect = self.rect.move(delta.x, 0)
            if not any(new_rect.colliderect(tile) for tile in blocked_tiles):
                self.rect = new_rect
                moved = True
            new_rect = self.rect.move(0, delta.y)
            if not any(new_rect.colliderect(tile) for tile in blocked_tiles):
                self.rect = new_rect
                moved = True
        return moved

    def gain_gold(self, amount: int) -> None:
        self.gold += amount

    def spend_gold(self, amount: int) -> bool:
        if self.gold >= amount:
            self.gold -= amount
            return True
        return False

    def gain_xp(self, amount: int) -> bool:
        self.xp += amount
        leveled_up = False
        while self.xp >= required_xp(self.level):
            self.xp -= required_xp(self.level)
            self.level += 1
            self.max_hp += self.data.hp_per_level
            self.base_atk += self.data.atk_per_level
            self.base_def += self.data.def_per_level
            self.max_mp += self.data.mp_per_level
            self.hp = self.max_hp
            self.mp = self.max_mp
            leveled_up = True
        return leveled_up

    def current_weapon_bonus(self) -> int:
        weapon = self.inventory.get_equipped_weapon()
        return weapon.attack_bonus if weapon else 0

    def current_shield_bonus(self) -> int:
        shield = self.inventory.get_equipped_shield()
        return shield.defense_bonus if shield else 0

    def total_attack(self) -> int:
        return self.base_atk + self.current_weapon_bonus()

    def total_defense(self) -> int:
        return self.base_def + self.current_shield_bonus()

    def take_damage(self, amount: int) -> None:
        self.hp = max(0, self.hp - amount)

    def heal(self, amount: int) -> None:
        self.hp = min(self.max_hp, self.hp + amount)

    def restore_mana(self, amount: int) -> None:
        self.mp = min(self.max_mp, self.mp + amount)

    def spend_mp(self, amount: int) -> bool:
        if self.mp >= amount:
            self.mp -= amount
            return True
        return False

    def revive_full(self) -> None:
        self.hp = self.max_hp
        self.mp = self.max_mp
        self.rect.topleft = (0, 0)

    def reset_stats_for_new_game(self) -> None:
        self.level = 1
        self.xp = 0
        self.gold = 100
        self.max_hp = self.data.base_hp
        self.hp = self.max_hp
        self.max_mp = self.data.base_mp
        self.mp = self.max_mp
        self.base_atk = self.data.base_atk
        self.base_def = self.data.base_def
        self.inventory = InventoryManager()
