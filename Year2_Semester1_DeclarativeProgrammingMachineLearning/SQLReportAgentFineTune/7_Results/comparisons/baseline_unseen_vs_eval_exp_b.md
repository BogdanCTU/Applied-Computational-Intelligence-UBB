# Statistical Evaluation Comparison: baseline_unseen vs eval_exp_b

## 1. Executive Summary Table

| Metric | Baseline (`baseline_unseen`) | Fine-Tuned (`eval_exp_b`) | Absolute Delta | Relative Gain |
| :--- | :---: | :---: | :---: | :---: |
| **Execution Accuracy (EX)** | **68.0%** | **56.0%** | **-12.0%** | **-17.65%** |
| 95% Bootstrap CI (EX) | [48.0%, 84.0%] | [36.0%, 76.0%] | - | - |
| **Exact Match Rate (EM)** | 20.0% | 24.0% | +4.0% | - |
| **Valid SQL Rate (VSR)** | 100.0% | 100.0% | 0.0% | - |
| **Average Latency** | 1680.7 ms | 4222.05 ms | +2541.35 ms | - |
| **Total Test Samples** | 25 | 25 | - | - |

## 2. Visual Metric Comparison

```text
Execution Accuracy (EX):
Baseline:    █████████████████░░░░░░░░ 68.0%
Fine-Tuned:  ██████████████░░░░░░░░░░░ 56.0%

Valid SQL Rate (VSR):
Baseline:    █████████████████████████ 100.0%
Fine-Tuned:  █████████████████████████ 100.0%
```

## 3. Paired Sample Contingency Analysis

- **Both Correct**: 13
- **Improved by Fine-Tuning** (Baseline Fail -> Fine-Tuned Pass): **1**
- **Regressed by Fine-Tuning** (Baseline Pass -> Fine-Tuned Fail): 4
- **Both Failed**: 7

## 4. Error Category Distributions

| Error Category | Baseline Count | Fine-Tuned Count |
| :--- | :---: | :---: |
| `execution_mismatch` | 7 | 8 |
| `none` | 17 | 14 |
| `schema_linking_error` | 1 | 2 |
| `syntax_error` | 0 | 1 |
