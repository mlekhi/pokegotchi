"""Touchscreen view for the Pokegotchi game."""

from datetime import datetime, timezone
from pathlib import Path

import pygame

from .save_store import load_game, save_game
from .state import GameState, advance_time, apply_action, new_game, species_for


SPRITE_DIR = Path(__file__).resolve().parents[2] / "assets" / "sprites"
STARTERS = ("bulbasaur", "charmander", "squirtle")
STARTER_CARDS = tuple(pygame.Rect(x, 155, 220, 195) for x in (30, 290, 550))
BUTTONS = (
    pygame.Rect(20, 375, 180, 85),
    pygame.Rect(215, 375, 180, 85),
    pygame.Rect(410, 375, 180, 85),
    pygame.Rect(605, 375, 175, 85),
)
INK = (38, 53, 46)
BACKGROUND = (237, 243, 235)
PANEL = (255, 255, 249)
ACCENT = (92, 148, 113)


class PokegotchiApp:
    def __init__(self, surface: pygame.Surface, save_path: Path):
        self.surface = surface
        self.save_path = Path(save_path)
        self.state: GameState | None = load_game(self.save_path)
        self.screen = "home" if self.state is not None else "starter_selection"
        self.reaction_text = ""
        self.reaction_started_ms = 0
        self.evolution_started_ms = 0
        self.old_species = ""
        self.new_species = ""
        self._sprites: dict[str, pygame.Surface] = {}
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
        if self.screen == "starter_selection":
            self._draw_selection()
        elif self.screen == "evolution":
            self._draw_evolution(now)
        else:
            self._draw_home(now)

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

        for index, button in enumerate(BUTTONS):
            if not button.collidepoint(position):
                continue
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
        self.surface.blit(font.render(value, True, color), (x, y))

    def _draw_selection(self) -> None:
        self._text("Choose your starter", 252, 62, large=True)
        self._text("Tap a card to begin", 313, 112, small=True)
        colors = ((137, 184, 136), (235, 160, 109), (121, 176, 213))
        for card, starter, color in zip(STARTER_CARDS, STARTERS, colors):
            pygame.draw.rect(self.surface, PANEL, card, border_radius=18)
            pygame.draw.rect(self.surface, color, card, width=4, border_radius=18)
            self._draw_sprite(starter, pygame.Rect(card.x + 35, card.y + 15, 150, 135))
            label = self._font.render(starter.capitalize(), True, INK)
            self.surface.blit(label, label.get_rect(center=(card.centerx, card.bottom - 28)))

    def _draw_home(self, now: int) -> None:
        assert self.state is not None
        self._draw_stats()
        pygame.draw.rect(self.surface, PANEL, pygame.Rect(40, 150, 340, 200), border_radius=18)
        self._draw_sprite(species_for(self.state), pygame.Rect(80, 165, 240, 175))
        species = species_for(self.state)
        self._text(species.capitalize(), 420, 180, large=True)
        self._text(f"Level {self.state.level}", 422, 235)
        self._text(f"XP {self.state.xp}", 422, 270)
        status = "Fainted" if self.state.fainted else "Sleeping" if self.state.asleep else "Awake"
        self._text(f"Status: {status}", 422, 305)

        labels = ("Feed", "Play", "Heal", "Wake" if self.state.asleep else "Sleep")
        colors = ((118, 171, 111), (228, 171, 92), (219, 119, 120), (124, 149, 206))
        for button, label, color in zip(BUTTONS, labels, colors):
            pygame.draw.rect(self.surface, color, button, border_radius=15)
            text = self._font.render(label, True, PANEL)
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
            pygame.draw.rect(self.surface, (205, 216, 204), pygame.Rect(x, 61, 175, 22), border_radius=8)
            if value:
                pygame.draw.rect(self.surface, color, pygame.Rect(x, 61, round(175 * value / 100), 22), border_radius=8)

    def _draw_evolution(self, now: int) -> None:
        elapsed = now - self.evolution_started_ms
        shown_species = self.old_species if elapsed // 200 % 2 == 0 else self.new_species
        self._text("Evolution!", 317, 65, large=True)
        self._draw_sprite(shown_species, pygame.Rect(260, 130, 280, 230))
        self._text(f"{self.old_species.capitalize()} is evolving into {self.new_species.capitalize()}!", 160, 402)

    def _draw_sprite(self, species: str, area: pygame.Rect) -> None:
        sprite = self._sprites.get(species)
        if sprite is None:
            try:
                sprite = pygame.image.load(str(SPRITE_DIR / f"{species}.png")).convert_alpha()
            except (FileNotFoundError, pygame.error):
                self._draw_placeholder(species, area)
                return
            self._sprites[species] = sprite

        width, height = sprite.get_size()
        factor = min(area.width / width, area.height / height)
        size = (max(1, round(width * factor)), max(1, round(height * factor)))
        scaled = pygame.transform.scale(sprite, size)
        self.surface.blit(scaled, scaled.get_rect(center=area.center))

    def _draw_placeholder(self, species: str, area: pygame.Rect) -> None:
        pygame.draw.rect(self.surface, (222, 232, 222), area, border_radius=12)
        pygame.draw.rect(self.surface, ACCENT, area, width=3, border_radius=12)
        name = self._small_font.render(species.capitalize(), True, INK)
        missing = self._small_font.render("sprite missing", True, INK)
        self.surface.blit(name, name.get_rect(center=(area.centerx, area.centery - 12)))
        self.surface.blit(missing, missing.get_rect(center=(area.centerx, area.centery + 14)))
