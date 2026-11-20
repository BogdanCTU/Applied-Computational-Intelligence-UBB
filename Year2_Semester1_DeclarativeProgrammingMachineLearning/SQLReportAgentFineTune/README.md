# SQLReportAgentFineTune: Independent Text-to-SQL LLM Fine-Tuning Laboratory

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Hardware](https://img.shields.io/badge/Hardware-Apple%20Silicon%20M4%20(16GB)-silver.svg)]()
[![Framework](https://img.shields.io/badge/Framework-Apple%20MLX%200.32-red.svg)](https://github.com/ml-explore/mlx)
[![Base Model](https://img.shields.io/badge/Target%20Model-Qwen2.5--Coder--3B--Instruct-purple.svg)](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct)
[![Method](https://img.shields.io/badge/Method-LoRA%20%2F%20QLoRA-orange.svg)]()

A 100% self-contained, offline-ready laboratory for supervised fine-tuning (SFT) and evaluation of sub-4-billion parameter language models on relational Text-to-SQL tasks. Engineered specifically for native Apple Silicon (M-series unified memory) via Apple's MLX and MLX-LM framework.

---

## 1. Project Overview & Objectives

Small open-source language models (< 4B parameters) frequently struggle with complex SQL generation tasks, producing syntactic errors, hallucinating schema columns, or failing on multi-table joins. 

This project provides a standalone, end-to-end laboratory to:
1. **Acquire & Preprocess Public Benchmarks**: Ingest standard benchmarks (Spider, BIRD subsets) and generate deterministic synthetic schema-aware samples.
2. **Quantized / Low-Rank Adaptation (LoRA / QLoRA)**: Fine-tune `Qwen2.5-Coder-3B-Instruct` natively on Apple Silicon using MLX without CUDA dependencies.
3. **Execution Accuracy (EX) Benchmark**: Evaluate models on dedicated SQLite execution engines, comparing output database state rather than surface string exact matches.
4. **Export & Deployment**: Fuse adapters and export GGUF / MLX models for downstream local deployment.

---

## 2. System Architecture

```text
SQLReportAgentFineTune/
│
├── 1_Source/          # Core Python modules, configuration, CLI & orchestration
│   ├── app/           # Domain subpackages (models, datasets, training, evaluation, inference)
│   ├── config/        # YAML configurations for hardware, LoRA hyperparameters, and benchmarks
│   ├── scripts/       # Automation scripts (env check, dataset download, pilot training)
│   ├── cli/           # Interactive terminal interface
│   └── main.py        # Master entrypoint
│
├── 2_Database/        # Independent data storage
│   ├── raw/           # Raw benchmark downloads (Spider, BIRD)
│   ├── processed/     # Formatted JSONL splits (train, valid, test)
│   ├── schemas/       # DDL and schema definitions
│   └── synthetic/     # Generated edge-case SQL pairs
│
├── 3_Tests/           # Automated verification suite (unit, integration, training)
├── 4_Deploy/          # Shell automation scripts (setup, train, evaluate)
├── 5_Documentation/   # Technical specifications, dataset documentation, model cards
├── 6_Models/          # Pretrained weights, LoRA adapters, checkpoints, and fused exports
├── 7_Results/         # Baseline vs fine-tuned comparative evaluation metrics
└── 8_Logs/            # Detailed training and evaluation logs
```

---

## 3. Hardware & Environment Specifications

- **Platform**: Apple MacBook Air M4 (10 cores: 4P + 6E)
- **Unified Memory**: 16 GB Unified Architecture
- **OS**: macOS Darwin ARM64
- **Runtime**: Python 3.13 native ARM64
- **Acceleration**: Apple Metal (`mlx.core.default_device() -> gpu:0`)
- **Primary Framework**: MLX (`mlx`, `mlx-lm`, `mlx-metal`)

---

## 4. Quick Start

### 4.1 Verify Environment
```bash
python 1_Source/scripts/verify_env.py
```

### 4.2 Run Test Suite
```bash
pytest 3_Tests
```
