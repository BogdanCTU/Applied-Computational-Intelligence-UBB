# Stage 2.1 Execution Report — Test Environment Remediation and Regression Verification
## Agent-OM: Scientific Replication, Local Adaptation & Windows Desktop Application

**Execution Date:** 2026-11-15  
**Stage:** Stage 2.1 (Test Environment Remediation, Infrastructure Inspection & Regression Baseline)  
**Host Environment:** Windows 11 (build 22631), Python 3.13.17 (`.venv\Scripts\python.exe`)  
**Workspace Directory:** `E:\PERSONAL\GitHub\1_Applied-Computational-Intelligence-UBB\Year2_Semester1_ApplicationComputationalLinguistics\RR2_Project`  
**Status:** COMPLETED — Infrastructure inspected, GUI path resolution stabilized, regression baseline established

---

## 1. Task A — PostgreSQL Test Infrastructure Assessment

### 1.1. Existing Configuration and Scripts Inspection
The PostgreSQL operational configuration was inspected across project files:
- **Startup Script (`scripts/start_postgres.ps1`):** Configured to run detached on `127.0.0.1:5432` pointing to `$ProjectDir\.pg\pgsql\bin\postgres.exe` and cluster `$ProjectDir\.pgdata`.
- **Shutdown Script (`scripts/stop_postgres.ps1`):** Uses `$ProjectDir\.pg\pgsql\bin\pg_ctl.exe -D $PgData stop -m fast`.
- **Environment Template (`.env.example`):** Specifies `DB_HOST=127.0.0.1`, `DB_PORT=5432`, `DB_USER=postgres`, `DB_NAME=agent_om_local`.
- **Database Safety Guard (`src/db/database_manager.py`):** Verified active; raises `RuntimeError` if any process attempts to execute `DROP TABLE` on the protected database `agent_om_local`.

### 1.2. Filesystem & Service Inspection
- **Port 5432 Listener:** Verified inactive via `Get-NetTCPConnection -LocalPort 5432`.
- **Windows Services:** Checked `Get-Service *postgres*` and `Get-Service *pgsql*`; no registered PostgreSQL Windows services exist.
- **Portable Binaries (`.pg`):** Verified absent via `Test-Path ".pg"` (`False`).
- **Data Cluster Directory (`.pgdata`):** Verified absent via `Test-Path ".pgdata"` (`False`).
- **Root Cause:** In the repository root `.gitignore`:
  ```
  Year2_Semester1_ApplicationComputationalLinguistics/RR2_Project/agent_om_local/.pg/
  Year2_Semester1_ApplicationComputationalLinguistics/RR2_Project/agent_om_local/.pgdata/
  ```
  The portable PostgreSQL binaries and data cluster were excluded from version control and were not transferred during repository cloning.

### 1.3. Safety Restraint Sign-Off (Instruction 10 Compliance)
In strict adherence to constraint 10:
> *"If PostgreSQL cannot be safely restored, stop and report the exact missing prerequisite. Do not install a second server or create a new cluster without documenting and obtaining authorization."*

- **Current State:** PostgreSQL cannot be started from the local repository because `.pg` and `.pgdata` do not exist on disk.
- **Action Taken:** No new cluster was initialized, no secondary server was installed, and no destructive operations were performed.
- **Prerequisite Required for Live Database Tests:** User authorization to either:
  1. Restore the original portable PostgreSQL 16.15 `.pg` and `.pgdata` directories from backup, OR
  2. Provision a clean local PostgreSQL 16 cluster with `pgvector` on port 5432 and restore schema/snapshots for `agent_om_local` (162/162/206/258 rows), `agent_om_test`, and `agent_om_parity`.

---

## 2. Task B — Missing `original_repo` Fixtures Assessment

### 2.1. Dependent Tests Catalog
Thirteen automated tests were identified that fail or error due to missing raw XML ontology files:

| # | Test Module & Name | Missing Required Fixture Path | Failure Symptom |
| :-: | :--- | :--- | :--- |
| 1 | `test_algorithmic_parity.py::test_combined_property_uri_order_matches_upstream_cmt_confof` | `original_repo/data/conference/cmt-confof/component/source.xml` | `FileNotFoundError` |
| 2 | `test_ontology.py::TestOntologyParser::test_load_cmt_source_exists` | `original_repo/data/conference/cmt-confof/component/source.xml` | `assert CMT_PATH.exists()` |
| 3 | `test_ontology.py::TestOntologyParser::test_load_confof_target_exists` | `original_repo/data/conference/cmt-confof/component/target.xml` | `assert CONFOF_PATH.exists()` |
| 4 | `test_ontology.py::TestEntityExtractorCMT::test_cmt_counts` | `original_repo/data/conference/cmt-confof/component/source.xml` | `FileNotFoundError` on load |
| 5 | `test_ontology.py::TestEntityExtractorCMT::test_cmt_uri_preservation` | `original_repo/data/conference/cmt-confof/component/source.xml` | `FileNotFoundError` on load |
| 6 | `test_ontology.py::TestEntityExtractorCMT::test_cmt_entity_types` | `original_repo/data/conference/cmt-confof/component/source.xml` | `FileNotFoundError` on load |
| 7 | `test_ontology.py::TestEntityExtractorConfOf::test_confof_counts` | `original_repo/data/conference/cmt-confof/component/target.xml` | `FileNotFoundError` on load |
| 8 | `test_ontology.py::TestEntityExtractorConfOf::test_confof_uri_preservation` | `original_repo/data/conference/cmt-confof/component/target.xml` | `FileNotFoundError` on load |
| 9 | `test_semantic_retriever.py::TestSemanticRetriever::test_expand_bnode_closure_named_cmt` | `original_repo/data/conference/cmt-confof/component/source.xml` | `FileNotFoundError` on load |
| 10| `test_semantic_retriever.py::TestSemanticRetriever::test_expand_bnode_closure_named_confof`| `original_repo/data/conference/cmt-confof/component/target.xml` | `FileNotFoundError` on load |
| 11| `test_syntactic_retriever.py::TestSyntacticRetriever::test_syntactic_extraction_on_cmt_entities` | `original_repo/data/conference/cmt-confof/component/source.xml` | `FileNotFoundError` on load |
| 12| `test_syntactic_retriever.py::TestSyntacticRetriever::test_syntactic_extraction_on_confof_entities` | `original_repo/data/conference/cmt-confof/component/target.xml` | `FileNotFoundError` on load |
| 13| `test_syntactic_retriever.py::TestSyntacticRetriever::test_string_uri_direct_retrieval` | `original_repo/data/conference/cmt-confof/component/source.xml` | `FileNotFoundError` on load |

### 2.2. Bounded Search of Known Documented Locations
In accordance with instruction 4, search was strictly limited to documented project paths:
- `E:/_3_Master/.../original_repo`: **Does not exist** (`False`).
- `E:/PERSONAL/.../RR2_Project/original_repo`: **Does not exist** (`False`).
- `E:/PERSONAL/.../original_repo`: **Does not exist** (`False`).

### 2.3. Root Cause & Scientific Preservation
- **Root Cause:** `Year2_Semester1_ApplicationComputationalLinguistics/RR2_Project/original_repo/` was listed in `.gitignore` and omitted from the git checkout.
- **Scientific Integrity Compliance:** In accordance with instruction 6, no synthetic data was fabricated, no substitute XML files were created, and no assertions were weakened. These 13 tests are documented as blocked by the missing `original_repo` upstream directory.

---

## 3. Task C — GUI Path Assertions Remediation

### 3.1. Analysis of GUI Test Failures
1. **`test_project_paths_resolution`:**
   - **Defect:** Rigid assertion `assert paths.project_root.name == "agent_om_local"`.
   - **Root Cause:** When running directly within `RR2_Project`, `resolve_project_paths()` correctly identifies the directory containing `src/` and `output/`. The test rigidly checked the legacy folder name rather than verifying directory contents.
   - **Correction:** Updated assertion to use stable project-root structural discovery:
     ```python
     assert (paths.project_root / "src").is_dir()
     assert (paths.project_root / "output").is_dir()
     assert paths.original_repo_dir.name == "original_repo"
     ```
   - **Result:** `test_project_paths_resolution PASSED` [100%].

2. **`src/gui/paths.py` Enhancement:**
   - **Improvement:** Added child directory check for `original_repo` in `resolve_project_paths()`:
     ```python
     workspace_root = project_root.parent
     original_repo_dir = workspace_root / "original_repo"
     if not original_repo_dir.is_dir() and (project_root / "original_repo").is_dir():
         original_repo_dir = project_root / "original_repo"
     ```
   - **Impact:** Preserves all existing GUI behavior while stably resolving `original_repo` whether placed inside `project_root` or alongside it.

3. **`test_environment_and_dataset_services` & `test_evaluation_and_report_export_services`:**
   - Failures in these two tests (`assert orig["exists"] is True` and `ref_upstream_gpt4o_cmt_confof` discovery) stem directly from the missing `original_repo` fixtures. In compliance with constraint 7, assertions were not modified or bypassed.

---

## 4. Task D — Targeted Regression Verification

Targeted regression tests were executed in `.venv`:

### 4.1. Merger & Rank Fusion Suite (`tests/test_merger.py`, `tests/test_rank_fusion.py`)
```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests/test_merger.py tests/test_rank_fusion.py -v
```
- **Result:** **13 passed in 0.22s (100% success)**
  - `TestReciprocalMerger::test_merge_exact_match` $\rightarrow$ PASSED
  - `TestReciprocalMerger::test_merge_asymmetric_drops` $\rightarrow$ PASSED
  - `TestReciprocalMerger::test_merge_with_reversed_target_orientation` $\rightarrow$ PASSED
  - `TestReciprocalMerger::test_analyze_merger` $\rightarrow$ PASSED
  - `TestReciprocalMerger::test_empty_alignments` $\rightarrow$ PASSED
  - `TestReciprocalMerger::test_disjoint_alignments` $\rightarrow$ PASSED
  - `TestReciprocalMerger::test_merge_alias_backward_compatibility` $\rightarrow$ PASSED (New test explicitly verifying `merger.merge(...)` alias).
  - `TestReciprocalRankFusion::test_single_ranking_k0` $\rightarrow$ PASSED
  - `TestReciprocalRankFusion::test_multi_ranking_accumulation` $\rightarrow$ PASSED
  - `TestReciprocalRankFusion::test_tie_breaking_lexicographical` $\rightarrow$ PASSED
  - `TestReciprocalRankFusion::test_exclusion_of_dummy_items` $\rightarrow$ PASSED
  - `TestReciprocalRankFusion::test_standard_rrf_k60` $\rightarrow$ PASSED
  - `TestReciprocalRankFusion::test_empty_or_none_rankings` $\rightarrow$ PASSED

### 4.2. GUI Navigation & Services Suite (`tests/test_gui_services_and_views.py`)
```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests/test_gui_services_and_views.py -v
```
- **Passed (5 tests):**
  - `test_project_paths_resolution` $\rightarrow$ **PASSED** (Remediated)
  - `test_configuration_service_profiles_and_guardrails` $\rightarrow$ **PASSED**
  - `test_database_service_mutex_and_protection` $\rightarrow$ **PASSED**
  - `test_main_window_all_10_screens_and_navigation` $\rightarrow$ **PASSED**
  - `test_runner_service_cooperative_cancellation` $\rightarrow$ **PASSED**
- **Blocked by Missing Fixture (2 tests):**
  - `test_environment_and_dataset_services` $\rightarrow$ FAILED (Missing `original_repo`)
  - `test_evaluation_and_report_export_services` $\rightarrow$ FAILED (Missing `original_repo`)

---

## 5. Task E — Integrity Verification Results

The official verification script was executed on historical outputs:
```powershell
& ".\.venv\Scripts\python.exe" scripts/verify_repo_integrity.py verify --root output --baseline output/replication_runs/manifests/historical_output_baseline_sha256.json
```
- **Verification Output:**
  ```json
  {
    "checked_at_utc": "2026-11-15T13:24:19.444179+00:00",
    "identical": true,
    "baseline_aggregate_sha256": "eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798",
    "current_aggregate_sha256": "eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798",
    "baseline_file_count": 30,
    "current_file_count": 30,
    "added_directories": [],
    "removed_directories": [],
    "added_files": [],
    "removed_files": [],
    "modified_files": []
  }
  ```
- **Finding:** All 30 historical experiment artifacts remain 100% byte-for-byte identical.
- **Protected Database Snapshot Record:** Preserved in `output/replication_runs/manifests/postgres_phase1_verification.json`:
  - `ontology_matching`: 162 rows
  - `syntactic_matching`: 162 rows
  - `lexical_matching`: 206 rows
  - `semantic_matching`: 258 rows

---

## 6. Summary of Changed Files in Stage 2.1

1. **`src/gui/paths.py`:** Added fallback discovery for `original_repo` inside `project_root`.
2. **`tests/test_gui_services_and_views.py`:** Stabilized project-root discovery assertion in `test_project_paths_resolution`.
3. **`tests/test_merger.py`:** Added `test_merge_alias_backward_compatibility` regression test.
4. **`docs/stage2_1_test_environment_remediation_report.md`:** Authored this complete remediation report.
5. **`docs/stage2_1_test_baseline_report.md`:** Authored the detailed test baseline breakdown.

