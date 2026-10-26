"""Load and play the committed PMD sprite sheets."""

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

import pygame

from .state import GameState


def select_animation(state: GameState, action: str | None = None, elapsed_ms: int = 0) -> str:
    if state.fainted or state.health == 0:
        return "Faint"
    if state.asleep:
        return "Sleep"
    if state.health < 25:
        return "Hurt"
    if action in {"feed", "play", "heal"} and 0 <= elapsed_ms < 1200:
        return "Walk"
    return "Idle"


@dataclass
class _Animation:
    frames: tuple[pygame.Surface, ...]
    durations: tuple[int, ...]

    def frame(self, elapsed_ms: int, *, loop: bool) -> pygame.Surface:
        total = sum(self.durations)
        tick = max(0, elapsed_ms) * 60 // 1000
        tick = tick % total if loop else min(tick, total - 1)
        for frame, duration in zip(self.frames, self.durations):
            if tick < duration:
                return frame
            tick -= duration
        return self.frames[-1]


class PmdAnimationPlayer:
    def __init__(self, root: Path):
        self.root = Path(root)
        self._metadata: dict[str, dict[str, ElementTree.Element]] = {}
        self._animations: dict[tuple[str, str], _Animation | None] = {}
        self._content_heights: dict[tuple[str, str], int] = {}

    def frame(self, species: str, name: str, elapsed_ms: int) -> pygame.Surface | None:
        animation = self._animation_for(species, name)
        if animation is None:
            return None
        return animation.frame(elapsed_ms, loop=name != "Faint")

    def content_height(self, species: str, name: str) -> int:
        key = species, name
        if key not in self._content_heights:
            animation = self._animation_for(species, name)
            height = 0
            if animation is not None:
                height = max(frame.get_bounding_rect().height for frame in animation.frames)
            self._content_heights[key] = height
        return self._content_heights[key]

    def _animation_for(self, species: str, name: str) -> _Animation | None:
        candidates = (name, "Hurt", "Idle") if name == "Faint" else (name, "Idle")
        for candidate in dict.fromkeys(candidates):
            animation = self._load(species, candidate)
            if animation is not None:
                return animation
        return None

    def max_frame_size(self, species: str) -> tuple[int, int] | None:
        if species not in self._metadata:
            try:
                root = ElementTree.parse(self.root / species / "AnimData.xml").getroot()
                self._metadata[species] = {
                    anim.findtext("Name"): anim for anim in root.findall("Anims/Anim")
                }
            except (OSError, ElementTree.ParseError):
                return None
        sizes = []
        for entry in self._metadata[species].values():
            source = entry.findtext("CopyOf") or entry.findtext("Name")
            source_entry = self._metadata[species].get(source, entry)
            try:
                sizes.append((int(source_entry.findtext("FrameWidth")), int(source_entry.findtext("FrameHeight"))))
            except (TypeError, ValueError):
                continue
        return (max(width for width, _ in sizes), max(height for _, height in sizes)) if sizes else None

    def _load(self, species: str, name: str) -> _Animation | None:
        key = species, name
        if key in self._animations:
            return self._animations[key]
        try:
            if species not in self._metadata:
                root = ElementTree.parse(self.root / species / "AnimData.xml").getroot()
                self._metadata[species] = {
                    anim.findtext("Name"): anim for anim in root.findall("Anims/Anim")
                }
            entry = self._metadata[species].get(name)
            if entry is None:
                return None
            source = entry.findtext("CopyOf") or name
            if source != name:
                entry = self._metadata[species][source]
            width = int(entry.findtext("FrameWidth"))
            height = int(entry.findtext("FrameHeight"))
            durations = tuple(int(item.text) for item in entry.findall("Durations/Duration"))
            if width <= 0 or height <= 0 or not durations or any(duration <= 0 for duration in durations):
                return None
            sheet = pygame.image.load(str(self.root / species / f"{source}-Anim.png")).convert_alpha()
            if sheet.get_width() != width * len(durations) or sheet.get_height() not in (height, height * 8):
                return None
            frames = tuple(sheet.subsurface(pygame.Rect(i * width, 0, width, height)).copy()
                           for i in range(len(durations)))
            self._animations[key] = _Animation(frames, durations)
        except (OSError, pygame.error, ElementTree.ParseError, ValueError, KeyError, TypeError):
            self._animations[key] = None
        return self._animations.get(key)
