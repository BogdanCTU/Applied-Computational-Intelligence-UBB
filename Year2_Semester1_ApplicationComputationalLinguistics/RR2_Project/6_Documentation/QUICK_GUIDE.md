# Quick Guide — Agent-OM Local Replication Workbench

## 1. What the Application Does

Agent-OM is a local ontology matching system and PySide6 desktop application that aligns concepts and properties between two OWL/RDF ontologies using a two-agent architecture (**Retrieval Agent** and **Matching Agent**), local **Ollama** language and embedding models (`http://127.0.0.1:11434`), and **PostgreSQL + `pgvector`** (`127.0.0.1:5432`).

---

## 2. Installation

Ensure **Python 3.13**, **PostgreSQL 16 + `pgvector`**, and **Ollama** are installed locally. From the project root:

```bash
# 1. Create and activate the Python 3.13 virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# 2. Install core and desktop GUI dependencies
.venv/bin/pip install -r requirements-dev.txt

# 3. Pull required local <=4B chat and dedicated embedding models in Ollama
ollama pull nomic-embed-text
ollama pull mxbai-embed-large
ollama pull qwen2.5:3b
ollama pull deepseek-r1:1.5b
```

---

## 3. Configuration

Copy `.env.example` to `.env` if you wish to customize local ports or default models. By default, the application connects strictly to loopback services:
- **PostgreSQL:** `127.0.0.1:5432` (user `postgres`)
- **Ollama:** `http://127.0.0.1:11434`
- **Available Profiles:** `local_4b_baseline`, `local_4b_optimized`, `local_4b_reasoning`, `local_adapted`, `upstream_lite_parity`, `experimental`, and `upstream_product_reference` (read-only).

---

## 4. Starting the Desktop Application

```bash
# Launch the interactive 10-screen PySide6 desktop GUI from source:
.venv/bin/python run_gui.py

# Or run the automated headless 10-screen self-test:
.venv/bin/python run_gui.py --self-test

# Or run the standalone packaged application:
./dist/AgentOM/AgentOM
```

---

## 5. Running an Experiment from the Command Line

```bash
# Run a fast 4-entity integration experiment with verified <=4B qwen2.5:3b + nomic-embed-text:
.venv/bin/python scripts/run_local_replication.py \
  --experiment-id quick_demo_4ent \
  --profile local_4b_optimized \
  --max-entities 2 \
  --db-name agent_om_4b_smoke

# Run the complete Phase 6 <=4B scientific evaluation suite (E1-E7):
.venv/bin/python scripts/run_phase6_small_model_evaluation.py

# Regenerate the 17-point intermediate comparisons and 5 Matplotlib charts:
.venv/bin/python scripts/generate_replication_comparisons_and_charts.py \
  --upstream-id phase1_cmt_confof_agent_om_lite_v1 \
  --parity-ids phase5_expC_local_parity_run1 phase5_expC_local_parity_run2 phase5_expC_local_parity_run3 \
  --adapted-ids phase5_expD_local_adapted_run2
```

---

## 6. Executing Tests

```bash
# Run the complete 133-test suite (unit, integration, and GUI tests):
.venv/bin/python -m pytest 2_Tests/ -v

# Run only isolated unit tests (no database or Ollama server required):
.venv/bin/python -m pytest 2_Tests/unit/ -v

# Run live database and Ollama integration tests:
.venv/bin/python -m pytest 2_Tests/integration/ -v

# Run PySide6 GUI service and view tests:
.venv/bin/python -m pytest 2_Tests/gui/ -v
```

---

## 7. Where to Find Results

- **Validated Final Tables, Figures & Manifests:** `5_Results/` (`5_Results/final/`, `5_Results/scientific_evaluation/`, `5_Results/comparisons/`, `5_Results/figures/`, `5_Results/manifests/`).
- **Per-Run Intermediate Data & Logs:** `4_Temporary/replication_runs/` and `4_Temporary/csv/`.
- **Benchmark Datasets & Ground Truth:** `3_Dataset/`.
- **Detailed Documentation & Experimental Reports:** `6_Documentation/`.
