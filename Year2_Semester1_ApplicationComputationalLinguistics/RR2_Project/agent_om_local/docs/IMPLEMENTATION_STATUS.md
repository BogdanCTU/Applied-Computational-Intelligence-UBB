# Agent-OM Replication & Windows GUI — Authoritative Implementation Status

**Last Updated:** 2026-11-02  
**Current Active Phase:** Phase 0 COMPLETED — Awaiting User Approval to Begin Phase 1  
**Workspace Root:** `e:\_3_Master\Applied-Computational-Intelligence-UBB\Year2_Semester1_ApplicationComputationalLinguistics\RR2_Project`  
**Local Project Root:** `agent_om_local/`  
**Upstream Read-Only Root:** `original_repo/`

---

## 1. Mandatory Project Constraints & Guardrails

1. **`original_repo/` is strictly READ-ONLY:** Never modify, rename, delete, overwrite, or create any file inside `original_repo/`.
2. **Workspace containment:** All new code, scripts, virtual environments, reports, configurations, outputs, and GUI files must reside strictly inside `agent_om_local/`.
3. **No Git commands:** **Do not execute any `git` commands under any circumstances.** Verify `original_repo/` immutability exclusively via read-only Python/PowerShell SHA-256 file manifests.
4. **No external publishing:** Never push, publish, or upload anything to GitHub or external services.
5. **Immutable datasets & ground truth:** Never modify original ontology datasets or reference alignments.
6. **100% local inference:** Never call cloud LLM APIs or paid inference services; use local Ollama models only. Never silently substitute models.
7. **Preserve historical artifacts:** Never overwrite or delete existing experimental results in `agent_om_local/output/` or reports in `agent_om_local/docs/`.
8. **Database safety:** Never run destructive database operations on `agent_om_local` without explicit approval. Always use a separate PostgreSQL database (`agent_om_upstream`) when executing upstream code, because upstream `om_csv_to_database.py` drops and recreates tables on every run.
9. **Phase-gated execution:** Never start a new phase or combine multiple phases without presenting the phase plan, updating this tracker, writing the phase report in `docs/`, and receiving explicit user approval.

---

## 2. Master Phase & Sub-Phase Roadmap

Allowed statuses: `NOT STARTED` | `IN PROGRESS` | `BLOCKED` | `COMPLETED`

| Phase / Sub-Phase | Description | Status | Key Deliverable / Evidence |
| :--- | :--- | :---: | :--- |
| **Pre-Audit (Steps 4–7D.1)** | Existing local pipeline (`src/`), 14 pytest modules, CMT–ConfOf hybrid experiments (`E1`–`E7`, threshold sensitivity, prompt-order ablation `A2` & repeatability) | `COMPLETED` | `src/`, `tests/`, `output/step5_*`–`step7d1_*`, `docs/step4_*`–`step7d1_*` |
| **Phase 0** | **Project and Environment Audit** | `COMPLETED` | `docs/phase0_audit_report.md`, `docs/IMPLEMENTATION_STATUS.md` |
| `0.1` | Inspect `original_repo/` and `agent_om_local/` structure, scripts, tests, outputs, and docs | `COMPLETED` | Inventoried 13 local modules, 14 test suites, 26 output files, 6 historical reports |
| `0.2` | Audit Python, portable PostgreSQL, `pgvector`, hardware, and local Ollama model manifests | `COMPLETED` | Verified Python `3.11.9`, PostgreSQL `16.15`, `pgvector 0.8.7`, Ollama `0.40.13`, RTX 4060 `8 GiB` |
| `0.3` | Catalog initial code/methodological discrepancies & design isolated baseline + GUI architecture | `COMPLETED` | Documented `DISC-01`–`DISC-09` in Section 5 below |
| `0.4` | Initialize `docs/IMPLEMENTATION_STATUS.md` and `docs/phase0_audit_report.md` | `COMPLETED` | Created on `2026-11-02` |
| **Phase 1** | **Upstream Baseline (`Agent-OM-Lite` on CMT–ConfOf)** | `NOT STARTED` | Planned: `docs/phase1_upstream_baseline_report.md` |
| `1.1` | Compute read-only SHA-256 baseline manifest of `original_repo/` (no Git commands) | `NOT STARTED` | Planned: `output/upstream_runs/original_repo_sha256_manifest.json` |
| `1.2` | Start portable PostgreSQL (`5432`) & Ollama (`11434`), verify `agent_om_local` DB intact, pull & inspect `llama3:8b` | `NOT STARTED` | Requires user approval (`DEC-02`, `DEC-03`) |
| `1.3` | Create isolated `agent_om_local/.venv_upstream` & isolated PostgreSQL database `agent_om_upstream` | `NOT STARTED` | Keeps `agent_om_local/.venv` and `agent_om_local` DB untouched |
| `1.4` | Implement `scripts/run_upstream_isolated.py` + unit/smoke tests (verify zero writes to `original_repo/` and `vector(4096)` ingestion) | `NOT STARTED` | Planned: `scripts/run_upstream_isolated.py`, `tests/test_upstream_isolated_runner.py` |
| `1.5` | Execute CMT–ConfOf `Agent-OM-Lite` (`llama3:8b`, 4096-dim) baseline, re-verify `original_repo/` SHA-256 manifest, write Phase 1 report | `NOT STARTED` | Planned: `output/upstream_runs/cmt_confof_agent_om_lite/`, `docs/phase1_upstream_baseline_report.md` |
| **Phase 2** | **Source-Level Comparison** | `NOT STARTED` | Planned: `docs/phase2_source_comparison_report.md` |
| `2.1` | Component-by-component audit across all 13 pipeline components (`original_repo` vs. `agent_om_local`) | `NOT STARTED` | Parsing, extraction, cleaning, 3 retrievers, DB/chunking, SQL similarity, RRF, bypass, validator, merger |
| `2.2` | Classify every difference (*Equivalent*, *Adapted*, *Missing*, *Incorrect*) with exact line anchors | `NOT STARTED` | Traceable parity table in `docs/phase2_source_comparison_report.md` |
| **Phase 3** | **Intermediate Output Comparison** | `NOT STARTED` | Planned: `docs/phase3_intermediate_comparison_report.md` |
| `3.1` | Run `agent_om_local` end-to-end feature extraction (`LexicalRetriever` + `SemanticRetriever`) under controlled local models | `NOT STARTED` | Non-destructive isolated output directory & separate DB/schema |
| `3.2` | Compare extracted entities, metadata, cleaned names, lexical/semantic texts, chunks, similarities, candidates, RRF groups, validations, and mergers | `NOT STARTED` | Planned: `output/phase3_comparison/`, `docs/phase3_intermediate_comparison_report.md` |
| **Phase 4** | **Algorithmic Parity & Regression Suite** | `NOT STARTED` | Planned: `docs/phase4_algorithmic_parity_report.md` |
| `4.1` | Resolve defects & add configurable parity toggles (`DISC-01`–`DISC-09`) without altering historical experiment scripts/outputs | `NOT STARTED` | Fixes in `src/` with backward-compatible defaults/flags |
| `4.2` | Add edge-case & parity regression tests (`pytest`), verify 100% pass rate & historical artifact preservation | `NOT STARTED` | Planned: `tests/test_algorithmic_parity.py`, `docs/phase4_algorithmic_parity_report.md` |
| **Phase 5** | **Experimental Reproduction** | `NOT STARTED` | Planned: `docs/phase5_experimental_reproduction_report.md` |
| `5.1` | Execute controlled CMT–ConfOf benchmark across upstream `Agent-OM` (read-only committed ref), upstream `Agent-OM-Lite`, local `Agent-OM-Lite` parity config, and local `qwen3.5:9b` + `nomic-embed-text` | `NOT STARTED` | Planned: `output/phase5_reproduction/` |
| `5.2` | Multi-run repeatability, `P`/`R`/`F1`/`TP`/`FP`/`FN`, runtime/calls/tokens accounting, and discrepancy explanation | `NOT STARTED` | Planned: `docs/phase5_experimental_reproduction_report.md` |
| **Phase 6** | **Scientific Replication Report** | `NOT STARTED` | Planned: `docs/phase6_scientific_replication_report.md` |
| `6.1` | Author final comprehensive scientific report (setup, versions, config tables, parity matrix, intermediate & final results, limitations, reproducibility guide, fidelity verdict) | `NOT STARTED` | Planned: `docs/phase6_scientific_replication_report.md` |
| **Phase 7** | **Windows Desktop GUI & PyInstaller Executable** | `NOT STARTED` | Planned: `src/gui/`, `run_gui.py`, `dist/`, `docs/phase7_gui_report.md` |
| `7.1` | Core `PySide6` application shell, service adapters, Dashboard, Environment Check, Dataset Selector, Config, and Log Console | `NOT STARTED` | Requires `PySide6` & `matplotlib` approval (`DEC-01`) |
| `7.2` | Step-by-step Replication Wizard, Individual Stage Runner (with safe Stop), Intermediate Viewer, Original-vs-Local Diff, Metrics/Charts, History, and CSV/JSON/MD Export | `NOT STARTED` | Orchestrates `src/` and `run_upstream_isolated.py` without duplicating algorithms |
| `7.3` | Automated GUI/controller tests, PyInstaller Windows `.exe` packaging (`dist/`), and `docs/phase7_gui_report.md` | `NOT STARTED` | Standalone local Windows `.exe` (PostgreSQL & Ollama detected externally) |

---

## 3. Verified Baseline Environment

* **Operating System:** Windows (`10.0.26300`), PowerShell shell.
* **Hardware:** `15.24 GiB` physical RAM; **NVIDIA GeForce RTX 4060 Laptop GPU** (`8,188 MiB` VRAM, NVIDIA driver `621.01`).
* **Upstream Snapshot (`original_repo/`):** Commit `89d0f967a466f17692768e5e370c29b35e5e77e3` (`2026-10-01`, OAEI 2026 submission; release tags `v1.0.0`/`v1.0.1` = PVLDB 2025 `46f0c72f`, `v1.0.2` = OAEI 2025 `d9656fd0`).
* **Python Environments:**
  * System installations: Python `3.11.9`, `3.12`, `3.13`.
  * `agent_om_local/.venv`: Python `3.11.9` (`rdflib 7.6.0`, `breame 0.1.2`, `pandas 3.1.0`, `numpy 2.4.6`, `psycopg2-binary 2.9.13`, `asyncpg 0.32.0`, `pgvector 0.5.1`, `ollama 0.6.3`, `langchain-core 1.7.3`, `langchain-ollama 1.1.0`, `langchain-text-splitters 1.1.3`, `python-dotenv 1.2.4`, `pyyaml 6.0.3`, `pytest 9.2.0`, `tqdm 4.70.1`, `colorama 0.4.6`, stdlib `tkinter` `8.6`).
  * Missing packages/envs: `agent_om_local/.venv_upstream` (not created yet); `PySide6`, `matplotlib`, `pyinstaller` (not installed yet).
* **PostgreSQL + `pgvector`:**
  * Portable PostgreSQL `16.15` at `agent_om_local/.pg/pgsql/bin/postgres.exe` with `pgvector 0.8.7` (`vector.dll`, `vector.control`, `vector--0.8.7.sql`).
  * Data directory: `agent_om_local/.pgdata` (`PG_VERSION = 16`).
  * Current runtime state: **Stopped** (`127.0.0.1:5432` not listening during Phase 0 audit).
  * Upstream database `agent_om_upstream`: **Not yet created**.
* **Ollama & Local Models:**
  * Ollama client/app version: `0.40.13` (`E:\_1_Applications\Ollama`).
  * Current runtime state: **Stopped** (`http://127.0.0.1:11434` unreachable during Phase 0 audit).
  * Local manifest store A (`E:\_1_Applications\Ollama\models\manifests`): `qwen3.5:9b`, `nomic-embed-text:latest`, `bge-m3:latest`, `gemma4:12b`, `phi4-mini:latest`, `qwen2.5-coder:7b`.
  * Local manifest store B (`C:\Users\bctod\.ollama\models\manifests`): `gemma4:12b`.
  * Missing model for `Agent-OM-Lite`: **`llama3:8b` is not yet pulled**.

---

## 4. Known Discrepancies Registry (`original_repo/` vs. `agent_om_local/`)

| ID | Component | Classification (Preliminary) | Description | Status |
| :---: | :--- | :---: | :--- | :---: |
| `DISC-01` | Experimental Pipeline (`scripts/run_experiments_step6.py`) | Methodological / Hybrid Input | Steps 5–7D populated PostgreSQL from upstream's `gpt-4o`-generated `ontology_matching.csv` rather than running local `RetrievalAgent.extract_representations_for_entities()`. | `OPEN` (Address in Phases 3 & 5) |
| `DISC-02` | Model & Vector Config (`src/config.py`) | Adapted / Incomplete | Local defaults to `qwen3.5:9b` + `nomic-embed-text` (`768`-dim); `AppConfig.embedding_dimensions` lacks `"llama3:8b": 4096`; LLM params omit Agent-OM-Lite's `seed=42, top_k=1, top_p=1.0, repeat_penalty=1.0`. | `OPEN` (Address in Phase 4) |
| `DISC-03` | Agent Tool Routing (`om_*.py` vs. `src/agents/`) | Intentional Adaptation | Upstream invokes an LLM `JsonOutputParser` tool-router before every `@tool` call (~975+ extra LLM calls on CMT–ConfOf; brittle on malformed JSON). Local calls Python methods deterministically. | `OPEN` (Verify in Phases 1–2; document in Phase 4) |
| `DISC-04` | Null Semantic Embedding (`src/db/database_manager.py`) | **Incorrect (Defect)** | Upstream replaces `null_value_sentence` with `""` → 0 chunks in `semantic_matching`. Local re-inserts `"Information is not available."` and embeds it → spurious `1.000` cosine similarity between unrelated isolated entities. (CMT–ConfOf had 0 empty semantic rows, so Steps 5–7D were unaffected.) | `OPEN` (Fix in Phase 4) |
| `DISC-05` | Code-IRI Label Lookup (`src/agents/matching_agent.py`) | **Missing Feature** | Local `MatchingAgent` hardcodes `uri_to_name()` instead of resolving `rdfs:label`/`skos:prefLabel` when `o1_is_code`/`o2_is_code` is `True`. (No impact on CMT–ConfOf where both are `False`.) | `OPEN` (Fix in Phase 4) |
| `DISC-06` | Property Sort & Punned URIs (`src/ontology/entity_extractor.py`) | Subtle Divergence | Upstream sorts ObjectProperties and DatatypeProperties together alphabetically (retaining punned duplicates); local sorts ObjectProperties first then DatatypeProperties, shifting `entity_id` numeric prefixes in RRF tie-breaking. | `OPEN` (Align/toggle in Phase 4) |
| `DISC-07` | Retriever LLM CoT (`src/retrieval/{lexical,semantic}_retriever.py`) | Configuration Defect | `LexicalRetriever._ensure_llm()` and `SemanticRetriever._ensure_llm()` omit `reasoning=False`, unlike `MatchingValidator._ensure_llm()`, risking slow CoT output on `qwen3.5:9b`. | `OPEN` (Fix in Phase 4) |
| `DISC-08` | Prompt Whitespace & Set Joining (`validator.py`, `lexical_retriever.py`, `semantic_retriever.py`) | Minor Formatting Adaptation | Upstream `validate()` has 28-space indentation on lines 2–5; upstream `lexical()` joins an unsorted `set`; upstream `semantic()` concatenates without `"\n"`. | `OPEN` (Audit impact in Phases 2–3) |
| `DISC-09` | Env Vars & Test Paths (`src/config.py`, `tests/test_*.py`) | Hygiene / Portability Defect | `.env.example` names (`DB_HOST`, `DEFAULT_CHAT_MODEL`) do not match `src/config.py` (`PGHOST`, `AGENT_OM_LLM`); 3 test files hardcode stale path `E:\_3_Master\_9_ACL_Project\...`. | `OPEN` (Fix in Phase 4) |

---

## 5. Outstanding Decisions Requiring User Approval

* **`DEC-01` — GUI Framework Confirmation:** Approve **`PySide6`** (recommended over `Tkinter`) + `matplotlib` + `PyInstaller` (`--onedir`) for Phase 7.
* **`DEC-02` — Phase 1 Service Startup & Model Pull:** Approve starting portable PostgreSQL (`127.0.0.1:5432`) and local Ollama (`127.0.0.1:11434`), using `OLLAMA_MODELS=E:\_1_Applications\Ollama\models` (where `qwen3.5:9b`, `nomic-embed-text`, and `bge-m3` already reside), and pulling **`llama3:8b`** (~4.7 GB) locally for `Agent-OM-Lite`.
* **`DEC-03` — Phase 1 Isolated Environment & Database Creation:** Approve creating `agent_om_local/.venv_upstream` (pinned upstream CLI dependencies) and creating the separate PostgreSQL database **`agent_om_upstream`** (`postgresql://postgres@127.0.0.1:5432/agent_om_upstream`).
* **`DEC-04` — Phase 1 Upstream Execution Scope:** Approve implementing `agent_om_local/scripts/run_upstream_isolated.py`, running a 2-entity smoke test to verify `llama3:8b` JSON tool-calling stability and `vector(4096)` storage, and then executing the full CMT–ConfOf `Agent-OM-Lite` baseline into `agent_om_local/output/upstream_runs/`. (Note: if `llama3:8b` triggers upstream's known `KeyError`/`JSONDecodeError` tool-router bug on any entity, we will record the exact failure verbatim rather than silently patching `original_repo/`.)

---

## 6. Implementation Log (Files, Commands, Tests & Issues)

### Phase 0 — Project and Environment Audit (`2026-11-02`)
* **Files Created:**
  * `agent_om_local/docs/phase0_audit_report.md`
  * `agent_om_local/docs/IMPLEMENTATION_STATUS.md`
* **Files Modified or Deleted:** None (`0` modified, `0` deleted).
* **Read-Only Audit Commands Executed & Actual Results:**
  * Directory & file inventory of workspace root, `agent_om_local/`, and `original_repo/` → Verified 13 local `src/` modules, 14 `tests/` files, 11 `scripts/` files, 26 `output/` artifacts, 6 `docs/` reports, and upstream OAEI/PVLDB files.
  * Python & `.venv` inspection (`python --version`, `py -0p`, `.venv\Lib\site-packages\*.dist-info`, `tkinter` version check) → Verified Python `3.11.9` in `.venv`, Tcl/Tk `8.6`, and exact package versions.
  * Portable PostgreSQL & `pgvector` check (`postgres.exe --version`, `pg_isready.exe`, `vector.control`, `.pgdata/PG_VERSION`) → Verified PostgreSQL `16.15` and `pgvector 0.8.7`; server currently stopped.
  * Ollama & hardware check (`ollama --version`, `127.0.0.1:11434/api/version`, manifest directories, `nvidia-smi`, system RAM) → Verified Ollama `0.40.13` (stopped), RTX 4060 Laptop GPU (`8,188 MiB` VRAM), `15.24 GiB` RAM, and confirmed `llama3:8b` is not yet pulled.
  * Static code & CSV grep checks (`Select-String` for `cmt-confof` scores, `extract_representations_for_entities` usage, `"Information is not available"`, unused `torch`/`transformers` imports, and stale `_9_ACL_Project` paths) → Uncovered `DISC-01` through `DISC-09` and upstream `Agent-OM-Lite` CMT–ConfOf reference score (`F1 = 34.78%`).
  * *(Note: Read-only repository metadata checks were run during initial Phase 0 discovery prior to the strict no-Git rule; per Constraint 3 above, zero Git commands are permitted from this point forward.)*
* **Tests Performed in Phase 0:** None executed (Phase 0 strictly prohibited running experiments or starting databases).
* **Failures / Deviations / Unresolved Issues:**
  * Ollama CLI (`ollama list`) timed out attempting to auto-spawn UI server from non-interactive shell while Ollama was stopped; resolved during audit by reading on-disk Ollama manifest directories directly.

---

## 7. Next Recommended Action

**Await user approval of Phase 1** (and confirmation of `DEC-01`–`DEC-04`), then execute **Phase 1 — Isolated Upstream Baseline (`Agent-OM-Lite` on CMT–ConfOf)** following the 11-step protocol.

