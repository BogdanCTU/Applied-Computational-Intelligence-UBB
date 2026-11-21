# User Guide and Application Manual

**Application:** C# Defect Predictor (Streamlit Workbench)  
**Entry Point:** `app.py` (`2_SourceCode/Python/app.py`)  
**System:** CISE Project 2 — Machine Learning-Based Bug Detection in C# Source Code  

---

## 1. System Requirements and Launch

| Requirement | Version / Details |
| :--- | :--- |
| Python | >= 3.11 (with packages from `requirements.txt`) |
| .NET SDK | 9.0 (`dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release`) |
| Git | Command-line client in system `PATH` |
| Network | Required only for GitHub repository discovery and cloning |

### Launch Commands

**Linux / macOS:**
```bash
source .venv/bin/activate
python -m streamlit run app.py
```

**Windows:**
```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run app.py
```
Or run `4_AppBuild\Windows\run_app.bat`.

---

## 2. Application Pages and Functionality

All pages share the unified `ModelManager.list_saved_models()` registry and reflect the class/file-level corpus alongside preserved legacy method-level artifacts.

| Page | Primary Controls | Outputs |
| :--- | :--- | :--- |
| **Dashboard** | Navigation only | Processed/registered repository counts, class observation label distribution, active champion model metrics & stored threshold from the unified registry, 5-stage class/file pipeline, and methodological constraints. |
| **Repository Collection** | Paginated GitHub discovery (`Batch Discovery`), checkpoint/run monitor (`Collection Runs & Progress`), manual URL import, repo sync/commit extraction | Composite selection rankings, exclusion reasons, checkpoint progress toward 100+ repositories, and per-repo mining stats. |
| **Bug Analysis & SZZ** | Strict bug-fix threshold slider, SZZ runner, class observation extractor & audit overrides (`1`, `0`, `-1`), legacy method tab | Classified bug-fixing commits, SZZ line-blame traces, and class-level pre-fix vs. post-fix code inspection with BIC provenance. |
| **Dataset Management** | Batch 40-metric class extraction, dataset snapshot viewer, boxplots across 40 features, custom snapshot builder & CSV/manifest export | Extraction counts, repository distribution table, feature distribution plots, and SHA-256 checksummed exports. |
| **Model Training** | Dataset selector (class or method), 6 model family options, hyperparameters, repository holdout ratio, inner-CV precision threshold optimization | Repository-separated GroupKFold CV vs. untouched holdout Precision/Recall/F1/ROC-AUC and serialized `.joblib` bundle with stored threshold. |
| **Model Evaluation** | Multi-model nested benchmark table, unified model selector, confusion matrix, ROC/PR curves, MDI & permutation importances, split provenance | Stored decision threshold, nested CV vs. holdout metrics, confusion matrices, and feature rankings. |
| **Real-World Bug Detection** | **Input A:** C# class editor; **Input B:** `.cs` file upload; repository class validation benchmark; prediction history & legacy method diagnostic | Class defect probability (`predict_proba()`), stored-threshold binary label (`Defect-Prone Class (1)` / `Candidate-Clean Class (0)`), risk category, 40 class metrics, file-level multi-class summary, and individual class drill-down. |
| **Settings** | GitHub PAT, collection concurrency/commit/checkpoint limits, Roslyn timeout, storage paths, risk tier sliders, unified default model selector | Session configuration updates and prediction history management. |

---

## 3. Prediction Semantics & File-Level Aggregation

1. **Class-Level Prediction (Primary Task):**
   - `defect_probability`: Estimated via `model.predict_proba(X_proc)[:, 1]`.
   - `predicted_label`: Explicitly computed by comparing `defect_probability >= bundle["decision_threshold"]` (never relying on an implicit `0.50` `model.predict()` cutoff when an optimized threshold is stored).
   - `risk_category`: Triage band based on `PredictionSettings` defaults (`Low risk <= 0.30`, `Medium risk 0.31–0.60`, `High risk > 0.60`), kept conceptually distinct from binary classification.
2. **File-Level Analysis (`.cs` Upload):**
   - Every `class`, `struct`, and `record` declared in the uploaded `.cs` file receives an independent `ClassPrediction`.
   - The file summary reports `classes_analyzed_count`, `classes_flagged_count`, `highest_class_risk_score`, `mean_class_risk_score`, `max_defect_probability`, and `file_risk_category`.
   - Elevated probabilities or flagged classifications indicate structural defect propensity supported by historical SZZ evidence, not formal verification of a confirmed defect.
3. **Legacy Method Compatibility:**
   - Preserved method-level bundles (`et_nested_opt_v3_depth6_leaf6_log2`, `rf_nested_opt_v3_depth6_leaf8_log2`, `exp_final_5fold_v2_best_rf_compact_regularized`, `rf_csharp_empirical_model`) remain selectable for the legacy single-method diagnostic view.

---

## 4. Troubleshooting

| Symptom | Cause | Corrective Action |
| :--- | :--- | :--- |
| `RoslynAnalyzer.dll` missing or build error | .NET 9.0 analyzer binary not compiled or `dotnet` not in `PATH` | Install .NET 9.0 SDK and run `dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release`. |
| Compatibility warning on Real-World Bug Detection page | A legacy method-level model is selected while analyzing a class/file | Select a `class`-granularity model (e.g. `class_precision_champion_v3`) in the Unified Registry dropdown. |
| GitHub API rate limit error | Unauthenticated GitHub API quota reached during discovery | Provide a GitHub Personal Access Token in **Settings** or `.env` (`GITHUB_TOKEN`), or resume from checkpoint. |
