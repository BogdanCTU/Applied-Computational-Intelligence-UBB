"""Unified Design System, Tokens, and Modern QSS Stylesheet for Report SQL Agent.

Establishes a cohesive dark-theme design language tailored for a professional
analytical desktop workspace. All typography, colors, borders, dimensions, and
interactive widget states are centralized here.
"""

from __future__ import annotations

# ===========================================================================
# 1. DESIGN TOKENS
# ===========================================================================


class ThemeColors:
    """Centralized semantic color palette for the application."""

    # Surfaces & Backgrounds
    BG_APP = "#0f1117"  # Deep dark base canvas
    BG_HEADER = "#151822"  # Top app header bar
    BG_PANEL = "#161922"  # Primary sidebar / lateral panel
    BG_SURFACE = "#1c202d"  # Card frames, widget containers
    BG_SURFACE_HOVER = "#232838"  # Hover state for interactive cards/items
    BG_SURFACE_ACTIVE = "#2b3245"  # Active/selected surface
    BG_INPUT = "#13161f"  # Text edits, spinboxes, inputs
    BG_CANVAS = "#12141c"  # Workspace canvas surrounding PDF pages

    # Borders & Dividers
    BORDER_SUBTLE = "#232838"  # Subtle separators and splitters
    BORDER_DEFAULT = "#2e3549"  # Standard widget container borders
    BORDER_STRONG = "#414b66"  # Hovered or prominent boundaries
    BORDER_FOCUS = "#3b82f6"  # Keyboard focus rings

    # Typography / Text Colors (WCAG AA Compliant contrast against dark surfaces)
    TEXT_PRIMARY = "#f8fafc"  # High-emphasis text (headers, primary labels)
    TEXT_SECONDARY = "#cbd5e1"  # Medium-emphasis text (body text, table items)
    TEXT_MUTED = "#94a3b8"  # Low-emphasis text (timestamps, captions, hints)
    TEXT_DISABLED = "#64748b"  # Disabled text

    # Primary Action (Royal/Indigo Blue)
    ACCENT_PRIMARY = "#3b82f6"
    ACCENT_HOVER = "#2563eb"
    ACCENT_PRESSED = "#1d4ed8"
    ACCENT_SURFACE = "rgba(59, 130, 246, 0.15)"
    ACCENT_BORDER = "rgba(59, 130, 246, 0.35)"

    # Success (Emerald)
    SUCCESS = "#10b981"
    SUCCESS_HOVER = "#059669"
    SUCCESS_PRESSED = "#047857"
    SUCCESS_SURFACE = "rgba(16, 185, 129, 0.12)"
    SUCCESS_BORDER = "rgba(16, 185, 129, 0.35)"

    # Warning (Amber)
    WARNING = "#f59e0b"
    WARNING_HOVER = "#d97706"
    WARNING_SURFACE = "rgba(245, 158, 11, 0.12)"
    WARNING_BORDER = "rgba(245, 158, 11, 0.35)"

    # Danger / Destructive (Rose/Red)
    DANGER = "#ef4444"
    DANGER_HOVER = "#dc2626"
    DANGER_PRESSED = "#b91c1c"
    DANGER_SURFACE = "rgba(239, 68, 68, 0.14)"
    DANGER_BORDER = "rgba(239, 68, 68, 0.35)"

    # Secondary Action Buttons
    BTN_SECONDARY_BG = "#222736"
    BTN_SECONDARY_HOVER = "#2d3347"
    BTN_SECONDARY_PRESSED = "#1c202d"


class Typography:
    """Standardized typography hierarchy."""

    FONT_FAMILY = (
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", '
        'Arial, "Noto Sans", sans-serif'
    )
    FONT_MONO = (
        '"JetBrains Mono", "SF Mono", "Menlo", "Consolas", "Courier New", monospace'
    )

    SIZE_TITLE = 17
    SIZE_PANEL_HEADER = 14
    SIZE_BODY = 13
    SIZE_METADATA = 12
    SIZE_CAPTION = 11


class Spacing:
    """Spacing scale (4px / 8px increments)."""

    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 20
    XXL = 24


# Legacy constant aliases for backwards-compatibility with existing tests
COLOR_BG_MAIN = ThemeColors.BG_APP
COLOR_BG_SURFACE = ThemeColors.BG_SURFACE
COLOR_BG_CARD = ThemeColors.BG_PANEL
COLOR_BG_INPUT = ThemeColors.BG_INPUT
COLOR_BORDER = ThemeColors.BORDER_DEFAULT
COLOR_BORDER_FOCUS = ThemeColors.BORDER_FOCUS
COLOR_TEXT_PRIMARY = ThemeColors.TEXT_PRIMARY
COLOR_TEXT_SECONDARY = ThemeColors.TEXT_SECONDARY
COLOR_TEXT_MUTED = ThemeColors.TEXT_MUTED
COLOR_ACCENT = ThemeColors.ACCENT_PRIMARY
COLOR_ACCENT_HOVER = ThemeColors.ACCENT_HOVER
COLOR_ACCENT_PRESSED = ThemeColors.ACCENT_PRESSED
COLOR_SUCCESS = ThemeColors.SUCCESS
COLOR_SUCCESS_HOVER = ThemeColors.SUCCESS_HOVER
COLOR_DANGER = ThemeColors.DANGER
COLOR_DANGER_HOVER = ThemeColors.DANGER_HOVER
COLOR_WARNING = ThemeColors.WARNING


# ===========================================================================
# 2. GLOBAL APPLICATION QSS STYLESHEET
# ===========================================================================

APP_STYLESHEET = f"""
/* -------------------------------------------------------------
   Global Reset and Defaults
   ------------------------------------------------------------- */
QWidget {{
    background-color: transparent;
    color: {ThemeColors.TEXT_PRIMARY};
    font-family: {Typography.FONT_FAMILY};
    font-size: 13px;
    selection-background-color: {ThemeColors.ACCENT_PRIMARY};
    selection-color: #ffffff;
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {ThemeColors.BG_APP};
}}

/* -------------------------------------------------------------
   Scrollbars
   ------------------------------------------------------------- */
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 2px 0 2px 0;
}}
QScrollBar::handle:vertical {{
    background-color: {ThemeColors.BORDER_STRONG};
    min-height: 28px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {ThemeColors.TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
    margin: 0 2px 0 2px;
}}
QScrollBar::handle:horizontal {{
    background-color: {ThemeColors.BORDER_STRONG};
    min-width: 28px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {ThemeColors.TEXT_MUTED};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* -------------------------------------------------------------
   Splitter Handles
   ------------------------------------------------------------- */
QSplitter::handle {{
    background-color: {ThemeColors.BORDER_SUBTLE};
}}
QSplitter::handle:hover {{
    background-color: {ThemeColors.ACCENT_PRIMARY};
}}
QSplitter::handle:horizontal {{
    width: 3px;
}}
QSplitter::handle:vertical {{
    height: 3px;
}}

/* -------------------------------------------------------------
   Dividers
   ------------------------------------------------------------- */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{ /* HLine / VLine */
    color: {ThemeColors.BORDER_SUBTLE};
    background-color: {ThemeColors.BORDER_SUBTLE};
    border: none;
}}

/* -------------------------------------------------------------
   Top Application Header Bar
   ------------------------------------------------------------- */
QFrame#header_bar {{
    background-color: {ThemeColors.BG_HEADER};
    border-bottom: 1px solid {ThemeColors.BORDER_DEFAULT};
    padding: 0px;
}}

QLabel#app_title {{
    font-size: 16px;
    font-weight: 700;
    color: {ThemeColors.TEXT_PRIMARY};
    letter-spacing: -0.2px;
}}

QLabel#app_subtitle {{
    font-size: 12px;
    color: {ThemeColors.TEXT_MUTED};
}}

/* Header Status Pills */
QLabel#status_pill_online {{
    background-color: {ThemeColors.SUCCESS_SURFACE};
    color: #34d399;
    border: 1px solid {ThemeColors.SUCCESS_BORDER};
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 600;
}}

QLabel#status_pill_offline {{
    background-color: {ThemeColors.DANGER_SURFACE};
    color: #f87171;
    border: 1px solid {ThemeColors.DANGER_BORDER};
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 600;
}}

/* Database mode badge */
QLabel#db_status_badge {{
    background-color: rgba(59, 130, 246, 0.1);
    color: #93c5fd;
    border: 1px solid rgba(59, 130, 246, 0.25);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 500;
}}

/* -------------------------------------------------------------
   Push Buttons Hierarchy
   ------------------------------------------------------------- */
QPushButton {{
    background-color: {ThemeColors.BTN_SECONDARY_BG};
    color: {ThemeColors.TEXT_PRIMARY};
    border: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-radius: 6px;
    padding: 0 14px;
    min-height: 32px;
    font-size: 13px;
    font-weight: 500;
    text-align: center;
}}
QPushButton:hover {{
    background-color: {ThemeColors.BTN_SECONDARY_HOVER};
    border-color: {ThemeColors.BORDER_STRONG};
    color: #ffffff;
}}
QPushButton:pressed {{
    background-color: {ThemeColors.BTN_SECONDARY_PRESSED};
    border-color: {ThemeColors.BORDER_DEFAULT};
}}
QPushButton:disabled {{
    background-color: {ThemeColors.BG_SURFACE};
    color: {ThemeColors.TEXT_DISABLED};
    border-color: {ThemeColors.BORDER_SUBTLE};
}}

/* Primary Buttons */
QPushButton#primary_button, QPushButton[primary="true"] {{
    background-color: {ThemeColors.ACCENT_PRIMARY};
    color: #ffffff;
    border: 1px solid {ThemeColors.ACCENT_PRIMARY};
    font-weight: 600;
}}
QPushButton#primary_button:hover, QPushButton[primary="true"]:hover {{
    background-color: {ThemeColors.ACCENT_HOVER};
    border-color: {ThemeColors.ACCENT_HOVER};
}}
QPushButton#primary_button:pressed, QPushButton[primary="true"]:pressed {{
    background-color: {ThemeColors.ACCENT_PRESSED};
    border-color: {ThemeColors.ACCENT_PRESSED};
}}
QPushButton#primary_button:disabled, QPushButton[primary="true"]:disabled {{
    background-color: rgba(59, 130, 246, 0.25);
    color: rgba(255, 255, 255, 0.4);
    border-color: transparent;
}}

/* Success Buttons */
QPushButton#success_button {{
    background-color: {ThemeColors.SUCCESS};
    color: #ffffff;
    border: 1px solid {ThemeColors.SUCCESS};
    font-weight: 600;
}}
QPushButton#success_button:hover {{
    background-color: {ThemeColors.SUCCESS_HOVER};
    border-color: {ThemeColors.SUCCESS_HOVER};
}}
QPushButton#success_button:pressed {{
    background-color: {ThemeColors.SUCCESS_PRESSED};
    border-color: {ThemeColors.SUCCESS_PRESSED};
}}

/* Danger / Destructive Buttons */
QPushButton#danger_button {{
    background-color: {ThemeColors.DANGER_SURFACE};
    color: #f87171;
    border: 1px solid {ThemeColors.DANGER_BORDER};
    font-weight: 600;
}}
QPushButton#danger_button:hover {{
    background-color: {ThemeColors.DANGER};
    color: #ffffff;
    border-color: {ThemeColors.DANGER};
}}
QPushButton#danger_button:pressed {{
    background-color: {ThemeColors.DANGER_PRESSED};
    border-color: {ThemeColors.DANGER_PRESSED};
}}

/* Toolbar Compact Buttons */
QPushButton.compact-btn, QPushButton[compact="true"] {{
    min-height: 28px;
    height: 28px;
    padding: 0 10px;
    font-size: 12px;
}}

/* Toolbar Icon Buttons */
QPushButton.icon-btn, QPushButton[icon_btn="true"] {{
    min-height: 28px;
    height: 28px;
    min-width: 28px;
    max-width: 28px;
    padding: 0px;
    font-size: 12px;
    font-weight: 600;
}}

/* -------------------------------------------------------------
   Input Fields and Editors
   ------------------------------------------------------------- */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {ThemeColors.BG_INPUT};
    color: {ThemeColors.TEXT_PRIMARY};
    border: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    min-height: 24px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {ThemeColors.BORDER_FOCUS};
    background-color: #171b26;
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {ThemeColors.BG_SURFACE};
    color: {ThemeColors.TEXT_DISABLED};
    border-color: {ThemeColors.BORDER_SUBTLE};
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {ThemeColors.BG_INPUT};
    color: {ThemeColors.TEXT_PRIMARY};
    border: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-radius: 6px;
    padding: 4px 8px;
    padding-right: 22px;
    font-size: 13px;
    min-height: 24px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {ThemeColors.BORDER_FOCUS};
    background-color: #171b26;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-bottom: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-top-right-radius: 5px;
    background-color: {ThemeColors.BG_SURFACE};
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border-left: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-bottom-right-radius: 5px;
    background-color: {ThemeColors.BG_SURFACE};
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {ThemeColors.BG_SURFACE_HOVER};
}}

QComboBox {{
    background-color: {ThemeColors.BG_INPUT};
    color: {ThemeColors.TEXT_PRIMARY};
    border: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 13px;
    min-height: 24px;
}}
QComboBox:focus {{
    border: 1px solid {ThemeColors.BORDER_FOCUS};
    background-color: #171b26;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid {ThemeColors.BORDER_DEFAULT};
}}
QComboBox QAbstractItemView {{
    background-color: {ThemeColors.BG_SURFACE};
    color: {ThemeColors.TEXT_PRIMARY};
    border: 1px solid {ThemeColors.BORDER_DEFAULT};
    selection-background-color: {ThemeColors.ACCENT_PRIMARY};
    selection-color: #ffffff;
    padding: 4px;
}}

/* -------------------------------------------------------------
   Tables and Views
   ------------------------------------------------------------- */
QTableView, QTableWidget, QTreeView, QListView {{
    background-color: {ThemeColors.BG_PANEL};
    alternate-background-color: {ThemeColors.BG_SURFACE};
    color: {ThemeColors.TEXT_SECONDARY};
    border: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-radius: 6px;
    gridline-color: {ThemeColors.BORDER_SUBTLE};
    font-size: 12px;
    selection-background-color: rgba(59, 130, 246, 0.25);
    selection-color: #ffffff;
}}
QTableView::item, QTableWidget::item {{
    padding: 4px 8px;
    border-bottom: 1px solid {ThemeColors.BORDER_SUBTLE};
}}
QTableView::item:hover, QTableWidget::item:hover {{
    background-color: {ThemeColors.BG_SURFACE_HOVER};
}}
QHeaderView::section {{
    background-color: {ThemeColors.BG_SURFACE};
    color: {ThemeColors.TEXT_PRIMARY};
    padding: 6px 10px;
    border: none;
    border-right: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-bottom: 1px solid {ThemeColors.BORDER_DEFAULT};
    font-weight: 600;
    font-size: 12px;
}}

/* -------------------------------------------------------------
   Cards, Panels, and Message Bubbles
   ------------------------------------------------------------- */
QFrame#card_frame {{
    background-color: {ThemeColors.BG_SURFACE};
    border: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-radius: 8px;
}}

QFrame#user_message_bubble {{
    background-color: #1e2638;
    border: 1px solid #3b82f650;
    border-radius: 10px;
    padding: 10px;
}}

QFrame#assistant_message_bubble {{
    background-color: {ThemeColors.BG_SURFACE};
    border: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-radius: 10px;
    padding: 10px;
}}

QFrame#system_event_bubble {{
    background-color: rgba(35, 40, 56, 0.6);
    border: 1px dashed {ThemeColors.BORDER_DEFAULT};
    border-radius: 8px;
    padding: 8px;
}}

/* Code / SQL Box */
QPlainTextEdit#sql_editor {{
    font-family: {Typography.FONT_MONO};
    font-size: 12px;
    background-color: #0d0f15;
    color: #67e8f9;
    border: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-radius: 6px;
    padding: 8px;
}}

/* -------------------------------------------------------------
   Group Boxes
   ------------------------------------------------------------- */
QGroupBox {{
    font-weight: 600;
    font-size: 13px;
    border: 1px solid {ThemeColors.BORDER_DEFAULT};
    border-radius: 8px;
    margin-top: 16px;
    padding: 20px 14px 14px 14px;
    background-color: {ThemeColors.BG_SURFACE};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 2px 8px;
    color: #93c5fd;
    font-weight: 600;
}}

/* -------------------------------------------------------------
   Check Boxes
   ------------------------------------------------------------- */
QCheckBox {{
    color: {ThemeColors.TEXT_SECONDARY};
    font-size: 13px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {ThemeColors.BORDER_STRONG};
    border-radius: 4px;
    background-color: {ThemeColors.BG_INPUT};
}}
QCheckBox::indicator:hover {{
    border-color: {ThemeColors.ACCENT_PRIMARY};
}}
QCheckBox::indicator:checked {{
    background-color: {ThemeColors.ACCENT_PRIMARY};
    border-color: {ThemeColors.ACCENT_PRIMARY};
}}
"""
