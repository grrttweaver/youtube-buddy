"""Main application window."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QEvent, QUrl, QSize, Qt
from PyQt6.QtGui import QDesktopServices, QDragEnterEvent, QDragLeaveEvent, QDropEvent, QImage, QPixmap, QResizeEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from youtube_buddy.action_delegate import ActionButtonDelegate
from youtube_buddy.checkbox_delegate import CheckboxDelegate
from youtube_buddy.config import get_window_geometry, set_window_geometry
from youtube_buddy.database import Database, Video
from youtube_buddy.drop_overlay import DropOverlay
from youtube_buddy.import_queue import ImportQueueWidget
from youtube_buddy.hover_table import HoverTableView, RowHoverDelegate
from youtube_buddy.title_delegate import TitleDelegate
from youtube_buddy.video_model import (
    COL_ACTIONS,
    COL_LENGTH,
    COL_SELECT,
    COL_THUMBNAIL,
    COL_TITLE,
    MIME_TYPE,
    VideoTableModel,
)
from youtube_buddy.workers import MetadataWorker, ThumbnailLoader
from youtube_buddy.media_urls import (
    VideoMetadata,
    extract_media_url_from_text,
    normalize_media_url,
)


class MainWindow(QMainWindow):
    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database
        self.setWindowTitle("YouTube Buddy")
        self.setMinimumSize(720, 520)
        self._restore_window_geometry()

        self._metadata_workers: list[MetadataWorker] = []
        self._thumbnail_loader = ThumbnailLoader(self)
        self._pending_urls: set[str] = set()
        self._drop_hover_count = 0
        self._remove_confirm_pending = False

        self.model = VideoTableModel(self)
        self.model.set_videos(database.list_videos())

        self._central = QWidget()
        self.setCentralWidget(self._central)
        if sys.platform == "darwin":
            self._central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self._central)
        top_margin = 36 if sys.platform == "darwin" else 20
        layout.setContentsMargins(20, top_margin, 20, 16)
        layout.setSpacing(16)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste a video link…")
        self.url_input.textChanged.connect(self._on_url_text_changed)
        self.url_input.returnPressed.connect(self._add_from_input)

        self.add_button = QPushButton("Add")
        self.add_button.setObjectName("addButton")
        self.add_button.setVisible(False)
        self.add_button.clicked.connect(self._add_from_input)

        input_row.addWidget(self.url_input, stretch=1)
        input_row.addWidget(self.add_button)

        self.import_queue = ImportQueueWidget()

        self.select_all_button = QPushButton("Select All")
        self.select_all_button.setObjectName("selectAllButton")
        self.select_all_button.setVisible(False)
        self.select_all_button.clicked.connect(self._select_all_videos)

        self.remove_selected_button = QPushButton("Remove Selected")
        self.remove_selected_button.setObjectName("removeSelectedButton")
        self.remove_selected_button.setVisible(False)
        self.remove_selected_button.clicked.connect(self._remove_selected_videos)

        self.remove_confirm_label = QLabel("Click again to remove")
        self.remove_confirm_label.setObjectName("removeConfirmLabel")
        self.remove_confirm_label.setVisible(False)

        selection_toolbar = QHBoxLayout()
        selection_toolbar.setSpacing(10)
        selection_toolbar.addWidget(self.select_all_button)
        selection_toolbar.addStretch()
        selection_toolbar.addWidget(self.remove_confirm_label)
        selection_toolbar.addWidget(self.remove_selected_button)

        self.table = HoverTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDropIndicatorShown(True)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.table.setDragDropOverwriteMode(False)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(78)
        self.table.setIconSize(QSize(112, 63))
        self.table.setWordWrap(True)

        self.row_delegate = RowHoverDelegate(self.table)
        self.table.setItemDelegateForColumn(COL_THUMBNAIL, self.row_delegate)
        self.table.setItemDelegateForColumn(COL_LENGTH, self.row_delegate)
        self.title_delegate = TitleDelegate(self.table)
        self.table.setItemDelegateForColumn(COL_TITLE, self.title_delegate)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_SELECT, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_THUMBNAIL, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_LENGTH, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_TITLE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_ACTIONS, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(COL_SELECT, 40)
        self.table.setColumnWidth(COL_THUMBNAIL, 128)
        self.table.setColumnWidth(COL_LENGTH, 72)
        self.table.setColumnWidth(COL_ACTIONS, 52)

        self.checkbox_delegate = CheckboxDelegate(self.table)
        self.table.setItemDelegateForColumn(COL_SELECT, self.checkbox_delegate)

        self.action_delegate = ActionButtonDelegate(self.table)
        self.action_delegate.delete_clicked.connect(self._delete_video_at_row)
        self.table.setItemDelegateForColumn(COL_ACTIONS, self.action_delegate)

        self.table.clicked.connect(self._on_row_clicked)
        self.model.order_changed.connect(self._persist_order)
        self.model.selection_changed.connect(self._update_selection_toolbar)

        layout.addLayout(input_row)
        layout.addWidget(self.import_queue)
        layout.addLayout(selection_toolbar)
        layout.addWidget(self.table, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.installEventFilter(self)
        self._set_status(f"{len(self.model.videos())} videos in playlist")

        self.setAcceptDrops(True)
        self._central.setAcceptDrops(True)
        self._install_drop_forwarding(self._central)

        self.drop_overlay = DropOverlay(self._central)
        self._position_drop_overlay()

        self._load_thumbnails_for_all()

    def _restore_window_geometry(self) -> None:
        geometry = get_window_geometry()
        if geometry and self.restoreGeometry(geometry):
            if self.width() < self.minimumWidth() or self.height() < self.minimumHeight():
                self.resize(
                    max(self.width(), self.minimumWidth()),
                    max(self.height(), self.minimumHeight()),
                )
            return
        self.resize(860, 620)

    def _install_drop_forwarding(self, widget: QWidget) -> None:
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_drop_overlay()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # noqa: N802
        self._hide_drop_overlay()
        super().dragLeaveEvent(event)

    def _position_drop_overlay(self) -> None:
        self.drop_overlay.setGeometry(self._central.rect())

    def _show_drop_overlay(self) -> None:
        self._drop_hover_count += 1
        if self._drop_hover_count == 1:
            self._position_drop_overlay()
            self.drop_overlay.show()
            self.drop_overlay.raise_()

    def _hide_drop_overlay(self) -> None:
        if self._drop_hover_count <= 0:
            return
        self._drop_hover_count -= 1
        if self._drop_hover_count == 0:
            self.drop_overlay.hide()

    def _reset_drop_overlay(self) -> None:
        self._drop_hover_count = 0
        self.drop_overlay.hide()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.DragEnter:
            handled = self._handle_drag_enter(event)
            if handled:
                self._show_drop_overlay()
            return handled
        if event.type() == QEvent.Type.DragMove:
            if self._mime_has_media_url(event.mimeData()):
                event.acceptProposedAction()
                return True
            return False
        if event.type() == QEvent.Type.DragLeave:
            self._hide_drop_overlay()
            return False
        if event.type() == QEvent.Type.Drop:
            handled = self._handle_drop(event)
            self._reset_drop_overlay()
            return handled
        return super().eventFilter(obj, event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._handle_drag_enter(event):
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        if self._handle_drop(event):
            self._reset_drop_overlay()
            return
        super().dropEvent(event)

    def _handle_drag_enter(self, event) -> bool:
        mime = event.mimeData()
        if mime.hasFormat(MIME_TYPE):
            return False
        if self._mime_has_media_url(mime):
            event.acceptProposedAction()
            return True
        return False

    def _handle_drop(self, event) -> bool:
        mime = event.mimeData()
        if mime.hasFormat(MIME_TYPE):
            return False
        url = self._url_from_mime(mime)
        if not url:
            return False
        event.acceptProposedAction()
        self.add_video_url(url)
        return True

    @staticmethod
    def _mime_has_media_url(mime) -> bool:
        if mime.hasUrls():
            for url in mime.urls():
                if normalize_media_url(url.toString()):
                    return True
        if mime.hasText():
            return extract_media_url_from_text(mime.text()) is not None
        return False

    @staticmethod
    def _url_from_mime(mime) -> str | None:
        if mime.hasUrls():
            for url in mime.urls():
                normalized = normalize_media_url(url.toString())
                if normalized:
                    return normalized
        if mime.hasText():
            return extract_media_url_from_text(mime.text())
        return None

    def _on_url_text_changed(self, text: str) -> None:
        normalized = extract_media_url_from_text(text)
        self.add_button.setVisible(normalized is not None)

    def _add_from_input(self) -> None:
        url = extract_media_url_from_text(self.url_input.text())
        if not url:
            self._set_status("That doesn't look like a valid video link.", error=True)
            return
        self.url_input.clear()
        self.add_button.setVisible(False)
        self.add_video_url(url)

    def add_video_url(self, url: str) -> None:
        normalized = normalize_media_url(url)
        if not normalized:
            self._set_status("That doesn't look like a valid video link.", error=True)
            return

        if normalized in self._pending_urls:
            self._set_status("That video is already being added.", error=True)
            return

        existing = self.database.video_by_url(normalized)
        if existing:
            self._set_status("That video is already in your playlist.", error=True)
            return

        self._pending_urls.add(normalized)
        self.import_queue.add(normalized)
        self._refresh_import_status()

        worker = MetadataWorker(normalized, parent=self)
        worker.finished_with_result.connect(self._on_metadata_loaded)
        worker.failed.connect(
            lambda message, url=normalized: self._on_metadata_failed(url, message)
        )
        worker.finished.connect(lambda worker=worker: self._cleanup_metadata_worker(worker))
        self._metadata_workers.append(worker)
        worker.start()

    def _on_metadata_loaded(self, metadata: VideoMetadata) -> None:
        self._pending_urls.discard(metadata.url)
        self.import_queue.remove(metadata.url)

        duplicate = self.database.video_by_url(metadata.url)
        if duplicate:
            self._refresh_import_status(error="That video is already in your playlist.")
            return

        video = self.database.insert_video(
            url=metadata.url,
            video_id=metadata.video_id,
            title=metadata.title,
            duration_seconds=metadata.duration_seconds,
            thumbnail_url=metadata.thumbnail_url,
            is_playlist=metadata.is_playlist,
            is_short=metadata.is_short,
            platform=metadata.platform,
        )
        self.model.append_video(video)
        self._load_thumbnail(video)
        self._refresh_import_status(success=f"Added “{video.title}”")

    def _on_metadata_failed(self, url: str, message: str) -> None:
        self._pending_urls.discard(url)
        self.import_queue.mark_failed(url, message)
        self._refresh_import_status(error=f"Could not fetch video details: {message}")

    def _load_thumbnails_for_all(self) -> None:
        for video in self.model.videos():
            if video.thumbnail_url:
                self._load_thumbnail(video)

    def _load_thumbnail(self, video: Video) -> None:
        if video.thumbnail_url:
            self._thumbnail_loader.enqueue(video.id, video.thumbnail_url)

    def _on_thumbnail_loaded(self, video_id: int, data: bytes) -> None:
        image = QImage()
        if not image.loadFromData(data):
            return

        scaled = QPixmap.fromImage(image).scaled(
            112,
            63,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.model.set_thumbnail(video_id, scaled)

    def _on_thumbnail_failed(self, _video_id: int) -> None:
        pass

    def _on_row_clicked(self, index) -> None:
        if index.column() in (COL_SELECT, COL_ACTIONS):
            return

        video = self.model.video_at(index.row())
        if video and QDesktopServices.openUrl(QUrl(video.url)):
            self._set_status(f"Opened “{video.title or video.url}” in browser")

    def _update_selection_toolbar(self) -> None:
        if self._remove_confirm_pending:
            self._cancel_remove_confirmation()

        has_selection = self.model.checked_count() > 0
        self.select_all_button.setVisible(has_selection)
        self.remove_selected_button.setVisible(has_selection)

    def _set_remove_confirmation_pending(self, pending: bool) -> None:
        self._remove_confirm_pending = pending
        self.remove_confirm_label.setVisible(pending)
        self.remove_selected_button.setProperty("armed", pending)
        self.remove_selected_button.style().unpolish(self.remove_selected_button)
        self.remove_selected_button.style().polish(self.remove_selected_button)

    def _cancel_remove_confirmation(self) -> None:
        if self._remove_confirm_pending:
            self._set_remove_confirmation_pending(False)

    def _select_all_videos(self) -> None:
        self.model.select_all()

    def _remove_selected_videos(self) -> None:
        video_ids = self.model.checked_video_ids()
        if not video_ids:
            self._cancel_remove_confirmation()
            return

        if not self._remove_confirm_pending:
            self._set_remove_confirmation_pending(True)
            return

        count = len(video_ids)
        noun = "video" if count == 1 else "videos"
        removed = self.model.remove_videos(video_ids)
        if removed:
            self.database.delete_videos([video.id for video in removed])
            self._set_status(f"Removed {len(removed)} {noun}")
        self._cancel_remove_confirmation()
        self._update_selection_toolbar()

    def _delete_video_at_row(self, row: int) -> None:
        video = self.model.video_at(row)
        if video is None:
            return

        title = video.title or video.url
        removed = self.model.remove_video(video.id)
        if removed is None:
            return

        self.database.delete_video(removed.id)
        self._set_status(f"Removed “{title}”")

    def _persist_order(self) -> None:
        ordered_ids = [video.id for video in self.model.videos()]
        if ordered_ids:
            self.database.update_sort_orders(ordered_ids)
        self._set_status(f"{len(ordered_ids)} videos in playlist")

    def _cleanup_metadata_worker(self, worker: MetadataWorker) -> None:
        if worker in self._metadata_workers:
            self._metadata_workers.remove(worker)
        worker.deleteLater()

    def _refresh_import_status(
        self,
        *,
        success: str | None = None,
        error: str | None = None,
    ) -> None:
        pending = len(self._pending_urls)
        if pending:
            noun = "import" if pending == 1 else "imports"
            message = f"Importing {pending} {noun}…"
            if error:
                message = f"{message} {error}"
            self._set_status(message, error=bool(error))
            return

        if error:
            self._set_status(error, error=True)
            return

        if success:
            self._set_status(success)
            return

        self._set_status(f"{len(self.model.videos())} videos in playlist")

    def _set_status(self, message: str, *, error: bool = False) -> None:
        self.status_bar.setStyleSheet(
            "color: #f7768e;" if error else "color: #565f89;"
        )
        self.status_bar.showMessage(message)

    def closeEvent(self, event) -> None:  # noqa: N802
        set_window_geometry(bytes(self.saveGeometry()))
        for worker in self._metadata_workers:
            if worker.isRunning():
                worker.wait(5000)
        self._thumbnail_loader.wait_for_all()
        self.database.close()
        super().closeEvent(event)
