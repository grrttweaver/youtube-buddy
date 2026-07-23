"""Main application window."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QEvent, QPoint, QTimer, QUrl, QSize, Qt
from PyQt6.QtGui import (
    QDesktopServices,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDropEvent,
    QImage,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPixmap,
    QResizeEvent,
    QColor,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from youtube_buddy.action_delegate import ActionButtonDelegate
from youtube_buddy.checkbox_delegate import CheckboxDelegate
from youtube_buddy.config import (
    get_recent_database_paths,
    get_window_geometry,
    remember_database,
    remove_recent_database,
    set_window_geometry,
)
from youtube_buddy.database import (
    DATABASE_OPEN_FILTER,
    DATABASE_SAVE_FILTER,
    Database,
    Video,
    default_database_path,
    ensure_database_suffix,
    migrate_legacy_database,
)
from youtube_buddy.drop_overlay import DropOverlay
from youtube_buddy.import_queue import ImportQueueWidget
from youtube_buddy.hover_table import (
    HoverTableView,
    OpaqueHeaderView,
    RowHoverDelegate,
    TABLE_VIEWPORT_BG,
)
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


class TitleDragRegion(QWidget):
    """Invisible overlay for window dragging; not placed in the main layout."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("titleDragRegion")
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

    def reposition(self, parent_width: int, height: int) -> None:
        self.setGeometry(0, 0, parent_width, height)
        self.raise_()


class SelectionToolbar(QWidget):
    """Bulk selection actions shown only while rows are checked."""

    HEIGHT = 44
    BACKGROUND = QColor(26, 27, 38)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("selectionToolbar")
        self.setFixedHeight(self.HEIGHT)
        if sys.platform == "darwin":
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
            self.setAutoFillBackground(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.select_all_button = QPushButton("Select All")
        self.select_all_button.setObjectName("selectAllButton")
        layout.addWidget(self.select_all_button)

        layout.addStretch()

        self.remove_confirm_label = QLabel("Click again to remove")
        self.remove_confirm_label.setObjectName("removeConfirmLabel")
        self.remove_confirm_label.setVisible(False)
        layout.addWidget(self.remove_confirm_label)

        self.remove_selected_button = QPushButton("Remove Selected")
        self.remove_selected_button.setObjectName("removeSelectedButton")
        layout.addWidget(self.remove_selected_button)

    def paintEvent(self, event) -> None:  # noqa: N802
        if sys.platform == "darwin":
            painter = QPainter(self)
            painter.fillRect(self.rect(), self.BACKGROUND)
            painter.end()
        super().paintEvent(event)

    def set_collapsed(self, collapsed: bool) -> None:
        if collapsed:
            self.hide()
            self.setFixedSize(0, 0)
            self.setParent(None)
            return

        self.setFixedHeight(self.HEIGHT)
        self.setMaximumWidth(16777215)
        self.show()


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
        self._window_drag_offset: QPoint | None = None

        self._build_menu()

        self.model = VideoTableModel(self)
        self.model.set_videos(database.list_videos())

        self._central = QWidget()
        self.setCentralWidget(self._central)
        if sys.platform == "darwin":
            self._central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self._central)
        if sys.platform == "darwin":
            # Glass windows already reserve title-bar space; keep a small gap only.
            layout.setContentsMargins(20, 8, 20, 16)
            self._drag_region = TitleDragRegion(self._central)
        else:
            layout.setContentsMargins(20, 20, 20, 16)
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

        self.selection_toolbar = SelectionToolbar(self._central)
        self.selection_toolbar.set_collapsed(True)
        self.selection_toolbar.select_all_button.clicked.connect(self._select_all_videos)
        self.selection_toolbar.remove_selected_button.clicked.connect(
            self._remove_selected_videos
        )
        self._selection_toolbar_in_layout = False

        self.table = HoverTableView()
        if sys.platform == "darwin":
            self.table.setHorizontalHeader(
                OpaqueHeaderView(Qt.Orientation.Horizontal, self.table)
            )
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(sys.platform != "darwin")
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

        if sys.platform == "darwin":
            self.table.viewport().setAttribute(
                Qt.WidgetAttribute.WA_OpaquePaintEvent, True
            )

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
        self._content_layout = layout
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

        if sys.platform == "darwin":
            self._central.installEventFilter(self)
            self._drag_region.installEventFilter(self)

        self._load_thumbnails_for_all()

    def _sync_macos_top_margin(self) -> None:
        if sys.platform != "darwin" or not self.isVisible():
            return

        from youtube_buddy.macos_glass import traffic_light_vertical_metrics

        metrics = traffic_light_vertical_metrics(self)
        layout = self._central.layout()
        if layout is None or metrics is None:
            return

        above_gap, button_bottom = metrics
        margins = layout.contentsMargins()
        desired_url_top = button_bottom + above_gap
        current_url_top = self.url_input.mapTo(self, QPoint(0, 0)).y()
        top_margin = margins.top() + (desired_url_top - current_url_top)
        top_margin = max(0, top_margin)

        if margins.top() != top_margin:
            layout.setContentsMargins(
                margins.left(),
                top_margin,
                margins.right(),
                margins.bottom(),
            )
            layout.activate()

        self._sync_title_drag_region()

    def _sync_title_drag_region(self) -> None:
        if sys.platform != "darwin":
            return

        url_top = self.url_input.mapTo(self._central, QPoint(0, 0)).y()
        height = max(0, url_top)
        self._drag_region.reposition(self._central.width(), height)

    def _content_band_top(self) -> int:
        return self.import_queue.mapTo(self._central, QPoint(0, self.import_queue.height())).y()

    def _toolbar_layout_shift(self) -> int:
        return SelectionToolbar.HEIGHT + self._content_layout.spacing()

    def _macos_erase_content_band(self, top: int, height: int) -> QWidget | None:
        if sys.platform != "darwin" or height <= 0:
            return None

        cover = QWidget(self._central)
        cover.setGeometry(0, top, self._central.width(), height)
        cover.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        cover.setAutoFillBackground(True)
        palette = cover.palette()
        palette.setColor(cover.backgroundRole(), TABLE_VIEWPORT_BG)
        cover.setPalette(palette)
        cover.show()
        cover.raise_()
        cover.repaint()
        QApplication.processEvents()
        return cover

    def _repaint_content_band(self) -> None:
        band_top = self._content_band_top()
        band_bottom = self.table.mapTo(self._central, QPoint(0, self.table.height())).y()
        height = max(0, band_bottom - band_top + 1)
        self._central.update(0, band_top, self._central.width(), height)
        self._central.repaint()
        self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        if sys.platform == "darwin":
            self._sync_macos_top_margin()
        self._position_drop_overlay()

    def _top_chrome_bottom(self) -> int:
        return self.url_input.mapTo(self._central, QPoint(0, self.url_input.height())).y()

    def _blocks_window_drag(self, widget: QWidget | None) -> bool:
        while widget is not None:
            if widget in (self.url_input, self.add_button):
                return True
            if widget in (self.table, self.import_queue, self.selection_toolbar):
                return True
            if isinstance(widget, HoverTableView):
                return True
            widget = widget.parentWidget()
        return False

    def _can_drag_window_at(self, global_pos: QPoint) -> bool:
        if self._central.mapFromGlobal(global_pos).y() > self._top_chrome_bottom():
            return False
        return not self._blocks_window_drag(QApplication.widgetAt(global_pos))

    def _start_window_drag(self, global_pos: QPoint) -> None:
        self._window_drag_offset = global_pos - self.frameGeometry().topLeft()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.grabMouse()

    def _finish_window_drag(self) -> None:
        self._window_drag_offset = None
        self.releaseMouse()
        self.unsetCursor()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._window_drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._window_drag_offset)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._window_drag_offset is not None:
            self._finish_window_drag()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()
        if sys.platform == "darwin":
            menu_bar.setNativeMenuBar(True)

        self._file_menu = menu_bar.addMenu("&File")

        open_action = self._file_menu.addAction("&Open Database…")
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_database)

        new_action = self._file_menu.addAction("&New Database…")
        new_action.triggered.connect(self._new_database)

        self._recent_separator = self._file_menu.addSeparator()
        self._recent_actions: list = []
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self) -> None:
        for action in self._recent_actions:
            self._file_menu.removeAction(action)
            action.deleteLater()
        self._recent_actions.clear()

        recent_paths = get_recent_database_paths()
        current_path = self.database.path.resolve()
        visible_paths = [
            path
            for path in recent_paths
            if path.exists() and path.resolve() != current_path
        ]

        self._recent_separator.setVisible(bool(visible_paths))
        shortcut_prefix = "Meta" if sys.platform == "darwin" else "Ctrl"
        for index, path in enumerate(visible_paths, start=1):
            action = self._file_menu.addAction(path.name)
            action.setToolTip(str(path))
            if index <= 9:
                action.setShortcut(QKeySequence(f"{shortcut_prefix}+{index}"))
            action.triggered.connect(
                lambda _checked=False, selected_path=path: self._open_database_at(
                    selected_path
                )
            )
            self._recent_actions.append(action)

    def _open_database(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Playlist Database",
            str(self.database.path.parent),
            DATABASE_OPEN_FILTER,
        )
        if path:
            self._open_database_at(Path(path))

    def _new_database(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Create Playlist Database",
            str(default_database_path()),
            DATABASE_SAVE_FILTER,
        )
        if not path:
            return

        db_path = ensure_database_suffix(Path(path))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._open_database_at(db_path)

    def _open_database_at(self, path: Path) -> None:
        resolved = migrate_legacy_database(path.resolve())
        if resolved == self.database.path.resolve():
            return

        if not resolved.exists():
            remove_recent_database(resolved)
            self._rebuild_recent_menu()
            QMessageBox.warning(
                self,
                "Database Not Found",
                f"The playlist database could not be found:\n{resolved}",
            )
            return

        if self._pending_urls and not self._confirm_cancel_imports():
            return

        self._cancel_pending_imports()
        self._thumbnail_loader.clear()
        self.database.close()
        self.database = Database(resolved)
        remember_database(resolved)

        self.model.set_videos(self.database.list_videos())
        self._cancel_remove_confirmation()
        self._update_selection_toolbar()
        self._load_thumbnails_for_all()
        self._rebuild_recent_menu()
        self.table.viewport().repaint()
        self.table.horizontalHeader().viewport().repaint()
        self._set_status(f"{len(self.model.videos())} videos in playlist")

    def _confirm_cancel_imports(self) -> bool:
        count = len(self._pending_urls)
        noun = "import" if count == 1 else "imports"
        answer = QMessageBox.question(
            self,
            "Switch Database",
            f"{count} {noun} still in progress.\n\n"
            "Switch databases anyway? Pending imports will be cancelled.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _cancel_pending_imports(self) -> None:
        for worker in list(self._metadata_workers):
            worker.finished_with_result.disconnect()
            worker.failed.disconnect()
            worker.finished.disconnect()
            if worker.isRunning():
                worker.wait(3000)
            worker.deleteLater()
        self._metadata_workers.clear()
        self._pending_urls.clear()
        self.import_queue.clear()

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
        if sys.platform == "darwin" and obj in (self._central, self._drag_region):
            if event.type() == QEvent.Type.MouseButtonPress and isinstance(
                event, QMouseEvent
            ):
                if (
                    event.button() == Qt.MouseButton.LeftButton
                    and self._window_drag_offset is None
                    and self._can_drag_window_at(event.globalPosition().toPoint())
                ):
                    self._start_window_drag(event.globalPosition().toPoint())
                    return True
            if event.type() == QEvent.Type.MouseMove and isinstance(event, QMouseEvent):
                if self._window_drag_offset is not None:
                    return False
                if obj is self._drag_region:
                    self._drag_region.setCursor(Qt.CursorShape.OpenHandCursor)
                elif obj is self._central:
                    if self._can_drag_window_at(event.globalPosition().toPoint()):
                        self._central.setCursor(Qt.CursorShape.OpenHandCursor)
                    else:
                        self._central.unsetCursor()

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
        if has_selection and not self._selection_toolbar_in_layout:
            stale_top = self.table.mapTo(self._central, QPoint(0, 0)).y()
            shift = self._toolbar_layout_shift()
            erase_height = (
                shift
                + self.table.horizontalHeader().height()
                + self.table.verticalHeader().defaultSectionSize()
                + 8
            )

            self.table.setUpdatesEnabled(False)
            self.selection_toolbar.set_collapsed(False)
            table_index = self._content_layout.indexOf(self.table)
            self._content_layout.insertWidget(table_index, self.selection_toolbar)
            self._selection_toolbar_in_layout = True
            self._content_layout.activate()
            self._central.updateGeometry()
            QApplication.processEvents()

            if sys.platform == "darwin":
                cover = self._macos_erase_content_band(stale_top, erase_height)
                QApplication.processEvents()
            else:
                cover = None

            self.table.setUpdatesEnabled(True)
            self.table.scrollTo(self.model.index(0, 0))
            self.table.viewport().repaint()
            self.selection_toolbar.raise_()
            if cover is not None:
                QTimer.singleShot(0, cover.deleteLater)
        elif not has_selection and self._selection_toolbar_in_layout:
            stale_top = self.table.mapTo(self._central, QPoint(0, 0)).y()
            shift = self._toolbar_layout_shift()
            erase_height = (
                shift
                + self.table.horizontalHeader().height()
                + self.table.verticalHeader().defaultSectionSize()
                + 8
            )

            self.table.setUpdatesEnabled(False)
            self._content_layout.removeWidget(self.selection_toolbar)
            self.selection_toolbar.set_collapsed(True)
            self._selection_toolbar_in_layout = False
            self._content_layout.activate()
            self._central.updateGeometry()
            QApplication.processEvents()

            if sys.platform == "darwin":
                cover = self._macos_erase_content_band(
                    max(0, stale_top - shift),
                    erase_height,
                )
                QApplication.processEvents()
            else:
                cover = None

            self.table.setUpdatesEnabled(True)
            self.table.viewport().repaint()
            if cover is not None:
                QTimer.singleShot(0, cover.deleteLater)

        if sys.platform == "darwin":
            self._repaint_macos_chrome()
            QTimer.singleShot(0, self._repaint_macos_chrome)
            QTimer.singleShot(50, self._repaint_macos_chrome)

    def _repaint_macos_chrome(self) -> None:
        self.update()
        self._central.update()
        self._central.repaint()
        if self.selection_toolbar.isVisible():
            self.selection_toolbar.update()
            self.selection_toolbar.repaint()
        self.table.update()
        self.table.repaint()
        header = self.table.horizontalHeader()
        header.update()
        header.repaint()
        header.viewport().repaint()
        self.table.viewport().repaint()

    def _set_remove_confirmation_pending(self, pending: bool) -> None:
        self._remove_confirm_pending = pending
        self.selection_toolbar.remove_confirm_label.setVisible(pending)
        remove_button = self.selection_toolbar.remove_selected_button
        remove_button.setProperty("armed", pending)
        remove_button.style().unpolish(remove_button)
        remove_button.style().polish(remove_button)

    def _cancel_remove_confirmation(self) -> None:
        if self._remove_confirm_pending:
            self._set_remove_confirmation_pending(False)

    def _select_all_videos(self) -> None:
        if (
            self.model.videos()
            and self.model.checked_count() == len(self.model.videos())
        ):
            self.model.clear_selection()
        else:
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
