# Report 2: Safety Fine-Tuning Methodology & Local Conversion
**Generated:** 2026-11-21 15:43 UTC | **Base Model:** `qwen3.5:4b` | **Mitigated Model:** `qwen3.5:4b-safety`

## 1. Mitigation Objectives & Data Separation
- Improve refusal robustness against prompt injection, data exfiltration, tool abuse, and unsafe compliance while preserving benign educational and defensive utility.
- **Training Examples:** 727 (Adversarial: 638, Benign: 89).
- **Validation Examples:** 181 (Adversarial: 145, Benign: 36).
- **Template-Family Overlap with Held-Out Evaluation:** 0 (strictly disjoint).

## 2. Apple Silicon Hardware Constraints & Ollama-to-MLX Conversion
- Ollama stores `qwen3.5:4b` as content-addressed single-tensor `nvfp4` (`group_size=16`) safetensors blobs (`*.weight.scale`) with `qwen3_5` multimodal weights.
- Because MLX-LM cannot train directly on Ollama's manifest/blob layout, `OllamaMLXConverter` reconstructs an MLX-LM directory mapping `*.weight.scale` -> `*.scales` and sets `quantization={group_size:16, bits:4, mode:'nvfp4'}` in `config.json`.
- After LoRA training and fusion, modified tensor blobs (`modified_blobs_written=31`, `reused_blobs=395`) are serialized back into Ollama's `nvfp4` blob format and registered as `qwen3.5:4b-safety`.

## 3. Fine-Tuning Configuration (16 GB Unified Memory)
- **Method:** `lora` (`rank=8`, `alpha=16.0`, `num_layers=4`)
- **Schedule:** `iters=60`, `batch_size=1`, `max_seq_length=384`, `lr=0.0001`, `grad_checkpoint=True`, `mask_prompt=True`.

## 4. Empirical Training & Verification Results
- **Run ID:** `qwen35_4b_safety_lora_v1` | **Duration:** 323.42 s | **Status:** `completed`
- **Initial Validation Loss:** 3.373 -> **Final Validation Loss:** 0.251
- **Final Training Loss:** 0.456
- **MLX Fused Generation Verified:** `True`
- **Ollama Converted Generation Verified:** `True`

### Validation Loss Trajectory
| Iteration | Val Loss |
|---:|---:|
| 1 | 3.373 |
| 20 | 1.058 |
| 40 | 0.407 |
| 60 | 0.251 |

## 5. References
[1] OWASP Foundation (2025). OWASP Top 10 for Large Language Model Applications v2.0. https://owasp.org/www-project-top-10-for-large-language-models/
[2] Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-Rank Adaptation of Large Language Models. ICLR 2022.
[3] McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. Psychometrika, 12(2), 153-157.
[4] Benjamini, Y., & Hochberg, Y. (1995). Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. JRSS-B, 57(1), 289-300.
[5] Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, 6(2), 65-70.
[6] Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. JASA, 22(158), 209-212.
[7] Hannun, A., Digani, J., Angelard-Gontier, A., et al. (2024). MLX & MLX-LM: Efficient Machine Learning on Apple Silicon. Apple Machine Learning Research.
