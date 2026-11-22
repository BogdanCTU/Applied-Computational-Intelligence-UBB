# 02. Training Contamination and Out-of-Sample Generalization Audit
**Template-Family Separation Status:** **PASS** (`0` held-out template families in training or validation).

## 1. Training Contamination Breakdown Across Dataset Splits
| Dataset Split | Total Cases | Adv / Benign | Template Families | Overlap w/ `held_out_eval` Families | Final User Turn in `train.jsonl` | Final User Turn in `valid.jsonl` |
|---|---:|---|---:|---:|---:|---:|
| `train_pool` | 720 | 636 / 84 | 151 | 0 | 720 (100%) | 0 |
| `val_pool` | 180 | 144 / 36 | 37 | 0 | 0 | 180 (100%) |
| **`held_out_eval`** | **300** | **240 / 60** | **60** | **0** | **0 (0%)** | **0 (0%)** |

> [!IMPORTANT]
> Because all `720` `train_pool` final user prompts appear verbatim in `2_FineTune/03_Processed_Datasets/train.jsonl` (`727` total examples) and all `180` `val_pool` final user prompts appear verbatim in `valid.jsonl` (`181` total examples), **75.0% of the 1,200-case benchmark consists of seen or validation-monitored prompts**. Only the **`300` `held_out_eval` cases (`240` adversarial + `60` benign)** provide independent evidence of out-of-sample safety generalization.

## 2. Safety & Utility Metrics Stratified by Split (Audited Evaluator v3)
| Split | Role in Inference | N (Adv/Ben) | Base AFR -> Mit AFR | Adv McNemar (fix/reg, p) | Base BTCR -> Mit BTCR | Base ORR -> Mit ORR | Base DDR -> Mit DDR |
|---|---|---|---:|---|---:|---:|---:|
| `train_pool` | In-sample training adherence (contaminated) | 720 (636/84) | 2.83% -> 0.00% | 18/0, p=7.63e-06 | 89.29% -> 54.76% | 3.57% -> 44.05% | 2.78% -> 0.14% |
| `val_pool` | Validation checkpoint selection (contaminated) | 180 (144/36) | 3.47% -> 0.69% | 4/0, p=0.125000 | 72.22% -> 41.67% | 19.44% -> 58.33% | 3.89% -> 0.00% |
| `held_out_eval` | Independent unseen generalization (UNCONTAMINATED) | 300 (240/60) | 3.75% -> 0.00% | 9/0, p=0.003906 | 91.67% -> 53.33% | 0.00% -> 45.00% | 4.33% -> 0.33% |
| `complete_dataset` | Pooled aggregate (25% unseen / 75% seen) | 1200 (1020/180) | 3.14% -> 0.10% | 31/0, p=9.31e-10 | 86.67% -> 51.67% | 5.56% -> 47.22% | 3.33% -> 0.17% |

## 3. Generalization Conclusion
- **Adversarial Generalization Confirmed (`held_out_eval`, n=240 adv):** Audited AFR dropped from `3.75%` (`9/240`) to `0.00%` (`0/240`; McNemar fixed=`9`, regressed=`0`, exact `p = 0.003906`).
- **Benign Over-Refusal Also Generalized (`held_out_eval`, n=60 ben):** BTCR dropped from `91.67%` (`55/60`) to `53.33%` (`32/60`), while Over-Refusal Rate rose from `0.00%` (`0/60`) to `45.00%` (`27/60`; McNemar fixed=`0`, regressed=`23`, exact `p = 2.38e-07`).
