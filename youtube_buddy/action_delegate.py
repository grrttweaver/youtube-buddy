"""Delegate for per-row action buttons."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QPainter
from PyQt6.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from youtube_buddy.hover_table import HOVER_COLOR, HoverTableView, paint_item_background


class ActionButtonDelegate(QStyledItemDelegate):
    delete_clicked = pyqtSignal(int)

    BUTTON_SIZE = 32

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index,
    ) -> None:
        if not index.isValid():
            return

        paint_item_background(painter, option, index)
        table = option.widget
        if isinstance(table, HoverTableView) and index.row() == table.hover_row:
            painter.fillRect(option.rect, HOVER_COLOR)

        button_rect = self._button_rect(option.rect)
        icon = option.widget.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon) if option.widget else QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        icon.paint(painter, button_rect, Qt.AlignmentFlag.AlignCenter)

    def editorEvent(
        self,
        event: QEvent,
        model,
        option: QStyleOptionViewItem,
        index,
    ) -> bool:
        if not index.isValid():
            return False

        if event.type() == QEvent.Type.MouseButtonRelease:
            mouse_event = event
            if not isinstance(mouse_event, QMouseEvent):
                return False
            if (
                mouse_event.button() == Qt.MouseButton.LeftButton
                and self._button_rect(option.rect).contains(mouse_event.pos())
            ):
                self.delete_clicked.emit(index.row())
                return True

        return False

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:  # noqa: N802
        return QSize(self.BUTTON_SIZE + 16, option.rect.height())

    @classmethod
    def _button_rect(cls, cell_rect: QRect) -> QRect:
        size = cls.BUTTON_SIZE
        x = cell_rect.x() + (cell_rect.width() - size) // 2
        y = cell_rect.y() + (cell_rect.height() - size) // 2
        return QRect(x, y, size, size)
