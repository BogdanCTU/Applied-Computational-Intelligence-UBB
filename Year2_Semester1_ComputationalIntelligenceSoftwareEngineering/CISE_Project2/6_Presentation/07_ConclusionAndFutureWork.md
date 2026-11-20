# 07 — Conclusions, Limitations & Future Work

---

## 1. Summary of Empirical Findings

1. **Nested Repository-Level Optimization (RQ1 & RQ2):** Under $5 \times 4$ nested `GroupKFold` validation across the 5 repositories in Dataset #2 ($N = 578$), shallow-regularized ensemble models with `max_features='log2'` improved cross-repository generalization over the original baseline (`rf_compact_regularized`):
   - **Optimized Extra Trees (`et_nested_opt_v3_depth6_leaf6_log2`):** Improved outer fold-mean ROC-AUC from `0.7037 ± 0.1292` to **`0.7349 ± 0.0703`** (`+0.0312`, cutting inter-repository standard deviation by 45.6%), nested threshold F1 from `0.7408 ± 0.0760` to **`0.7667 ± 0.0723`**, and pooled OOF F1 from `0.7294` to **`0.7653`** (recall `91.76%`, precision `65.64%`).
   - **Optimized Random Forest (`rf_nested_opt_v3_depth6_leaf8_log2`):** Improved outer fold-mean ROC-AUC to **`0.7216 ± 0.1156`**, outer PR-AUC to **`0.6465 ± 0.1026`**, and achieved the lowest outer Brier score (**`0.2055 ± 0.0374`**).
2. **Feature Collinearity & Signal Concentration (RQ3):** Although 11 feature pairs exceed $|r| \ge 0.85$, retaining all 26 metrics with randomized feature subsampling (`max_features='log2'`) outperformed hard correlation pruning. Out-of-fold permutation importance is led by `parameter_count` (`+0.0802` ROC-AUC drop), `method_length` (`+0.0258`), and `loc` (`+0.0170`).
3. **Historical External Holdout Scope (RQ4):** The baseline model (`rf_compact_regularized` at $\tau^* = 0.40$) achieved F1 `0.7845`, recall `89.87%`, and ROC-AUC `0.8209` on `JamesNK/Newtonsoft.Json` ($N = 159$). Because `Newtonsoft.Json` was previously examined, it was excluded from optimization.

---

## 2. Methodological Limitations & Threats to Validity

| Limitation | Empirical Evidence & Impact |
| :--- | :--- |
| **Repository Count ($G = 5$)** | Dataset #2 spans 5 training repositories, limiting the sample size for outer fold-level hypothesis tests ($p = 0.2143$ paired $t$-test; $p = 0.3125$ Wilcoxon on $K=5$ folds) and destabilizing inner `CalibratedClassifierCV` scaling. |
| **Repository Size Imbalance** | `Humanizr/Humanizer` accounts for `50.35%` ($291/578$) of Dataset #2, whereas `App-vNext/Polly` ($34$) and `FluentValidation` ($28$) together represent `10.72%`. |
| **Semantic Defects in Short Methods** | On Dataset #2 (`et_nested_opt_v3_depth6_leaf6_log2` at $\tau = 0.40$), false negatives ($FN = 23$) average `loc = 7.74` and `cyclomatic_complexity = 1.65`, showing that single-line logic/omission bugs in compact methods are rarely separable from static syntax alone. Conversely, false positives ($FP = 134$) occur in larger utility methods (`loc = 15.10`, `parameter_count = 2.66`). |
| **Candidate-Clean Labeling (OWA)** | Negative instances ($y = 0$) are methods without historical bug-fix blame traces rather than formally verified defect-free methods. |
| **Temporal Asymmetry** | Defect-prone methods are extracted from historical pre-fix BIC revisions, whereas candidate-clean methods are sampled from the stable `HEAD` snapshot. |
| **External Holdout Requirement** | Because `Newtonsoft.Json` was used for historical baseline evaluation, a new unseen C# repository is required for an unbiased external holdout evaluation of `et_nested_opt_v3_depth6_leaf6_log2` and `rf_nested_opt_v3_depth6_leaf8_log2`. |
| **Base-Rate Precision Shift** | Dataset #2 has a `48.27%` defect base rate. In production codebases with a $\sim 5\%$ defect prevalence, a detector with $\sim 90\%$ recall and $\sim 60\%$ specificity acts as a code-review prioritization filter rather than a blocking CI gate. |

---

## 3. Future Work

1. **New External Holdout Repository:** Mine an additional independent C# repository (e.g., `AutoMapper/AutoMapper` or `DapperLib/Dapper`) to conduct a single-shot external evaluation of the nested-optimized models.
2. **Process & Change Metrics:** Combine the 26 static Roslyn AST metrics with historical Git process features (commit churn, author count, file age) to reduce false positives on stable utility methods.
3. **Semantic Code Representations:** Integrate token or AST graph embeddings for short methods (`loc <= 8`) where static complexity counts remain low.
4. **Configurable Binary Threshold in `BugPredictor`:** Expose the decision threshold ($\tau = 0.40$ vs. $\tau = 0.50$) directly in `BugPredictor.predict_from_metrics()` alongside the existing `Low`/`Medium`/`High` risk tier settings.
