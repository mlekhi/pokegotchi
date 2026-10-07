import json
from datetime import datetime, timezone

import pytest

from pokegotchi.save_store import load_game, save_game
from pokegotchi.state import new_game

NOW = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)


def test_save_round_trip_preserves_game_state(tmp_path):
    path = tmp_path / "save.json"
    original = new_game("charmander", NOW)
    original.level, original.xp, original.asleep = 5, 12, True

    save_game(path, original)

    assert load_game(path) == original


def test_existing_save_without_elapsed_counters_still_loads(tmp_path):
    path = tmp_path / "save.json"
    path.write_text(json.dumps({
        "line": "bulbasaur",
        "level": 1,
        "xp": 0,
        "health": 80,
        "hunger": 80,
        "happiness": 80,
        "energy": 80,
        "asleep": False,
        "fainted": False,
        "last_updated": NOW.isoformat(),
    }))

    state = load_game(path)

    assert state is not None
    assert state.awake_elapsed_us == 0
    assert state.sleep_elapsed_us == 0


def test_invalid_save_starts_a_new_selection(tmp_path):
    path = tmp_path / "save.json"
    path.write_text("not json")

    assert load_game(path) is None


def test_missing_save_starts_a_new_selection(tmp_path):
    assert load_game(tmp_path / "missing.json") is None


@pytest.mark.parametrize(
    "updates",
    [
        {"line": "pikachu"},
        {"health": 101},
        {"last_updated": "not a timestamp"},
    ],
)
def test_invalid_fields_start_a_new_selection(tmp_path, updates):
    path = tmp_path / "save.json"
    data = {
        "line": "bulbasaur",
        "level": 1,
        "xp": 0,
        "health": 80,
        "hunger": 80,
        "happiness": 80,
        "energy": 80,
        "asleep": False,
        "fainted": False,
        "last_updated": NOW.isoformat(),
    }
    data.update(updates)
    path.write_text(json.dumps(data))

    assert load_game(path) is None


def test_missing_fields_start_a_new_selection(tmp_path):
    path = tmp_path / "save.json"
    path.write_text(json.dumps({"line": "bulbasaur"}))

    assert load_game(path) is None


@pytest.mark.parametrize(
    "updates",
    [
        {"level": 0},
        {"level": 11},
        {"level": True},
        {"xp": -1},
        {"xp": 1.5},
        {"asleep": 1},
        {"fainted": "false"},
        {"last_updated": "2026-10-05T12:00:00"},
    ],
)
def test_invalid_runtime_fields_start_a_new_selection(tmp_path, updates):
    path = tmp_path / "save.json"
    data = {
        "line": "bulbasaur",
        "level": 1,
        "xp": 0,
        "health": 80,
        "hunger": 80,
        "happiness": 80,
        "energy": 80,
        "asleep": False,
        "fainted": False,
        "last_updated": NOW.isoformat(),
    }
    data.update(updates)
    path.write_text(json.dumps(data))

    assert load_game(path) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("awake_elapsed_us", -1),
        ("awake_elapsed_us", 3_600_000_000),
        ("awake_elapsed_us", 1.5),
        ("sleep_elapsed_us", None),
        ("sleep_elapsed_us", True),
    ],
)
def test_invalid_elapsed_remainder_starts_a_new_selection(tmp_path, field, value):
    path = tmp_path / "save.json"
    state = new_game("bulbasaur", NOW)
    save_game(path, state)
    data = json.loads(path.read_text())
    data[field] = value
    path.write_text(json.dumps(data))

    assert load_game(path) is None
