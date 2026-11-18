# Evaluation Benchmark & Metrics

## 1. Primary Metric: Execution Accuracy (EX)

In Text-to-SQL tasks, measuring exact SQL string match (EM) is fundamentally flawed because semantically identical queries can use different aliases, table join orders, or syntax variations (e.g. `JOIN` vs `INNER JOIN`, `WHERE a IN (...)` vs `WHERE EXISTS (...)`).

Therefore, **Execution Accuracy (EX)** serves as the primary evaluation metric:

$$\text{Execution Accuracy (EX)} = \frac{\sum_{i=1}^{N} \mathbb{I}(\text{Result}(\hat{y}_i) \equiv \text{Result}(y_i))}{N} \times 100$$

Where $\text{Result}(q)$ executes query $q$ against the isolated SQLite test database and compares the resulting multiset of tuples against the golden reference output.

## 2. Secondary Metrics

- **Exact Match (EM)**: Structural token equality after keyword uppercase formatting and whitespace normalization.
- **Valid SQL Rate (VSR)**: Percentage of generated outputs that parse into valid SQLite statements without syntax errors.
- **Query Latency (ms)**: Generation and execution latency per question.

## 3. Running Evaluations

```bash
# Evaluate Base Model
python 1_Source/main.py eval --run-name baseline

# Evaluate Fine-Tuned Model with LoRA Adapter
python 1_Source/main.py eval --run-name fine_tuned --adapter 6_Models/adapters/full_lora_run

# Compare Baseline vs Fine-Tuned
python 1_Source/main.py compare --baseline baseline --finetuned fine_tuned
```
Reports are automatically exported to `7_Results/comparisons/` in JSON and Markdown formats.
