# Academic Methodology & Methodological Integrity Review
## Machine Learning-Based Software Defect Prediction for C# Source Code

**Document Version:** 1.0.0  
**Date:** November 2026  
**Author / Specialist:** Senior ML4SE Research Engineer & Academic Reviewer  
**Context:** Babeș-Bolyai University, M.Sc. in Applied Computational Intelligence, CISE Project 2  
**Purpose:** Formal academic audit, terminology standardization, and methodological disclosure guide for defect prediction research.

---

## 1. Executive Summary & Purpose

This document provides a comprehensive academic methodology review and establishes rigorous standards for machine learning research applied to software engineering (ML4SE). 

In empirical defect prediction, imprecise terminology and unstated methodological assumptions often lead to overstated claims regarding model capability, ground truth validity, and generalization. This review systematically formalizes:
1. **Academic Terminology Standardization**: Replacing informal industry phrases with academically defensible constructs.
2. **Core Methodological Disclosures**: Documenting the theoretical and empirical limitations of SZZ labeling, the Open-World Assumption, temporal labeling asymmetry, and artificial class balancing.
3. **Cross-Validation & Partitioning Rigor**: Establishing mathematical requirements for repository-aware cross-validation and distinguishing `GroupKFold` from `StratifiedGroupKFold`.
4. **Threshold Selection & Optimism Bias**: Identifying and mitigating post-selection inference bias in decision threshold tuning.
5. **Probability Evaluation Separation**: Decoupling classification, discrimination, probability error, and true empirical calibration.
6. **Independent Holdout Protocol**: Formulating a strict, blinded protocol for the final uncompromised holdout evaluation on `JamesNK/Newtonsoft.Json`.
7. **Human Validation Framework**: Establishing ordinal inter-rater reliability protocols for developer perception studies.

---

## 2. Standardized Academic Terminology

To adhere to the rigorous standards of premier empirical software engineering venues (e.g., IEEE TSE, ACM TOSEM, MSR, ICSE), all documentation, reports, and code comments must strictly employ standardized academic terminology:

| Informal / Flawed Term | Standardized Academic Term | Methodological Justification |
| :--- | :--- | :--- |
| *"Ground-truth defect labels"* / *"Confirmed bugs"* | **SZZ-derived defect labels** | SZZ is a heuristic tracing algorithm subject to false positives (e.g., cosmetic edits blamed to refactorings). Labels represent high-confidence proxy approximations, not absolute ground truth. |
| *"Clean / Non-buggy methods"* | **Candidate-clean observations** | Under the Open-World Assumption, absence of recorded defect fixes does not certify code as defect-free. Latent defects may remain unreported. |
| *"Gold standard holdout"* | **Independent repository-level holdout** | "Gold standard" implies authoritative, flawless verification. An external repository evaluates out-of-domain transferability under domain-specific distribution shifts. |
| *"Standard cross-validation"* / *"KFold"* | **Repository-aware cross-validation** | Emphasizes that repository identity is the grouping variable, strictly preventing intra-repository code leakage across folds. |
| *"Production validation"* / *"Model proof"* | **Exploratory empirical evaluation** | Acknowledges that retrospective dataset evaluations on open-source repositories provide empirical evidence rather than formal mathematical proof. |

---

## 3. Mandatory Methodological Disclosures

### 3.1 SZZ Algorithm Limitations & False Positives
The Śliwerski–Zimmermann–Zeller (SZZ) algorithm operates by identifying bug-fixing commits via keyword/issue heuristics and tracing deleted or modified lines back to their introducing commits via `git blame`. While indispensable in mining software repositories, SZZ has known theoretical and practical limitations:
1. **Cosmetic & Formatting Blame**: If a developer reformatted code, adjusted indentation, or touched comments prior to a fix, `git blame` may identify the formatting commit as the bug-inducing commit (BIC).  
   *Mitigation in Pipeline:* `SZZAnalyzer` executes `git blame -w -M -C` to ignore whitespace and detect intra-file line movements, and explicitly strips comment-only and bracket-only deletions.
2. **Refactoring Noise**: Large-scale architectural refactorings (e.g., method extraction, class restructuring) that modify target lines can be mistakenly implicated as defect-introducing commits.
3. **Merge Commit Artifacts**: Non-linear branching can obscure true parentage.  
   *Mitigation in Pipeline:* SZZ restricts diff extraction to mainline parents (`parents[0]`) to isolate changes merged into primary integration branches.

### 3.2 Open-World Assumption (OWA) & Latent Defects
In software repository mining, datasets operate under the **Open-World Assumption**:
- An observed bug fix provides positive evidence of a historical defect ($y=1$).
- However, the absence of a recorded bug fix does **not** prove that a method is clean ($y=0$).
- Many software defects remain dormant, undetected, or unpatched for years. Consequently, negative observations sampled from stable HEAD revisions are **candidate clean**, not certified defect-free. Label noise in class 0 is an inherent constraint of retrospective mining.

### 3.3 Temporal Labeling Asymmetry
A subtle construct validity threat exists in the temporal sampling of observations:
- **Buggy Methods ($y=1$)**: Extracted from historical parent commits preceding a bug fix (often dating from 2018–2022).
- **Candidate-Clean Methods ($y=0$)**: Sampled from the latest repository HEAD revision (2024–2026).
- **Academic Consequence**: C# language standards and compiler idioms evolve (e.g., C# 8 nullability, C# 9 records, C# 10 file-scoped namespaces). While Roslyn extracts AST token metrics uniformly, structural style differences between historical and contemporary commits could introduce subtle temporal confounding.

### 3.4 Artificial Class Balancing vs. Industrial Prevalence
In typical enterprise software systems, method-level defect prevalence is estimated at **5% to 15%** (class imbalance). In our benchmark dataset:
- Candidate clean methods are deliberately sampled at a **~1:1 ratio** against SZZ-traced buggy methods to achieve an experimental balance (~47%–50% positive prevalence).
- **Impact on Evaluation**:
  - Balanced datasets stabilize decision tree split criteria and maximize training sample efficiency.
  - However, raw Precision values and predicted probability distributions cannot be directly extrapolated to industrial environments without adjusting for the true prior base rate via Bayes' theorem:
    $$P(\text{Buggy} \mid \text{Flag}) = \frac{P(\text{Flag} \mid \text{Buggy}) \cdot P(\text{Buggy})}{P(\text{Flag} \mid \text{Buggy}) \cdot P(\text{Buggy}) + P(\text{Flag} \mid \text{Clean}) \cdot P(\text{Clean})}$$
  - A precision of 0.47 on a 50/50 balanced dataset corresponds to an operational precision of ~10%–15% in a repository with 10% base defect density.

### 3.5 Cross-Repository Generalization Limitations
Static code metrics (LOC, McCabe Cyclomatic Complexity, statement counts, parameter counts) quantify **procedural risk envelopes** rather than localized semantic bugs:
- Different open-source projects adopt radically distinct architectural patterns:
  - `CommandLineParser`: Dense switch tables, reflection-heavy binding, deep AST nesting.
  - `MediatR`: Extremely compact, delegate-driven CQRS pipeline handlers.
  - `Humanizer`: High volume of localized string manipulation extensions.
- When an ensemble trained on one domain is evaluated on another, structural metrics often flag necessary complexity as defects, driving False Positives. Conversely, subtle semantic faults in compact utility methods remain undetectable via syntactic metrics alone (False Negatives).

### 3.6 Multicollinearity in Code Metrics
Structural metrics derived from syntax trees naturally exhibit strong collinearity:
- `method_length`, `loc`, `logical_loc`, and `statement_count` correlate heavily ($r > 0.85$).
- While Random Forest is generally robust to collinearity due to random feature subsampling ($\sqrt{p}$ or $\log_2(p)$), in-sample feature importance (MDI) spreads weight across redundant dimensions. When evaluated out-of-sample on an unseen repository, permuting redundant features independently can yield slight negative permutation importance due to tree re-weighting.

### 3.7 Post-Selection Optimism in Decision Threshold Tuning
In standard machine learning workflows, evaluating multiple decision thresholds ($\tau \in [0.20, 0.80]$) across pooled cross-validation predictions identifies the empirical optimum (e.g., $\tau = 0.30$).
- **Optimism Bias**: When the same validation predictions are used to rank hyperparameter configurations AND select the optimal operating threshold, the reported CV F1 score (0.7533) exhibits post-selection optimism.
- **Academic Standard**: To prevent leakage, the final holdout repository was strictly isolated from threshold selection. However, for internal cross-validation reporting, nested cross-validation is recommended to fully isolate threshold tuning from performance estimation.

### 3.8 Researcher Confirmation Bias on Historical Holdout
During early prototype iterations, `commandlineparser/commandline` was evaluated post-hoc to diagnose classification errors. Although no model parameters were trained on this data:
- Inspecting specific false positives and false negatives introduces **researcher confirmation bias**, as subsequent architectural adjustments (e.g., regularizing tree depth, tuning leaf samples) could be subconsciously influenced by knowledge of holdout failure modes.
- **Remediation**: `commandlineparser/commandline` is formally reclassified as an **archival diagnostic benchmark**, while `JamesNK/Newtonsoft.Json` is introduced as the uncompromised, blinded final holdout repository.

### 3.9 Production-Only Filtering & Test Code Elimination
A critical validity threat in software defect prediction is the unintentional inclusion of test fixtures, unit tests, and test-assertion helpers in the training dataset:
- **Construct Contamination**: Test classes exhibit fundamentally distinct syntactic and structural characteristics (e.g., assertion chains, fixture setup methods, mock interactions) compared to production business logic. Training or validating a defect predictor on test methods causes construct contamination and distorts feature importance.
- **Symmetric Inclusion Mandate**: Filtering must apply symmetrically across both classes. In early iterations, candidate-clean sampling used a naive exclusion regex while SZZ traces were less strictly bounded, allowing test methods to enter the buggy class while forbidding them from the clean class.
- **High-Precision Classification**: The pipeline utilizes a centralized classifier (`src/utils/source_classifier.py`) that filters test directories, test project conventions (`*.Tests/`), and test fixture filenames (`*Tests.cs`, `*Tester.cs`), while carefully preserving legitimate production files (such as `ContestManager.cs`, `ProductionTestConfiguration.cs`, and standalone utilities like `Tester.cs`).

### 3.10 Disambiguation of Empirical Yield Metrics
Mining yields must be formally disambiguated to avoid misleading claims regarding dataset efficiency:
1. **Bug-Fix Detection Rate** ($\text{classified fixes} / \text{sampled commits}$): Measures commit-level issue heuristic efficiency (typically 3%–5% in mature C# repos).
2. **SZZ Trace Success Rate** ($\text{traced fixes} / \text{classified fixes}$): Measures SZZ line blame resolution efficiency (typically 85%–95%).
3. **Positive-Method Yield** ($\text{production buggy methods} / \text{sampled commits}$): Measures the true density of defect-inducing methods extracted per commit mined (typically 3%–5%).
4. **Total Usable Observations**: The combined balanced dataset ($\text{production buggy} + \text{production clean}$), which doubles the positive method count under a 1:1 sampling policy.

---

## 4. Repository-Aware Cross-Validation Architecture

### 4.1 Strict Group Separation Requirements
To guarantee zero intra-repository data leakage, the validation harness enforces:
1. **Repository Identity as Group Variable**: The grouping key is strictly `repository_id`.
2. **Indivisible Partitioning**: All observations belonging to a repository must reside exclusively within the training partition or exclusively within the validation partition of any given fold.
3. **In-Fold Preprocessing Pipeline**:
   - Median imputation for missing metrics.
   - `VarianceThreshold` pruning for zero-variance features.
   - `StandardScaler` normalization (for linear models).
   - Preprocessing transformers are fitted strictly on the training partition of each fold and applied to the validation partition without snooping.

### 4.2 GroupKFold vs. StratifiedGroupKFold
- When the number of training repositories equals the number of folds ($N_{\text{repos}} = K = 5$), each fold's validation partition contains exactly one repository.
- Under this condition, `StratifiedGroupKFold` cannot reassign observations across folds because repository groups are indivisible.
- Because our sampling methodology enforces a 1:1 ratio between SZZ buggy methods and candidate clean methods, each repository's internal class balance is naturally ~45%–55%, satisfying stratification requirements without manual grouping adjustments.

---

## 5. Decision Threshold Selection Methodology

To eliminate post-selection inference bias, the threshold selection protocol must be separated from final performance reporting:

### Recommended Protocol: Nested Out-of-Fold Threshold Selection
```
Outer CV Fold k (Train on Repos A, B, C; Val on Repo D):
  │
  ├── Inner CV Loop (within Repos A, B, C):
  │     ├── Train configurations across sub-folds
  │     ├── Sweep thresholds on inner out-of-fold predictions
  │     └── Select optimal threshold τ*
  │
  └── Apply τ* to Outer Validation Repo D (Unbiased Evaluation)
```

In the current $K=2$ prototype (which lacks sufficient repositories for nested partitioning), the threshold was tuned on pooled out-of-fold predictions and transferred to the independent holdout. The report explicitly documents this as an empirical limitation, validated by the fact that the holdout repository remained completely isolated from the threshold sweep.

---

## 6. Rigorous Probability Evaluation

Model evaluation must strictly separate four distinct mathematical concepts:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      PROBABILITY EVALUATION TAXONOMY                   │
├───────────────────┬────────────────────────────────────────────────────┤
│ Dimension         │ Primary Metric & Interpretation                    │
├───────────────────┼────────────────────────────────────────────────────┤
│ 1. Discrimination │ ROC-AUC & PR-AUC (Average Precision)               │
│                   │ Measures ability to rank buggy methods above clean │
│                   │ methods across ALL possible thresholds.            │
├───────────────────┼────────────────────────────────────────────────────┤
│ 2. Classification │ Precision, Recall, F1-Score, Confusion Matrix      │
│                   │ Measures binary decision utility at a specific     │
│                   │ operational threshold τ (e.g. τ = 0.50 or 0.30).   │
├───────────────────┼────────────────────────────────────────────────────┤
│ 3. Scoring Rule   │ Brier Score Loss                                   │
│                   │ Mean squared difference between predicted risk     │
│                   │ probability and binary ground truth.               │
├───────────────────┼────────────────────────────────────────────────────┤
│ 4. Calibration    │ Expected Calibration Error (ECE) & Reliability Plot│
│                   │ Measures whether a predicted risk of P=0.70        │
│                   │ actually corresponds to 70% empirical bug rate.    │
└───────────────────┴────────────────────────────────────────────────────┘
```

### Critical Epistemological Caveat:
> **A lower Brier score does NOT prove that a model is well-calibrated.**
- The Brier score decomposes into **Reliability (calibration)**, **Resolution (discrimination)**, and **Uncertainty (inherent label entropy)**:
  $$\text{BS} = \text{Reliability} - \text{Resolution} + \text{Uncertainty}$$
- A model with strong discrimination can achieve a low Brier score even if its raw probabilities are uncalibrated.
- Raw Random Forest probabilities reflect the proportion of decision trees voting positive; they are **not calibrated Bayesian posteriors**. When calibrating models (via Platt Scaling / Sigmoid or Isotonic Regression), the calibrator must be fitted strictly on training data.

---

## 7. Independent Holdout Protocol (`JamesNK/Newtonsoft.Json`)

To ensure unassailable academic validity during final evaluation:

1. **Prerequisite Verification**: Confirm that `JamesNK/Newtonsoft.Json` has zero historical representation in the project codebase, notebooks, or documentation.
2. **Frozen Pipeline Mining**: Clone and extract methods using the exact, unmodified pipeline (`commit_collector`, `szz_analyzer`, `label_manager`, `roslyn_client`).
3. **Snapshot Freezing**: Create and hash a permanent dataset snapshot (`csharp_empirical_holdout_newtonsoft_v1.0.0.csv`).
4. **Model & Threshold Freezing**: Train the winning configuration (`rf_feature_constrained_log2`) and freeze the decision threshold ($\tau = 0.30$) strictly using the training partition.
5. **One-Shot Evaluation**: Evaluate the frozen model on `Newtonsoft.Json` exactly once.
6. **No Post-Hoc Tuning**: Record all classification, discrimination, and calibration metrics without performing subsequent model alterations.

---

## 8. Human Validation Study Protocol Rigor

In [docs/DEVELOPER_STUDY_TEMPLATE.md](file:///e:/PERSONAL/GitHub/1_Applied-Computational-Intelligence-UBB/Year2_Semester1_ComputationalIntelligenceSoftwareEngineering/CISE_Project2/docs/DEVELOPER_STUDY_TEMPLATE.md):
1. **Sampling Transparency**: The 24 methods are explicitly stratified across confusion matrix quadrants (6 TP, 6 FP, 6 TN, 6 FN) to evaluate why false alarms and subtle misses occur.
2. **Double-Blind Protection**: Reviewers receive zero model risk scores, SZZ labels, commit hashes, or repository identities.
3. **Public Searchability Limitation**: Evaluators with public GitHub access could search unique string literals or signatures. The protocol discloses this limitation and prescribes identifier de-anonymization (`Method_01`, `Tokenize_Args`) when executing strict blinded studies.
4. **Ordinal Consensus**: Inter-rater agreement on 5-point Likert scales must be evaluated using **Krippendorff's Alpha ($\alpha$) with ordinal difference metric**, Intraclass Correlation Coefficient $\text{ICC}(2, k)$, and Kendall's $W$, rather than unweighted nominal Fleiss' $\kappa$.
5. **Pending Status**: The developer validation study remains explicitly labeled as **PENDING EMPIRICAL EXECUTION** until real developer assessments are gathered. No synthetic or simulated human responses are reported.

---

*This methodology review governs all subsequent dataset expansions and academic report revisions.*

