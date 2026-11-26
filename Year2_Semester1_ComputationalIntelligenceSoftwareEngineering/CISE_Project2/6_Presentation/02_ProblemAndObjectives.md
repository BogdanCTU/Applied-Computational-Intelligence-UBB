# Slide 2 — Problem Statement & Scope Correction (`v4.0.0`)

## From Risk-Scoring to Explicit Bug Detection Classification

- **Clear Developer Decision:** Practitioners need explicit **`BUG` / `CLEAN`** verdicts at class and `.cs` file level rather than uncalibrated Low/Medium/High risk dashboards.
- **Top-200 Star-Ranked Benchmark:** Replacing smaller/stratified subsets with the **Top 200 public C# repositories ranked by GitHub stars descending** evaluates generalization across major production C# systems (`2dust/v2rayN` down to `tmenier/Flurl`).
- **Honest Localization Distinction:**
  - **Verified Historical SZZ Evidence:** Map pre-fix bug-fix diffs to enclosing class, method, and line ranges when matched historically in SQLite (`class_bug_localizations`).
  - **ML-Estimated Suspicious Methods:** Train a **separate** method localizer (`method_localizer_top200_v4.joblib`) on method metrics rather than misrepresenting class feature importances as line proof.
  - **Unavailable Exact Lines on Unseen Code:** Explicitly report exact buggy line ranges as **`unavailable`** when no historical SZZ match exists.
- **Safety Guarantee:** Never classify a multi-class `.cs` file as `CLEAN` when syntax errors or per-class extraction failures occur (`ANALYSIS INCOMPLETE`).

---

*Previous:* [Project Overview](01_ProjectOverview.md) | *Next:* [System Architecture](03_SystemArchitecture.md)
