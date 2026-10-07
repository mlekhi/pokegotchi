import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .state import HOUR_MICROSECONDS, STARTERS, GameState


def _encode_datetime(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"cannot encode {type(value).__name__}")


def save_game(path: Path, state: GameState) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(asdict(state), default=_encode_datetime))
    temporary.replace(path)


def load_game(path: Path) -> GameState | None:
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or data.get("line") not in STARTERS:
            return None
        if type(data.get("level")) is not int or not 1 <= data["level"] <= 10:
            return None
        if type(data.get("xp")) is not int or data["xp"] < 0:
            return None
        if type(data.get("asleep")) is not bool or type(data.get("fainted")) is not bool:
            return None
        for field in ("awake_elapsed_us", "sleep_elapsed_us"):
            value = data.get(field, 0)
            if type(value) is not int or not 0 <= value < HOUR_MICROSECONDS:
                return None

        last_updated = datetime.fromisoformat(data["last_updated"])
        if last_updated.tzinfo is None or last_updated.utcoffset() is None:
            return None
        data["last_updated"] = last_updated
        return GameState(**data)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
