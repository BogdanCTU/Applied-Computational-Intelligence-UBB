# Phase 0 Audit Report — Project, Repository, and Environment Audit

**Date:** 2026-11-02  
**Project:** Agent-OM Guided Replication and Windows Desktop Application  
**Phase Status:** COMPLETED (Read-Only Audit; Zero Code/Database/Experiment Modifications)

---

## 1. Objective & Scope

Phase 0 establishes an empirical, read-only baseline of the workspace (`original_repo/` and `agent_om_local/`), verifies the local software and hardware environment (Python, PostgreSQL, `pgvector`, Ollama, and local model manifests), catalogs existing scripts, tests, outputs, and documentation from Steps 4–7D.1, identifies already-verifiable discrepancies between the upstream and local implementations, and defines a safe execution strategy for Phase 1 alongside a Windows desktop GUI architecture recommendation.

Every finding below explicitly distinguishes **Verified Facts** from **Assumptions / Items Requiring Runtime Verification**.

---

## 2. Repository Inventory & Lineage

### 2.1. Upstream Repository (`original_repo/` — Strictly Read-Only)
* **Verified Fact — Upstream Snapshot:** Tracks `https://github.com/qzc438/ontology-llm` at commit `89d0f967a466f17692768e5e370c29b35e5e77e3` (`2026-10-01`, *"OAEI 2026 submission - Update author version"*), with zero local modifications.
* **Verified Fact — Upstream Release Evolution:**
  * `v1.0.0` / `v1.0.1` (`46f0c72f`, `2025-04-19`): PVLDB 2025 reproducibility snapshot. Extracted 2 lexical predicates (`rdfs:comment`, `skos:definition`), had no blank-node closure expansion in `semantic()`, and used `enchant`/`hunspell` spelling helpers in `util.py`.
  * `v1.0.2` (`d9656fd0`, `2025-12-09`): OAEI 2025 update. Expanded `lexical()` to 10 annotation predicates, added `expand_bnode_closure_named()` to `semantic()` alongside the 18 structural predicates, updated `alignment/conference/cmt-confof/component/predict.csv`, and added `result_csv/result-om-2025-test.csv`.
  * `HEAD` (`89d0f967`, `2026-10-01`): Identical `om_ontology_to_csv.py`, `om_csv_to_database.py`, and `om_database_matching.py` logic to `v1.0.2`; replaced broken spellchecker normalization with word-level `breame` (`0.1.2`) in `util.cleaning()` (documented in `original_repo/CHANGES.md`), pinned LangChain `0.3.27` in `requirements.txt`, and added `web_app.py` and `web_overrides.py`.
* **Verified Fact — Core Upstream Pipeline Files:**
  * `run_config.py`: Top-level configuration and sequential subprocess driver (`om_ontology_to_csv.py` → `om_csv_to_database.py` → `om_database_matching.py`). Currently configured in source to `gpt-5`, `text-embedding-ada-002` (`1536`), and `dh/ironagedanube-pactols/component/`.
  * `util.py`: URI parsing (`uri_to_name`), syntactic cleaning (`cleaning`, `change_to_snake_case`, `repair_acronyms`, `change_phrase_british_to_american`), vocabulary exception filtering (`remove_exceptions`), and CSV metric/cost writers (`calculate_metrics`, `calculate_cost`).
  * `om_ontology_to_csv.py`: Retrieval Agent Part 1 (reference alignment extraction `find_reference`, entity extraction `find_all_entities`, and LLM JSON tool-routed `@tool` functions `syntactic`, `lexical`, `semantic`, `init`).
  * `om_csv_to_database.py`: Retrieval Agent Part 2 (`entity_id` formatting, `null_value_sentence` replacement with `""`, 500-char chunking via `RecursiveCharacterTextSplitter(separators=[".", "\n"])`, embedding batching, and destructive `DROP TABLE IF EXISTS` / `CREATE TABLE` on `ontology_matching`, `syntactic_matching`, `lexical_matching`, `semantic_matching`).
  * `om_database_matching.py`: Matching Agent (`entity_matching` cosine similarity SQL via `pgvector` `<=>`, RRF with `k=0` and lexicographical tie-breaking, score-group validation loop with exact-name bypass, LLM `validate` tool, and `merge` inner-join reciprocal intersection).
  * `web_overrides.py`: Import-hook launcher (`ONTOLOGY_WEB_OVERRIDES` + `sys.meta_path`) demonstrating how `run_config` attributes can be overridden in memory without editing `run_config.py`.
* **Verified Fact — Committed Upstream CMT–ConfOf Baselines:**
  * Ground truth (`data/conference/cmt-confof/component/reference.xml` & `alignment/conference/cmt-confof/component/true.csv`): **16** equivalence (`=`) correspondences between CMT (88 entities: 29 Classes, 59 Properties) and ConfOf (74 entities: 38 Classes, 36 Properties).
  * Committed `gpt-4o-2024-05-13` + `text-embedding-ada-002` artifacts (`alignment/conference/cmt-confof/component/`):
    * `ontology_matching.csv`: 162 rows (88 Source, 74 Target).
    * `predict.csv`: 8 pairs (`TP=6, FP=2, FN=10` → `P=75.00%, R=37.50%, F1=50.00%`).
    * `alignment/conference/result.csv` & `result_csv/result-reference.csv`: Reports `P=66.67%, R=37.50%, F1=48.00%` for `cmt-confof/component/llm_with_agent`.
  * Committed `Agent-OM-Lite` (`llama3:8b`) CMT–ConfOf benchmark entry (`result_csv/result-om-2025-test.csv`, lines 33–38):
    * `source_no_validation`: `P=6.33%, R=31.25%, F1=10.53%`
    * `source`: `P=12.20%, R=31.25%, F1=17.54%`
    * `target_no_validation`: `P=6.06%, R=25.00%, F1=9.76%`
    * `target`: `P=12.50%, R=25.00%, F1=16.67%`
    * `no_validation`: `P=14.29%, R=25.00%, F1=18.18%`
    * `llm_with_agent`: **`P=57.14%, R=25.00%, F1=34.78%`** (corresponds to `TP=4, FP=3, FN=12`, 7 predicted pairs).

### 2.2. Local Repository (`agent_om_local/`)
* **Core Modules (`src/`):**
  * `src/config.py` (`AppConfig`)
  * `src/utils/text_processing.py` (`uri_to_name`, `uri_to_prefix_name`, `repair_acronyms`, `change_to_snake_case`, `change_british_to_american`, `change_phrase_british_to_american`, `cleaning`)
  * `src/ontology/parser.py` (`OntologyGraph`, `OntologyParseError`, `load_ontology`)
  * `src/ontology/entity_extractor.py` (`EntityType`, `OntologyEntity`, `ExtractionSummary`, `EntityExtractor`)
  * `src/db/database_manager.py` (`DatabaseManager`)
  * `src/retrieval/syntactic_retriever.py` (`SyntacticRetriever`)
  * `src/retrieval/lexical_retriever.py` (`LexicalRetriever`)
  * `src/retrieval/semantic_retriever.py` (`SemanticRetriever`)
  * `src/retrieval/rank_fusion.py` (`reciprocal_rank_fusion`)
  * `src/agents/retrieval_agent.py` (`RetrievalAgent`)
  * `src/matching/validator.py` (`ValidationRecord`, `MatchingValidator`)
  * `src/matching/merger.py` (`ReciprocalMerger`)
  * `src/agents/matching_agent.py` (`DirectionalMatchResult`, `PipelineResult`, `MatchingAgent`)
* **Experiment & Infrastructure Scripts (`scripts/`):**
  * PostgreSQL lifecycle: `start_postgres.ps1`, `stop_postgres.ps1`
  * Step 5 retrieval audit: `run_retrieval_audit.py`
  * Step 6 core & ablation runner: `run_experiments_step6.py`, `compare_step6_results.py`, `inspect_e1_logs.py`
  * Step 7A threshold sensitivity: `run_threshold_sensitivity.py`
  * Step 7B τ=0.875 & validator loss audit: `run_step7b_investigation.py`
  * Step 7C reciprocal eligibility audit: `audit_reciprocal_eligibility.py`
  * Step 7D & 7D.1 prompt-order ablation & repeatability: `run_step7d_prompt_order_ablation.py`, `run_step7d1_reproducibility.py`
* **Automated Test Suite (`tests/`):** 14 pytest files (`test_ontology.py`, `test_text_processing.py`, `test_syntactic_retriever.py`, `test_lexical_retriever.py`, `test_semantic_retriever.py`, `test_rank_fusion.py`, `test_retrieval_agent.py`, `test_validator.py`, `test_merger.py`, `test_matching_agent.py`, `test_threshold_sensitivity.py`, `test_threshold_validation_step7b.py`, `test_prompt_order_ablation.py`, `test_step7d1_reproducibility.py`).
* **Historical Experimental Outputs (`output/`) & Documentation (`docs/`):**
  * 26 CSV/JSON result files (`e1`–`e7`, `step5_*`, `step6_*`, `step7a_*`, `step7b_*`, `step7c_*`, `step7d_*`, `step7d1_*`) and 6 markdown reports (`step4_corrections.md`, `step6_final_audit.md`, `step7b_threshold_validation_report.md`, `step7c_ablation_plan.md`, `step7d_prompt_order_report.md`, `step7d1_reproducibility_report.md`).
  * **Zero GUI files** exist yet.

---

## 3. Environment & Model Audit

| Subsystem | Verified Facts | Items Requiring Runtime Verification |
| :--- | :--- | :--- |
| **OS & Hardware** | Windows (`10.0.26300`), `15.24 GiB` RAM, **NVIDIA GeForce RTX 4060 Laptop GPU (`8,188 MiB` VRAM, Driver `621.01`)**. | Peak VRAM and latency when running `llama3:8b` 4096-dim embeddings + chat completions locally. |
| **Python Installations** | System Pythons: `3.11.9`, `3.12`, `3.13`. `agent_om_local/.venv` uses **Python `3.11.9`**. | None. |
| **Packages in `agent_om_local/.venv`** | `rdflib 7.6.0`, `breame 0.1.2`, `pandas 3.1.0`, `numpy 2.4.6`, `psycopg2-binary 2.9.13`, `asyncpg 0.32.0`, `pgvector 0.5.1`, `ollama 0.6.3`, `langchain-core 1.7.3`, `langchain-ollama 1.1.0`, `langchain-text-splitters 1.1.3`, `python-dotenv 1.2.4`, `pyyaml 6.0.3`, `pytest 9.2.0`, `tqdm 4.70.1`, `colorama 0.4.6`, stdlib `tkinter` (`Tcl/Tk 8.6`).<br>**Missing for GUI:** `PySide6`, `matplotlib`, `pyinstaller`.<br>**Incompatible with `original_repo`:** lacks `langchain==0.3.27` & `langchain_community==0.3.31` and uses `pandas 3.1` / `numpy 2.4` instead of upstream's `pandas==2.0.3` / `numpy==1.26.4`. | Installing `.venv_upstream` in Phase 1 and GUI dependencies in Phase 7 (upon approval). |
| **PostgreSQL + `pgvector`** | Portable **PostgreSQL `16.15`** in `agent_om_local/.pg/pgsql/bin/` with **`pgvector 0.8.7`** (`vector.dll`, `vector.control`, `vector--0.8.7.sql`) and cluster `agent_om_local/.pgdata` (`PG_VERSION = 16`). Server is currently **stopped** (`127.0.0.1:5432` not listening). | Starting PostgreSQL in Phase 1, verifying `agent_om_local` table counts (`162` entities), creating isolated `agent_om_upstream` DB, and verifying `vector(4096)` table writes. |
| **Ollama & Local Models** | **Ollama `0.40.13`** at `E:\_1_Applications\Ollama` (HTTP `127.0.0.1:11434` currently stopped; `OLLAMA_MODELS` unset in shell).<br>**Manifest store 1 (`E:\_1_Applications\Ollama\models\manifests`):** `qwen3.5:9b`, `nomic-embed-text:latest`, `bge-m3:latest`, `gemma4:12b`, `phi4-mini:latest`, `qwen2.5-coder:7b`.<br>**Manifest store 2 (`C:\Users\bctod\.ollama\models\manifests`):** `gemma4:12b`.<br>**Missing model:** **`llama3:8b` is NOT pulled in either store.** | Starting Ollama pointing to `E:\_1_Applications\Ollama\models`, recording exact model SHA digests, and pulling `llama3:8b` (requires approval). |

---

## 4. Completed vs. Missing Replication Phases

1. **Phase 0 — Project & Environment Audit:** **COMPLETED** (documented in this report and `IMPLEMENTATION_STATUS.md`).
2. **Phase 1 — Upstream Baseline:** **NOT STARTED** (`original_repo/` never executed locally; `.venv_upstream`, `agent_om_upstream` DB, `llama3:8b`, and non-invasive isolated launcher needed).
3. **Phase 2 — Source-Level Comparison:** **PARTIAL → TO BE FORMALIZED** (9 discrepancies identified in Phase 0; full 13-component traceable parity matrix pending in Phase 2).
4. **Phase 3 — Intermediate Output Comparison:** **PARTIAL → TO BE COMPLETED** (Steps 5–7D compared retrieval/validation downstream of upstream's `gpt-4o` CSV, but local `LexicalRetriever` and `SemanticRetriever` have never been run on the 162 CMT–ConfOf entities, nor compared under identical `llama3:8b` inputs).
5. **Phase 4 — Algorithmic Parity:** **PARTIAL → TO BE COMPLETED** (discrepancies `DISC-01`–`DISC-09` require non-destructive fixes, parity toggles, and regression tests).
6. **Phase 5 — Experimental Reproduction:** **PARTIAL → TO BE COMPLETED** (existing `qwen3.5:9b` + `nomic-embed-text` hybrid runs complete; end-to-end local runs and head-to-head `Agent-OM-Lite` `llama3:8b` baseline comparison pending).
7. **Phase 6 — Scientific Report:** **NOT STARTED** (step reports exist; unified scientific replication report pending).
8. **Phase 7 — Windows Desktop GUI & PyInstaller Packaging:** **NOT STARTED**.

---

## 5. Verified Discrepancies Already Identified (`DISC-01` to `DISC-09`)

1. **`DISC-01` — Hybrid Feature Origin in Steps 5–7D (`scripts/run_experiments_step6.py` lines 103–130):**
   * Local experiments loaded `original_repo/alignment/conference/cmt-confof/component/ontology_matching.csv` (generated upstream by `gpt-4o-2024-05-13`) into PostgreSQL rather than calling `RetrievalAgent.extract_representations_for_entities()`. Local lexical and semantic verbalization has never been executed end-to-end on CMT–ConfOf.
2. **`DISC-02` — Model, Sampling & Vector Dimension Configuration (`src/config.py` lines 38–53):**
   * Local uses `qwen3.5:9b` + `nomic-embed-text` (`768`-dim) without `seed=42`, `top_k=1`, or `repeat_penalty=1.0`. `AppConfig.embedding_dimensions` lacks `"llama3:8b": 4096` (defaulting unknown models to `768`).
3. **`DISC-03` — LLM JSON Tool-Router vs. Deterministic Python Calls (`om_*.py` vs. `src/agents/`):**
   * Upstream invokes an LLM JSON tool-router (`create_tool_use_agent` with `JsonOutputParser`) on every single `syntactic`, `lexical`, `semantic`, `validate`, `merge`, and `init` step (~975+ extra LLM calls on CMT–ConfOf, risking `KeyError`/`JSONDecodeError` on malformed JSON). Local agents invoke Python functions directly and reserve LLM calls strictly for lexical, semantic, and validation prompts.
4. **`DISC-04` — Empty/Null Semantic Embedding Defect (`src/db/database_manager.py` lines 108–110 vs. `om_csv_to_database.py` lines 40–41):**
   * Upstream replaces `"Information is not available."` with `""`, producing **0 chunks** in `semantic_matching` for isolated entities. Local `DatabaseManager.create_embedding_table()` re-inserts `"Information is not available."` when text is empty and embeds it—causing any two isolated entities across Source and Target to achieve a spurious **`1.000` cosine similarity** in `semantic_matching`. (Verified: `cmt-confof`'s committed `ontology_matching.csv` has 0 occurrences of `"Information is not available"`, so historical CMT–ConfOf runs were unaffected, but ontologies with isolated entities are vulnerable.)
5. **`DISC-05` — Missing `ontology_is_code` Label Lookup in `MatchingAgent` (`src/agents/matching_agent.py` lines 131, 144 vs. `om_database_matching.py` lines 297–303):**
   * Local `MatchingAgent.match_entity()` always uses `uri_to_name()` instead of resolving `rdfs:label` / `skos:prefLabel` when `o1_is_code` or `o2_is_code` is `True`. Equivalent on `cmt-confof` (`False`/`False`), but incorrect on code-IRI tracks (Anatomy, MultiFarm, DH, Bio-ML, Biodiv, MSE-3).
6. **`DISC-06` — Property Ordering & `entity_id` Prefix Indexing (`src/ontology/entity_extractor.py` lines 185–225 vs. `om_ontology_to_csv.py` lines 268–286):**
   * Upstream appends ObjectProperties and DatatypeProperties into a single list and sorts all properties alphabetically together (also retaining punned duplicates). Local `EntityExtractor` emits all sorted ObjectProperties followed by all sorted DatatypeProperties, altering numeric `entity_id` prefixes used in RRF lexicographical tie-breaking.
7. **`DISC-07` — Missing `reasoning=False` in Local Retrieval LLM Defaults (`src/retrieval/lexical_retriever.py` lines 73–77, `semantic_retriever.py` lines 75–79):**
   * Unlike `MatchingValidator._ensure_llm()`, neither `LexicalRetriever` nor `SemanticRetriever` passes `reasoning=False` when instantiating default `ChatOllama("qwen3.5:9b")`, which can trigger ~65s/call internal CoT tokens during retrieval.
8. **`DISC-08` — Minor Prompt Indentation, Annotation Set Sorting & Verbalization Joining:**
   * Upstream `validate()` has 28 leading spaces on lines 2–5 of its triple-quoted f-string; local `PROMPT_TEMPLATE` is left-aligned. Local `LexicalRetriever` sorts `extra_set` deterministically (upstream joins an unsorted `set`). Local `SemanticRetriever` strips and joins the two verbalizations with `"\n"` (upstream concatenates directly).
9. **`DISC-09` — `.env.example` Variable Mismatch & Non-Portable Hardcoded Test Paths:**
   * `.env.example` uses `DB_HOST`, `DB_NAME`, `DEFAULT_CHAT_MODEL`, `DEFAULT_EMBEDDING_MODEL`, whereas `src/config.py` reads `PGHOST`, `PGDATABASE`, `AGENT_OM_LLM`, `AGENT_OM_EMBEDDING` without calling `load_dotenv()`.
   * `tests/test_ontology.py` (line 11), `tests/test_semantic_retriever.py` (line 13), and `tests/test_syntactic_retriever.py` (line 11) hardcode `E:\_3_Master\_9_ACL_Project\original_repo\...` rather than resolving relative to `RR2_Project`.

---

## 6. Recommended Isolated Baseline Execution Strategy

1. **Read-Only Integrity Verification Without Git:**
   * Per project rules (**no Git commands under any circumstances**), `original_repo/` integrity will be verified before and after every upstream run by computing a read-only SHA-256 file manifest (file count, byte sizes, and SHA-256 digests of tracked files in `original_repo/`) stored in `agent_om_local/output/upstream_runs/`.
2. **Working-Directory & Import-Hook Isolation (`run_upstream_isolated.py`):**
   * Upstream scripts write `subgraph.ttl`, `subgraph_complex.ttl`, `agent.log`, `time.csv`, `result.csv`, `cost.csv`, and `alignment/...` relative to CWD, and `run_config.py` fails on import if `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is `None`.
   * A dedicated wrapper `agent_om_local/scripts/run_upstream_isolated.py` will run with `cwd = agent_om_local/output/upstream_runs/<run_id>/`, add `original_repo/` to `PYTHONPATH` read-only, inject inert local-only env vars (`OPENAI_API_KEY=LOCAL_DISABLED`, `ANTHROPIC_API_KEY=LOCAL_DISABLED`, `OPENAI_BASE_URL=http://127.0.0.1:9`), and use a `sys.meta_path` loader hook (adapted from `original_repo/web_overrides.py`) to configure `Agent-OM-Lite` (`ChatOllama("llama3:8b", temperature=0.0, seed=42, top_p=1.0, top_k=1, repeat_penalty=1.0)`, `OllamaEmbeddings("llama3:8b")`, `vector_length=4096`), read `source.xml`/`target.xml`/`reference.xml` from `original_repo/data/conference/cmt-confof/component/`, redirect `connection_string` to `postgresql://postgres@127.0.0.1:5432/agent_om_upstream`, and write all outputs inside `agent_om_local/output/upstream_runs/<run_id>/`.
3. **Environment & Database Isolation:**
   * Dedicated virtual environment `agent_om_local/.venv_upstream` (Python `3.11.9`) with upstream's pinned CLI packages (`langchain==0.3.27`, `langchain_community==0.3.31`, `langchain-ollama==0.2.3`, `numpy==1.26.4`, `pandas==2.0.3`, `rdflib==7.0.0`, `breame==0.1.2`, `asyncpg==0.28.0`, `psycopg2_binary==2.9.9`, `pgvector==0.1.8`, `python-dotenv==1.0.1`, `colorama==0.4.6`).
   * Dedicated PostgreSQL database `agent_om_upstream` on the portable PostgreSQL 16.15 instance (`127.0.0.1:5432`), completely isolated from `agent_om_local`.

---

## 7. Recommended Windows Desktop GUI Architecture

* **Framework Choice: `PySide6` (Qt 6 for Python)** over `Tkinter`, paired with `matplotlib` (`FigureCanvasQTAgg`) for precision/recall/threshold charts and `PyInstaller` (`--onedir`) for standalone Windows `.exe` packaging.
* **Rationale:**
  * Native `QThread` / `QProcess` and thread-safe Qt signals support responsive live log streaming and clean cancellation of long-running Ollama/PostgreSQL pipeline stages without freezing the UI.
  * `QTableView` + `QAbstractTableModel` + `QSortFilterProxyModel` cleanly renders 162 multi-paragraph entity descriptions, RRF rankings, validation reasoning logs, and side-by-side color-coded original-vs-local diffs.
  * Native `QMainWindow` + sidebar navigation + `QWizard` directly supports all 11 required screens while orchestrating `agent_om_local/src/` and `run_upstream_isolated.py` via thin service adapters (zero algorithm duplication, 100% local, zero cloud/telemetry calls, non-destructive timestamped run directories).

