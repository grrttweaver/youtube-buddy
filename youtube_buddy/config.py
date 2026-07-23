"""Application configuration persistence."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from platformdirs import user_config_dir

APP_NAME = "youtube-buddy"
CONFIG_FILENAME = "config.json"
MAX_RECENT_DATABASES = 5


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
    config["database_path"] = str(path.resolve())
    save_config(config)


def get_recent_database_paths(*, existing_only: bool = False) -> list[Path]:
    paths = [
        Path(value)
        for value in load_config().get("recent_database_paths", [])
        if value
    ]
    if existing_only:
        paths = [path for path in paths if path.exists()]
    return paths[:MAX_RECENT_DATABASES]


def remember_database(path: Path) -> None:
    resolved = str(path.resolve())
    config = load_config()
    recent = [
        item
        for item in config.get("recent_database_paths", [])
        if item and item != resolved
    ]
    recent.insert(0, resolved)
    config["recent_database_paths"] = recent[:MAX_RECENT_DATABASES]
    config["database_path"] = resolved
    save_config(config)


def remove_recent_database(path: Path) -> None:
    resolved = str(path.resolve())
    config = load_config()
    config["recent_database_paths"] = [
        item
        for item in config.get("recent_database_paths", [])
        if item and item != resolved
    ]
    save_config(config)


def replace_database_path(old: Path, new: Path) -> None:
    old_resolved = old.resolve()
    new_resolved = new.resolve()
    if old_resolved == new_resolved:
        return

    config = load_config()

    stored = config.get("database_path")
    if stored and Path(stored).resolve() == old_resolved:
        config["database_path"] = str(new_resolved)

    recent: list[str] = []
    seen: set[str] = set()
    for item in config.get("recent_database_paths", []):
        if not item:
            continue
        item_path = Path(item)
        updated = str(new_resolved) if item_path.resolve() == old_resolved else item
        if updated in seen:
            continue
        seen.add(updated)
        recent.append(updated)

    config["recent_database_paths"] = recent
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
