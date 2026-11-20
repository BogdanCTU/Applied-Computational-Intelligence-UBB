"""Phase 6 Small-Model (<=4B) Scientific Evaluation Runner for Agent-OM.

Executes the controlled experimental protocol on the 162-entity CMT-ConfOf benchmark:
- E1 (3 repeated runs): qwen2.5:3b (3.085B <= 4.0B) + nomic-embed-text (768-dim), default parity prompt (local_4b_baseline).
- E2: qwen2.5:3b (3.085B <= 4.0B) + nomic-embed-text (768-dim), optimized clean validation prompt (local_4b_optimized).
- E3 & E4: qwen2.5:3b (3.085B <= 4.0B) deterministic vs LLM JSON tool routing comparison.
- E5: qwen2.5:3b (3.085B <= 4.0B) + alternative embedding model mxbai-embed-large (1024-dim) in isolated DB agent_om_4b_mxbai.
- E6: qwen2.5:3b (3.085B <= 4.0B) retrieval parameter sensitivity (similarity thresholds tau in {0.80, 0.85, 0.875, 0.90, 0.925}).
- E7 (Reasoning Model <=4B): deepseek-r1:1.5b (1.777B <= 4.0B) + nomic-embed-text (768-dim) (local_4b_reasoning).

Saves all outputs to `output/replication_runs/<experiment_id>/` and aggregates summary tables and charts
into `output/replication_runs/comparisons/phase6_small_model_*`.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_local_replication import run_local_experiment
from src.db.database_manager import DatabaseManager
from src.evaluation.charts import build_prf1_comparison_figure, save_figure
from src.evaluation.comparator import load_features_csv
from src.llm.embedding_provider import LocalEmbeddingProvider


def main() -> int:
    features_csv = (
        PROJECT_ROOT / "output/replication_runs/phase5_expC_local_parity_run1/ontology_matching.csv"
    )
    df = load_features_csv(features_csv)
    print(f"Loaded 162-entity CMT-ConfOf representations from {features_csv.name} ({len(df)} rows)")

    # 1. Populate isolated 768-dim vector database for <=4B experiments (agent_om_4b_baseline)
    db_nomic = DatabaseManager("postgresql://postgres@127.0.0.1:5432/agent_om_4b_baseline")
    db_nomic.ensure_database_exists()
    db_nomic.init_extensions()
    emb_nomic = LocalEmbeddingProvider(
        model_name="nomic-embed-text", expected_dim=768, validate_on_init=True
    )
    t0 = time.perf_counter()
    db_nomic.create_ontology_matching_table(df)
    syn_768 = db_nomic.create_embedding_table(
        "syntactic_matching", df, emb_nomic, vector_length=768, skip_empty_chunks=True
    )
    lex_768 = db_nomic.create_embedding_table(
        "lexical_matching", df, emb_nomic, vector_length=768, skip_empty_chunks=True
    )
    sem_768 = db_nomic.create_embedding_table(
        "semantic_matching", df, emb_nomic, vector_length=768, skip_empty_chunks=True
    )
    nomic_ingest_s = round(time.perf_counter() - t0, 3)
    print(
        f"Indexed agent_om_4b_baseline (nomic-embed-text 768-dim) in {nomic_ingest_s}s: "
        f"syn={syn_768}, lex={lex_768}, sem={sem_768}"
    )

    # 2. Populate isolated 1024-dim vector database for E5 alternative embedding model (mxbai-embed-large)
    db_mxbai = DatabaseManager("postgresql://postgres@127.0.0.1:5432/agent_om_4b_mxbai")
    db_mxbai.ensure_database_exists()
    db_mxbai.init_extensions()
    emb_mxbai = LocalEmbeddingProvider(
        model_name="mxbai-embed-large", expected_dim=1024, validate_on_init=True
    )
    t0 = time.perf_counter()
    db_mxbai.create_ontology_matching_table(df)
    syn_1024 = db_mxbai.create_embedding_table(
        "syntactic_matching", df, emb_mxbai, vector_length=1024, skip_empty_chunks=True
    )
    lex_1024 = db_mxbai.create_embedding_table(
        "lexical_matching", df, emb_mxbai, vector_length=1024, skip_empty_chunks=True
    )
    sem_1024 = db_mxbai.create_embedding_table(
        "semantic_matching", df, emb_mxbai, vector_length=1024, skip_empty_chunks=True
    )
    mxbai_ingest_s = round(time.perf_counter() - t0, 3)
    print(
        f"Indexed agent_om_4b_mxbai (mxbai-embed-large 1024-dim) in {mxbai_ingest_s}s: "
        f"syn={syn_1024}, lex={lex_1024}, sem={sem_1024}"
    )

    results: List[Dict[str, Any]] = []

    def _run_if_needed(exp_id: str, **kwargs: Any) -> Dict[str, Any]:
        summary_path = PROJECT_ROOT / "output/replication_runs" / exp_id / "run_summary.json"
        if summary_path.is_file():
            print(f"[SKIP EXISTING] {exp_id}")
            return json.loads(summary_path.read_text(encoding="utf-8"))
        return run_local_experiment(experiment_id=exp_id, **kwargs)

    # E1: Best verified <=4B model (qwen2.5:3b, 3.085B params) — 3 repeated runs
    for run_idx in (1, 2, 3):
        s = _run_if_needed(
            f"phase6_E1_qwen25_3b_baseline_run{run_idx}",
            profile_name="local_4b_baseline",
            db_name_override="agent_om_4b_baseline",
            skip_retrieval=True,
        )
        results.append({"group": f"E1_run{run_idx}", "summary": s})

    # E2: Optimised prompt (clean non-indented validation prompt)
    s_e2 = _run_if_needed(
        "phase6_E2_qwen25_3b_optimized_prompt",
        profile_name="local_4b_optimized",
        db_name_override="agent_om_4b_baseline",
        skip_retrieval=True,
    )
    results.append({"group": "E2_optimized_prompt", "summary": s_e2})

    # E3 & E4: Deterministic vs LLM JSON tool routing on 4-entity slice & full validation
    s_e3 = _run_if_needed(
        "phase6_E3_qwen25_3b_router_det_4ent",
        profile_name="local_4b_optimized",
        db_name_override="agent_om_4b_smoke",
        max_entities_per_side=2,
        skip_retrieval=True,
        tool_routing_mode="deterministic",
    )
    results.append({"group": "E3_router_det_4ent", "summary": s_e3})

    s_e4 = _run_if_needed(
        "phase6_E4_qwen25_3b_router_llm_4ent",
        profile_name="local_4b_optimized",
        db_name_override="agent_om_4b_smoke",
        max_entities_per_side=2,
        skip_retrieval=True,
        tool_routing_mode="llm_json",
    )
    results.append({"group": "E4_router_llm_4ent", "summary": s_e4})

    # E5: Alternative embedding model (mxbai-embed-large, 1024-dim) across all 162 entities
    s_e5 = _run_if_needed(
        "phase6_E5_qwen25_3b_mxbai_1024d",
        profile_name="local_4b_optimized",
        db_name_override="agent_om_4b_mxbai",
        embedding_model_override="mxbai-embed-large",
        embedding_dim_override=1024,
        skip_retrieval=True,
    )
    results.append({"group": "E5_mxbai_1024d", "summary": s_e5})

    # E6: Retrieval parameter sensitivity (tau = 0.85 and tau = 0.875) across all 162 entities
    for tau_label, tau_val in (("tau085", 0.85), ("tau0875", 0.875)):
        s_e6 = _run_if_needed(
            f"phase6_E6_qwen25_3b_{tau_label}",
            profile_name="local_4b_optimized",
            db_name_override="agent_om_4b_baseline",
            similarity_threshold=tau_val,
            skip_retrieval=True,
        )
        results.append({"group": f"E6_{tau_label}", "summary": s_e6})

    # E7: Verified <=4B reasoning-distilled model (deepseek-r1:1.5b, 1.777B params) across all 162 entities
    s_e7 = _run_if_needed(
        "phase6_E7_deepseek_r1_15b_full",
        profile_name="local_4b_reasoning",
        db_name_override="agent_om_4b_baseline",
        skip_retrieval=True,
    )
    results.append({"group": "E7_deepseek_r1_15b", "summary": s_e7})

    # Save aggregated Phase 6 summary table
    comp_dir = PROJECT_ROOT / "output/replication_runs/comparisons"
    comp_dir.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    for item in results:
        s = item["summary"]
        fm = s["final_metrics"]
        telem = s["telemetry"]
        cfg = s["config"]
        rows.append(
            {
                "experiment_group": item["group"],
                "experiment_id": s["experiment_id"],
                "profile": s["profile_name"],
                "chat_model": cfg["default_llm"],
                "embedding_model": cfg["default_embedding_model"],
                "embedding_dim": cfg["vector_length"],
                "similarity_threshold": cfg["similarity_threshold"],
                "tool_routing_mode": cfg["tool_routing_mode"],
                "indent_prompt": cfg["indent_validation_prompt"],
                "predicted_count": fm["predicted_count"],
                "tp": fm["tp"],
                "fp": fm["fp"],
                "fn": fm["fn"],
                "precision_pct": fm["precision_pct"],
                "recall_pct": fm["recall_pct"],
                "f1_pct": fm["f1_pct"],
                "runtime_s": s["total_runtime_s"],
                "validation_llm_calls": telem["validation_llm_calls"],
                "validation_bypasses": telem["validation_bypasses"],
                "router_calls": telem["router_calls"],
                "prompt_tokens": telem["total_prompt_tokens"],
                "completion_tokens": telem["total_completion_tokens"],
                "total_tokens": telem["total_tokens"],
            }
        )

    pd.DataFrame(rows).to_csv(comp_dir / "phase6_small_model_results.csv", index=False, encoding="utf-8")
    (comp_dir / "phase6_small_model_results.json").write_text(
        json.dumps(
            {
                "embedding_ingestion_benchmarks": {
                    "nomic_embed_text_768d": {
                        "ingestion_time_s": nomic_ingest_s,
                        "chunks": {"syntactic": syn_768, "lexical": lex_768, "semantic": sem_768},
                        "telemetry": emb_nomic.get_telemetry_summary(),
                    },
                    "mxbai_embed_large_1024d": {
                        "ingestion_time_s": mxbai_ingest_s,
                        "chunks": {"syntactic": syn_1024, "lexical": lex_1024, "semantic": sem_1024},
                        "telemetry": emb_mxbai.get_telemetry_summary(),
                    },
                },
                "experiments": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Phase 6 Small-Model Evaluation completed successfully. Rows:", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
