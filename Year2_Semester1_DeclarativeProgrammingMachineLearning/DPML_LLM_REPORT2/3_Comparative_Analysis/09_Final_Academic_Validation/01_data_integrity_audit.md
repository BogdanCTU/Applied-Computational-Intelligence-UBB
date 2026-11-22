# 01. Independent Data Integrity Audit
**Audit Status:** **PASS** | **SQLite `PRAGMA integrity_check`:** `ok`

## 1. Ten-Point Verification Checklist
| # | Verification Criterion | Result | Evidence |
|---:|---|---|---|
| 1 | Exactly 1,200 unique test cases | PASS | `penetration_dataset_v1.0.jsonl` contains 1,200 rows, 1,200 unique `test_id`s |
| 2 | Exactly 1,200 successful baseline responses | PASS | `exp_baseline_full_v3`: 1,200 `completed` rows, 0 infrastructure errors |
| 3 | Exactly 1,200 successful fine-tuned responses | PASS | `exp_mitigated_full_v3`: 1,200 `completed` rows, 0 infrastructure errors |
| 4 | Identical test IDs across experiments | PASS | Symmetric difference between baseline, mitigated, and dataset `test_id` sets is empty |
| 5 | No duplicate execution records | PASS | 1,200 distinct IDs in SQLite and both raw JSONL exports |
| 6 | No missing raw responses | PASS | 0 empty/null `final_response_text` entries across 2,400 executions |
| 7 | Correct model digests | PASS | Baseline `7f3251fa6878a78a606bcb3c074283306e5ad2ea411a7774a9dd98a4bc7f2d13`; Mitigated `4f64caf59930e66de5ebdb4fde80076578f1027cb252e68580de5a9105e9a904` |
| 8 | Correct dataset SHA-256 | PASS | `2da78ee70c0501bdcbf0656e0622eebb5eaeae9b8f6ff8a7b15b30aa04c95e91` (exact match across file & both manifests) |
| 9 | Correct category and split assignments | PASS | 12 categories × 100 (`85` adv + `15` benign); splits `720 / 180 / 300` |
| 10 | Database and export consistency (`v2`) | PASS | SQLite `PRAGMA integrity_check=ok`; precomputed `08_Full_Evaluation` JSONs match raw `v2` recomputation identically |

## 2. Cryptographic Digests Verified
- **Dataset SHA-256:** `2da78ee70c0501bdcbf0656e0622eebb5eaeae9b8f6ff8a7b15b30aa04c95e91`
- **System Prompt (`sys_safety_v1.0`) SHA-256:** `6de5509ea3ad5af3b942b6f67de37680bdc77b521dff89c0bf6a965fdc3f3597`
- **Baseline Raw JSONL SHA-256:** `ca2153488f034a6158fe7d6c4e59cf2427f33c47428f15caf8322e03cc4f3125`
- **Mitigated Raw JSONL SHA-256:** `f68f4754240d9befcdcfc02f66ebab998f9b0aadbab2f312284856bfe223b3d0`
