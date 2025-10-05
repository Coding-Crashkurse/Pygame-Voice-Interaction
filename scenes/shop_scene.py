from __future__ import annotations

from typing import List

import pygame
from difflib import get_close_matches

from constants import SCREEN_HEIGHT, SCREEN_WIDTH, SCENE_CITY
from inventory.items import POTIONS, SHIELDS, WEAPONS
from merchant_dialogue import VoiceChannel, create_channel
from voice.assistant import PurchaseOutcome
from scenes.base import BaseScene
from ui.components import Button


class ShopScene(BaseScene):
    def __init__(self, app: "GameApp") -> None:
        super().__init__(app)
        self.font = pygame.font.SysFont("arial", 28)
        self.small_font = pygame.font.SysFont("arial", 22)
        self.items = self._build_items()
        self.buttons: List[Button] = []
        self.back_button: Button | None = None
        self.feedback: str = ""
        self.channel = None
        self.row_height = 72
        self.list_height = self.row_height * 4
        self.scroll_offset = 0.0

    def _build_items(self):
        return [
            {
                "name": "Short Sword",
                "type": "weapon",
                "price": WEAPONS["Short Sword"].price,
                "sprite": "short_sword",
                "stock_key": None,
                "bonus": "+6 ATK",
            },
            {
                "name": "Steel Sword",
                "type": "weapon",
                "price": WEAPONS["Steel Sword"].price,
                "sprite": "steel_sword",
                "stock_key": None,
                "bonus": "+12 ATK",
            },
            {
                "name": "Wooden Shield",
                "type": "shield",
                "price": SHIELDS["Wooden Shield"].price,
                "sprite": "wooden_shield",
                "stock_key": None,
                "bonus": "+2 DEF",
            },
            {
                "name": "Iron Shield",
                "type": "shield",
                "price": SHIELDS["Iron Shield"].price,
                "sprite": "iron_shield",
                "stock_key": None,
                "bonus": "+5 DEF",
            },
            {
                "name": "Heal Potion",
                "type": "potion",
                "price": POTIONS["Heal Potion"].price,
                "sprite": "heal_potion",
                "stock_key": "Heal Potion",
                "bonus": "Restores 40 HP",
            },
            {
                "name": "Mana Potion",
                "type": "potion",
                "price": POTIONS["Mana Potion"].price,
                "sprite": "mana_potion",
                "stock_key": None,
                "bonus": "Restores 40 MP",
            },
        ]

    def on_enter(self, **kwargs) -> None:
        self.scroll_offset = 0.0
        self._create_buttons()
        self.feedback = ""
        self._ensure_channel()

    def on_exit(self) -> None:
        if self.channel and hasattr(self.channel, "close"):
            try:
                self.channel.close()  # type: ignore[attr-defined]
            except Exception:
                pass
        self.channel = None

    def _ensure_channel(self) -> None:
        if self.channel and hasattr(self.channel, "close"):
            try:
                self.channel.close()  # type: ignore[attr-defined]
            except Exception:
                pass
        kind = "voice" if getattr(self.app, "voice_enabled", False) else "buttons"
        self.channel = create_channel(
            kind, self._render_ui, self._handle_input, scene=self
        )

    def _create_buttons(self) -> None:
        self.buttons.clear()
        start_y = 180
        for idx, _item in enumerate(self.items):
            rect = pygame.Rect(SCREEN_WIDTH - 260, start_y + idx * 80, 120, 40)
            button = Button(
                rect, "Buy", self.small_font, lambda index=idx: self._purchase(index)
            )
            self.buttons.append(button)
        back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT - 100, 160, 50)
        self.back_button = Button(back_rect, "Back", self.font, self._return_to_city)

    def _return_to_city(self) -> None:
        player = self.app.player
        spawn = (
            player.rect.center if player else (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        )
        self.app.change_scene(SCENE_CITY, spawn=spawn)

    def _handle_input(self, events):
        for event in events:
            if event.type == pygame.MOUSEWHEEL:
                self._scroll(-event.y * (self.row_height / 2))
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self._return_to_city()
                    return
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    self._scroll(self.row_height / 1.5)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    self._scroll(-self.row_height / 1.5)
                elif event.key == pygame.K_PAGEDOWN:
                    self._scroll(self.list_height)
                elif event.key == pygame.K_PAGEUP:
                    self._scroll(-self.list_height)
        for button in self.buttons:
            button.handle_events(events)
        if self.back_button:
            self.back_button.handle_events(events)

    def handle_events(self, events):
        if self.channel:
            self.channel.handle_input(events)
        else:
            self._handle_input(events)

    def _purchase(self, index: int) -> None:
        item = self.items[index]
        outcome = self._attempt_purchase(item)
        self.feedback = outcome.message

    def _attempt_purchase(self, item: dict) -> PurchaseOutcome:
        player = self.app.player
        stock_key = item.get("stock_key")
        price = int(item["price"])
        remaining = self.app.merchant_stock.get(stock_key, 0) if stock_key else None

        if stock_key and remaining is not None and remaining <= 0:
            self.app.assets.play_sound("error", volume=0.5)
            return PurchaseOutcome(
                False, item["name"], f"{item['name']} is out of stock!", None
            )

        if not player.spend_gold(price):
            self.app.assets.play_sound("error", volume=0.6)
            return PurchaseOutcome(
                False, item["name"], f"Not enough gold for {item['price']}g.", None
            )

        if item["type"] == "weapon":
            player.inventory.add_weapon(item["name"])
            if player.inventory.equipped_weapon is None:
                player.inventory.equip_weapon(item["name"])
        elif item["type"] == "shield":
            player.inventory.add_shield(item["name"])
            if player.inventory.equipped_shield is None:
                player.inventory.equip_shield(item["name"])
        else:
            player.inventory.add_potion(item["name"])

        if stock_key:
            self.app.merchant_stock[stock_key] = max(0, (remaining or 0) - 1)

        self.app.assets.play_sound("gold", volume=0.6)
        return PurchaseOutcome(
            True, item["name"], f"Bought {item['name']} for {price}g.", price
        )

    def attempt_voice_purchase(self, raw_item_name: str | None) -> PurchaseOutcome:
        if not raw_item_name or not raw_item_name.strip():
            self.app.assets.play_sound("error", volume=0.4)
            return PurchaseOutcome(
                False, None, "I did not catch which item you want.", None
            )
        match = self._resolve_item_name(raw_item_name)
        if match is None:
            self.app.assets.play_sound("error", volume=0.4)
            return PurchaseOutcome(
                False, None, f"I do not have '{raw_item_name}' in stock.", None
            )
        _index, item = match
        outcome = self._attempt_purchase(item)
        self.feedback = outcome.message
        return outcome

    def _resolve_item_name(self, raw_name: str) -> tuple[int, dict] | None:
        lowered = raw_name.lower().strip()
        if not lowered:
            return None
        name_lookup = {
            item["name"].lower(): (idx, item) for idx, item in enumerate(self.items)
        }
        if lowered in name_lookup:
            return name_lookup[lowered]
        matches = get_close_matches(lowered, list(name_lookup.keys()), n=1, cutoff=0.6)
        if matches:
            return name_lookup[matches[0]]
        return None

    def _render_ui(self, surface: pygame.Surface) -> None:
        surface.fill((25, 30, 36))
        panel_width = 760
        panel_height = int(self.list_height + 220)
        voice_overlay = isinstance(self.channel, VoiceChannel)
        if voice_overlay:
            panel_left = 48
        else:
            panel_left = (SCREEN_WIDTH - panel_width) // 2
        panel_top = max(40, (SCREEN_HEIGHT - panel_height) // 2)
        panel = pygame.Rect(panel_left, panel_top, panel_width, panel_height)
        pygame.draw.rect(surface, (40, 50, 60), panel, border_radius=16)
        pygame.draw.rect(surface, (180, 200, 220), panel, 3, border_radius=16)

        title = self.font.render("Merchant Shop", True, pygame.Color("white"))
        surface.blit(title, (panel.left + 32, panel.top + 20))
        gold_text = self.small_font.render(
            f"Your Gold: {self.app.player.gold}", True, pygame.Color("#ffd54f")
        )
        surface.blit(
            gold_text, (panel.right - gold_text.get_width() - 32, panel.top + 24)
        )

        list_rect = pygame.Rect(
            panel.left + 40, panel.top + 110, panel.width - 80, self.list_height
        )
        list_surface = pygame.Surface(list_rect.size, pygame.SRCALPHA)
        list_surface.fill((0, 0, 0, 0))

        header_labels = ["Item", "Bonus", "Price", "Stock"]
        header_positions = [
            90,
            260,
            400,
            500,
        ]
        header_y = -24
        for label, x in zip(header_labels, header_positions):
            header = self.small_font.render(label, True, pygame.Color("#90caf9"))
            list_surface.blit(header, (x, header_y))

        col_icon = 30
        col_item = 90
        col_bonus = 260
        col_price = 400
        col_stock = 500
        button_width = 110
        button_height = 44
        button_local_x = list_rect.width - button_width - 10

        max_scroll = max(0.0, len(self.items) * self.row_height - self.list_height)
        self.scroll_offset = max(0.0, min(self.scroll_offset, max_scroll))

        for idx, item in enumerate(self.items):
            row_y = idx * self.row_height - self.scroll_offset
            button = self.buttons[idx]

            if item["stock_key"]:
                remaining = self.app.merchant_stock.get(item["stock_key"], 0)
                out_of_stock = remaining <= 0
                stock_display = "Out" if out_of_stock else str(remaining)
            else:
                remaining = None
                out_of_stock = False
                stock_display = "\u221e"

            button.enabled = (not out_of_stock) and (
                self.app.player.gold >= item["price"]
            )

            if row_y + self.row_height < 0 or row_y > self.list_height:
                button.rect = pygame.Rect(-1000, -1000, 0, 0)
                continue

            row_rect = pygame.Rect(0, int(row_y), list_rect.width, self.row_height - 6)
            row_color = (50, 60, 72) if idx % 2 == 0 else (46, 54, 66)
            pygame.draw.rect(list_surface, row_color, row_rect, border_radius=12)

            icon = self.app.assets.get_image(item["sprite"], (48, 48))
            icon_rect = icon.get_rect(
                center=(col_icon, int(row_y + self.row_height / 2))
            )
            list_surface.blit(icon, icon_rect)

            item_text = self.small_font.render(
                item["name"], True, pygame.Color("white")
            )
            list_surface.blit(item_text, (col_item, int(row_y + 6)))

            bonus_text = self.small_font.render(
                item["bonus"], True, pygame.Color("#c5e1a5")
            )
            list_surface.blit(bonus_text, (col_bonus, int(row_y + 6)))

            price_text = self.small_font.render(
                f"{item['price']}g", True, pygame.Color("#ffd54f")
            )
            list_surface.blit(price_text, (col_price, int(row_y + 6)))

            stock_color = (
                pygame.Color("#e57373") if out_of_stock else pygame.Color("white")
            )
            stock_text = self.small_font.render(stock_display, True, stock_color)
            list_surface.blit(stock_text, (col_stock, int(row_y + 6)))

            button_local_rect = pygame.Rect(
                button_local_x,
                int(row_y + (self.row_height - button_height) / 2),
                button_width,
                button_height,
            )
            self._draw_button_sprite(
                list_surface,
                button_local_rect,
                button.text,
                out_of_stock or not button.enabled,
            )
            button.rect = button_local_rect.move(list_rect.left, list_rect.top)

        surface.blit(list_surface, list_rect.topleft)

        instructions = self.small_font.render(
            "Scroll: Mouse wheel / Arrows | Esc: Back", True, pygame.Color("#b0bec5")
        )
        surface.blit(instructions, (panel.left + 32, panel.bottom - 80))

        if self.back_button:
            self.back_button.rect = pygame.Rect(
                panel.centerx - 70, panel.bottom - 62, 140, 48
            )
            self._render_button(surface, self.back_button)

        if self.feedback:
            feedback_text = self.small_font.render(
                self.feedback, True, pygame.Color("#ffcc80")
            )
            surface.blit(feedback_text, (panel.left + 32, panel.bottom - 116))

    def _scroll(self, delta: float) -> None:
        max_scroll = max(0.0, len(self.items) * self.row_height - self.list_height)
        self.scroll_offset = max(0.0, min(self.scroll_offset + delta, max_scroll))

    def _draw_button_sprite(
        self, surface: pygame.Surface, rect: pygame.Rect, text: str, disabled: bool
    ) -> None:
        color = pygame.Color("#455a64") if disabled else pygame.Color("#1e88e5")
        pygame.draw.rect(surface, color, rect, border_radius=6)
        pygame.draw.rect(surface, pygame.Color("white"), rect, 2, border_radius=6)
        text_color = pygame.Color("#b0bec5") if disabled else pygame.Color("white")
        text_surface = self.small_font.render(text, True, text_color)
        surface.blit(text_surface, text_surface.get_rect(center=rect.center))

    def _render_button(
        self, surface: pygame.Surface, button: Button, disabled: bool = False
    ) -> None:
        color = (
            pygame.Color("#455a64")
            if disabled or not button.enabled
            else pygame.Color("#1e88e5")
        )
        pygame.draw.rect(surface, color, button.rect, border_radius=6)
        pygame.draw.rect(
            surface, pygame.Color("white"), button.rect, 2, border_radius=6
        )
        text_color = (
            pygame.Color("#b0bec5")
            if disabled or not button.enabled
            else pygame.Color("white")
        )
        text = button.font.render(button.text, True, text_color)
        text_rect = text.get_rect(center=button.rect.center)
        surface.blit(text, text_rect)

    def render(self, surface: pygame.Surface) -> None:
        if self.channel:
            self.channel.render(surface)
        else:
            self._render_ui(surface)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import GameApp
