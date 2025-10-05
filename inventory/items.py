from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Weapon:
    name: str
    attack_bonus: int
    price: int


@dataclass(frozen=True)
class Shield:
    name: str
    defense_bonus: int
    price: int


@dataclass(frozen=True)
class Potion:
    name: str
    restore_amount: int
    price: int
    resource: str  # "hp" or "mp"


WEAPONS: Dict[str, Weapon] = {
    "Short Sword": Weapon("Short Sword", attack_bonus=6, price=50),
    "Steel Sword": Weapon("Steel Sword", attack_bonus=12, price=120),
}

SHIELDS: Dict[str, Shield] = {
    "Wooden Shield": Shield("Wooden Shield", defense_bonus=2, price=40),
    "Iron Shield": Shield("Iron Shield", defense_bonus=5, price=110),
}

POTIONS: Dict[str, Potion] = {
    "Heal Potion": Potion("Heal Potion", restore_amount=40, price=20, resource="hp"),
    "Mana Potion": Potion("Mana Potion", restore_amount=40, price=20, resource="mp"),
}
