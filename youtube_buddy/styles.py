"""Application styling."""

from __future__ import annotations

import sys

APP_STYLESHEET = """
QWidget {
    background-color: #1a1b26;
    color: #c0caf5;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #1a1b26;
}

QLabel#setupTitle {
    font-size: 18px;
    font-weight: 600;
    color: #7aa2f7;
}

QLabel#setupSubtitle {
    color: #565f89;
}

QLabel#statusLabel {
    color: #f7768e;
    min-height: 18px;
}

QLineEdit {
    background-color: #24283b;
    border: 1px solid #414868;
    border-radius: 8px;
    padding: 10px 14px;
    color: #c0caf5;
    selection-background-color: #414868;
}

QLineEdit:focus {
    border-color: #7aa2f7;
}

QPushButton {
    background-color: #414868;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    color: #c0caf5;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #565f89;
}

QPushButton:pressed {
    background-color: #7aa2f7;
    color: #1a1b26;
}

QPushButton#addButton {
    background-color: #7aa2f7;
    color: #1a1b26;
    font-weight: 600;
}

QPushButton#addButton:hover {
    background-color: #89b4fa;
}

QPushButton#addButton:disabled {
    background-color: #414868;
    color: #565f89;
}

QPushButton#removeSelectedButton {
    background-color: #f7768e;
    color: #1a1b26;
    font-weight: 600;
}

QPushButton#removeSelectedButton:hover {
    background-color: #ff8497;
}

QPushButton#removeSelectedButton[armed="true"] {
    background-color: #ff8497;
    border: 2px solid #ffffff;
}

QPushButton#removeSelectedButton[armed="true"]:hover {
    background-color: #ff9aab;
}

QLabel#removeConfirmLabel {
    color: #f7768e;
    font-weight: 600;
}

QPushButton#selectAllButton {
    background-color: #414868;
    color: #c0caf5;
    padding: 8px 12px;
}

QWidget#importQueue {
    background-color: #24283b;
    border: 1px solid #414868;
    border-radius: 10px;
    padding: 10px 12px;
}

QLabel#importQueueSummary {
    color: #7aa2f7;
    font-weight: 600;
    padding-bottom: 2px;
}

QWidget#importQueueRow {
    background-color: #1f2335;
    border-radius: 8px;
}

QLabel#importQueueStatus {
    color: #7aa2f7;
    font-weight: 700;
}

QLabel#importQueueText {
    color: #a9b1d6;
}

QWidget#importQueueRow[failed="true"] QLabel#importQueueStatus {
    color: #f7768e;
}

QWidget#importQueueRow[failed="true"] QLabel#importQueueText {
    color: #f7768e;
}

QTableView {
    background-color: #24283b;
    alternate-background-color: #1f2335;
    border: 1px solid #414868;
    border-radius: 10px;
    gridline-color: #32364a;
    selection-background-color: #414868;
    selection-color: #c0caf5;
}

QTableView::item {
    padding: 6px 8px;
    border: none;
}

QHeaderView::section {
    background-color: #1f2335;
    color: #7aa2f7;
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid #414868;
    font-weight: 600;
}

QScrollBar:vertical {
    background: #1a1b26;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #414868;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #565f89;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QMenuBar {
    background-color: #1a1b26;
    color: #c0caf5;
    border-bottom: 1px solid #32364a;
    padding: 4px 8px;
    spacing: 4px;
}

QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
    border-radius: 6px;
}

QMenuBar::item:selected {
    background-color: #414868;
}

QMenu {
    background-color: #24283b;
    color: #c0caf5;
    border: 1px solid #414868;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 8px 28px 8px 16px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #414868;
}

QMenu::separator {
    height: 1px;
    background: #414868;
    margin: 6px 8px;
}

QDialog {
    background-color: #1a1b26;
}

QRadioButton {
    spacing: 8px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
}

QStatusBar {
    background-color: #1f2335;
    color: #565f89;
    border-top: 1px solid #32364a;
}

QWidget#dropOverlay {
    background-color: rgba(26, 27, 38, 0.2);
    border-radius: 10px;
}

QLabel#dropOverlayLabel {
    background-color: rgba(36, 40, 59, 0.92);
    color: #c0caf5;
    border: 2px dashed #7aa2f7;
    border-radius: 12px;
    padding: 20px 32px;
    font-size: 18px;
    font-weight: 600;
}
"""

MACOS_STYLESHEET = """
QWidget {
    background-color: transparent;
    color: #c0caf5;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: transparent;
}

QWidget#selectionToolbar {
    background-color: #1a1b26;
}

QLabel#setupTitle {
    font-size: 18px;
    font-weight: 600;
    color: #7aa2f7;
}

QLabel#setupSubtitle {
    color: #565f89;
}

QLabel#statusLabel {
    color: #f7768e;
    min-height: 18px;
}

QLineEdit {
    background-color: rgba(36, 40, 59, 0.72);
    border: 1px solid rgba(65, 72, 104, 0.75);
    border-radius: 8px;
    padding: 10px 14px;
    color: #c0caf5;
    selection-background-color: rgba(65, 72, 104, 0.9);
}

QLineEdit:focus {
    border-color: #7aa2f7;
}

QPushButton {
    background-color: rgba(65, 72, 104, 0.78);
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    color: #c0caf5;
    font-weight: 500;
}

QPushButton:hover {
    background-color: rgba(86, 95, 137, 0.85);
}

QPushButton:pressed {
    background-color: #7aa2f7;
    color: #1a1b26;
}

QPushButton#addButton {
    background-color: rgba(122, 162, 247, 0.92);
    color: #1a1b26;
    font-weight: 600;
}

QPushButton#addButton:hover {
    background-color: rgba(137, 180, 250, 0.95);
}

QPushButton#addButton:disabled {
    background-color: rgba(65, 72, 104, 0.55);
    color: #565f89;
}

QPushButton#removeSelectedButton {
    background-color: rgba(247, 118, 142, 0.92);
    color: #1a1b26;
    font-weight: 600;
}

QPushButton#removeSelectedButton:hover {
    background-color: rgba(255, 132, 151, 0.95);
}

QPushButton#removeSelectedButton[armed="true"] {
    background-color: rgba(255, 132, 151, 0.95);
    border: 2px solid rgba(255, 255, 255, 0.9);
}

QPushButton#removeSelectedButton[armed="true"]:hover {
    background-color: rgba(255, 154, 171, 0.98);
}

QLabel#removeConfirmLabel {
    color: #f7768e;
    font-weight: 600;
}

QPushButton#selectAllButton {
    background-color: rgba(65, 72, 104, 0.78);
    color: #c0caf5;
    padding: 8px 12px;
}

QWidget#importQueue {
    background-color: rgba(36, 40, 59, 0.62);
    border: 1px solid rgba(65, 72, 104, 0.55);
    border-radius: 10px;
    padding: 10px 12px;
}

QLabel#importQueueSummary {
    color: #7aa2f7;
    font-weight: 600;
    padding-bottom: 2px;
}

QWidget#importQueueRow {
    background-color: rgba(31, 35, 53, 0.72);
    border-radius: 8px;
}

QLabel#importQueueStatus {
    color: #7aa2f7;
    font-weight: 700;
}

QLabel#importQueueText {
    color: #a9b1d6;
}

QWidget#importQueueRow[failed="true"] QLabel#importQueueStatus {
    color: #f7768e;
}

QWidget#importQueueRow[failed="true"] QLabel#importQueueText {
    color: #f7768e;
}

QTableView {
    background-color: #24283b;
    alternate-background-color: #1f2335;
    border: 1px solid rgba(65, 72, 104, 0.55);
    border-radius: 10px;
    gridline-color: rgba(50, 54, 74, 0.5);
    selection-background-color: rgba(65, 72, 104, 0.75);
    selection-color: #c0caf5;
}

QTableView::item {
    padding: 6px 8px;
    border: none;
}

QHeaderView {
    background-color: #1f2335;
}

QHeaderView::section {
    background-color: #1f2335;
    color: #7aa2f7;
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid rgba(65, 72, 104, 0.55);
    font-weight: 600;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: rgba(65, 72, 104, 0.75);
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(86, 95, 137, 0.85);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QDialog {
    background-color: #1a1b26;
}

QRadioButton {
    spacing: 8px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
}

QStatusBar {
    background-color: rgba(31, 35, 53, 0.45);
    color: #565f89;
    border-top: 1px solid rgba(50, 54, 74, 0.45);
}

QWidget#dropOverlay {
    background-color: rgba(26, 27, 38, 0.12);
    border-radius: 10px;
}

QLabel#dropOverlayLabel {
    background-color: rgba(36, 40, 59, 0.82);
    color: #c0caf5;
    border: 2px dashed #7aa2f7;
    border-radius: 12px;
    padding: 20px 32px;
    font-size: 18px;
    font-weight: 600;
}
"""


def get_stylesheet() -> str:
    if sys.platform == "darwin":
        return MACOS_STYLESHEET
    return APP_STYLESHEET
