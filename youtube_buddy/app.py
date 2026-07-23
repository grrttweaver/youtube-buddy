"""Application bootstrap and setup flow."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from youtube_buddy.assets import APP_ICON_PATH
from youtube_buddy.config import get_database_path, set_database_path
from youtube_buddy.database import Database
from youtube_buddy.main_window import MainWindow
from youtube_buddy.macos_glass import apply_macos_glass, is_macos
from youtube_buddy.setup_dialog import SetupDialog
from youtube_buddy.styles import get_stylesheet


def resolve_database_path(parent) -> Path | None:
    existing = get_database_path()
    if existing and existing.exists():
        return existing

    if existing and not existing.exists():
        answer = QMessageBox.question(
            parent,
            "Database Not Found",
            f"The saved playlist database could not be found:\n{existing}\n\n"
            "Would you like to choose a different database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return None

    dialog = SetupDialog(parent)
    if dialog.exec() != SetupDialog.DialogCode.Accepted:
        return None

    path = dialog.database_path()
    if path is None:
        return None

    set_database_path(path)
    return path


def _load_app_icon() -> QIcon | None:
    if not APP_ICON_PATH.exists():
        return None
    icon = QIcon(str(APP_ICON_PATH))
    return icon if not icon.isNull() else None


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("YouTube Buddy")
    app.setApplicationDisplayName("YouTube Buddy")
    if icon := _load_app_icon():
        app.setWindowIcon(icon)
    app.setStyle("Fusion")
    app.setStyleSheet(get_stylesheet())

    db_path = resolve_database_path(None)
    if db_path is None:
        return 0

    database = Database(db_path)
    window = MainWindow(database)
    if icon := _load_app_icon():
        window.setWindowIcon(icon)
    if is_macos():
        apply_macos_glass(window)
    else:
        window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
