# Slide 2 — Problem Statement and Objectives

- **Defect Prediction vs. Bug Detection:** Traditional complexity/churn metrics flag *bug-prone modules*, not *defective method code*.
- **Design Objectives:**
  1. Learn from real defective and fixed C# methods (`InferredBugs` + verified GitHub bug-fix commits + unit-test-backed hard negatives).
  2. Extract lexical, AST, control-flow, data-flow, and supplementary structural features via Roslyn.
  3. Enforce strict repository-level holdout isolation (`0` shared repos, pairs, or normalized hashes).
  4. Provide calibrated `BUG` / `CLEAN` / `UNCERTAIN` decisions and refuse `CLEAN` on syntax-broken code (`ANALYSIS_ERROR`).
