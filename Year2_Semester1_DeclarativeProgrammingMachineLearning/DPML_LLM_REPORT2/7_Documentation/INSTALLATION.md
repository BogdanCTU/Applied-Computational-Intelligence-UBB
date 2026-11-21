# Installation & Environment Guide

## Hardware & OS Requirements

- Apple Silicon Mac (verified on Apple MacBook Air M4, `arm64`, 16 GB unified memory).
- macOS with at least 15 GB free disk space for weights, adapters, and exports.
- Python 3.13 (`3.13.16` verified).
- Local Ollama (`0.40.17` verified) listening on `http://127.0.0.1:11434` with `qwen3.5:4b` pulled locally.

## Setup Steps

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e . --no-build-isolation --no-deps
python -m source.cli check-environment
```

## Verification

Confirm that `check-environment` reports:
- `ollama_reachable: true`
- `baseline_model.available: true` (`qwen3.5:4b`)
- `mlx_available: true`
- `sqlite_tables` initialized (16 tables).
