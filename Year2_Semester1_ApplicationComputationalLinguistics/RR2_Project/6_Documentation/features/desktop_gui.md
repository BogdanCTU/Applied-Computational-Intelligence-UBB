# Feature Documentation — PySide6 Desktop GUI (`src/gui/`)

## 1. Feature Purpose
The Desktop GUI provides an interactive, multi-tab **PySide6 (Qt 6)** scientific workbench for inspecting ontologies, validating local ≤4B Ollama models and PostgreSQL + `pgvector` databases, launching or replaying Agent-OM matching pipelines, comparing experimental metrics ($P$, $R$, $F_1$, MRR, Hits@$k$, latency), and reading project documentation offline. It also supports a headless `--self-test` mode for automated CI and standalone PyInstaller binary verification.

---

## 2. Input Data
- **User Controls & Configuration Selections:**
  - Active model profile selection (`local_4b_default`, `local_4b_baseline`, `local_4b_mxbai`, `local_4b_reasoner`, `local_qwen35_comparison`, `historical_8b`, `historical_12b`).
  - Similarity threshold $\tau \in [0.50, 0.99]$ and top-$k$ parameter.
  - Selected replication run manifest (`manifest.json`), comparison matrix (`phase5_17point_comparison.json`, `phase6_ablation_matrix.json`), or Markdown report (`6_Documentation/`).
- **CLI Flags:**
  - `--self-test`: Runs automated headless tab instantiation, service verification, and screenshot/log validation before exiting with code `0`.

---

## 3. Processing Steps
1. **Application Startup (`1_Source/gui/app.py`):**
   - Initializes `QApplication`, loads the dark/scientific Qt stylesheet (`1_Source/gui/styles/theme.py`), and resolves paths dynamically via `1_Source/gui/paths.py`.
2. **Service Layer Initialization (`1_Source/gui/services/`):**
   - `EnvironmentService` (`environment_service.py`), `DatabaseService` (`database_service.py`), and `OllamaService` (`ollama_service.py`): Probe Python `3.13`, PostgreSQL `127.0.0.1:5432` (`pgvector` status and row counts across `agent_om_local` and `agent_om_adapted`), and Ollama `127.0.0.1:11434` (installed models and exact GGUF parameter counts).
   - `ConfigurationService` (`configuration_service.py`): Manages the 7 model profiles and enforces the strict ≤4B ($4,000,000,000$) parameter ceiling.
   - `DatasetService` (`dataset_service.py`) & `PipelineInspectionService` (`pipeline_inspection_service.py`): Inspect extracted CMT and ConfOf ontology entities, candidates, and stage outputs.
   - `ExperimentRunnerService` (`experiment_runner_service.py`): Executes or replays Agent-OM matching runs on a background `QThread` (`1_Source/gui/workers/experiment_worker.py`) so the Qt event loop remains responsive.
   - `ExperimentHistoryService` (`experiment_history_service.py`), `EvaluationService` (`evaluation_service.py`), and `ArtifactComparisonService` (`artifact_comparison_service.py`): Load historical and Phase 5/6 replication run manifests, CSV predictions, comparison JSONs, and PNG charts.
   - `ReportGenerationService` (`report_generation_service.py`): Exports comparison reports and CSV summaries to `output/replication_runs/exports/` without modifying protected historical baseline files.
3. **Interactive Tab Views (`1_Source/gui/views/`):**
   - **Dashboard View (`dashboard_view.py`):** Project status cards, environment health indicators, and quick-launch controls.
   - **Environment View (`environment_view.py`):** Live verification of Python 3.13, PostgreSQL + `pgvector`, Ollama models, and the ≤4B parameter cap ($4,000,000,000$ ceiling).
   - **Configuration View (`configuration_view.py`) & Dataset View (`dataset_view.py`):** Profile selector, hyperparameter controls ($\tau$, $k$, prompt mode), and CMT–ConfOf ontology entity browser.
   - **Wizard View (`wizard_view.py`) & Inspector View (`inspector_view.py`):** Guided pipeline execution with live progress bar, stage-by-stage log streaming, and candidate inspection.
   - **Evaluation View (`evaluation_view.py`), Comparison View (`comparison_view.py`), & History View (`history_view.py`):** Interactive tables of all replication runs, TP/FP/FN breakdowns, 17-point multi-tier comparisons, and embedded scientific charts.
   - **Export View (`export_view.py`):** Reproducible run bundle and Markdown report exporter.

---

## 4. Output Data
- **Visual Analytics & Interactive Tables:** Rendered directly in the PySide6 desktop window.
- **Exported Run Bundles:** Saved to `output/replication_runs/exports/` when the user triggers an export.
- **Self-Test Verification Exit Code:** Returns exit code `0` with diagnostic confirmation when invoked with `--self-test`.

---

## 5. Main Implementation Files
- [`1_Source/gui/app.py`](../../1_Source/gui/app.py) — Entry point and `--self-test` harness.
- [`1_Source/gui/main_window.py`](../../1_Source/gui/main_window.py) — Main `QMainWindow` container and 10-tab navigation workspace.
- [`1_Source/gui/paths.py`](../../1_Source/gui/paths.py) — Dynamic path resolver for source and PyInstaller (`sys._MEIPASS`) frozen builds.
- [`1_Source/gui/services/`](../../1_Source/gui/services/) — `environment_service.py`, `ollama_service.py`, `database_service.py`, `configuration_service.py`, `dataset_service.py`, `pipeline_inspection_service.py`, `experiment_runner_service.py`, `experiment_history_service.py`, `evaluation_service.py`, `artifact_comparison_service.py`, `report_generation_service.py`.
- [`1_Source/gui/views/`](../../1_Source/gui/views/) — `dashboard_view.py`, `environment_view.py`, `dataset_view.py`, `configuration_view.py`, `wizard_view.py`, `inspector_view.py`, `evaluation_view.py`, `comparison_view.py`, `history_view.py`, `export_view.py`.
- [`packaging/agent_om.spec`](../../packaging/agent_om.spec) — PyInstaller standalone packaging specification.

---

## 6. Configuration Options
- `--self-test`: CLI flag for automated headless verification.
- `QT_QPA_PLATFORM=offscreen`: Standard Qt environment variable for headless CI / terminal testing.

---

## 7. Dependencies
- `PySide6` (`6.12.0`), `PySide6-Addons`, `PySide6-Essentials`, `shiboken6`.
- `matplotlib` (`3.11.2`) for chart rendering.

---

## 8. Relevant Tests
- [`2_Tests/gui/test_gui_services_and_views.py`](../../2_Tests/gui/test_gui_services_and_views.py) — End-to-end `pytest-qt` test suite covering `MainWindow`, all tab views, `EnvCheckService`, `ArtifactsService`, `ExportService`, and `--self-test` execution.

---

## 9. Known Limitations
- Running a live full-dataset LLM pipeline from the GUI requires local Ollama and PostgreSQL services to be active; however, browsing all historical and Phase 5/6 replication runs, alignment tables, and charts works completely offline.
