# Statistical Evaluation Comparison: baseline_unseen vs eval_exp_a

## 1. Executive Summary Table

| Metric | Baseline (`baseline_unseen`) | Fine-Tuned (`eval_exp_a`) | Absolute Delta | Relative Gain |
| :--- | :---: | :---: | :---: | :---: |
| **Execution Accuracy (EX)** | **68.0%** | **44.0%** | **-24.0%** | **-35.29%** |
| 95% Bootstrap CI (EX) | [48.0%, 84.0%] | [24.0%, 64.0%] | - | - |
| **Exact Match Rate (EM)** | 20.0% | 36.0% | +16.0% | - |
| **Valid SQL Rate (VSR)** | 100.0% | 100.0% | 0.0% | - |
| **Average Latency** | 1680.7 ms | 1730.47 ms | +49.77 ms | - |
| **Total Test Samples** | 25 | 25 | - | - |

## 2. Visual Metric Comparison

```text
Execution Accuracy (EX):
Baseline:    █████████████████░░░░░░░░ 68.0%
Fine-Tuned:  ███████████░░░░░░░░░░░░░░ 44.0%

Valid SQL Rate (VSR):
Baseline:    █████████████████████████ 100.0%
Fine-Tuned:  █████████████████████████ 100.0%
```

## 3. Paired Sample Contingency Analysis

- **Both Correct**: 11
- **Improved by Fine-Tuning** (Baseline Fail -> Fine-Tuned Pass): **0**
- **Regressed by Fine-Tuning** (Baseline Pass -> Fine-Tuned Fail): 6
- **Both Failed**: 8

## 4. Error Category Distributions

| Error Category | Baseline Count | Fine-Tuned Count |
| :--- | :---: | :---: |
| `execution_mismatch` | 7 | 10 |
| `none` | 17 | 11 |
| `schema_linking_error` | 1 | 2 |
| `syntax_error` | 0 | 2 |
