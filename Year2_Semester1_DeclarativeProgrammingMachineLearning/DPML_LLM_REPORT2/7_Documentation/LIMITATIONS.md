# Known Limitations & Threat Validity

1. **Rule-Based Evaluator Scope**: The deterministic rule-based evaluator avoids external LLM-judge circularity and external API calls, but heuristic patterns may misclassify nuanced implicit refusals or subtle partial compliance; manual academic review (`reviewer_annotations`) mitigates this risk.
2. **Quantized LoRA Adaptation**: Training adapts 4-bit `nvfp4` frozen weights via LoRA on the upper `num_layers=4` decoder layers with `max_sequence_length=512` to fit safely within 16 GB unified memory; adapting deeper layers or longer sequences requires higher memory or more iterations.
3. **Greedy Decoding Baseline**: Evaluations run at `temperature=0.0` for deterministic paired comparison; stochastic sampling (`temperature > 0`) could expose rare tail-risk failures not seen under greedy decoding.
4. **Synthetic Sandbox Scope**: Tool-abuse tests operate strictly over synthetic local fixtures (`SYNTHETIC_TABLES`, `SYNTHETIC_DOCUMENTS`), measuring model boundary behavior rather than production database engines.
5. **Vision Tower Excluded from LoRA**: `qwen3_5`'s text decoder layers are fine-tuned while the original `vision_tower` blobs are preserved unchanged in the exported Ollama manifest.
