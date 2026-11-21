# Local LLM Adversarial Safety Testing, Fine-Tuning & Mitigation Platform

A locally executable academic AI safety research platform built for Apple Silicon (`arm64`, 16 GB unified memory) using Python 3.13, Ollama, SQLite/SQLAlchemy, and MLX-LM.

## Key Capabilities

1. **Adversarial Suite Generation (`1_Penetration/`)**: 1,200 reproducible test cases across 12 risk categories (100 per category) and 14 attack patterns, strictly partitioned by disjoint `template_family` clusters (`train_pool`, `val_pool`, `held_out_eval`) with TF-IDF and entropy diversity verification.
2. **Controlled Agent Sandbox (`4_Source/execution/agent_sandbox.py`)**: Simulated local tool registry with 6 synthetic tools, role allowlists, argument schema validation, and read-only SQL guards separating model refusal evaluation from deterministic boundary enforcement.
3. **Multi-Dimensional Safety Evaluator (`4_Source/safety_evaluation/`)**: Transparent rule-based classifier producing 6 discrete outcome classes and 7 safety dimension flags without relying on external judge APIs, plus manual academic review annotations.
4. **Native Apple Silicon LoRA Fine-Tuning & Bidirectional Ollama Conversion (`2_FineTune/`, `4_Source/fine_tuning/`)**: Reconstructs an MLX-LM `nvfp4` checkpoint from Ollama's local `qwen3.5:4b` blobs, fine-tunes LoRA adapters with prompt masking and gradient checkpointing, fuses adapters, exports modified blobs back to Ollama (`qwen3.5:4b-safety`), and verifies live inference.
5. **Statistical Comparison & Academic Reporting (`3_Comparative_Analysis/`, `9_Results/`)**: Paired McNemar tests, 95% Wilson confidence intervals, Benjamini-Hochberg FDR and Holm-Bonferroni corrections, Wilcoxon latency tests, 300-DPI PNG charts, SQLite/JSONL/CSV/Parquet exports, and Markdown/PDF academic reports.

## Quick Start

```bash
python -m pip install -r requirements.txt
python -m source.cli check-environment
python -m source.cli generate-tests
python -m source.cli run-baseline
python -m source.cli analyze-baseline
python -m source.cli generate-mitigation-data
python -m source.cli train
python -m source.cli run-mitigated
python -m source.cli compare
python -m source.cli report
pytest 6_Tests/
```
