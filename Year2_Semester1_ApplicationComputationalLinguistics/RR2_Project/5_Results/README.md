# 5_Results — Validated Scientific Evaluation Results, Comparisons, Figures, and Manifests

## 1. Overview

This directory contains only the validated, final scientific evaluation tables, 17-dimension intermediate comparisons, publication figures, and cryptographic verification manifests supporting the conclusions of the Agent-OM replication and $\le 4\text{B}$ local model adaptation study.

All intermediate execution logs, per-run candidate JSONs, and raw step CSVs are stored separately in `4_Temporary/`.

---

## 2. Directory Structure

```text
5_Results/
├── final/
│   ├── phase5_benchmark_summary.csv
│   ├── phase5_benchmark_summary.json
│   ├── phase5_6variants_all_experiments.csv
│   ├── phase5_stage_attrition_comparison.csv
│   └── threshold_sensitivity.csv
├── scientific_evaluation/
│   ├── phase6_small_model_results.csv
│   └── phase6_small_model_results.json
├── comparisons/
│   ├── phase3_summary_table.csv
│   ├── phase3_17point_upstream_lite_vs_local_parity.json
│   ├── phase3_17point_upstream_lite_vs_local_adapted.json
│   ├── phase3_17point_local_parity_vs_local_adapted.json
│   ├── phase3_17point_upstream_gpt4o_vs_local_adapted.json
│   ├── phase3_17point_upstream_gpt4o_vs_upstream_lite.json
│   └── phase5_router_overhead.json
├── figures/
│   ├── prf1_comparison.png
│   ├── pr_scatter_isof1.png
│   ├── runtime_and_llm_calls.png
│   ├── stage_attrition_tp.png
│   └── threshold_sensitivity_local_adapted.png
├── manifests/
│   ├── implementation_manifest.json
│   ├── ollama_model_inventory.json
│   ├── environment_manifest.json
│   ├── workspace_integrity_manifest.json
│   ├── dependency_audit.json
│   ├── historical_output_baseline_sha256.json
│   ├── historical_docs_baseline_sha256.json
│   ├── original_repo_baseline_sha256.json
│   ├── llama3_8b_verification.json
│   ├── postgres_phase1_verification.json
│   └── venv_upstream_packages.json
└── README.md
```

---

## 3. Provenance and Description of Final Results

### 3.1. Final Replication Benchmark Results (`5_Results/final/`)

| File | Generating Script & Experiment IDs | Models & Configuration | Classification | Complete Intermediate Data Location |
| :--- | :--- | :--- | :---: | :--- |
| `final/phase5_benchmark_summary.{csv,json}` | `scripts/generate_replication_comparisons_and_charts.py` aggregating `ref_upstream_gpt4o_cmt_confof`, `phase1_cmt_confof_agent_om_lite_v1`, `phase5_expC_local_parity_run1`..`run3`, and `phase5_expD_local_adapted_run2` | Compares GPT-4o (`1536`-dim), Upstream Agent-OM-Lite (`llama3:8b` `4096`-dim), Local Parity (`llama3:8b` `4096`-dim, 3 repeated runs), and Local Adapted (`nomic-embed-text` `768`-dim) | Historical Reference + Newly Reproduced & Verified | `4_Temporary/replication_runs/phase1_*`, `4_Temporary/replication_runs/phase5_*` |
| `final/phase5_6variants_all_experiments.csv` | `scripts/generate_replication_comparisons_and_charts.py` | Evaluates all 6 alignment stages (`s2t_no_val`, `t2s_no_val`, `merged_no_val`, `s2t_val`, `t2s_val`, `final_merged`) across Experiments A, B, C, and D | Newly Reproduced & Verified | `4_Temporary/replication_runs/*/metrics_6variants.csv` |
| `final/phase5_stage_attrition_comparison.csv` | `scripts/generate_replication_comparisons_and_charts.py` | Tracks candidate count and True Positive retention across retrieval, RRF, validation, and reciprocal merger stages | Newly Reproduced & Verified | `4_Temporary/replication_runs/*/stage_attrition.json` |
| `final/threshold_sensitivity.csv` | `scripts/generate_replication_comparisons_and_charts.py` (`_compute_threshold_sweep_on_db`) | Cosine threshold sweep across $\tau \in [0.50, 0.95]$ on `agent_om_adapted` (`nomic-embed-text` `768`-dim) | Independently Verified | `4_Temporary/csv/step7a_threshold_sensitivity.csv` |

### 3.2. Phase 6 Small-Model ($\le 4\text{B}$) Scientific Evaluation (`5_Results/scientific_evaluation/`)

| File | Generating Script & Experiment IDs | Models & Configuration | Classification | Complete Intermediate Data Location |
| :--- | :--- | :--- | :---: | :--- |
| `scientific_evaluation/phase6_small_model_results.{csv,json}` | `scripts/run_phase6_small_model_evaluation.py` (`phase6_E1_qwen25_3b_baseline_run1`..`run3`, `phase6_E2_qwen25_3b_optimized_prompt`, `phase6_E3_qwen25_3b_router_det_4ent`, `phase6_E4_qwen25_3b_router_llm_4ent`, `phase6_E5_qwen25_3b_mxbai_1024d`, `phase6_E6_qwen25_3b_tau085`, `phase6_E6_qwen25_3b_tau0875`, `phase6_E7_deepseek_r1_15b_full`) | Strictly verified $\le 4.0\text{B}$ models: `qwen2.5:3b` (`3,085,938,688` params) and `deepseek-r1:1.5b` (`1,777,088,000` params) paired with `nomic-embed-text` (`768`-dim) and `mxbai-embed-large` (`1024`-dim) | Newly Generated & Independently Verified | `4_Temporary/replication_runs/phase6_*` |

### 3.3. Phase 3 17-Point Intermediate Comparisons (`5_Results/comparisons/`)

| File | Description | Classification |
| :--- | :--- | :---: |
| `comparisons/phase3_summary_table.csv` | Summary table across all 17 intermediate comparison dimensions for 5 experiment pairs (Entity Jaccard, `entity_id` match %, syntactic exact match %, lexical/semantic word Jaccard, embedding dimensions, RRF agreement, validation agreement, and final merged Jaccard). | Independently Verified |
| `comparisons/phase3_17point_*.json` | Detailed 17-dimension JSON comparison reports generated by `1_Source/evaluation/comparator.py` (`compare_two_runs_17_points`). | Independently Verified |
| `comparisons/phase5_router_overhead.json` | Telemetry comparison between deterministic tool orchestration and LLM JSON tool routing (`tool_routing_mode="llm_json"`). | Independently Verified |

### 3.4. Publication Figures (`5_Results/figures/`)

1. `prf1_comparison.png`: Grouped bar chart of Precision, Recall, and $F_1$ across Experiments A, B, C, and D.
2. `pr_scatter_isof1.png`: Precision vs. Recall scatter plot with iso-$F_1$ contours.
3. `runtime_and_llm_calls.png`: Execution runtime and total LLM invocation count comparison.
4. `stage_attrition_tp.png`: Stage-by-stage candidate and True Positive attrition curve.
5. `threshold_sensitivity_local_adapted.png`: Cosine similarity threshold sensitivity curve ($\tau \in [0.50, 0.95]$).
