"""Delegate for checkbox selection column."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QStyle,
    QStyleOptionButton,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from youtube_buddy.hover_table import HOVER_COLOR, HoverTableView


class CheckboxDelegate(QStyledItemDelegate):
    toggled = pyqtSignal(int)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index,
    ) -> None:
        table = option.widget
        if isinstance(table, HoverTableView) and index.row() == table.hover_row:
            painter.fillRect(option.rect, HOVER_COLOR)

        check_state = index.data(Qt.ItemDataRole.CheckStateRole)
        if check_state is None:
            check_state = Qt.CheckState.Unchecked

        style = option.widget.style() if option.widget else QApplication.style()
        checkbox_rect = style.subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator,
            option,
            option.widget,
        )
        checkbox_rect.moveCenter(option.rect.center())

        check_option = QStyleOptionButton()
        check_option.rect = checkbox_rect
        check_option.state = QStyle.StateFlag.State_Enabled
        if check_state == Qt.CheckState.Checked:
            check_option.state |= QStyle.StateFlag.State_On
        else:
            check_option.state |= QStyle.StateFlag.State_Off

        style.drawControl(QStyle.ControlElement.CE_CheckBox, check_option, painter)

    def editorEvent(
        self,
        event: QEvent,
        model,
        option: QStyleOptionViewItem,
        index,
    ) -> bool:
        if not index.isValid() or event.type() != QEvent.Type.MouseButtonRelease:
            return False

        mouse_event = event
        if not isinstance(mouse_event, QMouseEvent):
            return False
        if mouse_event.button() != Qt.MouseButton.LeftButton:
            return False

        current = index.data(Qt.ItemDataRole.CheckStateRole) or Qt.CheckState.Unchecked
        new_state = (
            Qt.CheckState.Unchecked
            if current == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        if model.setData(index, new_state, Qt.ItemDataRole.CheckStateRole):
            self.toggled.emit(index.row())
            return True
        return False
