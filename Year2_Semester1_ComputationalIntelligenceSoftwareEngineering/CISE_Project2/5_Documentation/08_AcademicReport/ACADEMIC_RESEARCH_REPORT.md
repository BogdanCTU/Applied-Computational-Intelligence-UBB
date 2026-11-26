# Academic Research Report — Machine Learning-Based C# Source-Code Bug Detection (`v5.0.0`)

**Institution:** Babeș-Bolyai University — Computational Intelligence in Software Engineering (CISE)  
**System Version:** `5.0.0` (Complete Redesign)

---

## Abstract

We present the design, implementation, and repository-isolated evaluation of a machine-learning C# source-code bug detection system (`v5.0.0`) that classifies individual C# methods into `BUG`, `CLEAN`, or `UNCERTAIN`. Moving away from traditional project-level defect-proneness metrics and SZZ heuristics, we construct a validated corpus of `5,275` C# methods (`2,264` `BUG`, `3,011` `CLEAN`) across `637` distinct repositories by combining Microsoft's `InferredBugs` (`InferSharp`) dataset, focused GitHub bug-fix commits, and unit-test-backed complex hard negatives after excluding `6,755` invalid, noisy, or conflicting records. Using a `.NET 9.0` Roslyn preprocessor (`RoslynPreprocessor`), we extract lexical token/API n-grams, AST structures, control-flow features, data-flow/nullability/resource features, and supplementary structural metrics (`536` features total). On a strictly unseen `137`-repository holdout (`1,132` methods), `RandomForestClassifier` (Experiment `I`) achieves `0.5586` PR-AUC and `0.5848` ROC-AUC (vs. `0.5012` PR-AUC for structural metrics alone), while achieving `85.41%` binary specificity and `0.00%` confident false-positive rate (`38.63%` `UNCERTAIN`) on a dedicated `233`-method hard-negative benchmark across `12` unseen repositories.

## 1. Introduction & Problem Statement

Traditional software defect prediction relies on file/class size, complexity, and repository churn—correlating with *where* bugs accumulate rather than *whether a method's source code contains a defect pattern*. This work addresses method-level source-code bug detection for C# using real defective and fixed source examples, explicit verification provenance, and calibrated three-way (`BUG` / `CLEAN` / `UNCERTAIN`) predictions.

## 2. Dataset Construction & Validation

- **InferredBugs (`inferredbugs/csharp`):** Inspected all `2,891` bug directories (`641` repos); filtered delegation-stub refactors, test/generated files, normalization-identical pairs, and cross-label hash collisions to retain `1,383` `BUG` (`static_analyzer_verified_fix`) and `1,368` `CLEAN` (`post_fix_verified`) across `536` repos.
- **GitHub Bug-Fix Commits:** Mined `60` cloned repositories (`400` commits/repo) with strict commit-message and focused-diff filtering (`<= 3` `.cs` files, `<= 2` changed methods/file), retaining `881` `BUG` (`commit_verified_bugfix`) and `887` `CLEAN` (`post_fix_verified`) across `56` repos.
- **Verified Hard Negatives:** Collected `756` complex (`cyclomatic_complexity >= 4`, `logical_loc >= 12`) unit-test-referenced, clean-history methods across `45` disjoint repos (`233` across `12` repos strictly isolated as `hard_negative_test`).

## 3. Methodology: Roslyn Preprocessing & Feature Groups

Five independent extractors map Roslyn-parsed methods to `536` features:
1. **Lexical (`420`):** `20` token/operator/null-literal ratios + `300` token 1–2 gram TF-IDF + `100` API invocation TF-IDF.
2. **AST (`49`):** Expression/statement frequencies, null syntax (`?.`, `??`, `is null`), casts, LINQ, exceptions.
3. **Control-Flow (`21`):** Branch/loop/nesting/early-return/empty-catch/unreachable-code counts + `AnalyzeControlFlow`.
4. **Data-Flow (`30`):** `AnalyzeDataFlow` counts, parameter null-check coverage, unchecked nullable dereferences, undisposed `IDisposable` allocations, and explicit `semantic_model_available` / `dfg_unresolved_symbol_ratio`.
5. **Structural (`16`):** Cyclomatic complexity, LOC, parameter count, modifiers (comparison baseline).

## 4. Experimental Evaluation

Evaluated with `5×3` repository-grouped `StratifiedGroupKFold` (`3,910` dev samples / `488` repos) and tested on untouched `independent_test` (`1,132` / `137` repos), `hard_negative_test` (`233` / `12` repos), and `temporal_test` (`453` / `14` repos):
- **A–I Comparison:** Source-code features (`H`: `0.5944` ROC-AUC, `0.5583` PR-AUC; `I`: `0.5848` ROC-AUC, `0.5586` PR-AUC) consistently outperform structural metrics (`A`: `0.5439` ROC-AUC, `0.5012` PR-AUC).
- **Ablation:** Removing `lexical` (`-0.0201` PR-AUC) and `ast` (`-0.0124` PR-AUC) causes the largest drop.
- **Hard Negatives & Uncertainty:** With OOF-calibrated thresholds (`0.440 / 0.470 / 0.541`), `RandomForestClassifier` achieves `85.41%` specificity on complex correct methods and `0.00%` confident false positives (`90` marked `UNCERTAIN`, `143` marked `CLEAN`).
- **Secondary Baselines:** `ExtraTreesClassifier` reaches `0.5969` ROC-AUC and `0.5712` PR-AUC at `t=0.50`, confirming consistent signal across tree ensembles while Random Forest remains primary.

## 5. Threats to Validity & Limitations

- **Internal Validity:** Before/after pairs differ by small localized edits; aggregate feature counts limit separation between a buggy method and its own post-fix twin (`77.92%` FPR on `inferredbugs_post_fix` vs. `14.59%` FPR on `hard_negative_test`).
- **Construct Validity:** Missing project-level `.csproj` dependencies restrict cross-assembly Roslyn semantic resolution.
- **Ethical / Practical Interpretation:** `CLEAN` indicates no defect pattern detected above threshold; it never guarantees bug-free correctness.
