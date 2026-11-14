# 03 — System Architecture & Workflow

---

## 1. End-to-End Pipeline Architecture

The system coordinates four distinct processing stages: Git mining, C# Roslyn analysis, machine learning validation, and live user serving.

```mermaid
flowchart TD
    subgraph Stage1["Stage 1: Git & SZZ Mining"]
        A["GitHub Repositories"] --> B["Git Commit Mining"]
        B --> C["Bug-Fix Classification<br/>(Regex Confidence)"]
        C --> D["SZZ Algorithm<br/>(git blame -w -M -C)"]
        D --> E["Pre-Fix Defect-Prone Methods"]
        B --> F["Stable HEAD Candidate-Clean Methods"]
    end

    subgraph Stage2["Stage 2: Roslyn AST Engine"]
        E --> G["Production C# Filter<br/>(Excludes test/generated code)"]
        F --> G
        G --> H[".NET 9 Roslyn Analyzer<br/>(AST Visitor)"]
        H --> I["26 Static Code Metrics"]
    end

    subgraph Stage3["Stage 3: Persistence & ML"]
        I --> J[("SQLite Database &<br/>Versioned CSVs")]
        J --> K["GroupKFold 5-Fold Partitioning"]
        K --> L["Model Benchmark & Tuning<br/>(Random Forest Champion)"]
    end

    subgraph Stage4["Stage 4: Streamlit UI"]
        L --> M["Live Predictor Workbench<br/>(Risk Score + Top Features)"]
    end
```

---

## 2. Technology Stack

- **Application Backend & UI:** Python 3.13, Streamlit, Pydantic, Pandas, NumPy, Scikit-Learn
- **Static Code Analysis:** C# 13, .NET 9.0 SDK, `Microsoft.CodeAnalysis.CSharp` (Roslyn AST compiler API)
- **Data Persistence:** SQLite 3 with Write-Ahead Logging (WAL) and foreign keys
- **Version Control Engine:** Git CLI via GitPython and subprocess line blame
- **Testing & Quality Assurance:** pytest (123 automated tests), GitHub Actions compatible

---

## 3. High-Performance Bridge Architecture

```mermaid
sequenceDiagram
    participant User as Developer / UI
    participant Py as Python Bridge (roslyn_client.py)
    participant DotNet as Roslyn Analyzer (.NET 9)
    participant Model as BugPredictor (Random Forest)

    User->>Py: Submit C# Method Snippet
    Py->>DotNet: Invoke CLI via standard input (stdin)
    DotNet->>DotNet: Parse SyntaxTree & Compute 26 Metrics
    DotNet-->>Py: Return Structured JSON Metrics via stdout
    Py->>Model: Vectorize Metrics & Impute Missing
    Model-->>User: Output Defect Probability & Risk Category
```

- **Zero-Disk Subprocess Communication:** C# source code is streamed into the Roslyn CLI via standard input (`stdin`), preventing temporary disk clutter.
- **Robust Error Handling:** Subprocess timeout bounds (30 seconds) and automatic binary rebuilding ensure high reliability.

