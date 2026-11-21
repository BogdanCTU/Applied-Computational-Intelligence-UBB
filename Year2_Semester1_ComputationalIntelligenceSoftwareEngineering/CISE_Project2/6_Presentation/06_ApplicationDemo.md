# Slide 6 — Streamlit Class & File Bug Detection Application

## Multi-Granularity User Workflow (`2_SourceCode/Python/app.py`)

All `8` Streamlit pages read from the unified `ModelManager.list_saved_models()` registry (`class_precision_champion_v3` defaulted at top, with stored threshold `tau = 0.600`).

1. **Input A — Single C# Class / Struct / Record Paste (`predict_class_code`):**
   - Parses snippet with Roslyn `v3.0.0`, isolates target type (`40` metrics), computes `predict_proba()[:, 1]`, and flags defect propensity at $\ge \tau$ alongside top influential metrics and internal methods.
2. **Input B — Full `.cs` Source File Upload (`predict_csharp_file`):**
   - Independently extracts and predicts every non-nested and nested type inside multi-class `.cs` files without collapsing classes together.
   - Displays file-level summary (`classes_analyzed_count`, `classes_flagged_count`, `max_defect_probability`, `mean_class_risk_score`) plus expandable per-class breakdown.
3. **Backward-Compatible Method Diagnostic Mode (`predict_method_code`):**
   - Retained for legacy `26`-metric method inspection when a historical method model bundle is selected.
4. **Repository Telemetry & Evaluation Pages:**
   - Updated `Dashboard`, `Repository Collection`, `Bug Analysis`, `Dataset Management`, `Model Training`, and `Model Evaluation` views backed live by SQLite (`122` repos, `5,711` dataset classes, `3_TestResults/ClassModelOptimization/`).

---

*Previous:* [Machine Learning Results](05_MachineLearningResults.md) | *Next:* [Conclusion & Future Work](07_ConclusionAndFutureWork.md)
