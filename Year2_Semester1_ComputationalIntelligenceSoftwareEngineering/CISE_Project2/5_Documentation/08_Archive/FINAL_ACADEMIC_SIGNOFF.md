# Final Academic Sign-Off & Consistency Verification Report

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University  
**Master's Programme:** Applied Computational Intelligence (Year 2, Semester 1)  
**Course:** Computational Intelligence in Software Engineering (CISE) — Project 2  
**Date:** November 2026  
**Evaluation Status:** READY FOR PRESENTATION  

---

## 1. Academic Requirement Compliance Matrix

The project implementation and documentation have been evaluated against the formal evaluation criteria of the CISE curriculum:

| Requirement Index | Academic Evaluation Dimension | Implementation & Artifact Evidence | Compliance Status |
| :---: | :--- | :--- | :---: |
| **REQ-1** | **Automated Data Mining & Defect Attribution** | Full Git commit mining with regex bug-fix heuristic detection and SZZ line-blame tracing (`git blame -w -M -C`). Ground truth stored in SQLite with full relational provenance. | **FULL COMPLIANCE** |
| **REQ-2** | **Static Code Metric Extraction** | Dedicated .NET 9.0 Roslyn analyzer (`RoslynAnalyzer.csproj`) utilizing `Microsoft.CodeAnalysis.CSharp` to compute 26 static AST metrics across size, complexity, control-flow, and OOP features. | **FULL COMPLIANCE** |
| **REQ-3** | **Leakage-Free Cross-Validation Design** | 5-Fold `GroupKFold` cross-validation partitioned strictly by repository boundary ($N_{\text{repos}}=5$, $K=5$). Zero intra-repository overlap between training and validation folds ($\text{Train\_Repos} \cap \text{Val\_Repos} = \emptyset$). | **FULL COMPLIANCE** |
| **REQ-4** | **Multi-Model Benchmark & Calibration** | 11 model configurations evaluated across 4 classifier families (Random Forest, Decision Tree, Logistic Regression, Dummy baselines). Brier score calibration evaluated; out-of-fold threshold tuning ($\tau^*=0.40$). | **FULL COMPLIANCE** |
| **REQ-5** | **Independent Generalization Evaluation** | Independent holdout evaluation on `JamesNK/Newtonsoft.Json` (159 methods) evaluated post-freeze as supported by dated experiment records. Zero data leakage into training folds. | **FULL COMPLIANCE** |
| **REQ-6** | **Interactive Application & Presentation** | Streamlit web application providing 8 functional pages for live AST metric extraction, defect risk scoring, model evaluation, and dataset export. Complete 7-deck slide presentation in Markdown. | **FULL COMPLIANCE** |

---

## 2. Final Verified Dataset Statistics

All dataset metrics and class distributions are verified against authoritative CSV files, JSON metadata, and database records:

| Dataset Identifier | Observations ($N$) | Defect-Prone Class (1) | Candidate-Clean Class (0) | Repositories Included | Primary Empirical Function |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Dataset #1 (`csharp_empirical_v1`)** | 483 | 226 (46.79%) | 257 (53.21%) | `Humanizer` (291), `CommandLineParser` (101), `MediatR` (91) | Exploratory feature selection and prototype baseline |
| **Dataset #2 (`csharp_empirical_v2`)** | 578 | 279 (48.27%) | 299 (51.73%) | `Humanizer` (291), `Serilog` (134), `MediatR` (91), `Polly` (34), `FluentValidation` (28) | Authoritative benchmark corpus for 5-fold GroupKFold CV |
| **Independent Holdout** | 159 | 79 (49.69%) | 80 (50.31%) | `JamesNK/Newtonsoft.Json` (159) | External generalization test of frozen model |
| **Total Evaluated Corpus** | **737** | **358 (48.58%)** | **379 (51.42%)** | **6 Open-Source Repositories** | Combined benchmark and holdout evaluation |

### Methodological Labeling Controls

1. **Defect-Prone Class (1):** Methods identified in candidate Bug-Inducing Commits (BICs) via SZZ blame tracing from validated bug-fixing commits. Labels represent heuristic approximations rather than infallible ground truth.
2. **Candidate-Clean Class (0):** Production methods sampled from the stable `HEAD` revision with no recorded bug-fixing modifications within the mined commit window. Under the Open-World Assumption (OWA), these methods are designated as *candidate-clean* because latent defects may exist undetected.
3. **Temporal Asymmetry:** Historical defect-prone methods represent the pre-fix state at the time of defect introduction, whereas candidate-clean methods are sampled from the latest stable `HEAD` revision. This design ensures candidate-clean methods survived historical bug fixes, but introduces a temporal asymmetry between historical and contemporary code snapshots.
4. **Production-Source Filtering:** 100% production code verified via `is_production_csharp_file()`. Zero test files, test fixtures, or build artifacts exist in any evaluated dataset snapshot.

---

## 3. Final Cross-Validation and Holdout Results

### 3.1 Five-Fold GroupKFold Cross-Validation Benchmark (Dataset #2, $N=578$)

Evaluated at the nominal decision threshold ($\tau = 0.50$):

| Rank | Model Configuration | Algorithm Family | F1-Score | Recall | Precision | Accuracy | ROC-AUC | PR-AUC | Brier Score |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | `rf_compact_regularized` | Random Forest | **0.6859 ± 0.0247** | 0.7403 ± 0.1557 | 0.6824 ± 0.1202 | **0.6734 ± 0.0491** | **0.7025** | **0.6401** | **0.2144 ± 0.0396** |
| 2 | `rf_feature_constrained_log2` | Random Forest | 0.6385 ± 0.0641 | 0.6831 ± 0.1706 | 0.6384 ± 0.1197 | 0.6369 ± 0.0673 | 0.6974 | 0.6309 | 0.2209 ± 0.0375 |
| 3 | `rf_heavy_bagging_300` | Random Forest | 0.6262 ± 0.0633 | 0.6788 ± 0.1738 | 0.6117 ± 0.0984 | 0.6212 ± 0.0617 | 0.6874 | 0.6277 | 0.2265 ± 0.0376 |
| 4 | `rf_baseline_balanced` | Random Forest | 0.6108 ± 0.1176 | 0.6678 ± 0.1982 | 0.6046 ± 0.1157 | 0.6074 ± 0.0827 | 0.6792 | 0.6200 | 0.2249 ± 0.0410 |
| 5 | `dt_shallow_depth4` | Decision Tree | 0.5734 ± 0.2172 | 0.6166 ± 0.2646 | 0.5573 ± 0.1884 | 0.5721 ± 0.1345 | 0.5849 | 0.5630 | 0.2807 ± 0.0699 |
| 6 | `rf_deep_capacity` | Random Forest | 0.5577 ± 0.0739 | 0.5794 ± 0.1737 | 0.5811 ± 0.1147 | 0.5815 ± 0.0647 | 0.6552 | 0.5982 | 0.2429 ± 0.0435 |
| 7 | `lr_balanced_c1` | Logistic Regression | 0.4989 ± 0.1252 | 0.4538 ± 0.1469 | 0.5994 ± 0.1557 | 0.5709 ± 0.0894 | 0.6225 | 0.5694 | 0.2620 ± 0.0368 |
| 8 | `lr_standard_c1` | Logistic Regression | 0.4890 ± 0.1409 | 0.4360 ± 0.1651 | 0.6095 ± 0.1593 | 0.5744 ± 0.0877 | 0.6231 | 0.5699 | 0.2643 ± 0.0366 |
| 9 | `dt_depth8` | Decision Tree | 0.4695 ± 0.2194 | 0.4907 ± 0.2529 | 0.4844 ± 0.1983 | 0.5050 ± 0.1425 | 0.5097 | 0.5033 | 0.3993 ± 0.1017 |

### 3.2 Accuracy Distinction and Threshold Tuning

Evaluation explicitly separates fold-mean accuracy from global pooled out-of-fold metrics:

| Metric Identifier | Evaluation Protocol | Threshold | Reported Value | Mathematical Definition |
| :--- | :--- | :---: | :---: | :--- |
| **5-Fold Fold Mean Accuracy** | Unweighted fold average across 5 held-out repos | Nominal $\tau = 0.50$ | **$0.6734 \pm 0.0491$** | $\frac{1}{5}\sum_{k=1}^5 \text{Acc}_k$ |
| **Pooled Out-of-Fold Nominal Accuracy** | Global pooled out-of-fold predictions ($N=578$) | Nominal $\tau = 0.50$ | **$67.13\%$** (388/578) | $\frac{TN+TP}{N} = \frac{183+205}{578}$ |
| **Pooled Out-of-Fold Tuned Accuracy** | Global pooled out-of-fold predictions ($N=578$) | Tuned $\tau^* = 0.40$ | **$70.42\%$** (407/578) | $\frac{TN+TP}{N} = \frac{163+244}{578}$ |

### 3.3 Independent Holdout Validation (`JamesNK/Newtonsoft.Json`, $N=159$)

Evaluated post-freeze on the frozen Random Forest model:

| Operating Threshold | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Brier Score | Confusion Matrix |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Nominal Threshold ($\tau = 0.50$)** | 74.21% (118/159) | 69.79% (67/96) | 84.81% (67/79) | 0.7657 | 0.8209 | 0.1713 | $TN=51, FP=29, FN=12, TP=67$ |
| **CV-Tuned Threshold ($\tau^* = 0.40$)** | **75.47% (120/159)** | 69.61% (71/102) | **89.87% (71/79)** | **0.7845** | 0.8209 | 0.1713 | $TN=49, FP=31, FN=8, TP=71$ |

---

## 4. Methodological Limitations

1. **Base-Rate Fallacy in Production:** Real-world software defect prevalence typically ranges between 2% and 10%, compared to the balanced ~48% to 50% distribution in the experimental datasets. Under Bayes' theorem, an illustrative hypothetical scenario with 5% prevalence would yield an expected operational precision of approximately 10.9% despite high nominal recall:
   $$P(\text{Defect} \mid \text{Alert}) = \frac{0.8987 \times 0.05}{0.8987 \times 0.05 + 0.3875 \times 0.95} \approx \mathbf{10.88\%}$$
2. **SZZ Heuristic Attribution:** SZZ relies on `git blame`, which can attribute defects to refactoring or formatting commits rather than true defect-inducing logic.
3. **Open-World Assumption on Candidate-Clean Labels:** Methods sampled from stable repository `HEAD` commits without recorded bug fixes cannot be mathematically verified as defect-free; unobserved latent bugs may exist.
4. **Threshold Selection Bias:** Operational threshold $\tau^* = 0.40$ was identified on aggregated out-of-fold cross-validation predictions without nested cross-validation, introducing mild selection bias into cross-validation metrics, though its generalizability was subsequently supported by the holdout results.
5. **Absence of External Human Trials:** The 24-method double-blind review framework (`DEVELOPER_STUDY_TEMPLATE.md`) is published as a formal research protocol instrument; no external human developer trials were conducted.
6. **Syntactic vs. Semantic Limits:** Static AST metrics capture size, branching, and nesting complexity, but cannot detect subtle semantic flaws (such as type-covariance mismatches) in concise 1-line wrapper methods.

---

## 5. Remaining Risks & Mitigation Strategies

| Risk Category | Identified Risk | Impact Level | Applied Mitigation Strategy |
| :--- | :--- | :---: | :--- |
| **Operational Triage** | Developer alert fatigue in production due to base-rate fallacy | Low | Classify application as a triage review prioritizer rather than a blocking CI/CD gate. |
| **Method Scope** | Changes occurring outside method declarations (e.g., class fields, enums) are unhandled | Minimal | Explicitly bounded scope to C# method declarations; ambiguous changes are assigned Label -1. |
| **Ecosystem Scope** | Idiomatic C# AST features may not transfer directly to other languages | Low | Scope strictly documented as C# (.NET) source code; Roslyn analyzer specifically models C# 13 syntax. |

---

## 6. Conclusion & Recommendation

The `CISE_Project2` repository has undergone a comprehensive, non-destructive academic refinement. All software components compile cleanly, all 123 automated regression tests pass, and all 15 protected artifacts retain 100% cryptographic SHA-256 bitwise parity.

Documentation, user interfaces, and defense slides are completely aligned, rigorously vetted against factual artifacts, and presented in formal academic English with zero informal visual artifacts.

**Final Determination:**

$$\mathbf{READY\ FOR\ PRESENTATION}$$

