"""macOS Liquid Glass window styling."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QTimer
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
    configure_macos_window_drag(window)


def _ns_rect_metrics(rect) -> tuple[float, float, float, float]:
    if hasattr(rect, "origin") and hasattr(rect, "size"):
        return rect.origin.x, rect.origin.y, rect.size.width, rect.size.height
    (origin, size) = rect
    if hasattr(origin, "x"):
        return origin.x, origin.y, size.width, size.height
    return origin[0], origin[1], size[0], size[1]


def traffic_light_vertical_metrics(
    window: QMainWindow,
) -> tuple[int, int] | None:
    """Return traffic-light top inset and bottom edge in QMainWindow coordinates."""
    if not is_macos():
        return None

    try:
        from pyqt_liquidglass._bridge import get_nswindow_from_widget
    except ImportError:
        return None

    ns_window = get_nswindow_from_widget(window)
    if ns_window is None:
        return None

    close_btn = ns_window.standardWindowButton_(0)  # ty: ignore
    if close_btn is None:
        return None

    titlebar = close_btn.superview()  # ty: ignore
    if titlebar is None:
        return None

    _, btn_y, _, btn_height = _ns_rect_metrics(close_btn.frame())  # ty: ignore
    _, _, _, titlebar_height = _ns_rect_metrics(titlebar.frame())  # ty: ignore
    btn_top = int(titlebar_height - (btn_y + btn_height))
    btn_bottom = int(titlebar_height - btn_y)
    return btn_top, btn_bottom


def configure_macos_window_drag(window: QMainWindow) -> None:
    """Sync top padding and the invisible drag overlay after glass is applied."""
    sync_margin = getattr(window, "_sync_macos_top_margin", None)
    if sync_margin is not None:
        QTimer.singleShot(0, sync_margin)
        QTimer.singleShot(50, sync_margin)

    drag_region = getattr(window, "_drag_region", None)
    if drag_region is not None:
        drag_region.raise_()
