"""Table view with full-row hover tracking."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QColor, QBrush, QMouseEvent, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QHeaderView,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QTableView,
)


HOVER_COLOR = (
    QColor(42, 49, 80)
    if sys.platform == "darwin"
    else QColor("#2a3150")
)

ROW_BG_EVEN = QColor(36, 40, 59)
ROW_BG_ODD = QColor(31, 35, 53)
ROW_BG_SELECTED = QColor(65, 72, 104)

_ITEM_BACKGROUND_DELEGATE = QStyledItemDelegate()


def paint_item_background(
    painter: QPainter,
    option: QStyleOptionViewItem,
    index: QModelIndex,
) -> None:
    if sys.platform == "darwin":
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            color = ROW_BG_SELECTED
        elif index.row() % 2 == 1:
            color = ROW_BG_ODD
        else:
            color = ROW_BG_EVEN
        painter.fillRect(option.rect, color)
        painter.restore()
        return

    item_option = QStyleOptionViewItem(option)
    _ITEM_BACKGROUND_DELEGATE.initStyleOption(item_option, index)
    widget = option.widget
    style = widget.style() if widget else QApplication.style()
    style.drawPrimitive(
        QStyle.PrimitiveElement.PE_PanelItemViewItem,
        item_option,
        painter,
        widget,
    )


TABLE_VIEWPORT_BG = QColor(36, 40, 59)
HEADER_BG = QColor(31, 35, 53)


class OpaqueHeaderView(QHeaderView):
    """Header that paints opaque section backgrounds on translucent macOS windows."""

    def __init__(self, orientation: Qt.Orientation, parent=None) -> None:
        super().__init__(orientation, parent)
        if sys.platform == "darwin":
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self.setAutoFillBackground(True)
            viewport = self.viewport()
            viewport.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
            viewport.setAttribute(Qt.WidgetAttribute.WA_StaticContents, False)

    def paintSection(  # noqa: N802
        self,
        painter: QPainter,
        rect,
        logicalIndex: int,
    ) -> None:
        if sys.platform == "darwin":
            painter.fillRect(rect, HEADER_BG)
        super().paintSection(painter, rect, logicalIndex)


class HoverTableView(QTableView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hover_row = -1
        self.viewport().setMouseTracking(True)
        self.setMouseTracking(True)
        if sys.platform == "darwin":
            viewport = self.viewport()
            viewport.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
            viewport.setAttribute(Qt.WidgetAttribute.WA_StaticContents, False)

    def scrollContentsBy(self, dx: int, dy: int) -> None:  # noqa: N802
        if sys.platform == "darwin" and dy:
            painter = QPainter(self.viewport())
            painter.fillRect(self.viewport().rect(), TABLE_VIEWPORT_BG)
            painter.end()
        super().scrollContentsBy(dx, dy)
        if sys.platform == "darwin" and dy:
            self.viewport().repaint()

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
        paint_item_background(painter, option, index)
        table = option.widget
        if isinstance(table, HoverTableView) and index.row() == table.hover_row:
            painter.save()
            painter.fillRect(option.rect, HOVER_COLOR)
            painter.restore()

        if sys.platform == "darwin":
            item_option = QStyleOptionViewItem(option)
            item_option.backgroundBrush = QBrush()
            painter.save()
            painter.setClipRect(option.rect)
            super().paint(painter, item_option, index)
            painter.restore()
            return

        super().paint(painter, option, index)
