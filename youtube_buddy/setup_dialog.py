"""Initial database setup dialog."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from youtube_buddy.database import (
    DATABASE_OPEN_FILTER,
    DATABASE_SAVE_FILTER,
    default_database_path,
    ensure_database_suffix,
    migrate_legacy_database,
)


class SetupDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("YouTube Buddy — Setup")
        self.setMinimumWidth(480)
        self._database_path: Path | None = None

        title = QLabel("Welcome to YouTube Buddy")
        title.setObjectName("setupTitle")

        subtitle = QLabel(
            "Choose how you'd like to store your playlist. "
            "Your choice will be remembered for next time."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("setupSubtitle")

        self.new_radio = QRadioButton("Create a new playlist database")
        self.existing_radio = QRadioButton("Use an existing playlist database")
        self.new_radio.setChecked(True)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select a location for your database…")
        self.path_input.setReadOnly(True)

        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self._browse)

        path_row = QHBoxLayout()
        path_row.addWidget(self.path_input, stretch=1)
        path_row.addWidget(browse_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(self.new_radio)
        layout.addWidget(self.existing_radio)
        layout.addLayout(path_row)
        layout.addWidget(self.status_label)
        layout.addWidget(buttons)

        self.new_radio.toggled.connect(self._update_default_path)
        self._update_default_path()

    def database_path(self) -> Path | None:
        return self._database_path

    def _update_default_path(self) -> None:
        if self.new_radio.isChecked() and not self.path_input.text():
            default = default_database_path()
            self.path_input.setText(str(default))
            self._database_path = default
        self.status_label.setText("")

    def _browse(self) -> None:
        if self.new_radio.isChecked():
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Create Playlist Database",
                str(default_database_path()),
                DATABASE_SAVE_FILTER,
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Playlist Database",
                str(Path.home()),
                DATABASE_OPEN_FILTER,
            )

        if path:
            self.path_input.setText(path)
            self._database_path = Path(path)
            self.status_label.setText("")

    def _accept(self) -> None:
        path_text = self.path_input.text().strip()
        if not path_text:
            self.status_label.setText("Please choose a database location.")
            return

        path = Path(path_text)
        if self.existing_radio.isChecked() and not path.exists():
            self.status_label.setText("That database file does not exist.")
            return

        if self.new_radio.isChecked():
            path.parent.mkdir(parents=True, exist_ok=True)
            path = ensure_database_suffix(path)
        else:
            path = migrate_legacy_database(path)

        self._database_path = path
        self.accept()
