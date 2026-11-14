# C# Defect Predictor: Machine Learning-Based Software Bug Detection

An academic-grade, fully local Machine Learning system for predicting software defect proneness in C# source code methods using **Multi-Model Supervised Learning (Random Forest Ensembles, Decision Trees, Logistic Regression, Dummy Baselines)** and static code metrics extracted via **Microsoft Roslyn**.

Developed for the Computational Intelligence in Software Engineering curriculum.

---

## 🚀 Key Capabilities

- **Automated GitHub Discovery & Cloning**: Query public C# repositories via GitHub REST API, clone full histories, and track commit diffs incrementally.
- **Bug-Fix & SZZ Traceability**: Identify bug-fixing commits via commit message heuristics and issue/PR references; trace candidate Bug-Inducing Commits (BICs) using `git blame -w -M -C`.
- **Roslyn Static Code Metrics**: Cross-platform .NET 9.0 CLI calculating 26 structural, complexity, and OOP metrics using `Microsoft.CodeAnalysis.CSharp`. Isolates enclosing methods from nested lambdas/local functions and normalizes newlines across platforms.
- **Zero-Leakage ML Pipeline**: Enforces repository-aware data partitioning (`GroupShuffleSplit` on `repository_id`), ensuring code from the same repository never leaks between training and test sets.
- **Multi-Model Benchmarking & Dual Importances**: Supervised classification benchmarked across Random Forest, Decision Tree, Logistic Regression, and DummyClassifier baselines. Evaluated with repository-aware `GroupKFold` cross-validation and analyzed via **MDI (Gini)** and **Permutation Feature Importance** with out-of-fold threshold tuning.
- **Real-Time Method & File Bug Prediction**: Interactive Streamlit interface to paste C# snippets or upload complete `.cs` files, extract Roslyn metrics live, estimate defect risk scores, identify influential metrics, and export CSV reports.
- **Privacy-Preserving & Fully Local**: Operates 100% on the local workstation. No external LLMs, no paid APIs, no telemetry, and raw source code is never stored without explicit user consent.

---

## 🏗️ System Architecture

```mermaid
flowchart LR
    subgraph DataCollection[1. Data Collection]
        GH[GitHub REST API] --> Cloner[RepositoryManager]
        Cloner --> Commits[CommitCollector]
    end

    subgraph MiningSZZ[2. Mining & SZZ]
        Commits --> FixDetector[BugFixDetector]
        FixDetector --> SZZ[SZZAnalyzer]
        SZZ --> Labeler[LabelManager]
    end

    subgraph Metrics[3. Roslyn Metrics]
        Labeler --> Roslyn[Microsoft.CodeAnalysis.CSharp CLI]
        Roslyn --> Builder[DatasetBuilder]
    end

    subgraph MLPipeline[4. Random Forest]
        Builder --> Split[GroupShuffleSplit by repo]
        Split --> Trainer[ModelTrainer: RF + GroupKFold]
        Trainer --> Evaluator[ModelEvaluator: Test Metrics & AUC]
    end

    subgraph GUI[5. Local Prediction]
        Trainer --> Predictor[BugPredictor]
        InputCode[Raw C# / .cs File] --> Predictor
        Predictor --> Streamlit[Streamlit Multi-Page UI]
    end
```

---

## 📋 Prerequisites

1. **Python**: Version 3.11 or higher (Python 3.11, 3.12, 3.13 supported).
2. **.NET SDK**: .NET 9.0 SDK or higher installed (`dotnet --version`).
3. **Git**: Git CLI installed and available in `PATH`.
4. **GitHub Token (Optional)**: Personal Access Token (PAT) for querying GitHub REST API above anonymous rate limits.

---

## 💻 Installation & Setup

### Windows (PowerShell)

```powershell
# 1. Clone or navigate to the repository
cd CISE_PROJECT_2

# 2. Create and activate a Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install project dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Verify .NET SDK installation and build Roslyn Analyzer
dotnet --version
dotnet build roslyn_analyzer\RoslynAnalyzer.csproj -c Release

# 5. Run the Streamlit Application
streamlit run app.py
```

### macOS / Linux (Bash / Zsh)

```bash
# 1. Clone or navigate to the repository
cd CISE_PROJECT_2

# 2. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Verify .NET SDK installation and build Roslyn Analyzer
dotnet --version
dotnet build roslyn_analyzer/RoslynAnalyzer.csproj -c Release

# 5. Run the Streamlit Application
streamlit run app.py
```

The application will launch in your browser at `http://localhost:8501`.

---

## 🧪 Running the Test Suite

Run all unit and integration tests across all pipeline phases:

```bash
# On Windows
.\.venv\Scripts\pytest.exe -v

# On macOS/Linux
pytest -v
```

All tests execute deterministically offline without network dependencies.

---

## 🖥️ Streamlit Multi-Page Interface Guide

| Page | Description |
| :--- | :--- |
| **📊 Dashboard** | High-level repository, commit, observation, model, and health statistics. |
| **📥 Repository Collection** | Search GitHub public repositories, clone full histories, and track commit diffs. |
| **🔍 Bug Analysis & SZZ** | Detect bug-fixing commits, trace bug-inducing commits (SZZ), and label methods. |
| **📁 Dataset Management** | Extract 26 Roslyn static code metrics, inspect distributions, and export versioned CSV snapshots. |
| **🧠 Model Training** | Train models across 4 algorithm families with repository-aware `GroupKFold` CV and compare with dummy baselines. |
| **📈 Model Evaluation** | Inspect holdout test metrics, confusion matrices, ROC/PR curves, and MDI vs Permutation feature importances. |
| **🎯 Real-World Bug Prediction** | Paste C# snippets or upload `.cs` files for real-time defect risk scoring, influential metric attribution, and validation benchmarks. |
| **⚙️ Settings** | Configure GitHub PAT, local storage paths, Roslyn project path, prediction thresholds, and privacy options. |

---

## 📊 Defect Risk Score Interpretation

- **0.00 – 0.30 (🟢 Low risk)**: Metrics are within standard clean method baselines.
- **0.31 – 0.60 (🟡 Medium risk)**: Moderate structural complexity or branching; review logic flow.
- **0.61 – 1.00 (🔴 High risk)**: Structural complexity, nesting, or branching strongly match historical defect patterns. Prioritize for focused code review and testing.

> [!IMPORTANT]
> **Defect Risk Caveat**: The risk score is an estimated metric propensity indicating structural complexity. It is **not** a formal proof that a method contains a bug, nor does a low-risk score guarantee code correctness.

---

## 🔒 Privacy & Local Processing

- **No Remote Telemetry**: All code analysis, parsing, training, and predictions occur 100% locally on your machine.
- **Source Code Privacy**: Raw source code is not persisted in prediction logs by default. Users may toggle history logging or clear stored predictions at any time in **Settings**.
- **No Paid External Dependencies**: Operates independently of commercial LLM APIs.

---

## 📑 Empirical Assessment & Academic Report

An empirical study across 3 real-world open-source repositories (`commandlineparser/commandline`, `LuckyPennySoftware/MediatR`, `Humanizr/Humanizer`) with 483 method observations and zero cross-repository data leakage is documented in:

👉 **[docs/FINAL_REPORT.md](docs/FINAL_REPORT.md)**

Key experimental findings (Authoritative multi-model experiment `exp_20261113_170914`):
- **Training Partition**: 382 methods across `Humanizer` (291) and `MediatR` (91) evaluated with 2-fold `GroupKFold` cross-validation.
- **Holdout Evaluation**: Evaluated on independent repository `commandlineparser/commandline` (101 methods: 44 buggy, 57 clean).
- **Best Model Configuration**: `rf_feature_constrained_log2` (CV Mean F1: **0.6801** vs Dummy baseline 0.0000).
- **Holdout Results at Nominal Threshold ($\tau = 0.50$)**:
  - Defect Recall: **77.27%** (34/44 buggy methods identified)
  - Precision: **46.58%** | F1-Score: **0.5812** | Accuracy: **51.49%** | Brier Score: **0.2627**
- **Holdout Results at CV-Optimized Threshold ($\tau = 0.30$)**:
  - Defect Recall: **95.45%** (42/44 buggy methods identified)
  - Precision: **47.19%** | F1-Score: **0.6316** | Accuracy: **51.49%**
- **Top MDI Predictive Features**: `method_length` (0.1354), `loc` (0.0964), `parameter_count` (0.0775), `method_call_count` (0.0550), and `statement_count` (0.0443).
- **Reproducible Multi-Model Pipeline**: `python scripts/run_experiments.py`.
- **Pilot Expansion Status**: Controlled pilot collection v2 on `FluentValidation/FluentValidation` completed (28 production observations: 14 buggy, 14 clean, 0% test leakage); verified in SQLite and ready for expansion once authorized.


