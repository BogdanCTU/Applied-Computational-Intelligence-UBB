# Agent-OM Guided Replication Workbench — Windows Desktop Application User Guide

## 1. Overview

The **Agent-OM Guided Replication & Validation Workbench** is a standalone Python/PySide6 Windows desktop application built for reproducing, auditing, and experimentally validating **Agent-OM: Leveraging LLM Agents for Ontology Matching** (Qiang et al., *PVLDB* 2025, Vol. 18, pp. 516–529; arXiv:2312.00326).

### Core Safety & Privacy Guarantees
- **100% Local Loopback Inference & Storage:** Communicates exclusively with local **Ollama** (`127.0.0.1:11434`) and local **PostgreSQL + pgvector** (`127.0.0.1:5432`). No cloud APIs, external network calls, or telemetry are ever used.
- **Read-Only Upstream Protection:** `original_repo/` is treated as strictly read-only. Dataset discovery and reference comparisons never create, modify, or delete files inside `original_repo/`.
- **Non-Destructive Artifact & Database Isolation:** The historical database `agent_om_local` and historical `output/step*` artifacts are protected from destructive writes. All new GUI runs write to dedicated `agent_om_local/output/replication_runs/<experiment_id>/` directories and isolated PostgreSQL databases (`agent_om_parity`, `agent_om_adapted`, `agent_om_experimental`, or custom user-created databases).

---

## 2. Runtime Prerequisites (External Local Services)

Consistent with scientific packaging best practices, the Windows executable bundles the Python runtime, PySide6 UI, Matplotlib, RDFLib, LangChain-Ollama, and PostgreSQL client libraries, while keeping database storage and LLM inference services external:

1. **Windows 10 / 11 (x64)**
2. **PostgreSQL 16+ with `pgvector` (`0.8+`) listening on `127.0.0.1:5432`:**
   - Using the workspace portable PostgreSQL server:
     ```powershell
     & "agent_om_local\.pg\pgsql\bin\postgres.exe" -D "agent_om_local\.pgdata" -p 5432 -h 127.0.0.1
     ```
3. **Ollama (`0.4+`) listening on `127.0.0.1:11434`:**
   - Required models for **Agent-OM-Lite Parity** (`upstream_lite_parity`):
     - `llama3:8b` (`ollama pull llama3:8b` — used for both chat and 4096-dim embeddings via the built-in loopback `LlamaBridgeEmbeddings` adapter)
   - Required models for **Local Adapted** (`local_adapted`):
     - `qwen3.5:9b` (`ollama pull qwen3.5:9b`)
     - `nomic-embed-text` (`ollama pull nomic-embed-text`)

---

## 3. Launching the Application on Windows

### Option A — Standalone Packaged Windows Executable (No Python `.venv` Required)
Double-click in Windows Explorer or run from PowerShell/CMD:
```powershell
.\agent_om_local\dist\AgentOM\AgentOM.exe
```
*(Or via the top-level convenience launcher `.\agent_om_local\dist\AgentOM.exe`.)*

### Option B — Running from Python Source
```powershell
cd agent_om_local
.\.venv\Scripts\python.exe run_gui.py
```

### Automated Offscreen Verification CLI Flags
Both `run_gui.py` and `AgentOM.exe` support deterministic headless verification:
```powershell
# Verify all 10 GUI screens, PostgreSQL health, Ollama health, and dataset discovery:
.\agent_om_local\dist\AgentOM\AgentOM.exe --self-test

# Also execute a 2-entity/side end-to-end smoke run and export a complete report bundle:
.\agent_om_local\dist\AgentOM\AgentOM.exe --self-test --smoke-run-id exe_smoke_verify --export-bundle-name exe_bundle_verify
```

---

## 4. Building the Windows Executable from Source

From inside `agent_om_local/`:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```
This runs PyInstaller cleanly using `agent_om.spec` (`--onedir` mode for fast startup and zero temp-extraction overhead) and outputs:
- `agent_om_local/dist/AgentOM/AgentOM.exe` (packaged application directory)
- `agent_om_local/dist/AgentOM.exe` (top-level launcher)

---

## 5. Guided 10-Screen Replication Workflow

1. **1. Dashboard:** Displays live health badges for PostgreSQL (`127.0.0.1:5432`), Ollama (`127.0.0.1:11434`), `original_repo/` read-only verification (`8,358` files), indexed run counts, workflow shortcuts, and the CMT–ConfOf benchmark comparison table.
2. **2. Environment Diagnostics:** Inspects OS, Python/executable runtime mode, NVIDIA GPU/VRAM (`nvidia-smi`), installed Ollama models and SHA digests, PostgreSQL databases, `pgvector` version, and table row counts/vector dimensions. Allows creating new isolated PostgreSQL databases with one click.
3. **3. Dataset Manager:** Discovers read-only OAEI datasets in `original_repo/data/` (defaulting to `conference/cmt-confof/component`) or lets you browse custom local `.owl`/`.rdf`/`.xml` source, target, and reference alignments, previewing triple counts, classes, object/datatype properties, and gold alignments.
4. **4. Configuration Profiles:** Switches between the 4 explicit profiles:
   - `upstream_product_reference` (read-only GPT-4o + `text-embedding-ada-002` reference metadata; cloud execution blocked)
   - `upstream_lite_parity` (`llama3:8b` + `llama3:8b` `4096`-dim, `temp=0.0, seed=42, top_k=1, repeat_penalty=1.0`, 28-space prompt, empty semantic chunks skipped)
   - `local_adapted` (`qwen3.5:9b` `reasoning=False` + `nomic-embed-text` `768`-dim)
   - `experimental` (customizable cosine similarity threshold, `top_k`, `rrf_k`, predicate scope `head` vs `pvl_v1`, and tool routing `deterministic` vs `llm_json`)
   Includes JSON preset import/export.
5. **5. Replication Wizard (14 Stages):** Executes either end-to-end local replication from raw XML ontologies or the isolated upstream `Agent-OM-Lite` harness on a background `QThread` so the UI never freezes. Tracks stages `1`–`14` live and provides a red **Cancel Active Run** button for cooperative cancellation.
6. **6. Pipeline Stage Inspector:** Searchable, sortable per-entity table inspecting cleaned syntactic text, LLM lexical explanations, semantic verbalizations, top-k retrieval candidates, RRF fused lists, validation prompts/responses, and final match status.
7. **7. Original vs Local Comparison:** Computes and displays the complete **17-point intermediate artifact comparison** and pair-level TP/FP/FN set diffs (`Shared`, `Only in A`, `Only in B`) between any two runs or committed upstream references.
8. **8. Evaluation & Charts:** Renders interactive Matplotlib charts (`Precision / Recall / F1` grouped bars, `Precision vs Recall` scatter with iso-F1 contours, `Stage-by-Stage True Positive Attrition`, `Similarity Threshold Sensitivity`, and `Runtime & LLM Calls`) alongside stage attrition tables.
9. **9. Live Logs & Run History:** Real-time streaming execution console, progress bar, **Cancel Active Run** control, and historical run browser with full `run_summary.json` and `config_snapshot.json` inspection.
10. **10. Report & Artifact Export:** Exports non-destructive timestamped bundles into `agent_om_local/output/exports/<bundle_name>/` containing CSV/JSON benchmark tables, 200-DPI PNG charts, OAEI Alignment API RDF/XML (`alignment.rdf`), 6 prediction CSV variants, and Markdown replication reports.

---

## 6. Troubleshooting

| Symptom | Cause | Resolution |
| :--- | :--- | :--- |
| **PostgreSQL status shows OFFLINE** | Portable PostgreSQL server is not running on `127.0.0.1:5432`. | Start `postgres.exe -D agent_om_local\.pgdata -p 5432 -h 127.0.0.1` and click **Refresh Diagnostics**. |
| **Ollama status shows OFFLINE** | Local Ollama daemon is not running on `127.0.0.1:11434`. | Run `ollama serve` locally and verify models via `ollama list`. |
| **Configuration Blocked: `agent_om_local` is protected** | Attempted to run a write pipeline targeting the protected historical database. | Select `agent_om_parity`, `agent_om_adapted`, `agent_om_experimental`, or create a new isolated DB on the **Environment Diagnostics** screen. |
| **Database locked by another active run** | Concurrent experiment already holds the write mutex for that database. | Wait for the active run to finish or cancel it cleanly from the **Replication Wizard** or **Live Logs** screen. |
| **VRAM pressure on 8 GB GPU during `upstream_lite_parity`** | `llama3:8b` uses ~5.4 GB VRAM. | `LlamaBridgeEmbeddings` automatically unloads the transient embedding alias (`keep_alive=0`) immediately after vector indexing before `ChatOllama` validation begins; avoid running two GPU experiments simultaneously. |

