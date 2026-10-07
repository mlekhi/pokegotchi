from datetime import datetime, timezone
from pathlib import Path

import pygame
import pytest

from pokegotchi.animation import PmdAnimationPlayer, select_animation
from pokegotchi.state import new_game


NOW = datetime(2026, 10, 7, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("changes", "action", "elapsed", "expected"),
    [
        ({}, None, 0, "Idle"),
        ({}, "feed", 500, "Walk"),
        ({}, "play", 1199, "Walk"),
        ({}, "heal", 1200, "Idle"),
        ({"health": 24}, None, 0, "Hurt"),
        ({"asleep": True}, "play", 500, "Sleep"),
        ({"health": 0, "fainted": True}, "heal", 500, "Faint"),
    ],
)
def test_animation_selection_follows_game_state(changes, action, elapsed, expected):
    state = new_game("bulbasaur", NOW)
    for name, value in changes.items():
        setattr(state, name, value)

    assert select_animation(state, action, elapsed) == expected


def test_player_uses_metadata_durations_and_front_direction(tmp_path, pygame_surface):
    pack = tmp_path / "bulbasaur"
    pack.mkdir()
    (pack / "AnimData.xml").write_text(
        "<AnimData><Anims><Anim><Name>Idle</Name><FrameWidth>2</FrameWidth>"
        "<FrameHeight>2</FrameHeight><Durations><Duration>3</Duration>"
        "<Duration>6</Duration></Durations></Anim></Anims></AnimData>"
    )
    sheet = pygame.Surface((4, 16), pygame.SRCALPHA)
    sheet.fill((255, 0, 0), pygame.Rect(0, 0, 2, 2))
    sheet.fill((0, 0, 255), pygame.Rect(2, 0, 2, 2))
    sheet.fill((0, 255, 0), pygame.Rect(0, 2, 4, 14))
    pygame.image.save(sheet, str(pack / "Idle-Anim.png"))
    player = PmdAnimationPlayer(tmp_path)

    assert player.frame("bulbasaur", "Idle", 49).get_at((0, 0))[:3] == (255, 0, 0)
    assert player.frame("bulbasaur", "Idle", 50).get_at((0, 0))[:3] == (0, 0, 255)
    assert player.frame("bulbasaur", "Idle", 150).get_at((0, 0))[:3] == (255, 0, 0)


def test_missing_faint_animation_uses_hurt_sheet(tmp_path, pygame_surface):
    pack = tmp_path / "ivysaur"
    pack.mkdir()
    (pack / "AnimData.xml").write_text(
        "<AnimData><Anims><Anim><Name>Hurt</Name><FrameWidth>2</FrameWidth>"
        "<FrameHeight>2</FrameHeight><Durations><Duration>4</Duration>"
        "</Durations></Anim></Anims></AnimData>"
    )
    sheet = pygame.Surface((2, 2), pygame.SRCALPHA)
    sheet.fill((255, 0, 0))
    pygame.image.save(sheet, str(pack / "Hurt-Anim.png"))

    assert PmdAnimationPlayer(tmp_path).frame("ivysaur", "Faint", 0).get_at((0, 0))[:3] == (255, 0, 0)


def test_missing_pack_returns_no_frame(tmp_path, pygame_surface):
    assert PmdAnimationPlayer(tmp_path).frame("bulbasaur", "Idle", 0) is None


@pytest.mark.parametrize(
    "species",
    ("bulbasaur", "ivysaur", "venusaur", "charmander", "charmeleon",
     "charizard", "squirtle", "wartortle", "blastoise"),
)
@pytest.mark.parametrize("animation", ("Idle", "Walk", "Sleep", "Hurt", "Faint"))
def test_committed_pmd_packs_have_usable_frames(species, animation, pygame_surface):
    root = Path(__file__).resolve().parents[1] / "assets" / "pmd"

    frame = PmdAnimationPlayer(root).frame(species, animation, 0)

    assert frame is not None
    assert frame.get_width() > 0
