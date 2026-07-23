"""macOS Liquid Glass window styling."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QMainWindow


def is_macos() -> bool:
    return sys.platform == "darwin"


def apply_macos_glass(window: QMainWindow) -> None:
    """Apply native macOS glass to the main window. No-op if unavailable."""
    if not is_macos():
        window.show()
        return

    try:
        import pyqt_liquidglass as glass
    except ImportError:
        window.show()
        return

    glass.prepare_window_for_glass(window)
    glass.apply_glass_to_window(window)
    glass.setup_traffic_lights_inset(window, x_offset=16, y_offset=14)
