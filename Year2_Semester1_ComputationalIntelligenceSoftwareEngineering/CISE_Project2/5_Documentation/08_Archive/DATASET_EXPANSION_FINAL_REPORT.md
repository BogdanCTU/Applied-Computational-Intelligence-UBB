# Final Dataset Expansion Report: Multi-Repository Empirical Corpus

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Babeș-Bolyai University, Faculty of Mathematics and Computer Science  
**Master's Programme:** Applied Computational Intelligence  
**Author / Auditor:** Autonomous Senior ML4SE Specialist  
**Date:** November 2026  
**Artifact:** `reports/dataset_expansion/dataset_expansion_summary.json`  

---

## 1. Executive Summary

This report documents the execution and empirical validation of **Phase 2: Controlled Dataset Expansion**. To transition the project from a preliminary 2-repository training corpus to a genuine multi-repository benchmark capable of supporting 5-fold repository-aware cross-validation ($N_{\text{repos}}=5$, $K=5$), two additional production C# open-source repositories were ingested: `serilog/serilog` and `App-vNext/Polly`. 

These repositories were combined with historical production training repositories (`Humanizer`, `MediatR`) and the corrected pilot repository (`FluentValidation`) to synthesize **Dataset Snapshot #2** (`csharp_empirical_v2`, version `2.0.0`), containing **578 production method observations** across 5 distinct repository domains. Throughout this expansion, Dataset Snapshot #1 (`csharp_empirical_v1`, 483 observations) remained strictly intact, and the final evaluation holdout candidate (`JamesNK/Newtonsoft.Json`) remained completely un-cloned, un-inspected, and quarantined.

---

## 2. Ingestion & Mining Pipeline Execution

The standardized mining pipeline was executed across the two candidate repositories with an extraction ceiling of 350 commits each:

### 2.1 Summary of Collection Metrics

| Repository | Domain / Purpose | Commits Mined | Bug-Fixing Commits ($\tau \ge 0.50$) | SZZ Line Traces | Unique BICs | Usable Buggy Methods | Usable Clean Methods | Yield (Methods) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `serilog/serilog` | Structured Logging Framework | 350 | 23 | 147 | 57 | 66 | 68 | 134 |
| `App-vNext/Polly` | Resilience & Fault-Handling | 350 | 18 | 48 | 16 | 17 | 17 | 34 |

### 2.2 SZZ Tracing & Production-Only Path Enforcement

Both repositories were processed through the enhanced SZZ line-blame tracing algorithm with strict path filtering via `src/utils/source_classifier.py`:
1. **Parent-State Checkout:** For each bug-fixing commit, modified and deleted lines were blamed on the immediate mainline parent commit ($P_0$) using whitespace- and comment-insensitive blame (`git blame -w -M -C`).
2. **Production-Path Guard:** All test directories (`test/`, `tests/`, `specs/`, `testing/`) and test project conventions (e.g. `Serilog.Tests`, `Polly.Specs`) were excluded prior to line blame and method extraction. Zero test methods leaked into the observation pool.
3. **Roslyn Method Resolution:** Deleted lines within production `.cs` files were mapped to concrete syntax nodes using Roslyn's `CSharpSyntaxTree`. Lines occurring outside method declarations (e.g. using directives, property signatures, enum declarations) were cleanly rejected.
4. **Candidate-Clean Sampling:** Stable methods at repository `HEAD` were sampled at a 1:1 ratio matching the SZZ-derived buggy methods, excluding any signature appearing in the historical bug-inducing pool.

---

## 3. Dataset Snapshot #2 Composition & Characteristics

Dataset Snapshot #2 was formally snapshotted in SQLite (ID #2) and exported to `data/processed/csharp_empirical_v2_v2.0.0.csv`.

### 3.1 Repository Distribution in Dataset Snapshot #2

| Repository Identifier | Full Name | Buggy (Label 1) | Clean (Label 0) | Total Observations | % of Dataset |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Repo #4** | `Humanizr/Humanizer` | 139 | 152 | 291 | 50.35% |
| **Repo #15** | `serilog/serilog` | 66 | 68 | 134 | 23.18% |
| **Repo #3** | `LuckyPennySoftware/MediatR` | 43 | 48 | 91 | 15.74% |
| **Repo #16** | `App-vNext/Polly` | 17 | 17 | 34 | 5.88% |
| **Repo #14** | `FluentValidation/FluentValidation` | 14 | 14 | 28 | 4.84% |
| **Total** | **5 Repositories** | **279 (48.27%)** | **299 (51.73%)** | **578 (100.0%)** | **100.0%** |

### 3.2 Feature Completeness & Quality Integrity

- **Feature Count:** 26 Roslyn static code metrics (Lines of Code, Logical LOC, Parameter Count, Statement Count, Cyclomatic Complexity, Max Nesting Depth, Boolean/Logical/Conditional Operator Counts, Control Flow Branching, Exception Handling, Object Creation, Modifiers).
- **Missing Values:** Exactly **0 missing values** across all 26 numerical features across all 578 observations.
- **Deduplication:** 11 duplicate method signatures across repeated commit revisions were filtered out.
- **Test File Leakage:** **0 test files detected**; 100% of observations belong to verifiable production source code.

---

## 4. Preservation of Invariants & Experimental Rigor

### 4.1 Strict Preservation of Historical Dataset Snapshot #1
Dataset Snapshot #1 was verified in the SQLite database and exported to `data/processed/csharp_empirical_v1_v1.0.0.csv`.
- Historical Observations: **483 total** (226 positive, 257 candidate-clean).
- Repositories: `CommandLineParser` (101), `Humanizer` (291), `MediatR` (91).
- Database Verification: Pre-expansion and post-expansion counts match with zero bit drift.

### 4.2 Quarantine of Independent Holdout (`Newtonsoft.Json`)
To prevent data snooping, hyperparameter leakage, and threshold overfitting:
- `JamesNK/Newtonsoft.Json` has not been cloned to disk.
- Zero records exist in the SQLite database for `Newtonsoft.Json`.
- The holdout repository will only be ingested in Phase 4 after all model architectures, preprocessing transformers, and classification thresholds are completely frozen during Phase 3.

---

## 5. Readiness for Phase 3: 5-Fold GroupKFold Cross-Validation

With exactly 5 distinct, well-characterized C# open-source repositories present in Dataset Snapshot #2, the prerequisite for **5-fold repository-aware cross-validation** ($N_{\text{repos}}=5$, $K=5$) is fully met. Each fold will leave out one entire repository during training and evaluate strictly on unseen project code.

