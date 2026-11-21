# Academic Methodology & Reproducibility

## Reproducibility Controls

- Fixed random seed (`seed=42`) across dataset generation, LoRA shuffling, and Ollama decoding (`temperature=0.0`).
- Immutable raw payloads archived in `1_Penetration/04_Raw_Results/`, `3_Comparative_Analysis/02_Mitigated/`, and SQLite `model_responses`.
- Versioned system prompt (`sys_safety_v1.0`), dataset version (`v1.0`), and evaluator rule version (`v1.0`).
- Automated hot backups (`5_Data/backups/`) and multi-format exports (`JSONL`, `JSON`, `CSV`, `Parquet`).

## Academic Integrity

- All metrics, p-values, loss trajectories, and qualitative failure excerpts are generated strictly from empirical executions stored in SQLite.
- Statistical significance ($p_{\text{FDR}} < 0.05$) is explicitly distinguished from practical significance ($\ge 5.0$ percentage-point failure reduction).
