"""Table model for playlist videos with drag-and-drop reordering."""

from __future__ import annotations

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, QMimeData, pyqtSignal
from PyQt6.QtGui import QPixmap

from youtube_buddy.database import Video
from youtube_buddy.youtube import format_duration

MIME_TYPE = "application/x-youtube-buddy-row"

COL_SELECT = 0
COL_THUMBNAIL = 1
COL_LENGTH = 2
COL_TITLE = 3
COL_ACTIONS = 4


class VideoTableModel(QAbstractTableModel):
    HEADERS = ["", "Thumbnail", "Length", "Title", ""]
    order_changed = pyqtSignal()
    selection_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._videos: list[Video] = []
        self._thumbnails: dict[int, QPixmap] = {}
        self._checked_ids: set[int] = set()

    def set_videos(self, videos: list[Video]) -> None:
        self.beginResetModel()
        self._videos = list(videos)
        self._checked_ids.clear()
        self._thumbnails = {
            video.id: pixmap
            for video in self._videos
            if (pixmap := self._thumbnails.get(video.id)) is not None
        }
        self.endResetModel()
        self.selection_changed.emit()

    def videos(self) -> list[Video]:
        return list(self._videos)

    def video_at(self, row: int) -> Video | None:
        if 0 <= row < len(self._videos):
            return self._videos[row]
        return None

    def row_for_id(self, video_id: int) -> int | None:
        for index, video in enumerate(self._videos):
            if video.id == video_id:
                return index
        return None

    def checked_video_ids(self) -> list[int]:
        return [video.id for video in self._videos if video.id in self._checked_ids]

    def checked_count(self) -> int:
        return len(self._checked_ids)

    def select_all(self) -> None:
        if not self._videos:
            return
        self._checked_ids = {video.id for video in self._videos}
        self._emit_select_column_changed()
        self.selection_changed.emit()

    def clear_selection(self) -> None:
        if not self._checked_ids:
            return
        self._checked_ids.clear()
        self._emit_select_column_changed()
        self.selection_changed.emit()

    def set_checked(self, video_id: int, checked: bool) -> None:
        if checked:
            if video_id in self._checked_ids:
                return
            self._checked_ids.add(video_id)
        else:
            if video_id not in self._checked_ids:
                return
            self._checked_ids.discard(video_id)

        row = self.row_for_id(video_id)
        if row is not None:
            index = self.index(row, COL_SELECT)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
        self.selection_changed.emit()

    def set_thumbnail(self, video_id: int, pixmap: QPixmap) -> None:
        row = self.row_for_id(video_id)
        if row is None:
            return
        self._thumbnails[video_id] = pixmap
        index = self.index(row, COL_THUMBNAIL)
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DecorationRole])

    def append_video(self, video: Video) -> None:
        row = len(self._videos)
        self.beginInsertRows(QModelIndex(), row, row)
        self._videos.append(video)
        self.endInsertRows()

    def update_video(self, video: Video) -> None:
        row = self.row_for_id(video.id)
        if row is None:
            return
        self._videos[row] = video
        left = self.index(row, 0)
        right = self.index(row, self.columnCount() - 1)
        self.dataChanged.emit(left, right)

    def remove_video(self, video_id: int) -> Video | None:
        row = self.row_for_id(video_id)
        if row is None:
            return None

        self.beginRemoveRows(QModelIndex(), row, row)
        video = self._videos.pop(row)
        self._thumbnails.pop(video_id, None)
        self._checked_ids.discard(video_id)
        self.endRemoveRows()
        self.order_changed.emit()
        self.selection_changed.emit()
        return video

    def remove_videos(self, video_ids: list[int]) -> list[Video]:
        ids = set(video_ids)
        rows = sorted(
            (index for index, video in enumerate(self._videos) if video.id in ids),
            reverse=True,
        )
        removed: list[Video] = []
        for row in rows:
            self.beginRemoveRows(QModelIndex(), row, row)
            video = self._videos.pop(row)
            self._thumbnails.pop(video.id, None)
            self._checked_ids.discard(video.id)
            removed.append(video)
            self.endRemoveRows()

        if removed:
            self.order_changed.emit()
            self.selection_changed.emit()
        return removed

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._videos)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self.HEADERS)

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(self.HEADERS)
        ):
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        video = self._videos[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.UserRole:
            return video

        if column == COL_SELECT and role == Qt.ItemDataRole.CheckStateRole:
            return (
                Qt.CheckState.Checked
                if video.id in self._checked_ids
                else Qt.CheckState.Unchecked
            )

        if column == COL_THUMBNAIL:
            if role == Qt.ItemDataRole.DecorationRole:
                return self._thumbnails.get(video.id)
            if role == Qt.ItemDataRole.DisplayRole:
                return None
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return int(Qt.AlignmentFlag.AlignCenter)

        if column == COL_LENGTH and role == Qt.ItemDataRole.DisplayRole:
            return format_duration(video.duration_seconds)

        if column == COL_TITLE and role == Qt.ItemDataRole.DisplayRole:
            return video.title or "Loading…"

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column == COL_LENGTH:
                return int(Qt.AlignmentFlag.AlignCenter)
            if column == COL_SELECT:
                return int(Qt.AlignmentFlag.AlignCenter)
            if column == COL_TITLE:
                return int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            return int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:  # noqa: N802
        if not index.isValid() or index.column() != COL_SELECT:
            return False
        if role != Qt.ItemDataRole.CheckStateRole:
            return False

        video = self._videos[index.row()]
        checked = value == Qt.CheckState.Checked
        self.set_checked(video.id, checked)
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:  # noqa: N802
        if not index.isValid():
            return Qt.ItemFlag.ItemIsDropEnabled

        if index.column() == COL_SELECT:
            return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )

        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
        )

    def supportedDropActions(self) -> Qt.DropAction:  # noqa: N802
        return Qt.DropAction.MoveAction

    def supportedDragActions(self) -> Qt.DropAction:  # noqa: N802
        return Qt.DropAction.MoveAction

    def mimeTypes(self) -> list[str]:  # noqa: N802
        return [MIME_TYPE]

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:  # noqa: N802
        mime = QMimeData()
        rows = sorted({index.row() for index in indexes if index.isValid()})
        if rows:
            mime.setData(MIME_TYPE, str(rows[0]).encode())
        return mime

    def dropMimeData(  # noqa: N802
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if action != Qt.DropAction.MoveAction or not data.hasFormat(MIME_TYPE):
            return False

        source_row = int(bytes(data.data(MIME_TYPE)).decode())
        if source_row < 0 or source_row >= len(self._videos):
            return False

        if row == -1:
            if parent.isValid():
                row = parent.row() + 1
            else:
                row = len(self._videos)

        if source_row < row:
            row -= 1

        if source_row == row:
            return False

        self.beginMoveRows(QModelIndex(), source_row, source_row, QModelIndex(), row)
        video = self._videos.pop(source_row)
        self._videos.insert(row, video)
        self.endMoveRows()
        self.order_changed.emit()
        return True

    def _emit_select_column_changed(self) -> None:
        if not self._videos:
            return
        top = self.index(0, COL_SELECT)
        bottom = self.index(len(self._videos) - 1, COL_SELECT)
        self.dataChanged.emit(top, bottom, [Qt.ItemDataRole.CheckStateRole])
