# Machine Learning-Based C# Bug Detection Classifier (`v4.0.0`)
## Comprehensive Academic Project Report — CISE Project 2

**Institution:** Babeș-Bolyai University, Faculty of Mathematics and Computer Science  
**Programme:** Applied Computational Intelligence, Master's Degree  
**Course:** Computational Intelligence in Software Engineering (CISE), Project 2  
**Date:** November 25, 2026  

---

## 1. Abstract

This project presents a **Machine Learning-Based C# Bug Detection Classifier** that analyzes complete C# classes, structs, records, and multi-class `.cs` source files statically (without compiling or executing target programs) and classifies each type explicitly as **`BUG`** (`BUG DETECTED`) or **`CLEAN`**. Expanding beyond earlier 5-repository method (`v2.0.0`) and 106-repository risk-scoring (`v3.0.0`) stages, version `4.0.0` constructs a **Top-200 star-ranked empirical C# corpus** (`500` discovered repositories -> `367` eligible candidates -> **`200` processed repositories** ranging from `4,409` to `121,429` stars; `179` documented exclusions; `0` failures) yielding **`9,588` deduplicated class observations** (`4,425` `BUG` = `46.15%`, `5,163` `CLEAN` = `53.85%`) measured by `40` isolated .NET 9.0 Roslyn AST metrics.

Furthermore, SZZ blame mining (`git blame -w -M -C`) is extended to map pre-fix changes to both the enclosing class and enclosing method/line ranges (`7,361` verified historical localization records stored in `class_bug_localizations`), while a **separately validated ML Method Localizer** (`method_localizer_top200_v4.joblib`, `26` method metrics over `67,556` method examples) ranks suspicious methods within `BUG` classes without conflating class-level feature importances with line proof. Under strict zero-leakage repository partitioning (**`160` Development repos / `7,546` classes** vs. **`40` Untouched Holdout repos / `2,042` classes**), a regularized Random Forest (`rf_depth12_leaf4_log2_all40`, inner-CV threshold $\tau = 0.520$) achieves **77.66% Nested CV OOF precision** and **79.47% untouched holdout precision** (**62.02% recall**, **69.67% F1**, **0.8180 ROC-AUC**, **0.8104 PR-AUC**, **15.71% FPR**, **37.98% FNR**), surpassing the `>= 75%` holdout precision target and outperforming `DummyClassifier` (`51.93%` precision, `0.5221` ROC-AUC).

---

## 2. Evolution & Problem Formulation

| Research Stage | Granularity & Framing | Scale | Key Validation Outcome |
|---|---|---|---|
| **v2.0.0** (Baseline) | Single C# method defect propensity (`26` features) | `5` dev + `1` holdout repo (`578 + 159` methods) | `69.61%` precision on single holdout repo (`Newtonsoft.Json`) |
| **v3.0.0** (Class Transformation) | Class/file risk scoring (`40` isolated features) | `106` repos (`5,711` classes: `84` dev / `22` holdout) | `83.43%` holdout precision, `0.8449` ROC-AUC |
| **v4.0.0** (Current Classifier) | Explicit **`BUG` / `CLEAN`** classifier + separate ML Method Localizer + partial-analysis guard | **Top-200 star-ranked repos** (`9,588` classes: `160` dev / `40` holdout) | **`79.47%` holdout precision**, **`62.02%` recall**, `0.8180` ROC-AUC, **`68.64%` Top-3 method localizer hit** |

---

## 3. Top-200 Star-Ranked Repository Discovery & SZZ Localization

1. **Star-Descending Selection (`run_top200_csharp_pipeline.py`):** Paginated `language:csharp fork:false archived:false` sorted by `stars` descending. Audited `500` repositories -> excluded `133` pre-clone (`132` oversized >`120,000` KB, `1` empty/insufficient size) -> queued `367` candidates -> cloned & processed **`200` repositories** (`4,409`–`121,429` stars; `46` post-clone exclusions: `29` no bug fixes, `10` insufficient production `.cs` files, `5` no SZZ traces on production C#, `1` no substantive buggy classes, `1` no clean classes; `0` failures).
2. **SZZ Class + Method + Line Attribution (`label_manager.py`):** Mined `46,053` commits, `405,930` diffs, and `24,166` SZZ traces. Mapped deleted lines in pre-fix commits to enclosing types AND enclosing method bounds via Roslyn `--batch-stdin`, persisting **`7,361` verified historical localization rows** (`class_bug_localizations`) and extracting **`67,556` method observations** (`method_localization_top200_v4.csv`).
3. **Deduplication & Export:** Filtered `9,646` candidates (`41` intra-repo exact, `12` cross-repo exact, `5` repeated structural revisions removed; `0` test files; `1,025` distinct historical revisions kept inside single-repo groups) -> Dataset #3 (`csharp_class_top200_v4`, **`9,588` classes**: `4,425` BUG, `5,163` CLEAN, `65` columns, `0` nulls, SHA-256 `c7ff8436...`).

---

## 4. Feature Sufficiency & Zero-Leakage Experimental Design

- **40 Roslyn Class Metrics Sufficiency (`feature_sufficiency_audit.json`):** All `40` features exhibit nonzero variance and zero missing values; `10` pairs exceed Spearman $|\rho| > 0.90$. Ablating those `10` redundant features (`30`-feature RF) slightly raised holdout precision (`80.83%` vs. `79.47%`) at the expense of Nested CV F1 (`0.7160` vs. `0.7193`) and Holdout F1/Recall (`68.90%` / `60.04%` vs. `69.67%` / `62.02%`); therefore all 40 features were retained.
- **Zero-Leakage Partition:** `160` Development repos (`7,546` classes: `3,414` BUG, `4,132` CLEAN) evaluated via `5×4` Nested `GroupKFold` across 12 configs / 7 ML families, with threshold selection (`select_classifier_threshold()`) strictly on inner CV folds (`τ = 0.520`). Evaluated once on `40` untouched Holdout repos (`2,042` classes: `1,011` BUG, `1,031` CLEAN).
- **Separated ML Method Localizer (`method_localizer_top200_v4.joblib`):** Trained exclusively on `157` matching dev repos (`54,678` methods across `2,670` BUG classes) using the `26` method Roslyn features, evaluated once on the `38` matching holdout repos (`12,878` methods across `778` BUG classes).

---

## 5. Empirical Results

### 5.1 Binary Class Classifier (`40` Untouched Holdout Repos, `2,042` Classes)

| Model Family | Config ID | $\tau_{\text{CV}}$ | OOF Prec / Rec / F1 | Holdout Prec | Holdout Rec | Holdout F1 | ROC-AUC | PR-AUC | FPR / FNR |
|---|---|---:|---|---:|---:|---:|---:|---:|---|
| **Random Forest (Champ)** | `rf_depth12_leaf4_log2_all40` | `0.52` | **77.66%** / **66.99%** / **71.93%** | **79.47%** | **62.02%** | **69.67%** | 0.8180 | **0.8104** | 15.71% / **37.98%** |
| Random Forest (Pruned 30) | `rf_depth12_leaf4_corr_pruned` | `0.54` | 77.96% / 66.20% / 71.60% | 80.83% | 60.04% | 68.90% | 0.8186 | 0.8074 | 13.97% / 39.96% |
| Calibrated Ensemble | `calibrated_rf_sigmoid` | `0.54` | 77.77% / 66.49% / 71.69% | 81.05% | 59.64% | 68.72% | 0.8182 | 0.8099 | 13.68% / 40.36% |
| HistGradientBoosting | `hgb_depth5_leaf20_l2_2` | `0.58` | 77.90% / 64.41% / 70.51% | 81.84% | 58.85% | 68.47% | **0.8202** | 0.8078 | 12.80% / 41.15% |
| Extra Trees | `et_depth12_leaf4_log2_bal` | `0.54` | **78.24%** / 64.24% / 70.55% | 79.17% | 56.78% | 66.13% | 0.8103 | 0.8014 | 14.65% / 43.22% |
| Logistic Regression | `lr_std_l2_c01_bal` | `0.56` | **78.24%** / 62.57% / 69.53% | **81.89%** | 54.10% | 65.16% | 0.8041 | 0.7972 | **11.74%** / 45.90% |
| Decision Tree | `dt_depth6_leaf12_bal` | `0.64` | 78.23% / 60.31% / 68.11% | 81.56% | 56.87% | 67.02% | 0.7951 | 0.7747 | 12.61% / 43.13% |
| `DummyClassifier` | `dummy_stratified` | `0.30` | 45.57% / 46.10% / 45.84% | 51.93% | 47.97% | 49.87% | 0.5221 | 0.5067 | 43.55% / 52.03% |

Holdout Confusion Matrix for Champion (`rf_depth12_leaf4_log2_all40`): `TN = 869`, `FP = 162`, `FN = 384`, `TP = 627` (`Brier = 0.1763`).

### 5.2 Method Localizer Holdout (`38` Repos, `778` BUG Classes, `12,878` Methods)
At CV threshold $\tau = 0.600$: **Top-1 Class Hit = `44.99%`**, **Top-3 Class Hit = `68.64%`**, Method **ROC-AUC = `0.6611`**, **PR-AUC = `0.1906`**, **Precision = `22.46%`**, **Recall = `28.31%`**, **F1 = `25.05%`**, **FPR = `11.17%`**, **FNR = `71.69%`** (`CM = [[10266, 1291], [947, 374]]`). Because exact buggy line coordinates cannot be reliably inferred statically from AST counters alone, exact line localization is reported **only** for verified SZZ historical matches and marked **`unavailable`** on unseen code.

---

## 6. Refactored Streamlit Application & Partial-Analysis Safety

The updated Streamlit UI (`2_SourceCode/Python/application/pages/bug_prediction.py` and `app.py`) renders **`BUG DETECTED`** (`st.error`) or **`CLEAN`** (`st.success`) as the primary verdict, relegates probability/confidence to secondary display, presents individual class verdicts plus overall counts for multi-class `.cs` files, strictly separates verified SZZ evidence from ML-estimated suspicious methods, and flags syntax-broken or incomplete files as **`ANALYSIS INCOMPLETE`** (never `CLEAN`).

---

## 7. Threats to Validity & Conclusions

Primary threats include Open-World negative labels (`HEAD` files without observed fixes), SZZ tangled-commit noise, structural blind spots on concise semantic bugs (`37.98%` FNR), base-rate precision decay under low real-world defect prevalence (`17.20%` PPV at `5%` prevalence; `30.49%` at `10%`), and the unavailability of exact line localization on unseen code. Despite these boundaries, scaling to **200 star-ranked C# repositories (`9,588` classes)** delivers an honest, leak-free static bug detection classifier achieving **`79.47%` untouched holdout precision** (`0.8180` ROC-AUC) alongside provenance-transparent method localization.
