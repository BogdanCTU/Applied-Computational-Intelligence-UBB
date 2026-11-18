# Datasets Specification & Acquisition

## 1. Public Benchmark Sources

The fine-tuning laboratory integrates standard, authoritative Text-to-SQL benchmarks:

1. **Yale Spider Benchmark**:
   - Official Source: [Yale LILY Lab Spider](https://yale-lily.github.io/spider)
   - Characteristics: Complex cross-domain SQLite databases with nested queries, joins, and aggregations.
   - Databases included in bundled suite: `concert_singer`, `flight_2`, `world_1`.

2. **BIRD Benchmark**:
   - Official Source: [BIRD Bench](https://bird-bench.github.io/)
   - Focus: Real-world, large-scale enterprise databases with business logic and domain knowledge.
   - Bundled suite: `financial` domain.

3. **Deterministic Synthetic Generation**:
   - Generated internally in `2_Database/synthetic/`
   - Domains: `retail_analytics`, `hospital_management`
   - Purpose: Specifically targets multi-table join column ambiguity (2-way, 3-way, 4-way joins), date arithmetic (`strftime('%Y-%m', date)`), and NULL edge-cases.

## 2. Leakage Prevention & Data Splitting

- **Schema-Aware Partitioning**: Evaluation test splits are strictly separated to evaluate zero-shot database generalization.
- **Split Distribution**:
  - `train.jsonl` (85%): Supervised fine-tuning examples.
  - `valid.jsonl` (10%): Evaluation checkpoints during training steps.
  - `test.jsonl` (5%): Unseen hold-out benchmark test set.

## 3. Training Format (ChatML)

Each record in `2_Database/processed/*.jsonl` is formatted as standard Qwen/ChatML messages:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a specialized Text-to-SQL AI..."
    },
    {
      "role": "user",
      "content": "Database Schema:\n...\n\nUser Question:\nWhich product category generated the highest profit?\n\nGenerate the SQLite query to answer the question."
    },
    {
      "role": "assistant",
      "content": "```sql\nSELECT categories.category_name, SUM(...) ...\n```"
    }
  ]
}
```
