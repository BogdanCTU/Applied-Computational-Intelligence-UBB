# 03 — System Architecture & Workflow

---

## 1. End-to-End Pipeline Architecture

The system comprises four stages: Git/SZZ mining, Roslyn AST metric extraction, repository-grouped machine learning validation, and the Streamlit application interface.

```mermaid
flowchart TD
    subgraph Stage1["Stage 1: Git & SZZ Mining"]
        A["GitHub C# Repositories"] --> B["Git Commit Mining"]
        B --> C["Bug-Fix Commit Classification"]
        C --> D["SZZ Line Blame<br/>(git blame -w -M -C)"]
        D --> E["Pre-Fix Defect-Prone Methods (y=1)"]
        B --> F["Stable HEAD Candidate-Clean Methods (y=0)"]
    end

    subgraph Stage2["Stage 2: Roslyn AST Engine"]
        E --> G["Production C# Path Filter"]
        F --> G
        G --> H[".NET 9.0 Roslyn Analyzer"]
        H --> I["26 Static Code Metrics"]
    end

    subgraph Stage3["Stage 3: Persistence & Nested Validation"]
        I --> J[("SQLite Database &<br/>Versioned CSV Datasets")]
        J --> K["5x4 Nested GroupKFold<br/>(Grouped by Repository)"]
        K --> L["Versioned Model Bundles (.joblib)<br/>(Extra Trees & Random Forest)"]
    end

    subgraph Stage4["Stage 4: Streamlit Application"]
        L --> M["8-Page Engineering Interface<br/>(Evaluation & Live Prediction)"]
    end
```

---

## 2. Technology Stack

- **Python Backend & ML:** Python 3.13, `scikit-learn`, `pandas`, `numpy`, `scipy`, `joblib`, `pydantic`
- **Static Analysis Engine:** C# 13, .NET 9.0 SDK, `Microsoft.CodeAnalysis.CSharp` (Roslyn syntax tree API)
- **Persistence Layer:** SQLite 3 (WAL mode, foreign keys) and SHA-256 checksummed CSV/JSON artifacts
- **Version Control Mining:** Git CLI (`git log`, `git show`, `git blame -w -M -C`) and `GitPython`
- **Web Interface & Verification:** Streamlit 8-page UI and `pytest` automated test suite (123 tests)

---

## 3. Python-to-Roslyn Bridge

```mermaid
sequenceDiagram
    participant UI as Streamlit UI
    participant Py as RoslynAnalyzerClient (Python)
    participant CLI as RoslynAnalyzer (.NET 9 CLI)
    participant ML as BugPredictor (Model Bundle)

    UI->>Py: Pass C# source code string
    Py->>CLI: Stream source via stdin (--stdin)
    CLI->>CLI: Parse CSharpSyntaxTree & compute 26 metrics
    CLI-->>Py: Return JSON metric array via stdout
    Py->>ML: Apply bundle imputer, scaler & selector
    ML-->>UI: Return defect probability, label & risk tier
```

- **Subprocess Communication:** C# source code is passed to the compiled `.NET 9.0` analyzer via `stdin` and returned as structured JSON over `stdout`.
- **Bundle Encapsulation:** Each `.joblib` model bundle stores the fitted `SimpleImputer(strategy="median")`, optional `StandardScaler` / feature selector, fitted classifier, feature names, and cross-validation metadata.
