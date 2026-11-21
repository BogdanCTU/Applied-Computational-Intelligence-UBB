# Phase 0 Forensic Workspace Audit Report
## Agent-OM: Scientific Replication, Python 3.13 Modernisation, Local $\le 4\text{B}$ LLM Adaptation & Desktop Application

**Audit Date:** 2026-11-20T10:59:19+02:00  
**Auditor:** Principal Python Engineer, ML Research Engineer & Scientific Replication Researcher  
**Target Publication:** Qiang, Z., Wang, W., & Taylor, K. (2024). *Agent-OM: Leveraging LLM Agents for Ontology Matching*. PVLDB, Vol. 18, No. 3, pp. 516–529 (DOI: `10.14778/3712221.3712222`, arXiv:2312.00326).  
**Reference Repository:** `qzc438/ontology-llm` (Baseline SHA-256: `afed3137d9905945c5167559b15ef62815c64220a0aa1038ea06893e97b7c7c0`)  
**Current Workspace Root:** `/Users/stefanapopa/Documents/8) DOCUMENTE BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_ApplicationComputationalLinguistics/RR2_Project`  
**Generated Manifests:**
- `output/replication_runs/manifests/environment_manifest.json`
- `output/replication_runs/manifests/workspace_integrity_manifest.json`
- `output/replication_runs/manifests/dependency_audit.json`

---

## 1. Executive Summary & Forensic Delta vs. Historical Snapshot (`2026-11-15`)

The supplied historical audit (`1_Documents/2_Project/current_implementation_audit.md`, dated `2026-11-15`) was generated on a **Windows 11 (`x86_64`)** workstation (`E:\PERSONAL\GitHub\...`, previously `E:\_3_Master\...`). Today (`2026-11-20`), the project resides on a **macOS (`arm64`, Apple M4, 16 GB Unified Memory)** machine.

### Key Forensic Findings
1. **Host Platform Migration & Documentation Reorganization:**
   - The workspace is currently running on **macOS 27.0.1 (`Darwin 27.0.0 arm64`, Apple M4, 16 GB RAM)**.
   - The legacy `docs/` folder was relocated to `1_Documents/2_Project/` (18 markdown reports) and the reference paper was placed at `1_Documents/1_Paper/AgentOmPaper.pdf`.
   - Because `src/gui/paths.py` and several scripts resolve `project_root / "docs"`, path resolution must support both `1_Documents/2_Project/` and `docs/`.
2. **Virtual Environment Status (`.venv` vs `.venv_upstream`):**
   - Unlike the 2026-11-15 Windows snapshot (where `.venv` was completely absent), a fresh macOS Python 3.13.16 virtual environment (`.venv/`) was initialized today (`2026-11-20 10:40`) and populated with the 16 base packages from `requirements.txt` (`54` distributions total).
   - **Missing from `.venv/`:** `PySide6`, `matplotlib`, `pytest-qt`, and `pyinstaller` (which were listed in `requirements-py313.txt` on Windows but not in `requirements.txt`).
   - `.venv_upstream/` remains absent (excluded by `.gitignore` during workspace transfer).
3. **Historical Experiment Artifacts & Line-Ending Forensics:**
   - All **30 historical outputs** (`output/e1_predictions.csv` through `output/step7d1_*`) are present on disk.
   - Raw SHA-256 verification against `historical_output_baseline_sha256.json` initially reported a size difference on all 30 files because the files were converted from Windows `CRLF` (`\r\n`) to Unix `LF` (`\n`) during transfer.
   - **Forensic Proof of Integrity:** Normalizing `LF -> CRLF` across the 30 files reproduces the **exact historical aggregate SHA-256** (`eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798`) across `30/30` files (`100%` byte-for-byte content identity).
4. **Completed Replication Runs Preserved:**
   - `phase1_cmt_confof_agent_om_lite_v1` (162 entities, $P=41.67\%, R=31.25\%, F_1=35.71\%$) and `phase1_smoke_cmt_confof_4ent` are 100% intact, including full PostgreSQL table snapshots (`db_ontology_matching_snapshot.csv` [162 rows], `db_syntactic_matching_chunks.csv` [162 rows], `db_lexical_matching_chunks.csv` [206 rows], `db_semantic_matching_chunks.csv` [258 rows]) and `llm_telemetry.jsonl`.
   - `phase5_expC_local_parity_run1` ($F_1=42.86\%$), `run2` ($F_1=44.45\%$), `run3` ($F_1=44.45\%$), `phase5_expC_router_det_4ent`, and `phase5_expC_router_llm_4ent` are 100% intact, including `extracted_entities.json`, `candidates_s2t.json`, `candidates_t2s.json`, `validation_records.json`, and `stage_attrition.json`.
5. **Local Ollama Service & $\le 4\text{B}$ Parameter Audit Discovery:**
   - Local Ollama (`0.40.16`, `/usr/local/bin/ollama`) is **actively running and listening** on `http://127.0.0.1:11434`.
   - Two models are currently installed in `~/.ollama/models`:
     1. `qwen3.5:4b` (digest `7f3251fa6878...`, format `safetensors`, runner `mlx`, quantization `nvfp4`): **`general.parameter_count = 4,538,986,496` (`4.54B` parameters)**.
     2. `gemma4:12b` (digest `c7597fc90b86...`, format `safetensors`, runner `mlx`, quantization `nvfp4`): **`general.parameter_count = 12,382,568,756` (`12.38B` parameters)**.
   - **Critical Scientific Finding (Section 6.1 Compliance):** Although `qwen3.5:4b` carries a `:4b` tag, querying `/api/show` proves its actual total parameter count is **$4,538,986,496$ ($4.54\text{B}$)** (`details.parameter_size = "4.5B"`). Under the strict $\le 4,000,000,000$ ($4.0\text{B}$) rule (*"Never infer parameter count from the model tag alone"*), `qwen3.5:4b` exceeds $4.00 \times 10^9$ by $538.99\text{M}$ parameters! Furthermore, neither `llama3:8b`, `nomic-embed-text`, `mxbai-embed-large`, `phi4-mini`, nor `deepseek-r1:1.5b` / `qwen2.5:3b` / `llama3.2:3b` are currently pulled in `~/.ollama/models`.
6. **PostgreSQL & `pgvector` Status:**
   - Port `5432` is not listening. Neither `.pg/` nor `.pgdata/` exists in the workspace (excluded by `.gitignore`, and the previous `.pg` contained Windows x64 binaries anyway). Homebrew `postgresql@16` and `pgvector` are not currently installed on this macOS host.
   - However, the exact table contents of the protected `agent_om_local` / `agent_om_upstream` database (`162 / 162 / 206 / 258` rows) are preserved in `output/replication_runs/phase1_cmt_confof_agent_om_lite_v1/db_*.csv` and `phase5_expC_local_parity_run1/ontology_matching.csv`.
7. **Phase 3 Comparator Import Defect Already Repaired:**
   - The import defects noted in the historical audit (`src.matching.reciprocal_merger` and `src.retrieval.rrf`) were **already repaired** in Stage 2 (`scripts/generate_replication_comparisons_and_charts.py` lines 44–45 now import `from src.matching.merger import ReciprocalMerger` and `from src.retrieval.rank_fusion import reciprocal_rank_fusion`, and `ReciprocalMerger.merge = merge_alignments` is defined).
   - However, `generate_replication_comparisons_and_charts.py` still calls `_compute_threshold_sweep_on_db()` requiring a live PostgreSQL connection on `127.0.0.1:5432` and expects `phase5_expD_local_adapted_run1` to have a completed `run_summary.json`.

---

## 2. Detailed Forensic Investigation (8 Mandatory Questions)

### 2.1. Why the Previous Virtual Environments Are Missing
- **Historical Context:** On the Windows machine, `.venv/` and `.venv_upstream/` were excluded by the repository `.gitignore` and were not transferred when the workspace was copied.
- **Current State on macOS:**
  - `.venv/` **exists** (`created 2026-11-20 10:40`) using `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13` (`Python 3.13.16`, `arm64`). It has the base `requirements.txt` packages installed, but lacks `PySide6`, `matplotlib`, `pytest-qt`, and `pyinstaller`.
  - `.venv_upstream/` is **absent**. Because `.venv_upstream` was only used in Phase 1 to run `original_repo/` (`Agent-OM-Lite` baseline, which is already completed and preserved in `output/replication_runs/phase1_cmt_confof_agent_om_lite_v1/`), `.venv_upstream` is not needed unless re-running raw upstream code.

### 2.2. Whether PostgreSQL Binaries and Database Cluster Can Be Restored Safely
- **Current State:** `.pg/` and `.pgdata/` are absent from the workspace, and no PostgreSQL server is installed or listening on `127.0.0.1:5432`. Even if `.pg/` had been copied from Windows, its `.exe` binaries (`PostgreSQL 16.15, compiled by Visual C++ build 1944, 64-bit`) would not execute on macOS `arm64`.
- **Safe Recovery Path:**
  - Install local PostgreSQL 16 and `pgvector` natively via Homebrew (`brew install postgresql@16 pgvector`) or initialize an isolated local cluster at `.pgdata_local/` bound strictly to `127.0.0.1:5432`.
  - Reconstruct the protected `agent_om_local` database (`162 / 162 / 206 / 258` rows) from the committed CSV snapshots (`output/replication_runs/phase1_cmt_confof_agent_om_lite_v1/db_*.csv`) while keeping the `PROTECTED_DATABASES = frozenset({"agent_om_local"})` write-guard active in `src/db/database_manager.py`.
  - Create isolated experiment databases: `agent_om_parity`, `agent_om_adapted`, `agent_om_4b_baseline`, `agent_om_4b_optimized`, `agent_om_test`.

### 2.3. Whether the Ollama Model Directory Contains Any Verified $\le 4\text{B}$ Models
- **Active Service:** Ollama `0.40.16` is running at `http://127.0.0.1:11434`.
- **Installed Models in `~/.ollama/models`:**

| Model Tag | Digest | Format / Runner | Architecture | Exact `general.parameter_count` | Reported `parameter_size` | Strict $\le 4.0\text{B}$ ($4 \times 10^9$) Check |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `qwen3.5:4b` | `7f3251fa6878...` | `safetensors` / `mlx` (`nvfp4`) | `qwen3_5` | `4,538,986,496` | `4.5B` | **FAILS STRICT $4.0\text{B}$** ($4.54\text{B} > 4.00\text{B}$) |
| `gemma4:12b` | `c7597fc90b86...` | `safetensors` / `mlx` (`nvfp4`) | `gemma4_unified` | `12,382,568,756` | `12.4B` | **FAILS** ($12.38\text{B} > 4.00\text{B}$) |

- **Implications for Phase 3 & Phase 6:**
  - The Windows machine listed in the 2026-11-15 audit had `deepseek-r1:1.5b`, `gemma4:e4b`, `phi4-mini:latest`, and `qwen3.5:4b` in `E:\Applications\Ollama\Models`, whereas this macOS machine currently has only `qwen3.5:4b` (`4.54B`) and `gemma4:12b` (`12.38B`).
  - To satisfy strict $\le 4,000,000,000$ total parameters (`AC-06`) and separate embedding models (`AC-07`), we should pull verified $\le 4\text{B}$ chat models (e.g., `deepseek-r1:1.5b` [$\approx 1.78\text{B}$], `phi4-mini:latest` [$\approx 3.84\text{B}$], `llama3.2:3b` [$\approx 3.21\text{B}$], or `qwen2.5:3b` [$\approx 3.09\text{B}$]) and dedicated embedding models (`nomic-embed-text` [$137\text{M}$, $768$-dim] and `mxbai-embed-large` [$335\text{M}$, $1024$-dim]) via local `ollama pull`, and/or clarify whether `qwen3.5:4b` ($4.54\text{B}$) should be tested as a borderline $4\text{B}$-class model alongside a strictly $\le 4.00\text{B}$ model.

### 2.4. Completeness of `src/`, `tests/`, and GUI Implementation
- **`src/` (31 Python files):** 100% present and syntactically valid under Python 3.13.16:
  - `src/config.py`: Central `AppConfig` with 4 profiles (`upstream_product_reference`, `upstream_lite_parity`, `local_adapted`, `experimental`), loopback guards, cloud model guards, and `DEFAULT_EMBEDDING_DIMENSIONS`.
  - `src/agents/`: `retrieval_agent.py`, `matching_agent.py`, `tool_router.py`.
  - `src/db/`: `database_manager.py` (with `agent_om_local` `DROP TABLE` protection).
  - `src/evaluation/`: `metrics.py`, `comparator.py` (17-point comparator), `charts.py` (5 Matplotlib figure builders).
  - `src/gui/`: `main_window.py`, `paths.py`, `state.py`, 11 services in `src/gui/services/`, and 10 views in `src/gui/views/`, plus `run_gui.py` entrypoint with `--self-test`.
  - `src/matching/`: `merger.py` (`ReciprocalMerger`), `validator.py` (`LLMValidator`).
  - `src/ontology/`: `parser.py`, `entity_extractor.py`.
  - `src/retrieval/`: `syntactic_retriever.py`, `lexical_retriever.py`, `semantic_retriever.py`, `rank_fusion.py`.
  - `src/utils/`: `llama_embed_bridge.py`, `text_processing.py`.
- **`src/llm/` (Phase 3 Target):** Not yet created (`chat_provider.py`, `embedding_provider.py`, `model_registry.py`, `ollama_client.py`, `model_validator.py`).
- **`tests/` (17 test modules, 126 total tests):**
  - Excluding `test_gui_services_and_views.py` (awaiting `PySide6` installation in `.venv`), `119` tests collect cleanly: **`98` pass (`100%` of self-contained logic tests)**, `8` error due to PostgreSQL offline (`127.0.0.1:5432`), and `13` fail/error due to missing `original_repo/data/conference/cmt-confof/component/source.xml` and `target.xml`.

### 2.5. Integrity of Historical Experiment Outputs
- All 30 historical files in `output/` (`e1_predictions.csv` .. `step7d1_validation_decisions.csv`) are present.
- As proven in `workspace_integrity_manifest.json`, converting `LF -> CRLF` yields the exact baseline aggregate SHA-256 `eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798`. We can restore `CRLF` line endings on those 30 read-only files (or add line-ending-aware verification) so `scripts/verify_repo_integrity.py verify` returns `"identical": true` directly (`AC-19`).

### 2.6. Status of Comparator Import Defects
- **Already Fixed in Code:** `scripts/generate_replication_comparisons_and_charts.py` (lines 44–45) already imports `from src.matching.merger import ReciprocalMerger` and `from src.retrieval.rank_fusion import reciprocal_rank_fusion`.
- **Remaining Blockers in `generate_replication_comparisons_and_charts.py`:**
  1. Missing `matplotlib` and `PySide6` in `.venv` (needed because line 43 imports `PipelineInspectionService` from `src.gui.services`).
  2. `_compute_threshold_sweep_on_db()` queries live PostgreSQL databases (`agent_om_parity` and `agent_om_adapted`) on `127.0.0.1:5432`. If run offline or before `agent_om_adapted` is populated, it should fall back gracefully to the saved candidate JSON snapshots (`candidates_s2t.json`, `candidates_t2s.json`) and historical threshold sensitivity outputs (`step7a_threshold_sensitivity.csv`).
  3. Default `--adapted-runs` expects `phase5_expD_local_adapted_run1/run_summary.json`, which is currently incomplete.

### 2.7. Recoverability of Incomplete `phase5_expD_local_adapted_run1` & Missing `original_repo/` Raw Ontologies
- `output/replication_runs/phase5_expD_local_adapted_run1/` contains only `config_snapshot.json` (configured for `qwen3.5:9b` + `nomic-embed-text` `768`-dim) and `extracted_entities.json` (`88` CMT entities + `74` ConfOf entities = `162` entities, `90,400` bytes).
- **Crucial Recovery Capability:** Even though `original_repo/` is missing from the workspace, `extracted_entities.json` in `phase5_expC_local_parity_run1` and `phase5_expD_local_adapted_run1` contains the complete extracted entity definitions (URIs, labels, comments, properties, domains, ranges, types), `db_ontology_matching_snapshot.csv` contains the exact formatted syntactic/lexical/semantic texts for all 162 entities, and the 16 gold reference alignment pairs for CMT–ConfOf are recorded in `output/step5_correspondence_comparison.csv` and `phase1_cmt_confof_agent_om_lite_v1/run_summary.json`.
- In addition, `scripts/run_local_replication.py` already supports `--skip-retrieval --reuse-features-csv` (using `ontology_matching.csv` / `extracted_entities.json`) once PostgreSQL + Ollama are available!

### 2.8. Recoverability of PyInstaller Configuration
- `scripts/build_exe.ps1` is present and intact.
- `agent_om.spec` and `dist/` were excluded by `.gitignore`, so `agent_om.spec` needs to be re-created for PyInstaller `--onedir` packaging.
- *Platform Note:* PyInstaller builds native executables for the host OS (on macOS `arm64`, it builds `dist/AgentOM/AgentOM` / `AgentOM.app`; on Windows 11, it builds `dist/AgentOM/AgentOM.exe`). We can author a cross-platform `agent_om.spec` and verification script that works on macOS and Windows.

---

## 3. Classification of Discrepancies

| ID | Category | Item / Component | Observed State | Impact | Remediation Phase |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GAP-01** | **Missing Dependencies** | `PySide6`, `matplotlib`, `pytest-qt`, `pyinstaller` | Absent from macOS `.venv/` (`54` base packages installed) | Blocks GUI launch, `test_gui_services_and_views.py`, chart generation, and PyInstaller build | **Phase 1** |
| **GAP-02** | **Path Restructuring** | `docs/` moved to `1_Documents/2_Project/` | `src/gui/paths.py` hardcodes `docs_dir = project_root / "docs"` | GUI report exporter and documentation checks look in non-existent `docs/` | **Phase 0 / Phase 1** (Path resolver fallback) |
| **GAP-03** | **Line-Ending Drift** | 30 files in `output/` (`CRLF` $\rightarrow$ `LF`) | Content 100% identical, but byte sizes differ by line count | `verify_repo_integrity.py` reports `identical: false` unless `CRLF` is restored | **Phase 1** (Restore `CRLF` on the 30 read-only historical files) |
| **GAP-04** | **Environmental Problem** | PostgreSQL + `pgvector` offline (`127.0.0.1:5432`) | Not installed / not running on macOS host | Blocks 8 DB unit tests and live vector retrieval runs | **Phase 2** (`brew install postgresql@16 pgvector` + restore `agent_om_local` from snapshot) |
| **GAP-05** | **Model Inventory Gap** | Strict $\le 4\text{B}$ chat models & embedding models | Only `qwen3.5:4b` ($4.54\text{B}$) and `gemma4:12b` ($12.38\text{B}$) installed in Ollama | `qwen3.5:4b` exceeds strict $4.00\text{B}$ ($4.54\text{B}$); no dedicated embedding model (`nomic-embed-text`, `mxbai-embed-large`) or `llama3:8b` currently pulled | **Phase 2 & Phase 3** (`ollama pull` approved models) |
| **GAP-06** | **Missing Source Files** | `original_repo/` raw XML ontology files | `original_repo/` excluded by `.gitignore` during workspace migration | Blocks 15 pytest tests that load `original_repo/data/conference/cmt-confof/component/*.xml` | **Phase 2 / Phase 8** (Locate/restore `original_repo` or provide verified read-only fixture fallback) |
| **GAP-07** | **New Architecture** | `src/llm/` provider separation & $\le 4\text{B}$ profiles | Currently coupled inside `src/config.py` (`build_chat_llm`, `build_embeddings_service`) | Required for `AC-06`, `AC-07`, `AC-08` (`src/llm/chat_provider.py`, `embedding_provider.py`, `model_registry.py`, `ollama_client.py`, `model_validator.py`) | **Phase 3** |
| **GAP-08** | **Incomplete Experiment** | `phase5_expD_local_adapted_run1` | Aborted after `extracted_entities.json` | Blocks `AC-11` (Phase 3 comparisons) & `AC-12` (Phase 5 Exp D report) | **Phase 5** (Run new `phase5_expD_local_adapted_run2` preserving `run1`) |
| **GAP-09** | **Excluded Build Artifact**| `agent_om.spec` & `dist/AgentOM/` | Excluded by `.gitignore` | Blocks `AC-17` (PyInstaller standalone `--self-test`) | **Phase 9** |

---

## 4. Critical Risks & Mitigation Strategy

1. **Risk 1 — The `:4b` Tag Trap on `qwen3.5:4b` ($4.54\text{B}$ actual parameters):**
   - *Finding:* Ollama `/api/show` reports `general.parameter_count = 4,538,986,496` for `qwen3.5:4b`.
   - *Mitigation:* Implement `src/llm/model_validator.py` querying `/api/show` (`general.parameter_count`) at runtime. Pull a strictly $\le 4,000,000,000$ parameter model (such as `phi4-mini:latest` [$3.84\text{B}$], `llama3.2:3b` [$3.21\text{B}$], `qwen2.5:3b` [$3.09\text{B}$], or `deepseek-r1:1.5b` [$1.78\text{B}$]) for strict $\le 4.0\text{B}$ compliance, while optionally benchmarking `qwen3.5:4b` ($4.54\text{B}$) with an explicit metadata flag if desired.
2. **Risk 2 — Cross-Platform Environment (macOS Apple M4 vs. Windows 11 Spec):**
   - *Finding:* Current host is macOS `arm64` (Apple M4, 16 GB RAM), whereas historical runs were on Windows 11.
   - *Mitigation:* All Python 3.13 code, PySide6 GUI views, PostgreSQL + `pgvector`, Ollama API calls, and PyInstaller `--onedir` specs must use platform-agnostic `pathlib.Path` and support both macOS (`arm64`) and Windows (`win32`).
3. **Risk 3 — Missing `original_repo/` Raw XML Files:**
   - *Finding:* 15 unit tests and default CLI arguments reference `original_repo/data/conference/cmt-confof/component/{source,target,reference}.xml`.
   - *Mitigation:* Never fabricate fake ontologies. Check if the user can provide the read-only `original_repo/` folder (or OAEI `cmt.owl`/`confOf.owl`/`cmt-confOf.rdf` files), and enable `run_local_replication.py` to execute directly from the preserved `extracted_entities.json` / `db_ontology_matching_snapshot.csv` when raw XMLs are absent.

---

## 5. Prioritised Recovery & Implementation Plan

| Phase | Title | Key Actions | Estimated Compute / Time |
| :---: | :--- | :--- | :---: |
| **Phase 1** | **Python 3.13 Environment Recovery** | Install `PySide6`, `matplotlib`, `pytest-qt`, `pyinstaller` into `.venv/`; restore `CRLF` on the 30 historical `output/` files so `verify_repo_integrity.py` passes 100%; update `src/gui/paths.py` for `1_Documents/2_Project/`; generate `requirements-dev.txt`, `requirements-lock.txt`, ` PYTHON_313_COMPATIBILITY.md`, and `phase1_environment_recovery_report.md`. | ~2 mins (CPU/Network) |
| **Phase 2** | **Restore Local Database & Ollama Inventory** | Provision local PostgreSQL 16 + `pgvector` on `127.0.0.1:5432`; restore protected `agent_om_local` (`162/162/206/258` rows) from Phase 1 CSV snapshots; create isolated experiment DBs; pull required local Ollama models (`nomic-embed-text`, `mxbai-embed-large`, plus approved $\le 4\text{B}$ chat models); generate `ollama_model_inventory.json`. | ~5–10 mins (Download + DB init) |
| **Phase 3** | **Implement $\le 4\text{B}$ Local Model Architecture (`src/llm/`)** | Create `src/llm/{ollama_client.py, model_registry.py, model_validator.py, chat_provider.py, embedding_provider.py}` with strict `/api/show` parameter count verification ($\le 4 \times 10^9$), dynamic vector dimension validation, and add `local_4b_baseline`, `local_4b_optimized`, `local_4b_reasoning` profiles to `src/config.py`. | ~10 mins (Engineering + unit tests) |
| **Phase 4** | **Verify Algorithmic Parity** | Run full parity regression suite (`tests/test_algorithmic_parity.py`) against live local PostgreSQL; update `phase4_algorithmic_parity_report.md` confirming zero regression from `src/llm/` abstraction. | ~2 mins |
| **Phase 5** | **Complete Existing Experiments (Phase 3 Comparator & Exp D)** | Complete `phase5_expD_local_adapted_run2` (preserving incomplete `run1`); run `scripts/generate_replication_comparisons_and_charts.py` to generate `output/replication_runs/comparisons/` (17-point comparison JSON/CSV + 5 PNG charts); author `phase3_intermediate_comparison_report.md` and `phase5_experimental_reproduction_report.md`. | ~15–25 mins (162 entities on Apple M4 MLX/Metal) |
| **Phase 6** | **Scientific Evaluation of $\le 4\text{B}$ Models (`E1`–`E6` + 3x Repeatability)** | Run staged validation (1-entity smoke $\rightarrow$ 4-entity integration $\rightarrow$ full 162-entity `E1`–`E6` + 3 repeatability runs) using verified $\le 4\text{B}$ model(s); author `phase6_small_model_evaluation.md`. | ~45–75 mins total inference |
| **Phase 7–9** | **GUI Integration, Automated Testing (`pytest`) & PyInstaller Packaging** | Expose $\le 4\text{B}$ validator & new profiles in GUI; add unit/integration tests for `src/llm/`; run full `pytest tests -q`; author `agent_om.spec`, build standalone application in `dist/AgentOM/`, verify `--self-test`, update `USER_GUIDE.md` & `final_acceptance_report.md`. | ~10 mins |
| **Phase 10** | **Final Scientific Replication Report (21 Sections)** | Author comprehensive `final_replication_report.md` separating Paper vs. Upstream Repo vs. Local 8B Parity vs. Local $\le 4\text{B}$ Adaptation results. | ~15 mins |

---

## 6. Exact Next Commands (For Phase 1 Upon Approval)

```bash
# 1. Install missing GUI, chart, testing, and packaging wheels into Python 3.13 .venv
.venv/bin/pip install PySide6 matplotlib pytest-qt pyinstaller

# 2. Verify all 17 core imports individually
.venv/bin/python -c "import rdflib, breame, pandas, numpy, psycopg2, asyncpg, pgvector, ollama, langchain_core, langchain_ollama, langchain_text_splitters, dotenv, yaml, PySide6, matplotlib, pytest, pytestqt, PyInstaller; print('ALL_IMPORTS_OK')"

# 3. Export locked Python 3.13 dependency manifest
.venv/bin/pip freeze > requirements-lock.txt

# 4. Normalize LF -> CRLF on the 30 historical output files and verify exact aggregate SHA-256 (eb28e7a7...)
.venv/bin/python scripts/verify_repo_integrity.py verify --root output --baseline output/replication_runs/manifests/historical_output_baseline_sha256.json
```

---

## 7. Acceptance Criteria for Phase 1 (`Python 3.13 Environment Recovery`)

- **`AC-01` & `AC-02`:** `.venv` runs Python `3.13.16` with all 17 required packages (`rdflib`, `breame`, `pandas`, `numpy`, `psycopg2-binary`, `asyncpg`, `pgvector`, `ollama`, `langchain-core`, `langchain-ollama`, `langchain-text-splitters`, `python-dotenv`, `PyYAML`, `PySide6`, `matplotlib`, `pytest`, `pytest-qt`, `pyinstaller`) importing cleanly with zero errors.
- **`AC-19`:** `scripts/verify_repo_integrity.py verify --root output --baseline output/replication_runs/manifests/historical_output_baseline_sha256.json` returns `"identical": true` (`aggregate_sha256 = eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798`).
- **Deliverables Created:** `requirements-dev.txt`, `requirements-lock.txt`, `PYTHON_313_COMPATIBILITY.md`, and `phase1_environment_recovery_report.md`.
