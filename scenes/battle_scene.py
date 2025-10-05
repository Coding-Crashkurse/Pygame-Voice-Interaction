from __future__ import annotations

import math
from typing import List

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH
from scenes.base import BaseScene
from utils.config import ATTACK_ANIMATION_SECONDS


class BattleScene(BaseScene):
    def __init__(self, app: "GameApp") -> None:
        super().__init__(app)
        self.enemy = None
        self.enemy_sprite_key: str = ""
        self.return_scene: str = ""
        self.from_field_enemy = None
        self.is_boss = False
        self.state = "player"
        self.font = pygame.font.SysFont("arial", 28)
        self.small_font = pygame.font.SysFont("arial", 22)
        self.status_font = pygame.font.SysFont("arial", 20)
        self.log: List[str] = []
        self.player_action_rect = pygame.Rect(0, 0, 200, 60)
        self.player_heal_rect = pygame.Rect(0, 0, 200, 60)
        self._display_player_hp = 0.0
        self._display_enemy_hp = 0.0
        self.attack_anim_duration = max(0.05, ATTACK_ANIMATION_SECONDS)
        self.animation_phase: str | None = None
        self.animation_timer: float = 0.0
        self.animation_payload: dict | None = None

    def on_enter(self, **kwargs) -> None:
        enemy = kwargs.get("enemy")
        if enemy is None:
            raise ValueError("BattleScene requires an enemy")
        self.enemy = enemy
        self.enemy_sprite_key = kwargs.get("sprite_key", "skeleton")
        self.return_scene = kwargs.get("return_scene", "city")
        self.from_field_enemy = kwargs.get("field_enemy")
        self.is_boss = kwargs.get("is_boss", False)
        self.state = "player"
        self.log = [f"A wild {self.enemy.name} appears!"]
        self._display_player_hp = float(self.app.player.hp)
        self._display_enemy_hp = float(self.enemy.hp)
        self.animation_phase = None
        self.animation_timer = 0.0
        self.animation_payload = None

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.state == "player" and self.animation_phase is None:
                    if event.key in (
                        pygame.K_RETURN,
                        pygame.K_SPACE,
                        pygame.K_KP_ENTER,
                    ):
                        self._player_attack()
                    elif event.key in (pygame.K_h, pygame.K_p):
                        self._player_use_heal_potion()
                elif self.state == "victory" and event.key in (
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                    pygame.K_KP_ENTER,
                ):
                    self._finish_battle()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "player" and self.animation_phase is None:
                    if self.player_action_rect.collidepoint(event.pos):
                        self._player_attack()
                    elif self.player_heal_rect.collidepoint(event.pos):
                        self._player_use_heal_potion()
                elif self.state == "victory":
                    self._finish_battle()

    def update(self, dt: float) -> None:
        player = self.app.player
        approach_speed = 300 * dt
        if abs(self._display_player_hp - player.hp) <= approach_speed:
            self._display_player_hp = float(player.hp)
        else:
            direction = 1 if self._display_player_hp < player.hp else -1
            self._display_player_hp += direction * approach_speed

        if abs(self._display_enemy_hp - self.enemy.hp) <= approach_speed:
            self._display_enemy_hp = float(self.enemy.hp)
        else:
            direction = 1 if self._display_enemy_hp < self.enemy.hp else -1
            self._display_enemy_hp += direction * approach_speed

        if self.animation_phase:
            self.animation_timer = max(0.0, self.animation_timer - dt)
            if self.animation_timer == 0.0:
                self._complete_animation()

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((20, 20, 40))
        battlefield = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT - 160)
        pygame.draw.rect(surface, (30, 40, 80), battlefield)
        pygame.draw.rect(surface, (80, 100, 160), battlefield, 4)

        enemy_img = self.app.assets.get_image(
            self.enemy_sprite_key, (220, 200) if self.is_boss else (160, 140)
        )
        enemy_rect = enemy_img.get_rect(midtop=(int(SCREEN_WIDTH * 0.7), 160))

        player_sprite_key = (
            "warrior" if self.app.player.player_class == "Fighter" else "sorcerer"
        )
        player_img = self.app.assets.get_image(player_sprite_key, (140, 180))
        base_player_rect = player_img.get_rect(
            midbottom=(int(SCREEN_WIDTH * 0.25), battlefield.bottom - 40)
        )

        player_rect, enemy_draw_rect = self._apply_animation_offsets(
            base_player_rect, enemy_rect
        )

        surface.blit(enemy_img, enemy_draw_rect.topleft)
        surface.blit(player_img, player_rect.topleft)

        self._draw_attack_flash(surface, player_rect, enemy_draw_rect)
        self._draw_status_panels(surface, player_rect, enemy_draw_rect)
        self._draw_bars(surface)
        self._draw_action_panel(surface)

    def _player_attack(self) -> None:
        if self.state != "player" or self.animation_phase is not None:
            return
        player = self.app.player
        weapon = player.inventory.get_equipped_weapon()
        base_attack = (
            player.base_atk
            + (player.level - 1) * 2
            + (weapon.attack_bonus if weapon else 0)
        )
        damage = max(1, base_attack - self.enemy.defense)
        mp_spent = False
        if player.player_class == "Sorcerer" and player.mp >= 5:
            player.spend_mp(5)
            damage += 5
            mp_spent = True
        attack_name = weapon.name if weapon else "Fist Hit"
        message = f"{player.name} uses {attack_name}! {damage} damage"
        if mp_spent:
            message += " (+5 MP burst)"
        payload = {
            "turn": "player",
            "damage": damage,
            "message": message,
        }
        self.animation_phase = "player"
        self.animation_timer = self.attack_anim_duration
        self.animation_payload = payload
        self.state = "anim"
        sfx_key = "heavy_hit" if self.enemy_sprite_key != "blob" else "slime_hit"
        self.app.assets.play_sound(sfx_key, volume=0.5)


def _player_use_heal_potion(self) -> None:
    if self.state != "player" or self.animation_phase is not None:
        return
    player = self.app.player
    if player.hp >= player.max_hp:
        self.app.assets.play_sound("error", volume=0.4)
        self._push_log("HP is already full!")
        return
    heal_potions = player.inventory.potions.get("Heal Potion", 0)
    if heal_potions <= 0:
        self.app.assets.play_sound("error", volume=0.4)
        self._push_log("No Heal Potions left!")
        return
    potion = player.inventory.consume_potion("Heal Potion")
    before = player.hp
    player.heal(potion.restore_amount)
    restored = player.hp - before
    self.app.assets.play_sound("drink", volume=0.6)
    self._push_log(f"{player.name} uses {potion.name}! Restored {restored} HP.")
    self.animation_phase = "enemy"
    self.animation_payload = self._prepare_enemy_attack()
    self.animation_timer = self.attack_anim_duration
    self.state = "anim"

    def _prepare_enemy_attack(self) -> dict:
        attack = self.enemy.choose_attack()
        raw_damage = attack.roll_damage()
        player = self.app.player
        defense = player.base_def + (player.level - 1) + player.current_shield_bonus()
        damage = max(1, raw_damage - defense)
        message = f"{self.enemy.name} uses {attack.name}! {damage} damage"
        return {
            "turn": "enemy",
            "damage": damage,
            "message": message,
        }

    def _complete_animation(self) -> None:
        if not self.animation_payload:
            self.animation_phase = None
            return
        payload = self.animation_payload
        self.animation_payload = None
        phase = payload["turn"]
        if phase == "player":
            self.enemy.take_damage(payload["damage"])
            self._push_log(payload["message"])
            if self.enemy.is_defeated():
                self.animation_phase = None
                self._handle_victory()
            else:
                self.animation_phase = "enemy"
                self.animation_payload = self._prepare_enemy_attack()
                self.animation_timer = self.attack_anim_duration
                self.app.assets.play_sound("player_hit", volume=0.6)
        elif phase == "enemy":
            player = self.app.player
            player.take_damage(payload["damage"])
            self._push_log(payload["message"])
            self.animation_phase = None
            if player.hp <= 0:
                self._handle_defeat()
            else:
                self.state = "player"

    def _handle_victory(self) -> None:
        player = self.app.player
        gold_gain = self.enemy.gold_reward
        xp_gain = self.enemy.xp_reward
        if gold_gain:
            player.gain_gold(gold_gain)
            self.app.assets.play_sound("gold", volume=0.5)
        leveled = False
        if xp_gain:
            leveled = player.gain_xp(xp_gain)
        if xp_gain or gold_gain:
            self._push_log(f"Gained {xp_gain} XP and {gold_gain}g")
        death_sfx = "monster_death" if self.is_boss else "collapse"
        if not self.is_boss and self.enemy_sprite_key == "blob":
            death_sfx = "slime_hit"
        self.app.assets.play_sound(death_sfx, volume=0.7 if self.is_boss else 0.5)
        if leveled:
            self.app.assets.play_sound("level_up", volume=0.7)
            self._push_log("Level up! Stats restored.")
        self._push_log("Enemy defeated!")
        self.state = "victory"

    def _handle_defeat(self) -> None:
        self._push_log("You were defeated...")
        self.app.assets.play_sound("collapse", volume=0.7)
        self.state = "defeat"
        self.animation_phase = None
        self.animation_payload = None
        self.app.end_battle(False, self.return_scene)

    def _finish_battle(self) -> None:
        if self.state == "victory":
            self.app.end_battle(
                True, self.return_scene, field_enemy=self.from_field_enemy
            )

    def _push_log(self, text: str) -> None:
        self.log.append(text)
        if len(self.log) > 4:
            self.log = self.log[-4:]

    def _apply_animation_offsets(
        self, player_rect: pygame.Rect, enemy_rect: pygame.Rect
    ) -> tuple[pygame.Rect, pygame.Rect]:
        if not self.animation_phase or self.attack_anim_duration <= 0:
            return player_rect, enemy_rect
        progress = 1.0 - (self.animation_timer / self.attack_anim_duration)
        shake = int(12 * math.sin(progress * math.pi))
        if self.animation_phase == "player":
            return player_rect.move(shake, 0), enemy_rect.move(-shake // 3, 0)
        if self.animation_phase == "enemy":
            return player_rect.move(shake // 3, 0), enemy_rect.move(-shake, 0)
        return player_rect, enemy_rect

    def _draw_attack_flash(
        self, surface: pygame.Surface, player_rect: pygame.Rect, enemy_rect: pygame.Rect
    ) -> None:
        if not self.animation_phase or self.attack_anim_duration <= 0:
            return
        progress = 1.0 - (self.animation_timer / self.attack_anim_duration)
        if progress < 0.6:
            return
        intensity = min(180, int(255 * (progress - 0.6) / 0.4))
        flash_surface = pygame.Surface((120, 120), pygame.SRCALPHA)
        flash_surface.fill((255, 255, 255, intensity))
        target_rect = enemy_rect if self.animation_phase == "player" else player_rect
        flash_rect = flash_surface.get_rect(center=target_rect.center)
        surface.blit(flash_surface, flash_rect.topleft)

    def _draw_status_panels(
        self, surface: pygame.Surface, player_rect: pygame.Rect, enemy_rect: pygame.Rect
    ) -> None:
        player = self.app.player
        player_panel = pygame.Rect(player_rect.left - 20, player_rect.top - 90, 260, 78)
        player_panel.left = max(20, player_panel.left)
        if player_panel.right > SCREEN_WIDTH - 20:
            player_panel.right = SCREEN_WIDTH - 20
        if player_panel.top < 20:
            player_panel.top = 20

        enemy_panel = pygame.Rect(
            enemy_rect.right - 260 + 20, enemy_rect.top - 90, 260, 78
        )
        if enemy_panel.right > SCREEN_WIDTH - 20:
            enemy_panel.right = SCREEN_WIDTH - 20
        if enemy_panel.left < 20:
            enemy_panel.left = 20
        if enemy_panel.top < 20:
            enemy_panel.top = 20

        self._draw_status_panel(
            surface,
            player_panel,
            f"{player.name} Lv{player.level}",
            self._display_player_hp,
            player.hp,
            player.max_hp,
            hp_color=(90, 200, 120),
            mp_values=(player.mp, player.max_mp),
        )

        self._draw_status_panel(
            surface,
            enemy_panel,
            self.enemy.name,
            self._display_enemy_hp,
            self.enemy.hp,
            self.enemy.max_hp,
            hp_color=(220, 120, 140),
        )

    def _draw_status_panel(
        self,
        surface: pygame.Surface,
        panel: pygame.Rect,
        title: str,
        animated_hp: float,
        actual_hp: int,
        max_hp: int,
        hp_color: tuple[int, int, int],
        mp_values: tuple[int, int] | None = None,
    ) -> None:
        background = pygame.Surface(panel.size, pygame.SRCALPHA)
        background.fill((12, 20, 36, 200))
        surface.blit(background, panel.topleft)
        pygame.draw.rect(surface, (120, 160, 220), panel, 2, border_radius=12)

        title_text = self.status_font.render(title, True, pygame.Color("white"))
        surface.blit(title_text, (panel.left + 16, panel.top + 10))

        hp_label = self.status_font.render("HP", True, pygame.Color("#ffcc80"))
        surface.blit(hp_label, (panel.left + 16, panel.top + 34))

        hp_bar_rect = pygame.Rect(panel.left + 50, panel.top + 38, panel.width - 70, 12)
        ratio = 0.0 if max_hp <= 0 else max(0.0, min(1.0, animated_hp / max_hp))
        fill_width = int(hp_bar_rect.width * ratio)
        if fill_width > 0:
            pygame.draw.rect(
                surface,
                hp_color,
                (hp_bar_rect.left, hp_bar_rect.top, fill_width, hp_bar_rect.height),
                border_radius=6,
            )
        pygame.draw.rect(surface, (220, 220, 255), hp_bar_rect, 2, border_radius=6)

        hp_value_text = self.status_font.render(
            f"{max(actual_hp, 0)}/{max_hp}", True, pygame.Color("white")
        )
        surface.blit(
            hp_value_text,
            (hp_bar_rect.right - hp_value_text.get_width(), panel.top + 32),
        )

        if mp_values is not None:
            current_mp, max_mp = mp_values
            mp_label = self.status_font.render("MP", True, pygame.Color("#9fa8da"))
            surface.blit(mp_label, (panel.left + 16, panel.top + 58))
            mp_bar_rect = pygame.Rect(
                panel.left + 50, panel.top + 62, panel.width - 70, 10
            )
            mp_ratio = 0.0 if max_mp <= 0 else max(0.0, min(1.0, current_mp / max_mp))
            mp_fill = int(mp_bar_rect.width * mp_ratio)
            if mp_fill > 0:
                pygame.draw.rect(
                    surface,
                    (100, 140, 240),
                    (mp_bar_rect.left, mp_bar_rect.top, mp_fill, mp_bar_rect.height),
                    border_radius=5,
                )
            pygame.draw.rect(surface, (200, 210, 255), mp_bar_rect, 2, border_radius=5)
            mp_value_text = self.status_font.render(
                f"{current_mp}/{max_mp}", True, pygame.Color("white")
            )
            surface.blit(
                mp_value_text,
                (mp_bar_rect.right - mp_value_text.get_width(), panel.top + 54),
            )

    def _draw_bars(self, surface: pygame.Surface) -> None:
        player = self.app.player
        self._draw_bar(
            surface,
            (80, SCREEN_HEIGHT - 140),
            320,
            self._display_player_hp,
            player.hp,
            player.max_hp,
            "HP",
            (200, 60, 60),
        )
        self._draw_bar(
            surface,
            (80, SCREEN_HEIGHT - 100),
            320,
            float(player.mp),
            player.mp,
            player.max_mp,
            "MP",
            (80, 120, 220),
        )
        self._draw_bar(
            surface,
            (SCREEN_WIDTH - 420, SCREEN_HEIGHT - 120),
            320,
            self._display_enemy_hp,
            self.enemy.hp,
            self.enemy.max_hp,
            f"{self.enemy.name} HP",
            (220, 80, 120),
        )

    def _draw_bar(
        self,
        surface: pygame.Surface,
        position,
        width,
        display_value,
        actual_value,
        maximum,
        label,
        color,
    ) -> None:
        x, y = position
        pygame.draw.rect(surface, (40, 40, 60), (x, y, width, 22), border_radius=8)
        ratio = 0 if maximum == 0 else max(0.0, min(1.0, display_value / maximum))
        pygame.draw.rect(
            surface, color, (x, y, int(width * ratio), 22), border_radius=8
        )
        pygame.draw.rect(
            surface, (220, 220, 255), (x, y, width, 22), 2, border_radius=8
        )
        text = self.small_font.render(
            f"{int(actual_value)}/{maximum}", True, pygame.Color("white")
        )
        surface.blit(text, text.get_rect(center=(x + width // 2, y + 11)))
        label_text = self.small_font.render(label, True, pygame.Color("#b0bec5"))
        surface.blit(label_text, (x, y - 24))


def _draw_action_panel(self, surface: pygame.Surface) -> None:
    panel = pygame.Rect(0, SCREEN_HEIGHT - 160, SCREEN_WIDTH, 160)
    pygame.draw.rect(surface, (15, 15, 30), panel)
    pygame.draw.rect(surface, (100, 120, 200), panel, 3)

    button_width, button_height = 200, 60
    spacing = 24
    total = button_width * 2 + spacing
    button_top = panel.top + 48
    start_x = panel.centerx - total // 2

    heal_rect = pygame.Rect(start_x, button_top, button_width, button_height)
    attack_rect = pygame.Rect(
        start_x + button_width + spacing, button_top, button_width, button_height
    )
    self.player_heal_rect = heal_rect
    self.player_action_rect = attack_rect

    player_turn = self.state == "player" and self.animation_phase is None

    # Heal button
    player = self.app.player
    heal_count = player.inventory.potions.get("Heal Potion", 0)
    can_heal = player_turn and heal_count > 0 and player.hp < player.max_hp
    heal_color = (80, 150, 90) if can_heal else (50, 50, 70)
    pygame.draw.rect(surface, heal_color, heal_rect, border_radius=8)
    pygame.draw.rect(
        surface,
        (220, 240, 220) if can_heal else (120, 120, 140),
        heal_rect,
        2,
        border_radius=8,
    )
    heal_label = "Heal"
    if heal_count:
        heal_label = f"Heal x{heal_count}"
    heal_text = self.small_font.render(heal_label, True, pygame.Color("white"))
    surface.blit(heal_text, heal_text.get_rect(center=heal_rect.center))

    # Attack button
    attack_color = (60, 100, 200) if player_turn else (50, 50, 70)
    pygame.draw.rect(surface, attack_color, attack_rect, border_radius=8)
    pygame.draw.rect(surface, (230, 230, 255), attack_rect, 2, border_radius=8)
    attack_text = self.font.render("Attack", True, pygame.Color("white"))
    surface.blit(attack_text, attack_text.get_rect(center=attack_rect.center))

    for idx, line in enumerate(reversed(self.log)):
        text_surface = self.small_font.render(line, True, pygame.Color("#eeeeee"))
        surface.blit(
            text_surface, (attack_rect.right + 40, SCREEN_HEIGHT - 140 + idx * 28)
        )

    if self.state == "victory":
        prompt = "Press Enter to continue"
    elif player_turn:
        extra = " | H to Heal" if heal_count > 0 else ""
        prompt = f"Press Enter/Click to Attack{extra}"
    else:
        prompt = "Battling..."
    prompt_text = self.small_font.render(prompt, True, pygame.Color("#b0bec5"))
    surface.blit(prompt_text, (panel.left + 40, panel.top + 110))


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import GameApp
