# Slide 5 — Machine Learning Results (`A`–`I` & Independent Evaluation)

- **Champion:** `RandomForestClassifier` Experiment `I` (`536` features across all 5 groups; `rf_I_v5.0.0_20261126_150933`).
- **Thresholds (OOF-Calibrated):** `threshold_low = 0.440`, `threshold_center = 0.470`, `threshold_high = 0.541`.

| Evaluation Split | Samples (Repos) | Accuracy | Precision | Recall | F1 | Specificity / FPR | ROC-AUC | PR-AUC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dev Nested CV OOF | `3,910` (`488`) | `0.5642` | `0.5085` | `0.6667` | `0.5770` | `0.4818` / `0.5182` | `0.6000` | `0.5287` |
| Independent Test | `1,132` (`137`) | `0.5433` | `0.5028` | `0.6833` | `0.5793` | `0.4239` / `0.5761` | `0.5848` | `0.5586` |
| Hard-Negative Test | `233` (`12`) | `0.8541` | — | — | — | `0.8541` / `0.1459` | — | — |
| Temporal Test | `453` (`14`) | `0.5475` | `0.5473` | `0.4911` | `0.5176` | `0.6026` / `0.3974` | `0.5524` | `0.5365` |

- On `hard_negative_test`, **selective FPR is `0.00%`** (`143` `CLEAN`, `90` `UNCERTAIN`, `0` confident false-positive `BUG`s).
- Structural metrics alone (`A`) achieved only `0.5012` test PR-AUC vs. `0.5586` (`I`).
