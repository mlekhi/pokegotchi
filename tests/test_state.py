from datetime import datetime, timedelta, timezone

import pytest

from pokegotchi import state as game
from pokegotchi.state import new_game

NOW = datetime(2026, 10, 5, tzinfo=timezone.utc)


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


def test_play_changes_happiness_energy_and_xp():
    state = new_game("squirtle", NOW)
    assert game.apply_action(state, "play") is True
    assert (state.happiness, state.energy, state.xp) == (100, 65, 10)


def test_fainted_pokemon_can_only_be_healed():
    state = new_game("charmander", NOW)
    state.health = 0
    state.fainted = True
    assert game.apply_action(state, "feed") is False
    assert game.apply_action(state, "heal") is True
    assert state.health == 50
    assert state.fainted is False


def test_level_five_evolves_bulbasaur_to_ivysaur():
    state = new_game("bulbasaur", NOW)
    state.level, state.xp = 4, 99
    game.apply_action(state, "play")
    assert (state.level, game.species_for(state)) == (5, "ivysaur")


def test_feed_clamps_hunger_and_grants_five_xp():
    state = new_game("bulbasaur", NOW)
    assert game.apply_action(state, "feed") is True
    assert (state.hunger, state.xp) == (100, 5)


def test_sleep_toggles_and_wake_is_allowed_while_asleep():
    state = new_game("bulbasaur", NOW)
    assert game.apply_action(state, "sleep") is True
    assert state.asleep is True
    assert game.apply_action(state, "feed") is False
    assert game.apply_action(state, "play") is False
    assert game.apply_action(state, "wake") is True
    assert state.asleep is False
    assert game.apply_action(state, "sleep") is True
    assert game.apply_action(state, "sleep") is True
    assert state.asleep is False


def test_fainted_pokemon_rejects_all_actions_except_heal():
    state = new_game("bulbasaur", NOW)
    state.health = 0
    state.fainted = True
    for action in ("feed", "play", "sleep", "wake"):
        assert game.apply_action(state, action) is False
    assert state.asleep is False
    assert game.apply_action(state, "heal") is True


def test_unknown_action_is_rejected_without_changing_state():
    state = new_game("bulbasaur", NOW)
    before = state.__dict__.copy()
    assert game.apply_action(state, "dance") is False
    assert state.__dict__ == before


def test_xp_preserves_excess_across_multiple_levels():
    state = new_game("bulbasaur", NOW)
    state.xp = 99
    assert game.apply_action(state, "play") is True
    assert (state.level, state.xp) == (3, 34)


@pytest.mark.parametrize(
    ("starter", "middle", "final"),
    [
        ("bulbasaur", "ivysaur", "venusaur"),
        ("charmander", "charmeleon", "charizard"),
        ("squirtle", "wartortle", "blastoise"),
    ],
)
def test_species_changes_at_levels_five_and_ten(starter, middle, final):
    state = new_game(starter, NOW)
    assert game.species_for(state) == starter
    state.level = 5
    assert game.species_for(state) == middle
    state.level = 10
    assert game.species_for(state) == final


def test_level_cap_is_ten():
    state = new_game("squirtle", NOW)
    state.level, state.xp = 9, 224
    assert game.apply_action(state, "play") is True
    assert (state.level, state.xp, game.species_for(state)) == (10, 9, "blastoise")
    for _ in range(100):
        game.apply_action(state, "feed")
    assert state.level == 10


def test_awake_decay_applies_each_hour():
    state = new_game("bulbasaur", NOW)
    game.advance_time(state, NOW + timedelta(hours=1))
    assert (state.hunger, state.happiness, state.energy, state.health) == (72, 76, 74, 80)
    assert state.last_updated == NOW + timedelta(hours=1)


def test_sleeping_decay_restores_energy():
    state = new_game("bulbasaur", NOW)
    state.asleep = True
    game.advance_time(state, NOW + timedelta(hours=1))
    assert (state.hunger, state.happiness, state.energy, state.health) == (76, 78, 90, 80)


@pytest.mark.parametrize(
    ("stat", "starting_value"),
    [("hunger", 32), ("happiness", 18), ("energy", 15)],
)
def test_low_stat_after_decay_costs_health(stat, starting_value):
    state = new_game("bulbasaur", NOW)
    setattr(state, stat, starting_value)
    game.advance_time(state, NOW + timedelta(hours=1))
    assert state.health == 70


def test_health_clamps_at_zero_and_causes_fainting():
    state = new_game("bulbasaur", NOW)
    state.hunger = 0
    state.health = 10
    game.advance_time(state, NOW + timedelta(hours=2))
    assert state.health == 0
    assert state.fainted is True
    assert game.apply_action(state, "heal") is True
    assert (state.health, state.fainted) == (50, False)


def test_offline_decay_is_capped_at_twelve_hours():
    state = new_game("bulbasaur", NOW)
    game.advance_time(state, NOW + timedelta(hours=20))
    assert state.hunger == 0
    assert state.last_updated == NOW + timedelta(hours=20)


def test_later_call_does_not_replay_capped_gap():
    state = new_game("bulbasaur", NOW)
    state.asleep = True
    game.advance_time(state, NOW + timedelta(hours=20))
    assert (state.hunger, state.last_updated) == (32, NOW + timedelta(hours=20))
    game.advance_time(state, NOW + timedelta(hours=21))
    assert (state.hunger, state.last_updated) == (28, NOW + timedelta(hours=21))


def test_partial_hour_updates_timestamp_without_changing_stats():
    state = new_game("bulbasaur", NOW)
    game.advance_time(state, NOW + timedelta(minutes=30))
    assert (state.hunger, state.last_updated) == (80, NOW + timedelta(minutes=30))
    game.advance_time(state, NOW + timedelta(minutes=90))
    assert (state.hunger, state.last_updated) == (72, NOW + timedelta(minutes=90))


def test_time_before_last_update_does_not_change_state():
    state = new_game("bulbasaur", NOW)
    game.advance_time(state, NOW - timedelta(hours=1))
    assert (state.hunger, state.last_updated) == (80, NOW)
