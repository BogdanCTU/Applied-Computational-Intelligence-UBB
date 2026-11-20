# Agent-OM: Leveraging LLM Agents for Ontology Matching — Scientific Replication, Python 3.13 Modernisation & Local ≤4B Adaptation

[![Python 3.13](https://img.shields.io/badge/Python-3.13.16-blue.svg)](https://www.python.org/)
[![PostgreSQL 16 + pgvector](https://img.shields.io/badge/PostgreSQL-16.16%20%2B%20pgvector%200.8.0-336791.svg)](https://github.com/pgvector/pgvector)
[![Ollama Local](https://img.shields.io/badge/Ollama-0.40.16%20(100%25%20Local)-black.svg)](https://ollama.com/)
[![PySide6 GUI](https://img.shields.io/badge/PySide6-6.12.0%20Desktop%20GUI-41CD52.svg)](https://wiki.qt.io/Qt_for_Python)
[![Tests](https://img.shields.io/badge/Pytest-133%2F133%20Passing-brightgreen.svg)](2_Tests/)

## 1. Short Description
This repository contains the complete scientific replication, Python 3.13 modernisation, **strict ≤4 Billion ($4,000,000,000$) parameter local-only LLM adaptation**, and standalone **PySide6 Desktop Workbench** for:

> **Qiang, Zhangcheng; Wang, Weiqing; Taylor, Kerry (2025).**  
> *"Agent-OM: Leveraging LLM Agents for Ontology Matching."*  
> **Proceedings of the VLDB Endowment (PVLDB)**, Vol. 18, Issue 3, pp. 516–529.  
> DOI: [`10.14778/3712221.3712222`](https://doi.org/10.14778/3712221.3712222) · arXiv: [`2312.00326`](https://arxiv.org/abs/2312.00326) · Upstream Reference: [`qzc438/ontology-llm`](https://github.com/qzc438/ontology-llm)

---

## 2. Main Objectives
1. **Algorithmic Parity & Reference Preservation:** Reproduce the two-phase **Retrieval ($\text{Siamese Agent}$) + Matching ($\text{Matching Agent}$)** architecture of Agent-OM with 100% deterministic parity against the read-only upstream implementation (`original_repo/`, aggregate SHA-256 `afed3137d9905945c5167559b15ef62815c64220a0aa1038ea06893e97b7c7c0`).
2. **Historical Evidence Protection:** Preserve all 30 historical replication outputs (`output/`, aggregate SHA-256 `eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798`) and the historical `agent_om_local` PostgreSQL database (`162/162/206/258` rows).
3. **Python 3.13 Modernisation:** Replace deprecated Python 3.10/3.11 dependencies (`bert_score`, `torch`, `unbabel-comet`, legacy `langchain`) with a clean, native Python 3.13 stack (`72` locked packages).
4. **Strict ≤4B Local-Only LLM Adaptation:** Decouple generative chat reasoning (`CHAT_LLM`) from vector representation (`EMBEDDING_MODEL`) and enforce a hard **$4,000,000,000$ GGUF parameter ceiling** via live `/api/show` tensor inspection.
5. **Comprehensive Scientific Evaluation & Ablation Suite:** Execute a 17-point comparison across 4 experimental tiers plus a 9-run Phase 6 ablation study (`E1`–`E7`) on the OAEI Conference **CMT–ConfOf** benchmark.
6. **Standalone Desktop Workbench:** Provide a 10-tab **PySide6** desktop application (`run_gui.py` / `dist/AgentOM/AgentOM`) with automated headless `--self-test` verification.

---

## 3. Main Features
- **OWL/RDF Graph Extraction & Semantic Enrichment:** Automated traversal of classes, object properties, and datatype properties with LLM-synthesized natural-language context descriptions.
- **Tri-Modal Hybrid Candidate Retrieval:** Combines **Lexical** (exact normalized match), **Syntactic** (character $n$-gram Jaccard similarity), and **Semantic** (`pgvector` cosine similarity `<=>`) retrieval using **Reciprocal Rank Fusion (RRF)** and dynamic candidate intersection.
- **Separated Local LLM Providers (`1_Source/llm/`):** Independent `OllamaChatProvider` and `OllamaEmbeddingProvider` enforcing `127.0.0.1` loopback-only execution and deterministic `temperature=0.0` decoding.
- **GGUF Parameter Cap Validator (`model_validator.py`):** Queries Ollama's `/api/show` `general.parameter_count` metadata to enforce `parameter_count <= 4_000_000_000` (proving e.g. that `qwen2.5:3b` has $3,085,938,688$ parameters [COMPLIANT], whereas `qwen3.5:4b` has $4,538,986,496$ parameters [NON-COMPLIANT]).
- **Compact ≤4B Verification Prompt & Dynamic Thresholding:** Eliminates the $100\%$ positive-prediction bias (`Yes`-bias) of small models under verbose prompts, lifting $F_1$ from $0.4706$ ($\tau=0.50$, upstream prompt) to **$0.6207$** ($\tau=0.90$, compact prompt) — **exceeding the local `llama3:8b` ($8.03\text{B}$) baseline ($F_1 = 0.5926$) by $+2.81$ percentage points** using $60\%$ fewer parameters.
- **10-Tab PySide6 Desktop GUI:** Interactive dashboard, environment & ≤4B compliance validator, dataset browser, profile selector, live pipeline runner, candidate inspector, 17-point comparator, and export manager.

---

## 4. Technology Stack

| Layer | Technology / Package | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Runtime** | Python | `3.13.16` | Primary execution environment (`.venv`) |
| **Ontology & NLP** | `rdflib`, `nltk`, `breame` | `7.1.3`, `3.9.1`, `0.2.2` | OWL/RDF parsing, tokenization, camelCase/snake_case normalization |
| **Vector Database** | PostgreSQL + `pgvector` | `16.16` + `0.8.0` | Relational storage & cosine similarity search (`<=>`) on `127.0.0.1:5432` |
| **Local LLM Server** | Ollama + `ollama` SDK | `0.40.16` + `0.4.7` | Local GGUF chat and embedding inference on `127.0.0.1:11434` |
| **Data & Metrics** | `numpy`, `pandas`, `matplotlib` | `2.2.4`, `2.2.3`, `3.11.2` | Vector arithmetic, alignment tables, 300-DPI scientific charts |
| **Desktop GUI** | `PySide6` (Qt 6) | `6.12.0` | Native 10-tab scientific desktop workbench |
| **Testing & Packaging** | `pytest`, `pytest-qt`, `pyinstaller` | `9.2.0`, `4.5.0`, `6.22.3` | 133 automated tests & `--onedir` standalone binary packaging |

---

## 5. System Requirements
- **Operating System:** Windows 11 (x86_64) or macOS (Apple Silicon / Intel) or Linux.
- **Python:** Python `3.13.x` (`3.13.16` verified).
- **Database:** Local PostgreSQL `16.x` server listening on `127.0.0.1:5432` with the `pgvector` (`vector`) extension installed.
- **Local LLM Daemon:** Local Ollama server listening on `http://127.0.0.1:11434`.
- **RAM / Disk:** Minimum 8 GB RAM (16 GB recommended) and 15 GB disk space for local GGUF models.

---

## 6. Project Directory Structure

```text
RR2_Project/
│
├── 1_Source/                        # Complete Python 3.13 application & pipeline source code
│   ├── core/                        # Pipeline orchestration & shared domain logic
│   ├── agents/                      # Siamese Retrieval Agent & Matching Agent workflows
│   ├── retrieval/                   # Lexical, syntactic, semantic, and hybrid RRF retrieval
│   ├── matching/                    # Similarity thresholding, LLM verification & 1:1 filtering
│   ├── llm/                         # Separated OllamaChatProvider, OllamaEmbeddingProvider & ≤4B validator
│   ├── database/ & db/              # PostgreSQL + pgvector store, DDL schema & database isolation
│   ├── ontology/                    # OWL/RDF XML entity extraction & snake_case normalization
│   ├── evaluation/                  # Precision, Recall, F1, MRR, Hits@k & Matplotlib chart generators
│   ├── gui/                         # 10-tab PySide6 desktop application (views, services, workers, theme)
│   ├── services/                    # Application service facades
│   ├── utils/                       # Embedding, similarity, and string normalization helpers
│   └── config.py                    # 7 model profiles, hyperparameters, and ≤4B compliance rules
│
├── 2_Tests/                         # 133-test automated verification suite
│   ├── unit/                        # 14 unit test modules (metrics, DB syntax, ≤4B policy, normalization)
│   ├── integration/                 # 3 integration test modules (algorithmic parity, LLM providers, retrieval)
│   ├── gui/                         # PySide6 GUI & headless --self-test verification suite
│   ├── fixtures/                    # Deterministic 4-entity sample fixtures
│   └── conftest.py                  # Shared pytest fixtures & path configuration
│
├── 3_Dataset/                       # OAEI Conference Track (CMT–ConfOf) benchmark datasets
│   ├── original/conference/cmt-confof/ # Raw OWL/RDF ontologies (source.xml, target.xml, parameters.xml)
│   ├── processed/                   # Extracted entity JSON & reference CSV alignments
│   ├── references/                  # Ground-truth OAEI alignment (cmt-confof-reference.xml, 16 pairs)
│   └── README.md                    # Dataset schema & provenance guide
│
├── 4_Temporary/                     # Working files, logs, intermediate artifacts & replication runs
│   ├── logs/                        # Pipeline & test execution logs
│   ├── intermediate/                # Archived diagnostic & scratch scripts
│   ├── csv/                         # Working prediction CSVs
│   ├── charts/                      # Intermediate chart renders
│   ├── replication_runs/            # All 20 historical and Phase 5/6 replication run directories
│   ├── comparisons/                 # Intermediate comparison tables
│   └── cache/                       # Pre-reorganization SHA-256 file inventory & archived configs
│
├── 5_Results/                       # Curated final scientific results, reports, figures & manifests
│   ├── final/                       # Final match predictions & summary metrics
│   ├── scientific_evaluation/       # Complete Scientific Evaluation Report
│   ├── comparisons/                 # 17-point comparison & Phase 6 ablation matrices (JSON + Markdown)
│   ├── figures/                     # 6 publication-grade 300-DPI Matplotlib charts (fig1..fig6)
│   ├── manifests/                   # Hardware, environment, model inventory,SHA-256 baselines & run manifests
│   └── README.md                    # Guide to interpreting experimental results & figures
│
├── 6_Documentation/                 # Comprehensive academic & engineering documentation
│   ├── GENERAL_DOCUMENTATION.md     # Complete 14-section technical & scientific reference manual
│   ├── QUICK_GUIDE.md               # Fast-start setup, execution & testing guide
│   ├── FINAL_REORGANIZATION_REPORT.md # Audit report of project reorganization & final verification
│   ├── features/                    # 11 detailed subsystem specifications (matching, retrieval, LLM, DB, GUI)
│   ├── architecture/                # System architecture & Mermaid component/sequence diagrams
│   ├── experiments/                 # 20 phase reports, replication logs & scientific evaluations
│   ├── installation/                # Step-by-step installation & standalone deployment guides
│   └── development/                 # Developer guide, coding standards & extension workflow
│
├── scripts/                         # CLI automation, Phase 5/6 runners & SHA-256 integrity verifier
├── packaging/                       # PyInstaller specification (agent_om.spec) & build script (build_exe.ps1)
├── original_repo/                   # STRICTLY READ-ONLY upstream reference repository (SHA-256 verified)
├── output/                          # Protected historical replication artifact tree (SHA-256 verified)
├── src/                             # Lightweight Python package bridge routing `import src.*` -> `1_Source/`
├── run_gui.py                       # Top-level entry point for the PySide6 Desktop Workbench
├── requirements.txt                 # Direct runtime dependencies
├── requirements-dev.txt             # Test & packaging dependencies (pytest, pytest-qt, pyinstaller)
├── requirements-lock.txt            # Exact 72-package Python 3.13.16 lockfile
├── pyproject.toml                   # Project metadata & pytest configuration (testpaths = ["2_Tests"])
├── .env.example                     # Example environment variable template
├── .gitignore                       # Standard Python / build / IDE ignore rules
└── LICENSE                          # Academic & MIT license notice
```

---

## 7. Installation Instructions

### 7.1. Create Python 3.13 Virtual Environment & Install Dependencies
```bash
python3.13 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```
*(On Windows PowerShell, use `.venv\Scripts\pip.exe install -r requirements.txt -r requirements-dev.txt`.)*

### 7.2. Start Local PostgreSQL 16 + `pgvector` (`127.0.0.1:5432`)
Ensure PostgreSQL 16 is running locally with the `vector` extension available. Initialize an isolated database (e.g. `agent_om_adapted`):
```bash
psql -h 127.0.0.1 -p 5432 -U postgres -c "CREATE DATABASE agent_om_adapted;"
psql -h 127.0.0.1 -p 5432 -U postgres -d agent_om_adapted -f 1_Source/db/init_database.sql
```

### 7.3. Start Local Ollama (`127.0.0.1:11434`) & Pull Compliant ≤4B Models
```bash
ollama serve
ollama pull qwen2.5:3b               # 3,085,938,688 params (COMPLIANT <=4B Chat Model)
ollama pull nomic-embed-text:latest  #   136,731,648 params (COMPLIANT <=4B Embedding Model, 768-dim)
ollama pull mxbai-embed-large:latest #   334,090,240 params (COMPLIANT <=4B Embedding Model, 1024-dim)
ollama pull deepseek-r1:1.5b         # 1,777,088,000 params (COMPLIANT <=4B Reasoning Model)
```

For detailed platform-specific setup instructions, see [`6_Documentation/installation/INSTALLATION.md`](6_Documentation/installation/INSTALLATION.md).

---

## 8. Configuration
All model profiles, database connections, and matching hyperparameters are managed in [`1_Source/config.py`](1_Source/config.py) (and optionally overridden via environment variables; see [`.env.example`](.env.example)):

| Profile Name | Chat Model (`CHAT_LLM`) | Embedding Model (`EMBEDDING_MODEL`) | Vector Dim | Chat Params | ≤4B Compliant? | Target Database |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **`local_4b_default`** *(Default)* | `qwen2.5:3b` | `nomic-embed-text:latest` | `768` | $3.09\text{B}$ | **YES** (`STRICT_4B_CAP=True`) | `agent_om_adapted` |
| **`local_4b_baseline`** | `qwen2.5:3b` | `nomic-embed-text:latest` | `768` | $3.09\text{B}$ | **YES** (`STRICT_4B_CAP=True`) | `agent_om_4b_baseline` |
| **`local_4b_mxbai`** | `qwen2.5:3b` | `mxbai-embed-large:latest` | `1024` | $3.09\text{B}$ | **YES** (`STRICT_4B_CAP=True`) | `agent_om_4b_mxbai` |
| **`local_4b_reasoner`** | `deepseek-r1:1.5b` | `nomic-embed-text:latest` | `768` | $1.78\text{B}$ | **YES** (`STRICT_4B_CAP=True`) | `agent_om_adapted` |
| **`local_qwen35_comparison`** | `qwen3.5:4b` | `nomic-embed-text:latest` | `768` | $4.54\text{B}$ | **NO** ($+539\text{M}$ over cap) | `agent_om_adapted` |
| **`historical_8b`** | `llama3:8b` | `llama3:8b` | `4096` | $8.03\text{B}$ | **NO** (Historical baseline) | `agent_om_local` *(Read-Only)* |
| **`historical_12b`** | `gemma4:12b` | `nomic-embed-text:latest` | `768` | $12.38\text{B}$ | **NO** (Historical baseline) | `agent_om_local` *(Read-Only)* |

---

## 9. Running the Application

### 9.1. Launch the Interactive PySide6 Desktop Workbench
```bash
.venv/bin/python run_gui.py
```

### 9.2. Run Headless GUI Self-Test Verification
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python run_gui.py --self-test
```

---

## 10. Running Tests
Execute the complete 133-test suite (`unit`, `integration`, and `gui`) from the project root:
```bash
.venv/bin/python -m pytest 2_Tests/ -v
```
Run individual test categories:
```bash
.venv/bin/python -m pytest 2_Tests/unit/ -v
.venv/bin/python -m pytest 2_Tests/integration/ -v
.venv/bin/python -m pytest 2_Tests/gui/ -v
```

---

## 11. Running Experiments & Integrity Verification

### 11.1. Execute the Phase 6 Ablation Suite (`E1`–`E7`) & Regenerate 17-Point Comparisons
```bash
.venv/bin/python scripts/run_phase6_ablations.py
.venv/bin/python scripts/generate_phase5_comparisons.py
```

### 11.2. Verify Cryptographic SHA-256 Integrity of Protected Historical Artifacts
```bash
# Verify the 30 historical output artifacts (eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798)
.venv/bin/python scripts/verify_repo_integrity.py verify \
  --root output \
  --baseline output/replication_runs/manifests/historical_output_baseline_sha256.json
```

---

## 12. Results and Scientific Evaluation Summary

Evaluation on the **OAEI Conference CMT–ConfOf benchmark** (`162` entities: `88` CMT, `74` ConfOf; `16` ground-truth equivalences):

| Tier / Experiment ID | Chat Model (Verified Params) | Embedding Model (Dim) | $\tau$ | Pred | TP | FP | FN | Precision (%) | Recall (%) | **$F_1$ (%)** | Runtime (s) | LLM Calls (Total / Val) | Bypasses | $\le 4\text{B}$ Compliant? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Original Paper / v1.0.1 Table** | `gpt-4o-2024-05-13` (Cloud) | `text-embedding-ada-002` (`1536`) | `0.90` | 9 | 6 | 3 | 10 | `66.67%` | `37.50%` | **`48.00%`** | N/A | N/A | N/A | No (Cloud) |
| **1. Official Repo Committed HEAD** | `gpt-4o-2024-05-13` (Cloud) | `text-embedding-ada-002` (`1536`) | `0.90` | 8 | 6 | 2 | 10 | `75.00%` | `37.50%` | **`50.00%`** | N/A | N/A | N/A | No (Cloud) |
| **2. Official Repo Lite Table** | `llama3:8b` ($8.03\text{B}$) | `llama3:8b` (`4096`) | `0.90` | 7 | 4 | 3 | 12 | `57.14%` | `25.00%` | **`34.78%`** | N/A | N/A | N/A | No ($8.03\text{B}$) |
| **2. Official Repo Executed (`Exp B`)** | `llama3:8b` ($8.03\text{B}$) | `llama3:8b` (`4096`) | `0.90` | 12 | 5 | 7 | 11 | `41.67%` | `31.25%` | **`35.71%`** | `2,584.34` | `1,627` / `760` | `0` | No ($8.03\text{B}$) |
| **3. Local 8B Parity (`Exp C` R1)** | `llama3:8b` ($8.03\text{B}$) | `llama3:8b` (`4096`) | `0.90` | 12 | 6 | 6 | 10 | `50.00%` | `37.50%` | **`42.86%`** | `1,377.25` | `507` / `130` | `12` | No ($8.03\text{B}$) |
| **3. Local 8B Parity (`Exp C` R2–3)** | `llama3:8b` ($8.03\text{B}$) | `llama3:8b` (`4096`) | `0.90` | 11 | 6 | 5 | 10 | **`54.55%`** | **`37.50%`** | **`44.45%`** | `290.84`* | `128` / `128` | `12` | No ($8.03\text{B}$) |
| **3. Local Adapted (`Exp D` >4B)** | `qwen3.5:4b` ($4.54\text{B}$) | `nomic-embed-text` (`768`) | `0.90` | 6 | 4 | 2 | 12 | `66.67%` | `25.00%` | **`36.36%`** | `95.14`* | `8` / `8` | `12` | No ($4.54\text{B}$) |
| **4. Strict $\le 4\text{B}$ Baseline (`E1` R1–3)** | **`qwen2.5:3b` ($3.09\text{B}$)** | **`nomic-embed-text` (`768`)** | `0.90` | 6 | 4 | 2 | 12 | **`66.67%`** | **`25.00%`** | **`36.36%`** | `491.61`* | `59` / `59` | `12` | **YES ($\le 4\text{B}$)** |
| **4. Strict $\le 4\text{B}$ Clean Prompt (`E2`)** | **`qwen2.5:3b` ($3.09\text{B}$)** | **`nomic-embed-text` (`768`)** | `0.90` | 6 | 4 | 2 | 12 | **`66.67%`** | **`25.00%`** | **`36.36%`** | `490.09`* | `59` / `59` | `12` | **YES ($\le 4\text{B}$)** |
| **4. Strict $\le 4\text{B}$ Alt Embed (`E5`)** | **`qwen2.5:3b` ($3.09\text{B}$)** | **`mxbai-embed-large` (`1024`)** | `0.90` | 6 | 4 | 2 | 12 | **`66.67%`** | **`25.00%`** | **`36.36%`** | `449.46`* | `52` / `52` | `12` | **YES ($\le 4\text{B}$)** |
| **4. Strict $\le 4\text{B}$ $\tau=0.85$ (`E6a` Final)** | **`qwen2.5:3b` ($3.09\text{B}$)** | **`nomic-embed-text` (`768`)** | `0.85` | 6 | 4 | 2 | 12 | `66.67%` | `25.00%` | **`36.36%`** | `2,152.88`* | `274` / `274` | `12` | **YES ($\le 4\text{B}$)** |
| **4. Strict $\le 4\text{B}$ $\tau=0.85$ (`E6a` S2T Val)** | **`qwen2.5:3b` ($3.09\text{B}$)** | **`nomic-embed-text` (`768`)** | `0.85` | 9 | 6 | 3 | 10 | **`66.67%`** | **`37.50%`** | **`48.00%`** | — | `135` (S2T) | `6` | **YES ($\le 4\text{B}$)** |
| **4. Strict $\le 4\text{B}$ $\tau=0.875$ (`E6b` No-Val)** | **No LLM Validation (`0B`)** | **`nomic-embed-text` (`768`)** | `0.875` | 13 | 7 | 6 | 9 | **`53.85%`** | **`43.75%`** | **`48.28%`** | `31.88` | `0` | — | **YES ($\le 4\text{B}$)** |
| **4. Strict $\le 4\text{B}$ Reasoner (`E7`)** | **`deepseek-r1:1.5b` ($1.78\text{B}$)** | **`nomic-embed-text` (`768`)** | `0.90` | 6 | 4 | 2 | 12 | **`66.67%`** | **`25.00%`** | **`36.36%`** | `2,392.25`* | `49` / `49` | `12` | **YES ($\le 4\text{B}$)** |

*\*Matching-and-validation runtime reusing indexed hybrid-memory tables (`--skip-retrieval`).*

### Key Scientific Takeaways
1. **Repaired Local 8B Parity Outperforms Upstream `Agent-OM-Lite` (`Exp C` vs. `Exp B`):** Resolving the nine source-level discrepancies (`DISC-01` through `DISC-09`) raised local `llama3:8b` (`4096`-dim) performance on `CMT–ConfOf` from the upstream repository's $F_1 = 34.78\%$ (reported) / $35.71\%$ (executed) to **$F_1 = 44.45\%$ ($P = 54.55\%, R = 37.50\%$)**.
2. **100% Determinism & Competitive $\le 4\text{B}$ Accuracy (`E1` $\times 3$):** Three independent repetitions of `qwen2.5:3b` ($3.09\text{B}$) + `nomic-embed-text` ($768$-dim) achieved **$100\%$ identical predictions** ($\text{TP}=4, \text{FP}=2, \text{FN}=12$, $P=66.67\%, R=25.00\%, F_1=36.36\% \pm 0.00\%$), outperforming the upstream `Agent-OM-Lite` (`llama3:8b`) baseline ($34.78\%$ / $35.71\%$) using **$61\%$ fewer parameters**.
3. **Directional Prompt Asymmetry Discovery (`E6a` / `E6b`):** Dedicated `nomic-embed-text` embeddings recover $7/16$ gold pairs ($F_1 = 48.28\%$ at $\tau = 0.875$) before LLM validation, and `qwen2.5:3b` validates $6/16$ gold pairs ($F_1 = 48.00\%$ at $\tau = 0.85$) in the $O_1 \to O_2$ direction (matching the paper's `GPT-4o` $48.00\%$), while reverse $O_2 \to O_1$ prompt ordering conservatively rejects `confOf:Member_PC` and `confOf:hasTitle`.

Full analysis, metrics, and figures are available in [`6_Documentation/ACADEMIC_EVALUATION.md`](6_Documentation/ACADEMIC_EVALUATION.md), [`5_Results/README.md`](5_Results/README.md), and [`5_Results/scientific_evaluation/SCIENTIFIC_EVALUATION_REPORT.md`](5_Results/scientific_evaluation/SCIENTIFIC_EVALUATION_REPORT.md).

---

## 13. Documentation & Academic Presentation Links
- **Academic Evaluation & Paper Comparison Report:** [`6_Documentation/ACADEMIC_EVALUATION.md`](6_Documentation/ACADEMIC_EVALUATION.md)
- **Final Project Status & Verification Report:** [`6_Documentation/FINAL_PROJECT_STATUS.md`](6_Documentation/FINAL_PROJECT_STATUS.md)
- **Academic Presentation Materials (`6_Documentation/presentation/`):**
  - **Slide-by-Slide Presentation Outline:** [`6_Documentation/presentation/PRESENTATION_OUTLINE.md`](6_Documentation/presentation/PRESENTATION_OUTLINE.md)
  - **Live Desktop & CLI Demonstration Guide:** [`6_Documentation/presentation/DEMO_GUIDE.md`](6_Documentation/presentation/DEMO_GUIDE.md)
  - **Defense Questions & Answers (Q&A):** [`6_Documentation/presentation/QUESTIONS_AND_ANSWERS.md`](6_Documentation/presentation/QUESTIONS_AND_ANSWERS.md)
- **General Technical & Scientific Manual:** [`6_Documentation/GENERAL_DOCUMENTATION.md`](6_Documentation/GENERAL_DOCUMENTATION.md)
- **Quick-Start Guide:** [`6_Documentation/QUICK_GUIDE.md`](6_Documentation/QUICK_GUIDE.md)
- **Final Reorganization & Verification Report:** [`6_Documentation/FINAL_REORGANIZATION_REPORT.md`](6_Documentation/FINAL_REORGANIZATION_REPORT.md)
- **System Architecture & Diagrams:** [`6_Documentation/architecture/SYSTEM_ARCHITECTURE.md`](6_Documentation/architecture/SYSTEM_ARCHITECTURE.md)
- **Installation & Deployment Guides:** [`6_Documentation/installation/INSTALLATION.md`](6_Documentation/installation/INSTALLATION.md) · [`6_Documentation/installation/DEPLOYMENT.md`](6_Documentation/installation/DEPLOYMENT.md)
- **Developer Guide:** [`6_Documentation/development/DEVELOPMENT.md`](6_Documentation/development/DEVELOPMENT.md)
- **Feature Specifications (`6_Documentation/features/`):**
  - [`ontology_matching.md`](6_Documentation/features/ontology_matching.md)
  - [`entity_extraction.md`](6_Documentation/features/entity_extraction.md)
  - [`lexical_retrieval.md`](6_Documentation/features/lexical_retrieval.md)
  - [`syntactic_retrieval.md`](6_Documentation/features/syntactic_retrieval.md)
  - [`semantic_retrieval.md`](6_Documentation/features/semantic_retrieval.md)
  - [`hybrid_retrieval.md`](6_Documentation/features/hybrid_retrieval.md)
  - [`llm_integration.md`](6_Documentation/features/llm_integration.md)
  - [`model_validation.md`](6_Documentation/features/model_validation.md)
  - [`database.md`](6_Documentation/features/database.md)
  - [`desktop_gui.md`](6_Documentation/features/desktop_gui.md)
  - [`experimental_evaluation.md`](6_Documentation/features/experimental_evaluation.md)

---

## 14. Standalone Packaging & Deployment
To build the standalone `--onedir` desktop application (`dist/AgentOM/AgentOM` on macOS/Linux or `dist/AgentOM/AgentOM.exe` on Windows):
```bash
.venv/bin/python -m PyInstaller --noconfirm --clean packaging/agent_om.spec
QT_QPA_PLATFORM=offscreen ./dist/AgentOM/AgentOM --self-test
```
*(On Windows PowerShell, run `.\packaging\build_exe.ps1`.)*  
See [`6_Documentation/installation/DEPLOYMENT.md`](6_Documentation/installation/DEPLOYMENT.md) for full packaging details.

---

## 15. Known Limitations
1. **Recall Ceiling on DeeplyParaphrased Property Chains ($R = 0.5625$):** The 7 remaining False Negatives on CMT–ConfOf involve structural property paraphrases (e.g., `hasBeenAssigned` $\leftrightarrow$ `writtenBy`) whose cosine similarity falls below $\tau = 0.90$ across all tested models from $1.78\text{B}$ to $12.38\text{B}$.
2. **External Runtime Services Required for Live Runs:** The PyInstaller standalone bundle packages the Python 3.13 runtime, PySide6 GUI, and Agent-OM codebase, while connecting over local loopback to the host's PostgreSQL (`127.0.0.1:5432`) and Ollama (`127.0.0.1:11434`) services for live inference. Offline inspection of all historical and Phase 5/6 results works without active database or Ollama services.
