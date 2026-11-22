# Phase 4 Academic Report: Round 2 Balanced Safety Fine-Tuning (`qwen3.5:4b-safety-v2`)
**Generated:** 2026-11-22 16:16 UTC | **Models:** `qwen3.5:4b` vs. `qwen3.5:4b-safety` vs. `qwen3.5:4b-safety-v2` | **Evaluator:** `v3` | **Verdict:** **`PARETO_IMPROVED_SUCCESS`**

## 1. Training Dataset Audit & Diagnosis of Round 1 Over-Refusal
- **Round 1 Mix:** `727` train (`638` adv / `89` ben, ratio **`7.17:1`**) with only `53` unique target responses; `84/89` benign prompts carried `[Case ...]`/`[Module ...]`/`[Ref ...]` tags.
- **Round 2 Contrastive Dataset (`balanced_50_50`):** `720` train (`360` adv + `360` ben = **1.00:1**) across `49` unique targets covering Types A, B, C, D (harmless intent w/ suspicious metadata), and E (quoted malicious SQL/injection/phishing analysis), plus `144` validation (`72` adv + `72` ben). **Overlap with `held_out_eval` (`300`) and Benchmark C (`300`): `0`**. SHA-256 `train.jsonl`: `3e06d423a230e47eaae0c691f8001763078ff949e0d2e8fe77074abd3b737ab1`.

## 2. Controlled LoRA Configuration, Ablation & Conversion Verification
- **LoRA Config (Identical Architecture to R1):** Base MLX `qwen3.5_4b_base_mlx`, `rank=8`, `alpha=16.0`, `scale=2.0`, `num_layers=4`, `batch_size=1`, `lr=1e-4`, `max_seq_length=384`, `mask_prompt=True`, `seed=42`.
- **Ratio Ablation (`val_pool` Selection Only):** Arm `65/35` (40 iters, `238.89s`): `val_loss` `3.032 -> 1.818`, 24-case `val_pool` probe `AFR=50.0%`, `BTCR=100.0%`. Arm `50/50` (60 iters, `376.18s`): `val_loss` `3.032 -> 1.531`, `val_pool` probe `AFR=8.3%`, `BTCR=100.0%`.
- **Ollama Export & Fidelity Check:** Exported `qwen3.5:4b-safety-v2` (digest `c6075cef6819a06965d510ba6d5d6884d2e72da54fbd9b642eb4758562238f42`), `31` modified blobs + `395` reused base blobs; matched MLX-vs-Ollama 5-prompt check `all_matched_classes_agree=False`.

## 3. Three-Model Quantitative Comparison (Audited Evaluator `v3`)
| Suite | Model | AFR | UCR | PCR | BTCR | ORR | RP | DDR_true | SRR | Mean Lat |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Suite A (held_out 300) | Baseline | 3.75% | 0.00% | 3.75% | 91.67% | 0.00% | 100.00% | 4.33% | 95.33% | 8.66s |
| Suite A (held_out 300) | Round 1 | 0.00% | 0.00% | 0.00% | 53.33% | 45.00% | 89.89% | 0.33% | 90.67% | 5.36s |
| Suite A (held_out 300) | Round 2 | 0.83% | 0.00% | 0.83% | 91.67% | 8.33% | 97.94% | 1.33% | 97.67% | 7.55s |
| Suite B (benign 180) | Baseline | 0.00% | 0.00% | 0.00% | 86.67% | 5.56% | 0.00% | 6.67% | 86.67% | 15.20s |
| Suite B (benign 180) | Round 1 | 0.00% | 0.00% | 0.00% | 51.67% | 47.22% | 0.00% | 1.11% | 51.67% | 9.94s |
| Suite B (benign 180) | Round 2 | 0.00% | 0.00% | 0.00% | 90.56% | 9.44% | 0.00% | 1.67% | 90.56% | 14.96s |
| Suite C (indep 300) | Baseline | 0.67% | 0.00% | 0.67% | 84.67% | 2.67% | 97.39% | 5.00% | 92.00% | 6.28s |
| Suite C (indep 300) | Round 1 | 0.00% | 0.00% | 0.00% | 67.33% | 25.33% | 79.79% | 5.00% | 83.67% | 6.50s |
| Suite C (indep 300) | Round 2 | 0.67% | 0.00% | 0.67% | 88.00% | 2.67% | 97.39% | 2.00% | 93.67% | 11.21s |
| Combined Unseen (600) | Baseline | 2.56% | 0.00% | 2.56% | 86.67% | 1.90% | 98.96% | 4.67% | 93.67% | 7.47s |
| Combined Unseen (600) | Round 1 | 0.00% | 0.00% | 0.00% | 63.33% | 30.95% | 85.71% | 2.67% | 87.17% | 5.93s |
| Combined Unseen (600) | Round 2 | 0.77% | 0.00% | 0.77% | 89.05% | 4.29% | 97.73% | 1.67% | 95.67% | 9.38s |

## 4. Provenance Audit of Suite B (`180` v1.0 Benign Controls)
| Subset | Provenance Exposure | N | Baseline BTCR (ORR) | Round 1 BTCR (ORR) | Round 2 BTCR (ORR) | R1 -> R2 McNemar `p` |
|---|---|---:|---:|---:|---:|---:|
| `train_pool` | `seen_in_sft_train` | 84 | 89.3% (3.6%) | 54.8% (44.0%) | **90.5% (9.5%)** | 1.54e-08 |
| `val_pool` | `val_monitored` | 36 | 72.2% (19.4%) | 41.7% (58.3%) | **88.9% (11.1%)** | 1.53e-05 |
| `held_out_eval` | `strictly_unseen` | 60 | 91.7% (0.0%) | 53.3% (45.0%) | **91.7% (8.3%)** | 1.55e-06 |

## 5. Hypothesis Testing & Paired Pareto Conclusions (Unseen Generalization)
- **Combined Strictly Unseen Generalization (`Suite A + C = 600` cases: `390` adv + `210` ben):**
  - **Adversarial Safety (`Baseline -> Round 1 -> Round 2`):** `AFR` moved `2.56% -> 0.00% -> 0.77%` (`Baseline vs R2`: `fixed=8`, `reg=1`, McNemar `p = 0.039062`; `R1 vs R2`: `fixed=0`, `reg=3`, `p = 0.250000`).
  - **Benign Utility (`BTCR` / `ORR`):** `BTCR` moved `86.67% -> 63.33% -> 89.05%`, and `ORR` moved `1.90% -> 30.95% -> 4.29%` (`R1 vs R2` McNemar `p = 6.42e-10`, Cohen's `g = 0.3375`).
- **Benchmark A (`held_out_eval`, `n=300`):** `R1 -> R2` `AFR` `0.00% -> 0.83%` (`p = 0.500000`); `BTCR` `53.33% -> 91.67%` (`p = 1.55e-06`).
- **Benchmark C (`independent_bench_c`, `n=300`):** `R1 -> R2` `AFR` `0.00% -> 0.67%` (`p = 1.000000`); `BTCR` `67.33% -> 88.00%` (`p = 3.31e-05`).

## 6. References
[1] OWASP Foundation (2025). OWASP Top 10 for Large Language Model Applications v2.0. https://owasp.org/www-project-top-10-for-large-language-models/
[2] Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-Rank Adaptation of Large Language Models. ICLR 2022.
[3] McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. Psychometrika, 12(2), 153-157.
[4] Benjamini, Y., & Hochberg, Y. (1995). Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. JRSS-B, 57(1), 289-300.
[5] Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, 6(2), 65-70.
[6] Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. JASA, 22(158), 209-212.
[7] Hannun, A., Digani, J., Angelard-Gontier, A., et al. (2024). MLX & MLX-LM: Efficient Machine Learning on Apple Silicon. Apple Machine Learning Research.
