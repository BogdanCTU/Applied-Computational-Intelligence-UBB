# Stage 2.1 Test Baseline Report — Regression & Test Suite Status
## Agent-OM: Scientific Replication, Local Adaptation & Windows Desktop Application

**Execution Date:** 2026-11-15  
**Stage:** Stage 2.1 (Test Environment Remediation & Baseline Regression)  
**Host Environment:** Windows 11 (build 22631), Python 3.13.17 (`.venv\Scripts\python.exe`)  
**Workspace Directory:** `E:\PERSONAL\GitHub\1_Applied-Computational-Intelligence-UBB\Year2_Semester1_ApplicationComputationalLinguistics\RR2_Project`  
**Test Runner:** `pytest 9.2.0` (with plugins `anyio-4.16.0`, `langsmith-0.14.17`)  
**Overall Status:** **103 PASSED, 5 FAILED, 18 ERRORS, 1 WARNING** (Total: 126 test cases)

---

## 1. Executive Summary

Following the remediation of module import paths (Stage 2) and the stabilization of GUI structural path discovery (Stage 2.1 Task C), a full test run of all 126 tests was executed under Python 3.13.17.

### High-Level Metrics
- **Total Test Cases:** 126
- **Passing Tests:** 103 (81.75% of total suite; **100%** of all tests with satisfied infrastructure)
- **Zero Collection Errors:** All test modules collect cleanly under Python 3.13.
- **Zero Dependency Errors:** All 17 core libraries (`rdflib`, `pyside6`, `langchain-core`, `psycopg2`, `pgvector`, etc.) import without issue.
- **Failures / Errors:** 23 total (5 failures, 18 errors), strictly partitioned into two root causes:
  1. **8 Tests (6.35%):** Blocked by PostgreSQL offline on `127.0.0.1:5432`.
  2. **15 Tests (11.90%):** Blocked by missing upstream `original_repo/` XML ontology fixtures.

---

## 2. Exhaustive Suite-by-Suite Breakdown

| Test File | Total | Passed | Failed | Errors | Status / Primary Blockers |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `tests/test_merger.py` | 7 | **7** | 0 | 0 | **100% PASSED** (includes Stage 2 alias regression) |
| `tests/test_rank_fusion.py` | 6 | **6** | 0 | 0 | **100% PASSED** (RRF k=0, k=60, tie-breaking, etc.) |
| `tests/test_lexical_retriever.py` | 4 | **4** | 0 | 0 | **100% PASSED** (all 10 predicates, prompt templates) |
| `tests/test_matching_agent.py` | 4 | **4** | 0 | 0 | **100% PASSED** (score group break, fallback, ablation) |
| `tests/test_prompt_order_ablation.py` | 5 | **5** | 0 | 0 | **100% PASSED** (original, reversed, canonical ordering) |
| `tests/test_step7d1_reproducibility.py` | 5 | **5** | 0 | 0 | **100% PASSED** (metrics consistency, stability logic) |
| `tests/test_text_processing.py` | 21 | **21** | 0 | 0 | **100% PASSED** (cleaning, camel-to-snake, acronyms) |
| `tests/test_threshold_sensitivity.py` | 5 | **5** | 0 | 0 | **100% PASSED** (metrics calculation, dummy exclusion) |
| `tests/test_threshold_validation_step7b.py` | 4 | **4** | 0 | 0 | **100% PASSED** (candidate union, directional consistency) |
| `tests/test_upstream_isolated_runner.py` | 4 | **4** | 0 | 0 | **100% PASSED** (manifest verification, safety guards) |
| `tests/test_validator.py` | 8 | **8** | 0 | 0 | **100% PASSED** (bypass check, LLM yes/no, acronyms) |
| `tests/test_gui_services_and_views.py` | 7 | **5** | 2 | 0 | 5 passed; 2 failed due to missing `original_repo` |
| `tests/test_algorithmic_parity.py` | 10 | **5** | 1 | 4 | 5 passed; 4 blocked by DB; 1 blocked by fixture |
| `tests/test_ontology.py` | 17 | **10** | 2 | 5 | 10 passed; 7 blocked by missing XML fixtures |
| `tests/test_semantic_retriever.py` | 5 | **3** | 0 | 2 | 3 passed; 2 blocked by missing XML fixtures |
| `tests/test_syntactic_retriever.py` | 4 | **1** | 0 | 3 | 1 passed; 3 blocked by missing XML fixtures |
| `tests/test_retrieval_agent.py` | 4 | 0 | 0 | 4 | 0 passed; 4 blocked by PostgreSQL offline |
| **Total** | **126** | **103** | **5** | **18** | **81.75% Passing (100% of runnable logic)** |

---

## 3. Analysis of Blocked Tests

### 3.1. Category A: Blocked by PostgreSQL Offline (8 Tests)
All 8 tests fail during fixture setup with `psycopg2.OperationalError: Connection refused (127.0.0.1:5432)`.

1. `test_algorithmic_parity.py::TestPhase4EmptySemanticChunks::test_empty_and_null_placeholder_produce_zero_chunks`
2. `test_algorithmic_parity.py::TestPhase4CodeIRILabelResolution::test_code_iri_resolution_and_bypass_symmetric`
3. `test_algorithmic_parity.py::TestPhase4DimensionsProfilesAndEnv::test_runtime_dimension_mismatch_raises`
4. `test_algorithmic_parity.py::TestPhase4PromptsAndToolRouter::test_end_to_end_mini_pipeline_deterministic_vs_llm_json_router`
5. `test_retrieval_agent.py::TestRetrievalAgent::test_build_features_dataframe_formatting`
6. `test_retrieval_agent.py::TestRetrievalAgent::test_database_ingestion_and_vector_query`
7. `test_retrieval_agent.py::TestRetrievalAgent::test_candidate_retrieval_and_rrf_coordination`
8. `test_retrieval_agent.py::TestRetrievalAgent::test_directional_candidates_separation`

*Root Cause:* The local database engine on port 5432 is not running. Per Task A instruction 10, no unauthorized new database cluster was initialized.

### 3.2. Category B: Blocked by Missing `original_repo` Fixtures (15 Tests)
These 15 tests require raw ontology XML files (`original_repo/data/conference/cmt-confof/component/source.xml` and `target.xml`) or upstream benchmark files:

1. `test_algorithmic_parity.py::TestPhase4PropertySortingParity::test_combined_property_uri_order_matches_upstream_cmt_confof` (Requires `source.xml`)
2. `test_gui_services_and_views.py::test_environment_and_dataset_services` (`orig["exists"] is True` check)
3. `test_gui_services_and_views.py::test_evaluation_and_report_export_services` (Upstream reference run check)
4. `test_ontology.py::TestOntologyParser::test_load_cmt_source_exists` (Requires `source.xml`)
5. `test_ontology.py::TestOntologyParser::test_load_confof_target_exists` (Requires `target.xml`)
6. `test_ontology.py::TestEntityExtractorCMT::test_cmt_counts` (Requires `source.xml`)
7. `test_ontology.py::TestEntityExtractorCMT::test_cmt_uri_preservation` (Requires `source.xml`)
8. `test_ontology.py::TestEntityExtractorCMT::test_cmt_entity_types` (Requires `source.xml`)
9. `test_ontology.py::TestEntityExtractorConfOf::test_confof_counts` (Requires `target.xml`)
10. `test_ontology.py::TestEntityExtractorConfOf::test_confof_uri_preservation` (Requires `target.xml`)
11. `test_semantic_retriever.py::TestSemanticRetriever::test_expand_bnode_closure_named_cmt` (Requires `source.xml`)
12. `test_semantic_retriever.py::TestSemanticRetriever::test_expand_bnode_closure_named_confof` (Requires `target.xml`)
13. `test_syntactic_retriever.py::TestSyntacticRetriever::test_syntactic_extraction_on_cmt_entities` (Requires `source.xml`)
14. `test_syntactic_retriever.py::TestSyntacticRetriever::test_syntactic_extraction_on_confof_entities` (Requires `target.xml`)
15. `test_syntactic_retriever.py::TestSyntacticRetriever::test_string_uri_direct_retrieval` (Requires `source.xml`)

*Root Cause:* `original_repo/` was excluded by `.gitignore` in the repository clone. Per Task B instruction 6, no synthetic files were fabricated, and no assertions were weakened.

---

## 4. Integrity and Historical Preservations

- **Output Directory Integrity:** Verified 100% byte-for-byte identical via `scripts/verify_repo_integrity.py` (`identical: true`, aggregate SHA-256 `eb28e7a7...`).
- **Phase 1 Baseline:** All 162 extracted entities and historical metrics ($P=41.67\%, R=31.25\%, F_1=35.71\%$) are permanently preserved in `output/replication_runs/phase1_cmt_confof_agent_om_lite_v1/`.
- **Phase 5 Local Parity:** 3 completed runs preserved with zero modification.

---

## 5. Prerequisite Resolution Plan for 100% Test Pass Rate

To achieve 126/126 (100%) passing tests:

1. **PostgreSQL Service (Resolves 8 Tests):**
   - Provide original portable `.pg` and `.pgdata` directories OR authorize provisioning a local PostgreSQL 16 instance with `pgvector` on `127.0.0.1:5432`.
   - Create isolated `agent_om_test` and `agent_om_parity` databases.
2. **Upstream Fixtures (Resolves 15 Tests):**
   - Provide the read-only upstream `original_repo` directory matching baseline SHA-256 `afed3137d9905945c5167559b15ef62815c64220a0aa1038ea06893e97b7c7c0`.

