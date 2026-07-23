"""Visual queue for in-progress URL imports."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from youtube_buddy.media_urls import media_platform
from youtube_buddy.social import extract_facebook_reel_id, extract_instagram_reel_id
from youtube_buddy.youtube import extract_playlist_id, extract_video_id, is_playlist_url, is_short_url


def _import_label(url: str) -> str:
    platform = media_platform(url)

    if platform == "instagram":
        reel_id = extract_instagram_reel_id(url)
        if reel_id:
            short_id = reel_id if len(reel_id) <= 18 else f"{reel_id[:18]}…"
            return f"Instagram Reel · {short_id}"
        return "Instagram Reel"

    if platform == "facebook":
        reel_id = extract_facebook_reel_id(url)
        if reel_id:
            short_id = reel_id if len(reel_id) <= 18 else f"{reel_id[:18]}…"
            return f"Facebook Reel · {short_id}"
        return "Facebook Reel"

    if is_playlist_url(url):
        playlist_id = extract_playlist_id(url)
        if playlist_id:
            short_id = playlist_id if len(playlist_id) <= 18 else f"{playlist_id[:18]}…"
            return f"Playlist · {short_id}"
        return "Playlist"

    video_id = extract_video_id(url)
    if video_id:
        if is_short_url(url):
            return f"Short · {video_id}"
        return f"Video · {video_id}"

    return "Video link"


class _ImportQueueRow(QWidget):
    def __init__(self, url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.url = url
        self.setObjectName("importQueueRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.status_label = QLabel("…")
        self.status_label.setObjectName("importQueueStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFixedWidth(16)

        self.text_label = QLabel(_import_label(url))
        self.text_label.setObjectName("importQueueText")
        self.text_label.setTextFormat(Qt.TextFormat.PlainText)

        layout.addWidget(self.status_label)
        layout.addWidget(self.text_label, stretch=1)

    def set_importing(self) -> None:
        self.setProperty("failed", False)
        self.status_label.setText("…")
        self.text_label.setText(_import_label(self.url))
        self.style().unpolish(self)
        self.style().polish(self)

    def set_failed(self, message: str) -> None:
        self.setProperty("failed", True)
        self.status_label.setText("!")
        self.text_label.setText(message)
        self.style().unpolish(self)
        self.style().polish(self)


class ImportQueueWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("importQueue")
        self._rows: dict[str, _ImportQueueRow] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("importQueueSummary")

        self.rows_container = QWidget()
        self.rows_container.setObjectName("importQueueRows")
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(4)

        outer.addWidget(self.summary_label)
        outer.addWidget(self.rows_container)
        self.hide()

    def active_count(self) -> int:
        return len(self._rows)

    def add(self, url: str) -> None:
        if url in self._rows:
            return

        row = _ImportQueueRow(url, self.rows_container)
        self._rows[url] = row
        self.rows_layout.addWidget(row)
        self._refresh()

    def remove(self, url: str) -> None:
        row = self._rows.pop(url, None)
        if row is None:
            return

        self.rows_layout.removeWidget(row)
        row.deleteLater()
        self._refresh()

    def mark_failed(self, url: str, message: str) -> None:
        row = self._rows.get(url)
        if row is None:
            return

        short = message.strip()
        if len(short) > 72:
            short = f"{short[:69]}…"
        row.set_failed(f"Failed · {short}")

        QTimer.singleShot(5000, lambda url=url: self.remove(url))

    def clear(self) -> None:
        for row in list(self._rows.values()):
            self.rows_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()
        self.hide()

    def _refresh(self) -> None:
        count = len(self._rows)
        if count == 0:
            self.hide()
            return

        noun = "import" if count == 1 else "imports"
        self.summary_label.setText(f"Importing {count} {noun}")
        self.show()
