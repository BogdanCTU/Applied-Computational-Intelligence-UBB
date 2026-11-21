# Release Notes — Version 1.0.0 (Updated with Nested Model Optimization)

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Babeș-Bolyai University, Faculty of Mathematics and Computer Science  

---

## 1. Overview

This release provides an empirical machine-learning pipeline and local Streamlit workbench for method-level defect prediction in C# source code using 26 static Abstract Syntax Tree (AST) metrics extracted via Microsoft Roslyn (`.NET 9.0`).

---

## 2. Deliverables and Experimental Results

### A. Datasets and Labeling
- **Repositories Mined:** 7 open-source C# repositories (`Humanizer`, `Serilog`, `MediatR`, `Polly`, `FluentValidation`, `CommandLineParser`, `Newtonsoft.Json`).
- **Labeling:** SZZ line-blame attribution (`git blame -w -M -C`) for defect-prone methods (`label = 1`, pre-fix revision) and `HEAD` sampling under the Open-World Assumption for candidate-clean methods (`label = 0`).
- **Dataset #1 (`csharp_empirical_v1` v1.0.0):** 483 methods across 3 repositories (226 defect-prone, 257 candidate-clean).
- **Dataset #2 (`csharp_empirical_v2` v2.0.0):** 578 production methods across 5 repositories (279 defect-prone, 299 candidate-clean, 0 test files).

### B. Baseline and Nested Model Optimization (`Dataset #2`, $N = 578$)

| Model Artifact | Estimator | Validation Protocol | Outer ROC-AUC | Outer Brier | Nested $\tau_{\text{inner}}^*$ F1 | Pooled OOF F1 ($\tau_{\text{inner}}^*$) | Pooled OOF Recall | Pooled OOF Precision | Pooled OOF Accuracy |
| :--- | :--- | :--- | :---: | :---: | :---: | ---: | ---: | ---: | ---: |
| `exp_final_5fold_v2_best_rf_compact_regularized.joblib` | `RandomForestClassifier` (Baseline) | $5 \times 4$ Nested `GroupKFold` | 0.7037 ± 0.1292 | 0.2146 ± 0.0398 | 0.7408 ± 0.0760 | 0.7294 | 88.89% | 61.85% | 68.17% |
| `rf_nested_opt_v3_depth6_leaf8_log2.joblib` | `RandomForestClassifier` (Optimized) | $5 \times 4$ Nested `GroupKFold` | 0.7216 ± 0.1156 | 0.2055 ± 0.0374 | 0.7539 ± 0.0706 | 0.7406 | 88.53% | 63.66% | 70.07% |
| `et_nested_opt_v3_depth6_leaf6_log2.joblib` | `ExtraTreesClassifier` (Optimized) | $5 \times 4$ Nested `GroupKFold` | 0.7349 ± 0.0703 | 0.2062 ± 0.0213 | 0.7667 ± 0.0723 | 0.7653 | 91.76% | 65.64% | 72.84% |

- **Historical Baseline Holdout (`JamesNK/Newtonsoft.Json`, $N = 159$):** Evaluated once for the baseline `rf_compact_regularized` model prior to optimization (at $\tau = 0.50$: Accuracy 74.21%, Precision 69.79%, Recall 84.81%, F1 0.7657, ROC-AUC 0.8209, Brier 0.1713; at unnested CV threshold $\tau^* = 0.40$: Accuracy 75.47%, Precision 69.61%, Recall 89.87%, F1 0.7845). `Newtonsoft.Json` was excluded from the nested optimization study; the optimized models have not yet been evaluated on a new unseen repository.

### C. Streamlit Workbench and Inference Configuration
- Eight pages: Dashboard, Repository Collection, Bug Analysis & SZZ, Dataset Management, Model Training, Model Evaluation, Defect Prediction, and Settings.
- Live inference in `BugPredictor` uses `model.predict()` ($\tau = 0.50$) for binary `predicted_label` and maps `predict_proba()` to Low ($\le 0.30$), Medium ($0.31\text{--}0.60$), and High ($> 0.60$) risk categories.


---

# Release Notes — Version 3.0.0 (100+ Repository Class & File-Level Transformation)

**Release Date:** November 21, 2026  
**Scope:** Full research & engineering transformation from a 5-repository method-level predictor into a 106-repository class- and file-level static C# bug detection platform optimized for high precision (`>= 80%`).

## Major Highlights

1. **106-Repository Empirical C# Class Corpus (`csharp_class_empirical_v3` v3.0.0)**
   - Expanded GitHub discovery (`github_client.py`), shallow-free full-history clone handling (`repository_manager.py`), single-call Git log ingestion (`commit_collector.py`), strict bug-fix commit filtering (`bug_fix_detector.py`), and cached SZZ blame tracing (`szz_analyzer.py`).
   - Built a resumable, checkpointed pipeline (`2_SourceCode/Scripts/run_100_repo_class_pipeline.py`) that mined `300` candidate repos (`304` queued), documented `15` exclusions, and processed **`106` repositories** (`0` failures) yielding **`5,711` class observations** (`2,829` defect-prone, `2,882` candidate-clean; SHA-256 `7087edb5...`).

2. **Roslyn Analyzer `v3.0.0` (40 Class Metrics + Multi-Class `.cs` Support)**
   - Extended `2_SourceCode/RoslynAnalyzer/Program.cs` with C# `LanguageVersion.Latest` parsing, isolated class/struct/record extraction (`GetTypeOwnedNodes<T>`), `--batch-stdin` NDJSON streaming, 40 class-level static metrics, and full backward compatibility for the original 26 method-level metrics.

3. **Precision-Optimized ML Engine (7 Model Families)**
   - Evaluated `DummyClassifier`, `LogisticRegression`, `DecisionTreeClassifier`, `RandomForestClassifier`, `ExtraTreesClassifier`, `HistGradientBoostingClassifier`, and `CalibratedClassifierCV` using strict repository-grouped `5x4` Nested `GroupKFold` (`84` dev repos / `4,730` classes) plus an untouched `22`-repository holdout (`981` classes).
   - Selected `class_precision_champion_v3` (`rf_opt_depth12_leaf4_log2` with inner-CV decision threshold `tau = 0.600`), achieving **82.30% precision / 61.71% recall** in Nested CV OOF and **83.43% precision / 61.99% recall / 0.8449 ROC-AUC** on the untouched holdout — surpassing both the `>= 75%` minimum and `>= 80%` preferred precision targets without holdout leakage.
   - Deployed 8 versioned class-level `.joblib` bundles alongside all 4 preserved historical method-level bundles.

4. **Class & Full `.cs` File Streamlit Application**
   - Updated `2_SourceCode/Python/app.py` and all 8 Streamlit pages under `2_SourceCode/Python/application/pages/` via a unified `ModelManager` registry.
   - Updated `BugPredictor` (`predict_class_code`, `predict_csharp_file`, plus legacy `predict_method_code`) to classify directly against `predict_proba()[:, 1] >= decision_threshold`.

5. **Historical Preservation**
   - Preserved all v1/v2 method-level CSVs (`csharp_empirical_v1_v1.0.0.csv`, `csharp_empirical_v2_v2.0.0.csv`), all 4 historical `.joblib` bundles, all original SQLite `observations`/`features` rows, a pre-migration DB archive (`bug_detection_method_v2_archive.db`), and historical `3_TestResults/CrossValidation` and `HoldoutEvaluation` JSON reports intact.
