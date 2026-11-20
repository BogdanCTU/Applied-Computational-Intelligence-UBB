# Model Card: Qwen2.5-Coder-3B-Instruct (SQL Fine-Tuned)

## 1. Model Details

- **Base Architecture**: Qwen 2.5 Coder
- **Parameter Count**: 3.09 Billion Parameters
- **Pretrained Identifier**: `mlx-community/Qwen2.5-Coder-3B-Instruct-4bit` (Hugging Face)
- **Target Task**: Supervised Text-to-SQL for Relational SQLite
- **Fine-Tuning Method**: Parameter-Efficient LoRA / QLoRA (Rank = 8, Alpha = 16)
- **Quantization**: 4-bit Group Quantization (MLX Native)
- **Context Window**: 32,768 tokens

## 2. Intended Use & Capabilities

- Generates safe, read-only SQLite `SELECT` and `WITH` statements from natural language.
- Resolves complex relational schemas including 3-way and 4-way joins, primary/foreign key navigation, date formatting (`strftime`), group-by aggregations, and NULL handling.
- Optimized for offline execution on Apple Silicon MacBooks (M1-M4) with 16 GB unified RAM.

## 3. Training & Inference Constraints

- Out-of-Scope: Destructive mutations (`DROP`, `DELETE`, `UPDATE`, `ALTER`).
- Safety Authorizer: All queries are executed in a read-only SQLite transaction handle.
