"""Application theme and modern stylesheet for the Report SQL Agent desktop app."""

from __future__ import annotations

# Color Palette Constants
COLOR_BG_MAIN = "#18181f"
COLOR_BG_SURFACE = "#22222b"
COLOR_BG_CARD = "#2a2a36"
COLOR_BG_INPUT = "#323242"
COLOR_BORDER = "#3e3e52"
COLOR_BORDER_FOCUS = "#3b82f6"

COLOR_TEXT_PRIMARY = "#f9fafb"
COLOR_TEXT_SECONDARY = "#d1d5db"
COLOR_TEXT_MUTED = "#9ca3af"

COLOR_ACCENT = "#3b82f6"
COLOR_ACCENT_HOVER = "#2563eb"
COLOR_ACCENT_PRESSED = "#1d4ed8"

COLOR_SUCCESS = "#10b981"
COLOR_SUCCESS_HOVER = "#059669"
COLOR_DANGER = "#ef4444"
COLOR_DANGER_HOVER = "#dc2626"
COLOR_WARNING = "#f59e0b"

# Global Stylesheet
APP_STYLESHEET = f"""
/* Global Reset and Typography */
QWidget {{
    background-color: {COLOR_BG_MAIN};
    color: {COLOR_TEXT_PRIMARY};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    selection-background-color: {COLOR_ACCENT};
    selection-color: #ffffff;
}}

/* Main Window and Containers */
QMainWindow {{
    background-color: {COLOR_BG_MAIN};
}}

QSplitter::handle {{
    background-color: {COLOR_BORDER};
    width: 2px;
    height: 2px;
}}
QSplitter::handle:hover {{
    background-color: {COLOR_ACCENT};
}}

QFrame[frameShape="4"], QFrame[frameShape="5"] {{ /* HLine and VLine */
    color: {COLOR_BORDER};
    background-color: {COLOR_BORDER};
}}

/* Header Bar */
QFrame#header_bar {{
    background-color: {COLOR_BG_SURFACE};
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 8px 16px;
}}

QLabel#app_title {{
    font-size: 16px;
    font-weight: 700;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel#app_subtitle {{
    font-size: 12px;
    color: {COLOR_TEXT_MUTED};
}}

/* Badges and Indicators */
QLabel#status_pill_online {{
    background-color: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
}}

QLabel#status_pill_offline {{
    background-color: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
}}

/* Push Buttons */
QPushButton {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {COLOR_BG_INPUT};
    border-color: {COLOR_TEXT_MUTED};
}}
QPushButton:pressed {{
    background-color: {COLOR_BG_SURFACE};
}}
QPushButton:disabled {{
    background-color: {COLOR_BG_SURFACE};
    color: {COLOR_TEXT_MUTED};
    border-color: {COLOR_BORDER};
}}

/* Primary Action Buttons */
QPushButton#primary_button, QPushButton[primary="true"] {{
    background-color: {COLOR_ACCENT};
    color: #ffffff;
    border: none;
    font-weight: 600;
}}
QPushButton#primary_button:hover, QPushButton[primary="true"]:hover {{
    background-color: {COLOR_ACCENT_HOVER};
}}
QPushButton#primary_button:pressed, QPushButton[primary="true"]:pressed {{
    background-color: {COLOR_ACCENT_PRESSED};
}}
QPushButton#primary_button:disabled, QPushButton[primary="true"]:disabled {{
    background-color: #3b82f640;
    color: #93c5fd80;
}}

/* Success Buttons */
QPushButton#success_button {{
    background-color: {COLOR_SUCCESS};
    color: #ffffff;
    border: none;
    font-weight: 600;
}}
QPushButton#success_button:hover {{
    background-color: {COLOR_SUCCESS_HOVER};
}}

/* Danger Buttons */
QPushButton#danger_button {{
    background-color: rgba(239, 68, 68, 0.2);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.4);
    font-weight: 600;
}}
QPushButton#danger_button:hover {{
    background-color: {COLOR_DANGER};
    color: #ffffff;
}}

/* Input Fields and Editors */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {COLOR_BG_INPUT};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {COLOR_BORDER_FOCUS};
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {COLOR_BG_SURFACE};
    color: {COLOR_TEXT_MUTED};
}}

/* Scroll Bars */
QScrollBar:vertical {{
    background-color: {COLOR_BG_MAIN};
    width: 8px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background-color: {COLOR_BORDER};
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {COLOR_TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {COLOR_BG_MAIN};
    height: 8px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLOR_BORDER};
    min-width: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {COLOR_TEXT_MUTED};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Tables and Tree Views */
QTableView, QTableWidget, QTreeView, QListView {{
    background-color: {COLOR_BG_SURFACE};
    alternate-background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    gridline-color: {COLOR_BORDER};
    font-size: 12px;
}}
QTableView::item:selected, QTableWidget::item:selected {{
    background-color: rgba(59, 130, 246, 0.3);
    color: #ffffff;
}}
QHeaderView::section {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_SECONDARY};
    padding: 6px 10px;
    border: none;
    border-right: 1px solid {COLOR_BORDER};
    border-bottom: 1px solid {COLOR_BORDER};
    font-weight: 600;
    font-size: 12px;
}}

/* Cards and Surfaces */
QFrame#card_frame {{
    background-color: {COLOR_BG_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}

QFrame#user_message_bubble {{
    background-color: #1e3a8a;
    border: 1px solid #2563eb;
    border-radius: 10px;
    padding: 10px;
}}

QFrame#assistant_message_bubble {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    padding: 10px;
}}

QFrame#system_event_bubble {{
    background-color: rgba(55, 65, 81, 0.4);
    border: 1px dashed {COLOR_BORDER};
    border-radius: 8px;
    padding: 6px;
}}

/* Code / SQL Box */
QPlainTextEdit#sql_editor {{
    font-family: "JetBrains Mono", "SF Mono", Consolas, "Courier New", monospace;
    font-size: 12px;
    background-color: #111116;
    color: #67e8f9;
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    line-height: 1.4;
}}

/* Tab Widget */
QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    background-color: {COLOR_BG_SURFACE};
    border-radius: 6px;
}}
QTabBar::tab {{
    background-color: {COLOR_BG_MAIN};
    color: {COLOR_TEXT_MUTED};
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid transparent;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background-color: {COLOR_BG_SURFACE};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-bottom: none;
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_SECONDARY};
}}

/* Dialogs */
QDialog {{
    background-color: {COLOR_BG_MAIN};
}}

/* Group Box */
QGroupBox {{
    font-weight: 600;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {COLOR_ACCENT};
}}
"""

