# Phase II Experimental Design: Schema-Grounded Text-to-SQL

## 1. Executive Summary & Experimental Objectives

Phase I demonstrated that Low-Rank Adaptation at rank 8 ($r=8$) preserved baseline Execution Accuracy (62.5% vs 62.5%) while tripling Exact Match (13.0% $\rightarrow$ 40.0%) and lifting format validity to 100.0%. However, higher ranks ($r=16, 32$) suffered severe regressions (-2.0% and -13.0%), driven by:
1. **Unnecessary Multi-Table Join Chaining**: Overfitting to Spider's table graphs on simple queries.
2. **Schema Linking Degradation**: Swapping column attributions across table aliases (`T1, T2`).
3. **Runaway Autoregressive Join Loops**: Endless recursive join expansion in high-capacity adapters.

**Phase II Objective**: Shift from direct surface SQL token prediction to **structured schema-grounded fine-tuning**, forcing the model to explicitly resolve relevant tables, columns, and relationships under `<SCHEMA_SELECTION>` prior to generating `<SQL>`.

---

## 2. Experimental Triad Specification

All experiments use the fixed base model `Qwen2.5-Coder-3B-Instruct-4bit` on Apple Silicon M4 under strictly identical optimizer settings ($r=8, \alpha=16$, AdamW $\text{lr}=10^{-4}$, effective batch size 4):

| Experiment Code | Strategy / Variant | Input Prompt Representation | Target Output Representation | Core Scientific Hypothesis |
| :--- | :--- | :--- | :--- | :--- |
| **`exp_phase2_a_direct_r8`** | **Dataset A: Direct SQL** | Full schema prompt + User Question | Direct SQL target (` ```sql ... ``` `) | Controls for synthetic data augmentation; serves as direct benchmark baseline. |
| **`exp_phase2_b_grounded_r8`** | **Dataset B: Schema-Grounded** | Relevant schema prompt (pruned) + User Question | `<SCHEMA_SELECTION>` + `<SQL>` | Evaluates whether structured schema selection improves table/column attribution when distractors are minimized. |
| **`exp_phase2_c_distractors_r8`**| **Dataset C: Distractor Grounding**| Full schema prompt (with distractors) + Question | `<SCHEMA_SELECTION>` + `<SQL>` | Evaluates whether the model learns to filter irrelevant tables/columns from complex multi-table enterprise schemas. |

---

## 3. Dataset Composition & Cryptographic Manifest

Phase II training datasets were constructed from 3,500 base records plus 20 targeted, SQLite-validated synthetic query pairs countering Phase I error modes:

| Dataset File | Role | Records | SHA-256 Hash |
| :--- | :--- | :---: | :--- |
| **`phase2_train_a.jsonl`** | Variant A Train | 3,520 | `1dc7ff636d225dc64d66766bdc9f35a9b9679656acfdb19732f1cfe37c140570` |
| **`phase2_valid_a.jsonl`** | Variant A Valid | 350 | `9a44f25246e5c86c6a70fd6e6e9c23aa91bc039821460728dd56e5915c31d520` |
| **`phase2_train_b.jsonl`** | Variant B Train | 3520 | `e137b49437e4ce8e2d6fd7b152e8423588560b021cc2abe54e2e3ed81fb4eab8` |
| **`phase2_valid_b.jsonl`** | Variant B Valid | 350 | `6a85168410694f2dd052aef71e829941ed3d2480b4f9d7418c5cb2167f2dab57` |
| **`phase2_train_c.jsonl`** | Variant C Train | 3,520 | `9102a44b52957ac649acfb1c9dcbf29a021ea16f25d6a6498843f1b0eeb1b34e` |
| **`phase2_valid_c.jsonl`** | Variant C Valid | 350 | `f66b88b1be5d899e852ef1548fdf52b8abd7f5888878260ea9ee09ca85737550` |

---

## 4. Protected Dual-Benchmark Evaluation Architecture

To prevent over-tuning on the development set, Phase II implements a **two-tier held-out evaluation architecture**:

1. **Development Benchmark (`DEV_UNSEEN_200`)**:
   - File: `2_Database/processed/evaluation_sample_unseen_200.json`
   - Size: 200 stratified unseen-schema queries across all 22 databases.
   - Purpose: Iterative model diagnostics and historical comparability with Phase I.
2. **Final Confirmation Benchmark (`CONFIRMATION_UNSEEN_200`)**:
   - File: `2_Database/processed/confirmation_sample_unseen_200.json`
   - Size: 200 unexamined unseen-schema queries sampled from the remaining 844 unseen pool (`seed=1337`).
   - SHA-256: `3d84b925a5eec2d63b7f74021cf502be73f51f301f7fb9584a1b6e56e8fc5835`
   - **Zero Overlap**: Verified 0 overlapping IDs with `DEV_UNSEEN_200`.
   - Purpose: Unbiased confirmation of generalization.

---

## 5. Training Schedule & Optimizer Budget

- **Dataset Size ($N$)**: 3,520 examples.
- **Batch Size ($B$)**: 2 examples per device step.
- **Gradient Accumulation ($G$)**: 2 steps.
- **Effective Batch Size**: $2 \times 2 = 4$ examples.
- **Optimizer Updates per Epoch**: $3,520 / 4 = 880$ steps.
- **Conservative Training Budget**: 100 optimizer updates (~0.11 epochs / 400 sample exposures).
  - Validation evaluation interval: every 20 steps.
  - Checkpoint saving interval: every 20 steps.
  - Early stopping condition: if validation loss consistently degrades across 2 consecutive evaluation checkpoints.

---

## 6. Evaluation Metrics & Contingency Analysis

In addition to traditional execution metrics, Phase II evaluates:
1. **Schema Table Selection**: Precision, Recall, and F1 score against ground truth tables.
2. **Schema Column Selection**: Precision, Recall, and F1 score against ground truth columns.
3. **4-Way Schema-Execution Contingency**:
   - $n_{11}$: Schema Selection Correct AND SQL Execution Correct
   - $n_{10}$: Schema Selection Correct BUT SQL Execution Wrong
   - $n_{01}$: Schema Selection Wrong BUT SQL Execution Correct
   - $n_{00}$: Both Schema Selection and SQL Execution Wrong
4. **Latency Profiles**: Average, Median, and P90 latency.
5. **Statistical Significance**: Paired 95% bootstrap confidence intervals and McNemar's test.
