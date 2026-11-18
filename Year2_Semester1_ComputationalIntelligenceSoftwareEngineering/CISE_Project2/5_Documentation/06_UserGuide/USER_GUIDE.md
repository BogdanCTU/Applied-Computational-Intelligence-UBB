# User Guide and Application Manual

**Application:** C# Defect Predictor (Streamlit Workbench)  
**Entry Point:** `app.py` (`2_SourceCode/Python/app.py`)  
**System:** CISE Project 2 — Machine Learning-Based Software Defect Prediction for C# Source Code  

---

## 1. System Requirements and Launch

| Requirement | Version / Details |
| :--- | :--- |
| Python | >= 3.11 (with packages from `requirements.txt`) |
| .NET SDK | 9.0 (`dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release`) |
| Git | Command-line client in system `PATH` |
| Network | Required only for GitHub repository search and cloning |

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

| Page | Primary Controls | Outputs |
| :--- | :--- | :--- |
| **Dashboard** | Navigation only | System summary metrics, observation class distribution table, latest SQLite registered model summary, 5-stage pipeline overview, and methodological constraints table. |
| **Repository Collection** | GitHub search filters, manual URL input, clone/pull, commit extraction, DB unlink | Discovered repository list, managed repositories table, sync status, and recent commit preview. |
| **Bug Analysis & SZZ** | Repository selector, bug-fix confidence slider, SZZ runner, observation extractors, label override buttons | Filtered commit list, SZZ line-blame trace table, and pre-fix/post-fix method inspection with manual label overrides (`1`, `0`, `-1`). |
| **Dataset Management** | Batch feature extraction, metric selector, snapshot builder, CSV exporter | Extraction progress, dataset snapshots table, class and evidence tables, boxplot distributions, correlation matrix, and CSV downloads. |
| **Model Training** | Dataset selector, Random Forest hyperparameter sliders, holdout ratio, `GroupKFold` fold count | Repository split counts, cross-validation vs. holdout metrics table, and saved `.joblib` model bundle. |
| **Model Evaluation** | Model selector, evaluation tabs | Accuracy/Precision/Recall/F1/ROC-AUC/PR-AUC metrics, confusion matrix, classification report, ROC/PR curves, MDI and permutation feature importances, and hyperparameters. |
| **Real-World Bug Prediction** | Model selector, C# method editor, `.cs` file uploader, repository validation benchmark, history controls | Method risk score (`[0.0, 1.0]`), risk category (`Low`, `Medium`, `High`), binary predicted class ($\tau = 0.50$), influential metrics table, all 26 Roslyn metrics, batch file CSV export, and validation error analysis. |
| **Settings** | GitHub PAT input, storage directory paths, Roslyn `.csproj` path, risk thresholds, privacy toggles | Session configuration updates and prediction history cleanup. |

---

## 3. Available Model Bundles and Threshold Configuration

| Model Name (`4_AppBuild/Assets/Models/`) | Estimator | Training Dataset | Role |
| :--- | :--- | :--- | :--- |
| `et_nested_opt_v3_depth6_leaf6_log2` | `ExtraTreesClassifier` | Dataset #2 ($N=578$, 5 repos) | Default selected model in Model Evaluation & Defect Prediction (Nested CV Rank #1 by ROC-AUC `0.7349` and Nested F1 `0.7667`) |
| `rf_nested_opt_v3_depth6_leaf8_log2` | `RandomForestClassifier` | Dataset #2 ($N=578$, 5 repos) | Optimized Random Forest variant (Outer ROC-AUC `0.7216`, Outer Brier `0.2055`, Nested F1 `0.7539`) |
| `exp_final_5fold_v2_best_rf_compact_regularized` | `RandomForestClassifier` | Dataset #2 ($N=578$, 5 repos) | Preserved baseline Random Forest model (Outer ROC-AUC `0.7037`, Nested F1 `0.7408`) |
| `rf_csharp_empirical_model` | `RandomForestClassifier` | Dataset #1 ($N=382$ train) | Preserved initial exploratory model registered in SQLite |

- **Binary Classification Threshold (`predicted_label`):** `BugPredictor` uses `model.predict()`, which applies the nominal $\tau = 0.50$ probability cutoff.
- **Risk Category Ceilings (`risk_category`):** `PredictionSettings` defaults to Low risk ($\le 0.30$), Medium risk ($0.31\text{--}0.60$), and High risk ($> 0.60$), adjustable in **Settings**.

---

## 4. Troubleshooting

| Symptom | Cause | Corrective Action |
| :--- | :--- | :--- |
| `RoslynAnalyzer.dll` missing or build error | .NET 9.0 analyzer binary not compiled or `dotnet` not in `PATH` | Install .NET 9.0 SDK and run `dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release`. |
| No models listed on Defect Prediction page | Model directory misconfigured or empty | Verify `4_AppBuild/Assets/Models/` contains `.joblib` bundles in **Settings**. |
| `Database locked` error | Concurrent write transaction on SQLite | Wait for active batch extraction/mining to complete; WAL mode handles concurrent reads. |
| GitHub API rate limit error | Unauthenticated GitHub API quota (60 requests/hr) reached | Provide a GitHub Personal Access Token in **Settings** or `.env` (`GITHUB_TOKEN`). |
