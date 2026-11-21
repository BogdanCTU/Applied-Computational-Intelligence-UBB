# Slide 2 — Problem Statement & Transformation Objectives

## Limitations of Legacy Method-Level v2

- **Narrow Empirical Diversity:** Only `5` training repositories (`578` methods) + `1` holdout (`159` methods).
- **High Structural Noise:** Tiny helper methods (`3–10` LOC) had overlapping metric vectors across buggy and clean methods, capping holdout precision around **`69.61%`** (well below real-world precision needs).
- **Unrealistic Developer Input:** Practitioners review **complete classes and `.cs` source files** (often containing multiple classes/structs/records), not isolated out-of-context methods.

---

## v3.0.0 Transformation Objectives

1. **>= 100 C# Repositories:** Build a resumable, checkpointed collection pipeline (`run_100_repo_class_pipeline.py`) across diverse open-source C# projects -> **Achieved: `106` processed repositories (`5,711` classes)**.
2. **Class & Multi-Class File Granularity:** Extend `.NET 9.0` Roslyn analyzer to extract **40 isolated class metrics** (`schema v3.0.0`) with zero nested-type bleed-over while aggregating multi-class `.cs` files cleanly.
3. **High Precision Target:** Achieve **$\ge 80\%$ preferred precision** ($\ge 75\%$ minimum) with recall $\ge 50\%$ using zero-leakage nested `GroupKFold` and untouched repo holdout validation.
4. **Scientific Epistemology:** Frame predictions strictly as **ML-based static defect indications** under historical SZZ evidence and the Open-World Assumption — never as formal bug proof.

---

*Previous:* [Project Overview](01_ProjectOverview.md) | *Next:* [System Architecture](03_SystemArchitecture.md)
