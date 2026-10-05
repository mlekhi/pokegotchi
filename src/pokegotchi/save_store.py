import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .state import STARTERS, GameState


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
        data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        return GameState(**data)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
