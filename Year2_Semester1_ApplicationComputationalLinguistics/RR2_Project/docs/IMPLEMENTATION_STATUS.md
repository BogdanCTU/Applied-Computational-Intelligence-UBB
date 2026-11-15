# Agent-OM Replication & Windows GUI — Authoritative Implementation Status

**Last Updated:** 2026-11-02  
**Current Active Phase:** Phases 0, 1, 2, 4 COMPLETED; GUI & `AgentOM.exe` Built & Verified; Phase 3 & Phase 5 Local Parity Run (`task-563`) Active  
**Workspace Root:** `e:\_3_Master\Applied-Computational-Intelligence-UBB\Year2_Semester1_ApplicationComputationalLinguistics\RR2_Project`  
**Local Project Root:** `agent_om_local/`  
**Upstream Read-Only Root:** `original_repo/`

---

## 1. Mandatory Project Constraints & Guardrails

1. **`original_repo/` is strictly READ-ONLY:** Never modify, rename, delete, overwrite, or create any file inside `original_repo/` (`aggregate_sha256 = afed3137d9905945c5167559b15ef62815c64220a0aa1038ea06893e97b7c7c0`).
2. **Workspace containment:** All new code, scripts, virtual environments, reports, configurations, outputs, executables, and GUI files reside strictly inside `agent_om_local/`.
3. **No Git commands:** **Zero `git` commands under any circumstances.** Repository immutability is verified exclusively via `scripts/verify_repo_integrity.py` SHA-256 file manifests.
4. **No external publishing:** Never push, publish, or upload anything to GitHub or external services.
5. **Immutable datasets & ground truth:** Never modify original ontology datasets or reference alignments.
6. **100% local inference:** Local Ollama (`http://127.0.0.1:11434`) and portable PostgreSQL (`127.0.0.1:5432`) only; zero cloud APIs, zero telemetry, zero silent model substitution.
7. **Preserve historical artifacts:** Existing Step 4–7D.1 outputs (`eb28e7a7...`) and reports (`91ad180c...`) remain untouched; all new runs write to `agent_om_local/output/replication_runs/<experiment_id>/`.
8. **Database safety:** Protected database `agent_om_local` (`162 / 162 / 206 / 258` rows) is guarded in code against `DROP TABLE`; isolated databases (`agent_om_upstream`, `agent_om_parity`, `agent_om_adapted`, `agent_om_experimental`, `agent_om_test`) are used for all replication runs and tests.

---

## 2. Master Phase & Sub-Phase Roadmap

Allowed statuses: `NOT STARTED` | `IN PROGRESS` | `BLOCKED` | `COMPLETED`

| Phase / Sub-Phase | Description | Status | Key Deliverable / Evidence |
| :--- | :--- | :---: | :--- |
| **Pre-Audit (Steps 4–7D.1)** | Existing local pipeline (`src/`), 14 pytest modules, CMT–ConfOf hybrid experiments (`E1`–`E7`, threshold sensitivity, prompt-order ablation `A2` & repeatability) | `COMPLETED` | `src/`, `tests/`, `output/step5_*`–`step7d1_*`, `docs/step4_*`–`step7d1_*` |
| **Phase 0** | **Project and Environment Audit & Baseline Manifests** | `COMPLETED` | `docs/phase0_audit_report.md`, `scripts/verify_repo_integrity.py`, `output/replication_runs/manifests/` |
| **Phase 1** | **Upstream Baseline (`Agent-OM-Lite` on CMT–ConfOf)** | `COMPLETED` | `docs/phase1_upstream_baseline_report.md`, `output/replication_runs/phase1_cmt_confof_agent_om_lite_v1/` |
| `1.1` | Compute read-only SHA-256 baseline manifests (`original_repo/`, `output/`, `docs/`) | `COMPLETED` | `original_repo_baseline_sha256.json` (`8,358` files, `afed3137...`) |
| `1.2` | Start portable PostgreSQL (`127.0.0.1:5432`), verify Ollama `0.40.13` & `llama3:8b` (`4096`-dim via `LlamaEmbeddingBridge`) | `COMPLETED` | `llama3_8b_verification.json` (`365c0bd3...`), `postgres_phase1_verification.json` |
| `1.3` | Create isolated `agent_om_local/.venv_upstream` (78 pinned deps, no PyTorch) & isolated DB `agent_om_upstream` | `COMPLETED` | `venv_upstream_packages.json`, `agent_om_upstream` `vector(4096)` verified |
| `1.4` | Implement `scripts/run_upstream_isolated.py` + unit tests + 4-entity smoke test (`task-206`) | `COMPLETED` | `pytest`: `4 passed`; `phase1_smoke_cmt_confof_4ent` (`117.32s`, exit `0`, `original_repo_unchanged: true`) |
| `1.5` | Execute full 162-entity CMT–ConfOf `Agent-OM-Lite` baseline (`task-281`), compare vs committed `F1=34.78%`, write report | `COMPLETED` | `phase1_cmt_confof_agent_om_lite_v1`: `2,584.34s`, `1,627` calls, `P=41.67%, R=31.25%, F1=35.71%`, `original_repo_unchanged: true` |
| **Phase 2** | **Source-Level Comparison (22 Components across 3 Versions)** | `COMPLETED` | `docs/replication_parity_matrix.md` |
| **Phase 3** | **Intermediate Output Comparison (17 Dimensions from Raw XML)** | `IN PROGRESS` | `src/evaluation/comparator.py`, `scripts/generate_replication_comparisons_and_charts.py`; `phase5_expC_local_parity_run1` running (`task-563`) |
| **Phase 4** | **Algorithmic Parity Fixes (`4.1`–`4.11`) & Regression Suite** | `COMPLETED` | `docs/phase4_algorithmic_parity_report.md`, `tests/test_algorithmic_parity.py` (`125 passed` total suite) |
| **Phase 5** | **Controlled Experimental Reproduction & Attrition Analysis** | `IN PROGRESS` | `phase5_expC_local_parity_run1` (`task-563`) actively running; `local_adapted` queued next |
| **Phase 6** | **Complete Scientific Replication Report (21 Sections)** | `NOT STARTED` | Planned: `docs/final_replication_report.md` |
| **Phase 7** | **Windows Desktop GUI (`PySide6`) & PyInstaller Executable** | `IN PROGRESS` | `src/gui/` (`11` services, `10` screens), `run_gui.py`, `dist/AgentOM/AgentOM.exe` built & `--self-test` verified (`is_frozen: true`); final smoke run pending after Phase 5 |

---

## 3. Discrepancy Resolution Summary (`Phase 4`)

All discrepancies (`DISC-01`–`DISC-09`) documented in Phase 0 and the 22-component Parity Matrix (`docs/replication_parity_matrix.md`) have been resolved in code and verified by `118/118` passing unit and integration tests (`tests/test_algorithmic_parity.py`):
- Empty semantic text (`"Information is not available."`) produces `0` vector rows (`skip_empty_chunks=True`).
- Symmetric `o1_is_code` / `o2_is_code` label resolution (`rdfs:label` -> `skos:prefLabel` -> `uri_to_name`) in `MatchingAgent` and `RetrievalAgent`.
- Combined alphabetical URI property sorting (`combine_properties_sort=True`) preserving punned properties.
- `"llama3:8b": 4096` registered + `LlamaBridgeEmbeddings` + strict runtime vector dimension verification (no silent `768` fallback).
- Centralized `AppConfig.build_chat_llm()` passing `temperature`, `seed`, `top_k`, `top_p`, `repeat_penalty`, `num_ctx`, and `reasoning` consistently across lexical, semantic, and validation LLMs.
- 28-space validation prompt indentation (`indent_validation_prompt=True` in `upstream_lite_parity`), `predicate_scope` (`"head"` vs `"pvl_v1"`), and optional `LLMJsonToolRouter` (`tool_routing_mode="llm_json"`).
- Protected `agent_om_local` database write-guard + `tests/test_retrieval_agent.py` isolated to `agent_om_test` + stale `_9_ACL_Project` paths removed.
- Four explicit profiles (`upstream_product_reference`, `upstream_lite_parity`, `local_adapted`, `experimental`) implemented in `src/config.py`.

---

## 4. Implementation Log (Recent Milestones)

### Phase 2 & Phase 4 (`2026-11-02`)
* **Files Created:**
  * `agent_om_local/docs/replication_parity_matrix.md`
  * `agent_om_local/docs/phase4_algorithmic_parity_report.md`
  * `agent_om_local/src/agents/tool_router.py`
  * `agent_om_local/src/evaluation/__init__.py`
  * `agent_om_local/src/evaluation/metrics.py`
  * `agent_om_local/src/evaluation/comparator.py`
  * `agent_om_local/src/evaluation/charts.py`
  * `agent_om_local/scripts/run_local_replication.py`
  * `agent_om_local/tests/test_algorithmic_parity.py`
* **Files Modified:**
  * `agent_om_local/.env.example`, `agent_om_local/src/config.py`, `agent_om_local/src/db/database_manager.py`, `agent_om_local/src/ontology/parser.py`, `agent_om_local/src/ontology/entity_extractor.py`, `agent_om_local/src/retrieval/lexical_retriever.py`, `agent_om_local/src/retrieval/semantic_retriever.py`, `agent_om_local/src/matching/validator.py`, `agent_om_local/src/agents/retrieval_agent.py`, `agent_om_local/src/agents/matching_agent.py`, `agent_om_local/src/utils/llama_embed_bridge.py`, `agent_om_local/tests/test_ontology.py`, `agent_om_local/tests/test_semantic_retriever.py`, `agent_om_local/tests/test_syntactic_retriever.py`, `agent_om_local/tests/test_retrieval_agent.py`.
* **Commands & Tests Executed:**
  * `.venv\Scripts\python.exe -m pytest tests -q` → **`118 passed, 1 warning in 14.33s`**.
  * Verified `agent_om_local` DB row counts → `{'ontology_matching': 162, 'syntactic_matching': 162, 'lexical_matching': 206, 'semantic_matching': 258}` (unchanged).
  * Installed `PySide6 6.12.0`, `matplotlib 3.11.2`, `pyinstaller 6.22.3` into `agent_om_local/.venv`.

---

## 5. Next Action

1. Implement the PySide6 Windows Desktop GUI (`agent_om_local/src/gui/` + `agent_om_local/run_gui.py` — 11 services and 10 screens) while `task-281` finishes the full 162-entity `Agent-OM-Lite` baseline.
2. Finalize Phase 1 report (`docs/phase1_upstream_baseline_report.md`) upon `task-281` completion.
3. Execute Phase 3 & Phase 5 controlled local experiments (`upstream_lite_parity` and `local_adapted` + repeatability runs), generate comparison artifacts & Matplotlib charts, and author `docs/phase3_intermediate_comparison_report.md`, `docs/phase5_experimental_reproduction_report.md`, and `docs/final_replication_report.md`.
4. Run automated GUI tests, build PyInstaller `.exe` (`dist/AgentOM/`), verify standalone `.exe` execution, and author `docs/USER_GUIDE.md` and `docs/final_acceptance_report.md`.
