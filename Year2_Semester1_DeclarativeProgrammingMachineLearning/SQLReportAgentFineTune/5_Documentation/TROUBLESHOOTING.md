# Troubleshooting & Operations FAQ

### 1. Memory Allocation Issues (OutOfMemoryError)
- **Symptom**: Process killed by macOS during large model loads or long training sequences.
- **Remedy**:
  1. Reduce `--batch-size` from 2 to 1 in `1_Source/config/default_config.yaml`.
  2. Enable gradient checkpointing: `--grad-checkpoint`.
  3. Ensure 4-bit model quantization (`mlx-community/Qwen2.5-Coder-3B-Instruct-4bit`) is utilized.

### 2. Missing Database File
- **Symptom**: `FileNotFoundError: Database file not found: ...` during evaluation.
- **Remedy**: Run `python 1_Source/scripts/acquire_datasets.py` to regenerate all SQLite test databases.

### 3. MLX GPU Not Detected
- **Symptom**: `MLX Device: cpu` instead of `Device(gpu, 0)`.
- **Remedy**: Ensure the Python environment is native ARM64 (`python -c "import platform; print(platform.machine())"` outputs `arm64`, not `x86_64` under Rosetta).

### 4. Query Timeout
- **Symptom**: Evaluation reports query execution timeout.
- **Remedy**: Increase `timeout_seconds` in `EvaluationConfig` or check if the generated query contains Cartesian product (`CROSS JOIN`) on unindexed tables.
