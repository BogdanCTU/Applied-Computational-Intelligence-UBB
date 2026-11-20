# Statistical Evaluation Comparison: baseline_known vs eval_exp_b_known

## 1. Executive Summary Table

| Metric | Baseline (`baseline_known`) | Fine-Tuned (`eval_exp_b_known`) | Absolute Delta | Relative Gain |
| :--- | :---: | :---: | :---: | :---: |
| **Execution Accuracy (EX)** | **73.33%** | **73.33%** | **0.0%** | **0.0%** |
| 95% Bootstrap CI (EX) | [46.67%, 93.33%] | [53.33%, 93.33%] | - | - |
| **Exact Match Rate (EM)** | 26.67% | 26.67% | 0.0% | - |
| **Valid SQL Rate (VSR)** | 93.33% | 100.0% | +6.67% | - |
| **Average Latency** | 4750.75 ms | 5288.38 ms | +537.63 ms | - |
| **Total Test Samples** | 15 | 15 | - | - |

## 2. Visual Metric Comparison

```text
Execution Accuracy (EX):
Baseline:    ██████████████████░░░░░░░ 73.33%
Fine-Tuned:  ██████████████████░░░░░░░ 73.33%

Valid SQL Rate (VSR):
Baseline:    ███████████████████████░░ 93.33%
Fine-Tuned:  █████████████████████████ 100.0%
```

## 3. Paired Sample Contingency Analysis

- **Both Correct**: 10
- **Improved by Fine-Tuning** (Baseline Fail -> Fine-Tuned Pass): **1**
- **Regressed by Fine-Tuning** (Baseline Pass -> Fine-Tuned Fail): 1
- **Both Failed**: 3

## 4. Error Category Distributions

| Error Category | Baseline Count | Fine-Tuned Count |
| :--- | :---: | :---: |
| `execution_mismatch` | 3 | 4 |
| `none` | 11 | 11 |
| `syntax_error` | 1 | 0 |
