"""Delegate for title column with optional playlist and shorts badges."""

from __future__ import annotations

from PyQt6.QtCore import QModelIndex, QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPalette
from PyQt6.QtWidgets import QStyle, QStyleOptionViewItem

from youtube_buddy.database import Video
from youtube_buddy.hover_table import HOVER_COLOR, HoverTableView, RowHoverDelegate

BADGE_PADDING_H = 6
BADGE_PADDING_V = 2
BADGE_RADIUS = 5
BADGE_GAP = 8
TITLE_MARGIN_H = 8
TITLE_MARGIN_V = 6

PLST_BADGE_BG = QColor("#7aa2f7")
PLST_BADGE_FG = QColor("#1a1b26")
SHRT_BADGE_BG = QColor("#ff9e64")
SHRT_BADGE_FG = QColor("#1a1b26")
IGRL_BADGE_BG = QColor("#e1306c")
IGRL_BADGE_FG = QColor("#ffffff")
FBRL_BADGE_BG = QColor("#1877f2")
FBRL_BADGE_FG = QColor("#ffffff")

TEXT_FLAGS = (
    Qt.AlignmentFlag.AlignLeft
    | Qt.AlignmentFlag.AlignTop
    | Qt.TextFlag.TextWordWrap
)


class TitleDelegate(RowHoverDelegate):
    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        table = option.widget
        if isinstance(table, HoverTableView) and index.row() == table.hover_row:
            painter.fillRect(option.rect, HOVER_COLOR)

        video = index.data(Qt.ItemDataRole.UserRole)
        title = index.data(Qt.ItemDataRole.DisplayRole)
        if not isinstance(title, str):
            title = "Loading…"

        if isinstance(video, Video):
            if video.is_playlist:
                self._paint_badged_title(
                    painter, option, title, "PLST", PLST_BADGE_BG, PLST_BADGE_FG
                )
                return
            if video.is_short:
                self._paint_badged_title(
                    painter, option, title, "SHRT", SHRT_BADGE_BG, SHRT_BADGE_FG
                )
                return
            if video.platform == "instagram":
                self._paint_badged_title(
                    painter, option, title, "IGRL", IGRL_BADGE_BG, IGRL_BADGE_FG
                )
                return
            if video.platform == "facebook":
                self._paint_badged_title(
                    painter, option, title, "FBRL", FBRL_BADGE_BG, FBRL_BADGE_FG
                )
                return

        self._paint_wrapped_title(painter, option, title)

    def _text_color(self, option: QStyleOptionViewItem) -> QColor:
        if option.state & QStyle.StateFlag.State_Selected:
            return option.palette.color(QPalette.ColorRole.HighlightedText)
        return option.palette.color(QPalette.ColorRole.Text)

    def _paint_selection(self, painter: QPainter, option: QStyleOptionViewItem) -> None:
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

    def _paint_wrapped_title(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        title: str,
    ) -> None:
        painter.save()
        self._paint_selection(painter, option)
        painter.setFont(option.font)
        painter.setPen(self._text_color(option))

        text_rect = option.rect.adjusted(
            TITLE_MARGIN_H,
            TITLE_MARGIN_V,
            -TITLE_MARGIN_H,
            -TITLE_MARGIN_V,
        )
        painter.drawText(text_rect, int(TEXT_FLAGS), title)
        painter.restore()

    def _paint_badged_title(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        title: str,
        badge_text: str,
        badge_bg: QColor,
        badge_fg: QColor,
    ) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_selection(painter, option)

        font = option.font
        painter.setFont(font)
        metrics = painter.fontMetrics()

        badge_width = metrics.horizontalAdvance(badge_text) + BADGE_PADDING_H * 2
        badge_height = metrics.height() + BADGE_PADDING_V * 2
        badge_x = option.rect.x() + TITLE_MARGIN_H
        badge_y = option.rect.y() + TITLE_MARGIN_V
        badge_rect = QRect(badge_x, badge_y, badge_width, badge_height)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(badge_bg)
        painter.drawRoundedRect(badge_rect, BADGE_RADIUS, BADGE_RADIUS)

        painter.setPen(badge_fg)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        painter.setPen(self._text_color(option))

        title_rect = QRect(
            badge_rect.right() + BADGE_GAP,
            option.rect.y() + TITLE_MARGIN_V,
            option.rect.width() - (badge_rect.right() - option.rect.x()) - BADGE_GAP - TITLE_MARGIN_H,
            option.rect.height() - TITLE_MARGIN_V * 2,
        )
        painter.drawText(title_rect, int(TEXT_FLAGS), title)
        painter.restore()
