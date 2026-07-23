"""Application asset paths."""

from __future__ import annotations

import sys
from pathlib import Path


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


ASSETS_DIR = _resource_root() / "assets"
APP_ICON_PATH = ASSETS_DIR / "icon.png"

