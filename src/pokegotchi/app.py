"""Touchscreen view for the Pokegotchi game."""

from datetime import datetime, timezone
from math import cos, sin, tau
from pathlib import Path

import pygame

from .animation import PmdAnimationPlayer, select_animation
from .save_store import load_game, save_game
from .state import GameState, advance_time, apply_action, new_game, species_for


SPRITE_DIR = Path(__file__).resolve().parents[2] / "assets" / "sprites"
PMD_DIR = Path(__file__).resolve().parents[2] / "assets" / "pmd"
STARTERS = ("bulbasaur", "charmander", "squirtle")
EVOLUTION_MS = 3000
EVOLUTION_REVEAL_MS = 1500
STARTER_CARDS = tuple(pygame.Rect(x, 155, 220, 195) for x in (30, 290, 550))
BUTTONS = tuple(pygame.Rect(20 + index * 194, 375, 178, 85) for index in range(4))
MENU_BUTTON = pygame.Rect(704, 16, 60, 60)
BACK_BUTTON = pygame.Rect(40, 26, 72, 72)
MENU_EXIT_BUTTON = pygame.Rect(688, 372, 72, 72)
HABITAT = pygame.Rect(20, 88, 760, 272)
NAVY = (24, 45, 78)
CREAM = (245, 230, 184)
GRASS = (105, 160, 103)
SAND = (214, 181, 109)
SKY = (113, 181, 205)
SHADOW = (12, 28, 52)
TEXTURE = (34, 59, 88)
MUTED = (144, 171, 196)
SPRITE_FILL = 0.55
INK = CREAM
BACKGROUND = NAVY
ACCENT = GRASS


class PokegotchiApp:
    def __init__(self, surface: pygame.Surface, save_path: Path):
        self.surface = surface
        self.save_path = Path(save_path)
        self.state: GameState | None = load_game(self.save_path)
        self.screen = "home" if self.state is not None else "starter_selection"
        self.exit_requested = False
        self.reaction_text = ""
        self.reaction_action: str | None = None
        self.reaction_started_ms = 0
        self.evolution_started_ms = 0
        self.old_species = ""
        self.new_species = ""
        self._sprites: dict[str, pygame.Surface] = {}
        self._animations = PmdAnimationPlayer(PMD_DIR)
        self._animation_key: tuple[str, str] | None = None
        self._animation_started_ms = 0
        self._font = pygame.font.Font(None, 29)
        self._small_font = pygame.font.Font(None, 24)
        self._large_font = pygame.font.Font(None, 43)

        if self.state is not None:
            previous_update = self.state.last_updated
            advance_time(self.state, datetime.now(timezone.utc))
            if self.state.last_updated != previous_update:
                save_game(self.save_path, self.state)

    def draw(self) -> None:
        now = pygame.time.get_ticks()
        if self.screen == "evolution" and now - self.evolution_started_ms >= EVOLUTION_MS:
            self.screen = "home"
            save_game(self.save_path, self.state)

        self.surface.fill(BACKGROUND)
        self._draw_texture()
        if self.screen == "starter_selection":
            self._draw_selection(now)
        elif self.screen == "evolution":
            self._draw_evolution(now)
        elif self.screen == "menu":
            self._draw_menu(now)
        else:
            self._draw_home(now)

    def update_time(self) -> None:
        if self.state is None:
            return
        before = (self.state.health, self.state.hunger, self.state.happiness, self.state.energy, self.state.fainted)
        advance_time(self.state, datetime.now(timezone.utc))
        after = (self.state.health, self.state.hunger, self.state.happiness, self.state.energy, self.state.fainted)
        if after != before:
            save_game(self.save_path, self.state)

    def handle_tap(self, position: tuple[int, int]) -> None:
        if self.screen == "starter_selection":
            for card, starter in zip(STARTER_CARDS, STARTERS):
                if card.collidepoint(position):
                    self.state = new_game(starter, datetime.now(timezone.utc))
                    self.screen = "home"
                    save_game(self.save_path, self.state)
                    return
            return
        if self.screen == "menu":
            if BACK_BUTTON.collidepoint(position):
                self.screen = "home"
            elif MENU_EXIT_BUTTON.collidepoint(position):
                self.exit_requested = True
            return
        if self.screen != "home" or self.state is None:
            return

        if MENU_BUTTON.collidepoint(position):
            self.screen = "menu"
            return

        for index, button in enumerate(BUTTONS):
            if not button.collidepoint(position):
                continue
            self.update_time()
            action = ("feed", "play", "heal", "wake" if self.state.asleep else "sleep")[index]
            previous_species = species_for(self.state)
            if not apply_action(self.state, action):
                return
            now = pygame.time.get_ticks()
            self.reaction_text = {
                "feed": "Yum!",
                "play": "Let's play!",
                "heal": "Feeling better!",
                "sleep": "Sweet dreams!",
                "wake": "Good morning!",
            }[action]
            self.reaction_started_ms = now
            self.reaction_action = action
            current_species = species_for(self.state)
            if current_species != previous_species:
                self.old_species = previous_species
                self.new_species = current_species
                self.evolution_started_ms = now
                self.screen = "evolution"
            else:
                save_game(self.save_path, self.state)
            return

    def _text(self, value: str, x: int, y: int, *, large: bool = False, small: bool = False, color=INK) -> None:
        font = self._large_font if large else self._small_font if small else self._font
        self.surface.blit(font.render(value, False, color), (x, y))

    def _draw_texture(self) -> None:
        for y in range(12, 480, 32):
            for x in range(28, 800, 48):
                pygame.draw.rect(self.surface, TEXTURE, pygame.Rect(x, y, 2, 2))

    def _draw_panel(self, rect: pygame.Rect, fill=NAVY) -> None:
        pygame.draw.rect(self.surface, SHADOW, rect.move(1, 1))
        pygame.draw.rect(self.surface, fill, rect)
        pygame.draw.rect(self.surface, CREAM, rect, width=2)

    def _draw_button(self, rect: pygame.Rect, color) -> None:
        pygame.draw.rect(self.surface, SHADOW, rect)
        pygame.draw.rect(self.surface, color, rect.inflate(-4, -4))
        pygame.draw.rect(self.surface, CREAM, rect, width=2)
        pygame.draw.rect(self.surface, SHADOW, pygame.Rect(rect.x + 4, rect.bottom - 6, rect.width - 8, 2))

    def _draw_selection(self, now: int) -> None:
        self._draw_panel(pygame.Rect(180, 40, 440, 108))
        self._text("Choose your starter", 252, 62, large=True)
        self._text("Tap a card to begin", 313, 112, small=True)
        colors = (GRASS, SAND, SKY)
        for card, starter, color in zip(STARTER_CARDS, STARTERS, colors):
            self._draw_panel(card)
            pygame.draw.rect(self.surface, color, pygame.Rect(card.x + 6, card.y + 6, card.width - 12, 4))
            self._draw_sprite(starter, pygame.Rect(card.x + 35, card.y + 15, 150, 135), elapsed_ms=now)
            label = self._font.render(starter.capitalize(), False, INK)
            self.surface.blit(label, label.get_rect(center=(card.centerx, card.bottom - 28)))

    def _draw_home(self, now: int) -> None:
        assert self.state is not None
        self._draw_panel(pygame.Rect(20, 14, 760, 64))
        self._draw_stats()
        self._draw_habitat()
        self._draw_name_chip()
        self._draw_button(MENU_BUTTON, SAND)
        self._draw_menu_icon(MENU_BUTTON.center)
        reaction_age = now - self.reaction_started_ms
        animation = select_animation(self.state, self.reaction_action, reaction_age)
        species = species_for(self.state)
        animation_key = species, animation
        if animation_key != self._animation_key:
            self._animation_key = animation_key
            self._animation_started_ms = now
        animation_age = reaction_age if animation == "Walk" else now - self._animation_started_ms
        self._draw_sprite(
            species, pygame.Rect(235, 100, 330, 350),
            animation=animation, elapsed_ms=animation_age,
        )

        labels = ("Feed", "Play", "Heal", "Wake" if self.state.asleep else "Sleep")
        colors = (GRASS, SAND, (207, 111, 108), SKY)
        actions = ("feed", "play", "heal", "wake" if self.state.asleep else "sleep")
        for button, label, color, action in zip(BUTTONS, labels, colors, actions):
            self._draw_button(button, color)
            self._draw_care_icon(action, button.centerx, 406, color)
            text = self._small_font.render(label, False, NAVY)
            self.surface.blit(text, text.get_rect(center=(button.centerx, 443)))

        age = now - self.reaction_started_ms
        if self.reaction_text and 0 <= age < 1200:
            text = self._font.render(self.reaction_text, False, NAVY)
            bubble = text.get_rect(center=(400, 122 - age // 120)).inflate(22, 10)
            pygame.draw.rect(self.surface, CREAM, bubble)
            self.surface.blit(text, text.get_rect(center=bubble.center))
        elif age >= 1200:
            self.reaction_text = ""

    def _stat_color(self, value: int) -> tuple[int, int, int]:
        if value >= 67:
            return INK
        if value >= 34:
            return (220, 168, 79)
        return (216, 105, 105)

    def _draw_stats(self) -> None:
        assert self.state is not None
        stats = (
            ("Health", self.state.health, (216, 105, 105)),
            ("Hunger", self.state.hunger, (220, 168, 79)),
            ("Happiness", self.state.happiness, (107, 177, 120)),
            ("Energy", self.state.energy, (112, 150, 211)),
            ("Sleep", "Z" if self.state.asleep else "-", SKY),
        )
        for index, (label, value, color) in enumerate(stats):
            x = 80 + index * 132
            self._draw_stat_icon(label, x, 16, color)
            if label == "Sleep":
                text = value
                text_color = INK if self.state.asleep else MUTED
            else:
                text = str(value)
                text_color = self._stat_color(value)
            width = self._font.size(text)[0]
            self._text(text, x + 14 - width // 2, 46, color=text_color)

    def _draw_stat_icon(self, label: str, x: int, y: int, color: tuple[int, int, int]) -> None:
        pygame.draw.rect(self.surface, SHADOW, pygame.Rect(x + 2, y + 2, 28, 28))
        pygame.draw.rect(self.surface, color, pygame.Rect(x, y, 28, 28))
        pygame.draw.rect(self.surface, CREAM, pygame.Rect(x, y, 28, 28), width=2)
        if label == "Health":
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x + 11, y + 5, 6, 18))
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x + 5, y + 11, 18, 6))
        elif label == "Hunger":
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x + 7, y + 6, 3, 15))
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x + 16, y + 6, 3, 15))
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x + 14, y + 19, 7, 3))
        elif label == "Happiness":
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x + 6, y + 8, 4, 4))
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x + 18, y + 8, 4, 4))
            pygame.draw.line(self.surface, CREAM, (x + 8, y + 18), (x + 14, y + 21), 3)
            pygame.draw.line(self.surface, CREAM, (x + 14, y + 21), (x + 20, y + 18), 3)
        elif label == "Energy":
            pygame.draw.polygon(self.surface, CREAM, [(x + 15, y + 4), (x + 7, y + 16), (x + 13, y + 16), (x + 10, y + 24), (x + 22, y + 11), (x + 16, y + 11)])
        else:
            pygame.draw.circle(self.surface, CREAM, (x + 14, y + 14), 9)
            pygame.draw.circle(self.surface, color, (x + 19, y + 9), 8)

    def _draw_name_chip(self) -> None:
        assert self.state is not None
        name = species_for(self.state).capitalize()
        text_width, text_height = self._font.size(name)
        chip = pygame.Rect(36, 100, text_width + 26, 36)
        pygame.draw.rect(self.surface, SHADOW, chip.move(2, 2))
        pygame.draw.rect(self.surface, SAND, chip)
        pygame.draw.rect(self.surface, CREAM, chip, width=2)
        self._text(name, chip.centerx - text_width // 2, chip.centery - text_height // 2, color=NAVY)

    def _draw_habitat(self) -> None:
        pygame.draw.rect(self.surface, SHADOW, HABITAT.move(2, 2))
        pygame.draw.rect(self.surface, SKY, HABITAT)
        pygame.draw.rect(self.surface, GRASS, pygame.Rect(HABITAT.x, 210, HABITAT.width, 150))
        pygame.draw.ellipse(self.surface, SAND, pygame.Rect(245, 270, 310, 75))
        pygame.draw.ellipse(self.surface, (186, 147, 87), pygame.Rect(279, 328, 235, 13))
        for x, y in ((230, 156), (585, 169), (640, 145)):
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x, y, 56, 8))
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x + 11, y - 7, 34, 8))
        for x, y in ((93, 266), (166, 318), (604, 286), (695, 325)):
            pygame.draw.line(self.surface, (59, 125, 83), (x, y), (x - 4, y - 8), 3)
            pygame.draw.line(self.surface, (59, 125, 83), (x, y), (x + 4, y - 9), 3)
        for x, y in ((118, 324), (673, 263)):
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x, y, 5, 5))
            pygame.draw.rect(self.surface, (216, 105, 105), pygame.Rect(x + 1, y + 1, 3, 3))
        pygame.draw.rect(self.surface, CREAM, HABITAT, width=3)

    def _draw_care_icon(self, action: str, x: int, y: int, color: tuple[int, int, int]) -> None:
        pygame.draw.rect(self.surface, SHADOW, pygame.Rect(x - 20, y - 18, 40, 36))
        if action == "feed":
            pygame.draw.polygon(self.surface, color, [
                (x - 14, y), (x + 14, y), (x + 9, y + 12), (x - 9, y + 12),
            ])
            pygame.draw.ellipse(self.surface, color, pygame.Rect(x - 11, y - 13, 22, 14))
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x - 15, y - 2, 30, 3))
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x - 6, y - 18, 3, 4))
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x + 3, y - 18, 3, 4))
        elif action == "play":
            pygame.draw.circle(self.surface, color, (x, y), 12)
            pygame.draw.circle(self.surface, CREAM, (x, y), 12, 2)
            pygame.draw.line(self.surface, CREAM, (x - 9, y - 8), (x + 9, y + 8), 2)
        elif action == "heal":
            pygame.draw.rect(self.surface, color, pygame.Rect(x - 4, y - 12, 8, 24))
            pygame.draw.rect(self.surface, color, pygame.Rect(x - 12, y - 4, 24, 8))
        elif action == "sleep":
            pygame.draw.circle(self.surface, color, (x, y), 12)
            pygame.draw.circle(self.surface, SHADOW, (x + 6, y - 5), 10)
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x + 10, y - 12, 5, 2))
        else:
            pygame.draw.circle(self.surface, color, (x, y), 8)
            for dx, dy in ((0, -14), (0, 14), (-14, 0), (14, 0), (-10, -10), (10, -10), (-10, 10), (10, 10)):
                pygame.draw.rect(self.surface, CREAM, pygame.Rect(x + dx - 2, y + dy - 2, 4, 4))

    def _draw_menu_icon(self, center: tuple[int, int]) -> None:
        x, y = center
        for offset in (-10, 0, 10):
            pygame.draw.rect(self.surface, NAVY, pygame.Rect(x - 14, y + offset - 2, 28, 4))

    def _status(self) -> str:
        assert self.state is not None
        if self.state.fainted:
            return "Fainted"
        if self.state.asleep:
            return "Sleeping"
        needs = (
            (self.state.health, "Needs healing"),
            (self.state.hunger, "Needs food"),
            (self.state.happiness, "Needs play"),
            (self.state.energy, "Needs rest"),
        )
        lowest, need = min(needs, key=lambda item: item[0])
        return need if lowest < 50 else "Doing well"

    def _draw_menu(self, now: int) -> None:
        assert self.state is not None
        self._draw_panel(pygame.Rect(20, 18, 760, 444))
        self._draw_button(BACK_BUTTON, SKY)
        self._draw_back_icon(BACK_BUTTON.center)
        title = self._large_font.render("Menu", False, INK)
        self.surface.blit(title, title.get_rect(center=(400, 56)))

        self._text(species_for(self.state).capitalize(), 64, 132, large=True)
        pygame.draw.ellipse(self.surface, SHADOW, pygame.Rect(510, 264, 140, 14))
        self._draw_sprite(species_for(self.state), pygame.Rect(430, 60, 320, 350), elapsed_ms=now)
        if self.state.fainted:
            status_color = (216, 105, 105)
        elif self.state.asleep:
            status_color = SKY
        else:
            status_color = self._stat_color(min(
                self.state.health, self.state.hunger, self.state.happiness, self.state.energy,
            ))
        groups = (
            ("Level", str(self.state.level), 64, INK),
            ("XP", str(self.state.xp), 200, INK),
            ("Status", self._status(), 330, status_color),
        )
        for label, value, x, color in groups:
            self._text(label, x, 204, small=True, color=MUTED)
            self._text(value, x, 226, color=color)

        pygame.draw.line(self.surface, TEXTURE, (64, 286), (400, 286), 2)
        self._draw_clock_icon(70, 310)
        self._text(self.state.last_updated.strftime("%Y-%m-%d %H:%M UTC"), 88, 302, small=True, color=MUTED)

        self._draw_button(MENU_EXIT_BUTTON, SAND)
        self._draw_exit_icon(MENU_EXIT_BUTTON.center)

    def _draw_clock_icon(self, x: int, y: int) -> None:
        pygame.draw.circle(self.surface, MUTED, (x, y), 7, 2)
        pygame.draw.line(self.surface, MUTED, (x, y), (x, y - 4), 2)
        pygame.draw.line(self.surface, MUTED, (x, y), (x + 3, y + 2), 2)

    def _draw_back_icon(self, center: tuple[int, int]) -> None:
        x, y = center
        pygame.draw.rect(self.surface, NAVY, pygame.Rect(x - 16, y - 3, 20, 6))
        pygame.draw.polygon(self.surface, NAVY, [
            (x - 20, y), (x - 8, y - 10), (x - 8, y + 10),
        ])

    def _draw_exit_icon(self, center: tuple[int, int]) -> None:
        x, y = center
        pygame.draw.lines(self.surface, NAVY, False, [
            (x + 6, y - 14), (x - 10, y - 14), (x - 10, y + 14), (x + 6, y + 14),
        ], 4)
        pygame.draw.rect(self.surface, NAVY, pygame.Rect(x - 2, y - 3, 16, 6))
        pygame.draw.polygon(self.surface, NAVY, [
            (x + 18, y), (x + 8, y - 8), (x + 8, y + 8),
        ])

    def _draw_card_title(self, title: str, card: pygame.Rect) -> None:
        self._text(title, card.x + 24, card.y + 22, small=True, color=SAND)
        pygame.draw.line(
            self.surface, TEXTURE,
            (card.x + 24, card.y + 50), (card.right - 24, card.y + 50), 2,
        )

    def _draw_rows(self, card: pygame.Rect, rows: tuple[tuple[str, str], ...], start_y: int) -> None:
        for index, (label, value) in enumerate(rows):
            y = start_y + index * 34
            self._text(label, card.x + 24, y, small=True, color=MUTED)
            self._text(value, card.x + 130, y, small=True)

    def _draw_evolution(self, now: int) -> None:
        elapsed = now - self.evolution_started_ms
        revealed = elapsed >= EVOLUTION_REVEAL_MS
        shown_species = self.new_species if revealed else self.old_species
        panel = pygame.Rect(100, 40, 600, 400)
        self._draw_panel(panel)
        self._draw_evolution_effect(panel, elapsed)
        self._draw_sprite(shown_species, pygame.Rect(260, 130, 280, 230), elapsed_ms=now)
        if revealed:
            lines = (
                "Congratulations!",
                f"{self.old_species.capitalize()} has evolved into {self.new_species.capitalize()}!",
            )
        else:
            lines = ("What?", f"{self.old_species.capitalize()} is evolving!")
        self._draw_dialog(lines)

    def _draw_dialog(self, lines: tuple[str, ...]) -> None:
        box = pygame.Rect(116, 336, 568, 88)
        pygame.draw.rect(self.surface, SHADOW, box.move(0, 4), border_radius=10)
        pygame.draw.rect(self.surface, SKY, box, border_radius=10)
        inner = box.inflate(-10, -10)
        pygame.draw.rect(self.surface, CREAM, inner, border_radius=7)
        pygame.draw.rect(self.surface, NAVY, inner, width=2, border_radius=7)
        for index, line in enumerate(lines):
            self._text(line, box.x + 28, box.y + 20 + index * 32, color=NAVY)

    def _draw_evolution_effect(self, panel: pygame.Rect, elapsed_ms: int) -> None:
        scale = 4
        small = pygame.Surface((panel.width // scale, panel.height // scale), pygame.SRCALPHA)
        center = small.get_width() // 2, small.get_height() // 2

        # rotating light rays behind the sprite, drawn chunky to match the pixel art
        rotation = elapsed_ms * 0.0006
        for index in range(12):
            angle = rotation + index * tau / 12
            spread = 0.06
            far = small.get_width()
            pygame.draw.polygon(small, (120, 170, 210, 16), [
                center,
                (center[0] + cos(angle - spread) * far, center[1] + sin(angle - spread) * far),
                (center[0] + cos(angle + spread) * far, center[1] + sin(angle + spread) * far),
            ])

        # expanding pulse rings
        for offset in (0, 400):
            age = (elapsed_ms + offset) % 800
            radius = 10 + age * 0.085
            shade = 90 + int(45 * (1 - age / 800))
            pygame.draw.circle(small, (shade, shade + 32, shade + 58, 70), center, int(radius), 1)

        effect = pygame.transform.scale(small, panel.size)
        full_center = panel.width // 2, panel.height // 2

        # orbiting sparkles stay sharp and unfiltered
        for index in range(14):
            phase = elapsed_ms * 0.0025 + index * 1.7
            angle = index * 2.4 + elapsed_ms * 0.0004
            radius = 90 + (index * 53) % 150 + sin(phase) * 12
            x = round(full_center[0] + cos(angle) * radius)
            y = round(full_center[1] + sin(angle) * radius * 0.75)
            if y > 330:
                continue
            twinkle = (sin(phase * 2) + 1) / 2
            size = 2 + round(twinkle * 3)
            color = (245, 230, 184, int(80 + 150 * twinkle))
            pygame.draw.rect(effect, color, pygame.Rect(x - size, y - 1, size * 2 + 1, 3))
            pygame.draw.rect(effect, color, pygame.Rect(x - 1, y - size, 3, size * 2 + 1))

        self.surface.blit(effect, panel.topleft)

    def _draw_sprite(self, species: str, area: pygame.Rect, *, animation: str = "Idle", elapsed_ms: int = 0) -> None:
        animated = self._animations.frame(species, animation, elapsed_ms)
        sprite = animated or self._static_sprite(species)
        if sprite is None:
            self._draw_placeholder(species, area)
            return

        width, height = sprite.get_size()
        canvas_size = self._animations.max_frame_size(species)
        scale_width, scale_height = canvas_size or (width, height)
        factor = min(area.width / scale_width, area.height / scale_height)
        if animated is not None:
            reference = self._animations.content_height(species, "Idle")
            content = self._animations.content_height(species, animation)
            if reference and content:
                # size by visible pixels instead of the padded frame so
                # every animation shows the pokemon at the same height
                factor = area.height * SPRITE_FILL / content
                bounds = sprite.get_bounding_rect()
                if bounds.width and bounds.width * factor > area.width:
                    factor = area.width / bounds.width
        size = (max(1, round(width * factor)), max(1, round(height * factor)))
        scaled = pygame.transform.scale(sprite, size)
        if animated is None:
            self.surface.blit(scaled, scaled.get_rect(center=area.center))
            return
        content_bottom = round(sprite.get_bounding_rect().bottom * factor)
        baseline = area.centery + round(area.height * 0.07)
        self.surface.blit(scaled, (area.centerx - size[0] // 2, baseline - content_bottom))

    def _static_sprite(self, species: str) -> pygame.Surface | None:
        sprite = self._sprites.get(species)
        if sprite is None:
            try:
                sprite = pygame.image.load(str(SPRITE_DIR / f"{species}.png")).convert_alpha()
            except (FileNotFoundError, pygame.error):
                return None
            self._sprites[species] = sprite
        return sprite

    def _draw_placeholder(self, species: str, area: pygame.Rect) -> None:
        self._draw_panel(area)
        name = self._small_font.render(species.capitalize(), False, INK)
        missing = self._small_font.render("sprite missing", False, INK)
        self.surface.blit(name, name.get_rect(center=(area.centerx, area.centery - 12)))
        self.surface.blit(missing, missing.get_rect(center=(area.centerx, area.centery + 14)))
