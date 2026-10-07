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
EXIT_BUTTON = pygame.Rect(724, 150, 36, 36)
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
        if self.screen != "home" or self.state is None:
            return

        if EXIT_BUTTON.collidepoint(position):
            self.exit_requested = True
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
        self._draw_panel(pygame.Rect(18, 18, 764, 101))
        self._draw_stats()
        self._draw_panel(pygame.Rect(40, 150, 340, 200))
        self._draw_panel(pygame.Rect(404, 150, 356, 200))
        self._draw_button(EXIT_BUTTON, SAND)
        exit_label = self._font.render("X", False, NAVY)
        self.surface.blit(exit_label, exit_label.get_rect(center=EXIT_BUTTON.center))
        reaction_age = now - self.reaction_started_ms
        animation = select_animation(self.state, self.reaction_action, reaction_age)
        species = species_for(self.state)
        animation_key = species, animation
        if animation_key != self._animation_key:
            self._animation_key = animation_key
            self._animation_started_ms = now
        animation_age = reaction_age if animation == "Walk" else now - self._animation_started_ms
        self._draw_sprite(
            species, pygame.Rect(80, 165, 240, 175),
            animation=animation, elapsed_ms=animation_age,
        )
        self._text(species.capitalize(), 420, 180, large=True)
        self._text(f"Level {self.state.level}", 422, 235)
        self._text(f"XP {self.state.xp}", 422, 270)
        if self.state.fainted:
            status = "Fainted"
        elif self.state.asleep:
            status = "Sleeping"
        else:
            needs = (
                (self.state.health, "Needs healing"),
                (self.state.hunger, "Needs food"),
                (self.state.happiness, "Needs play"),
                (self.state.energy, "Needs rest"),
            )
            lowest, need = min(needs, key=lambda item: item[0])
            status = need if lowest < 50 else "Doing well"
        self._text(f"Status: {status}", 422, 305)

        labels = ("Feed", "Play", "Heal", "Wake" if self.state.asleep else "Sleep")
        colors = (GRASS, SAND, (207, 111, 108), SKY)
        for button, label, color in zip(BUTTONS, labels, colors):
            self._draw_button(button, color)
            text = self._font.render(label, False, NAVY)
            self.surface.blit(text, text.get_rect(center=button.center))

        age = now - self.reaction_started_ms
        if self.reaction_text and 0 <= age < 1200:
            self._text(self.reaction_text, 420, 340 - age // 60, color=ACCENT)
        elif age >= 1200:
            self.reaction_text = ""

    def _draw_stats(self) -> None:
        assert self.state is not None
        stats = (
            ("Health", self.state.health, (216, 105, 105)),
            ("Hunger", self.state.hunger, (220, 168, 79)),
            ("Happiness", self.state.happiness, (107, 177, 120)),
            ("Energy", self.state.energy, (112, 150, 211)),
        )
        for index, (label, value, color) in enumerate(stats):
            x = 25 + index * 200
            self._text(label, x, 25, small=True)
            self._text(str(value), x + 153, 25, small=True)
            pygame.draw.rect(self.surface, SHADOW, pygame.Rect(x, 61, 175, 22))
            if value:
                pygame.draw.rect(self.surface, color, pygame.Rect(x + 3, 64, round(169 * value / 100), 16))
            pygame.draw.rect(self.surface, CREAM, pygame.Rect(x, 61, 175, 22), width=2)

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
        factor = min(area.width / width, area.height / height)
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
