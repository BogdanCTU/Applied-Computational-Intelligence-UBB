"""Centralized light theme design system for the Agent-OM Workbench."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory, QWidget


@dataclass(frozen=True)
class LightPalette:
    """Authoritative light theme color tokens."""

    bg_main: str = "#F5F6F8"
    surface_primary: str = "#FFFFFF"
    surface_secondary: str = "#EEF1F4"
    text_primary: str = "#17202A"
    text_secondary: str = "#52606D"
    text_disabled: str = "#89939E"
    primary_action: str = "#2457A6"
    primary_action_hover: str = "#1D478A"
    primary_action_text: str = "#FFFFFF"
    secondary_btn_bg: str = "#E8EDF3"
    secondary_btn_hover: str = "#DCE3EC"
    secondary_btn_text: str = "#243447"
    border: str = "#CBD2DA"
    input_bg: str = "#FFFFFF"
    focus_outline: str = "#2457A6"
    success: str = "#237A4B"
    success_bg: str = "#EAF5EF"
    warning: str = "#946200"
    warning_bg: str = "#FDF6E7"
    error: str = "#B42318"
    error_hover: str = "#911B12"
    error_bg: str = "#FDECEC"
    table_alt_row: str = "#F5F7FA"
    selection_bg: str = "#DCE8F8"
    selection_text: str = "#17202A"


PALETTE = LightPalette()

# Standardized spacing scale (px)
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24


def get_ui_font_family() -> str:
    """Return appropriate system UI font family without triggering generic alias warnings."""
    if platform.system() == "Windows":
        return "Segoe UI"
    sys_font = QFontDatabase.systemFont(QFontDatabase.GeneralFont).family()
    return sys_font or "Helvetica Neue"


def get_monospace_font_family() -> str:
    """Return crisp cross-platform monospace font family."""
    if platform.system() == "Windows":
        return "Consolas"
    fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont).family()
    return fixed_font or "Menlo"


def status_colors(level: str) -> Tuple[str, str]:
    """Return `(foreground_hex, background_hex)` accessible pair for a semantic status level."""
    lvl = (level or "neutral").strip().lower()
    if lvl in ("success", "ok", "valid", "connected", "completed", "ready", "compliant"):
        return PALETTE.success, PALETTE.success_bg
    if lvl in ("warning", "warn", "cancelled", "exceeds"):
        return PALETTE.warning, PALETTE.warning_bg
    if lvl in ("error", "failed", "disconnected", "blocked", "critical"):
        return PALETTE.error, PALETTE.error_bg
    if lvl in ("info", "running", "active", "readonly"):
        return PALETTE.primary_action, PALETTE.selection_bg
    return PALETTE.text_primary, PALETTE.surface_primary


def build_application_stylesheet(p: LightPalette = PALETTE) -> str:
    """Build centralized light QSS covering all Qt widgets in the workbench."""
    ui_font = get_ui_font_family()
    mono_font = get_monospace_font_family()
    check_svg_path = (Path(__file__).resolve().parent / "check_white.svg").as_posix()

    return f"""
    * {{
        font-family: "{ui_font}";
    }}

    QMainWindow, QDialog {{
        background-color: {p.bg_main};
        color: {p.text_primary};
    }}

    QWidget {{
        color: {p.text_primary};
        font-size: 13px;
    }}

    /* Application Top Header Bar */
    QFrame#AppHeader {{
        background-color: {p.surface_primary};
        border: none;
        border-bottom: 1px solid {p.border};
    }}
    QLabel#AppTitleLabel {{
        color: {p.text_primary};
        font-size: 20px;
        font-weight: 700;
        background: transparent;
    }}
    QLabel#HeaderPageLabel {{
        color: {p.text_secondary};
        font-size: 14px;
        font-weight: 600;
        background: transparent;
    }}
    QLabel#HeaderMetaLabel {{
        color: {p.text_secondary};
        font-size: 12px;
        background: transparent;
    }}

    /* Left Navigation Sidebar */
    QListWidget#SidebarNav {{
        background-color: {p.surface_secondary};
        color: {p.text_primary};
        border: none;
        border-right: 1px solid {p.border};
        padding: 8px 0px;
        font-size: 13px;
        outline: none;
    }}
    QListWidget#SidebarNav::item {{
        height: 38px;
        padding: 0px 14px;
        border-left: 3px solid transparent;
        color: {p.text_primary};
    }}
    QListWidget#SidebarNav::item:hover {{
        background-color: {p.secondary_btn_hover};
    }}
    QListWidget#SidebarNav::item:selected {{
        background-color: {p.selection_bg};
        color: {p.selection_text};
        border-left: 3px solid {p.primary_action};
        font-weight: 700;
    }}

    /* Stacked Content Area */
    QStackedWidget#MainStack {{
        background-color: {p.bg_main};
    }}

    /* Page Titles & Subtitles */
    QLabel[labelRole="pageTitle"] {{
        color: {p.text_primary};
        font-size: 18px;
        font-weight: 700;
        background: transparent;
    }}
    QLabel[labelRole="pageSubtitle"] {{
        color: {p.text_secondary};
        font-size: 12px;
        font-weight: 400;
        background: transparent;
    }}
    QLabel[labelRole="sectionTitle"] {{
        color: {p.text_primary};
        font-size: 14px;
        font-weight: 700;
        background: transparent;
    }}
    QLabel[labelRole="meta"] {{
        color: {p.text_secondary};
        font-size: 12px;
        background: transparent;
    }}

    /* Content Frames & Cards */
    QFrame#MetricPanel {{
        background-color: {p.surface_primary};
        border: 1px solid {p.border};
        border-radius: 4px;
    }}
    QFrame#SummaryBanner {{
        background-color: {p.surface_secondary};
        border: 1px solid {p.border};
        border-radius: 4px;
        padding: 8px 12px;
    }}
    QFrame#SectionSeparator {{
        background-color: {p.border};
        max-height: 1px;
        border: none;
    }}

    /* Group Boxes (clean section header above card border) */
    QGroupBox {{
        background-color: {p.surface_primary};
        border: 1px solid {p.border};
        border-radius: 4px;
        margin-top: 22px;
        padding: 12px 12px 12px 12px;
        font-size: 14px;
        font-weight: 700;
        color: {p.text_primary};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 2px;
        top: 0px;
        padding: 0px;
        background-color: transparent;
        color: {p.text_primary};
        font-size: 14px;
        font-weight: 700;
    }}

    /* Buttons */
    QPushButton {{
        background-color: {p.secondary_btn_bg};
        color: {p.secondary_btn_text};
        border: 1px solid {p.border};
        border-radius: 4px;
        padding: 6px 14px;
        min-height: 22px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {p.secondary_btn_hover};
    }}
    QPushButton:focus {{
        border: 2px solid {p.focus_outline};
    }}
    QPushButton:disabled {{
        background-color: {p.surface_secondary};
        color: {p.text_disabled};
        border: 1px solid {p.border};
    }}

    QPushButton[buttonRole="primary"] {{
        background-color: {p.primary_action};
        color: {p.primary_action_text};
        border: 1px solid {p.primary_action};
    }}
    QPushButton[buttonRole="primary"]:hover {{
        background-color: {p.primary_action_hover};
        border: 1px solid {p.primary_action_hover};
    }}
    QPushButton[buttonRole="primary"]:disabled {{
        background-color: {p.surface_secondary};
        color: {p.text_disabled};
        border: 1px solid {p.border};
    }}

    QPushButton[buttonRole="destructive"] {{
        background-color: {p.error};
        color: {p.primary_action_text};
        border: 1px solid {p.error};
    }}
    QPushButton[buttonRole="destructive"]:hover {{
        background-color: {p.error_hover};
        border: 1px solid {p.error_hover};
    }}
    QPushButton[buttonRole="destructive"]:disabled {{
        background-color: {p.surface_secondary};
        color: {p.text_disabled};
        border: 1px solid {p.border};
    }}

    /* Text Inputs, Combos, Spinners */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: {p.input_bg};
        color: {p.text_primary};
        border: 1px solid {p.border};
        border-radius: 4px;
        padding: 5px 8px;
        min-height: 22px;
        font-size: 13px;
        selection-background-color: {p.selection_bg};
        selection-color: {p.selection_text};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {{
        border: 2px solid {p.focus_outline};
    }}
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background-color: {p.surface_secondary};
        color: {p.text_disabled};
    }}
    QComboBox QAbstractItemView {{
        background-color: {p.surface_primary};
        color: {p.text_primary};
        border: 1px solid {p.border};
        selection-background-color: {p.selection_bg};
        selection-color: {p.selection_text};
    }}

    QCheckBox {{
        color: {p.text_primary};
        font-size: 13px;
        spacing: 8px;
        background: transparent;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {p.text_disabled};
        border-radius: 3px;
        background-color: {p.input_bg};
    }}
    QCheckBox::indicator:hover {{
        border: 1px solid {p.primary_action};
    }}
    QCheckBox::indicator:focus {{
        border: 2px solid {p.focus_outline};
    }}
    QCheckBox::indicator:checked {{
        background-color: {p.primary_action};
        border: 1px solid {p.primary_action};
        image: url("{check_svg_path}");
    }}
    QCheckBox:disabled {{
        color: {p.text_disabled};
    }}
    QCheckBox::indicator:disabled {{
        background-color: {p.surface_secondary};
        border: 1px solid {p.border};
    }}

    /* Monospace / Read-Only Text Panes */
    QPlainTextEdit {{
        background-color: {p.surface_primary};
        color: {p.text_primary};
        border: 1px solid {p.border};
        border-radius: 4px;
        padding: 6px;
        font-family: "{mono_font}";
        font-size: 12px;
        selection-background-color: {p.selection_bg};
        selection-color: {p.selection_text};
    }}

    /* Tables */
    QTableWidget, QTableView {{
        background-color: {p.surface_primary};
        alternate-background-color: {p.table_alt_row};
        color: {p.text_primary};
        border: 1px solid {p.border};
        gridline-color: {p.border};
        font-size: 12px;
        selection-background-color: {p.selection_bg};
        selection-color: {p.selection_text};
    }}
    QTableWidget::item, QTableView::item {{
        padding: 4px 8px;
        border-bottom: 1px solid {p.surface_secondary};
    }}
    QTableWidget::item:selected, QTableView::item:selected {{
        background-color: {p.selection_bg};
        color: {p.selection_text};
    }}
    QHeaderView::section {{
        background-color: {p.surface_secondary};
        color: {p.text_primary};
        font-size: 12px;
        font-weight: 700;
        padding: 6px 8px;
        border: none;
        border-bottom: 1px solid {p.border};
        border-right: 1px solid {p.border};
    }}
    QTableCornerButton::section {{
        background-color: {p.surface_secondary};
        border: none;
        border-bottom: 1px solid {p.border};
    }}

    /* Tabs */
    QTabWidget::pane {{
        background-color: {p.surface_primary};
        border: 1px solid {p.border};
        border-radius: 4px;
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: {p.surface_secondary};
        color: {p.text_secondary};
        border: 1px solid {p.border};
        border-bottom: none;
        padding: 7px 14px;
        margin-right: 2px;
        font-size: 13px;
        font-weight: 600;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    QTabBar::tab:selected {{
        background-color: {p.surface_primary};
        color: {p.text_primary};
        border-top: 2px solid {p.primary_action};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {p.secondary_btn_hover};
        color: {p.text_primary};
    }}

    /* Progress Bar */
    QProgressBar {{
        background-color: {p.surface_secondary};
        color: {p.text_primary};
        border: 1px solid {p.border};
        border-radius: 4px;
        text-align: center;
        min-height: 20px;
        font-size: 12px;
        font-weight: 600;
    }}
    QProgressBar::chunk {{
        background-color: {p.primary_action};
        border-radius: 2px;
    }}

    /* Scrollbars & Splitters */
    QSplitter::handle {{
        background-color: {p.surface_secondary};
        border: 1px solid {p.border};
    }}
    QScrollArea {{
        background-color: {p.bg_main};
        border: none;
    }}

    /* Status Bar & MessageBox */
    QStatusBar {{
        background-color: {p.surface_secondary};
        color: {p.text_secondary};
        border-top: 1px solid {p.border};
        font-size: 12px;
        padding: 2px 8px;
    }}
    QMessageBox {{
        background-color: {p.surface_primary};
        color: {p.text_primary};
    }}
    QMessageBox QLabel {{
        color: {p.text_primary};
        font-size: 13px;
    }}
    """


def build_light_palette(p: LightPalette = PALETTE) -> QPalette:
    """Construct explicit light QPalette overriding OS dark mode defaults."""
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(p.bg_main))
    pal.setColor(QPalette.WindowText, QColor(p.text_primary))
    pal.setColor(QPalette.Base, QColor(p.surface_primary))
    pal.setColor(QPalette.AlternateBase, QColor(p.table_alt_row))
    pal.setColor(QPalette.ToolTipBase, QColor(p.surface_primary))
    pal.setColor(QPalette.ToolTipText, QColor(p.text_primary))
    pal.setColor(QPalette.Text, QColor(p.text_primary))
    pal.setColor(QPalette.Button, QColor(p.secondary_btn_bg))
    pal.setColor(QPalette.ButtonText, QColor(p.secondary_btn_text))
    pal.setColor(QPalette.BrightText, QColor(p.primary_action_text))
    pal.setColor(QPalette.Link, QColor(p.primary_action))
    pal.setColor(QPalette.Highlight, QColor(p.selection_bg))
    pal.setColor(QPalette.HighlightedText, QColor(p.selection_text))
    pal.setColor(QPalette.PlaceholderText, QColor(p.text_disabled))

    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor(p.text_disabled))
    pal.setColor(QPalette.Disabled, QPalette.Button, QColor(p.surface_secondary))
    pal.setColor(QPalette.Disabled, QPalette.Base, QColor(p.surface_secondary))
    return pal


def apply_light_theme(target: QCoreApplication | QWidget | None = None) -> None:
    """Apply the centralized light palette, Fusion style, UI font, and stylesheet."""
    app = QApplication.instance()
    stylesheet = build_application_stylesheet(PALETTE)
    palette = build_light_palette(PALETTE)

    if app is not None:
        if "Fusion" in QStyleFactory.keys():
            app.setStyle(QStyleFactory.create("Fusion"))
        app.setPalette(palette)
        font = QFont(get_ui_font_family())
        font.setPixelSize(13)
        app.setFont(font)
        if app.styleSheet() != stylesheet:
            app.setStyleSheet(stylesheet)

    if isinstance(target, QWidget):
        target.setPalette(palette)
        if app is None:
            target.setStyleSheet(stylesheet)
