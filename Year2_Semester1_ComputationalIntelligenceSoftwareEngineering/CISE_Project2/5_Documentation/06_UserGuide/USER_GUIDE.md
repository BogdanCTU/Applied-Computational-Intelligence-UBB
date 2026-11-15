# User Guide & Application Manual

**Application:** C# Defect Predictor (Streamlit Web Workbench)  
**Entry Point:** `app.py` or `2_SourceCode/Python/app.py`  
**System:** CISE Project 2 — Machine Learning-Based Software Defect Prediction for C# Source Code  

---

## 1. Quick Start

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Microsoft .NET 9.0 SDK
- Git command-line client

### Launching the Application
On Windows, you can launch the application with one click using:
```cmd
4_AppBuild\Windows\run_app.bat
```
Or manually from PowerShell / Terminal:
```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run app.py
```
*(Alternatively, `streamlit run app.py` can be used directly once the virtual environment is activated).*
The application will open in your default browser at `http://localhost:8501`.

---

## 2. Page-by-Page Walkthrough

The application sidebar provides navigation between 8 specialized tabs:

### Tab 1: Dashboard
- **Overview:** Displays global system statistics: total registered repositories, cloned repositories, mined commits, bug-fixing commits, total observations (defect-prone vs. candidate-clean), generated datasets, and registered models.
- **Workflow:** Review the current state of the database and summary metrics.

### Tab 2: Repository Collection
- **Overview:** Interface for discovering, registering, and cloning open-source C# projects from GitHub.
- **Features:** Search GitHub by keywords or language; view star counts and sizes; trigger automated local cloning via Git.

### Tab 3: Bug Analysis & SZZ
- **Overview:** Inspect mined commit logs and run the SZZ heuristic.
- **Features:** Filter commits by bug-fixing confidence; view regex evidence; execute line-blame tracing (`git blame -w -M -C`) to discover Bug-Inducing Commits (BICs); extract pre-fix method code.

### Tab 4: Dataset Management
- **Overview:** Create, version, and export machine learning datasets.
- **Features:** Select repository cohorts; inspect observation class balance; generate structured CSV datasets with the 26 Roslyn-extracted static code metrics; view dataset metadata JSON.

### Tab 5: Model Training
- **Overview:** Train candidate machine learning classifiers on exported datasets.
- **Features:** Configure hyperparameters (e.g., number of trees, max depth); select validation schemes (Random Split vs. Repository GroupKFold); monitor training progress.

### Tab 6: Model Evaluation
- **Overview:** Detailed performance analysis and benchmark comparisons.
- **Features:** Inspect confusion matrices, ROC curves, Precision-Recall curves, classification reports, threshold sweep curves, and cross-validation fold breakdowns.

### Tab 7: Real-World Bug Prediction
- **Overview:** Interactive, real-time defect risk analysis for C# methods and files.
- **Usage:**
  1. Paste a C# class or method into the text editor, or upload a `.cs` file.
  2. Click **"Analyze Method & Predict Defect Risk"**.
  3. The system parses the code via the Roslyn AST analyzer, extracts the 26 static features, and feeds them into the trained Random Forest model.
  4. View the resulting risk classification:
     - **Low Risk:** Risk score below low threshold ($\le 0.35$).
     - **Medium Risk:** Risk score between thresholds ($0.35 - 0.65$).
     - **High Risk:** Risk score exceeding high threshold ($> 0.65$).
  5. Inspect the influential features (e.g. `method_length`, `cyclomatic_complexity`, `parameter_count`) explaining the prediction.

### Tab 8: Settings
- **Overview:** Application configuration and diagnostic tools.
- **Features:** Inspect active file paths (database, models, datasets, Roslyn binary); test Roslyn analyzer connectivity; configure risk score thresholds and privacy logging.

---

## 3. Troubleshooting

| Symptom | Probable Cause | Resolution |
| :--- | :--- | :--- |
| `RoslynAnalyzer.dll not found` | The .NET analyzer has not been compiled. | Run `dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release`. |
| `No model loaded` in Tab 7 | Model asset path not resolved. | Verify that `4_AppBuild/Assets/Models/rf_csharp_empirical_model.joblib` exists. |
| `Database locked` error | Another process is holding an exclusive SQLite write lock. | Ensure only one instance of the app is writing, or restart the app (WAL mode handles concurrent readers). |
| GitHub API rate limit error | Anonymous API quota exhausted. | Set `GITHUB_TOKEN=your_token` in `.env` file at repository root. |

