from datetime import datetime, timezone

import pytest

from pokegotchi.state import new_game


def test_new_game_uses_the_chosen_starter_and_default_stats():
    state = new_game("bulbasaur", datetime(2026, 10, 5, tzinfo=timezone.utc))
    assert (state.line, state.level, state.xp) == ("bulbasaur", 1, 0)
    assert (state.health, state.hunger, state.happiness, state.energy) == (80, 80, 80, 80)
    assert state.asleep is False
    assert state.fainted is False


def test_game_state_rejects_out_of_range_stat_values_on_construction():
    from pokegotchi.state import GameState

    values = ["bulbasaur", 1, 0, 80, 80, 80, 101, False, False, datetime.now(timezone.utc)]
    with pytest.raises(ValueError, match="energy"):
        GameState(*values)


def test_game_state_rejects_non_integer_stat_values_on_mutation():
    state = new_game("bulbasaur", datetime(2026, 10, 5, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="health"):
        state.health = 99.5
