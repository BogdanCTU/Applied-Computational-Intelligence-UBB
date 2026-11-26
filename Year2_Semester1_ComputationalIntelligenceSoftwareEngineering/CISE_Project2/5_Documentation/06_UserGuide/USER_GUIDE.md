# User Guide and Application Manual (`v4.0.0`)

**Application:** C# Bug Detection Classifier (Streamlit Workbench)  
**Entry Point:** `app.py` (`2_SourceCode/Python/app.py`)  
**System:** CISE Project 2 — Machine Learning-Based C# Bug Detection Classifier  

---

## 1. System Requirements and Launch

| Requirement | Version / Details |
| :--- | :--- |
| Python | >= 3.11 (`.venv` environment) |
| .NET SDK | 9.0 (`dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release`) |
| Git | Command-line client in system `PATH` |
| Network | Required only for GitHub repository discovery and cloning |

### Launch Commands
```bash
# macOS / Linux
.venv/bin/streamlit run 2_SourceCode/Python/app.py
```

---

## 2. Application Pages and Functionality

All pages read from the unified `ModelManager.list_saved_models()` registry (`class_bug_classifier_top200_v4` is prioritized first; auxiliary `method_localizer` bundles are automatically paired during inference and hidden from the primary classifier selector).

| Page | Primary Controls | Outputs |
| :--- | :--- | :--- |
| **Dashboard** | Navigation & model status | Processed repository count (`200+`), BUG/CLEAN label totals, active classifier threshold/metrics, 5-stage pipeline diagram, and static-indicator scope disclaimer. |
| **Repository Collection** | Paginated GitHub star-desc discovery, checkpoint monitor (`run_top200_csharp_pipeline`), manual repo import, commit sync | Top-200 star ranking, transparent exclusion reasons, checkpoint progress, and mining statistics. |
| **Bug Analysis & SZZ** | Bug-fix threshold slider, SZZ runner, class & method/line localization inspector, legacy method tab | Classified bug-fix commits, SZZ traces, `class_bug_localizations` verified methods & line ranges, and pre-fix vs. post-fix inspection. |
| **Dataset Management** | Batch 40-metric class extraction, dataset snapshot viewer, boxplots, CSV/manifest export | Extraction counts, Top-200 repository distribution, SHA-256 checksummed CSV (`csharp_class_top200_v4`), and method localization corpus stats. |
| **Model Training** | Dataset selector, ML family selection, repository holdout ratio, inner-CV threshold optimization | Repository-separated CV vs. holdout Precision/Recall/F1/ROC-AUC/PR-AUC/FPR/FNR and versioned `.joblib` bundle. |
| **Model Evaluation** | Multi-model nested benchmark (`12` v4 configs), confusion matrix, ROC/PR curves, feature importances | Outer CV vs. holdout metrics, FPR/FNR rates, confusion matrices, and repository split provenance. |
| **Real-World Bug Detection** | **Tab 1:** Paste C# Class; **Tab 2:** Upload `.cs` File (single/multi-class); **Tab 3:** Repo Validation Benchmark; **Tab 4:** Prediction History & Legacy Method Diagnostic | Explicit **`BUG DETECTED`** (`st.error`) / **`CLEAN`** (`st.success`) verdict, secondary probability & confidence, **Verified Historical SZZ Locations** vs. **ML-Estimated Suspicious Methods**, per-class table + overall `.cs` file counts, and **`ANALYSIS INCOMPLETE`** warning on syntax errors. |
| **Settings** | GitHub PAT, Top-200 collection limits (`target=200`, `max_size_kb=120000`), Roslyn timeout, storage paths, default classifier selector | Session config updates and SQLite history management. |

---

## 3. Interpreting Predictions & Bug Localization

1. **Class Verdict (`BUG DETECTED` vs. `CLEAN`):**
   - Each extracted `class`, `struct`, or `record` is scored independently via `defect_probability = predict_proba(X_proc)[:, 1]`.
   - When `defect_probability >= decision_threshold` (`0.520` for `class_bug_classifier_top200_v4`), the verdict is **`BUG DETECTED`** (`classification="BUG"`); otherwise **`CLEAN`** (`classification="CLEAN"`).
   - Confidence (`confidence`) and raw probability are shown strictly as secondary context.
2. **Distinguishing Localization Sources:**
   - **Verified Historical SZZ Evidence (SQLite Match):** Shown only when the analyzed class matches a stored revision in `class_bug_localizations`—displays exact pre-fix commit SHAs, affected method signatures, and historical line ranges.
   - **ML-Estimated Suspicious Methods (`method_localizer_top200_v4.joblib`):** For unseen `BUG` classes without historical SZZ matches, ranks methods inside the class by standalone method defect score and shows method declaration line ranges explicitly labeled as **ML-estimated (not verified ground truth)**.
   - **Unavailable Exact Lines:** On unseen code, exact buggy line numbers are explicitly displayed as **`unavailable`**. Class-level feature drivers explain why the class resembles buggy history statistically, never claiming line proof.
3. **Multi-Class `.cs` Files & Syntax Failures:**
   - Multi-class `.cs` uploads evaluate every valid class independently and present an overall summary (`Analyzed`, `BUG`, `CLEAN`, `Failed/Syntax Errors`).
   - If Roslyn reports syntax errors (`syntax_error_count > 0`) or any class fails extraction (`classes_failed_count > 0`), the file verdict is **`ANALYSIS INCOMPLETE`** (or **`BUG (PARTIAL ANALYSIS)`** if another class flagged BUG) and **never `CLEAN`**.

---

## 4. Troubleshooting

| Symptom | Cause | Corrective Action |
| :--- | :--- | :--- |
| `RoslynAnalyzer.dll` missing | .NET 9.0 Release binary not compiled | Run `dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release`. |
| Granularity mismatch warning | Legacy method model active on class/file view | Select `class_bug_classifier_top200_v4` from the classifier dropdown. |
| `NoClassesFoundError` | Pasted snippet contains only top-level statements or unparseable syntax with 0 valid classes | Wrap code inside a complete `class`, `struct`, or `record` declaration and fix syntax errors. |
| GitHub rate-limit hit | Unauthenticated API quota reached | Set `GITHUB_TOKEN` in `.env` or **Settings**, then resume from checkpoint. |
