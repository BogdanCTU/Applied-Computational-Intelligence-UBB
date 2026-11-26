# Slide 6 — Refactored Bug Detection GUI & Provenance Display

## Primary `BUG DETECTED` / `CLEAN` Experience (`2_SourceCode/Python/application/pages/bug_prediction.py`)

All `8` Streamlit pages share `ModelManager.list_saved_models()` with `class_bug_classifier_top200_v4` ($\tau = 0.520$) selected first:

1. **Clear Binary Primary Verdict (`format_class_verdict`, `format_file_verdict`):**
   - Displays **`BUG DETECTED`** (`st.error`) or **`CLEAN`** (`st.success`), with probability and model confidence placed secondary.
2. **Multi-Class `.cs` Files & Partial-Analysis Safety (`predict_csharp_file`):**
   - Evaluates each extracted `class`/`struct`/`record` independently, summarizes **`BUG`**, **`CLEAN`**, and **Failed/Syntax Error** counts, and displays **`ANALYSIS INCOMPLETE`** (`st.warning`) rather than `CLEAN` whenever any syntax error or failed class exists.
3. **Strictly Provenance-Separated Bug Localization:**
   - **Verified Historical SZZ Evidence:** Displayed ONLY on historical SQLite matches (`class_bug_localizations`), showing exact commit SHAs, affected methods, and line ranges.
   - **ML-Estimated Suspicious Methods:** On unseen `BUG` classes, `method_localizer_top200_v4.joblib` ranks suspicious methods, while exact buggy lines are explicitly marked **`unavailable`**.

---

*Previous:* [Machine Learning Results](05_MachineLearningResults.md) | *Next:* [Conclusion & Future Work](07_ConclusionAndFutureWork.md)
