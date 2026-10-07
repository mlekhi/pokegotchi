from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess

import pygame
import pytest

from pokegotchi.app import PokegotchiApp
from pokegotchi.save_store import load_game, save_game
from pokegotchi.state import new_game


def test_first_run_shows_starter_selection(tmp_path, pygame_surface):
    app = PokegotchiApp(pygame_surface, tmp_path / "save.json")
    assert app.screen == "starter_selection"
    app.draw()


@pytest.mark.parametrize(
    ("tap", "starter"),
    [((140, 230), "bulbasaur"), ((400, 230), "charmander"), ((660, 230), "squirtle")],
)
def test_starter_card_creates_and_saves_a_game(tmp_path, pygame_surface, tap, starter):
    path = tmp_path / "save.json"
    app = PokegotchiApp(pygame_surface, path)

    app.handle_tap(tap)

    assert app.screen == "home"
    assert load_game(path).line == starter
    app.draw()


def test_invalid_save_returns_to_starter_selection(tmp_path, pygame_surface):
    path = tmp_path / "save.json"
    path.write_text("invalid")

    app = PokegotchiApp(pygame_surface, path)

    assert app.screen == "starter_selection"
    app.draw()


def test_loaded_game_is_shown_on_home_screen(tmp_path, pygame_surface):
    path = tmp_path / "save.json"
    save_game(path, new_game("squirtle", datetime.now(timezone.utc)))

    app = PokegotchiApp(pygame_surface, path)

    assert app.screen == "home"
    app.draw()


@pytest.mark.parametrize(
    ("tap", "stat", "expected"),
    [((110, 415), "hunger", 100), ((300, 415), "happiness", 100), ((500, 415), "health", 100)],
)
def test_care_buttons_apply_rules_and_save(tmp_path, pygame_surface, tap, stat, expected):
    path = tmp_path / "save.json"
    app = PokegotchiApp(pygame_surface, path)
    app.handle_tap((140, 230))

    app.handle_tap(tap)

    assert getattr(load_game(path), stat) == expected
    assert app.reaction_text
    app.draw()


def test_sleep_button_wakes_a_sleeping_pokemon(tmp_path, pygame_surface):
    path = tmp_path / "save.json"
    app = PokegotchiApp(pygame_surface, path)
    app.handle_tap((140, 230))

    app.handle_tap((690, 415))
    assert load_game(path).asleep is True
    app.handle_tap((690, 415))

    assert load_game(path).asleep is False
    assert app.reaction_text


def test_evolution_waits_two_seconds_before_saving(tmp_path, pygame_surface, monkeypatch):
    path = tmp_path / "save.json"
    state = new_game("bulbasaur", datetime.now(timezone.utc))
    state.level, state.xp = 4, 99
    save_game(path, state)
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)
    app = PokegotchiApp(pygame_surface, path)

    app.handle_tap((300, 415))

    assert app.screen == "evolution"
    assert load_game(path).level == 4
    app.draw()
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 2999)
    app.draw()
    assert app.screen == "evolution"
    assert load_game(path).level == 4
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 3000)
    app.draw()
    assert app.screen == "home"
    assert load_game(path).level == 5


def test_missing_sprite_draws_named_placeholder(tmp_path, pygame_surface, monkeypatch):
    from pokegotchi import app as app_module

    monkeypatch.setattr(app_module, "SPRITE_DIR", tmp_path / "no-sprites")
    app = PokegotchiApp(pygame_surface, tmp_path / "save.json")
    app.handle_tap((140, 230))

    app.draw()

    assert pygame_surface.get_at((140, 185))[:3] != pygame_surface.get_at((20, 185))[:3]


def test_available_sprite_is_loaded_without_blurring(tmp_path, pygame_surface, monkeypatch):
    from pokegotchi import app as app_module

    monkeypatch.setattr(app_module, "SPRITE_DIR", tmp_path)
    sprite = pygame.Surface((2, 2), pygame.SRCALPHA)
    sprite.fill((255, 0, 0), pygame.Rect(0, 0, 1, 2))
    sprite.fill((0, 0, 255), pygame.Rect(1, 0, 1, 2))
    pygame.image.save(sprite, str(tmp_path / "bulbasaur.png"))
    app = PokegotchiApp(pygame_surface, tmp_path / "save.json")
    app.handle_tap((140, 230))

    app.draw()

    assert pygame_surface.get_at((130, 200))[:3] == (255, 0, 0)
    assert pygame_surface.get_at((270, 200))[:3] == (0, 0, 255)


def test_main_opens_fullscreen_and_persists_touches(tmp_path, pygame_surface, monkeypatch):
    from pokegotchi import main as main_module

    monkeypatch.setenv("HOME", str(tmp_path))
    set_mode = pygame.display.set_mode
    display_calls = []

    def record_set_mode(size, flags=0):
        display_calls.append((size, flags))
        return set_mode(size, flags)

    batches = iter(
        (
            [pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(140, 230))],
            [pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(110, 415))],
            [pygame.event.Event(pygame.QUIT)],
        )
    )
    monkeypatch.setattr(pygame.display, "set_mode", record_set_mode)
    monkeypatch.setattr(pygame.event, "get", lambda: next(batches))

    main_module.main()

    assert display_calls == [((800, 480), pygame.FULLSCREEN)]
    saved = load_game(tmp_path / ".local/share/pokegotchi/save.json")
    assert saved.line == "bulbasaur"
    assert saved.hunger == 100


def test_quit_saves_evolution_before_animation_finishes(tmp_path, pygame_surface, monkeypatch):
    from pokegotchi import main as main_module

    monkeypatch.setenv("HOME", str(tmp_path))
    path = tmp_path / ".local/share/pokegotchi/save.json"
    path.parent.mkdir(parents=True)
    state = new_game("bulbasaur", datetime.now(timezone.utc))
    state.level, state.xp = 4, 99
    save_game(path, state)
    batches = iter(
        (
            [pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(300, 415))],
            [pygame.event.Event(pygame.QUIT)],
        )
    )
    monkeypatch.setattr(pygame.event, "get", lambda: next(batches))

    main_module.main()

    assert load_game(path).level == 5


def test_quit_persists_unsaved_in_memory_state(tmp_path, pygame_surface, monkeypatch):
    from pokegotchi import main as main_module

    monkeypatch.setenv("HOME", str(tmp_path))
    path = tmp_path / ".local/share/pokegotchi/save.json"
    path.parent.mkdir(parents=True)
    save_game(path, new_game("squirtle", datetime.now(timezone.utc)))
    real_app = main_module.PokegotchiApp
    instances = []

    def make_app(surface, save_path):
        app = real_app(surface, save_path)
        instances.append(app)
        return app

    def quit_after_change():
        instances[0].state.hunger = 17
        return [pygame.event.Event(pygame.QUIT)]

    monkeypatch.setattr(main_module, "PokegotchiApp", make_app)
    monkeypatch.setattr(pygame.event, "get", quit_after_change)

    main_module.main()

    assert load_game(path).hunger == 17


def test_pi_installer_creates_venv_and_autostart_entry(tmp_path):
    project_dir = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python3"
    fake_python.write_text(
        '#!/bin/sh\n'
        'test "$1" = "-m" && test "$2" = "venv" || exit 1\n'
        'mkdir -p "$3/bin"\n'
        'cat > "$3/bin/python" <<\'EOF\'\n'
        '#!/bin/sh\n'
        'printf "%s\\n" "$@" > "$POKEGOTCHI_TEST_LOG"\n'
        'EOF\n'
        'chmod +x "$3/bin/python"\n'
    )
    fake_python.chmod(0o755)
    log = tmp_path / "pip-args"
    env = {
        "HOME": str(tmp_path),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "POKEGOTCHI_TEST_LOG": str(log),
    }

    subprocess.run(["bash", str(project_dir / "scripts/install-pi.sh")], env=env, check=True)

    venv_python = tmp_path / ".local/share/pokegotchi/venv/bin/python"
    entry = (tmp_path / ".config/autostart/pokegotchi.desktop").read_text()
    assert venv_python.is_file()
    assert log.read_text().splitlines() == ["-m", "pip", "install", "-r", str(project_dir / "requirements.txt")]
    assert "Type=Application\n" in entry
    assert f"Exec=env PYTHONPATH={project_dir}/src {venv_python} -m pokegotchi.main\n" in entry
