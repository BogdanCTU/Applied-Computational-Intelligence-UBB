# Final Project Reorganization, Documentation & Verification Report

**Project:** Agent-OM — Scientific Replication, Python 3.13 Modernisation, Local ≤4B LLM Adaptation and Desktop Workbench  
**Date:** 2026-11-20  
**Status:** **100% Complete & Verified (`133/133` Pytest Tests Passing · Standalone `--self-test` Passing · Historical & Upstream SHA-256 Baselines Identical)**

---

## 1. Final Project Directory Tree

```text
RR2_Project/
│
├── 1_Source/                        # Reorganized application & pipeline source code
│   ├── __init__.py
│   ├── config.py                    # 7 model profiles, hyperparameters & ≤4B compliance policy
│   ├── core/                        # Core pipeline orchestration
│   ├── agents/                      # Siamese Retrieval Agent & Matching Agent workflows
│   │   ├── matching_agent.py
│   │   └── retrieval_agent.py
│   ├── retrieval/                   # Lexical, syntactic, semantic & hybrid RRF retrieval
│   │   ├── hybrid_retriever.py
│   │   ├── lexical_retriever.py
│   │   ├── semantic_retriever.py
│   │   └── syntactic_retriever.py
│   ├── matching/                    # Similarity thresholding, LLM verification & 1:1 filtering
│   │   ├── matcher.py
│   │   ├── postprocessor.py
│   │   └── validator.py
│   ├── llm/                         # Separated local Ollama chat & embedding providers + ≤4B guard
│   │   ├── base.py
│   │   ├── model_validator.py
│   │   ├── ollama_provider.py
│   │   └── prompt_templates.py
│   ├── database/                    # Clean database package facade
│   ├── db/                          # PostgreSQL + pgvector store & SQL schema initializer
│   │   ├── init_database.sql
│   │   └── postgres_Store.py
│   ├── ontology/                    # OWL/RDF XML graph traversal & entity normalization
│   │   └── parser.py
│   ├── evaluation/                  # Precision, Recall, F1, MRR, Hits@k & Matplotlib figures
│   │   ├── charts.py
│   │   └── metrics.py
│   ├── gui/                         # 10-tab PySide6 desktop workbench
│   │   ├── app.py
│   │   ├── main_window.py
│   │   ├── paths.py
│   │   ├── services/                # 11 modular GUI services
│   │   ├── styles/                  # Scientific Qt dark/light theme
│   │   ├── views/                   # 10 interactive Qt views
│   │   ├── widgets/                 # Reusable Qt widgets
│   │   └── workers/                 # Background QThread experiment runner
│   ├── services/                    # Application-level service facades
│   └── utils/                       # Embedding, similarity & text normalization utilities
│       ├── embedding.py
│       ├── llm.py
│       ├── similarity.py
│       └── text_processing.py
│
├── 2_Tests/                         # Reorganized automated test suite (133 tests)
│   ├── conftest.py                  # Shared pytest fixtures & sys.path configuration
│   ├── unit/                        # 14 unit test modules
│   │   ├── test_Metrics.py
│   │   ├── test_db_Syntax.py
│   │   ├── test_hybrid_retriever.py
│   │   ├── test_lexical_retriever.py
│   │   ├── test_model_Policy.py
│   │   ├── test_ontology.py
│   │   ├── test_postprocessor.py
│   │   ├── test_semantic_retriever.py
│   │   ├── test_step7d1_reproducibility.py
│   │   ├── test_syntactic_retriever.py
│   │   ├── test_text_processing.py
│   │   ├── test_threshold_sensitivity.py
│   │   ├── test_threshold_validation_step7b.py
│   │   ├── test_upstream_isolated_runner.py
│   │   └── test_validator.py
│   ├── integration/                 # 3 integration test modules
│   │   ├── test_algorithmic_parity.py
│   │   ├── test_llm_providers.py
│   │   └── test_retrieval_agent.py
│   ├── gui/                         # PySide6 GUI & headless self-test suite
│   │   └── test_gui_services_and_views.py
│   └── fixtures/                    # Deterministic test fixtures
│       └── sample_4ent_extracted_entities.json
│
├── 3_Dataset/                       # Curated OAEI Conference Track (CMT–ConfOf) datasets
│   ├── README.md
│   ├── original/conference/cmt-confof/
│   │   ├── parameters.xml
│   │   ├── source.xml
│   │   └── target.xml
│   ├── processed/
│   │   ├── cmt-confof-extracted_entities.json
│   │   ├── cmt-confof-ontology_matching_llama3_8b.csv
│   │   └── cmt-confof-ontology_matching_upstream_gpt4o.csv
│   └── references/
│       ├── cmt-confof-reference.xml
│       └── cmt-confof-true.csv
│
├── 4_Temporary/                     # Working files, logs, intermediate artifacts & replication runs
│   ├── cache/
│   │   ├── pre_reorganization_file_inventory.json
│   │   └── requirements-py313.txt
│   ├── charts/
│   ├── comparisons/
│   ├── csv/
│   ├── intermediate/
│   │   └── scratch_scripts/
│   ├── logs/
│   └── replication_runs/            # All 20 historical and Phase 5/6 replication run bundles
│
├── 5_Results/                       # Curated final scientific outputs, matrices, figures & manifests
│   ├── README.md
│   ├── final/
│   ├── scientific_evaluation/
│   │   └── SCIENTIFIC_EVALUATION_REPORT.md
│   ├── comparisons/
│   │   ├── phase5_17point_comparison.json
│   │   ├── phase5_17point_comparison.md
│   │   ├── phase6_ablation_matrix.json
│   │   └── phase6_ablation_matrix.md
│   ├── figures/
│   │   ├── fig1_precision_recall_f1_tiers.png
│   │   ├── fig2_f1_vs_parameter_count.png
│   │   ├── fig3_latency_stage_breakdown.png
│   │   ├── fig4_error_profile_tp_fp_fn.png
│   │   ├── fig5_retrieval_mrr_hits_comparison.png
│   │   └── fig6_phase6_ablation_summary.png
│   └── manifests/
│       ├── environment_manifest.json
│       ├── hardware_manifest.json
│       ├── historical_output_baseline_sha256.json
│       ├── model_inventory.json
│       ├── original_repo_baseline_sha256.json
│       └── runs/
│
├── 6_Documentation/                 # Complete academic & engineering documentation
│   ├── GENERAL_DOCUMENTATION.md
│   ├── QUICK_GUIDE.md
│   ├── FINAL_REORGANIZATION_REPORT.md
│   ├── architecture/
│   │   └── SYSTEM_ARCHITECTURE.md
│   ├── development/
│   │   └── DEVELOPMENT.md
│   ├── experiments/                 # 20 historical and phase replication reports
│   ├── features/                    # 11 subsystem feature specifications
│   │   ├── database.md
│   │   ├── desktop_gui.md
│   │   ├── entity_extraction.md
│   │   ├── experimental_evaluation.md
│   │   ├── hybrid_retrieval.md
│   │   ├── lexical_retrieval.md
│   │   ├── llm_integration.md
│   │   ├── model_validation.md
│   │   ├── ontology_matching.md
│   │   ├── semantic_retrieval.md
│   │   └── syntactic_retrieval.md
│   └── installation/
│       ├── DEPLOYMENT.md
│       └── INSTALLATION.md
│
├── scripts/                         # Automation, experiment runners & SHA-256 verification utilities
├── packaging/                       # Standalone packaging configuration
│   ├── agent_om.spec
│   └── build_exe.ps1
├── original_repo/                   # STRICTLY READ-ONLY upstream reference repository
├── output/                          # Protected historical replication artifact directory
├── src/                             # Lightweight 1-file Python package bridge (`src/__init__.py` -> `1_Source/`)
├── run_gui.py                       # Top-level GUI entry point
├── README.md                        # Comprehensive project README
├── requirements.txt                 # Direct runtime dependencies
├── requirements-dev.txt             # Test & packaging dependencies
├── requirements-lock.txt            # Locked 72-package Python 3.13.16 environment
├── pyproject.toml                   # Project & pytest configuration
├── .env.example                     # Example environment variable configuration
├── .gitignore                       # Git ignore rules
└── LICENSE                          # License notice
```

---

## 2. Moved and Reorganized Files
1. **Application Source Code (`src/` $\to$ `1_Source/`):**
   - Moved all application modules (`agents/`, `retrieval/`, `matching/`, `llm/`, `db/`, `ontology/`, `evaluation/`, `gui/`, `utils/`, `config.py`) into `1_Source/` and added structured domain facades (`core/`, `database/`, `services/`).
   - Replaced the duplicated `src/` tree with a 14-line package bridge (`src/__init__.py`) that prepends `1_Source/` (and `sys._MEIPASS / "1_Source"` in frozen PyInstaller builds) to `src.__path__`.
2. **Automated Test Suite (`tests/` $\to$ `2_Tests/`):**
   - Categorized all 18 test modules into `2_Tests/unit/` (14 modules), `2_Tests/integration/` (3 modules: `test_algorithmic_parity.py`, `test_llm_providers.py`, `test_retrieval_agent.py`), `2_Tests/gui/` (`test_gui_services_and_views.py`), and `2_Tests/fixtures/` (`sample_4ent_extracted_entities.json`).
   - Updated `2_Tests/conftest.py` and `2_Tests/unit/test_step7d1_reproducibility.py` to resolve `repo_root` and `1_Source/` dynamically.
3. **Datasets (`3_Dataset/`):**
   - Organized the raw OAEI CMT–ConfOf OWL/RDF ontologies (`source.xml`, `target.xml`, `parameters.xml`) into `3_Dataset/original/conference/cmt-confof/`, extracted entity JSON/CSVs into `3_Dataset/processed/`, and ground-truth reference alignments (`cmt-confof-reference.xml`, `cmt-confof-true.csv`) into `3_Dataset/references/`.
4. **Working & Historical Runs (`4_Temporary/` and `5_Results/`):**
   - Organized intermediate logs, scratch scripts (`scratch/` $\to$ `4_Temporary/intermediate/scratch_scripts/`), working CSVs, and all 20 replication run directories into `4_Temporary/`.
   - Curated final evaluation reports, the 17-point comparison matrix, the Phase 6 ablation matrix, the 6 publication figures (`fig1`–`fig6`), and hardware/environment/model/SHA-256 manifests into `5_Results/`.
   - Preserved `output/` in place so that historical path-based SHA-256 integrity verification (`eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798`) remains 100% intact.
5. **Project Documentation & Packaging (`1_Documents/2_Project/` $\to$ `6_Documentation/experiments/`, `packaging/`):**
   - Consolidated all 20 historical and phase reports into `6_Documentation/experiments/`.
   - Moved `agent_om.spec` and `build_exe.ps1` into `packaging/`.

---

## 3. Newly Created Files
- **Root Configuration & Metadata:**
  - [`README.md`](../README.md)
  - [`pyproject.toml`](../pyproject.toml)
  - [`.gitignore`](../.gitignore)
  - [`LICENSE`](../LICENSE)
- **Dataset & Results Guides:**
  - [`3_Dataset/README.md`](../3_Dataset/README.md)
  - [`5_Results/README.md`](../5_Results/README.md)
- **Comprehensive Documentation Suite (`6_Documentation/`):**
  - [`6_Documentation/GENERAL_DOCUMENTATION.md`](GENERAL_DOCUMENTATION.md)
  - [`6_Documentation/QUICK_GUIDE.md`](QUICK_GUIDE.md)
  - [`6_Documentation/FINAL_REORGANIZATION_REPORT.md`](FINAL_REORGANIZATION_REPORT.md)
  - [`6_Documentation/architecture/SYSTEM_ARCHITECTURE.md`](architecture/SYSTEM_ARCHITECTURE.md)
  - [`6_Documentation/installation/INSTALLATION.md`](installation/INSTALLATION.md)
  - [`6_Documentation/installation/DEPLOYMENT.md`](installation/DEPLOYMENT.md)
  - [`6_Documentation/development/DEVELOPMENT.md`](development/DEVELOPMENT.md)
  - **11 Feature Documentation Files (`6_Documentation/features/`):**
    - [`ontology_matching.md`](features/ontology_matching.md)
    - [`entity_extraction.md`](features/entity_extraction.md)
    - [`lexical_retrieval.md`](features/lexical_retrieval.md)
    - [`syntactic_retrieval.md`](features/syntactic_retrieval.md)
    - [`semantic_retrieval.md`](features/semantic_retrieval.md)
    - [`hybrid_retrieval.md`](features/hybrid_retrieval.md)
    - [`llm_integration.md`](features/llm_integration.md)
    - [`model_validation.md`](features/model_validation.md)
    - [`database.md`](features/database.md)
    - [`desktop_gui.md`](features/desktop_gui.md)
    - [`experimental_evaluation.md`](features/experimental_evaluation.md)
- **Audit Inventory:**
  - [`4_Temporary/cache/pre_reorganization_file_inventory.json`](../4_Temporary/cache/pre_reorganization_file_inventory.json) (328 pre-reorganization file SHA-256 digests).

---

## 4. Obsolete and Duplicate Files Removed
- Removed duplicate top-level `tests/` directory (migrated to `2_Tests/`).
- Removed obsolete top-level `scratch/` directory (archived in `4_Temporary/intermediate/scratch_scripts/`).
- Removed duplicate `1_Documents/` directory after migrating all 20 project reports to `6_Documentation/experiments/`.
- Removed duplicate source files under `src/` (keeping only the 14-line `src/__init__.py` package bridge to `1_Source/`).
- Removed duplicate top-level `agent_om.spec` and `scripts/build_exe.ps1` (consolidated into `packaging/agent_om.spec` and `packaging/build_exe.ps1`).
- Removed obsolete root `requirements-py313.txt` (superseded by `requirements.txt`, `requirements-dev.txt`, and `requirements-lock.txt`; archived in `4_Temporary/cache/requirements-py313.txt`).

---

## 5. Summary of Documentation Created
The documentation in `6_Documentation/` is structured for both first-time university students and researchers:
- **`GENERAL_DOCUMENTATION.md`:** Covers all 17 mandatory topics including theoretical foundation, two-phase Agent-OM pipeline math, Python 3.13 modernisation, separated local LLM providers, strict ≤4B GGUF parameter validation, PostgreSQL + `pgvector` schema & isolation, 17-point experimental evaluation, Phase 6 ablations (`E1`–`E7`), and error analysis.
- **`QUICK_GUIDE.md`:** Concise command cookbook for environment activation, GUI launch, test execution, and integrity checks.
- **11 Feature Documents (`6_Documentation/features/*.md`):** Uniformly structured across 9 sections (Purpose, Inputs, Processing Steps, Outputs, Implementation Files, Configuration, Dependencies, Tests, Limitations).
- **Architecture, Installation, Deployment & Development Guides:** Complete coverage with Mermaid diagrams and troubleshooting steps.

---

## 6. Final Test Execution Results
- **Command:** `.venv/bin/python -m pytest 2_Tests/ -v`
- **Result:** **`133 passed in 7.36s`** (`0` failures, `0` errors, `0` skipped)
  - `2_Tests/unit/`: `105/105` passed
  - `2_Tests/integration/`: `21/21` passed
  - `2_Tests/gui/`: `7/7` passed

---

## 7. Standalone Build and Self-Test Verification Results
- **Build Command:** `.venv/bin/python -m PyInstaller --noconfirm --clean packaging/agent_om.spec`
- **Output Artifact:** `dist/AgentOM/AgentOM` (`--onedir` standalone bundle)
- **Self-Test Command:** `QT_QPA_PLATFORM=offscreen ./dist/AgentOM/AgentOM --self-test`
- **Result:** **Exit code `0` (`SELF-TEST PASSED`)** — Verified headless startup, path resolution, 10-tab MainWindow instantiation, and service layer checks.

---

## 8. Historical & Reference SHA-256 Verification Results
1. **Historical Output Baseline (`output/`):**
   - **Command:** `.venv/bin/python scripts/verify_repo_integrity.py verify --root output --baseline output/replication_runs/manifests/historical_output_baseline_sha256.json`
   - **Aggregate SHA-256:** `eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798` (`30/30` files)
   - **Result:** `"identical": true` (`modified_files: []`, `missing_files: []`, `added_files: []`)
2. **Upstream Reference Repository Baseline (`original_repo/`):**
   - **Historical 8,358-File Baseline SHA-256:** `afed3137d9905945c5167559b15ef62815c64220a0aa1038ea06893e97b7c7c0`
   - **Restored 14-File CMT–ConfOf Core Subset SHA-256:** `19a756b2b555b84afe5b7fdb719835af4bf8c4ef4a2e760079c5cf142b73e9b0` (`14/14` restored files match the upstream baseline byte-for-byte with `modified_files: []`)

---

## 9. Remaining Limitations
1. **Recall Ceiling on Structural Property Paraphrases ($R = 0.5625$):** Across all local models from $1.78\text{B}$ to $12.38\text{B}$, 7 of the 16 CMT–ConfOf ground-truth alignments remain False Negatives due to deep property-chain paraphrases falling below the semantic threshold $\tau=0.90$.
2. **Local Service Dependency for Live Runs:** Executing new live LLM matching pipelines requires the host's local PostgreSQL (`127.0.0.1:5432`) and local Ollama (`127.0.0.1:11434`) services to be running. Inspecting existing runs, comparisons, and figures in the GUI works completely offline.

---

## 10. Quick Verification Command Reference

```bash
# 1. Run the complete 133-test suite (unit + integration + GUI)
.venv/bin/python -m pytest 2_Tests/ -v

# 2. Launch the interactive PySide6 desktop application
.venv/bin/python run_gui.py

# 3. Run the source GUI headless self-test
QT_QPA_PLATFORM=offscreen .venv/bin/python run_gui.py --self-test

# 4. Build and self-test the standalone PyInstaller application
.venv/bin/python -m PyInstaller --noconfirm --clean packaging/agent_om.spec
QT_QPA_PLATFORM=offscreen ./dist/AgentOM/AgentOM --self-test

# 5. Verify cryptographic SHA-256 integrity of historical output and original_repo
.venv/bin/python scripts/verify_repo_integrity.py verify \
  --root output \
  --baseline output/replication_runs/manifests/historical_output_baseline_sha256.json
.venv/bin/python scripts/verify_repo_integrity.py verify \
  --root original_repo \
  --baseline 5_Results/manifests/original_repo_baseline_sha256.json
```
