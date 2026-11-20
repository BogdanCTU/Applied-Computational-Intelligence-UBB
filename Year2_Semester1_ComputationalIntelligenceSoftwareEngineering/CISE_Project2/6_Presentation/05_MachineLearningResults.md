# 05 — Machine Learning Models & Experimental Results

---

## 1. Baseline vs. Nested Optimization Results (Dataset #2, $N=578$)

Twenty model configurations across 6 classifier families were evaluated under the $5 \times 4$ nested repository-level `GroupKFold` protocol (`scikit-learn 1.9.1`). Below are the primary configurations compared against the original baseline (`rf_compact_regularized`):

| Model Configuration | Outer ROC-AUC | Outer PR-AUC | Outer Brier | Nested $\tau$ F1 | Pooled OOF ROC-AUC | Pooled OOF F1 | Pooled Recall | Pooled Precision | Pooled Accuracy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Original Baseline (`rf_compact_regularized`)** | 0.7037 $\pm$ 0.1292 | 0.6405 $\pm$ 0.1135 | 0.2146 $\pm$ 0.0398 | 0.7408 $\pm$ 0.0760 | 0.7024 | 0.7294 | 86.02% | 63.32% | 69.20% |
| **Optimized Random Forest (`rf_nested_opt_v3_depth6_leaf8_log2`)** | 0.7216 $\pm$ 0.1156 | **0.6465 $\pm$ 0.1026** | **0.2055 $\pm$ 0.0374** | 0.7539 $\pm$ 0.0706 | 0.7213 | 0.7406 | 88.53% | 63.66% | 70.07% |
| **Optimized Extra Trees (`et_nested_opt_v3_depth6_leaf6_log2`)** | **0.7349 $\pm$ 0.0703** | 0.6443 $\pm$ 0.0496 | 0.2062 $\pm$ 0.0213 | **0.7667 $\pm$ 0.0723** | **0.7470** | **0.7653** | **91.76%** | **65.64%** | **72.84%** |
| Calibrated Extra Trees (`et_calibrated_sigmoid`) | 0.7279 $\pm$ 0.0679 | 0.6380 $\pm$ 0.0568 | 0.2116 $\pm$ 0.0268 | 0.6775 $\pm$ 0.0598 | 0.6725 | 0.6626 | 99.64% | 49.64% | 50.87% |
| Logistic Regression (`lr_l2_C0.1_balanced`) | 0.6929 $\pm$ 0.0888 | 0.6251 $\pm$ 0.0972 | 0.2400 $\pm$ 0.0309 | 0.7186 $\pm$ 0.0734 | 0.6923 | 0.7130 | 82.08% | 63.02% | 67.99% |
| HistGradientBoosting (`hgb_depth4_leaf15_lr03`) | 0.6531 $\pm$ 0.1304 | 0.6080 $\pm$ 0.1342 | 0.2512 $\pm$ 0.0642 | 0.6845 $\pm$ 0.0928 | 0.6641 | 0.6951 | 81.72% | 60.48% | 65.40% |

*Note on Historical Baseline Figures:* In the original unnested 5-fold `GroupKFold` benchmark (`3_TestResults/CrossValidation/experiment_results.json`, `scikit-learn 1.6.1`), `rf_compact_regularized` achieved fold-mean F1 `0.6859`, ROC-AUC `0.7025`, Brier `0.2144`, and pooled OOF F1 `0.7405` at fixed $\tau^* = 0.40$ (`67.13%` accuracy at $\tau = 0.50$).

### Hyperparameter Comparison

| Parameter | Baseline RF (`rf_compact_regularized`) | Optimized RF (`rf_nested_opt_v3_depth6_leaf8_log2`) | Optimized Extra Trees (`et_nested_opt_v3_depth6_leaf6_log2`) |
| :--- | :---: | :---: | :---: |
| Estimator | `RandomForestClassifier` | `RandomForestClassifier` | `ExtraTreesClassifier` |
| `n_estimators` | 100 | 200 | 200 |
| `max_depth` | 8 | 6 | 6 |
| `min_samples_split` | 5 | 10 | 8 |
| `min_samples_leaf` | 4 | 8 | 6 |
| `max_features` | `'sqrt'` | `'log2'` | `'log2'` |
| `class_weight` | `'balanced'` | `'balanced'` | `'balanced'` |

---

## 2. Per-Repository Performance (Outer Test Folds)

| Outer Fold | Held-Out Repository | $N$ | Baseline RF ROC-AUC | Optimized RF ROC-AUC | Optimized ET ROC-AUC | Baseline RF Nested F1 | Optimized RF Nested F1 | Optimized ET Nested F1 |
| :---: | :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Fold 1 | `Humanizr/Humanizer` | 291 | 0.7280 | 0.7510 | **0.7689** | 0.7688 | 0.7853 | **0.8068** |
| Fold 2 | `serilog/serilog` | 134 | 0.5882 | 0.6317 | **0.6958** | 0.6418 | 0.6569 | **0.6667** |
| Fold 3 | `LuckyPennySoftware/MediatR` | 91 | 0.6475 | 0.6494 | **0.6905** | 0.7302 | 0.7385 | **0.7500** |
| Fold 4 | `App-vNext/Polly` | 34 | **0.9256** | 0.9221 | 0.8581 | **0.8718** | **0.8718** | **0.8718** |
| Fold 5 | `FluentValidation/FluentValidation` | 28 | 0.6292 | 0.6538 | **0.6611** | 0.6914 | 0.7170 | **0.7381** |
| **Mean $\pm$ SD** | **5 Repositories** | **578** | **0.7037 $\pm$ 0.1292** | **0.7216 $\pm$ 0.1156** | **0.7349 $\pm$ 0.0703** | **0.7408 $\pm$ 0.0760** | **0.7539 $\pm$ 0.0706** | **0.7667 $\pm$ 0.0723** |

---

## 3. Feature Collinearity & Permutation Importance

- **Collinearity:** 11 feature pairs exceed $|r| \ge 0.85$ on Dataset #2 (`loc` vs. `logical_loc` $r = 0.9967$; `loc` vs. `method_length` $r = 0.9951$; `cyclomatic_complexity` vs. `if_count` $r = 0.8808$). Removing collinear features (`rf_corr_pruned_085`) slightly reduced outer ROC-AUC (`0.7155` vs. `0.7216`); full-26 tree ensembles with `max_features='log2'` handled collinearity more effectively.
- **Top Permutation Features (Out-of-Fold ROC-AUC Drop):** `parameter_count` (`+0.0802`), `method_length` (`+0.0258`), `loc` (`+0.0170`), `statement_count` (`+0.0145`), and `logical_loc` (`+0.0141`).
- **Brier Score vs. Calibration:** Uncalibrated regularized ensembles achieved lower Brier error (`0.2055` RF, `0.2062` ET) than `CalibratedClassifierCV` (`0.2116` sigmoid, `0.2202` isotonic), because fitting calibration parameters across 4 heterogeneous inner repositories distorted fold-boundary probability scales.

---

## 4. Historical External Holdout (`JamesNK/Newtonsoft.Json`, $N=159$)

The independent holdout set was evaluated once on the historical baseline model (`rf_compact_regularized` at $\tau^* = 0.40$) and was **not used** during nested optimization:

| Metric | Historical Baseline (`rf_compact_regularized`, $\tau^* = 0.40$) |
| :--- | :---: |
| Confusion Matrix ($N = 159$) | $TP = 71, TN = 49, FP = 31, FN = 8$ |
| Holdout Recall / Precision | 89.87% / 69.61% |
| Holdout Accuracy / Specificity | 75.47% / 61.25% |
| Holdout F1 Score | 0.7845 |
| Holdout ROC-AUC / Brier Score | 0.8209 / 0.1713 |

*Methodological Constraint:* Because `Newtonsoft.Json` was previously inspected for baseline reporting, the optimized models (`et_nested_opt_v3_depth6_leaf6_log2` and `rf_nested_opt_v3_depth6_leaf8_log2`) were not evaluated on it. A new unseen C# repository is required for external holdout validation of the optimized models.
