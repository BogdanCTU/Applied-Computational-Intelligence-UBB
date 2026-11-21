# Dataset Generation & Leakage Prevention

## Penetration Dataset (`1_Penetration/02_Test_Cases/`)

- Generated deterministically (`random_seed=42`) by `PenetrationTestGenerator`.
- Enforces unique `test_id`s, SHA-256 prompt deduplication, 120-subcategory rotation, and 14-attack-pattern rotation.
- Partitioned strictly by disjoint `template_family` clusters (20 families per category):
  - `train_pool` (families `00..11`, 60% = 720 cases)
  - `val_pool` (families `12..14`, 15% = 180 cases)
  - `held_out_eval` (families `15..19`, 25% = 300 cases: 240 adversarial + 60 benign)

## Mitigation Fine-Tuning Dataset (`2_FineTune/03_Processed_Datasets/`)

- `MitigationDatasetBuilder` generates `train.jsonl` and `valid.jsonl` in MLX-LM `ChatDataset` (`{"messages": [...]}`) format exclusively from `train_pool`, `val_pool`, and curated supplemental pairs.
- **Anti-Leakage Invariant**: Zero `test_id`s or `template_family` identifiers from `held_out_eval` appear in `train.jsonl` or `valid.jsonl`.
- **Positive Target Integrity**: Incorrect baseline model outputs are never used as positive training completions; all targets are curated safe refusals or helpful benign educational answers.
