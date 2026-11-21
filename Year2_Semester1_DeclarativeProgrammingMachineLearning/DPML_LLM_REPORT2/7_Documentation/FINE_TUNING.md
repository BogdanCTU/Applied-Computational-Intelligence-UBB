# Fine-Tuning & Bidirectional Ollama <-> MLX-LM Conversion

## Architecture & Quantization Verification

Ollama serves `qwen3.5:4b` using its `mlx` runner with `safetensors` blobs quantized in `nvfp4` (`group_size=16`, 4-bit weights stored as `U32` with `U8` scales under `<tensor>.weight.scale`). `mlx-lm 0.32.2` natively supports `qwen3_5` (`Qwen3_5ForConditionalGeneration`) and `nvfp4` (`QuantizedLinear`), enabling native LoRA adaptation and fusion on Apple Silicon M4.

## Conversion Pipeline (`OllamaMLXConverter`)

1. **Ollama -> MLX-LM (`export_ollama_to_mlx`)**:
   - Reads `~/.ollama/models/manifests/registry.ollama.ai/library/qwen3.5/4b`.
   - Copies tokenizer, chat template, and config JSONs; injects `"quantization": {"group_size": 16, "bits": 4, "mode": "nvfp4"}` into `config.json`.
   - Translates `*.weight.scale` keys into MLX `*.scales` keys and packs `language_model.*` tensors into `model.safetensors`.
2. **MLX-LM LoRA Fine-Tuning & Fusion**:
   - Runs `mlx_lm lora` (`batch_size=1`, `num_layers=4`, `max_seq_length=512`, `lora_rank=8`, `grad_checkpoint=True`, `mask_prompt=True`) sized comfortably for 16 GB unified memory.
   - Runs `mlx_lm fuse` to merge trained LoRA updates back into `nvfp4` layers.
3. **MLX-LM -> Ollama (`export_fused_mlx_to_ollama`)**:
   - Compares every fused `language_model.*` layer against the original Ollama blob, re-serializes only modified layers in Ollama's exact single-tensor `nvfp4` format (`{"group_size": "16", "quant_type": "nvfp4"}`), preserves content-addressed base blobs for untouched layers and vision tower, writes the `4b-safety` manifest, and verifies `ollama show qwen3.5:4b-safety` + live `/api/chat`.
