# Automated Test Execution Report

**Date:** 2026-11-14  
**Environment:** Python 3.13.17 / Windows / pytest 9.2.0  
**Target:** `2_SourceCode/Tests/`  
**System:** CISE Project 2 — Machine Learning-Based Software Defect Prediction for C# Source Code  

---

## 1. Summary of Execution

```text
============================= test session starts =============================
platform win32 -- Python 3.13.17, pytest-9.2.0, pluggy-1.7.0
rootdir: CISE_Project2
configfile: pytest.ini
testpaths: 2_SourceCode/Tests
plugins: anyio-4.16.0, mock-3.17.0
collected 121 items

2_SourceCode/Tests/test_bug_fix_detector.py ...                          [  2%]
2_SourceCode/Tests/test_bug_predictor.py .......                         [  8%]
2_SourceCode/Tests/test_commit_collector.py ..                           [  9%]
2_SourceCode/Tests/test_config.py .                                      [ 10%]
2_SourceCode/Tests/test_database.py ...                                  [ 13%]
2_SourceCode/Tests/test_dataset_builder_and_exporter.py ...              [ 15%]
2_SourceCode/Tests/test_experiment_runner.py .......                     [ 21%]
2_SourceCode/Tests/test_fluentvalidation_pilot.py ..                     [ 23%]
2_SourceCode/Tests/test_github_client.py ......                          [ 28%]
2_SourceCode/Tests/test_label_manager.py ...                             [ 30%]
2_SourceCode/Tests/test_ml_pipeline.py ......                            [ 35%]
2_SourceCode/Tests/test_model_baselines.py .....                         [ 39%]
2_SourceCode/Tests/test_repository_manager.py ...                        [ 42%]
2_SourceCode/Tests/test_roslyn_metrics.py ......                         [ 47%]
2_SourceCode/Tests/test_source_classifier.py ........................... [ 80%]
.....................                                                    [ 97%]
2_SourceCode/Tests/test_szz_analyzer.py ...                              [100%]

============================ 121 passed in 32.62s =============================
```

---

## 2. Test Module Breakdown

| Test File | Test Count | Status | Domain Covered |
| :--- | :---: | :---: | :--- |
| `test_bug_fix_detector.py` | 3 | PASS | Regex bug-fix identification and keyword filtering |
| `test_bug_predictor.py` | 7 | PASS | Model inference, risk categorization, feature importances |
| `test_commit_collector.py` | 2 | PASS | Git commit mining, diff parsing, and C# file detection |
| `test_config.py` | 1 | PASS | Settings validation and path resolution |
| `test_database.py` | 3 | PASS | SQLite connection, table schemas, and foreign-key integrity |
| `test_dataset_builder_and_exporter.py`| 3 | PASS | Feature aggregation, dataset creation, and CSV export |
| `test_experiment_runner.py` | 7 | PASS | 5-Fold GroupKFold CV execution and metric calculation |
| `test_fluentvalidation_pilot.py` | 2 | PASS | Production source filtering on pilot repository |
| `test_github_client.py` | 6 | PASS | GitHub API rate-limit handling and repository discovery |
| `test_label_manager.py` | 3 | PASS | SZZ label assignment and observation persistence |
| `test_ml_pipeline.py` | 6 | PASS | End-to-end training, preprocessing, and model saving |
| `test_model_baselines.py` | 5 | PASS | Benchmark evaluation against 11 baseline algorithms |
| `test_repository_manager.py` | 3 | PASS | Git clone lifecycle and disk storage management |
| `test_roslyn_metrics.py` | 6 | PASS | Roslyn AST compilation and 26 static metric outputs |
| `test_source_classifier.py` | 61 | PASS | Strict production vs. test C# file filtering rules |
| `test_szz_analyzer.py` | 3 | PASS | Git blame line attribution and BIC identification |
| **TOTAL** | **121** | **PASS** | **100% Pass Rate (0 failures, 0 skipped, 0 errors)** |

