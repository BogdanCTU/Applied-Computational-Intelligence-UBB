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
