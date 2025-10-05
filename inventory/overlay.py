from __future__ import annotations

from typing import List, Tuple

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH
from entities.player import required_xp
from inventory.items import POTIONS


class InventoryOverlay:
    def __init__(self, app: "GameApp") -> None:
        self.app = app
        self.active = False
        self.font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 20)
        self.section_order = ["Weapons", "Shields", "Potions"]
        self.section_index = 0
        self.selection_index = 0

    def toggle(self) -> None:
        self.active = not self.active
        self.selection_index = 0
        self.section_index = 0

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        if not self.active:
            return
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_i):
                    self.toggle()
                    return
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.section_index = (self.section_index + 1) % len(self.section_order)
                    self.selection_index = 0
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.section_index = (self.section_index - 1) % len(self.section_order)
                    self.selection_index = 0
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    count = self._item_count_in_section()
                    if count > 0:
                        self.selection_index = (self.selection_index + 1) % count
                elif event.key in (pygame.K_UP, pygame.K_w):
                    count = self._item_count_in_section()
                    if count > 0:
                        self.selection_index = (self.selection_index - 1) % count
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._activate_selection()

    def _item_count_in_section(self) -> int:
        section = self.section_order[self.section_index]
        if section == "Weapons":
            return len(self.app.player.inventory.get_owned_weapons())
        if section == "Shields":
            return len(self.app.player.inventory.get_owned_shields())
        return len(self.app.player.inventory.get_potions())

    def _activate_selection(self) -> None:
        player = self.app.player
        section = self.section_order[self.section_index]
        if section == "Weapons":
            weapons = player.inventory.get_owned_weapons()
            if not weapons:
                return
            weapon = weapons[self.selection_index][0]
            player.inventory.equip_weapon(weapon.name)
            self.app.assets.play_sound("heavy_hit", volume=0.4)
        elif section == "Shields":
            shields = player.inventory.get_owned_shields()
            if not shields:
                return
            shield = shields[self.selection_index][0]
            player.inventory.equip_shield(shield.name)
            self.app.assets.play_sound("heavy_hit", volume=0.4)
        else:
            potions = player.inventory.get_potions()
            if not potions:
                return
            potion, _ = potions[self.selection_index]
            effect = player.inventory.consume_potion(potion.name)
            if effect.resource == "hp":
                player.heal(effect.restore_amount)
                self.app.assets.play_sound("drink", volume=0.6)
            else:
                player.restore_mana(effect.restore_amount)
                self.app.assets.play_sound("mana_drink", volume=0.6)

    def render(self, surface: pygame.Surface) -> None:
        if not self.active:
            return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 10, 200))
        surface.blit(overlay, (0, 0))

        panel_rect = pygame.Rect(200, 80, SCREEN_WIDTH - 400, SCREEN_HEIGHT - 160)
        pygame.draw.rect(surface, (30, 30, 40), panel_rect, border_radius=12)
        pygame.draw.rect(surface, (120, 200, 255), panel_rect, 3, border_radius=12)

        player = self.app.player
        header = self.font.render(f"{player.name} - Level {player.level}", True, pygame.Color("white"))
        surface.blit(header, (panel_rect.left + 30, panel_rect.top + 20))
        xp_text = self.small_font.render(f"XP: {player.xp} / {required_xp(player.level)}", True, pygame.Color("white"))
        hp_text = self.small_font.render(f"HP: {player.hp}/{player.max_hp}", True, pygame.Color("white"))
        mp_text = self.small_font.render(f"MP: {player.mp}/{player.max_mp}", True, pygame.Color("white"))
        gold_text = self.small_font.render(f"Gold: {player.gold}", True, pygame.Color("white"))
        surface.blit(xp_text, (panel_rect.left + 30, panel_rect.top + 60))
        surface.blit(hp_text, (panel_rect.left + 30, panel_rect.top + 90))
        surface.blit(mp_text, (panel_rect.left + 30, panel_rect.top + 120))
        surface.blit(gold_text, (panel_rect.left + 30, panel_rect.top + 150))

        equipped_weapon = player.inventory.get_equipped_weapon()
        equipped_shield = player.inventory.get_equipped_shield()
        eq_weapon_text = self.small_font.render(
            f"Equipped Weapon: {equipped_weapon.name if equipped_weapon else 'None'}",
            True,
            pygame.Color("white"),
        )
        eq_shield_text = self.small_font.render(
            f"Equipped Shield: {equipped_shield.name if equipped_shield else 'None'}",
            True,
            pygame.Color("white"),
        )
        surface.blit(eq_weapon_text, (panel_rect.left + 30, panel_rect.top + 180))
        surface.blit(eq_shield_text, (panel_rect.left + 30, panel_rect.top + 210))

        instructions = self.small_font.render("Arrows: navigate | Enter: equip/use | Esc/I: back", True, pygame.Color("#b0bec5"))
        surface.blit(instructions, (panel_rect.left + 30, panel_rect.bottom - 50))

        section_title = self.font.render(self.section_order[self.section_index], True, pygame.Color("#ffcc80"))
        title_y = panel_rect.top + 250
        surface.blit(section_title, (panel_rect.centerx - section_title.get_width() // 2, title_y))

        list_rect = pygame.Rect(panel_rect.left + 60, title_y + 45, panel_rect.width - 120, panel_rect.bottom - (title_y + 115))
        items = self._items_for_section()
        for idx, (label, extra) in enumerate(items):
            is_selected = idx == self.selection_index
            color = pygame.Color("#ffe082") if is_selected else pygame.Color("white")
            text = self.small_font.render(label, True, color)
            surface.blit(text, (list_rect.left, list_rect.top + idx * 30))
            if extra:
                extra_text = self.small_font.render(extra, True, color)
                surface.blit(extra_text, (list_rect.right - extra_text.get_width(), list_rect.top + idx * 30))

    def _items_for_section(self) -> List[Tuple[str, str]]:
        player = self.app.player
        section = self.section_order[self.section_index]
        if section == "Weapons":
            items = []
            for weapon, count in player.inventory.get_owned_weapons():
                equipped = player.inventory.equipped_weapon == weapon.name
                label = f"{weapon.name} (+{weapon.attack_bonus} ATK)"
                extra = f"x{count}{' [Equipped]' if equipped else ''}"
                items.append((label, extra))
            return items
        if section == "Shields":
            items = []
            for shield, count in player.inventory.get_owned_shields():
                equipped = player.inventory.equipped_shield == shield.name
                label = f"{shield.name} (+{shield.defense_bonus} DEF)"
                extra = f"x{count}{' [Equipped]' if equipped else ''}"
                items.append((label, extra))
            return items
        items = []
        for potion, count in player.inventory.get_potions():
            label = f"{potion.name} (+{potion.restore_amount} {potion.resource.upper()})"
            extra = f"x{count}"
            items.append((label, extra))
        return items


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import GameApp


