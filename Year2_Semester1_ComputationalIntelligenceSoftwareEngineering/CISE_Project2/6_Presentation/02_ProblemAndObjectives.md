# 02 — Problem Definition & Research Objectives

---

## 1. Problem Formulation

### Method-Level Granularity
File-level defect prediction flags entire source files (often hundreds or thousands of lines), requiring manual inspection to locate the defect-prone routine. This project formulates defect prediction at the **method level**, mapping each C# method declaration to a 26-element static metric vector $\mathbf{x} \in \mathbb{R}^{26}$ and a binary defect label $y \in \{0, 1\}$.

### Methodological Controls Against Data Leakage
Empirical defect prediction faces two primary validity threats:
1. **Test-Code Contamination:** Unit test methods and auto-generated files have different structural distributions than production methods. The pipeline enforces path-level exclusion via `is_production_csharp_file()`.
2. **Repository-Level Data Leakage:** Standard random $K$-fold cross-validation places methods from the same project in both training and test partitions. All model evaluations enforce repository-grouped partitioning (`GroupKFold`).

---

## 2. Research Questions

| Research Question | Objective |
| :--- | :--- |
| **RQ1: Feasibility** | Can 26 static Roslyn AST metrics predict method-level defect-proneness across unseen C# repositories? |
| **RQ2: Model Optimization** | Do shallow-regularized Extra Trees and Random Forest ensembles improve cross-repository generalization under nested `GroupKFold` validation? |
| **RQ3: Feature Collinearity & Importance** | Which static metrics carry independent predictive signal under out-of-fold permutation importance when accounting for collinearity? |
| **RQ4: External Holdout Transfer** | How does the baseline model perform on an unseen external repository (`JamesNK/Newtonsoft.Json`), and what constraints govern holdout reuse? |

---

## 3. Project Objectives

- **Repository & SZZ Mining:** Mine Git commit histories, classify bug-fixing commits, and trace deleted lines to pre-fix method snapshots via `git blame -w -M -C`.
- **Production Code Filtering:** Exclude test projects, test fixtures, build directories (`obj/`, `bin/`), and generated C# files (`*.g.cs`, `*.Designer.cs`).
- **Static Metric Extraction:** Compute 26 method-level metrics using a .NET 9.0 Roslyn syntax analyzer.
- **Leakage-Free Model Optimization:** Evaluate 9 baseline configurations (5-fold `GroupKFold`) and 20 optimization configurations ($5 \times 4$ nested `GroupKFold`) on Dataset #2 ($N = 578$) with all imputation, scaling, feature selection, and threshold tuning confined inside training folds.
- **Interactive Engineering Interface:** Provide an 8-page Streamlit application for executing and inspecting each pipeline stage.
