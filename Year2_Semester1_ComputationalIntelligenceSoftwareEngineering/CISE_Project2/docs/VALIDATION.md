# Validation Protocol & Data Leakage Prevention

## 1. The Cross-Repository Data Leakage Problem

In software engineering defect prediction research, standard random row splitting (e.g. `train_test_split`) introduces severe data leakage and produces artificially inflated, non-generalizable results:

1. **Architectural & Style Leakage**: Methods written within the same repository share common coding styles, team conventions, class naming patterns, exception handling practices, and shared helper calls.
2. **Author Correlation**: Commits authored by the same developers exhibit correlated syntax habits.
3. **Over-Optimistic Metrics**: When methods from repository $R$ appear in both the training set and the test set, the classifier memorizes repository-specific metric baselines instead of learning general defect-inducing structural patterns.

### Mitigation Protocol: Repository-Aware Group Partitioning

To guarantee rigorous evaluation:
- We partition observations strictly by **`repository_id`**.
- **Holdout Test Set**: Created via `GroupShuffleSplit(n_splits=1, test_size=0.25)` grouped by `repository_id`. Repositories designated as holdout are excluded entirely from model fitting and hyperparameter optimization.
- **Cross-Validation**: Within the training repositories, internal validation uses `GroupKFold(n_splits=k)` grouped by `repository_id`. Folds alternate so that each fold evaluates on a repository unseen by the remaining $k-1$ training folds.
- **Preconditioning Rule**: The preprocessor (`DataPreprocessor`) fits its median imputation and variance thresholds exclusively on the training partition and transforms the test partition without updating its state.

---

## 2. Evaluation Metrics Specification

Because software defect datasets frequently exhibit natural class imbalance (e.g., 10%–25% buggy methods vs 75%–90% clean methods), simple accuracy is inadequate. The evaluation protocol reports:

### 2.1 Confusion Matrix

| | Predicted Clean (0) | Predicted Buggy (1) |
| :--- | :--- | :--- |
| **Actual Clean (0)** | True Negatives ($TN$) | False Positives ($FP$) |
| **Actual Buggy (1)** | False Negatives ($FN$) | True Positives ($TP$) |

### 2.2 Core Performance Metrics

1. **Accuracy**:
   $$\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}$$
2. **Precision (Positive Predictive Value)**:
   $$\text{Precision} = \frac{TP}{TP + FP}$$
   Measures the likelihood that a flagged method is genuinely defective. Critical in developer workflows to prevent "alert fatigue".
3. **Recall (Sensitivity / Detection Rate)**:
   $$\text{Recall} = \frac{TP}{TP + FN}$$
   Measures the proportion of actual buggy methods successfully identified by the model.
4. **F1-Score**:
   $$F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}} = \frac{2 TP}{2 TP + FP + FN}$$
   Harmonic mean of precision and recall; primary metric for model comparison.
5. **ROC-AUC (Receiver Operating Characteristic Area Under Curve)**:
   Measures the model's discriminative ability across all possible classification probability thresholds by integrating True Positive Rate against False Positive Rate.
6. **PR-AUC (Average Precision / Precision-Recall Curve)**:
   Summarizes the trade-off between precision and recall across decision thresholds; particularly informative under high class imbalance.

---

## 3. Baseline Comparison Protocol

To prove that the Random Forest model captures meaningful structural defect signals rather than trivial distributions:

- **Majority Class / Stratified Baseline (`DummyClassifier`)**:
  - Implements a naïve baseline that predicts class labels according to class distributions without examining input code metrics.
  - Both Random Forest and DummyClassifier are evaluated over the exact same `GroupKFold` repository splits.
  - The system reports the statistical lift of Random Forest over the dummy baseline across F1-score, accuracy, and ROC-AUC.

---

## 4. Verification & Validation Checklist

Before accepting a trained model artifact:
- [x] Zero repository overlap verified between training and holdout test partitions.
- [x] Preprocessor fitted solely on training partition.
- [x] Constant (zero-variance) features automatically removed.
- [x] Feature matrix $X$ stripped of identifiers (`observation_id`, `commit_sha`, `file_path`, `method_name`, `repository_id`).
- [x] Uncertain observations (`label = -1`) strictly excluded from dataset snapshots.
- [x] Evaluation metrics computed on untouched holdout test partition.
- [x] MDI and Permutation feature importances computed and cross-verified.
- [x] Model bundle serialized with complete execution provenance.

---

## 5. Real-World Validation & Error Analysis Protocol (Phase 6)

### 5.1 Observation Benchmarking
The application provides an interactive validation tab allowing users to test the trained model against mined C# observations stored in SQLite:
- Observations with SZZ ground-truth labels (**Label 1**: pre-fix buggy methods, **Label 0**: stable candidate clean methods) are passed to `BugPredictor.predict_from_metrics()`.
- Empirical validation accuracy, True Positives ($TP$), False Positives ($FP$), True Negatives ($TN$), and False Negatives ($FN$) are computed and displayed live in the interface.

### 5.2 Error Analysis Taxonomy
- **False Positives ($FP$)**: Clean methods flagged as defect-prone by the model. These typically represent methods with necessary high structural complexity (e.g., complex lexical parsers, bytecode emitters, or dispatch tables) that have been carefully designed and thoroughly verified.
- **False Negatives ($FN$)**: Buggy methods classified as clean. These often correspond to subtle semantic bugs (such as an incorrect comparison operator, off-by-one index, or omitted null check) that occur in structurally simple, compact methods.

### 5.3 Observation Provenance Separation
To maintain scientific rigor:
1. **Training Observations**: Observations from training repositories used to fit decision trees.
2. **Cross-Validation Observations**: Observations evaluated during internal `GroupKFold` folds.
3. **Holdout Evaluation Observations**: Observations from holdout repositories strictly used for final one-shot model scoring.
4. **Interactive Validation Observations**: Mined or newly ingested methods tested in the GUI to verify real-world behavior, never reused to retune model hyperparameters.

---

## 6. Empirical Validation Outcomes (Phase 7)

The empirical validation protocol was executed across 3 public GitHub repositories (`commandlineparser/commandline`, `LuckyPennySoftware/MediatR`, `Humanizr/Humanizer`):
- **Dataset Snapshot**: `csharp_empirical_v1` (v1.0.0, 483 observations: 226 Buggy, 257 Candidate Clean).
- **Leakage-Free Partition**: Trained on `MediatR` + `Humanizer` (382 methods); evaluated on holdout `CommandLineParser` (101 methods).
- **Results**:
  - Holdout Recall: **81.82%** (36/44 bugs identified)
  - Holdout Precision: **50.70%**
  - Holdout F1-Score: **0.6261**
  - Holdout ROC-AUC: **0.6118**
- Complete findings and error analysis are documented in [docs/FINAL_REPORT.md](FINAL_REPORT.md).
