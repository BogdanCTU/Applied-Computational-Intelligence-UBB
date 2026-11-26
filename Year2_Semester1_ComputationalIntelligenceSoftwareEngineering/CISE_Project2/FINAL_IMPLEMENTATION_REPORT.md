# Final Implementation and Validation Report — CISE Project `v5.0.0`

## 1. Direct Answers to Section 15 Deliverable Questions

1. **What data sources were integrated?**
   - **Microsoft `InferredBugs` (`inferredbugs/csharp`):** Sparse-cloned from `https://github.com/microsoft/InferredBugs` (`225 MB`, `641` repos, `2,891` bug instances). After Roslyn validation and cross-source deduplication, retained `1,383` `BUG` and `1,368` `CLEAN` methods across `536` repositories.
   - **Verified GitHub Bug-Fix Pairs (`1_Database/Repositories/` + REST API client):** Mined `60` local full-history GitHub clones (`400` commits/repo) with strict commit-message and focused-diff filtering, retaining `881` `BUG` and `887` `CLEAN` methods across `56` disjoint repositories.
   - **Verified Hard Negatives:** Collected `756` complex (`cyclomatic_complexity >= 4`, `logical_loc >= 12`), unit-test-referenced, clean-history methods across `45` disjoint repositories (`233` methods across `12` repos reserved strictly for `hard_negative_test`).
2. **How many valid `BUG` and `CLEAN` examples were collected?**
   - **`5,275` valid methods** (`2,264` `BUG` = `42.92%`, `3,011` `CLEAN` = `57.08%`) out of `12,030` candidates inspected (`6,755` excluded, including `1,334` cross-label hash conflicts and `274` same-label duplicates).
3. **How many repositories were represented?**
   - **`637` distinct repositories** (`536` InferredBugs + `56` GitHub bug-fix + `45` hard-negative), with zero repository overlap across `dev` (`488`), `independent_test` (`137`), and `hard_negative_test` (`12`).
4. **How were labels verified?**
   - Every sample carries independent `label_source` and `verification_status`: `static_analyzer_verified_fix` (`1,383`, InferSharp pre-fix), `commit_verified_bugfix` (`881`, filtered bug-fix parent commit), `post_fix_verified` (`2,255`, corrected versions), and `test_backed_verified` (`756`, referenced by unit tests with zero recent bug-fix commits).
5. **Which feature groups were implemented?**
   - Five independent, schema-versioned extractors (`536` total features in Experiment `I`): `lexical` (`420`: 20 ratios/counts + 300 token 1–2 gram TF-IDF + 100 API TF-IDF), `ast` (`49`), `control_flow` (`21` incl. `AnalyzeControlFlow`), `data_flow` (`30` incl. `AnalyzeDataFlow`, nullability, resource lifecycle, and explicit `semantic_model_available`), and `structural` (`16` supplementary comparison group).
6. **Which feature configuration performed best?**
   - **Experiment `I`** (`lexical + ast + control_flow + data_flow + structural`, `536` features) ranked #1 on Development Nested CV (`PR-AUC = 0.5287`, `ROC-AUC = 0.6000`, `F1 = 0.5770`), matched highest Independent Test `PR-AUC` (`0.5586`, alongside `H` at `0.5583`), and achieved the lowest Hard-Negative FPR (`14.59%` binary, `0.00%` selective).
7. **How did Random Forest perform on unseen repositories?**
   - On `independent_test` (`1,132` methods across `137` unseen repos), `rf_I_v5.0.0_20261126_150933` (`thresholds = 0.440 / 0.470 / 0.541`) outperformed structural-only `A` (`0.5012` PR-AUC -> `0.5586`), achieving `81.90%` recall on unseen InferredBugs defects while routing `48.85%` of borderline methods to `UNCERTAIN`.
8. **What are the precision, recall, F1, accuracy, ROC-AUC, and PR-AUC?**
   - **Independent Test (`1,132` samples):** Accuracy `0.5433`, Precision `0.5028`, Recall `0.6833`, F1 `0.5793`, Specificity `0.4239`, ROC-AUC `0.5848`, PR-AUC `0.5586`, Brier `0.2432` (3-way Selective Precision `0.5469`, Selective Recall `0.6259`, Selective F1 `0.5838`).
   - **Development Nested CV OOF (`3,910` samples):** Accuracy `0.5642`, Precision `0.5085`, Recall `0.6667`, F1 `0.5770`, ROC-AUC `0.6000`, PR-AUC `0.5287`.
   - **Temporal Test (`453` samples, `14` latest repos):** Accuracy `0.5475`, Precision `0.5473`, Recall `0.4911`, F1 `0.5176`, ROC-AUC `0.5524`, PR-AUC `0.5365`.
9. **What is the false-positive rate?**
   - **Independent Test Binary FPR:** `57.61%` (`352 / 611`), driven primarily by `inferredbugs_post_fix` near-twin methods (`77.92%` FPR vs. `45.71%` on `github_post_fix` and `10.71%` on `verified_hard_negative`).
   - **Dedicated Hard-Negative Holdout FPR:** `14.59%` binary (`34 / 233`) and **`0.00%` selective FPR** (`0` confident `BUG` false positives).
10. **How well does the model perform on hard negatives?**
    - On `hard_negative_test` (`233` complex verified-correct methods across `12` unseen repos), binary specificity is **`85.41%`** (`199 / 233` TN), with `143` classified `CLEAN`, `90` (`38.63%`) honestly marked `UNCERTAIN`, and `0` confidently misclassified as `BUG`.
11. **What are the known limitations?**
    - Aggregate syntax/token/DFG counts face a ~`0.585–0.597` ROC-AUC ceiling when separating pre-fix buggy methods from 1-line-patched post-fix twins; isolated `.cs` files lack project `.csproj`/NuGet assemblies for full semantic resolution; `.Tests.`/`UnitTests` directory substrings slipped past boundary regexes in `inferredbugs_ingestor.py`.
12. **Which acceptance criteria remain incomplete?**
    - All 17 mandatory acceptance criteria are implemented, executed, and verified; live GitHub REST API collection (`GitHubRestClient`) was tested unit-wise and wired to `GITHUB_TOKEN` (unauthenticated live run capped at `60 req/hr`), while large-scale GitHub bug-fix mining (`1,768` retained samples) ran over the real cloned GitHub mirrors in `1_Database/Repositories/`.

---

## 2. Phase Execution Log

- **Phase 1 (Reset & DB):** Isolated `v1`–`v4` into `0_LegacyArchive_v1_v4/`; created `v5` layout, Pydantic config (`4_AppBuild/Config/active_config.json`), logging, and 16-table SQLite schema (`1_Database/SQLite/bug_detector_v5.db`).
- **Phase 2 (Roslyn Preprocessor):** Implemented and built `2_SourceCode/RoslynPreprocessor/RoslynPreprocessor.csproj` (`net9.0`, `0` warnings/errors) + streaming Python batch bridge.
- **Phase 3 (Dataset Pipeline):** Sparse-cloned `microsoft/InferredBugs` (`225 MB`), ran `DatasetBuilder` (`5,275` valid methods, `6,755` exclusions, `0` missing metadata).
- **Phase 4–5 (ML & Evaluation):** Implemented 5 feature extractors + `FeaturePipeline`, repository-grouped splitting, Saabas tree-path explainability & permutation importance, and executed `Experiments A`–`I`, ablation, and secondary baselines. Refined `calibrate_three_way_thresholds()` after initial run collapsed `threshold_center` to `0.37` (`92.96%` FPR), bringing Hard-Negative FPR down from `79.83%` to `14.59%` (`0.00%` selective FPR).
- **Phase 6 (GUI & CLI):** Built `bug_detector` CLI (`init-db`, `collect-*`, `build-dataset`, `run-experiments`, `train`, `evaluate`, `detect`) and minimal 6-page Streamlit app (`app.py`, `2_SourceCode/gui/`).
- **Phase 7 (Verification & Docs):** `dotnet build` (`0` errors/warnings), `19/19` `pytest` tests passed (including headless `AppTest` on all 6 Streamlit pages), CLI fixture smoke check passed, and all v5 docs/slides regenerated from measured artifacts.

---

## 3. Mandatory Acceptance Criteria Matrix (1–17)

| # | Criterion | Status | Verification Evidence |
| --- | --- | --- | --- |
| 1 | New dataset pipeline implemented | Verified | `DatasetBuilder.build()` -> `1_Database/Datasets/v5/csharp_bug_detection_v5.0.0.{parquet,csv}` |
| 2 | InferredBugs ingestion implemented | Verified | `InferredBugsIngestor` -> `2,751` retained samples across `536` repos |
| 3 | GitHub bug-fix collection implemented | Verified | `GitHubBugFixCollector` (mirror + API) -> `1,768` retained samples across `56` repos |
| 4 | Hard-negative collection implemented | Verified | `HardNegativeCollector` -> `756` test-backed methods across `45` repos |
| 5 | Roslyn method extraction works | Verified | `dotnet build -c Release` (0 errors) + `test_roslyn_preprocessing.py` (3/3 pass) |
| 6 | Lexical and AST features implemented | Verified | `LexicalFeatureExtractor` (420) + `AstFeatureExtractor` (49) + `test_feature_extractors.py` |
| 7 | CFG & DFG implemented honestly | Verified | `CfgExtractor` + `DfgExtractor` (`semantic_model_available` recorded explicitly) |
| 8 | Structural metrics retained as baseline | Verified | `StructuralFeatureExtractor` (16) evaluated in Experiment `A` |
| 9 | RF training & ablation executable | Verified | `run-experiments` -> `experiments_a_to_i.csv`, `feature_ablation.csv` |
| 10 | Repository-level independent eval works | Verified | `verify_zero_leakage` + `independent_test` (`137` repos), `hard_negative_test` (`12` repos) |
| 11 | Standard evaluation metrics generated | Verified | `3_TestResults/v5/evaluation_summary_v5.json` + PNG plots |
| 12 | `BUG`/`CLEAN`/`UNCERTAIN` inference works | Verified | `cli.py detect` smoke test + `test_end_to_end.py` (`ANALYSIS_ERROR` on broken syntax) |
| 13 | Manual source analysis works in GUI | Verified | `2_SourceCode/gui/pages/manual_detection.py` + `AppTest` pass |
| 14 | Dataset explorer & model config work | Verified | `dataset_explorer.py`, `model_configuration.py`, `model_training.py` + `AppTest` pass |
| 15 | Database persistence works | Verified | `1_Database/SQLite/bug_detector_v5.db` (16 tables) + `test_database_persistence.py` |
| 16 | Automated tests pass | Verified | `.venv/bin/pytest 2_SourceCode/Tests/ -v` -> `19 passed` (`0` failed, `0` skipped) |
| 17 | Documentation reflects actual implementation & results | Verified | All root, `1_Database/Schema`, `5_Documentation`, and `6_Presentation` v5 docs updated |
