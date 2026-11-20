# Stage 2 Execution Report — Phase 3 Script Repair and Test Baseline
## Agent-OM: Scientific Replication, Local Adaptation & Windows Desktop Application

**Execution Date:** 2026-11-15  
**Stage:** Stage 2 (Phase 3 Script Repair, Symbol Verification & Test Suite Baseline)  
**Host Environment:** Windows 11 (build 22631), Python 3.13.17 (`.venv\Scripts\python.exe`)  
**Target Script:** `scripts/generate_replication_comparisons_and_charts.py`  
**Test Suite:** `tests/` (17 test modules, 125 collected test cases)  
**Status:** COMPLETED — Import defects repaired, syntax verified, full baseline executed

---

## 1. Module Structure and Symbol Verification

Before modifying any source code or script imports, the module structure and exported symbols under `src/` were rigorously inspected using Python reflection (`inspect` module):

### 1.1. Merger Inspection (`src/matching/merger.py`)
- **Module File:** `src/matching/merger.py`
- **Exported Class:** `ReciprocalMerger`
- **Exported Methods:**
  - `merge_alignments(self, source_to_target_pairs, target_to_source_pairs, target_to_source_is_reversed=False) -> Set[Tuple[str, str]]`
  - `normalize_pairs(pairs, assumed_orientation="Source->Target") -> Set[Tuple[str, str]]`
  - `analyze_merger(self, source_to_target_pairs, target_to_source_pairs, target_to_source_is_reversed=False) -> Dict[str, Any]`
- **Identified Defect in Caller:**
  `scripts/generate_replication_comparisons_and_charts.py` attempted to import `from src.matching.reciprocal_merger import ReciprocalMerger` (non-existent module name) and called `merger.merge(s2t_top1, t2s_top1)` instead of `merger.merge_alignments(s2t_top1, t2s_top1)`.

### 1.2. Rank Fusion Inspection (`src/retrieval/rank_fusion.py`)
- **Module File:** `src/retrieval/rank_fusion.py`
- **Exported Function:** `reciprocal_rank_fusion(*rankings, k=0, exclude_items=None) -> List[Tuple[float, List[Any]]]`
- **Signature & Return Protocol:**
  Returns grouped scores and entity IDs: `[(score, [item1, item2, ...]), ...]`.
- **Identified Defect in Caller:**
  `scripts/generate_replication_comparisons_and_charts.py` attempted to import `from src.retrieval.rrf import reciprocal_rank_fusion` (non-existent module name) and unpacked `for eid, _ in fused` assuming `fused` was flat `(eid, score)` tuples rather than grouped `(score, [eid1, eid2])`.

---

## 2. Code Corrections Executed

### 2.1. File: `scripts/generate_replication_comparisons_and_charts.py`
- **Lines 44–45 (Module Imports):**
  ```python
  # Replaced:
  from src.matching.reciprocal_merger import ReciprocalMerger
  from src.retrieval.rrf import reciprocal_rank_fusion

  # With correct canonical module locations:
  from src.matching.merger import ReciprocalMerger
  from src.retrieval.rank_fusion import reciprocal_rank_fusion
  ```
- **Lines 128–140 (RRF Group Unpacking & Method Invocation):**
  ```python
  # Replaced flat unpacking:
  fused = reciprocal_rank_fusion(*rankings, k=rrf_k)
  real_uris = [id_to_uri[eid] for eid, _ in fused if eid != "Entity-Dummy" and eid in id_to_uri]
  ...
  merged_top1 = merger.merge(s2t_top1, t2s_top1)

  # With protocol-faithful group unpacking and canonical method call:
  fused = reciprocal_rank_fusion(*rankings, k=int(rrf_k))
  real_uris: List[str] = []
  for _score, group in fused:
      for eid in group:
          if eid != "Entity-Dummy" and eid in id_to_uri and id_to_uri[eid] not in real_uris:
              real_uris.append(id_to_uri[eid])
  ...
  merged_top1 = merger.merge_alignments(s2t_top1, t2s_top1)
  ```

### 2.2. File: `src/matching/merger.py`
- Added backward-compatible convenience alias on `ReciprocalMerger`:
  ```python
  # Convenience alias for merge_alignments
  merge = merge_alignments
  ```

---

## 3. Syntax and Import Verification

The repaired script was verified in the Python 3.13 virtual environment:
1. **Compilation Check:**
   ```powershell
   & ".\.venv\Scripts\python.exe" -m py_compile scripts/generate_replication_comparisons_and_charts.py
   ```
   - **Exit Code:** `0` (clean compilation, no syntax errors).
2. **Import Verification:**
   ```powershell
   & ".\.venv\Scripts\python.exe" -c "import scripts.generate_replication_comparisons_and_charts; print('Import succeeded!')"
   ```
   - **Output:** `Import succeeded!`

---

## 4. Test Suite Execution & Categorization

The entire automated test suite was executed using `.venv\Scripts\python.exe -m pytest tests -v`.

### 4.1. Summary Statistics
- **Total Test Files:** 17 modules
- **Total Items Collected:** 125 test items
- **Passed:** **101 tests (80.8%)**
- **Failed:** 6 tests (4.8%)
- **Errors (Setup Failures):** 18 tests (14.4%)
- **Collection Errors:** **0 (0.0%)** — All 17 test modules successfully collected without import errors.
- **Dependency Errors:** **0 (0.0%)** — All Python 3.13 dependencies are satisfied in `.venv`.

### 4.2. Detailed Failure & Error Categorization

| Category | Count | Failing / Erroring Tests | Root Cause | Scope & Remediation |
| :--- | :---: | :--- | :--- | :--- |
| **Collection Errors** | `0` | None | None | All modules collected cleanly in Python 3.13. |
| **Dependency Errors** | `0` | None | None | All packages verified in `.venv`. |
| **Database Offline (Env Prerequisite)** | `8` | Setup error on `psycopg2.OperationalError: Connection refused (127.0.0.1:5432)`:<br>• `test_algorithmic_parity.py` (4 tests)<br>• `test_retrieval_agent.py` (4 tests) | PostgreSQL port 5432 is stopped; cluster `.pgdata` was omitted in git clone by `.gitignore`. | Environmental prerequisite for later live database runs. Code is guarded against accidental data destruction. |
| **Missing `original_repo` (Env Prerequisite)**| `13` | `FileNotFoundError` on `original_repo/data/conference/cmt-confof/component/source.xml`:<br>• `test_algorithmic_parity.py` (1 test)<br>• `test_ontology.py` (7 tests)<br>• `test_semantic_retriever.py` (2 tests)<br>• `test_syntactic_retriever.py` (3 tests) | Tests hardcode path to upstream `original_repo`, which was excluded by `.gitignore`. | Expected until `original_repo` is restored or test fixtures are pointed to local extracted entity snapshots. |
| **GUI Path & Dataset Expectations** | `3` | `AssertionError` in `test_gui_services_and_views.py`:<br>• `test_project_paths_resolution` (expected folder name `agent_om_local`, actual is `RR2_Project`)<br>• `test_environment_and_dataset_services` (checks `orig["exists"]`)<br>• `test_evaluation_and_report_export_services` (expects `ref_upstream_gpt4o_cmt_confof` in `original_repo`) | Relocation of workspace from `agent_om_local` subdirectory to repository root `RR2_Project`. | GUI path resolver handles both modes; test asserts legacy subdirectory name. |
| **Genuine Algorithmic Failures** | `0` | None | No algorithmic regressions identified. | 101 tests passed across parser, RRF, merger, validator, prompt ablation, and sensitivity analysis. |

---

## 5. Phase 3 Comparison Script Execution Check

In accordance with requirement 8 of Stage 2:
> *"Run the Phase 3 comparison/chart-generation script only if its required input artifacts are present and its output destination is confirmed to be a new, isolated directory. Do not overwrite existing comparisons or experiment results."*

### Pre-Condition Evaluation:
1. **Required Input Artifacts Check:**
   - `phase1_cmt_confof_agent_om_lite_v1` (Upstream Baseline): **PRESENT**
   - `phase5_expC_local_parity_run1`..`run3` (Local Parity): **PRESENT**
   - `phase5_expC_router_det_4ent` / `router_llm_4ent`: **PRESENT**
   - `phase5_expD_local_adapted_run1` (Local Adapted): **INCOMPLETE** (Only entity extraction completed; alignment and summary files are absent).
   - PostgreSQL Live DB connection (`127.0.0.1:5432`): **OFFLINE** (Required for live threshold sweep queries in `_extract_readonly_db_candidates`).
2. **Decision:**
   Execution of `scripts/generate_replication_comparisons_and_charts.py` was **intentionally deferred** to Stage 3 / Stage 4 when its input requirements (Exp D completion and database availability) are satisfied. Running prematurely would raise runtime errors and produce truncated comparisons.

---

## 6. Exact Files Modified or Created in Stage 2

1. **`scripts/generate_replication_comparisons_and_charts.py`** (Modified): Corrected `ReciprocalMerger` and `reciprocal_rank_fusion` import paths and updated RRF group unpacking logic.
2. **`src/matching/merger.py`** (Modified): Added `merge = merge_alignments` backward-compatibility alias on `ReciprocalMerger`.
3. **`docs/stage2_test_and_import_repair_report.md`** (Created): Authored this complete verification and test baseline report.

---

## 7. Stage 2 Sign-Off & Recommended Next Action

Stage 2 is successfully completed. The Phase 3 script import defects are repaired, syntax and imports are verified, and the test baseline is established with 101 passing tests and 0 collection or dependency errors.

**Recommended Next Action:**
Proceed to **Stage 3 & Stage 4**:
1. Provision/start local PostgreSQL 16 on `127.0.0.1:5432` with `agent_om_test` and `agent_om_parity`.
2. Complete `phase5_expD_local_adapted_run1`.
3. Execute `scripts/generate_replication_comparisons_and_charts.py` to generate the 17-point comparison data and 5 PNG figures into `output/replication_runs/comparisons/`.
4. Author `docs/phase3_intermediate_comparison_report.md` and `docs/phase5_experimental_reproduction_report.md`.

