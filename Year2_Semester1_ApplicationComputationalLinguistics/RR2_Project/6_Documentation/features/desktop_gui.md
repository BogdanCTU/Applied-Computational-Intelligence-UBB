# Feature Documentation — PySide6 Desktop GUI (`1_Source/gui/`)

## 1. Feature Purpose
The Desktop GUI provides an interactive, 10-screen **PySide6 (Qt 6)** scientific workbench with a unified light theme (`#F5F6F8` / `#FFFFFF` / `#EEF1F4`, `#2457A6` primary accent, `#17202A` primary text) for inspecting ontologies, verifying local PostgreSQL + `pgvector` and ≤4B Ollama models, running Agent-OM matching pipelines, inspecting intermediate outputs, comparing experiments, viewing evaluation charts, and exporting reproducible artifacts. It also supports headless `--self-test` verification for CI and standalone PyInstaller binary builds.

---

## 2. Input Data
- **User Controls & Configuration Selections:**
  - Active model profile selection (`local_4b_baseline`, `local_4b_optimized`, `local_4b_reasoning`, `local_adapted`, `upstream_lite_parity`, `experimental`, `upstream_product_reference`).
  - Matching parameters (`similarity_threshold`, `top_k`, `rrf_k`, `temperature`, `seed`, `tool_routing_mode`, `predicate_scope`, and parity checkboxes).
  - Selected OAEI benchmark or custom local ontology pair plus experiment run identifiers.
- **CLI Flags:**
  - `--self-test`: Runs headless offscreen verification across all 10 screens, PostgreSQL, Ollama, and dataset discovery, printing JSON diagnostics and exiting with code `0`.

---

## 3. Processing Steps
1. **Application Startup & Centralized Light Theme (`run_gui.py`, `1_Source/gui/styles/theme.py`):**
   - Initializes `QApplication`, applies the Fusion style, explicit light `QPalette`, system UI typography (`Segoe UI` on Windows, system font fallback elsewhere), and centralized QSS via `apply_light_theme()`.
   - Resolves workspace paths dynamically via `1_Source/gui/paths.py` across both Python source and frozen PyInstaller builds.
2. **Service Layer Initialization (`1_Source/gui/services/`):**
   - `EnvironmentService` (`environment_service.py`), `DatabaseService` (`database_service.py`), and `OllamaService` (`ollama_service.py`): Probe Python `3.13`, PostgreSQL `127.0.0.1:5432` (`pgvector` status and row counts across protected `agent_om_local` and isolated DBs), and Ollama `127.0.0.1:11434` (installed models and exact `/api/show` parameter counts).
   - `ConfigurationService` (`configuration_service.py`): Manages the 7 model profiles, enforces `agent_om_local` write protection and cloud read-only guards, and supports JSON preset import/export.
   - `DatasetService` (`dataset_service.py`) & `PipelineInspectionService` (`pipeline_inspection_service.py`): Inspect extracted CMT and ConfOf ontology entities, representations, similarity scores, and validation decisions.
   - `ExperimentRunnerService` (`experiment_runner_service.py`): Executes matching pipelines in a background `QThread` or isolated subprocess with DB mutex locking and cooperative cancellation.
   - `ExperimentHistoryService` (`experiment_history_service.py`), `EvaluationService` (`evaluation_service.py`), and `ArtifactComparisonService` (`artifact_comparison_service.py`): Load replication run manifests, compute 17-point intermediate comparisons, and generate Matplotlib figures.
   - `ReportGenerationService` (`report_generation_service.py`): Exports non-destructive timestamped bundles to `output/replication_runs/exports/` without modifying protected historical artifacts.
3. **Ten Interactive Workbench Screens (`1_Source/gui/views/`):**
   - **Dashboard (`dashboard_view.py`):** Service connection status panels, workflow quick actions, and CMT–ConfOf benchmark summary table.
   - **Environment (`environment_view.py`):** Runtime diagnostics, PostgreSQL database inspector + isolated DB provisioning, and Ollama `<=4B` model compliance table.
   - **Datasets (`dataset_view.py`):** Read-only OAEI benchmark loader and custom local ontology selector with entity/triple preview.
   - **Configuration (`configuration_view.py`):** Scrollable model profile selector, responsive hyperparameter grid, parity checkboxes, JSON presets, and configuration status validator.
   - **Run Pipeline (`wizard_view.py`):** Two-row execution controls (`Run Matching`, `Run Baseline`, `Cancel Run` with confirmation), progress bar, 14-stage pipeline status table, and live execution log.
   - **Inspector (`inspector_view.py`):** Searchable/sortable entity inspection table with tabs for Entity Representations, Retrieval and RRF Scores, and Validation Decisions.
   - **Comparison (`comparison_view.py`):** Automated pair-level classification table (`Shared TP`, `Shared FP`, `Missed by Both (FN)`, etc.) and 17-point JSON checkpoint comparison.
   - **Evaluation (`evaluation_view.py`):** Interactive Matplotlib figure tabs (`Precision, Recall & F1`, `Precision vs. Recall`, `Stage Attrition`, `Threshold Sensitivity`) and stage attrition table.
   - **Run History (`history_view.py`):** Execution status bar, live console output, full-width 9-column run history table, and JSON detail viewer.
   - **Export (`export_view.py`):** Export settings form and manifest log outputting CSV, JSON, RDF/XML, PNG charts, and Markdown reports.

---

## 4. Output Data
- **Interactive Tables, Status Panels, and Charts:** Rendered consistently in the light-themed Qt window (`1380x860` default, resizable down to `1024x680`).
- **Exported Run Bundles:** Written to `output/replication_runs/exports/`.
- **Self-Test Verification Output:** JSON diagnostics confirming `screens_verified: 10` and service reachability with exit code `0`.

---

## 5. Main Implementation Files
- [`run_gui.py`](../../run_gui.py) — Desktop GUI entry point and `--self-test` harness.
- [`1_Source/gui/main_window.py`](../../1_Source/gui/main_window.py) — Compact light header, 10-item left sidebar navigation, `QStackedWidget`, and status bar.
- [`1_Source/gui/styles/theme.py`](../../1_Source/gui/styles/theme.py) & [`check_white.svg`](../../1_Source/gui/styles/check_white.svg) — Centralized light color palette, Fusion `QPalette`, typography scale, and QSS design system.
- [`1_Source/gui/widgets/common.py`](../../1_Source/gui/widgets/common.py) — Standardized page headers, primary/secondary/destructive buttons, table configurator, accessible status items/labels, and user-friendly dialogs.
- [`1_Source/gui/paths.py`](../../1_Source/gui/paths.py) — Dynamic path resolver for source and PyInstaller (`sys._MEIPASS`) frozen builds.
- [`1_Source/gui/services/`](../../1_Source/gui/services/) — 11 GUI service modules (`environment_service.py`, `ollama_service.py`, `database_service.py`, `configuration_service.py`, `dataset_service.py`, `pipeline_inspection_service.py`, `experiment_runner_service.py`, `experiment_history_service.py`, `evaluation_service.py`, `artifact_comparison_service.py`, `report_generation_service.py`).
- [`1_Source/gui/views/`](../../1_Source/gui/views/) — All 10 view classes (`dashboard_view.py`, `environment_view.py`, `dataset_view.py`, `configuration_view.py`, `wizard_view.py`, `inspector_view.py`, `comparison_view.py`, `evaluation_view.py`, `history_view.py`, `export_view.py`).
- [`packaging/agent_om.spec`](../../packaging/agent_om.spec) — PyInstaller standalone `--onedir` packaging specification.

---

## 6. Configuration Options
- `--self-test`: CLI flag for automated headless verification.
- `QT_QPA_PLATFORM=offscreen`: Qt platform flag for headless CI / terminal execution.

---

## 7. Dependencies
- `PySide6` (`6.12.0`), `PySide6-Addons`, `PySide6-Essentials`, `shiboken6`.
- `matplotlib` (`3.11.2`) for embedded `FigureCanvasQTAgg` chart rendering.

---

## 8. Relevant Tests
- [`2_Tests/gui/test_gui_services_and_views.py`](../../2_Tests/gui/test_gui_services_and_views.py) — Automated `pytest-qt` test suite covering `MainWindow` navigation across all 10 screens, centralized light-theme `QPalette` tokens, all GUI services, database mutex locking, cooperative run cancellation, and export bundling.

---

## 9. Known Limitations
- Running a live ontology matching experiment from the GUI requires local PostgreSQL (`127.0.0.1:5432`) and local Ollama (`127.0.0.1:11434`) to be running; browsing existing runs, comparisons, and charts works offline.
- Automated screenshot inspection was conducted in headless Qt `offscreen` mode rather than a native Windows 11 desktop session.
