# Slide 1 — Project Overview: Static Bug Detection in C# (`v3.0.0`)

**Machine Learning-Based Bug Detection in C# Source Code**  
Babeș-Bolyai University — M.Sc. Applied Computational Intelligence  
Course: Computational Intelligence in Software Engineering (CISE), Project 2  

---

## Core Mission & Transformation

- **Goal:** Provide a reproducible static ML risk indicator capable of triaging entire C# classes, structs, records, and `.cs` source files **without executing code**.
- **v2 → v3 Evolution:**
  - **Repository Scale:** `5` training repos $\rightarrow$ **`106` processed public C# repositories** (`300` discovered, `15` documented exclusions, `0` failures).
  - **Granularity:** Isolated methods (`26` features) $\rightarrow$ **C# classes/structs/records (`40` isolated Roslyn metrics `v3.0.0`) + multi-class `.cs` file aggregation**.
  - **Precision Objective:** Exceed `>= 75%` minimum / `>= 80%` preferred precision while maintaining `>= 50%` recall under strict zero-leakage repository grouping.
- **Headline Result (`class_precision_champion_v3` at $\tau = 0.600$):**
  - **82.30% Precision / 61.71% Recall** (`5x4` Nested `GroupKFold` OOF, `84` dev repos)
  - **83.43% Precision / 61.99% Recall / 0.8449 ROC-AUC** (`22`-repo untouched holdout, `981` classes)

---

*Next:* [Problem & Objectives](02_ProblemAndObjectives.md)
