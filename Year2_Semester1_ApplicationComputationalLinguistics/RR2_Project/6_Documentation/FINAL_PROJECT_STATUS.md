# Final Project Status & Academic Presentation Readiness Report — Agent-OM

**Project:** Agent-OM: Leveraging LLM Agents for Ontology Matching — Scientific Replication, Python 3.13 Modernisation, Local $\le 4\text{B}$ LLM Adaptation and Desktop Workbench  
**Date:** 2026-11-20  
**Workspace Root:** `/Users/stefanapopa/Documents/8) DOCUMENTE BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_ApplicationComputationalLinguistics/RR2_Project`

---

## 1. Executive Status Classification

In accordance with the academic evaluation policy, the project status is classified across the four required dimensions as follows:

| Dimension | Official Status Classification | Evidence & Justification |
| :--- | :---: | :--- |
| **1. Software Implementation** | **Software implementation complete** | Modular Python `3.13.16` codebase organized in [`1_Source/`](../1_Source/) (`core/`, `agents/`, `retrieval/`, `matching/`, `llm/`, `database/`, `db/`, `ontology/`, `evaluation/`, `gui/`, `services/`, `utils/`, `config.py`) with 10-screen PySide6 desktop workbench and 7 configuration profiles. |
| **2. Local Ollama $\le 4\text{B}$ Adaptation** | **Local Ollama adaptation complete** | Separated `LocalChatProvider` (`/api/chat`) and `LocalEmbeddingProvider` (`/api/embed`) in [`1_Source/llm/`](../1_Source/llm/) with live `/api/show` `general.parameter_count <= 4_000_000_000` enforcement (`qwen2.5:3b` [$3.09\text{B}$], `deepseek-r1:1.5b` [$1.78\text{B}$], `nomic-embed-text` [$768$-dim], `mxbai-embed-large` [$1024$-dim]). |
| **3. Scientific Reproduction Status** | **Partial scientific reproduction** | Complete architectural reproduction and deep multi-tier empirical evaluation (upstream `Exp B`, repaired 8B parity `Exp C` $\times 3$, adapted `Exp D`, and $\le 4\text{B}$ ablations `E1`–`E7`) on the **OAEI Conference (`CMT–ConfOf`)** benchmark (`162` entities, `16` gold equivalences). Classified as *Partial scientific reproduction* (rather than full paper replication) because the original paper's OAEI `Anatomy` and `MSE` dataset files are not present in the local workspace archive and proprietary cloud APIs (`GPT-4o`) were evaluated via committed reference files rather than re-invoked over the internet. |
| **4. Academic Presentation Readiness** | **READY FOR ACADEMIC PRESENTATION** | All software verifications (`133/133` tests), standalone executable self-test (`exit 0`), historical SHA-256 integrity checks (`identical: true`), [`ACADEMIC_EVALUATION.md`](ACADEMIC_EVALUATION.md), and presentation materials ([`PRESENTATION_OUTLINE.md`](presentation/PRESENTATION_OUTLINE.md), [`DEMO_GUIDE.md`](presentation/DEMO_GUIDE.md), [`QUESTIONS_AND_ANSWERS.md`](presentation/QUESTIONS_AND_ANSWERS.md)) are complete and verified. |

---

## 2. Independent Final Software Verification Log (Section 1 Results)

Every verification step was executed independently from the final project structure. Actual commands, exit codes, and outputs are recorded below:

| # | Verification Task | Command Executed | Actual Exit Code | Verified Output Summary |
| :-: | :--- | :--- | :---: | :--- |
| **1** | **Unit Test Suite** | `.venv/bin/python -m pytest 2_Tests/unit/ -v` | **`0`** | **`105 passed, 1 warning in 1.78s`** across all 14 unit test modules in `2_Tests/unit/`. |
| **2** | **Integration Test Suite (Live PostgreSQL + Ollama)** | `.venv/bin/python -m pytest 2_Tests/integration/ -v` | **`0`** | **`21 passed in 4.73s`** across `test_algorithmic_parity.py`, `test_llm_providers.py` (including live Ollama `/api/show` and `/api/embed` probes), and `test_retrieval_agent.py` (live PostgreSQL + `pgvector`). |
| **3** | **GUI Test Suite (`pytest-qt`)** | `.venv/bin/python -m pytest 2_Tests/gui/ -v` | **`0`** | **`7 passed in 4.11s`** verifying `ProjectPaths`, `EnvironmentService`, `DatasetService`, `ConfigurationService`, `DatabaseService`, `EvaluationService`, `ReportGenerationService`, and all 10 `MainWindow` screens. |
| **4** | **Rebuild PyInstaller Standalone Application** | `rm -rf build dist && .venv/bin/python -m PyInstaller --noconfirm --clean packaging/agent_om.spec` | **`0`** | **`Build complete!`** Built `--onedir` standalone bundle at `dist/AgentOM/AgentOM` (`macOS-27.0.1-arm64`, Python `3.13.16`, PyInstaller `6.22.3`). |
| **5** | **Standalone Application `--self-test`** | `QT_QPA_PLATFORM=offscreen ./dist/AgentOM/AgentOM --self-test` | **`0`** | `"is_frozen": true`, `"screens_verified": 10`, `"postgresql_reachable": true`, `"postgresql_version": "PostgreSQL 16.16 (Homebrew)"`, `"ollama_reachable": true`, `"ollama_models_count": 6`, `"datasets_discovered": 1`. |
| **6** | **Historical Output SHA-256 Integrity** | `.venv/bin/python scripts/verify_repo_integrity.py verify --root output --baseline output/replication_runs/manifests/historical_output_baseline_sha256.json` | **`0`** | **`"identical": true`** (`30/30` files, `baseline_aggregate_sha256` = `current_aggregate_sha256` = `eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798`, `modified_files: []`). |
| **7** | **Original Dataset & Reference Alignment SHA-256 Integrity** | Verified all 14 files in `original_repo/` and `3_Dataset/original/conference/cmt-confof/` against `original_repo_baseline_sha256.json` | **`0`** | **`14/14` exact SHA-256 matches** (`source.xml = e0d55ee6d176...`, `target.xml = e869c4e75c65...`, `reference.xml = 3e02f17a9770...`, `parameters.xml = 4d29a6038d35...`, `predict.csv = af112033d9b1...`, `ontology_matching.csv = 2bec24892c59...`). |
| **8** | **Documented Source GUI Command Verification** | `QT_QPA_PLATFORM=offscreen .venv/bin/python run_gui.py --self-test` | **`0`** | `"is_frozen": false`, `"screens_verified": 10`, `"postgresql_reachable": true`, `"ollama_reachable": true`, `"ollama_models_count": 6`, `"datasets_discovered": 1`. |

---

## 3. Automated Test & Packaging Status

- **Total Automated Tests:** **`133 / 133` Passing (`100.0%`)**
  - Unit tests (`2_Tests/unit/`): `105 / 105` passing
  - Integration tests (`2_Tests/integration/`): `21 / 21` passing
  - GUI tests (`2_Tests/gui/`): `7 / 7` passing
- **Packaging Status:**
  - PyInstaller spec: [`packaging/agent_om.spec`](../packaging/agent_om.spec)
  - Windows build script: [`packaging/build_exe.ps1`](../packaging/build_exe.ps1)
  - Compiled bundle: `dist/AgentOM/AgentOM` (verified outside the IDE with `QT_QPA_PLATFORM=offscreen ./dist/AgentOM/AgentOM --self-test`, exit code `0`).

---

## 4. Benchmark Coverage Summary

| OAEI Track in Original PVLDB Paper | Present in Local Workspace (`3_Dataset/` & `original_repo/`)? | Evaluated in Local Replication? | Status & Explanation |
| :--- | :---: | :---: | :--- |
| **1. OAEI Conference (`CMT–ConfOf`)** | **YES** (`source.xml`, `target.xml`, `reference.xml`, `162` entities, `16` gold equivalences) | **YES** (`20` replication runs across Tiers 2, 3, and 4) | **Fully Verified:** Evaluated across unmodified upstream (`Exp B`), repaired local 8B parity (`Exp C` $\times 3$), out-of-limit adapted (`Exp D`), and 10 strict $\le 4\text{B}$ runs (`Phase 6 E1–E7`). |
| **2. OAEI Anatomy (`mouse–human`)** | **NO** (Raw OWL/RDF ontology files absent from workspace archive) | **NO** | **Documented Limitation:** Code-IRI support (`o1_is_code`, `o2_is_code`, 11 anatomy/SKOS vocabulary exclusions) is implemented and unit-tested, but the dataset XML files are not included in the local archive. |
| **3. OAEI MSE (`MaterialInformation–MatOnto`)** | **NO** (Raw OWL/RDF ontology files absent from workspace archive) | **NO** | **Documented Limitation:** Not present in `original_repo/data/` or `3_Dataset/`; cannot be downloaded under strict offline/no-Git constraints. |

---

## 5. Known Limitations

1. **Single-Track Empirical Scope:** Empirical claims are bounded to the OAEI Conference `CMT–ConfOf` benchmark (`162` entities, `16` gold equivalences).
2. **Directional Prompt Asymmetry in Sub-4B Validators:** On `CMT–ConfOf`, `qwen2.5:3b` ($3.09\text{B}$) achieves $F_1 = 48.00\%$ (`TP=6, FP=3`) in $O_1 \to O_2$ validation at $\tau = 0.85$ (`E6a`), matching the paper's reported `GPT-4o` $F_1$ ($48.00\%$). However, the reverse $O_2 \to O_1$ prompt rejects two abbreviated/prefixed gold pairs (`confOf:Member_PC` $\to$ `cmt:ProgramCommitteeMember` and `confOf:hasTitle` $\to$ `cmt:title`), causing the symmetric Reciprocal Siamese Merger ($\mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$) to yield `TP=4, FP=2, FN=12` ($P = 66.67\%, R = 25.00\%, F_1 = 36.36\%$).
3. **Host Service Dependency for Live Runs:** Executing new live matching pipelines requires local PostgreSQL (`127.0.0.1:5432`) and local Ollama (`127.0.0.1:11434`) services to be running on the host machine. Inspecting existing runs, comparisons, and charts works completely offline.
