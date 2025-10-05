from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import pygame


@dataclass
class EnemyAttack:
    name: str
    base_damage: int
    variance: int

    def roll_damage(self) -> int:
        return self.base_damage + random.randint(-self.variance, self.variance)


class Enemy:
    def __init__(self, name: str, max_hp: int, defense: int, attacks: Sequence[EnemyAttack], gold_reward: int, xp_reward: int) -> None:
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.defense = defense
        self.attacks = list(attacks)
        self.gold_reward = gold_reward
        self.xp_reward = xp_reward

    def is_defeated(self) -> bool:
        return self.hp <= 0

    def take_damage(self, amount: int) -> None:
        self.hp = max(0, self.hp - amount)

    def choose_attack(self) -> EnemyAttack:
        return random.choice(self.attacks)

    def reset(self) -> None:
        self.hp = self.max_hp


SKELETON_TEMPLATE = Enemy(
    name="Skeleton",
    max_hp=50,
    defense=1,
    attacks=[
        EnemyAttack("Slash", 10, 2),
        EnemyAttack("Stab", 12, 2),
    ],
    gold_reward=20,
    xp_reward=50,
)

BLOB_TEMPLATE = Enemy(
    name="Blob",
    max_hp=45,
    defense=0,
    attacks=[
        EnemyAttack("Bounce", 9, 2),
        EnemyAttack("Acid Drip", 11, 2),
    ],
    gold_reward=20,
    xp_reward=50,
)

BOSS_TEMPLATE = Enemy(
    name="Ancient Golem",
    max_hp=300,
    defense=3,
    attacks=[
        EnemyAttack("Crush", 18, 3),
        EnemyAttack("Earthshatter", 24, 3),
    ],
    gold_reward=0,
    xp_reward=0,
)


def clone_enemy(template: Enemy) -> Enemy:
    return Enemy(
        name=template.name,
        max_hp=template.max_hp,
        defense=template.defense,
        attacks=template.attacks,
        gold_reward=template.gold_reward,
        xp_reward=template.xp_reward,
    )


class WanderBehaviour:
    """Controls simple wandering for field enemies."""

    def __init__(self, rect: pygame.Rect, bounds: pygame.Rect, speed: float = 60.0) -> None:
        self.rect = rect
        self.bounds = bounds
        self.speed = speed
        self.direction = pygame.Vector2(0, 0)
        self._direction_timer = 0.0
        self._change_interval = random.uniform(1.0, 2.0)

    def update(self, dt: float, obstacles: Sequence[pygame.Rect]) -> None:
        self._direction_timer += dt
        if self._direction_timer >= self._change_interval:
            self._direction_timer = 0.0
            self._change_interval = random.uniform(1.0, 2.0)
            self.direction = random.choice([
                pygame.Vector2(1, 0),
                pygame.Vector2(-1, 0),
                pygame.Vector2(0, 1),
                pygame.Vector2(0, -1),
                pygame.Vector2(0, 0),
            ])

        if self.direction.length_squared() == 0:
            return

        delta = self.direction * self.speed * dt
        new_rect = self.rect.move(delta.x, 0)
        if self.bounds.contains(new_rect) and not any(new_rect.colliderect(obs) for obs in obstacles):
            self.rect = new_rect
        else:
            self.direction.x *= -1
        new_rect = self.rect.move(0, delta.y)
        if self.bounds.contains(new_rect) and not any(new_rect.colliderect(obs) for obs in obstacles):
            self.rect = new_rect
        else:
            self.direction.y *= -1
