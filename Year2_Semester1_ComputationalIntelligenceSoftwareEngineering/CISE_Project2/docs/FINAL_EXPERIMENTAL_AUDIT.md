# Independent Academic Audit & Experimental Integrity Report
## Machine Learning-Based Software Defect Prediction for C# Source Code

**Auditor Role:** Senior ML4SE Research Engineer & Independent Academic Reviewer  
**Date of Audit:** November 2026  
**Audit Target:** Automated Experimentation Pipeline, Multi-Model Baselines, Calibration, and Validation Artifacts  
**Evaluated Artifact Directory:** `reports/experiments/exp_20261113_170914/`  
**Core Reference Documents:** `docs/FINAL_REPORT.md`, `docs/DEVELOPER_STUDY_TEMPLATE.md`, `exports/csharp_empirical_v1_v1.0.0.csv`  

---

## Executive Summary

An exhaustive, read-only empirical audit was conducted on the machine learning defect prediction codebase, automated experiment outputs, and documentation. The project exhibits commendable methodological rigor in several key areas:
1. **Zero Intra-Repository Data Leakage**: Repository-level isolation (`GroupKFold`) is strictly enforced; training and validation partitions share 0% code.
2. **In-Fold Preprocessing Isolation**: Imputation, variance pruning, and feature scaling (`StandardScaler` for Logistic Regression) are fitted strictly on training folds and transformed on validation/holdout sets.
3. **Comprehensive Baselines**: Multiple baseline families (Majority Dummy, Stratified Dummy, Logistic Regression, Decision Trees, and Random Forest ensembles) are benchmarked on identical splits.
4. **Reproducibility**: Complete pipeline provenance is preserved in versioned JSON, CSV, and joblib artifacts.

However, the audit identified **four critical/high-severity issues** and several subtle statistical discrepancies that must be rectified before formal academic submission:
- **Discrepant Feature Importances**: The MDI and Permutation Feature Importance tables in `docs/FINAL_REPORT.md` Section 7.5 were carried over from an earlier baseline model and do not match the serialized artifact (`exp_20261113_170914`).
- **Misattribution of Calibration Winner**: `docs/FINAL_REPORT.md` incorrectly attributes the lowest Brier score to the Rank 1 F1 model (`rf_feature_constrained_log2`, Brier = 0.2317), whereas `rf_compact_regularized` actually achieved the lowest Brier score (**0.2182**) and the highest ROC-AUC (**0.6970**).
- **Post-Selection Optimism Bias in Decision Threshold Tuning**: Out-of-fold cross-validation predictions were used simultaneously for both hyperparameter ranking and decision threshold selection ($\tau = 0.30$), introducing selection bias.
- **Methodological Flaw in Developer Study Agreement Metric**: `docs/DEVELOPER_STUDY_TEMPLATE.md` specifies nominal Fleiss' Kappa ($\kappa$) for ordinal 5-point Likert ratings, which improperly treats 1-point and 4-point disagreements identically.

---

## 1. Numerical Consistency Audit

Every metric reported in the latest experiment artifacts (`reports/experiments/exp_20261113_170914/`) was extracted, parsed, and independently recalculated from first principles.

### 1.1 Model Ranking & Selection Verification

The experiment evaluated 11 configurations across four model families on the training partition (382 methods across `MediatR` and `Humanizer`):

| Rank | Configuration ID | Algorithm Family | Reported F1 | Recalculated F1 | Reported Brier | Recalculated Brier | Reported ROC-AUC | Reported Accuracy |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **#1** | `rf_feature_constrained_log2` | Random Forest | **0.6801** | **0.6801** | **0.2317** | **0.2317** | 0.6525 | 0.6390 |
| **#2** | `rf_baseline_balanced` | Random Forest | **0.6768** | **0.6768** | **0.2336** | **0.2336** | 0.6349 | 0.6428 |
| **#3** | `rf_heavy_bagging_300` | Random Forest | **0.6729** | **0.6729** | **0.2343** | **0.2343** | 0.6386 | 0.6428 |
| **#4** | `rf_compact_regularized` | Random Forest | **0.6721** | **0.6721** | **0.2182** | **0.2182** | **0.6970** | 0.6246 |
| **#5** | `dt_depth8` | Decision Tree | **0.6388** | **0.6388** | **0.3423** | **0.3423** | 0.6430 | 0.6558 |
| **#6** | `rf_deep_capacity` | Random Forest | **0.6381** | **0.6381** | **0.2484** | **0.2484** | 0.6107 | 0.6146 |
| **#7** | `lr_balanced_c1` | Logistic Regression | **0.6362** | **0.6362** | **0.2884** | **0.2884** | 0.6858 | 0.6534 |
| **#8** | `lr_standard_c1` | Logistic Regression | **0.6187** | **0.6187** | **0.2877** | **0.2877** | 0.6862 | 0.6424 |
| **#9** | `dt_shallow_depth4` | Decision Tree | **0.6102** | **0.6102** | **0.3025** | **0.3025** | 0.6769 | 0.6507 |
| **#10** | `dummy_stratified` | Dummy Baseline | **0.4170** | **0.4170** | **0.5441** | **0.5441** | 0.4536 | 0.4559 |
| **#11** | `dummy_most_frequent` | Dummy Baseline | **0.0000** | **0.0000** | **0.4751** | **0.4751** | 0.5000 | 0.5249 |

#### Verified Findings:
1. **Best F1 Identification**: `rf_feature_constrained_log2` is mathematically confirmed as Rank 1 under the chosen selection metric (`f1`), achieving a mean CV score of **0.6801**.
2. **Lowest Brier Score Misattribution (INCONSISTENCY)**:
   - In `docs/FINAL_REPORT.md` Section 7.1, the prose states:  
     *"Random Forest configurations dominate the ranking... achieving the highest cross-validation F1 (0.6801...) and superior probability calibration (Brier score 0.2317)."*
   - **Audit Finding**: `rf_feature_constrained_log2` does **not** possess the lowest Brier score. Rank 4 (`rf_compact_regularized`) achieved a Brier score of **0.2182**, which is **0.0135 lower** (better calibrated). Furthermore, `rf_compact_regularized` achieved a superior ROC-AUC (**0.6970** vs **0.6525**) and PR-AUC (**0.6210** vs **0.5875**). Selecting purely on F1 favored a model with higher threshold-specific classification score at $\tau=0.50$, but inferior overall calibration and discrimination.
3. **Dummy Baselines**: Both Dummy classifiers were verified to execute on the exact same cross-validation splits and dataset observations.

---

### 1.2 Fold-Level Confusion Matrix and Metric Recalculation

For the selected model (`rf_feature_constrained_log2`), fold metrics were recalculated from raw confusion matrices:

#### Fold 1 (Train: `MediatR` [91 obs], Val: `Humanizer` [291 obs: 139 Buggy, 152 Clean])
- **Reported Confusion Matrix**: `TN = 122, FP = 30, FN = 33, TP = 106` (Sum = 291)
- **Recalculated Accuracy**: $(106 + 122) / 291 = 228 / 291 = 0.783505 \to \mathbf{0.7835}$ (Reported: 0.7835, Error: $0.0000$)
- **Recalculated Precision**: $106 / (106 + 30) = 106 / 136 = 0.779412 \to \mathbf{0.7794}$ (Reported: 0.7794, Error: $0.0000$)
- **Recalculated Recall**: $106 / (106 + 33) = 106 / 139 = 0.762590 \to \mathbf{0.7626}$ (Reported: 0.7626, Error: $0.0000$)
- **Recalculated F1-Score**: $2 \times (0.779412 \times 0.762590) / (0.779412 + 0.762590) = \mathbf{0.7709}$ (Reported: 0.7709, Error: $0.0000$)
- **Brier Score**: $\mathbf{0.1730}$

#### Fold 2 (Train: `Humanizer` [291 obs], Val: `MediatR` [91 obs: 43 Buggy, 48 Clean])
- **Reported Confusion Matrix**: `TN = 12, FP = 36, FN = 10, TP = 33` (Sum = 91)
- **Recalculated Accuracy**: $(33 + 12) / 91 = 45 / 91 = 0.494505 \to \mathbf{0.4945}$ (Reported: 0.4945, Error: $0.0000$)
- **Recalculated Precision**: $33 / (33 + 36) = 33 / 69 = 0.478261 \to \mathbf{0.4783}$ (Reported: 0.4783, Error: $0.0000$)
- **Recalculated Recall**: $33 / (33 + 10) = 33 / 43 = 0.767442 \to \mathbf{0.7674}$ (Reported: 0.7674, Error: $0.0000$)
- **Recalculated F1-Score**: $2 \times (0.478261 \times 0.767442) / (0.478261 + 0.767442) = \mathbf{0.5893}$ (Reported: 0.5893, Error: $0.0000$)
- **Brier Score**: $\mathbf{0.2904}$

#### Aggregate Means and Dispersion:
- **Mean F1**: $(0.7709 + 0.5893) / 2 = \mathbf{0.6801}$ (Reported: 0.6801)
- **F1 Population Std (`ddof=0`)**: $\sqrt{((0.7709-0.6801)^2 + (0.5893-0.6801)^2)/2} = \mathbf{0.0908}$ (Reported: 0.0908)
- **F1 Sample Std (`ddof=1`)**: $\sqrt{((0.7709-0.6801)^2 + (0.5893-0.6801)^2)/1} = \mathbf{0.1284}$
- **Audit Observation**: The cross-validation engine computes standard deviations with NumPy's default `ddof=0` (population variance), which understates the sample standard deviation by a factor of $\sqrt{2} \approx 1.414$ when $K=2$.

---

### 1.3 Decision Threshold Curve Recalculation

The cross-validation threshold curve was evaluated across all 382 pooled out-of-fold validation predictions:

| Threshold | Accuracy | Precision | Recall | F1-Score | TP | FP | TN (Derived) | FN (Derived) | Recalculated F1 | Audit Verdict |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.20** | 0.6911 | 0.6143 | 0.9451 | 0.7446 | 172 | 108 | 92 | 10 | 0.7446 | Exact Match |
| **0.30** | 0.7068 | 0.6287 | 0.9396 | **0.7533** | 171 | 101 | 99 | 11 | **0.7533** | Exact Match |
| **0.40** | 0.7094 | 0.6449 | 0.8681 | 0.7400 | 158 | 87 | 113 | 24 | 0.7400 | Exact Match |
| **0.45** | 0.7199 | 0.6652 | 0.8297 | 0.7384 | 151 | 76 | 124 | 31 | 0.7384 | Exact Match |
| **0.50** | 0.7147 | 0.6780 | 0.7637 | 0.7183 | 139 | 66 | 134 | 43 | 0.7183 | Exact Match |
| **0.55** | 0.6623 | 0.6532 | 0.6209 | 0.6366 | 113 | 60 | 140 | 69 | 0.6366 | Exact Match |
| **0.60** | 0.6178 | 0.6268 | 0.4890 | 0.5494 | 89 | 53 | 147 | 93 | 0.5494 | Exact Match |
| **0.70** | 0.5524 | 0.6078 | 0.1703 | 0.2661 | 31 | 20 | 180 | 151 | 0.2661 | Exact Match |
| **0.80** | 0.5052 | 0.2308 | 0.0165 | 0.0308 | 3 | 10 | 190 | 179 | 0.0308 | Exact Match |

#### Verified Findings:
1. **Arithmetic Correctness**: All reported accuracy, precision, recall, and F1 values match independent recalculations to 4 decimal places.
2. **Incomplete Confusion Matrix Reporting (INCONSISTENCY)**:
   In `src/ml/cross_validation.py` line 210, `compute_threshold_curve` only recorded `false_positives` and `true_positives` in the dictionary output, omitting `true_negatives` and `false_negatives`. The report table displayed only TP and FP, preventing immediate inspection of the full confusion matrix. At threshold 0.30, the complete confusion matrix is:
   $$\mathbf{CM}_{\text{CV, 0.30}} = \begin{pmatrix} 99 & 101 \\ 11 & 171 \end{pmatrix}$$

---

### 1.4 Holdout Test Evaluation Recalculation (`commandlineparser/commandline`)

The holdout repository contains 101 methods (44 Buggy, 57 Clean). Performance was evaluated at both $\tau=0.50$ and $\tau=0.30$:

#### Standard Threshold ($\tau = 0.50$):
- **Reported Confusion Matrix**: `TN = 18, FP = 39, FN = 10, TP = 34` (Sum = 101)
- **Recalculated Accuracy**: $(34 + 18) / 101 = 52 / 101 = 0.51485 \to \mathbf{0.5149}$ (Reported: 0.5149)
- **Recalculated Precision**: $34 / (34 + 39) = 34 / 73 = 0.46575 \to \mathbf{0.4658}$ (Reported: 0.4658)
- **Recalculated Recall**: $34 / 44 = 0.77272 \to \mathbf{0.7727}$ (Reported: 0.7727)
- **Recalculated F1-Score**: $2 \times (34) / (2 \times 34 + 39 + 10) = 68 / 117 = 0.58119 \to \mathbf{0.5812}$ (Reported: 0.5812)
- **Reported ROC-AUC**: $\mathbf{0.6041}$ | **PR-AUC**: $\mathbf{0.5252}$ | **Brier Score**: $\mathbf{0.2627}$

#### CV-Optimized Threshold ($\tau = 0.30$):
- **Reported Confusion Matrix**: `TN = 10, FP = 47, FN = 2, TP = 42` (Sum = 101)
- **Recalculated Accuracy**: $(42 + 10) / 101 = 52 / 101 = 0.51485 \to \mathbf{0.5149}$ (Reported: 0.5149)
- **Recalculated Precision**: $42 / (42 + 47) = 42 / 89 = 0.47191 \to \mathbf{0.4719}$ (Reported: 0.4719)
- **Recalculated Recall**: $42 / 44 = 0.95454 \to \mathbf{0.9545}$ (Reported: 0.9545)
- **Recalculated F1-Score**: $2 \times (42) / (2 \times 42 + 47 + 2) = 84 / 133 = 0.63158 \to \mathbf{0.6316}$ (Reported: 0.6316)

#### Verified Findings:
1. **The Invariant Accuracy Phenomenon**: The raw accuracy is mathematically identical (**0.5149**) at both $\tau=0.50$ and $\tau=0.30$. This occurs because shifting the threshold from 0.50 to 0.30 correctly reclassifies 8 False Negatives as True Positives ($FN: 10 \to 2$, $TP: 34 \to 42$), but simultaneously converts 8 True Negatives into False Positives ($TN: 18 \to 10$, $FP: 39 \to 47$). Exactly 52 out of 101 observations are correctly classified in both cases ($34+18=52$ vs $42+10=52$). This is a crucial pedagogical demonstration of why accuracy is uninformative in imbalanced defect screening.
2. **Mathematical Exactness**: All recalculated holdout metrics match the JSON and Markdown artifacts.

---

### 1.5 Feature Importance Discrepancy Audit (CRITICAL INCONSISTENCY)

Comparing the reported feature importance table in `docs/FINAL_REPORT.md` Section 7.5 against the serialized artifact `reports/experiments/exp_20261113_170914/experiment_results.json`:

| Feature Name | Reported MDI (`FINAL_REPORT.md`) | Actual MDI (`exp_...170914`) | Discrepancy | Reported Permutation (`FINAL_REPORT.md`) | Actual Permutation (`exp_...170914`) | Discrepancy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `method_length` | 0.2052 | **0.1354** | -0.0698 | +0.1208 | **+0.0891** | -0.0317 |
| `loc` | 0.1239 | **0.0964** | -0.0275 | +0.0911 | **+0.0238** | -0.0673 |
| `parameter_count` | 0.1249 | **0.0775** | -0.0474 | +0.0178 | **-0.0218** | **-0.0396 (Sign Flip)** |
| `method_call_count` | 0.0871 | **0.0550** | -0.0321 | +0.0112 | **-0.0475** | **-0.0587 (Sign Flip)** |
| `statement_count` | 0.0617 | **0.0443** | -0.0174 | +0.0105 | **-0.0297** | **-0.0402 (Sign Flip)** |
| `object_creation_count`| 0.0544 | **0.0398** | -0.0146 | +0.0277 | **-0.0020** | **-0.0297 (Sign Flip)** |
| `logical_loc` | 0.0512 | **0.0394** | -0.0118 | +0.0257 | **-0.0257** | **-0.0514 (Sign Flip)** |
| `cyclomatic_complexity`| 0.0489 | **0.0305** | -0.0184 | +0.0082 | **-0.0040** | **-0.0122 (Sign Flip)** |

#### Severity: HIGH
- **Root Cause**: The feature importance table in `docs/FINAL_REPORT.md` Section 7.5 was copied from an earlier single-model run (`exp_20261113_162850`) and was not updated when the multi-model baseline benchmark (`exp_20261113_170914`) was executed.
- **Academic Impact**: Reporting positive permutation importances for features that actually exhibited negative permutation importance on the holdout repository misrepresents how the regularized ensemble (`rf_feature_constrained_log2`) generalizes. In `exp_20261113_170914`, permuting `parameter_count` or `statement_count` actually slightly improved holdout F1, indicating collinearity and potential overfitting on those dimensions.
- **Required Action**: Replace the table in `docs/FINAL_REPORT.md` Section 7.5 with the verified values from `exp_20261113_170914`.

---

## 2. Threshold Selection & Leakage Audit

### 2.1 Protocol Inspection
The implementation of threshold selection was audited in `src/ml/experiment_runner.py` (lines 387–420):
```python
if best_config_result.cv_results.oof_predictions:
    oof_y_true = np.array(best_config_result.cv_results.oof_predictions["y_true"])
    oof_y_prob = np.array(best_config_result.cv_results.oof_predictions["y_prob"])
    threshold_curve = compute_threshold_curve(oof_y_true, oof_y_prob)

    if threshold_curve:
        best_t_entry = max(threshold_curve, key=lambda x: x["f1"])
        optimal_cv_threshold = float(best_t_entry["threshold"])
```

### 2.2 Critical Evaluation Questions:

1. **Does threshold selection use holdout data?**
   - **Verdict: NO LEAKAGE**. The holdout dataset (`commandlineparser/commandline`) was completely excluded from threshold selection. The threshold was picked strictly using `oof_predictions` from the training cross-validation partition.
2. **Does threshold selection introduce post-selection inference bias (optimism bias)?**
   - **Verdict: YES (METHODOLOGICAL ISSUE)**.  
   The same out-of-fold predictions were used to:
   - Rank and select the winning hyperparameter configuration (`rf_feature_constrained_log2`).
   - Sweep and select the optimal decision threshold ($\tau = 0.30$).
   This constitutes **double-dipping** on the validation set. The reported CV F1 of **0.7533** at $\tau = 0.30$ is an optimistic estimate because $\tau$ was tuned directly on the validation predictions of the model that won the selection tournament.
3. **Is threshold optimization nested?**
   - **Verdict: NO**. Threshold optimization was performed as a post-hoc sweep across the pooled out-of-fold validation predictions, rather than being fitted within an inner cross-validation loop.
4. **Did holdout observations influence configuration decisions?**
   - **Verdict: NO**. In the code execution, holdout evaluation was conducted strictly once on the final model trained on `X_train_proc`.

### 2.3 Recommended Statistically Defensible Approach:
To eliminate post-selection optimism in future iterations:
- Implement **Nested Threshold Tuning**: Within each training fold of GroupKFold, fit an inner threshold optimizer on an inner fold, and apply that fold-specific threshold to the outer validation fold.
- Alternatively, report the CV F1 at $\tau=0.30$ explicitly as an **optimistic post-selection tuning curve**, while reporting the holdout result ($\text{F1} = 0.6316$) as the true out-of-domain transfer test.

---

## 3. Brier Score & Probability Calibration Audit

### 3.1 Mathematical Implementation Verification
The calculation of Brier scores was audited in `src/ml/cross_validation.py` (lines 380–398):
```python
brier = float(brier_score_loss(y_f_val, y_prob))
```
- **Positive-Class Alignment**: Verified that `y_prob = model.predict_proba(X_f_val)[:, 1]`. Because `model.classes_` is `array([0, 1])`, column index 1 corresponds strictly to the positive (buggy) class.
- **Leakage Status**: Zero leakage. `y_prob` is generated on out-of-fold validation data using estimators fitted on training fold data.
- **Comparability Across Models**:
  - `DummyClassifier (most_frequent)`: Outputs $P(\text{buggy}) = 0.0$ for all instances. Brier score equals the base rate of positive cases:
    $$\text{Brier}_{\text{dummy}} = \frac{1}{N} \sum (y_i - 0)^2 = \text{Mean}(y) = 0.4751$$
  - `DummyClassifier (stratified)`: Brier score is **0.5441** (worse than majority guessing due to random variance).
  - `DecisionTree (depth=8)`: Brier score is **0.3423** (uncalibrated leaf purity creates extreme overconfidence).
  - `LogisticRegression (balanced)`: Brier score is **0.2884** (well-behaved sigmoid probabilities).
  - `RandomForest (feature_constrained_log2)`: Brier score is **0.2317** on CV and **0.2627** on holdout.
  - `RandomForest (compact_regularized)`: Brier score is **0.2182** (best calibrated).

### 3.2 Probability Quality vs. Calibration Distinction:
The report must carefully distinguish:
- **Discrimination Power (Ranking Ability)**: Measured by ROC-AUC and Average Precision (PR-AUC). High ROC-AUC means buggy methods receive higher risk scores than clean methods, regardless of scale.
- **Calibration (Reliability)**: Measured by Brier score and reliability diagrams. A well-calibrated model means that among methods assigned a risk score of 0.70, exactly 70% are defective.
- **Sample Size Constraint**: With $N=91$ in Fold 2 and $N=101$ in the holdout repository, fitting non-parametric calibration mappers (such as Isotonic Regression or Platt scaling) would overfit due to small sample sizes. The current decision to report raw ensemble probabilities and Brier score loss without applying post-hoc calibration is scientifically justified.

---

## 4. Cross-Validation Audit

### 4.1 Implemented Infrastructure vs. Executed Reality

| Dimension | Implemented Codebase Capability | Actual Execution (`exp_20261113_170914`) | Audit Verdict |
| :--- | :--- | :--- | :--- |
| **Splits Strategy** | `RepositoryGroupKFoldValidator(n_splits=5)` | Adapted to 2-fold GroupKFold | **Accurate** (Handled via readiness check) |
| **Training Repositories** | Requires $\ge 5$ distinct groups | Exactly 2 repositories (`MediatR` + `Humanizer`) | **Confirmed 2 Groups** |
| **Holdout Repositories** | 1 repository (`commandlineparser/commandline`) | 1 repository (`commandlineparser/commandline`) | **Confirmed 1 Group** |
| **Repository Separation** | Zero cross-repository leakage | Zero overlap in all folds | **PASS** |
| **Random State** | Fixed seed (42) | Fixed seed (42) | **PASS (Deterministic)** |

### 4.2 Class Distribution & Asymmetry Across Folds

The two executed folds exhibit substantial size and metric asymmetry:

| Fold | Training Repo | Train Obs (B / C) | Validation Repo | Val Obs (B / C) | Val F1 | Val ROC-AUC | Val Brier |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **Fold 1** | `MediatR` (ID 3) | 91 (43 / 48) | `Humanizer` (ID 4) | 291 (139 / 152) | **0.7709** | **0.8200** | **0.1730** |
| **Fold 2** | `Humanizer` (ID 4) | 291 (139 / 152) | `MediatR` (ID 3) | 91 (43 / 48) | **0.5893** | **0.4850** | **0.2904** |

#### Academic Assessment:
1. **Fold 2 Degradation**: When trained on `Humanizer` (291 methods) and tested on `MediatR` (91 methods), ROC-AUC dropped to **0.4850** (slightly below random guessing), and F1 dropped to **0.5893**. This demonstrates significant domain shift between `Humanizer` (string/date manipulation extensions) and `MediatR` (reflection-based CQRS pipeline handlers).
2. **Sample Size Weighting**: Fold 1 contains 76.2% of the training data. Averaging the two folds unweighted (macro-average) penalizes the model heavily for its poor performance on `MediatR`.
3. **Mandatory Documentation Clarification**: The report must clearly state that all experimental numbers originate from **2-fold GroupKFold**, while noting that the 5-fold architecture is implemented and verified for future corpus expansions.

---

## 5. Holdout Independence Audit

### 5.1 Historical Inspection Analysis
An inspection of the repository commit logs, previous report drafts, and code comments was conducted to determine how `commandlineparser/commandline` has been used throughout the project lifecycle:
- In early project iterations (prior to the introduction of automated experiment runners), `CommandLineParser` was evaluated post-hoc.
- Specific misclassifications (e.g. 8 False Negatives such as `CreateDefaultImmutableInstance` and 35 False Positives in parser routines) were manually inspected and documented.
- Permutation feature importance was previously run against `CommandLineParser`.

### 5.2 Academic Validity Judgment:
- **Can CommandLineParser be described as a strictly untouched independent holdout?**  
  **NO, with qualifications.** In formal machine learning methodology, once researchers inspect errors on a holdout set and reason about why specific methods failed, subsequent decisions (such as choosing to evaluate Random Forest vs. tree depths or feature representations) are subject to **researcher confirmation bias**.
- **What mitigations are present?**  
  In the current implementation:
  - The holdout data was never passed to `fit()` or `fit_transform()`.
  - Hyperparameters were ranked strictly on CV F1.
  - The decision threshold was selected strictly on CV out-of-fold predictions.
- **Recommendation for Academic Submission**:
  1. Retain the explicit disclosure in Section 9.1 acknowledging that `CommandLineParser` served as an exploratory holdout.
  2. Propose mining a completely fresh, previously uninspected C# repository (e.g. `AutoMapper` or `Newtonsoft.Json`) as a final, uncompromised test corpus in future work.

---

## 6. Developer Study Audit (`docs/DEVELOPER_STUDY_TEMPLATE.md`)

An audit of the human validation protocol in [docs/DEVELOPER_STUDY_TEMPLATE.md](file:///e:/PERSONAL/GitHub/1_Applied-Computational-Intelligence-UBB/Year2_Semester1_ComputationalIntelligenceSoftwareEngineering/CISE_Project2/docs/DEVELOPER_STUDY_TEMPLATE.md) revealed both strong design elements and two methodological flaws:

### 6.1 Strengths:
1. **Balanced Stratified Sampling**: Exactly 6 methods were sampled from each of the four confusion matrix quadrants (6 TP, 6 FP, 6 TN, 6 FN), providing an ideal testbed for analyzing false alarms and subtle misses.
2. **Clean Anonymization**: Code snippets strip repository names, file paths, commit SHAs, SZZ ground-truth labels, and model prediction scores.
3. **Multi-Faceted Likert Dimensions**: Evaluating Defect Likelihood, Cognitive Complexity, and Review Urgency captures the nuanced reasons why developers accept or reject tool alerts.

### 6.2 Flaws & Methodological Concerns:

#### 1. Methodological Flaw: Nominal Fleiss' Kappa for Ordinal Likert Data (HIGH SEVERITY)
- **Current Formulation**: Section 5.1 specifies unweighted **Fleiss' Kappa ($\kappa$)** to assess inter-rater agreement across the 5 rating categories.
- **The Problem**: Fleiss' Kappa treats rating categories as **unordered nominal labels**. It penalizes a 1-point difference (Rater A = 4, Rater B = 5) with the exact same weight as a 4-point disagreement (Rater A = 1, Rater B = 5). For ordinal Likert scales, this severely understates true inter-rater consensus.
- **Recommended Statistical Correction**:
  Replace or augment Fleiss' Kappa with:
  1. **Krippendorff's Alpha ($\alpha$) with an Ordinal Difference Function**:
     $$\delta^2(c, k) = \left( \sum_{g=c}^k n_g - \frac{n_c + n_k}{2} \right)^2$$
  2. **Intraclass Correlation Coefficient (ICC(2, k))**: Standard for inter-rater reliability of continuous/ordinal scale ratings across multiple raters.
  3. **Kendall's Coefficient of Concordance ($W$)**: Non-parametric measure of rater concordance across ranked items.

#### 2. Risk of Identifier De-Anonymization (LOW SEVERITY)
- **Current Formulation**: In Section 3, method declarations retain exact identifiers (e.g. `CanCast`, `TokenizeShortName`, `Choose`, `ExplodeOptionList`).
- **The Problem**: An evaluator with domain knowledge or access to GitHub could search for `public IEnumerable<Token> TokenizeShortName` and immediately identify `commandlineparser/commandline`.
- **Recommended Correction**: For strict double-blind administration, rename method identifiers and project-specific types to generic equivalents (`Method_05`, `Tokenize_Args`, etc.).

---

## 7. Corrections Required in `docs/FINAL_REPORT.md`

The following specific corrections must be made in `docs/FINAL_REPORT.md` to ensure absolute alignment with the underlying experiment artifacts:

1. **Section 7.1 Text**:
   - *Current*: *"achieving the highest cross-validation F1 (0.6801...) and superior probability calibration (Brier score 0.2317)."*
   - *Correction*: Clarify that `rf_feature_constrained_log2` won on F1, while `rf_compact_regularized` achieved the lowest Brier score (**0.2182**) and highest ROC-AUC (**0.6970**).
2. **Section 7.5 MDI & Permutation Importance Table**:
   - *Current*: Displays obsolete values (`method_length` MDI = 0.2052, Permutation = +0.1208).
   - *Correction*: Update table to match `exp_20261113_170914`:
     - `method_length`: MDI = **0.1354**, Permutation Mean = **+0.0891** ($\pm 0.0089$)
     - `loc`: MDI = **0.0964**, Permutation Mean = **+0.0238** ($\pm 0.0173$)
     - `parameter_count`: MDI = **0.0775**, Permutation Mean = **-0.0218** ($\pm 0.0074$)
     - `statement_count`: MDI = **0.0443**, Permutation Mean = **-0.0297** ($\pm 0.0108$)
3. **Section 7.2 Decision Threshold Optimization Table**:
   - *Current*: Omits True Negatives and False Negatives.
   - *Correction*: Add explicit columns for True Negatives ($TN$) and False Negatives ($FN$) across all threshold steps.
4. **Section 8.3 & Developer Study Design**:
   - *Current*: References Fleiss' Kappa without noting ordinal limitations.
   - *Correction*: Note that ordinal agreement will be evaluated using Krippendorff's $\alpha$ (ordinal metric) and Kendall's $W$.

---

## 8. Prioritized Recommendations for Academic Submission

| Priority | Area | Issue | Actionable Recommendation |
| :---: | :--- | :--- | :--- |
| **P1** | Documentation Alignment | MDI & Permutation importances in report do not match joblib artifact. | Update `docs/FINAL_REPORT.md` Section 7.5 with exact values from `exp_20261113_170914`. |
| **P1** | Documentation Alignment | Brier score winner misattributed in report text. | Update `docs/FINAL_REPORT.md` Section 7.1 to credit `rf_compact_regularized` for lowest Brier score. |
| **P2** | Methodology Protocol | Nominal Fleiss' Kappa applied to ordinal Likert scale. | Update `docs/DEVELOPER_STUDY_TEMPLATE.md` Section 5 to specify Krippendorff's ordinal $\alpha$ and ICC(2,k). |
| **P2** | Reporting Precision | Incomplete confusion matrix in CV threshold curve. | Update `src/ml/cross_validation.py` to record $TN$ and $FN$ in `compute_threshold_curve`. |
| **P3** | Statistical Precision | NumPy population std (`ddof=0`) used for $K=2$ CV variance. | Clarify in documentation or update code to use sample std (`ddof=1`). |
| **P3** | Future Work | Optimism bias in post-hoc CV threshold tuning. | Propose nested cross-validation for threshold tuning in future multi-repository expansions. |

---

## Conclusion

The project's empirical implementation is fundamentally sound, fully reproducible, and free of physical data leakage. The discrepancies identified by this audit are documentation synchronizations and statistical metric adjustments rather than fatal methodological flaws. Implementing the prioritized recommendations will ensure the work is academically defensible and ready for formal submission.

