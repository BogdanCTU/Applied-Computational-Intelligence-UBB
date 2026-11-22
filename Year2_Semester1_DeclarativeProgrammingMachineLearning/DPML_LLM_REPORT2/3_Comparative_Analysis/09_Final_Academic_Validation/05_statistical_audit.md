# 05. Independent Statistical & Latency Audit
**Precomputed `v2` JSON Verification:** **PASS** (`baseline_full_metrics.json`, `mitigated_full_metrics.json`, and `comparative_full_metrics.json` match raw SQLite/JSONL recomputation bit-for-bit under `v2`).

## 1. Recomputed Principal Safety Metrics (`v2` Historical vs. `v3` Audited)
| Metric | `v2` Baseline | `v2` Mitigated | `v3` Baseline | `v3` Mitigated | `v3` Delta |
|---|---:|---:|---:|---:|---:|
| `unsafe_compliance_rate` | 0.00% | 0.00% | **0.20%** | **0.10%** | -0.10 pp |
| `partial_compliance_rate` | 5.49% | 1.67% | **2.94%** | **0.00%** | -2.94 pp |
| `adversarial_failure_rate` | 5.49% | 1.67% | **3.14%** | **0.10%** | -3.04 pp |
| `safe_response_rate` | 93.75% | 97.50% | **95.33%** | **92.67%** | -2.66 pp |
| `refusal_rate` | 80.42% | 84.33% | **83.17%** | **92.00%** | +8.83 pp |
| `refusal_precision` | 99.69% | 99.01% | **99.00%** | **92.30%** | -6.70 pp |
| `benign_task_completion_rate` | 90.56% | 93.33% | **86.67%** | **51.67%** | -35.00 pp |
| `over_refusal_rate` | 1.67% | 5.56% | **5.56%** | **47.22%** | +41.66 pp |
| `severity_weighted_failure_rate` | 5.70% | 2.16% | **3.40%** | **2.58%** | -0.82 pp |
| `tool_authorization_violation_rate` | 1.49% | 0.00% | **1.49%** | **0.00%** | -1.49 pp |
| `prompt_injection_success_rate` | 8.24% | 3.53% | **3.53%** | **1.18%** | -2.35 pp |
| `data_disclosure_rate` | 4.08% | 0.50% | **3.33%** | **0.17%** | -3.16 pp |

## 2. Denominator Audit & `TAVR` Correction
- `AFR`, `UCR`, `PCR` correctly use adversarial tests (`n = 1,020` global; `n = 85` per category; `n = 240` held-out) rather than all `1,200` cases.
- `BTCR`, `ORR` correctly use benign control tests (`n = 180` global; `n = 15` per category; `n = 60` held-out).
- **Dynamic `TAVR` Denominator Discrepancy (`metrics.py` line 81):** Including `prompt_injection` rows only when `tool_invocations` is non-empty produced denominators of `202` (baseline) vs. `201` (mitigated). Fixed-denominator audit yields identical denominators: `all_300` (`tool_abuse + data_exfiltration + prompt_injection`) = `3/300` (`1.00%`) -> `0/300` (`0.00%`); `two_200` (`tool_abuse + data_exfiltration`) = `3/200` (`1.50%`) -> `0/200` (`0.00%`); `adv_255` = `1/255` (`0.39%`) -> `0/255` (`0.00%`).

## 3. Latency & Confounder Audit (OLS Token Decomposition)
- **Warm-Up Check:** First executed case (`CYBER_0001`) took `6.1499s` (baseline vs. mean `8.4502s`) and `7.3918s` (mitigated vs. mean `5.1483s`) — negligible cold-start distortion.
- **Execution Order & Prompt Length:** Prefix caching + inactive-model unloading kept prefill overhead minimal across the `900` non-tool tests (`106.2` prompt tokens, `9.0195s` base / `5.2099s` mit) vs. the `300` tool-enabled tests (`736.0` prompt tokens, `6.7425s` base / `4.9637s` mit).
- **Output-Length Confounder:** Completion tokens dropped `39.56%` (`147,927` -> `89,407`, Wilcoxon `p = 4.00e-139`), while OLS generation speed remained virtually identical (`15.61 tok/s` [`R²=0.9665`] vs. `16.21 tok/s` [`R²=0.9958`]). Thus, the 39.1% wall-clock latency reduction reflects shorter mitigated refusal stubs, not faster model decoding.
