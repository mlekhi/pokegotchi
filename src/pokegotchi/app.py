"""Touchscreen view for the Pokegotchi game."""

from datetime import datetime, timezone
from pathlib import Path

import pygame

from .animation import PmdAnimationPlayer, select_animation
from .save_store import load_game, save_game
from .state import GameState, advance_time, apply_action, new_game, species_for


SPRITE_DIR = Path(__file__).resolve().parents[2] / "assets" / "sprites"
PMD_DIR = Path(__file__).resolve().parents[2] / "assets" / "pmd"
STARTERS = ("bulbasaur", "charmander", "squirtle")
STARTER_CARDS = tuple(pygame.Rect(x, 155, 220, 195) for x in (30, 290, 550))
BUTTONS = (
    pygame.Rect(20, 375, 180, 85),
    pygame.Rect(215, 375, 180, 85),
    pygame.Rect(410, 375, 180, 85),
    pygame.Rect(605, 375, 175, 85),
)
MENU_BUTTON = pygame.Rect(714, 28, 64, 64)
BACK_BUTTON = pygame.Rect(24, 24, 92, 60)
MENU_EXIT_BUTTON = pygame.Rect(510, 377, 250, 74)
HABITAT = pygame.Rect(40, 112, 720, 248)
NAVY = (24, 45, 78)
CREAM = (245, 230, 184)
GRASS = (105, 160, 103)
SAND = (214, 181, 109)
SKY = (113, 181, 205)
SHADOW = (12, 28, 52)
TEXTURE = (34, 59, 88)
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
        if self.screen == "evolution" and now - self.evolution_started_ms >= 2000:
            self.screen = "home"
            save_game(self.save_path, self.state)

        self.surface.fill(BACKGROUND)
        self._draw_texture()
        if self.screen == "starter_selection":
            self._draw_selection(now)
        elif self.screen == "evolution":
            self._draw_evolution(now)
        elif self.screen == "menu":
            self._draw_menu()
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
        self._draw_panel(pygame.Rect(18, 18, 764, 78))
        self._draw_stats()
        self._draw_habitat()
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
            species, pygame.Rect(295, 145, 210, 202),
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

    def _draw_stats(self) -> None:
        assert self.state is not None
        stats = (
            ("Health", self.state.health, (216, 105, 105)),
            ("Hunger", self.state.hunger, (220, 168, 79)),
            ("Happiness", self.state.happiness, (107, 177, 120)),
            ("Energy", self.state.energy, (112, 150, 211)),
            ("Sleep", "ON" if self.state.asleep else "OFF", SKY),
        )
        for index, (label, value, color) in enumerate(stats):
            x = 34 + index * 136
            self._draw_stat_icon(label, x, 40, color)
            self._text(label, x + 40, 34, small=True)
            self._text(str(value), x + 40, 59, small=True)

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

    def _draw_habitat(self) -> None:
        pygame.draw.rect(self.surface, SHADOW, HABITAT.move(2, 2))
        pygame.draw.rect(self.surface, SKY, HABITAT)
        pygame.draw.rect(self.surface, GRASS, pygame.Rect(HABITAT.x, 210, HABITAT.width, 150))
        pygame.draw.ellipse(self.surface, SAND, pygame.Rect(245, 270, 310, 75))
        pygame.draw.ellipse(self.surface, (186, 147, 87), pygame.Rect(279, 328, 235, 13))
        for x, y in ((105, 150), (585, 169), (640, 145)):
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
            pygame.draw.ellipse(self.surface, color, pygame.Rect(x - 13, y - 4, 26, 13))
            pygame.draw.rect(self.surface, color, pygame.Rect(x - 10, y + 4, 20, 6))
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x - 3, y - 12, 6, 5))
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

    def _draw_menu(self) -> None:
        assert self.state is not None
        self._draw_panel(pygame.Rect(18, 18, 764, 444))
        self._draw_button(BACK_BUTTON, SKY)
        self._text("Back", 44, 40, color=NAVY)
        self._text("Menu", 344, 38, large=True)
        self._draw_panel(pygame.Rect(40, 112, 346, 242))
        self._text("Pokemon details", 63, 132)
        self._text(species_for(self.state).capitalize(), 63, 177, large=True)
        self._text(f"Level {self.state.level}   XP {self.state.xp}", 63, 232)
        self._text(f"Status: {self._status()}", 63, 288)
        self._draw_panel(pygame.Rect(404, 112, 356, 242))
        self._text("Save and status", 427, 132)
        self._text("Save: local", 427, 180)
        self._text(self.state.last_updated.strftime("Updated: %Y-%m-%d %H:%M UTC"), 427, 217, small=True)
        self._text("Settings: coming soon", 427, 270, small=True)
        self._text("Evolution: coming soon", 427, 298, small=True)
        self._draw_button(MENU_EXIT_BUTTON, SAND)
        self._text("Exit to desktop", 540, 401, color=NAVY)

    def _draw_evolution(self, now: int) -> None:
        elapsed = now - self.evolution_started_ms
        shown_species = self.old_species if elapsed // 200 % 2 == 0 else self.new_species
        self._draw_panel(pygame.Rect(100, 40, 600, 400))
        self._text("Evolution!", 317, 65, large=True)
        self._draw_sprite(shown_species, pygame.Rect(260, 130, 280, 230), elapsed_ms=now)
        self._text(f"{self.old_species.capitalize()} is evolving into {self.new_species.capitalize()}!", 160, 402)

    def _draw_sprite(self, species: str, area: pygame.Rect, *, animation: str = "Idle", elapsed_ms: int = 0) -> None:
        sprite = self._animations.frame(species, animation, elapsed_ms)
        if sprite is None:
            sprite = self._static_sprite(species)
        if sprite is None:
            self._draw_placeholder(species, area)
            return

        width, height = sprite.get_size()
        canvas_size = self._animations.max_frame_size(species)
        scale_width, scale_height = canvas_size or (width, height)
        factor = min(area.width / scale_width, area.height / scale_height)
        size = (max(1, round(width * factor)), max(1, round(height * factor)))
        scaled = pygame.transform.scale(sprite, size)
        self.surface.blit(scaled, scaled.get_rect(center=area.center))

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
