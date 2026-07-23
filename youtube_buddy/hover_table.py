"""Table view with full-row hover tracking."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QColor, QMouseEvent, QPainter
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QTableView


HOVER_COLOR = (
    QColor(42, 49, 80, 140)
    if sys.platform == "darwin"
    else QColor("#2a3150")
)


class HoverTableView(QTableView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hover_row = -1
        self.viewport().setMouseTracking(True)
        self.setMouseTracking(True)

    @property
    def hover_row(self) -> int:
        return self._hover_row

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._set_hover_row(self.indexAt(event.pos()).row())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._set_hover_row(-1)
        super().leaveEvent(event)

    def _set_hover_row(self, row: int) -> None:
        if not self.model():
            return

        row = row if row >= 0 else -1
        if row == self._hover_row:
            return

        previous = self._hover_row
        self._hover_row = row

        for affected in {previous, row}:
            if affected >= 0:
                self._repaint_row(affected)

    def _repaint_row(self, row: int) -> None:
        model = self.model()
        if model is None:
            return

        top_left = model.index(row, 0)
        bottom_right = model.index(row, model.columnCount() - 1)
        self.viewport().update(self.visualRect(top_left).united(self.visualRect(bottom_right)))


class RowHoverDelegate(QStyledItemDelegate):
    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        table = option.widget
        if isinstance(table, HoverTableView) and index.row() == table.hover_row:
            painter.save()
            painter.fillRect(option.rect, HOVER_COLOR)
            painter.restore()
        super().paint(painter, option, index)
