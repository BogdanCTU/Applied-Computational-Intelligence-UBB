# Experimental Results and Limitations — CISE Bug Detector v5.0.0

## 1. Repository-Separated Partitions

Zero overlap across `repository_id`, `pair_id`, and normalized `source_hash` was programmatically asserted (`verify_zero_leakage`).

| Partition | Samples | Repositories | BUG (`1`) | CLEAN (`0`) | Purpose |
| --- | --- | --- | --- | --- | --- |
| `dev` | `3,910` | `488` | `1,743` (`44.58%`) | `2,167` (`55.42%`) | 5-fold outer × 3-fold inner grouped CV, HPO, calibration, threshold tuning |
| `independent_test` | `1,132` | `137` | `521` (`46.02%`) | `611` (`53.98%`) | Strictly untouched repository-separated holdout |
| `hard_negative_test` | `233` | `12` | `0` (`0.00%`) | `233` (`100.00%`) | Dedicated unseen complex test-backed correct methods |
| `temporal_train` / `temporal_test` | `1,315` / `453` | `42` / `14` | — / `224` | — / `229` | Chronological repository-separated evaluation over dated GitHub commits |

## 2. Controlled Feature Experiments (`A`–`I`, Random Forest)

All nine configurations were evaluated using identical `StratifiedGroupKFold` development folds and the untouched `137`-repo independent test set:

| Exp | Feature Groups | Features | Dev CV F1 | Dev CV PR-AUC | Dev CV ROC-AUC | Test Acc | Test Prec | Test Rec | Test F1 | Test Spec | Test FPR | Test ROC-AUC | Test PR-AUC | Test Brier | Uncert. Rate | Sel. F1 | HN FPR | HN Uncert. | HN Sel. FPR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `A` | `structural` | `16` | `0.5409` | `0.4995` | `0.5669` | `0.5194` | `0.4823` | `0.6027` | `0.5358` | `0.4484` | `0.5516` | `0.5439` | `0.5012` | `0.2527` | `21.91%` | `0.5417` | `24.46%` | `23.18%` | `18.99%` |
| `B` | `lexical` | `420` | `0.5621` | `0.5183` | `0.5804` | `0.5468` | `0.5055` | `0.7044` | `0.5886` | `0.4124` | `0.5876` | `0.5765` | `0.5438` | `0.2432` | `29.51%` | `0.6076` | `30.90%` | `39.91%` | `25.71%` |
| `C` | `ast` | `49` | `0.5700` | `0.5233` | `0.5897` | `0.5654` | `0.5210` | `0.6891` | `0.5934` | `0.4599` | `0.5401` | `0.5916` | `0.5343` | `0.2442` | `23.94%` | `0.6171` | `31.33%` | `24.89%` | `26.29%` |
| `D` | `control_flow` | `21` | `0.5526` | `0.4993` | `0.5704` | `0.5380` | `0.4985` | `0.6219` | `0.5534` | `0.4664` | `0.5336` | `0.5664` | `0.5057` | `0.2495` | `16.96%` | `0.5685` | `24.03%` | `21.89%` | `17.03%` |
| `E` | `data_flow` | `30` | `0.5708` | `0.5187` | `0.5849` | `0.5415` | `0.5015` | `0.6545` | `0.5679` | `0.4452` | `0.5548` | `0.5729` | `0.5324` | `0.2454` | `28.36%` | `0.5860` | `39.06%` | `27.47%` | `36.09%` |
| `F` | `lexical+ast` | `469` | `0.5677` | `0.5214` | `0.5879` | `0.5521` | `0.5098` | `0.6967` | `0.5888` | `0.4288` | `0.5712` | `0.5833` | `0.5428` | `0.2429` | `29.06%` | `0.6115` | `24.46%` | `33.91%` | `18.83%` |
| `G` | `lexical+ast+cfg` | `490` | `0.5653` | `0.5240` | `0.5903` | `0.5468` | `0.5057` | `0.6814` | `0.5805` | `0.4321` | `0.5679` | `0.5841` | `0.5447` | `0.2429` | `36.13%` | `0.6127` | `21.89%` | `33.05%` | `9.62%` |
| `H` | `lex+ast+cfg+dfg` | `520` | `0.5752` | `0.5271` | `0.5950` | `0.5459` | `0.5051` | `0.6718` | `0.5766` | `0.4386` | `0.5614` | **`0.5944`** | `0.5583` | **`0.2409`** | `28.53%` | **`0.6247`** | `29.18%` | `32.62%` | `21.02%` |
| `I` | `all 5 groups` | `536` | **`0.5770`** | **`0.5287`** | **`0.6000`** | `0.5433` | `0.5028` | `0.6833` | `0.5793` | `0.4239` | `0.5761` | `0.5848` | **`0.5586`** | `0.2432` | `48.85%` | `0.5838` | **`14.59%`** | `38.63%` | **`0.00%`** |

### Key Takeaways from `A`–`I`
- **Source-code representations beat traditional structural metrics (`A`):** Structural-only (`A`) achieved `0.5012` test PR-AUC (near the `0.4602` random baseline) and `0.5439` ROC-AUC, whereas combining lexical + AST + CFG + DFG (`H`/`I`) improved test PR-AUC to `0.5583`–`0.5586` (+`0.0574`) and ROC-AUC to `0.5944` (`H`) / `0.6000` (CV `I`).
- **Strongest single group:** `AST` (`C`, `49` features) achieved `0.5916` ROC-AUC and `0.5934` F1 on independent test, while `Lexical` (`B`) delivered the largest PR-AUC (`0.5438`).
- **Hard-Negative Behavior:** Experiment `I` achieved the lowest binary Hard-Negative FPR (`14.59%`, `85.41%` specificity) and **`0.00%` selective FPR** (zero confident false positives out of `233` complex verified-correct methods, with `38.63%` placed in `UNCERTAIN`).

## 3. Leave-One-Group-Out Feature Ablation (from `I`)

| Removed Group | Remaining Groups | CV F1 | CV PR-AUC | Test F1 | Test PR-AUC | Test ROC-AUC | $\Delta$ Test PR-AUC vs `I` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `lexical` | `ast+cfg+dfg+struct` | `0.5841` | `0.5265` | `0.5783` | `0.5385` | `0.5864` | **`-0.0201`** |
| `ast` | `lex+cfg+dfg+struct` | `0.5618` | `0.5258` | `0.5787` | `0.5462` | `0.5801` | **`-0.0124`** |
| `control_flow` | `lex+ast+dfg+struct` | `0.5716` | `0.5270` | `0.5876` | `0.5564` | `0.5859` | `-0.0022` |
| `structural` | `lex+ast+cfg+dfg` | `0.5671` | `0.5239` | `0.5941` | `0.5574` | `0.5952` | `-0.0012` |
| `data_flow` | `lex+ast+cfg+struct` | `0.5695` | `0.5220` | `0.5882` | `0.5578` | `0.5890` | `-0.0008` |

Removing `lexical` (`-0.0201` PR-AUC) and `ast` (`-0.0124` PR-AUC) caused the largest independent test degradation.

## 4. Secondary Baseline Comparison (Experiment `I` Features, Independent Test)

| Algorithm | Accuracy | Precision | Recall | F1 | Specificity | FPR | ROC-AUC | PR-AUC | Brier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `RandomForestClassifier` (Primary, calibrated thresholds) | `0.5433` | `0.5028` | `0.6833` | **`0.5793`** | `0.4239` | `0.5761` | `0.5848` | `0.5586` | `0.2432` |
| `ExtraTreesClassifier` (`t=0.50`) | **`0.5751`** | **`0.5467`** | `0.4491` | `0.4932` | `0.6825` | `0.3175` | **`0.5969`** | **`0.5712`** | **`0.2401`** |
| `HistGradientBoostingClassifier` (`t=0.50`) | `0.5521` | `0.5180` | `0.3858` | `0.4422` | **`0.6939`** | **`0.3061`** | `0.5676` | `0.5431` | `0.2519` |
| `LogisticRegression` (`t=0.50`) | `0.5477` | `0.5079` | `0.5547` | `0.5303` | `0.5417` | `0.4583` | `0.5675` | `0.5212` | `0.2547` |

## 5. Champion Model Evaluation (`rf_I_v5.0.0_20261126_150933`)

Calibrated thresholds (derived strictly from `dev` OOF predictions): `threshold_low = 0.440`, `threshold_center = 0.470`, `threshold_high = 0.541`.

### Independent Test Confusion Matrix (`1,132` samples)
- `TN = 259`, `FP = 352`, `FN = 165`, `TP = 356`
- 3-Way Distribution: `309` `BUG`, `270` `CLEAN`, `553` `UNCERTAIN` (`48.85%`), Selective Precision `0.5469`, Selective Recall `0.6259`, Selective F1 `0.5838`.

### Breakdown by Data Source (Independent Test & Hard-Negative Holdout)

| Subset | Samples | Repos | Accuracy / Recall / Spec | FPR | Uncert. Rate | Sel. FPR |
| --- | --- | --- | --- | --- | --- | --- |
| `inferredbugs_infersharp` (BUG) | `315` | `117` | Recall `81.90%` (`258/315`) | — | `50.16%` | — |
| `inferredbugs_post_fix` (CLEAN) | `317` | `117` | Spec `22.08%` (`70/317`) | `77.92%` | `52.68%` | `78.00%` |
| `github_bugfix_commit` (BUG) | `206` | `12` | Recall `47.57%` (`98/206`) | — | `45.15%` | — |
| `github_post_fix` (CLEAN) | `210` | `12` | Spec `54.29%` (`114/210`) | `45.71%` | `53.33%` | `23.47%` |
| `verified_hard_negative` (in test) | `84` | `7` | Spec `89.29%` (`75/84`) | `10.71%` | `27.38%` | `0.00%` |
| `hard_negative_test` (dedicated) | `233` | `12` | Spec `85.41%` (`199/233`) | `14.59%` | `38.63%` | **`0.00%`** |
| `temporal_test` (latest repos) | `453` | `14` | Acc `54.75%`, F1 `51.76%`, ROC-AUC `0.5524` | `39.74%` | `49.01%` | `46.09%` |

## 6. False Positive & False Negative Analysis (`error_analysis.json`)

- **Why `inferredbugs_post_fix` FPR is high (`77.92%`, `352` total test FPs):**
  1. **Near-twin fixed methods:** In InferredBugs, post-fix methods (`ib_Facepunch.Steamworks_1_fix`, `ib_Hangfire_14_fix`, `ib_Tommy_1_fix`) share ~90–95% of lexical tokens and AST counts with their buggy pre-fix versions (`p = 0.654`), often differing only in a downstream caller or a single guard.
  2. **Subdirectory unit-test naming:** Paths containing `.UnitTests/` or `.Tests/` (e.g., `RPGCore.Demo.BoardGame.UnitTests`, `Fleck.Tests`) slipped past directory-boundary regex filtering during InferredBugs ingestion (`p = 0.635–0.661`).
- **Why semantic logic bugs cause False Negatives (`165` total test FNs):**
  - Subtle domain/logic bugs in GitHub commits (`FluentValidation/NotEmptyValidator.IsValid`, `MessagePack-CSharp/AnalyzerUtilities`, `Dapper/DefaultTypeMap.MatchFirstOrDefault`) already exhibit defensive null checks and clean control flow (`p = 0.226–0.341`), so method-level static syntax/DFG counts alone cannot detect incorrect business invariants without specification or test oracle context.

## 7. Honest Limitations & Future Work

1. **Modest Discriminative Ceiling (`0.585–0.597` ROC-AUC):** Distinguishing a buggy method from its own 1-line patched post-fix twin using aggregate syntax/token counts is fundamentally harder than distinguishing whole files or cross-project risk; results honestly reflect this ceiling and route `48.85%` of ambiguous cases to `UNCERTAIN`.
2. **Partial Compilation Context:** Analyzing isolated `.cs` files without project `.csproj` / NuGet assemblies leaves external library symbols unresolved in `SemanticModel`.
3. **Future Work:** Graph/AST sequence embeddings (CodeBERT / GraphCodeBERT or tree-edit AST paths), full MSBuild/`.csproj` solution loading for inter-procedural Roslyn semantic analysis, and stricter `.Tests.` substring filtering during InferredBugs ingestion.
