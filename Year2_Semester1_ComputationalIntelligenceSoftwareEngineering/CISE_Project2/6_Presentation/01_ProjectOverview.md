# Slide 1 — Project Overview: C# Bug Detection Classifier (`v4.0.0`)

**Machine Learning-Based C# Bug Detection Classifier**  
Babeș-Bolyai University — M.Sc. Applied Computational Intelligence  
Course: Computational Intelligence in Software Engineering (CISE), Project 2  

---

## Core Mission & Transformation

- **Goal:** Provide a reproducible static classifier outputting explicit **`BUG`** (`BUG DETECTED`) vs. **`CLEAN`** verdicts for C# classes and multi-class `.cs` files **without executing code**.
- **v2 -> v3 -> v4 Evolution:**
  - **Repository Scale:** `5` -> `106` -> **Top `200` star-ranked public C# repositories** (`500` discovered, `367` eligible candidates, `179` documented exclusions, `0` failures; `4,409` to `121,429` stars).
  - **Dataset Size (`csharp_class_top200_v4`):** **`9,588` classes** (**`4,425` BUG** = `46.15%`, **`5,163` CLEAN** = `53.85%`), `40` isolated Roslyn metrics (`0` nulls), plus **`7,361` verified SZZ historical localization rows** and **`67,556` method localization rows**.
  - **Holdout Objective:** Achieve `>= 75%` precision on an untouched repository-level holdout (`40` repos, `2,042` classes) with balanced recall and zero data leakage.
- **Champion Holdout Result (`class_bug_classifier_top200_v4` at $\tau = 0.520$):**
  - **Precision: `79.47%`** | **Recall: `62.02%`** | **F1: `69.67%`** | **ROC-AUC: `0.8180`** | **PR-AUC: `0.8104`** | **FPR: `15.71%`** | **FNR: `37.98%`**

---

*Next:* [Problem & Objectives](02_ProblemAndObjectives.md)
