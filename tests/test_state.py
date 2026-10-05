from datetime import datetime, timezone

from pokegotchi.state import new_game


def test_new_game_uses_the_chosen_starter_and_default_stats():
    state = new_game("bulbasaur", datetime(2026, 10, 5, tzinfo=timezone.utc))
    assert (state.line, state.level, state.xp) == ("bulbasaur", 1, 0)
    assert (state.health, state.hunger, state.happiness, state.energy) == (80, 80, 80, 80)
    assert state.asleep is False
    assert state.fainted is False
