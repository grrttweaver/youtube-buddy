"""Application configuration persistence."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from platformdirs import user_config_dir

APP_NAME = "youtube-buddy"
CONFIG_FILENAME = "config.json"


def config_dir() -> Path:
    path = Path(user_config_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_dir() / CONFIG_FILENAME


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    path = config_path()
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_database_path() -> Path | None:
    value = load_config().get("database_path")
    return Path(value) if value else None


def set_database_path(path: Path) -> None:
    config = load_config()
    config["database_path"] = str(path)
    save_config(config)


def get_window_geometry() -> bytes | None:
    value = load_config().get("window_geometry")
    if not isinstance(value, str) or not value:
        return None
    try:
        return base64.b64decode(value.encode("ascii"))
    except (ValueError, UnicodeError):
        return None


def set_window_geometry(data: bytes) -> None:
    config = load_config()
    config["window_geometry"] = base64.b64encode(data).decode("ascii")
    save_config(config)
