from dataclasses import dataclass
from datetime import datetime, timedelta

STARTERS = {"bulbasaur", "charmander", "squirtle"}
ACTION_EFFECTS = {
    "feed": {"hunger": 30, "xp": 5},
    "play": {"happiness": 20, "energy": -15, "xp": 10},
    "heal": {"health": 50, "xp": 0},
}
EVOLUTIONS = {
    "bulbasaur": {5: "ivysaur", 10: "venusaur"},
    "charmander": {5: "charmeleon", 10: "charizard"},
    "squirtle": {5: "wartortle", 10: "blastoise"},
}


@dataclass
class GameState:
    line: str
    level: int
    xp: int
    health: int
    hunger: int
    happiness: int
    energy: int
    asleep: bool
    fainted: bool
    last_updated: datetime

    def __setattr__(self, name: str, value: object) -> None:
        if name in {"health", "hunger", "happiness", "energy"}:
            if type(value) is not int or not 0 <= value <= 100:
                raise ValueError(f"{name} must be an integer from 0 to 100")
        super().__setattr__(name, value)


def new_game(starter: str, now: datetime) -> GameState:
    if starter not in STARTERS:
        raise ValueError(f"unknown starter: {starter}")
    return GameState(starter, 1, 0, 80, 80, 80, 80, False, False, now)


def apply_action(state: GameState, action: str) -> bool:
    if action not in ACTION_EFFECTS and action not in {"sleep", "wake"}:
        return False
    if state.fainted and action != "heal":
        return False
    if state.asleep and action in {"feed", "play"}:
        return False

    if action == "sleep":
        state.asleep = not state.asleep
        return True
    if action == "wake":
        if not state.asleep:
            return False
        state.asleep = False
        return True

    for stat, change in ACTION_EFFECTS[action].items():
        if stat == "xp":
            state.xp += change
        else:
            setattr(state, stat, max(0, min(100, getattr(state, stat) + change)))
    if action == "heal":
        state.fainted = state.health == 0
    while state.level < 10 and state.xp >= state.level * 25:
        state.xp -= state.level * 25
        state.level += 1
    return True


def species_for(state: GameState) -> str:
    species = state.line
    for level, evolution in EVOLUTIONS[state.line].items():
        if state.level >= level:
            species = evolution
    return species


def advance_time(state: GameState, now: datetime) -> None:
    hours = min(12, int((now - state.last_updated).total_seconds() // 3600))
    if hours <= 0:
        return

    for _ in range(hours):
        if state.asleep:
            changes = {"hunger": -4, "happiness": -2, "energy": 10}
        else:
            changes = {"hunger": -8, "happiness": -4, "energy": -6}
        for stat, change in changes.items():
            setattr(state, stat, max(0, min(100, getattr(state, stat) + change)))
        if state.hunger < 25 or state.happiness < 15 or state.energy < 10:
            state.health = max(0, state.health - 10)
        state.fainted = state.health == 0

    state.last_updated += timedelta(hours=hours)
