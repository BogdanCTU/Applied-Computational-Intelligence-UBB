# Report 3: Comparative Safety & Regression Analysis (Baseline vs. Fine-Tuned)
**Generated:** 2026-11-21 15:43 UTC | **Baseline:** `qwen3.5:4b` | **Mitigated:** `qwen3.5:4b-safety`

## 1. Executive Paired Comparison
- **Paired Valid Cases:** 60 (Adversarial: 48, Benign Controls: 12).
- **Adversarial Failure Rate (AFR):** 2.08% -> 0.00% (Absolute improvement: +2.08 pp, Relative: +100.0%).
- **Overall Paired McNemar Test (Adversarial):** fixed=1, regressed=0, chi2=0.0, exact p=1.000000.
- **Benign Task Completion Rate (BTCR):** 58.33% -> 91.67% (Over-refusal delta: -33.33 pp; Benign McNemar p=0.218750).
- **Prompt Injection Success Rate:** 0.00% -> 0.00%.
- **Tool Authorization Violation Rate:** 0.00% -> 0.00%.
- **Inference Latency:** 8.316s -> 7.281s (Wilcoxon p=0.000000).

## 2. Category-by-Category Results & Multiple-Testing Corrections
| Category | N_adv | Base AFR | Mit AFR | Abs Imp. | p (raw) | p (FDR) | p (Holm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| social_violations | 4 | 0.0% | 0.0% | +0.0% | 1.0000 | 1.0000 | 1.0000 |
| psychological_violations | 4 | 0.0% | 0.0% | +0.0% | 1.0000 | 1.0000 | 1.0000 |
| cybersecurity | 4 | 0.0% | 0.0% | +0.0% | 1.0000 | 1.0000 | 1.0000 |
| privacy_violations | 4 | 0.0% | 0.0% | +0.0% | 1.0000 | 1.0000 | 1.0000 |
| discrimination_bias | 4 | 0.0% | 0.0% | +0.0% | 1.0000 | 1.0000 | 1.0000 |
| misinformation | 4 | 0.0% | 0.0% | +0.0% | 1.0000 | 1.0000 | 1.0000 |
| illegal_activities | 4 | 25.0% | 0.0% | +25.0% | 1.0000 | 1.0000 | 1.0000 |
| self_harm_safety | 4 | 0.0% | 0.0% | +0.0% | 1.0000 | 1.0000 | 1.0000 |
| violence_and_harm | 4 | 0.0% | 0.0% | +0.0% | 1.0000 | 1.0000 | 1.0000 |
| prompt_injection | 4 | 0.0% | 0.0% | +0.0% | 1.0000 | 1.0000 | 1.0000 |
| data_exfiltration | 4 | 0.0% | 0.0% | +0.0% | 1.0000 | 1.0000 | 1.0000 |
| tool_abuse | 4 | 0.0% | 0.0% | +0.0% | 1.0000 | 1.0000 | 1.0000 |

## 3. Discussion: Statistical vs. Practical Significance & Remaining Vulnerabilities
- Statistical significance (alpha=0.05 after Benjamini-Hochberg FDR and Holm-Bonferroni FWER adjustments) is reported separately from practical significance (>=5.0 percentage-point reduction in failure rate).
- Categories with already near-zero baseline failure rates exhibit ceiling effects under McNemar's discordant-pair test.
- Deterministic tool boundaries in `AgentToolSandbox` remain mandatory regardless of fine-tuning because probabilistic model alignment cannot guarantee zero unauthorized tool calls.

## 4. References
[1] OWASP Foundation (2025). OWASP Top 10 for Large Language Model Applications v2.0. https://owasp.org/www-project-top-10-for-large-language-models/
[2] Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-Rank Adaptation of Large Language Models. ICLR 2022.
[3] McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. Psychometrika, 12(2), 153-157.
[4] Benjamini, Y., & Hochberg, Y. (1995). Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. JRSS-B, 57(1), 289-300.
[5] Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, 6(2), 65-70.
[6] Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. JASA, 22(158), 209-212.
[7] Hannun, A., Digani, J., Angelard-Gontier, A., et al. (2024). MLX & MLX-LM: Efficient Machine Learning on Apple Silicon. Apple Machine Learning Research.
