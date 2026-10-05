from dataclasses import dataclass
from datetime import datetime

STARTERS = {"bulbasaur", "charmander", "squirtle"}


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
    """Apply an action when supported; task 1 defines no actions yet."""
    return False
