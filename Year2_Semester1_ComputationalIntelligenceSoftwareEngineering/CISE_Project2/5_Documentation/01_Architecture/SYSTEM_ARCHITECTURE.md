# System Architecture — CISE Bug Detector v5.0.0

## 1. Architectural Reset

Version `5.0.0` replaces the obsolete `v1`–`v4` class-level risk-scoring / SZZ defect-proneness system (archived in `0_LegacyArchive_v1_v4/`) with a modular, method-level **Machine Learning C# Source-Code Bug Detection System** powered by Microsoft Roslyn (`.NET 9.0`) and `scikit-learn` `RandomForestClassifier`.

## 2. End-to-End Component Architecture

```mermaid
flowchart LR
    subgraph Sources["1. Verified Data Sources"]
        IB["Microsoft InferredBugs<br/>(C# / InferSharp)"]
        GH["GitHub Bug-Fix Pairs<br/>(API + Local Mirrors)"]
        HN["Verified Hard Negatives<br/>(Test-Backed Complex Code)"]
    end

    subgraph Preproc["2. Roslyn Preprocessor (.NET 9.0)"]
        ME["MethodExtractor<br/>(Class/Struct/Record/Nested/Async)"]
        NT["Normalizer & Tokenizer"]
        FE["AST / CFG / DFG / Structural"]
    end

    subgraph DataLayer["3. Validation & Persistence"]
        VAL["Deduplicator & Cross-Label Guard"]
        DB[("SQLite v5<br/>16 Normalized Tables")]
        DS["Parquet / CSV / Audit JSON"]
    end

    subgraph ML["4. ML Pipeline (Python)"]
        SP["Repository-Grouped Split<br/>(Zero Leakage)"]
        FP["FeaturePipeline<br/>(Lexical TF-IDF + AST + CFG + DFG + Struct)"]
        RF["RandomForestClassifier +<br/>3-Way Calibration"]
        EXP["Explainability<br/>(Permutation + TreeInterpreter)"]
    end

    subgraph Apps["5. Delivery"]
        CLI["CLI (`python -m bug_detector`)"]
        GUI["Minimal 6-Page Streamlit GUI"]
    end

    IB --> ME
    GH --> ME
    HN --> ME
    ME --> NT --> FE --> VAL --> DB --> DS
    DB --> SP --> FP --> RF --> EXP
    RF --> CLI
    RF --> GUI
    EXP --> GUI
```

## 3. Module Layout (`2_SourceCode/`)

| Component | Path | Responsibility |
| --- | --- | --- |
| Roslyn Preprocessor | `2_SourceCode/RoslynPreprocessor/` | C# parsing, method extraction, normalization, tokenization, AST/CFG/DFG/structural extraction |
| Config & Logging | `2_SourceCode/bug_detector/config/`, `logging_utils.py` | Pydantic v2 validation, JSON persistence (`4_AppBuild/Config/active_config.json`), structured logging |
| Database Layer | `2_SourceCode/bug_detector/db/` | SQLite WAL manager, SQL migrations (`001_initial_v5.sql`), content-addressed blob & experiment CRUD |
| Data Collection | `2_SourceCode/bug_detector/collection/` | InferredBugs ingestor, GitHub API & mirror bug-fix collector, hard-negative collector, deduplicator |
| Preprocessing Bridge | `2_SourceCode/bug_detector/preprocessing/` | Persistent JSONL subprocess bridge to `RoslynPreprocessor.dll` |
| Feature Extractors | `2_SourceCode/bug_detector/features/` | 5 independent, testable extractors + sparse/dense `FeaturePipeline` |
| ML & Evaluation | `2_SourceCode/bug_detector/ml/` | Repository-grouped splitting, Random Forest CV/HPO, Experiments A–I, calibration, predictor |
| Explainability | `2_SourceCode/bug_detector/explainability/` | Held-out permutation importance & exact Saabas tree-path decomposition |
| CLI & Streamlit GUI | `2_SourceCode/bug_detector/cli.py`, `2_SourceCode/gui/` | Headless CLI workflows + 6-page Streamlit interface |
