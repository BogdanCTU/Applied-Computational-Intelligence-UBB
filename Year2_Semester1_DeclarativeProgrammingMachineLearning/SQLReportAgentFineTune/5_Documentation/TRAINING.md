# LoRA / QLoRA Training Guide

## 1. Apple Silicon Hardware Configuration

- **Machine**: MacBook Air M4 (16 GB Unified Memory)
- **Framework**: Apple MLX (`mlx-lm`)
- **Acceleration**: Metal GPU (`Device(gpu, 0)`)
- **Quantization Mode**: 4-bit QLoRA or 8-bit / BF16 LoRA
- **Peak Memory During Training**: ~2.4 GB Unified Memory (well within 16 GB envelope)

## 2. Hyperparameters

| Hyperparameter | Value | Description |
| :--- | :---: | :--- |
| **Fine-Tune Type** | `lora` | Low-Rank Adaptation |
| **LoRA Rank ($r$)** | `8` | Rank of low-rank matrices |
| **LoRA Alpha ($\alpha$)** | `16.0` | Scaling factor ($\alpha / r = 2.0$) |
| **LoRA Dropout** | `0.05` | Regularization dropout |
| **Num Layers** | `16` | Top transformer layers adapted |
| **Learning Rate** | `1e-4` | AdamW optimizer learning rate |
| **Batch Size** | `2` | Minibatch size per iteration |
| **Gradient Accumulation** | `2` | Effective batch size = 4 |
| **Gradient Checkpointing** | `True` | Trades compute for memory efficiency |
| **Max Sequence Length** | `2048` | Covers detailed schemas and user queries |
| **Mask Prompt** | `True` | Computes loss only on assistant SQL tokens |

## 3. Training Execution

### 3.1 Pilot Run (10 Iterations)
Used for rapid environment and loss curve verification:
```bash
python 1_Source/scripts/run_pilot_train.py
```

### 3.2 Full Production Run (600 Iterations)
```bash
python 1_Source/main.py train --run-name full_lora_run --iters 600
```
Log files are written in real-time to `8_Logs/training_{run_name}.log`. Checkpoints and adapter weights are stored under `6_Models/adapters/{run_name}/`.
