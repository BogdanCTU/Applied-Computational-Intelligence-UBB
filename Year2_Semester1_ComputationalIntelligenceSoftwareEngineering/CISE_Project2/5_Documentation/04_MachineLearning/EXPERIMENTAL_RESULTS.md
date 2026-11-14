# Consolidated Empirical Experimental Results

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University  
**Course:** Computational Intelligence in Software Engineering (CISE) — Project 2  
**Role:** Canonical Experimental Results & Model Evaluation Reference  
**Authoritative Artifacts:**  
- Cross-Validation: `3_TestResults/FinalCrossValidation/experiment_results.json`, `3_TestResults/FinalCrossValidation/experiment_results.csv`  
- Frozen Model: `4_AppBuild/Assets/Models/exp_final_5fold_v2_best_rf_compact_regularized.joblib`  
- Independent Holdout: `3_TestResults/HoldoutValidation/newtonsoft_holdout_results.json`  

---

## 1. Dataset Corpora Overview

| Dataset Snapshot | Semantic Version | Observations | Repositories Included | Defect Labels (Defect-Prone / Candidate-Clean) | Purpose |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Dataset #1** (`csharp_empirical_v1`) | `1.0.0` | 483 | 3 (`Humanizer`, `MediatR`, `commandline`) | 226 / 257 (46.8% defect-prone) | Exploratory baseline & 2-fold prototype |
| **Dataset #2** (`csharp_empirical_v2`) | `2.0.0` | **578** | **5** (`Humanizer`, `Serilog`, `MediatR`, `Polly`, `FluentValidation`) | **279 / 299 (48.3% defect-prone)** | Authoritative 5-fold cross-validation corpus |
| **Independent Holdout** (`newtonsoft_holdout`) | — | **159** | 1 (`JamesNK/Newtonsoft.Json`) | **79 / 80 (49.7% defect-prone)** | One-shot independent generalization test |

### 1.1 Dataset Snapshot #2: Repository Breakdown

| Repository ID | Full Name | Defect-Prone (Label 1) | Candidate-Clean (Label 0) | Total Observations | % of Dataset |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **Repo #4** | `Humanizr/Humanizer` | 139 | 152 | 291 | 50.35% |
| **Repo #15** | `serilog/serilog` | 66 | 68 | 134 | 23.18% |
| **Repo #3** | `LuckyPennySoftware/MediatR` | 43 | 48 | 91 | 15.74% |
| **Repo #16** | `App-vNext/Polly` | 17 | 17 | 34 | 5.88% |
| **Repo #14** | `FluentValidation/FluentValidation` | 14 | 14 | 28 | 4.84% |
| **Total** | **5 Repositories** | **279 (48.27%)** | **299 (51.73%)** | **578** | **100.0%** |

- **Feature Count:** Exactly **26 Roslyn numeric features** extracted per method.
- **Missing Values:** Exactly **0 missing values** across all 578 observations.
- **Production Filtering:** 100% production code verified via `is_production_csharp_file()` (0 test files).

---

## 2. Five-Fold Repository-Aware Cross-Validation Design

Cross-validation uses `GroupKFold` ($K=5$) grouped strictly by `repository_id`. Each fold holds out one entire repository as the validation set, ensuring zero intra-repository leakage ($\text{Train\_Repos} \cap \text{Val\_Repos} = \emptyset$):

| Fold Index | Validation Repository | Val Observations | Train Repositories | Train Observations | Intra-Repo Overlap |
| :---: | :--- | :---: | :--- | :---: | :---: |
| **Fold 1** | `Humanizr/Humanizer` | 291 | Serilog, MediatR, Polly, FluentValidation | 287 | **0 (Zero Leakage)** |
| **Fold 2** | `serilog/serilog` | 134 | Humanizer, MediatR, Polly, FluentValidation | 444 | **0 (Zero Leakage)** |
| **Fold 3** | `LuckyPennySoftware/MediatR` | 91 | Humanizer, Serilog, Polly, FluentValidation | 487 | **0 (Zero Leakage)** |
| **Fold 4** | `App-vNext/Polly` | 34 | Humanizer, Serilog, MediatR, FluentValidation | 544 | **0 (Zero Leakage)** |
| **Fold 5** | `FluentValidation/FluentValidation` | 28 | Humanizer, Serilog, MediatR, Polly | 550 | **0 (Zero Leakage)** |

Total evaluated across all 5 folds: $291 + 134 + 91 + 34 + 28 = 578$. Every repository serves as the validation partition in exactly one fold.

---

## 3. Comprehensive Model Benchmark Results

Eleven configurations across four classifier families were evaluated under identical 5-fold GroupKFold splits at the nominal default decision threshold ($\tau = 0.50$):

| Rank | Configuration ID | Algorithm Family | F1 (Mean ± Std) | Recall (Mean ± Std) | Precision (Mean ± Std) | Accuracy (Mean ± Std) | ROC-AUC | PR-AUC | Brier Score |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | `rf_compact_regularized` | Random Forest | **$0.6859 \pm 0.0247$** | $0.7403 \pm 0.1557$ | $0.6824 \pm 0.1202$ | **$0.6734 \pm 0.0491$** | **0.7025** | **0.6401** | **$0.2144 \pm 0.0396$** |
| 2 | `rf_feature_constrained_log2` | Random Forest | $0.6385 \pm 0.0641$ | $0.6831 \pm 0.1706$ | $0.6384 \pm 0.1197$ | $0.6369 \pm 0.0673$ | 0.6974 | 0.6309 | $0.2209 \pm 0.0375$ |
| 3 | `rf_heavy_bagging_300` | Random Forest | $0.6262 \pm 0.0633$ | $0.6788 \pm 0.1738$ | $0.6117 \pm 0.0984$ | $0.6212 \pm 0.0617$ | 0.6874 | 0.6277 | $0.2265 \pm 0.0376$ |
| 4 | `rf_baseline_balanced` | Random Forest | $0.6108 \pm 0.1176$ | $0.6678 \pm 0.1982$ | $0.6046 \pm 0.1157$ | $0.6074 \pm 0.0827$ | 0.6792 | 0.6200 | $0.2249 \pm 0.0410$ |
| 5 | `dt_shallow_depth4` | Decision Tree | $0.5734 \pm 0.2172$ | $0.6166 \pm 0.2646$ | $0.5573 \pm 0.1884$ | $0.5721 \pm 0.1345$ | 0.5849 | 0.5630 | $0.2807 \pm 0.0699$ |
| 6 | `rf_deep_capacity` | Random Forest | $0.5577 \pm 0.0739$ | $0.5794 \pm 0.1737$ | $0.5811 \pm 0.1147$ | $0.5815 \pm 0.0647$ | 0.6552 | 0.5982 | $0.2429 \pm 0.0435$ |
| 7 | `lr_balanced_c1` | Logistic Regression | $0.4989 \pm 0.1252$ | $0.4538 \pm 0.1469$ | $0.5994 \pm 0.1557$ | $0.5709 \pm 0.0894$ | 0.6225 | 0.5694 | $0.2620 \pm 0.0368$ |
| 8 | `dummy_stratified` | Baseline (Prior) | $0.4919 \pm 0.0821$ | $0.4644 \pm 0.1328$ | $0.5259 \pm 0.0526$ | $0.4984 \pm 0.0592$ | 0.4975 | 0.4815 | $0.4726 \pm 0.0700$ |
| 9 | `lr_standard_c1` | Logistic Regression | $0.4890 \pm 0.1409$ | $0.4360 \pm 0.1651$ | $0.6095 \pm 0.1593$ | $0.5744 \pm 0.0877$ | 0.6231 | 0.5699 | $0.2643 \pm 0.0366$ |
| 10 | `dt_depth8` | Decision Tree | $0.4695 \pm 0.2194$ | $0.4907 \pm 0.2529$ | $0.4844 \pm 0.1983$ | $0.5050 \pm 0.1425$ | 0.5097 | 0.5033 | $0.3993 \pm 0.1017$ |
| 11 | `dummy_most_frequent` | Baseline (Majority) | $0.0000 \pm 0.0000$ | $0.0000 \pm 0.0000$ | $0.0000 \pm 0.0000$ | $0.5173 \pm 0.0210$ | 0.5000 | 0.4827 | $0.4885 \pm 0.0218$ |

### 3.1 Fold-Level Breakdown for Winning Architecture (`rf_compact_regularized`)

| Fold | Held-Out Repository | Val Obs | Fold Confusion Matrix [TN, FP, FN, TP] | Fold Accuracy | Fold Precision | Fold Recall | Fold F1 | ROC-AUC | Brier Score |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | `Humanizr/Humanizer` | 291 | `[115, 37, 49, 90]` | 0.7045 | 0.7087 | 0.6475 | **0.6767** | 0.7972 | 0.1843 |
| **Fold 2** | `serilog/serilog` | 134 | `[15, 53, 2, 64]` | 0.5896 | 0.5470 | 0.9697 | **0.6995** | 0.5865 | 0.2702 |
| **Fold 3** | `LuckyPennySoftware/MediatR` | 91 | `[30, 18, 13, 30]` | 0.6593 | 0.6250 | 0.6977 | **0.6593** | 0.6781 | 0.2210 |
| **Fold 4** | `App-vNext/Polly` | 34 | `[16, 1, 8, 9]` | 0.7353 | 0.9000 | 0.5294 | **0.6667** | 0.8997 | 0.1579 |
| **Fold 5** | `FluentValidation` | 28 | `[7, 7, 2, 12]` | 0.6786 | 0.6316 | 0.8571 | **0.7273** | 0.5510 | 0.2384 |
| **Mean** | **5 Folds** | — | — | **0.6734** | **0.6824** | **0.7403** | **0.6859** | **0.7025** | **0.2144** |
| **Std** | Population ($\text{ddof}=0$) | — | — | $\pm 0.0491$ | $\pm 0.1202$ | $\pm 0.1557$ | $\pm 0.0247$ | $\pm 0.1303$ | $\pm 0.0396$ |

---

## 4. Reconciled Accuracy Metrics: Three Distinct Protocols

The project evaluates accuracy across three distinct dimensions. These figures represent different aggregation protocols and operating thresholds, and are mathematically reconciled below:

| Metric Identifier | Evaluation Protocol | Operating Threshold | Underlying Mathematical Formula | Reported Value | Mathematical Proof |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **5-Fold CV Mean Accuracy** | Unweighted fold-level average across 5 held-out repos | Nominal $\tau = 0.50$ | $\frac{1}{K}\sum_{k=1}^5 \text{Acc}_k$ | **$0.6734 \pm 0.0491$** ($67.34\%$) | $\frac{0.7045 + 0.5896 + 0.6593 + 0.7353 + 0.6786}{5} = \frac{3.367225}{5} = \mathbf{0.673445}$ |
| **Pooled OOF Nominal Accuracy** | Global pooled out-of-fold predictions ($N=578$) | Nominal $\tau = 0.50$ | $\frac{TN + TP}{N} = \frac{183 + 205}{578}$ | **$0.6713$** ($67.13\%$) | $\frac{388}{578} = \mathbf{0.671280}$ |
| **Pooled OOF Tuned Accuracy** | Global pooled out-of-fold predictions ($N=578$) | Tuned $\tau^* = 0.40$ | $\frac{TN + TP}{N} = \frac{163 + 244}{578}$ | **$0.7042$** ($70.42\%$) | $\frac{407}{578} = \mathbf{0.704152}$ |

---

## 5. Decision Threshold Optimization (Pooled Out-of-Fold)

Because missed defects carry higher remediation costs than false positive inspections, decision thresholds $\tau \in [0.10, 0.90]$ were swept across the pooled out-of-fold prediction probabilities:

| Threshold $\tau$ | Accuracy | Precision | Recall | F1-Score | True Negatives (TN) | False Positives (FP) | False Negatives (FN) | True Positives (TP) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0.20 | 0.6609 | 0.5928 | 0.9498 | 0.7300 | 117 | 182 | 14 | 265 |
| 0.30 | 0.6834 | 0.6143 | 0.9247 | 0.7382 | 137 | 162 | 21 | 258 |
| **0.40 ($\tau^*$)** | **0.7042** | **0.6421** | **0.8746** | **0.7405** | **163** | **136** | **35** | **244** |
| 0.45 | 0.7076 | 0.6528 | 0.8423 | 0.7355 | 174 | 125 | 44 | 235 |
| **0.50 (Nominal)** | **0.6713** | **0.6386** | **0.7348** | **0.6833** | **183** | **116** | **74** | **205** |
| 0.55 | 0.6540 | 0.6367 | 0.6595 | 0.6479 | 194 | 105 | 95 | 184 |
| 0.60 | 0.6453 | 0.6516 | 0.5699 | 0.6080 | 214 | 85 | 120 | 159 |
| 0.70 | 0.5502 | 0.5655 | 0.2939 | 0.3868 | 236 | 63 | 197 | 82 |
| 0.80 | 0.5173 | 0.5000 | 0.0538 | 0.0971 | 284 | 15 | 264 | 15 |

### Optimal Decision Cutoff
- **Optimal Threshold:** $\tau^* = 0.40$ maximizes the out-of-fold F1-score at **0.7405**.
- **Operational Impact:** Compared to nominal $\tau=0.50$, shifting to $\tau^*=0.40$ reduces False Negatives from 74 to 35, catching 39 additional defective methods and elevating Recall from 73.48% to **87.46%** with negligible precision impact (63.86% to 64.21%).
- **Methodological Context:** Decision threshold $\tau^* = 0.40$ was identified on pooled out-of-fold cross-validation predictions without nested cross-validation, which introduces mild threshold-selection bias, and was subsequently evaluated without alteration against the independent holdout repository (`Newtonsoft.Json`).

---

## 6. Frozen Model Artifact Specification

- **Serialized Path:** `4_AppBuild/Assets/Models/exp_final_5fold_v2_best_rf_compact_regularized.joblib`
- **Historical Benchmark Copy:** `3_TestResults/FinalCrossValidation/exp_final_5fold_v2_best_rf_compact_regularized.joblib`
- **File Size:** 145,504 bytes
- **SHA-256 Digest:** `625992350a78d28277c3521a3ff97f5e28cda4d4f6996c1dc90374512c19cb1e`
- **Algorithm:** `RandomForestClassifier`
- **Frozen Hyperparameters:** `n_estimators=100`, `max_depth=8`, `min_samples_split=5`, `min_samples_leaf=4`, `max_features='sqrt'`, `class_weight='balanced'`, `random_state=42`.
- **Integrated Preprocessor:** `DataPreprocessor` (median imputation, variance pruning) fitted on all 578 training observations with 26 feature inputs.

---

## 7. Independent Holdout Evaluation (`JamesNK/Newtonsoft.Json`)

To ensure an unbiased evaluation of real-world generalization, `JamesNK/Newtonsoft.Json` (159 production methods: 79 defect-prone, 80 candidate-clean; total evaluation corpus: 737 observations) was evaluated in a single un-tuned run after the model architecture and thresholds were frozen:

| Metric | Nominal Threshold ($\tau = 0.50$) | CV-Tuned Threshold ($\tau^* = 0.40$) |
| :--- | :---: | :---: |
| **Accuracy** | 74.21% (118/159) | **75.47% (120/159)** |
| **Precision** | **69.79%** (67/96) | 69.61% (71/102) |
| **Recall** | 84.81% (67/79) | **89.87% (71/79)** |
| **F1-Score** | 0.7657 | **0.7845** |
| **ROC-AUC** | **0.8209** | **0.8209** |
| **PR-AUC** | **0.7917** | **0.7917** |
| **Brier Score** | **0.1713** | **0.1713** |

### Confusion Matrices on Holdout Repository
- **At Nominal Threshold ($\tau = 0.50$):**
  $$TN = 51, \quad FP = 29, \quad FN = 12, \quad TP = 67$$
- **At CV-Tuned Threshold ($\tau^* = 0.40$):**
  $$TN = 49, \quad FP = 31, \quad FN = 8, \quad TP = 71$$

The independent holdout results confirm that cross-validation estimates ($F_1 = 0.6859, \text{AUC} = 0.7025$) were conservative. On an unseen production codebase, the model achieved **F1 = 0.7845** and **ROC-AUC = 0.8209**, correctly intercepting 9 out of 10 historical defects.

