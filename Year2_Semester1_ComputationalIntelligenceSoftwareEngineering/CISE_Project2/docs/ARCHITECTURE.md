# Architecture Design Document: C# Software Bug Detection System

## 1. System Overview

The **C# Defect Predictor** is an academic-grade machine learning system designed to predict defect proneness in C# source code methods using supervised Random Forest classification. The system operates strictly locally, requiring external internet access solely for cloning public GitHub repositories or querying GitHub's public REST API.

```mermaid
flowchart TD
    subgraph DataCollection[A. Data Collection Engine (Phase 2 Implemented)]
        GH[GitHub REST API] --> Discovery[GitHubClient: Discovery & Rate Limits]
        Discovery --> Clone[RepositoryManager: Full History Git Cloner]
        Manual[Manual URL Entry] --> Clone
        Clone --> ReposDir[(data/repositories/owner/name)]
        ReposDir --> CommitsExtract[CommitCollector: Commit & File Diff Extractor]
    end

    subgraph MiningSZZ[B. Bug Identification & SZZ (Phase 3 Implemented)]
        CommitsExtract --> BugFix[BugFixDetector: Heuristics & Issue Linkages]
        BugFix --> SZZ[SZZAnalyzer: git blame -w -M -C]
        SZZ --> RoslynMethodLocator[Roslyn Method Boundary Locator]
        RoslynMethodLocator --> Labels[LabelManager: Method Observations 1 / 0 / -1]
    end

    subgraph FeatureExtraction[C. Feature Extraction & Dataset Generation (Phase 4 Implemented)]
        Labels --> FeatExtract[FeatureExtractor: Batch & Incremental Pipeline]
        FeatExtract --> RoslynCLI[.NET Console App - 24 Code Metrics]
        RoslynCLI --> FeaturesTable[(SQLite: features table)]
        FeaturesTable --> DatasetBuilder[DatasetBuilder: Leakage Filter & Snapshot Builder]
        DatasetBuilder --> Exporter[DatasetExporter: CSV & Metadata JSON]
        Exporter --> ExportsDir[(exports/*.csv)]
    end

    subgraph MachineLearning[D. Machine Learning Pipeline (Phase 5 Implemented)]
        ExportsDir --> Preprocess[DataPreprocessor: Imputation & VarianceThreshold]
        Preprocess --> GroupSplit[split_by_repository: GroupShuffleSplit on repository_id]
        GroupSplit --> Trainer[ModelTrainer: RandomForestClassifier + GroupKFold CV]
        Trainer --> Baseline[DummyClassifier: Baseline Comparison]
        Trainer --> JoblibModel[(models/*.joblib Bundle)]
        JoblibModel --> Evaluator[ModelEvaluator: Test Set Metrics, ROC/PR Curves, MDI & Permutation]
    end

    subgraph RealTimeInference[E. Real-Time Bug Prediction & UI (Phase 6 Implemented)]
        JoblibModel --> BugPredictor[BugPredictor: Real-Time Inference Engine]
        CodeInput[Raw C# Code / .cs File Upload] --> BugPredictor
        BugPredictor --> RoslynInference[Roslyn AST Metrics Extractor]
        RoslynInference --> BundledPreproc[Fitted DataPreprocessor Transformation]
        BundledPreproc --> RFInference[Random Forest Inference & Risk Scoring]
        RFInference --> StreamlitUI[Streamlit Multi-Page UI]
        RFInference --> SQLiteHistory[(SQLite: predictions table)]
    end
```

## 2. Component Specifications

### 2.1 Data Collection Engine (`src/collection/`)
- **`github_client.py`**: Interacts with the GitHub Search & Repositories REST API with support for authenticated (PAT) and anonymous requests, exponential backoff, rate limit handling, and pagination.
- **`repository_manager.py`**: Manages local disk storage under `data/repositories/{owner}/{name}`, clones repositories with complete Git history via `GitPython`, checks out branches, protects against dirty local states, and maintains metadata in SQLite.
- **`commit_collector.py`**: Reads commit histories and file diffs from local repositories incrementally, distinguishes C# modifications, records merge commit relationships, and stores file change lists.

### 2.2 Mining and SZZ Engine (`src/mining/` & `src/labeling/`)
- **`bug_fix_detector.py`**: Discovers bug-fixing commits using natural language keywords (e.g., `fix`, `bug`, `defect`, `resolve`, `crash`, `regression`), GitHub issue/PR linkages (`#123`, `GH-45`), and diff filters with confidence scoring and manual review support.
- **`szz_analyzer.py`**: Enhanced SZZ implementation. For each confirmed bug fix, extracts deleted non-comment non-whitespace statements from the mainline parent diff, runs `git blame -w -M -C --porcelain` to identify candidate Bug-Inducing Commits (BICs), and records line-level traces into `szz_results`.
- **`label_manager.py`**: Resolves enclosing C# method boundaries using Roslyn AST. Extracts pre-fix buggy method source code (**Label 1**), samples stable methods (**Label 0**), and flags ambiguous commits as uncertain (**Label -1**).

### 2.3 Feature Extraction & Dataset Generation (`src/dataset/` & `roslyn_analyzer/`)
- **`roslyn_analyzer/Program.cs`**: Cross-platform .NET 9.0 console application calculating 24 structural, complexity, and OOP metrics using `Microsoft.CodeAnalysis.CSharp`. Isolates enclosing methods from nested local functions/lambdas, normalizes newlines across OSes, and supports bare snippet parsing via container wrapping.
- **`feature_extractor.py`**: Orchestrates batch and incremental metric calculation, handles syntax failures gracefully, and populates the `features` table.
- **`dataset_builder.py`**: Joins observations and features, removes data-leakage identifiers from feature matrix $X$, excludes uncertain observations (`-1`), verifies duplicates, and generates versioned snapshot records.
- **`exporter.py`**: Exports dataset snapshots to CSV format alongside companion provenance metadata JSON.

### 2.4 Machine Learning Engine (`src/ml/`)
- **`preprocessing.py`**: Implements `DataPreprocessor` (median missing value imputation, variance thresholding) and `split_by_repository()` enforcing zero repository leakage between train and test partitions.
- **`trainer.py`**: Implements `ModelTrainer` with `RandomForestClassifier`, executes `GroupKFold` cross-validation on training repositories, and calculates baseline comparison against `DummyClassifier`.
- **`evaluator.py`**: Implements `ModelEvaluator` calculating Accuracy, Precision, Recall, F1, ROC-AUC, Average Precision (PR-AUC), Confusion Matrix heatmap, ROC/PR curves, and both MDI and Permutation feature importances.
- **`model_manager.py`**: Implements `ModelManager` serializing model bundles (model, preprocessor, features, parameters, metrics, split summary) into compressed `.joblib` files and SQLite metadata tracking.
- **`predictor.py`**: Implements `BugPredictor` for real-time inference on unseen C# method snippets or entire `.cs` files, applying bundled preprocessing transformations, estimating defect risk scores, attributing influential structural metrics, and maintaining privacy-safe SQLite history.

### 2.5 Presentation Layer (`ui/` and `app.py`)
- Multi-page Streamlit application coordinating all phases:
  - System Overview & Experiment Dashboard (`dashboard.py`)
  - Repository Collection & Discovery (`repository_collection.py`)
  - Commit Analysis & SZZ Mining (`bug_analysis.py`)
  - Dataset Management & Roslyn Metrics Extraction (`dataset_management.py`)
  - Model Training with GroupKFold (`model_training.py`)
  - Model Evaluation & Feature Importance (`model_evaluation.py`)
  - Real-Time Bug Prediction & Validation (`bug_prediction.py`)
  - Application Settings & Privacy Guardrails (`settings.py`)
