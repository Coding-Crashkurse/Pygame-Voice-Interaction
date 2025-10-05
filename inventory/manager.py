from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from inventory.items import POTIONS, SHIELDS, WEAPONS, Potion, Shield, Weapon


class InventoryManager:
    def __init__(self) -> None:
        self.weapons: Dict[str, int] = {name: 0 for name in WEAPONS}
        self.shields: Dict[str, int] = {name: 0 for name in SHIELDS}
        self.potions: Dict[str, int] = {name: 0 for name in POTIONS}
        self.equipped_weapon: Optional[str] = None
        self.equipped_shield: Optional[str] = None

    def add_weapon(self, name: str) -> None:
        if name not in self.weapons:
            raise KeyError(f"Unknown weapon: {name}")
        self.weapons[name] += 1

    def add_shield(self, name: str) -> None:
        if name not in self.shields:
            raise KeyError(f"Unknown shield: {name}")
        self.shields[name] += 1

    def add_potion(self, name: str, amount: int = 1) -> None:
        if name not in self.potions:
            raise KeyError(f"Unknown potion: {name}")
        self.potions[name] += amount

    def consume_potion(self, name: str) -> Potion:
        if self.potions.get(name, 0) <= 0:
            raise ValueError(f"No potion named {name} available")
        self.potions[name] -= 1
        return POTIONS[name]

    def get_owned_weapons(self) -> List[Tuple[Weapon, int]]:
        return [(WEAPONS[name], count) for name, count in self.weapons.items() if count > 0]

    def get_owned_shields(self) -> List[Tuple[Shield, int]]:
        return [(SHIELDS[name], count) for name, count in self.shields.items() if count > 0]

    def get_potions(self) -> List[Tuple[Potion, int]]:
        return [(POTIONS[name], count) for name, count in self.potions.items() if count > 0]

    def equip_weapon(self, name: str) -> None:
        if self.weapons.get(name, 0) <= 0:
            raise ValueError(f"Weapon {name} not owned")
        self.equipped_weapon = name

    def equip_shield(self, name: str) -> None:
        if self.shields.get(name, 0) <= 0:
            raise ValueError(f"Shield {name} not owned")
        self.equipped_shield = name

    def get_equipped_weapon(self) -> Optional[Weapon]:
        if self.equipped_weapon:
            return WEAPONS[self.equipped_weapon]
        return None

    def get_equipped_shield(self) -> Optional[Shield]:
        if self.equipped_shield:
            return SHIELDS[self.equipped_shield]
        return None
