# Phase 1 Report — Isolated Upstream Baseline (`Agent-OM-Lite` on CMT–ConfOf)

**Date:** 2026-11-02  
**Phase Status:** COMPLETED  
**Experiment ID:** `phase1_cmt_confof_agent_om_lite_v1` (preceded by smoke verification `phase1_smoke_cmt_confof_4ent`)  
**Upstream Source Executed:** `original_repo/` (`HEAD` `89d0f967a466f17692768e5e570c29b35e5e77e3`, strictly read-only)  
**Isolated Database:** `postgresql://postgres@127.0.0.1:5432/agent_om_upstream` (`pgvector 0.8.7`, `vector(4096)`)  
**Output Directory:** `agent_om_local/output/replication_runs/phase1_cmt_confof_agent_om_lite_v1/`

---

## 1. Executive Summary

Phase 1 executed the unmodified upstream **Agent-OM** repository (`om_ontology_to_csv.py` → `om_csv_to_database.py` → `om_database_matching.py`) end-to-end on the full **162-entity OAEI Conference CMT–ConfOf** benchmark (`88` Source entities, `74` Target entities, `16` gold equivalence alignments) under the documented **Agent-OM-Lite** configuration (`llama3:8b` chat + `llama3:8b` `4096`-dim embeddings, `temperature=0.0`, `seed=42`, `top_k=1`, `top_p=1.0`, `repeat_penalty=1.0`).

- **Completion Status:** All 3 upstream scripts exited with return code `0` and **zero LLM JSON tool-router crashes** across **1,627 local Ollama LLM calls** (`341,648` total tokens) and **835 embedded text chunks** (`4096`-dim) in **`2,584.34 s` (`43.07 min`)**.
- **Headline Reproduction Result (`llm_with_agent` / `predict.csv`):**
  - **Executed Upstream `Agent-OM-Lite` (`HEAD` `89d0f967`):** `TP = 5`, `FP = 7`, `FN = 11` (`12` predicted) → **`Precision = 41.67%`, `Recall = 31.25%`, `F1 = 35.71%`**.
  - **Committed Upstream `Agent-OM-Lite` Reference (`result_csv/result-om-2025-test.csv`):** `TP = 4`, `FP = 3`, `FN = 12` (`7` predicted) → **`Precision = 57.14%`, `Recall = 25.00%`, `F1 = 34.78%`**.
  - **Net F1 Delta:** **`+0.93` percentage points** (`35.71%` vs `34.78%`). Our run recovered all 4 expected exact-name/core TPs (`Administrator`, `Author`, `Conference`, `Person`) plus `ProgramCommitteeMember ↔ Member_PC`, lifting recall by `+6.25` pp (`31.25%` vs `25.00%`).
- **Immutability & Isolation Proof:**
  - `original_repo/` SHA-256 manifest before and after execution: **`8,358` files, aggregate SHA-256 `afed3137d9905945c5167559b15ef62815c64220a0aa1038ea06893e97b7c7c0` (`original_repo_unchanged: true`)**.
  - Protected database `agent_om_local` row counts before and after execution: `ontology_matching = 162`, `syntactic_matching = 162`, `lexical_matching = 206`, `semantic_matching = 258` (`protected_agent_om_local_db_unchanged: true`).

---

## 2. Hermetic Isolation Architecture (`scripts/run_upstream_isolated.py`)

Because upstream `run_config.py`, `om_ontology_to_csv.py`, `om_csv_to_database.py`, and `om_database_matching.py` assume relative working-directory writes (`subgraph.ttl`, `subgraph_complex.ttl`, `agent.log`, `result.csv`, `time.csv`, `cost.csv`, `alignment/...`), import `ChatOpenAI`/`OpenAIEmbeddings` at module load time, and execute `DROP TABLE IF EXISTS` during vector ingestion, `agent_om_local/scripts/run_upstream_isolated.py` enforced six simultaneous isolation layers:

1. **Dedicated Upstream Virtual Environment (`agent_om_local/.venv_upstream`):** Python `3.11.9` with `78` pinned packages matching upstream (`langchain==0.3.27`, `langchain-community==0.3.31`, `langchain-ollama==0.2.3`, `numpy==1.26.4`, `pandas==2.0.3`, `rdflib==7.0.0`, `breame==0.1.2`, `psycopg2-binary==2.9.9`, `pgvector==0.1.8`) and zero PyTorch bloat.
2. **Working Directory & Bytecode Redirection:** Executed inside `output/replication_runs/phase1_cmt_confof_agent_om_lite_v1/` with `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPYCACHEPREFIX=<run_dir>/_pycache`.
3. **AST-Level `sys.meta_path` `run_config` Override (`sitecustomize.py`):** Replaced `llm` with `ChatOllama(model="llama3:8b", temperature=0.0, seed=42, top_p=1.0, top_k=1, repeat_penalty=1.0)` and `embeddings_service` with `OllamaEmbeddings(model="llama3:8b")` in memory prior to execution—eliminating any `ChatOpenAI` instantiation while leaving `original_repo/run_config.py` untouched on disk.
4. **Interpreter Audit Hook (`sys.addaudithook`):** Blocked at the CPython runtime boundary any write/delete/rename inside `original_repo/` or historical `agent_om_local/output/step*` paths, and blocked any non-loopback (`!= 127.0.0.1` / `::1`) socket connection.
5. **Isolated PostgreSQL Database (`agent_om_upstream`):** Hosted on portable PostgreSQL `16.15` (`127.0.0.1:5432`, `listen_addresses='127.0.0.1'`, `pgvector 0.8.7`).
6. **Loopback 4096-Dim `LlamaEmbeddingBridge` (`src/utils/llama_embed_bridge.py`):** Modern Ollama (`0.40.13`) rejects `/api/embed` on chat-templated `llama3:8b` unless instantiated without a chat template, and loading two copies of `llama3:8b` simultaneously exceeds 8 GB VRAM on the RTX 4060 Laptop GPU (`8,188 MiB`). `LlamaEmbeddingBridge` unloads the chat model before Stage 2 (`keep_alive=0`), serves genuine `4096`-dim `llama3:8b` (`365c0bd3c000a25d2f4bf7324dd7eb7b0202fb06b0395b65902cba298d12b188`) vectors over `127.0.0.1`, and unloads the embedding alias (`keep_alive=0`) before Stage 3 begins.

---

## 3. Verified Runtime, Telemetry, VRAM, and Hybrid Memory Statistics

### 3.1. Stage-by-Stage Execution Telemetry

| Upstream Script | Return Code | Wall-Clock Time (s) | LLM Calls | Prompt Tokens | Completion Tokens | Total Tokens | GPU VRAM Before → After |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `om_ontology_to_csv.py` | `0` | `1,592.18` | `866` | `125,658` | `73,864` | `199,522` | `941 MiB → 6,527 MiB` |
| `om_csv_to_database.py` | `0` | `122.52` | `1` (`init` router) + `835` embedded chunks | `112` | `24` | `136` | `6,527 MiB → 5,741 MiB` |
| `om_database_matching.py` | `0` | `866.71` | `760` | `109,273` | `32,717` | `141,990` | `1,082 MiB → 6,402 MiB` |
| **Total End-to-End** | **`0`** | **`2,584.34` (`43.07 min`)** | **`1,627`** | **`235,043`** | **`106,605`** | **`341,648`** | Peak `6,527 / 8,188 MiB` |

### 3.2. `agent_om_upstream` Hybrid Memory Snapshot (`vector(4096)`)

| PostgreSQL Table | Row Count | Verified `pgvector` Dimension | Notes |
| :--- | :---: | :---: | :--- |
| `ontology_matching` | `162` | — (Relational Text Table) | `88` Source (`CMT`) + `74` Target (`ConfOf`) entities |
| `syntactic_matching` | `162` | `4096` | `1` normalized identifier chunk per entity |
| `lexical_matching` | `358` | `4096` | 500-char chunks of `llama3:8b` lexical explanations |
| `semantic_matching` | `314` | `4096` | 500-char chunks of `llama3:8b` subgraph + BNode verbalizations (`"Information is not available."` stripped to `0` chunks) |

---

## 4. Six-Variant Alignment Comparison on CMT–ConfOf (`16` Gold Correspondences)

| Evaluation Variant | Executed Upstream `Agent-OM-Lite` (`HEAD` `89d0f967`)<br>`Pred (TP / FP / FN)` — `P / R / F1 (%)` | Committed `Agent-OM-Lite` (`result-om-2025-test.csv`)<br>`P / R / F1 (%)` | Committed `Agent-OM` GPT-4o (`result-reference.csv`)<br>`P / R / F1 (%)` |
| :--- | :---: | :---: | :---: |
| `1. source_no_validation` (`S→T` RRF top-1) | `47 (7 / 40 / 9)` — **`14.89 / 43.75 / 22.22`** | `6.33 / 31.25 / 10.53` | `17.07 / 43.75 / 24.56` |
| `2. source` (`S→T` validated) | `26 (7 / 19 / 9)` — **`26.92 / 43.75 / 33.33`** | `12.20 / 31.25 / 17.54` | `70.00 / 43.75 / 53.85` |
| `3. target_no_validation` (`T→S` RRF top-1) | `46 (7 / 39 / 9)` — **`15.22 / 43.75 / 22.58`** | `6.06 / 25.00 / 9.76` | `20.00 / 56.25 / 29.51` |
| `4. target` (`T→S` validated) | `27 (6 / 21 / 10)` — **`22.22 / 37.50 / 27.91`** | `12.50 / 25.00 / 16.67` | `54.55 / 37.50 / 44.44` |
| `5. no_validation` (Unvalidated Merger) | `21 (6 / 15 / 10)` — **`28.57 / 37.50 / 32.43`** | `14.29 / 25.00 / 18.18` | `35.29 / 37.50 / 36.36` |
| `6. llm_with_agent` (**Final `predict.csv`**) | `12 (5 / 7 / 11)` — **`41.67 / 31.25 / 35.71`** | **`57.14 / 25.00 / 34.78`** | **`66.67 / 37.50 / 48.00`** *(HEAD CSV: `75.00 / 37.50 / 50.00`)* |

### Pair-Level Inspection of Final `llm_with_agent` (`predict.csv`)
- **True Positives (`5`):**
  1. `http://cmt#Administrator` ↔ `http://confOf#Administrator`
  2. `http://cmt#Author` ↔ `http://confOf#Author`
  3. `http://cmt#Conference` ↔ `http://confOf#Conference`
  4. `http://cmt#Person` ↔ `http://confOf#Person`
  5. `http://cmt#ProgramCommitteeMember` ↔ `http://confOf#Member_PC`
- **False Positives (`7`):**
  - Lexical/syntactic false friends passed via exact-name bypass (`Paper ↔ Paper`, `writtenBy ↔ writtenBy`) plus overly permissive `llama3:8b` `"yes"` validations on structurally proximate conference properties (`PaperFullVersion ↔ Regular`, `acceptPaper ↔ writes`, `assignedTo ↔ hasHomePage`, `maxPapers ↔ maxChoice`, `paperAssignmentFinalizedBy ↔ hasAdministrativeEvent`).
- **Root Cause of `+0.93%` F1 / `+6.25%` Recall Shift vs `result-om-2025-test.csv`:**
  1. **Upstream Code Evolution (`v1.0.1` → `v1.0.2`/`HEAD`):** `HEAD` expands `lexical()` from 2 to 10 predicates, adds blank-node OWL restriction verbalization (`expand_bnode_closure_named()`) in `semantic()`, and replaces the broken `enchant`/`hunspell` spellchecker with `breame 0.1.2`. These richer semantic verbalizations surface `ProgramCommitteeMember ↔ Member_PC` above the `0.90` `llama3:8b` cosine threshold in both directions (`TP = 5` vs `4`) and cut unvalidated directional false positives nearly in half (`47` vs `79` in `S→T`).
  2. **Decoder-Only `llama3:8b` Embedding Anisotropy:** Isotropic embedding models (`nomic-embed-text`) separate unrelated entities well below `0.90`, whereas uncalibrated decoder-only `llama3:8b` hidden states exhibit high baseline cosine similarity (`>0.90`) across verbose boilerplate descriptions, producing `47` (`S→T`) and `46` (`T→S`) candidates above `0.90` that `llama3:8b` validation only partially filters (`FP = 7`).

