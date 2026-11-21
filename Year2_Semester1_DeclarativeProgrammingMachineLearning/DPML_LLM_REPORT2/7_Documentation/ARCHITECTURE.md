# System Architecture

## Overview

The **Local LLM Adversarial Safety Testing, Fine-Tuning & Mitigation Platform** is a modular, offline-capable academic research framework built in Python 3.13 for Apple Silicon (`arm64`, 16 GB unified memory). All inference, evaluation, fine-tuning, persistence, and reporting execute locally via Ollama and Apple MLX.

## Layered Module Architecture (`4_Source/`)

1. **Configuration & Validation (`4_Source/config/settings.py`)**: Pydantic v2 validation of `config.yaml` enforcing local-only endpoints (`127.0.0.1`/`localhost`) and runtime parameter bounds.
2. **Ollama Interface & Model Verification (`4_Source/ollama/`, `4_Source/models/`)**: Async/sync HTTP client with retries, rate limiting, `think` control, and `/api/tags` + `/api/show` verification of `qwen3.5:4b` and `qwen3.5:4b-safety`.
3. **Adversarial Suite & Taxonomy (`4_Source/penetration/`, `4_Source/test_generation/`)**: 12 risk categories, 120 subcategories, 14 attack patterns, deterministic 1,200-case generator, and TF-IDF + Shannon-entropy diversity reporting.
4. **Controlled Execution & Sandbox (`4_Source/execution/`)**: Single/multi-turn penetration runner and `AgentToolSandbox` with 6 synthetic tools, role allowlists, argument validation, and read-only SQL guards.
5. **Multi-Dimensional Safety Evaluation (`4_Source/safety_evaluation/`, `4_Source/classification/`)**: Transparent rule-and-rubric classifier over 6 outcome classes and 7 safety criteria, plus manual academic review persistence (`reviewer_annotations`).
6. **Persistence & Export (`4_Source/storage/`)**: Transaction-managed SQLite ORM (`5_Data/sqlite/research.db`) covering 16 relational tables, hot backups (`5_Data/backups/`), and multi-format export (`JSONL`, `JSON`, `CSV`, `Parquet`).
7. **Fine-Tuning & Conversion (`4_Source/fine_tuning/`, `4_Source/inference/`)**: Leakage-free dataset builder, bidirectional Ollama `nvfp4` ↔ MLX-LM safetensors converter (`OllamaMLXConverter`), MLX-LM LoRA trainer, weight fusion, and live model verification.
8. **Analytics & Academic Reporting (`4_Source/analytics/`, `4_Source/reporting/`)**: Safety metrics, Wilson CIs, paired McNemar tests, FDR/Holm-Bonferroni corrections, Wilcoxon latency tests, 300-DPI PNG charts, and ReportLab PDF + Markdown reports.
9. **CLI (`4_Source/cli.py`)**: Unified entrypoint (`python -m source.cli <command>`).
