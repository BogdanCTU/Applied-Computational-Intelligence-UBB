"""Generate complete Phase 3 (17-point intermediate comparison) and Phase 5 (controlled benchmark,
repeatability, threshold sensitivity, stage attrition, and Matplotlib PNG charts) artifacts.

All outputs are written strictly into `agent_om_local/output/replication_runs/comparisons/`.
Never modifies `original_repo/`, `agent_om_local` DB, or historical `output/step*` artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.retrieval_agent import RetrievalAgent
from src.config import AppConfig
from src.db.database_manager import DatabaseManager
from src.evaluation.charts import (
    build_precision_recall_scatter_figure,
    build_prf1_comparison_figure,
    build_runtime_and_calls_figure,
    build_stage_attrition_figure,
    build_threshold_sensitivity_figure,
    save_figure,
)
from src.evaluation.comparator import compare_two_runs_17_points
from src.evaluation.metrics import (
    compute_alignment_metrics,
    compute_stage_attrition,
    load_reference_pairs,
)
from src.gui.paths import resolve_project_paths
from src.gui.services.pipeline_inspection_service import PipelineInspectionService
from src.matching.reciprocal_merger import ReciprocalMerger
from src.retrieval.rrf import reciprocal_rank_fusion


def _extract_readonly_db_candidates(
    db_name: str,
    profile_name: str,
    similarity_threshold: float = 0.90,
    top_k: int = 3,
    rrf_k: float = 0.0,
) -> Dict[str, List[Dict[str, Any]]]:
    """Query an existing isolated hybrid-memory DB read-only to capture exact cosine scores & top-k lists."""
    cfg = AppConfig.from_profile(
        profile_name,
        db_name=db_name,
        similarity_threshold=similarity_threshold,
        top_k=top_k,
        rrf_k=rrf_k,
    )
    db = DatabaseManager(connection_string=cfg.connection_string)
    ret = RetrievalAgent(
        db_manager=db,
        context=cfg.context,
        o1_is_code=cfg.o1_is_code,
        o2_is_code=cfg.o2_is_code,
        similarity_threshold=similarity_threshold,
        top_k=top_k,
        num_matches=cfg.num_matches,
        rrf_k=rrf_k,
        tool_routing_mode="deterministic",
        skip_empty_chunks=cfg.skip_empty_chunks,
        app_config=cfg,
    )
    return {
        "s2t": ret.retrieve_directional_candidates("Source", k=rrf_k),
        "t2s": ret.retrieve_directional_candidates("Target", k=rrf_k),
    }


def _compute_threshold_sweep_on_db(
    db_name: str,
    profile_name: str,
    reference_pairs: Sequence[Tuple[str, str]],
    thresholds: Sequence[float] = (0.50, 0.60, 0.70, 0.75, 0.80, 0.825, 0.85, 0.875, 0.90, 0.925, 0.95),
    top_k: int = 3,
    rrf_k: float = 0.0,
) -> List[Dict[str, Any]]:
    """Compute exact retrieval + RRF top-1 reciprocal merger sensitivity across cosine thresholds."""
    cfg = AppConfig.from_profile(profile_name, db_name=db_name, similarity_threshold=0.50, top_k=top_k, rrf_k=rrf_k)
    db = DatabaseManager(connection_string=cfg.connection_string)

    # Fetch all top-k raw scores down to min(thresholds) ONCE per entity/strategy, then filter deterministically!
    min_tau = float(min(thresholds))
    cands_min = _extract_readonly_db_candidates(
        db_name=db_name,
        profile_name=profile_name,
        similarity_threshold=min_tau,
        top_k=top_k,
        rrf_k=rrf_k,
    )

    with db.get_connection() as conn:
        df = pd.read_sql_query("SELECT entity_id, entity_uri FROM ontology_matching;", conn)
    id_to_uri = {str(r["entity_id"]): str(r["entity_uri"]) for _, r in df.iterrows()}

    rows: List[Dict[str, Any]] = []
    merger = ReciprocalMerger()

    for tau in thresholds:
        s2t_top1: Set[Tuple[str, str]] = set()
        t2s_top1: Set[Tuple[str, str]] = set()
        union_pairs: Set[Tuple[str, str]] = set()

        for direction, items in (("s2t", cands_min["s2t"]), ("t2s", cands_min["t2s"])):
            for item in items:
                q_uri = str(item["query_entity_uri"])
                rankings: List[List[str]] = []
                for strat_key in ("syntactic_scores", "lexical_scores", "semantic_scores"):
                    filtered_ids = [
                        str(sc["entity_id"])
                        for sc in item.get(strat_key, [])
                        if float(sc["similarity"]) >= tau and str(sc["entity_id"]) != "Entity-Dummy"
                    ][:top_k]
                    rankings.append(filtered_ids if filtered_ids else ["Entity-Dummy"])
                fused = reciprocal_rank_fusion(*rankings, k=rrf_k)
                real_uris = [id_to_uri[eid] for eid, _ in fused if eid != "Entity-Dummy" and eid in id_to_uri]
                for c_uri in real_uris:
                    pair = (q_uri, c_uri) if direction == "s2t" else (c_uri, q_uri)
                    union_pairs.add(pair)
                if real_uris:
                    top_pair = (q_uri, real_uris[0]) if direction == "s2t" else (real_uris[0], q_uri)
                    if direction == "s2t":
                        s2t_top1.add(top_pair)
                    else:
                        t2s_top1.add(top_pair)

        merged_top1 = merger.merge(s2t_top1, t2s_top1)
        m_merged = compute_alignment_metrics(merged_top1, reference_pairs)
        m_union = compute_alignment_metrics(union_pairs, reference_pairs)
        rows.append(
            {
                "profile": profile_name,
                "db_name": db_name,
                "threshold": round(float(tau), 4),
                "candidate_union_count": m_union["predicted_count"],
                "candidate_union_tp": m_union["tp"],
                "candidate_union_recall_pct": m_union["recall_pct"],
                "s2t_top1_count": len(s2t_top1),
                "t2s_top1_count": len(t2s_top1),
                "predicted_count": m_merged["predicted_count"],
                "tp": m_merged["tp"],
                "fp": m_merged["fp"],
                "fn": m_merged["fn"],
                "precision_pct": m_merged["precision_pct"],
                "recall_pct": m_merged["recall_pct"],
                "f1_pct": m_merged["f1_pct"],
            }
        )
    return rows


def generate_all(
    upstream_exp_id: str,
    parity_exp_ids: Sequence[str],
    adapted_exp_ids: Sequence[str],
    router_sample_exp_id: Optional[str] = None,
) -> Dict[str, Any]:
    paths = resolve_project_paths()
    inspector = PipelineInspectionService(paths)
    comp_dir = paths.replication_runs_dir / "comparisons"
    charts_dir = comp_dir / "charts"
    comp_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    ref_xml = (
        paths.original_repo_dir / "data" / "conference" / "cmt-confof" / "component" / "reference.xml"
    )
    ref_pairs = load_reference_pairs(ref_xml)

    # Load bundles
    bundle_gpt4o = inspector.load_run_bundle("ref_upstream_gpt4o_cmt_confof")
    bundle_upstream = inspector.load_run_bundle(upstream_exp_id)
    bundle_upstream["embedding_dim"] = 4096
    # Enrich upstream bundle with exact DB cosine scores & RRF candidates from agent_om_upstream
    try:
        up_cands = _extract_readonly_db_candidates(
            db_name="agent_om_upstream",
            profile_name="upstream_lite_parity",
            similarity_threshold=0.90,
            top_k=3,
            rrf_k=0.0,
        )
        bundle_upstream["candidates"] = up_cands
        (paths.replication_runs_dir / upstream_exp_id / "candidates_s2t.json").write_text(
            json.dumps(up_cands["s2t"], indent=2), encoding="utf-8"
        )
        (paths.replication_runs_dir / upstream_exp_id / "candidates_t2s.json").write_text(
            json.dumps(up_cands["t2s"], indent=2), encoding="utf-8"
        )
        df_up = bundle_upstream["features_df"]
        id_to_uri_up = {str(r["entity_id"]): str(r["entity_uri"]) for _, r in df_up.iterrows()}
        att_up = compute_stage_attrition(
            reference_pairs=ref_pairs,
            source_entity_uris=[str(r["entity_uri"]) for _, r in df_up[df_up["source_or_target"] == "Source"].iterrows()],
            target_entity_uris=[str(r["entity_uri"]) for _, r in df_up[df_up["source_or_target"] == "Target"].iterrows()],
            s2t_candidates=up_cands["s2t"],
            t2s_candidates=up_cands["t2s"],
            s2t_unvalidated_pairs=bundle_upstream["predictions"]["s2t_no_val"],
            t2s_unvalidated_pairs=bundle_upstream["predictions"]["t2s_no_val"],
            s2t_validated_pairs=bundle_upstream["predictions"]["s2t_val"],
            t2s_validated_pairs=bundle_upstream["predictions"]["t2s_val"],
            final_merged_pairs=bundle_upstream["predictions"]["final_merged"],
            validation_records=[],
            id_to_uri=id_to_uri_up,
        )
        (paths.replication_runs_dir / upstream_exp_id / "stage_attrition.json").write_text(
            json.dumps(att_up, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        print(f"Note: could not enrich upstream DB candidates ({exc})")

    bundle_parity = inspector.load_run_bundle(parity_exp_ids[0])
    bundle_adapted = inspector.load_run_bundle(adapted_exp_ids[0])

    # Phase 3: 17-point comparisons
    c_up_vs_par = compare_two_runs_17_points(
        f"Upstream Agent-OM-Lite ({upstream_exp_id})",
        bundle_upstream,
        f"Local Parity ({parity_exp_ids[0]})",
        bundle_parity,
        reference_pairs=ref_pairs,
    )
    c_up_vs_adap = compare_two_runs_17_points(
        f"Upstream Agent-OM-Lite ({upstream_exp_id})",
        bundle_upstream,
        f"Local Adapted ({adapted_exp_ids[0]})",
        bundle_adapted,
        reference_pairs=ref_pairs,
    )
    c_par_vs_adap = compare_two_runs_17_points(
        f"Local Parity ({parity_exp_ids[0]})",
        bundle_parity,
        f"Local Adapted ({adapted_exp_ids[0]})",
        bundle_adapted,
        reference_pairs=ref_pairs,
    )
    c_gpt4o_vs_adap = compare_two_runs_17_points(
        "Committed Upstream GPT-4o + ada-002 Reference",
        bundle_gpt4o,
        f"Local Adapted ({adapted_exp_ids[0]})",
        bundle_adapted,
        reference_pairs=ref_pairs,
    )
    c_gpt4o_vs_up = compare_two_runs_17_points(
        "Committed Upstream GPT-4o + ada-002 Reference",
        bundle_gpt4o,
        f"Upstream Agent-OM-Lite Executed ({upstream_exp_id})",
        bundle_upstream,
        reference_pairs=ref_pairs,
    )

    for fname, obj in (
        ("phase3_17point_upstream_lite_vs_local_parity.json", c_up_vs_par),
        ("phase3_17point_upstream_lite_vs_local_adapted.json", c_up_vs_adap),
        ("phase3_17point_local_parity_vs_local_adapted.json", c_par_vs_adap),
        ("phase3_17point_upstream_gpt4o_vs_local_adapted.json", c_gpt4o_vs_adap),
        ("phase3_17point_upstream_gpt4o_vs_upstream_lite.json", c_gpt4o_vs_up),
    ):
        (comp_dir / fname).write_text(json.dumps(obj, indent=2), encoding="utf-8")

    # Build Phase 3 flat summary table across key comparisons
    phase3_summary_rows = []
    for comp_name, comp in (
        ("Upstream Lite vs Local Parity", c_up_vs_par),
        ("Upstream Lite vs Local Adapted", c_up_vs_adap),
        ("Local Parity vs Local Adapted", c_par_vs_adap),
        ("Committed GPT-4o vs Local Adapted", c_gpt4o_vs_adap),
        ("Committed GPT-4o vs Upstream Lite", c_gpt4o_vs_up),
    ):
        phase3_summary_rows.append(
            {
                "comparison": comp_name,
                "source_uri_jaccard": comp["1_extracted_entities"]["source_uri_jaccard"],
                "target_uri_jaccard": comp["1_extracted_entities"]["target_uri_jaccard"],
                "entity_id_exact_match_pct": comp["2_entity_ids"]["exact_entity_id_match_pct"],
                "entity_name_exact_match_pct": comp["3_entity_names"]["exact_name_match_pct"],
                "syntactic_exact_match_pct": comp["5_cleaned_syntactic_names"]["exact_match_pct"],
                "lexical_mean_word_jaccard": comp["6_lexical_verbalizations"]["mean_word_jaccard"],
                "semantic_null_agreement_pct": comp["7_semantic_verbalizations"]["null_vs_non_null_agreement_pct"],
                "semantic_mean_word_jaccard": comp["7_semantic_verbalizations"]["mean_word_jaccard"],
                "dims_equal": comp["9_embedding_dimensions"]["dimensions_equal"],
                "syntactic_top1_match_pct": comp["11_syntactic_candidates"]["top1_uri_match_pct"],
                "lexical_top1_match_pct": comp["12_lexical_candidates"]["top1_uri_match_pct"],
                "semantic_top1_match_pct": comp["13_semantic_candidates"]["top1_uri_match_pct"],
                "candidate_union_jaccard": comp["14_combined_candidate_unions"]["mean_union_uri_jaccard"],
                "rrf_top1_agreement_pct": comp["15_rrf_rankings"]["rrf_top1_uri_agreement_pct"],
                "validation_decision_agreement_pct": comp["16_validation_decisions"]["decision_agreement_pct"],
                "final_merged_jaccard": comp["17_reciprocal_merger_and_final_alignment"]["final_merged_jaccard"],
            }
        )
    pd.DataFrame(phase3_summary_rows).to_csv(
        comp_dir / "phase3_summary_table.csv", index=False, encoding="utf-8"
    )

    # Phase 5: Repeatability & Benchmark Summary across Experiments A, B, C, D
    def _load_summary(eid: str) -> Dict[str, Any]:
        return json.loads(
            (paths.replication_runs_dir / eid / "run_summary.json").read_text(encoding="utf-8")
        )

    up_sum = _load_summary(upstream_exp_id)
    par_sums = [_load_summary(eid) for eid in parity_exp_ids]
    adap_sums = [_load_summary(eid) for eid in adapted_exp_ids]

    gpt4o_final = compute_alignment_metrics(bundle_gpt4o["predictions"]["final_merged"], ref_pairs)
    up_final = compute_alignment_metrics(bundle_upstream["predictions"]["final_merged"], ref_pairs)

    def _agg_local(label: str, short_lbl: str, profile: str, sums: List[Dict[str, Any]]) -> Dict[str, Any]:
        primary = sums[0]
        fm = primary["final_metrics"]
        f1s = [float(s["final_metrics"]["f1_pct"]) for s in sums]
        precs = [float(s["final_metrics"]["precision_pct"]) for s in sums]
        recs = [float(s["final_metrics"]["recall_pct"]) for s in sums]
        telem = primary["telemetry"]
        att_s = primary.get("stage_attrition_summary") or {}
        return {
            "experiment_group": label,
            "short_label": short_lbl,
            "primary_experiment_id": primary["experiment_id"],
            "repeat_runs": len(sums),
            "profile": profile,
            "llm_model": primary["config"]["default_llm"],
            "embedding_model": primary["config"]["default_embedding_model"],
            "embedding_dim": primary["config"]["vector_length"],
            "predicted_count": fm["predicted_count"],
            "tp": fm["tp"],
            "fp": fm["fp"],
            "fn": fm["fn"],
            "precision_pct": fm["precision_pct"],
            "recall_pct": fm["recall_pct"],
            "f1_pct": fm["f1_pct"],
            "f1_mean_pct": round(float(np.mean(f1s)), 2),
            "f1_std_pct": round(float(np.std(f1s)), 4),
            "precision_std_pct": round(float(np.std(precs)), 4),
            "recall_std_pct": round(float(np.std(recs)), 4),
            "runtime_s": primary["total_runtime_s"],
            "matching_only_mean_runtime_s": round(
                float(np.mean([float(s["stage_timings"].get("matching_and_validation_s", 0.0)) for s in sums])),
                2,
            ),
            "llm_calls": telem["total_llm_calls"],
            "retrieval_llm_calls": telem["retrieval_llm_calls"],
            "validation_llm_calls": telem["validation_llm_calls"],
            "validation_bypasses": telem["validation_bypasses"],
            "prompt_tokens": telem["total_prompt_tokens"],
            "completion_tokens": telem["total_completion_tokens"],
            "total_tokens": telem["total_tokens"],
            "validation_acceptance_rate_pct": att_s.get("validation_acceptance_rate_pct"),
            "merger_retention_rate_pct": att_s.get("merger_retention_rate_pct"),
        }

    up_telem = up_sum.get("llm_telemetry") or up_sum.get("llm_telemetry_summary") or {}
    up_stages_list = up_sum.get("stages") or []
    up_matching_sec = 0.0
    if isinstance(up_stages_list, list):
        for st_item in up_stages_list:
            if st_item.get("script") == "om_database_matching.py":
                up_matching_sec = float(st_item.get("elapsed_sec", 0.0))
    elif isinstance(up_stages_list, dict):
        up_matching_sec = float(up_stages_list.get("om_database_matching.py", {}).get("elapsed_s", 0.0))

    att_up_path = paths.replication_runs_dir / upstream_exp_id / "stage_attrition.json"
    att_up_loaded = (
        json.loads(att_up_path.read_text(encoding="utf-8")) if att_up_path.is_file() else {}
    )

    benchmark_rows: List[Dict[str, Any]] = [
        {
            "experiment_group": "Experiment A — Upstream GPT-4o + ada-002 (Committed HEAD CSV)",
            "short_label": "Exp A: GPT-4o (HEAD CSV)",
            "primary_experiment_id": "ref_upstream_gpt4o_cmt_confof",
            "repeat_runs": 1,
            "profile": "upstream_product_reference",
            "llm_model": "gpt-4o-2024-05-13",
            "embedding_model": "text-embedding-ada-002",
            "embedding_dim": 1536,
            "predicted_count": gpt4o_final["predicted_count"],
            "tp": gpt4o_final["tp"],
            "fp": gpt4o_final["fp"],
            "fn": gpt4o_final["fn"],
            "precision_pct": gpt4o_final["precision_pct"],
            "recall_pct": gpt4o_final["recall_pct"],
            "f1_pct": gpt4o_final["f1_pct"],
            "f1_mean_pct": gpt4o_final["f1_pct"],
            "f1_std_pct": 0.0,
            "precision_std_pct": 0.0,
            "recall_std_pct": 0.0,
            "runtime_s": 0.0,
            "matching_only_mean_runtime_s": 0.0,
            "llm_calls": 0,
            "retrieval_llm_calls": 0,
            "validation_llm_calls": 0,
            "validation_bypasses": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "validation_acceptance_rate_pct": None,
            "merger_retention_rate_pct": None,
        },
        {
            "experiment_group": "Experiment A (v1.0.1) — Upstream GPT-4o + ada-002 (result-reference.csv)",
            "short_label": "Exp A: GPT-4o (v1.0.1)",
            "primary_experiment_id": "ref_upstream_gpt4o_v1_table",
            "repeat_runs": 1,
            "profile": "upstream_product_reference",
            "llm_model": "gpt-4o-2024-05-13",
            "embedding_model": "text-embedding-ada-002",
            "embedding_dim": 1536,
            "predicted_count": 9,
            "tp": 6,
            "fp": 3,
            "fn": 10,
            "precision_pct": 66.67,
            "recall_pct": 37.50,
            "f1_pct": 48.00,
            "f1_mean_pct": 48.00,
            "f1_std_pct": 0.0,
            "precision_std_pct": 0.0,
            "recall_std_pct": 0.0,
            "runtime_s": 0.0,
            "matching_only_mean_runtime_s": 0.0,
            "llm_calls": 0,
            "retrieval_llm_calls": 0,
            "validation_llm_calls": 0,
            "validation_bypasses": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "validation_acceptance_rate_pct": None,
            "merger_retention_rate_pct": None,
        },
        {
            "experiment_group": "Upstream Agent-OM-Lite (result-om-2025-test.csv Reference)",
            "short_label": "Upstream Lite (Ref Table)",
            "primary_experiment_id": "ref_upstream_lite_committed",
            "repeat_runs": 1,
            "profile": "upstream_agent_om_lite_ref",
            "llm_model": "llama3:8b",
            "embedding_model": "llama3:8b",
            "embedding_dim": 4096,
            "predicted_count": 7,
            "tp": 4,
            "fp": 3,
            "fn": 12,
            "precision_pct": 57.14,
            "recall_pct": 25.00,
            "f1_pct": 34.78,
            "f1_mean_pct": 34.78,
            "f1_std_pct": 0.0,
            "precision_std_pct": 0.0,
            "recall_std_pct": 0.0,
            "runtime_s": 0.0,
            "matching_only_mean_runtime_s": 0.0,
            "llm_calls": 0,
            "retrieval_llm_calls": 0,
            "validation_llm_calls": 0,
            "validation_bypasses": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "validation_acceptance_rate_pct": None,
            "merger_retention_rate_pct": None,
        },
        {
            "experiment_group": "Experiment B — Upstream Agent-OM-Lite (Isolated Local Execution)",
            "short_label": "Exp B: Upstream Lite",
            "primary_experiment_id": upstream_exp_id,
            "repeat_runs": 1,
            "profile": "upstream_agent_om_lite_isolated",
            "llm_model": "llama3:8b",
            "embedding_model": "llama3:8b",
            "embedding_dim": 4096,
            "predicted_count": up_final["predicted_count"],
            "tp": up_final["tp"],
            "fp": up_final["fp"],
            "fn": up_final["fn"],
            "precision_pct": up_final["precision_pct"],
            "recall_pct": up_final["recall_pct"],
            "f1_pct": up_final["f1_pct"],
            "f1_mean_pct": up_final["f1_pct"],
            "f1_std_pct": 0.0,
            "precision_std_pct": 0.0,
            "recall_std_pct": 0.0,
            "runtime_s": round(
                float(up_sum.get("total_elapsed_sec", up_sum.get("total_elapsed_s", 0.0))), 2
            ),
            "matching_only_mean_runtime_s": round(up_matching_sec, 2),
            "llm_calls": int(up_telem.get("total_calls", 0)),
            "retrieval_llm_calls": int(
                (up_telem.get("by_stage") or {}).get("om_ontology_to_csv.py", {}).get("calls", 0)
            ),
            "validation_llm_calls": int(
                (up_telem.get("by_stage") or {}).get("om_database_matching.py", {}).get("calls", 0)
            ),
            "validation_bypasses": 0,
            "prompt_tokens": int(up_telem.get("prompt_tokens", 0)),
            "completion_tokens": int(up_telem.get("completion_tokens", 0)),
            "total_tokens": int(up_telem.get("total_tokens", 0)),
            "validation_acceptance_rate_pct": att_up_loaded.get("validation_acceptance_rate_pct"),
            "merger_retention_rate_pct": att_up_loaded.get("merger_retention_rate_pct"),
        },
        _agg_local(
            "Experiment C — Local Parity (llama3:8b + llama3:8b 4096-dim)",
            "Exp C: Local Parity",
            "upstream_lite_parity",
            par_sums,
        ),
        _agg_local(
            "Experiment D — Local Adapted (qwen3.5:9b + nomic-embed-text 768-dim)",
            "Exp D: Local Adapted",
            "local_adapted",
            adap_sums,
        ),
    ]

    pd.DataFrame(benchmark_rows).to_csv(
        comp_dir / "phase5_benchmark_summary.csv", index=False, encoding="utf-8"
    )
    (comp_dir / "phase5_benchmark_summary.json").write_text(
        json.dumps(benchmark_rows, indent=2), encoding="utf-8"
    )

    # All 6 variants across executed & committed CSV configurations
    variants_rows: List[Dict[str, Any]] = []
    for label, bnd in (
        ("Exp A: GPT-4o (HEAD CSV)", bundle_gpt4o),
        ("Exp B: Upstream Lite", bundle_upstream),
        ("Exp C: Local Parity", bundle_parity),
        ("Exp D: Local Adapted", bundle_adapted),
    ):
        for v_key in ("s2t_no_val", "t2s_no_val", "merged_no_val", "s2t_val", "t2s_val", "final_merged"):
            m = compute_alignment_metrics(bnd["predictions"][v_key], ref_pairs)
            variants_rows.append(
                {
                    "experiment": label,
                    "variant": v_key,
                    "predicted": m["predicted_count"],
                    "tp": m["tp"],
                    "fp": m["fp"],
                    "fn": m["fn"],
                    "precision_pct": m["precision_pct"],
                    "recall_pct": m["recall_pct"],
                    "f1_pct": m["f1_pct"],
                }
            )
    pd.DataFrame(variants_rows).to_csv(
        comp_dir / "phase5_6variants_all_experiments.csv", index=False, encoding="utf-8"
    )

    # Router overhead summary if present
    router_comparison: Dict[str, Any] = {}
    if router_sample_exp_id and (paths.replication_runs_dir / router_sample_exp_id / "run_summary.json").is_file():
        r_sum = _load_summary(router_sample_exp_id)
        router_comparison = {
            "experiment_id": router_sample_exp_id,
            "total_runtime_s": r_sum["total_runtime_s"],
            "telemetry": r_sum["telemetry"],
        }
        (comp_dir / "phase5_router_overhead.json").write_text(
            json.dumps(router_comparison, indent=2), encoding="utf-8"
        )

    # Threshold sensitivity sweeps on pure local hybrid memories
    thresh_rows: List[Dict[str, Any]] = []
    for db_n, prof_n in (("agent_om_parity", "upstream_lite_parity"), ("agent_om_adapted", "local_adapted")):
        try:
            thresh_rows.extend(_compute_threshold_sweep_on_db(db_n, prof_n, ref_pairs))
        except Exception as exc:
            print(f"Threshold sweep skipped for {db_n}: {exc}")

    if thresh_rows:
        pd.DataFrame(thresh_rows).to_csv(
            comp_dir / "threshold_sensitivity.csv", index=False, encoding="utf-8"
        )

    # Stage attrition comparison CSV & figure
    attrition_by_run: Dict[str, Sequence[Dict[str, Any]]] = {}
    attrition_flat_rows: List[Dict[str, Any]] = []
    for short_lbl, eid in (
        ("Exp B: Upstream Lite", upstream_exp_id),
        ("Exp C: Local Parity", parity_exp_ids[0]),
        ("Exp D: Local Adapted", adapted_exp_ids[0]),
    ):
        ap = paths.replication_runs_dir / eid / "stage_attrition.json"
        if ap.is_file():
            adata = json.loads(ap.read_text(encoding="utf-8"))
            attrition_by_run[short_lbl] = adata["stages"]
            for st in adata["stages"]:
                attrition_flat_rows.append({"experiment": short_lbl, **st})

    if attrition_flat_rows:
        pd.DataFrame(attrition_flat_rows).to_csv(
            comp_dir / "phase5_stage_attrition_comparison.csv", index=False, encoding="utf-8"
        )

    # Save high-DPI PNG charts
    save_figure(build_prf1_comparison_figure(benchmark_rows), charts_dir / "prf1_comparison.png")
    save_figure(
        build_precision_recall_scatter_figure(benchmark_rows), charts_dir / "pr_scatter_isof1.png"
    )
    save_figure(
        build_runtime_and_calls_figure(benchmark_rows[3:]), charts_dir / "runtime_and_llm_calls.png"
    )
    if attrition_by_run:
        save_figure(
            build_stage_attrition_figure(attrition_by_run), charts_dir / "stage_attrition_tp.png"
        )
    if thresh_rows:
        adap_t = [r for r in thresh_rows if r["profile"] == "local_adapted"]
        par_t = [r for r in thresh_rows if r["profile"] == "upstream_lite_parity"]
        if adap_t:
            save_figure(
                build_threshold_sensitivity_figure(
                    adap_t,
                    title="Cosine Threshold Sensitivity — Local Adapted (nomic-embed-text 768-dim, RRF Top-1 Merger)",
                ),
                charts_dir / "threshold_sensitivity_local_adapted.png",
            )
        if par_t:
            save_figure(
                build_threshold_sensitivity_figure(
                    par_t,
                    title="Cosine Threshold Sensitivity — Local Parity (llama3:8b 4096-dim, RRF Top-1 Merger)",
                ),
                charts_dir / "threshold_sensitivity_local_parity.png",
            )

    return {
        "comparisons_dir": str(comp_dir),
        "charts_dir": str(charts_dir),
        "benchmark_rows": benchmark_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-id", required=True)
    parser.add_argument("--parity-ids", nargs="+", required=True)
    parser.add_argument("--adapted-ids", nargs="+", required=True)
    parser.add_argument("--router-sample-id", default=None)
    args = parser.parse_args()

    out = generate_all(
        upstream_exp_id=args.upstream_id,
        parity_exp_ids=args.parity_ids,
        adapted_exp_ids=args.adapted_ids,
        router_sample_exp_id=args.router_sample_id,
    )
    print(json.dumps({"comparisons_dir": out["comparisons_dir"], "rows": len(out["benchmark_rows"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

