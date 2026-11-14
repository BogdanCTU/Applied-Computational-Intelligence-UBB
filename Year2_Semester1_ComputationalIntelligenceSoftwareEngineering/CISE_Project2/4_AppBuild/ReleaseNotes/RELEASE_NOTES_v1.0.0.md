# Release Notes — Version 1.0.0

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Release Date:** 2026-11-14  
**Author:** CISE Project 2 Research Team  
**Institution:** Babeș-Bolyai University, Faculty of Mathematics and Computer Science  

---

## 1. Overview

Version 1.0.0 marks the completed, validated, and structured release of the C# Software Defect Prediction research platform. The system delivers an empirical machine-learning solution for identifying bug-prone C# source code methods using syntactic and structural features extracted from Roslyn Abstract Syntax Trees.

---

## 2. Key Capabilities & Deliverables

### A. Core Machine Learning & Methodology
- **Mined Repositories:** Mined 7 major open-source C# projects (`Polly`, `FluentValidation`, `Newtonsoft.Json`, `CommandLine`, `Humanizr`, `Serilog`, `21Questions`).
- **Ground-Truth Labeling:** SZZ algorithm with line-blame tracking (`git blame -w -M -C`) for Label 1 (defect-inducing) and stable HEAD sampling under the Open-World Assumption for Label 0 (candidate-clean).
- **Static Metrics:** 26 Roslyn-extracted AST metrics covering code size, control flow complexity (McCabe), lexical nesting, OOP flags, and exception handling.
- **Group-Aware Validation:** 5-fold `GroupKFold` cross-validation partitioned strictly by repository, preventing data leakage.
- **Benchmark Suite:** Comprehensive evaluation across 11 machine-learning classifiers.
- **Champion Model:** Tuned `RandomForestClassifier` achieving:
  - 5-Fold CV Unweighted Mean Accuracy: **$67.34\% \pm 4.91\%$**
  - Pooled Out-of-Fold Nominal Accuracy ($\tau = 0.50$): **$67.13\%$** ($388/578$)
  - Pooled Out-of-Fold Tuned Accuracy ($\tau^* = 0.40$): **$70.42\%$** ($407/578$, Recall $87.46\%$, F1 $0.7405$)
  - Independent Holdout Evaluation (`Newtonsoft.Json`, 159 observations): Recall **$89.87\%$** ($71/79$), Specificity **$61.25\%$** ($49/80$), F1 **$0.7676$**, ROC-AUC **$0.7958$**.

### B. Interactive Web Workbench
- Streamlit web interface with 8 functional tabs for repository mining, SZZ analysis, dataset export, model training, evaluation metrics, and real-time C# method defect prediction.
- Real-time risk bands (Low $<0.30$, Medium $0.30-0.60$, High $>0.60$) with influential feature explanations.

### C. Repository Structure
- Sequential 6-domain architecture:
  1. `1_Database`: SQLite database, original & processed datasets, schema definitions.
  2. `2_SourceCode`: Python application modules, Roslyn analyzer, tests, operational scripts.
  3. `3_TestResults`: Automated test logs, 5-fold CV outputs, holdout evaluations, model evaluation summaries.
  4. `4_AppBuild`: Windows launch batch script, frozen model assets, release notes.
  5. `5_Documentation`: Architectural specs, database design, source code guides, ML methodology, validation, user guide, authoritative academic report (`FINAL_REPORT.md`), and historical archives.
  6. `6_Presentation`: 7 presentation-oriented markdown slides for university defense.

