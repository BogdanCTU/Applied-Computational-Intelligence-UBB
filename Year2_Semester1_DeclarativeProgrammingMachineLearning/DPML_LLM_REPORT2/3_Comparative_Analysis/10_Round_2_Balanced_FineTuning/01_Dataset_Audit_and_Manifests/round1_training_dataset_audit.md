# Round 1 Training & Validation Dataset Audit

| Split | Total | Adversarial (%) | Benign (%) | Ratio (Adv:Ben) | Unique Prompts | Unique Target Replies | Template Families |
|---|---:|---:|---:|---:|---:|---:|---:|
| `train.jsonl` | 727 | 638 (87.76%) | 89 (12.24%) | 7.17:1 | 727 | 53 | 151 |
| `valid.jsonl` | 181 | 145 (80.11%) | 36 (19.89%) | 4.03:1 | 181 | 47 | 37 |

## Root Causes of Round 1 Benign Over-Refusal
1. **Severe Class Imbalance:** `638` adversarial vs. `89` benign (`7.17:1`) caused conservative refusal priors.
2. **Severe Semantic Target Repetition:** `727` training examples mapped onto only `53` distinct target completions, collapsing nuanced domain answers into repetitive generic 2-sentence stubs.
3. **Metadata Cue Conditioning:** `84/89` Round 1 benign prompts carried `[Case ...]`, `[Module ...]`, or `[Ref ...]` tags alongside sensitive keywords (`"In a benign educational overview on <subcategory>..."`), while the 638 adversarial refusals taught the adapter to reject bracketed audit/module tags.
