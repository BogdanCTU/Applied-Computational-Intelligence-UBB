# Machine-Learning Methodology and Training Guide

## 1. Primary Classifier & Experimental Design

The primary model is `scikit-learn` `RandomForestClassifier` trained on method-level source-code representations rather than repository statistics or SZZ metrics. Nine controlled configurations (`A`–`I`) isolate each feature group and cumulative combinations:

| Experiment | Feature Groups |
| --- | --- |
| `A` | Traditional structural metrics (comparison baseline) |
| `B` | Lexical features (Roslyn token stats + token n-gram TF-IDF + API call TF-IDF) |
| `C` | AST features (49 Roslyn syntax node counts & densities) |
| `D` | Control-flow features (21 branch/loop/exception/CFG metrics) |
| `E` | Data-flow features (30 DFG, nullability, and resource-lifecycle metrics) |
| `F` | Lexical + AST |
| `G` | Lexical + AST + Control-Flow |
| `H` | Lexical + AST + Control-Flow + Data-Flow |
| `I` | All source-code features + structural metrics |

Secondary baselines (`ExtraTreesClassifier`, `HistGradientBoostingClassifier`, `LogisticRegression`) are evaluated on the champion feature set for comparison without replacing Random Forest as the primary model.

## 2. Leakage-Free Repository-Grouped Validation

- **Hard-Negative Holdout (`hard_negative_test`):** Dedicated disjoint repositories of complex, unit-test-backed correct methods excluded from all training/tuning.
- **Independent Test Set (`independent_test`):** ~22% of remaining repositories (stratified across InferredBugs, GitHub bug-fixes, and dev hard-negatives) held out before any vocabulary fitting, HPO, calibration, or threshold selection.
- **Development Set (`dev`):** Evaluated via `StratifiedGroupKFold` (`5` outer folds, `3` inner HPO folds) grouped strictly by `repository_id`. TF-IDF vocabularies are fitted independently inside each training fold.
- **Automated Leakage Assertions (`verify_zero_leakage`):** Asserts `0` shared `repository_id`s, `0` split `pair_id`s, and `0` shared `source_hash`es across `dev`, `independent_test`, and `hard_negative_test`.

## 3. Calibration and `BUG` / `CLEAN` / `UNCERTAIN` Decision Rule

1. Inner/outer OOF probabilities compare `none`, `sigmoid`, and `isotonic` calibration by Brier score.
2. `calibrate_three_way_thresholds()` selects `threshold_center` on OOF predictions balancing F1 and Balanced Accuracy with a `specificity >= 0.45` guard (preventing predict-all-`BUG` threshold collapse).
3. `threshold_low < threshold_center < threshold_high` defines the abstention band:
   - `p > threshold_high` -> `BUG`
   - `p < threshold_low` -> `CLEAN` (meaning no defect pattern detected, not a formal proof of correctness)
   - `threshold_low <= p <= threshold_high` -> `UNCERTAIN`
4. Syntax-broken `.cs` files always return `ANALYSIS_ERROR`, never `CLEAN`.
