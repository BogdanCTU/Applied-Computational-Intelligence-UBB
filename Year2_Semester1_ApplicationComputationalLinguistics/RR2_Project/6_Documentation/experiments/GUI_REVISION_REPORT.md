# GUI Revision Report — Light Theme, Visual Consistency & Usability Refactoring

**Project:** Agent-OM Workbench (`RR2_Project`)  
**Date:** 2026-11-22  
**Scope:** Centralized light-theme design system, shared UI components, application shell, all 10 PySide6 views, GUI documentation, and visual/automated verification.  
**Non-Modification Guarantee:** Zero edits to `original_repo/`, ontology parsers, retrieval/RRF/matching algorithms, LLM providers, PostgreSQL schemas, `1_Source/config.py`, or historical experimental results (`output/`).

---

## 1. Previous GUI Problems Identified

An audit of the pre-revision GUI (`1_Source/gui/`) revealed the following visual and usability defects:
1. **Mixed Dark/Light Chrome & Contrast Inconsistencies:** A dark `#0F172A` top banner and dark `#1E293B` sidebar (`main_window.py`) were paired with pale light content panels (`#F8FAFC`), while Mac/Windows OS dark-mode system palettes could bleed into native controls (`QMessageBox`, `QComboBox`, `QCheckBox`).
2. **Scattered Hardcoded Styles:** Colors (`#2563EB`, `#059669`, `#DC2626`, `#DCFCE7`), font sizes, and inline `Consolas, monospace` strings were duplicated across `main_window.py` and individual view files without a shared palette or `QPalette`.
3. **GroupBox Header & Border Artifacts:** Unbalanced top margins caused `QGroupBox::title` text to straddle differing card and outer window background tones.
4. **Invisible Checkboxes Under Styled Controls:** Under Qt 6 Fusion styling, checkboxes (`QCheckBox`) lacked explicit indicator styling, causing unchecked indicator boxes to disappear on Tabs 3, 4, and 5 (`Datasets`, `Configuration`, `Run Pipeline`).
5. **Layout Crowding & Overlap at Smaller Window Sizes:** At `1100x720`, `Configuration` (`ConfigurationView`) compressed its `QFormLayout` and numeric spinbox grid until controls clipped vertically. Similarly, `Run Pipeline` placed 8 controls on a single cramped horizontal row, and `Run History` placed a 9-column table beside a JSON inspector in a horizontal splitter, forcing horizontal scrolling.
6. **Chart DPI & Ampersand Rendering Bugs:** Embedded Matplotlib canvases (`EvaluationView`) rendered at `160 DPI` inside Qt logical coordinates (`96 DPI`), clipping chart titles and axis labels, while single `&` characters in Qt tab titles (`Precision, Recall & F1`, `Retrieval & RRF Scores`) were consumed as keyboard mnemonics.
7. **Verbose & Technical Wording:** Screen names used numbered prefixes (`1. Dashboard` .. `10. Report & Artifact Export`), and labels used unnecessarily verbose wording (`Execute`, `Run Full Health Check`, `Provision New Isolated Database`, `Export Full Replication Bundle`).
8. **GUI Service Bug (`? baseline files`):** `EnvironmentService.check_original_repo_status()` queried `total_files` rather than `file_count` in `original_repo_baseline_sha256.json`, displaying `? baseline files` in the `Environment` tab.

---

## 2. New Centralized Design System (`1_Source/gui/styles/`)

Implemented in [`1_Source/gui/styles/theme.py`](../../1_Source/gui/styles/theme.py) with crisp SVG checkbox indicator asset [`check_white.svg`](../../1_Source/gui/styles/check_white.svg):

### 2.1. Light Theme Palette
| Role | Hex Token | Application |
| :--- | :---: | :--- |
| Main application background | `#F5F6F8` | `QMainWindow`, `QDialog`, `QStackedWidget#MainStack` |
| Primary content surface | `#FFFFFF` | `QGroupBox`, `#MetricPanel`, cards, tables, inputs |
| Secondary surface | `#EEF1F4` | Sidebar (`#SidebarNav`), `#SummaryBanner`, table/tab headers, status bar |
| Primary text | `#17202A` | Body copy, headings, active sidebar selection text |
| Secondary text | `#52606D` | Subtitles, metadata labels, inactive tabs, status bar text |
| Disabled text | `#89939E` | Disabled inputs and buttons |
| Primary action / Hover | `#2457A6` / `#1D478A` | Primary buttons (`buttonRole="primary"`), checked checkboxes, focus rings |
| Primary action text | `#FFFFFF` | Text on primary and destructive buttons |
| Secondary button BG / Text | `#E8EDF3` / `#243447` | Standard secondary actions (hover `#DCE3EC`) |
| Border | `#CBD2DA` | Cards, panels, inputs, headers, tables |
| Success (text / light tint) | `#237A4B` / `#EAF5EF` | Connected services, `OK`, `Compliant (<=4B)`, `Completed`, `Shared TP` |
| Warning (text / light tint) | `#946200` / `#FDF6E7` | Warnings, `Exceeds 4B`, `Cancelled`, `Blocked` configs |
| Error / Destructive (text / tint) | `#B42318` / `#FDECEC` | Disconnected services, `Failed`, `Shared FP`, destructive `Cancel Run` buttons |
| Table alternate row | `#F5F7FA` | Zebra striping across all `QTableWidget` and `QTableView` tables |
| Selection background / text | `#DCE8F8` / `#17202A` | Active navigation item and selected table rows |

### 2.2. Typography, Spacing & Geometry
- **Font Family:** System UI font (`Segoe UI` on Windows; platform native system font on macOS/Linux) for prose (`13px` normal, `20px` app title, `18px` page titles, `14px` section headings, `12px` tables/metadata); system monospace font (`Consolas` / `Menlo`, `12px`) for JSON, logs, and entity previews.
- **Qt Style & Palette:** Forces Qt `"Fusion"` style plus an explicit light `QPalette` (`build_light_palette`) so OS dark-mode settings cannot invert dialog or dropdown contrast.
- **Geometry:** Standardized `34px+` minimum height on inputs/buttons, `32px` table row height, `38px` sidebar navigation rows, and `4 / 8 / 12 / 16 / 24 px` spacing hierarchy.

---

## 3. Shared Reusable Components (`1_Source/gui/widgets/common.py`)

Created [`1_Source/gui/widgets/common.py`](../../1_Source/gui/widgets/common.py) exporting:
- `create_page_header(title, subtitle, right_widget)`: Enforces consistent `18px` bold page title, one-sentence `#52606D` subtitle, and optional top-right action button.
- `create_button(text, role, tooltip, accessible_name)`: Applies semantic `"primary"`, `"secondary"`, or `"destructive"` styling, accessible names, pointing-hand cursors, and functional tooltips.
- `configure_table(table, stretch_last, hide_vertical_header)`: Standardizes `32px` rows, alternating row striping, hidden gridlines, row selection, read-only triggers, and crisp header alignment.
- `make_status_item(text, level, align)` & `apply_status_label(label, text, level)`: Ensures every status indicator pairs readable text with accessible foreground/background contrast tokens (never communicating state by color alone).
- `show_info_dialog`, `show_warning_dialog`, `show_error_dialog`, `confirm_destructive_action`, and `format_user_error`: Standardized light-themed dialogs that summarize errors and next steps without exposing raw tracebacks.

---

## 4. Application Shell & Tab-by-Tab Refactoring

- **Main Window ([`main_window.py`](../../1_Source/gui/main_window.py)) & [`run_gui.py`](../../run_gui.py):** Replaced dark banner/sidebar with compact light header (`Agent-OM Workbench / <Current Page>` + right-aligned loopback metadata) and light `#EEF1F4` sidebar with concise unnumbered navigation items:
  `Dashboard`, `Environment`, `Datasets`, `Configuration`, `Run Pipeline`, `Inspector`, `Comparison`, `Evaluation`, `Run History`, `Export`.
- **Tab 1 — Dashboard (`dashboard_view.py`):** Four clean status panels (`PostgreSQL: Connected/Disconnected`, `Ollama Inference`, `Reference Repository`, `Recorded Runs`), concise 6-button `Quick Actions` bar (`Run Matching` primary), and full experiment ID visibility with right-aligned numeric columns.
- **Tab 2 — Environment (`environment_view.py`):** Primary `Check Status` button, `System Status` table, `PostgreSQL Databases` inspector (`Protected (Read-Only)` vs `Isolated (Writable)`), `Create Database` controls, and `Ollama Models` table with `Compliant (<=4B)` / `Exceeds 4B` status indicators. Also fixed `EnvironmentService` to read `file_count` so `8358 baseline files` renders accurately instead of `?`.
- **Tab 3 — Datasets (`dataset_view.py`):** `Load Dataset` primary button, standardized `Browse` buttons, crisp styled checkboxes (`QCheckBox::indicator` with `check_white.svg`), and clean plain-text dataset summary.
- **Tab 4 — Configuration (`configuration_view.py`):** Wrapped in a `QScrollArea` (`setWidgetResizable(True)`) with a 3-row responsive `QGridLayout` for hyperparameters and parity checkboxes, minimum `34px` input heights, `Apply Configuration` primary button, and accessible status banner. Eliminated all vertical control overlap at `1100x720`.
- **Tab 5 — Run Pipeline (`wizard_view.py`):** Split crowded execution bar into two clean rows (`Experiment ID` + entity cap / reuse options above `Run Matching`, `Run Baseline`, `Cancel Run`, and progress bar), added confirmation prompt on destructive `Cancel Run`, and standardized status cells in `Pipeline Stages`.
- **Tab 6 — Inspector (`inspector_view.py`):** Sized narrow columns (`Side`, `Type`, `Candidates`, `Validations`) to contents, added URI tooltips, auto-selected first row on load, and fixed mnemonic `&` stripping (`Retrieval && RRF Scores`).
- **Tab 7 — Comparison (`comparison_view.py`):** Auto-populates initial comparison on load, pairs readable `Classification` status cells (`Shared TP`, `Shared FP`, `Only in A/B`, `Missed by Both`) with high-contrast text/tints, and adds URI tooltips.
- **Tab 8 — Evaluation (`evaluation_view.py`):** Fixed mnemonic `&` stripping (`Precision, Recall && F1`), matched embedded Matplotlib figure DPI (`96 DPI`) and `tight_layout(pad=1.0)` so axis labels (`Percentage (%)`), bar annotations, rotated x-tick labels, and titles fit cleanly inside `FigureCanvasQTAgg` at both `1380x860` and `1100x720`.
- **Tab 9 — Run History (`history_view.py`):** Stacked the 9-column `Recorded Runs` table above the JSON detail pane inside a vertical splitter so all 9 metrics columns display without horizontal scrolling, added confirmation dialog on `Cancel Run`, and standardized `Completed` / `Reference` / `Cancelled` / `Failed` status indicators.
- **Tab 10 — Export (`export_view.py`):** Replaced Unicode bullets with `- ` plain-text items, added output directory tooltip, and standardized primary `Export Results` button and user-friendly restriction dialogs.

---

## 5. Accessibility Improvements

- **WCAG AA Text Contrast:** `#17202A` on `#FFFFFF` ($16.2:1$) and `#17202A` on `#F5F6F8` ($15.0:1$) exceed the $4.5:1$ normal-text and $3.0:1$ large-text thresholds; semantic status colors (`#237A4B` on `#EAF5EF`, `#946200` on `#FDF6E7`, `#B42318` on `#FDECEC`) pair legible text with light tints.
- **No Color-Only Status:** Every semantic cell and badge displays explicit textual status (`OK`, `Connected`, `Disconnected`, `Compliant (<=4B)`, `Exceeds 4B`, `Completed`, `Shared TP`).
- **Keyboard Focus & Screen-Reader Metadata:** Visible `#2457A6` focus outlines across buttons, inputs, combos, and checkboxes; explicit `setAccessibleName()` attributes on interactive controls; `Qt.StrongFocus` on navigation sidebar; destructive confirmation dialogs on active run cancellation.

---

## 6. Verification & Visual Review Evidence

### 6.1. Automated Test & Build Results
1. **GUI Tests (`.venv/bin/python -m pytest 2_Tests/gui/ -v`):** Exit code `0` — **`8 passed in 3.45s`** (7 original tests + new `test_light_theme_palette_and_accessibility_tokens`).
2. **Source Headless Self-Test (`QT_QPA_PLATFORM=offscreen .venv/bin/python run_gui.py --self-test`):** Exit code `0` — `screens_verified: 10`, `postgresql_reachable: true`, `ollama_reachable: true`, `ollama_models_count: 8`, `datasets_discovered: 1`.
3. **Full Test Suite (`.venv/bin/python -m pytest 2_Tests/ -v`):** Exit code `0` — **`134 passed, 1 warning in 10.58s`** (zero failures across unit, integration, and GUI tests).
4. **Standalone PyInstaller Build (`.venv/bin/python -m PyInstaller --noconfirm --clean packaging/agent_om.spec`):** Exit code `0` (`dist/AgentOM/AgentOM`).
5. **Packaged Executable Self-Test (`QT_QPA_PLATFORM=offscreen ./dist/AgentOM/AgentOM --self-test`):** Exit code `0` — `is_frozen: true`, `screens_verified: 10`, `postgresql_reachable: true`, `ollama_reachable: true`.
6. **Integrity Checks:**
   - `output/` historical SHA-256 baseline: **`"identical": true`** (`30/30` files, `eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798`).
   - `original_repo/` reference files: **`14/14` exact SHA-256 matches**.
   - Protected database `agent_om_local`: unchanged row counts (`ontology_matching: 162`, `syntactic_matching: 162`, `lexical_matching: 206`, `semantic_matching: 258`).
   - Pre-revision GUI file inventory archived in `4_Temporary/cache/pre_gui_revision_file_inventory.json` (`30` files).

### 6.2. Visual Screenshot Inspection (`4_Temporary/charts/gui_screenshots/`)
Headless Qt `QWidget.grab()` screenshots were captured and inspected across all 10 tabs at standard (`1380x860`) and compact (`1100x720`) window sizes plus a representative `QMessageBox` dialog (`dialog_sample.png`):
- Initial screenshot inspection caught invisible unchecked `QCheckBox` boxes, vertical spinbox/input overlap on compact `Configuration` (`1100x720`), Matplotlib chart `160 DPI` overflow on `Evaluation`, mnemonic `&` stripping on two `QTabBar` titles, and horizontal table cramming on `Run History`.
- After fixing each item, re-captured screenshots (`tab01_dashboard.png`–`tab10_export.png`, `compact_tab03/04/07/08/09/10`, `dialog_sample.png`) confirmed crisp light-theme contrast, visible checkboxes, unclipped `Evaluation` charts, responsive `Configuration` scrolling at `1100x720`, and zero horizontal scrollbars on `Run History`.

---

## 7. Known Remaining Limitations

1. **Offscreen Rendering Environment:** Visual screenshot verification was executed using Qt's `offscreen` platform plugin on macOS rather than an interactive Windows 11 desktop display server; minor native font metric differences on Windows (`Segoe UI`) were accounted for via responsive layouts, `QScrollArea`, and `34px` minimum control heights.
2. **Qt Offscreen Font Alias Startup Notice:** During headless `offscreen` startup, Qt's platform plugin emits a benign one-line notice (`Populating font family aliases... Replace uses of missing font family "Sans Serif"`) prior to `apply_light_theme()` overriding the application font.
3. **Host Services Needed for Live Matching:** Interactive browsing of runs, comparisons, and charts works completely offline, while executing new live matching pipelines requires local PostgreSQL (`127.0.0.1:5432`) and local Ollama (`127.0.0.1:11434`).
