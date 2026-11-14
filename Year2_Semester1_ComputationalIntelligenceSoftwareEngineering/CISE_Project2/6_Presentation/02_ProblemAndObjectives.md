# 02 — Problem Definition & Research Objectives

---

## 1. The Challenge of Defect Prediction

### Limitations of Coarse Granularity
Most traditional software engineering research operates at file or module granularity:
- High-level prediction flags entire 2,000-line files as defect-prone.
- Developers are overwhelmed and cannot pinpoint where the defect actually resides.
- **Our Focus:** Fine-grained **method-level prediction** that pinpoints the specific function containing the defect.

### Threats to Data Integrity
Defect prediction models frequently suffer from two critical pitfalls:
1. **Test-Code Pollution:** Test helper methods and unit test fixtures exhibit very different syntactic structures from production code. Mixing them into training sets introduces severe bias.
2. **Cross-Project Data Leakage:** Standard random $K$-fold cross-validation puts methods from the same repository in both train and test splits, causing over-optimistic evaluation results.

---

## 2. Research Questions (RQs)

| Research Question | Objective |
| :--- | :--- |
| **RQ1: Feasibility** | Can static AST metrics extracted at method granularity reliably predict defect-proneness in C# source code? |
| **RQ2: Classifier Performance** | Which machine learning algorithm delivers the highest defect prediction capability under cross-project evaluation? |
| **RQ3: Feature Importance** | Which syntactic and complexity metrics provide the strongest signal for software defect induction in C#? |
| **RQ4: Generalization** | Does a model trained across diverse repositories generalize effectively to an unseen external codebase (Holdout)? |

---

## 3. Measurable Project Objectives

- [x] **Repository Mining:** Automatically mine Git histories and commit messages from active C# repositories.
- [x] **SZZ Implementation:** Identify Bug-Inducing Commits (BICs) and map them to pre-fix method bodies.
- [x] **Production Filtering:** Eliminate test code, build artifacts, and auto-generated files from all datasets.
- [x] **Static Feature Extraction:** Implement a high-performance .NET 9 Roslyn analyzer calculating 26 static metrics per method.
- [x] **Rigorous Evaluation:** Benchmark 11 machine-learning models using 5-fold GroupKFold cross-validation and an independent holdout set.
- [x] **Tooling & UI:** Deliver an intuitive web dashboard for real-time developer code assessment.

