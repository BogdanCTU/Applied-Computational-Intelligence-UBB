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
| **Dashboard** | Navigation only | System summary metrics, observation class distribution table, latest model summary, 5-stage pipeline overview, and methodological constraints table. |
| **Repository Collection** | GitHub search filters, manual URL input, clone/pull, commit extraction, DB unlink | Discovered repository list, managed repositories table, sync status, and recent commit preview. |
| **Bug Analysis & SZZ** | Repository selector, bug-fix confidence slider, SZZ runner, observation extractors, label override buttons | Filtered commit list, SZZ line-blame trace table, and pre-fix/post-fix method inspection with manual label overrides (`1`, `0`, `-1`). |
| **Dataset Management** | Batch feature extraction, metric selector, snapshot builder, CSV exporter | Extraction progress, dataset snapshots table, class and evidence tables, boxplot distributions, correlation matrix, and CSV downloads. |
| **Model Training** | Dataset selector, Random Forest hyperparameter sliders, holdout ratio, `GroupKFold` fold count | Repository split counts, cross-validation vs. holdout metrics table, and saved `.joblib` model bundle. |
| **Model Evaluation** | Model selector, evaluation tabs | Accuracy/Precision/Recall/F1/ROC-AUC/PR-AUC metrics, confusion matrix, classification report, ROC/PR curves, MDI and permutation feature importances, and hyperparameters. |
| **Real-World Bug Prediction** | Model selector, C# method editor, `.cs` file uploader, repository validation benchmark, history controls | Method risk score (`[0.0, 1.0]`), risk category (`Low`, `Medium`, `High`), predicted class, influential metrics table, all 26 Roslyn metrics, batch file CSV export, and validation error analysis. |
| **Settings** | GitHub PAT input, storage directory paths, Roslyn `.csproj` path, risk thresholds, privacy toggles | Session configuration updates and prediction history cleanup. |

---

## 3. Troubleshooting

| Symptom | Cause | Corrective Action |
| :--- | :--- | :--- |
| `RoslynAnalyzer.dll` missing or build error | .NET 9.0 analyzer binary not compiled or `dotnet` not in `PATH` | Install .NET 9.0 SDK and run `dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release`. |
| No models listed on Defect Prediction page | Model directory misconfigured or empty | Verify `4_AppBuild/Assets/Models/` contains `.joblib` bundles in **Settings**. |
| `Database locked` error | Concurrent write transaction on SQLite | Wait for active batch extraction/mining to complete; WAL mode handles concurrent reads. |
| GitHub API rate limit error | Unauthenticated GitHub API quota (60 requests/hr) reached | Provide a GitHub Personal Access Token in **Settings** or `.env` (`GITHUB_TOKEN`). |
