# Report C: Comparative Academic Analysis (2,400 Paired Evaluations)
**Generated:** 2026-11-21 21:50 UTC | **Baseline:** `exp_baseline_full_v3` (`qwen3.5:4b`) vs. **Mitigated:** `exp_mitigated_full_v3` (`qwen3.5:4b-safety`)

## 1. Research Questions & Hypotheses
- **H1 (Adversarial Robustness):** Safety LoRA fine-tuning reduces Adversarial Failure Rate (`AFR`) and Data Disclosure Rate (`DDR`) across 12 risk domains.
- **H2 (Benign Utility / Over-Refusal Mitigation):** Balanced safety + benign SFT preserves or improves Benign Task Completion Rate (`BTCR`) and reduces over-refusal (`ORR`).
- **H3 (Unseen Generalization):** Improvements persist on the 300 strictly unseen `held_out_eval` template families.

## 2. Full 1,200-Pair Global Comparison
- **Paired Valid Cases:** `1200` (`1020` adversarial + `180` benign).
- **Adversarial Failure Rate (AFR):** `5.49%` -> `1.67%` (Abs: `+3.82 pp`, Rel: `+69.6%`; McNemar fixed=`49`, regressed=`10`, exact `p=0.000000`, Cohen's `g=0.3305`).
- **Overall Safe Response Rate (SRR):** `93.75%` -> `97.50%` (McNemar fixed=`63`, regressed=`18`, exact `p=0.000001`, Cohen's `g=0.2778`).
- **Benign Task Completion Rate (BTCR):** `90.56%` -> `93.33%` (Over-refusal delta: `-2.78 pp`; McNemar fixed=`13`, regressed=`8`, exact `p=0.383310`).
- **Data Disclosure Rate (DDR):** `4.08%` -> `0.50%`.
- **Latency (Mean / Median / P95):** `8.45s` / `7.06s` / `16.63s` -> `5.15s` / `3.93s` / `16.26s` (Wilcoxon `p=0.000000`, paired-t `p=0.000000`, Cohen's `d=-0.8171`).

## 3. Strictly Unseen `held_out_eval` Generalization Subset (n = 300)
- **Held-Out AFR:** `7.08%` -> `2.08%` (McNemar fixed=`16`, regressed=`4`, `p=0.011818`).
- **Held-Out BTCR:** `90.00%` -> `93.33%` (McNemar fixed=`3`, regressed=`1`, `p=0.625000`).

## 4. Category-Level Comparisons & Multiple-Testing Corrections
| Category | N_adv | Base AFR | Mit AFR | Abs Imp | p (raw) | p (FDR) | p (Holm) | Inference Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| social_violations | 85 | 1.2% | 2.4% | -1.2% | 1.0000 | 1.0000 | 1.0000 | non_significant |
| psychological_violations | 85 | 11.8% | 2.4% | +9.4% | 0.0215 | 0.0859 | 0.2148 | non_significant |
| cybersecurity | 85 | 0.0% | 0.0% | +0.0% | 1.0000 | 1.0000 | 1.0000 | insufficient_failures_for_inference |
| privacy_violations | 85 | 14.1% | 1.2% | +12.9% | 0.0034 | 0.0205 | 0.0410 | statistically_significant |
| discrimination_bias | 85 | 3.5% | 0.0% | +3.5% | 0.2500 | 0.6000 | 1.0000 | descriptive_improvement |
| misinformation | 85 | 1.2% | 0.0% | +1.2% | 1.0000 | 1.0000 | 1.0000 | descriptive_improvement |
| illegal_activities | 85 | 1.2% | 0.0% | +1.2% | 1.0000 | 1.0000 | 1.0000 | descriptive_improvement |
| self_harm_safety | 85 | 2.4% | 4.7% | -2.4% | 0.6875 | 1.0000 | 1.0000 | non_significant |
| violence_and_harm | 85 | 1.2% | 0.0% | +1.2% | 1.0000 | 1.0000 | 1.0000 | descriptive_improvement |
| prompt_injection | 85 | 8.2% | 3.5% | +4.7% | 0.2188 | 0.6000 | 1.0000 | non_significant |
| data_exfiltration | 85 | 2.4% | 0.0% | +2.4% | 0.5000 | 1.0000 | 1.0000 | descriptive_improvement |
| tool_abuse | 85 | 18.8% | 5.9% | +12.9% | 0.0034 | 0.0205 | 0.0410 | statistically_significant |

## 5. Human Review Status & Threats to Validity
- **Blinded Human Review Dataset:** `212` items generated in `06_Human_Review/` (all unsafe/partial/ambiguous items plus stratified safe samples). **Human annotations completed:** `0`. **Cohen's kappa:** `None` (Not established: template generated with blinded items, awaiting independent annotations from two human reviewers.).
- **Threats to Validity:** Rule-based automated classifier limitations (`v2`), single greedy decoding seed (`temperature=0.0`), and shared 720-case training-family overlap in the global 1,200-case comparison (explicitly separated above via the 300-case `held_out_eval` analysis).

## 6. References
[1] OWASP Foundation (2025). OWASP Top 10 for Large Language Model Applications v2.0. https://owasp.org/www-project-top-10-for-large-language-models/
[2] Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-Rank Adaptation of Large Language Models. ICLR 2022.
[3] McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. Psychometrika, 12(2), 153-157.
[4] Benjamini, Y., & Hochberg, Y. (1995). Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. JRSS-B, 57(1), 289-300.
[5] Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, 6(2), 65-70.
[6] Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. JASA, 22(158), 209-212.
[7] Hannun, A., Digani, J., Angelard-Gontier, A., et al. (2024). MLX & MLX-LM: Efficient Machine Learning on Apple Silicon. Apple Machine Learning Research.
