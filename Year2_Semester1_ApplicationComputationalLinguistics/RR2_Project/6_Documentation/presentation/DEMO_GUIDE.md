# Live Demonstration Guide — Agent-OM Desktop Workbench & CLI

**Project:** Agent-OM — Scientific Replication, Python 3.13 Modernisation & Local $\le 4\text{B}$ LLM Adaptation  
**Target Demo Duration:** 5–7 Minutes  
**Working Directory:** Project Root (`RR2_Project/`)

---

## 1. Pre-Demo Checklist (1 Minute Before Presenting)

Open a terminal in the project root directory and run the quick health check below to confirm that PostgreSQL 16 + `pgvector`, local Ollama, and all 6 local models are active:

```bash
# 1. Verify historical output SHA-256 integrity (returns "identical": true)
.venv/bin/python scripts/verify_repo_integrity.py verify \
  --root output \
  --baseline output/replication_runs/manifests/historical_output_baseline_sha256.json

# 2. Run the headless standalone application self-test (verifies all 10 GUI screens, PostgreSQL, and Ollama)
QT_QPA_PLATFORM=offscreen ./dist/AgentOM/AgentOM --self-test
```

Expected self-test output:
```json
{
  "is_frozen": true,
  "screens_verified": 10,
  "postgresql_reachable": true,
  "postgresql_version": "PostgreSQL 16.16 (Homebrew)",
  "ollama_reachable": true,
  "ollama_models_count": 6,
  "datasets_discovered": 1
}
```

---

## 2. Launching the Interactive PySide6 Desktop Workbench

You can launch the GUI either from the Python 3.13 source environment or directly from the packaged PyInstaller standalone binary:

```bash
# Option A: Launch from Python 3.13 source environment
.venv/bin/python run_gui.py

# Option B: Launch the standalone PyInstaller executable
./dist/AgentOM/AgentOM
```
*(On Windows 11, run `.\dist\AgentOM\AgentOM.exe` or `.venv\Scripts\python.exe run_gui.py`.)*

---

## 3. Step-by-Step Interactive Walkthrough (10 Workbench Tabs)

### Step 1 — Tab 1 (`1. Dashboard`) & Tab 2 (`2. Environment Diagnostics`) (1 min)
1. Start on **Tab 1 (`1. Dashboard`)** to show the project summary, active profile indicator, and service health badges.
2. Switch to **Tab 2 (`2. Environment Diagnostics`)** and click **Refresh Environment Status**:
   - Point out **Python `3.13.16`**, **PostgreSQL `16.16` + `pgvector 0.8.0`** on `127.0.0.1:5432`, and **Ollama `0.40.16`** on `127.0.0.1:11434`.
   - Highlight the **Protected Database (`agent_om_local`)** row counts (`ontology_matching=162`, `syntactic_matching=162`, `lexical_matching=206`, `semantic_matching=258`) and its **Read-Only Protection Guard**.
   - Point out the **Live Ollama Model Table** showing exact `/api/show` `general.parameter_count` values:
     - `qwen2.5:3b`: **`3,085,938,688` params (`3.09B`) — COMPLIANT ($\le 4.0\text{B}$)**
     - `deepseek-r1:1.5b`: **`1,777,088,000` params (`1.78B`) — COMPLIANT ($\le 4.0\text{B}$)**
     - `nomic-embed-text:latest`: **`136,727,040` params (`768`-dim) — COMPLIANT**
     - `mxbai-embed-large:latest`: **`334,092,288` params (`1024`-dim) — COMPLIANT**
     - `qwen3.5:4b`: **`4,538,986,496` params (`4.54B`) — EXCLUDED ($>4.0\text{B}$ ceiling)**

### Step 2 — Tab 3 (`3. Dataset Manager`) & Tab 4 (`4. Configuration Profiles`) (1 min)
1. Click **Tab 3 (`3. Dataset Manager`)**:
   - Show the discovered OAEI Conference **`cmt-confof`** dataset (`88` Source CMT entities, `74` Target ConfOf entities, `16` Reference Equivalences).
2. Click **Tab 4 (`4. Configuration Profiles`)**:
   - Cycle through the 7 profiles (`upstream_product_reference`, `upstream_lite_parity`, `local_adapted`, `experimental`, `local_4b_baseline`, `local_4b_optimized`, `local_4b_reasoning`).
   - Select **`local_4b_optimized`** (`qwen2.5:3b` + `nomic-embed-text` `768`-dim, `similarity_threshold=0.90`, `top_k=3`, `enforce_4b_limit=True`).

### Step 3 — Tab 5 (`5. Replication Wizard`) — Running a Live Ontology Matching Experiment (2 min)
1. Switch to **Tab 5 (`5. Replication Wizard (14 Stages)`)**:
   - **For a fast 5-second live classroom demonstration (reusing indexed `agent_om_4b_baseline` embeddings on the 4-entity slice):**
     - Or run the CLI command live in a side terminal so the audience sees real-time stage progress:
       ```bash
       .venv/bin/python scripts/run_local_replication.py \
         --experiment-id demo_live_4ent_qwen25_3b \
         --profile local_4b_optimized \
         --db-name agent_om_4b_baseline \
         --skip-retrieval \
         --max-entities 4
       ```
   - **For a full 4-entity end-to-end run from raw OWL/RDF XML (including live LLM lexical/semantic verbalization, chunking, `pgvector` embedding into `agent_om_4b_smoke`, RRF, validation, and merging in ~60–90 seconds):**
     ```bash
     .venv/bin/python scripts/run_local_replication.py \
       --experiment-id demo_live_full_4ent \
       --profile local_4b_optimized \
       --db-name agent_om_4b_smoke \
       --max-entities 4
     ```
2. Observe the 7 pipeline stages complete deterministically and output `TP`, `FP`, `FN`, `Precision`, `Recall`, and `F1`.

### Step 4 — Tab 6 (`6. Pipeline Stage Inspector`) & Tab 7 (`7. Original vs Local Comparison`) (1.5 min)
1. Open **Tab 6 (`6. Pipeline Stage Inspector`)**:
   - Select any completed full 162-entity experiment (e.g., `phase5_expC_local_parity_run2` or `phase6_E1_qwen25_3b_baseline_run1`).
   - Inspect individual entities (such as `http://cmt#ProgramCommitteeMember` or `http://cmt#Author`), their 3 representations (`syntactic`, `lexical`, `semantic`), their top-3 `pgvector` cosine similarity scores, RRF score groups, and exact-name bypass vs. LLM validation decisions.
2. Open **Tab 7 (`7. Original vs Local Comparison`)**:
   - Inspect the **17-Point Intermediate Comparison Matrix** comparing Upstream `Agent-OM-Lite` (`Exp B`), Repaired Local 8B Parity (`Exp C`, $F_1 = 44.45\%$), and Local Adapted (`Exp D` / `Phase 6 E1`, $F_1 = 36.36\%$).

### Step 5 — Tab 8 (`8. Evaluation & Charts`), Tab 9 (`9. History`), & Tab 10 (`10. Export`) (1 min)
1. Open **Tab 8 (`8. Evaluation & Charts`)**:
   - Display the interactive Matplotlib charts (`Precision / Recall / F1 Comparison`, `Precision-Recall Iso-F1 Scatter`, `Runtime & LLM Call Breakdown`, `Stage Attrition`, and `Cosine Threshold Sensitivity`).
2. Open **Tab 10 (`10. Report & Artifact Export`)**:
   - Click **Export Full Reproducible Bundle** to export timestamped CSVs, JSON summaries, Markdown reports, and 200-DPI PNG charts into `output/replication_runs/exports/`.
