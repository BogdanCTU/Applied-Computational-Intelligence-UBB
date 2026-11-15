"""End-to-end local Agent-OM replication runner executing strictly from raw ontology files.

Supports all executable profiles (`upstream_lite_parity`, `local_adapted`, `experimental`),
records full stage-by-stage telemetry, intermediate artifacts, 6-variant alignment CSVs,
OAEI RDF XML, stage attrition tables, and cooperative cancellation into a dedicated
`output/replication_runs/<experiment_id>/` directory using an isolated PostgreSQL database.
"""

from __future__ import annotations

import argparse
import csv
import json
import signal
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.matching_agent import MatchingAgent
from src.agents.retrieval_agent import RetrievalAgent
from src.config import VALID_PROFILES, AppConfig
from src.db.database_manager import DatabaseManager
from src.evaluation.comparator import load_features_csv
from src.evaluation.metrics import (
    compute_alignment_metrics,
    compute_stage_attrition,
    export_alignment_rdf_xml,
    load_reference_pairs,
    write_pairs_csv,
)
from src.ontology.entity_extractor import EntityExtractor, OntologyEntity
from src.ontology.parser import OntologyGraph, load_ontology


class ExperimentCancelledError(RuntimeError):
    """Raised when a user or signal requests safe cooperative cancellation."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_local_experiment(
    experiment_id: str,
    profile_name: str = "local_adapted",
    source_ontology_path: Optional[Path] = None,
    target_ontology_path: Optional[Path] = None,
    reference_alignment_path: Optional[Path] = None,
    output_base_dir: Optional[Path] = None,
    db_name_override: Optional[str] = None,
    max_entities_per_side: Optional[int] = None,
    skip_retrieval: bool = False,
    reuse_features_csv: Optional[Path] = None,
    similarity_threshold: Optional[float] = None,
    top_k: Optional[int] = None,
    rrf_k: Optional[int] = None,
    tool_routing_mode: Optional[str] = None,
    predicate_scope: Optional[str] = None,
    o1_is_code: Optional[bool] = None,
    o2_is_code: Optional[bool] = None,
    validate_matches: bool = True,
    reciprocal_merger: bool = True,
    stage_callback: Optional[Callable[[str, int, int, str], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """Execute a complete or matching-only local replication experiment and save all artifacts."""
    default_data_dir = (
        WORKSPACE_ROOT / "original_repo" / "data" / "conference" / "cmt-confof" / "component"
    )
    src_path = Path(source_ontology_path or (default_data_dir / "source.xml")).resolve()
    tgt_path = Path(target_ontology_path or (default_data_dir / "target.xml")).resolve()
    ref_path = (
        Path(reference_alignment_path).resolve()
        if reference_alignment_path is not None
        else (default_data_dir / "reference.xml").resolve()
    )

    overrides: Dict[str, Any] = {}
    if db_name_override:
        overrides["db_name"] = db_name_override
    if similarity_threshold is not None:
        overrides["similarity_threshold"] = float(similarity_threshold)
    if top_k is not None:
        overrides["top_k"] = int(top_k)
    if rrf_k is not None:
        overrides["rrf_k"] = int(rrf_k)
    if tool_routing_mode is not None:
        overrides["tool_routing_mode"] = tool_routing_mode
    if predicate_scope is not None:
        overrides["predicate_scope"] = predicate_scope
    if o1_is_code is not None:
        overrides["o1_is_code"] = bool(o1_is_code)
    if o2_is_code is not None:
        overrides["o2_is_code"] = bool(o2_is_code)

    app_cfg = AppConfig.from_profile(profile_name, **overrides)
    app_cfg.ensure_executable()

    runs_root = Path(output_base_dir or (app_cfg.output_dir / "replication_runs")).resolve()
    run_dir = runs_root / experiment_id
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(
            f"Experiment output directory already exists and is non-empty: {run_dir}. "
            "Use a unique experiment_id to preserve existing outputs."
        )
    run_dir.mkdir(parents=True, exist_ok=True)

    started_utc = _utc_now_iso()
    t_run_start = time.perf_counter()

    def _check_cancel(stage_name: str) -> None:
        if should_cancel and should_cancel():
            raise ExperimentCancelledError(f"Cancelled during stage '{stage_name}'.")

    def _emit(stage: str, current: int, total: int, message: str) -> None:
        print(f"[{stage}] ({current}/{total}) {message}", flush=True)
        if stage_callback:
            stage_callback(stage, current, total, message)

    # Save configuration snapshot immediately
    cfg_snapshot = {
        "experiment_id": experiment_id,
        "started_utc": started_utc,
        "source_ontology_path": str(src_path),
        "target_ontology_path": str(tgt_path),
        "reference_alignment_path": str(ref_path) if ref_path.is_file() else None,
        "max_entities_per_side": max_entities_per_side,
        "skip_retrieval": skip_retrieval,
        "reuse_features_csv": str(reuse_features_csv) if reuse_features_csv else None,
        "validate_matches": validate_matches,
        "reciprocal_merger": reciprocal_merger,
        "config": app_cfg.to_metadata_dict(),
    }
    (run_dir / "config_snapshot.json").write_text(
        json.dumps(cfg_snapshot, indent=2), encoding="utf-8"
    )

    db = DatabaseManager(connection_string=app_cfg.connection_string)
    db.ensure_database_exists()
    db.init_extensions()

    stage_timings: Dict[str, float] = {}
    retrieval_telemetry: Dict[str, Any] = {
        "llm_calls": 0,
        "feature_llm_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "router_calls": 0,
        "router_errors": 0,
    }
    chunk_counts: Dict[str, int] = {}

    try:
        # Stage 1 & 2: Ontology Loading & Entity Extraction
        _check_cancel("ontology_loading")
        t0 = time.perf_counter()
        _emit("1_ontology_loading", 1, 2, f"Loading source ontology {src_path.name}")
        src_ont: OntologyGraph = load_ontology(src_path)
        _emit("1_ontology_loading", 2, 2, f"Loading target ontology {tgt_path.name}")
        tgt_ont: OntologyGraph = load_ontology(tgt_path)
        stage_timings["ontology_loading_s"] = round(time.perf_counter() - t0, 4)

        _check_cancel("entity_extraction")
        t0 = time.perf_counter()
        extractor = EntityExtractor(combine_properties_sort=app_cfg.combine_properties_sort)
        src_entities, src_summary = extractor.extract_entities(
            src_ont, "Source", ontology_is_code=app_cfg.o1_is_code
        )
        tgt_entities, tgt_summary = extractor.extract_entities(
            tgt_ont, "Target", ontology_is_code=app_cfg.o2_is_code
        )
        if max_entities_per_side is not None and max_entities_per_side > 0:
            src_entities = src_entities[:max_entities_per_side]
            tgt_entities = tgt_entities[:max_entities_per_side]
        stage_timings["entity_extraction_s"] = round(time.perf_counter() - t0, 4)
        _emit(
            "2_entity_extraction",
            len(src_entities) + len(tgt_entities),
            len(src_entities) + len(tgt_entities),
            f"Extracted {len(src_entities)} source and {len(tgt_entities)} target entities.",
        )

        extracted_payload = {
            "source_summary": asdict(src_summary),
            "target_summary": asdict(tgt_summary),
            "source_entities": [asdict(e) for e in src_entities],
            "target_entities": [asdict(e) for e in tgt_entities],
        }
        (run_dir / "extracted_entities.json").write_text(
            json.dumps(extracted_payload, indent=2), encoding="utf-8"
        )

        ret_agent = RetrievalAgent(
            db_manager=db,
            context=app_cfg.context,
            o1_is_code=app_cfg.o1_is_code,
            o2_is_code=app_cfg.o2_is_code,
            similarity_threshold=app_cfg.similarity_threshold,
            top_k=app_cfg.top_k,
            num_matches=app_cfg.num_matches,
            rrf_k=app_cfg.rrf_k,
            tool_routing_mode=app_cfg.tool_routing_mode,
            skip_empty_chunks=app_cfg.skip_empty_chunks,
            app_config=app_cfg,
        )

        # Stage 3 & 4: Feature Generation & Hybrid Memory Ingestion (unless skip_retrieval)
        if skip_retrieval:
            _emit("3_feature_generation", 1, 1, "Reusing existing hybrid memory database tables.")
            with db.get_connection() as conn:
                features_df = pd.read_sql_query(
                    "SELECT entity_id, entity_uri, source_or_target, entity_type, "
                    "syntactic_matching, lexical_matching, semantic_matching "
                    "FROM ontology_matching ORDER BY entity_id ASC;",
                    conn,
                )
            features_df.to_csv(run_dir / "ontology_matching.csv", index=False, encoding="utf-8")
            row_counts = db.get_table_row_counts()
            chunk_counts = {
                "total_entities": row_counts.get("ontology_matching", 0),
                "syntactic_chunks": row_counts.get("syntactic_matching", 0),
                "lexical_chunks": row_counts.get("lexical_matching", 0),
                "semantic_chunks": row_counts.get("semantic_matching", 0),
            }
        else:
            if reuse_features_csv is not None:
                features_df = load_features_csv(reuse_features_csv)
                features_df.to_csv(run_dir / "ontology_matching.csv", index=False, encoding="utf-8")
                stage_timings["feature_generation_s"] = 0.0
            else:
                t0 = time.perf_counter()

                def _src_prog(idx: int, total: int, uri: str, dur: float) -> None:
                    _check_cancel("source_feature_generation")
                    _emit("3_source_retrieval", idx, total, f"{uri} ({dur:.2f}s)")

                def _tgt_prog(idx: int, total: int, uri: str, dur: float) -> None:
                    _check_cancel("target_feature_generation")
                    _emit("4_target_retrieval", idx, total, f"{uri} ({dur:.2f}s)")

                src_records = ret_agent.extract_representations_for_entities(
                    src_entities, src_ont, progress_callback=_src_prog, ontology_is_code=app_cfg.o1_is_code
                )
                src_telem = dict(ret_agent.last_extraction_telemetry)

                tgt_records = ret_agent.extract_representations_for_entities(
                    tgt_entities, tgt_ont, progress_callback=_tgt_prog, ontology_is_code=app_cfg.o2_is_code
                )
                tgt_telem = dict(ret_agent.last_extraction_telemetry)

                for k in retrieval_telemetry:
                    retrieval_telemetry[k] = int(src_telem.get(k, 0)) + int(tgt_telem.get(k, 0))

                features_df = ret_agent.build_features_dataframe(
                    src_records, tgt_records, source_ontology=src_ont, target_ontology=tgt_ont
                )
                features_df.to_csv(run_dir / "ontology_matching.csv", index=False, encoding="utf-8")
                stage_timings["feature_generation_s"] = round(time.perf_counter() - t0, 4)

            _check_cancel("vector_ingestion")
            t0 = time.perf_counter()
            _emit(
                "5_vector_ingestion",
                0,
                3,
                f"Embedding and indexing {len(features_df)} entities into {app_cfg.db_name} (dim={app_cfg.vector_length})",
            )
            chunk_counts = ret_agent.ingest_features_to_database(features_df)
            stage_timings["vector_ingestion_s"] = round(time.perf_counter() - t0, 4)
            _emit(
                "5_vector_ingestion",
                3,
                3,
                f"Indexed chunks: syn={chunk_counts['syntactic_chunks']}, "
                f"lex={chunk_counts['lexical_chunks']}, sem={chunk_counts['semantic_chunks']}",
            )

        (run_dir / "chunk_counts.json").write_text(
            json.dumps(chunk_counts, indent=2), encoding="utf-8"
        )

        # Stage 6: Candidate Retrieval & RRF Inspection Snapshot
        _check_cancel("candidate_retrieval")
        t0 = time.perf_counter()
        s2t_candidates = ret_agent.retrieve_directional_candidates("Source", k=app_cfg.rrf_k)
        t2s_candidates = ret_agent.retrieve_directional_candidates("Target", k=app_cfg.rrf_k)
        stage_timings["candidate_inspection_s"] = round(time.perf_counter() - t0, 4)
        (run_dir / "candidates_s2t.json").write_text(
            json.dumps(s2t_candidates, indent=2), encoding="utf-8"
        )
        (run_dir / "candidates_t2s.json").write_text(
            json.dumps(t2s_candidates, indent=2), encoding="utf-8"
        )

        # Stage 7: Directional Validation & Reciprocal Merging
        _check_cancel("matching_and_validation")
        t0 = time.perf_counter()
        _emit("6_matching_validation", 0, 2, "Running bidirectional RRF matching, LLM validation, and reciprocal merger")
        match_agent = MatchingAgent(
            db_manager=db,
            context=app_cfg.context,
            similarity_threshold=app_cfg.similarity_threshold,
            top_k=app_cfg.top_k,
            num_matches=app_cfg.num_matches,
            rrf_k=app_cfg.rrf_k,
            source_ontology=src_ont,
            target_ontology=tgt_ont,
            o1_is_code=app_cfg.o1_is_code,
            o2_is_code=app_cfg.o2_is_code,
            tool_routing_mode=app_cfg.tool_routing_mode,
            app_config=app_cfg,
        )
        pipeline_res = match_agent.run_pipeline(
            experiment_id=experiment_id,
            validate=validate_matches,
            reciprocal_merger=reciprocal_merger,
        )
        stage_timings["matching_and_validation_s"] = round(time.perf_counter() - t0, 4)
        _emit(
            "6_matching_validation",
            2,
            2,
            f"Completed matching: final_pairs={len(pipeline_res.final_predictions)}, "
            f"llm_validations={pipeline_res.total_validation_calls}, bypasses={pipeline_res.total_bypasses}",
        )

        # Save validation records
        all_val_records = [
            asdict(r)
            for r in (
                pipeline_res.source_to_target.validation_records
                + pipeline_res.target_to_source.validation_records
            )
        ]
        (run_dir / "validation_records.json").write_text(
            json.dumps(all_val_records, indent=2), encoding="utf-8"
        )
        if all_val_records:
            pd.DataFrame(all_val_records).to_csv(
                run_dir / "validation_records.csv", index=False, encoding="utf-8"
            )

        # Export all 6 upstream prediction CSV variants + OAEI RDF XML
        s2t_no_val = pipeline_res.source_to_target.unvalidated_predicted_pairs
        t2s_no_val = pipeline_res.target_to_source.unvalidated_predicted_pairs
        merged_no_val = s2t_no_val & t2s_no_val
        s2t_val = pipeline_res.source_to_target.predicted_pairs
        t2s_val = pipeline_res.target_to_source.predicted_pairs
        final_merged = pipeline_res.final_predictions

        align_dir = run_dir / "alignments"
        write_pairs_csv(s2t_no_val, align_dir / "predict_source_to_target_without_validation.csv")
        write_pairs_csv(t2s_no_val, align_dir / "predict_target_to_source_without_validation.csv")
        write_pairs_csv(merged_no_val, align_dir / "predict_merge_without_validation.csv")
        write_pairs_csv(s2t_val, align_dir / "predict_source_to_target.csv")
        write_pairs_csv(t2s_val, align_dir / "predict_target_to_source.csv")
        write_pairs_csv(final_merged, align_dir / "predict.csv")
        export_alignment_rdf_xml(
            final_merged,
            align_dir / "alignment.rdf",
            onto1_uri=src_ont.find_base_uri() or "http://source",
            onto2_uri=tgt_ont.find_base_uri() or "http://target",
        )

        # Stage 8: Evaluation & Stage Attrition
        metrics_by_variant: Dict[str, Any] = {}
        attrition: Optional[Dict[str, Any]] = None
        if ref_path.is_file():
            ref_pairs = load_reference_pairs(ref_path)
            # If running a subset smoke test, filter reference pairs to extracted URIs ONLY for subset diagnostics
            # while ALSO recording full-reference metrics explicitly.
            variant_sets = {
                "1_s2t_without_validation": s2t_no_val,
                "2_t2s_without_validation": t2s_no_val,
                "3_merge_without_validation": merged_no_val,
                "4_s2t_with_validation": s2t_val,
                "5_t2s_with_validation": t2s_val,
                "6_final_with_validation_and_merger": final_merged,
            }
            variant_rows: List[Dict[str, Any]] = []
            for v_name, v_pairs in variant_sets.items():
                m = compute_alignment_metrics(v_pairs, ref_pairs)
                metrics_by_variant[v_name] = m
                variant_rows.append(
                    {
                        "variant": v_name,
                        "predicted": m["predicted_count"],
                        "tp": m["tp"],
                        "fp": m["fp"],
                        "fn": m["fn"],
                        "precision_pct": m["precision_pct"],
                        "recall_pct": m["recall_pct"],
                        "f1_pct": m["f1_pct"],
                        "f1_exact_pct": m["f1_exact_pct"],
                    }
                )
            pd.DataFrame(variant_rows).to_csv(
                run_dir / "metrics_6variants.csv", index=False, encoding="utf-8"
            )

            id_to_uri = {
                str(r["entity_id"]): str(r["entity_uri"])
                for _, r in features_df.iterrows()
            }
            attrition = compute_stage_attrition(
                reference_pairs=ref_pairs,
                source_entity_uris=[str(r["entity_uri"]) for _, r in features_df[features_df["source_or_target"] == "Source"].iterrows()],
                target_entity_uris=[str(r["entity_uri"]) for _, r in features_df[features_df["source_or_target"] == "Target"].iterrows()],
                s2t_candidates=s2t_candidates,
                t2s_candidates=t2s_candidates,
                s2t_unvalidated_pairs=s2t_no_val,
                t2s_unvalidated_pairs=t2s_no_val,
                s2t_validated_pairs=s2t_val,
                t2s_validated_pairs=t2s_val,
                final_merged_pairs=final_merged,
                validation_records=(
                    pipeline_res.source_to_target.validation_records
                    + pipeline_res.target_to_source.validation_records
                ),
                id_to_uri=id_to_uri,
            )
            (run_dir / "stage_attrition.json").write_text(
                json.dumps(attrition, indent=2), encoding="utf-8"
            )
            pd.DataFrame(attrition["stages"]).to_csv(
                run_dir / "stage_attrition.csv", index=False, encoding="utf-8"
            )

        total_runtime_s = round(time.perf_counter() - t_run_start, 4)
        total_llm_calls = (
            int(retrieval_telemetry["llm_calls"])
            + int(pipeline_res.total_validation_calls)
            + int(pipeline_res.router_calls)
        )
        total_prompt_tokens = int(retrieval_telemetry["prompt_tokens"]) + int(
            pipeline_res.total_prompt_tokens
        )
        total_completion_tokens = int(retrieval_telemetry["completion_tokens"]) + int(
            pipeline_res.total_completion_tokens
        )

        summary = {
            "experiment_id": experiment_id,
            "status": "completed",
            "profile_name": profile_name,
            "started_utc": started_utc,
            "completed_utc": _utc_now_iso(),
            "total_runtime_s": total_runtime_s,
            "stage_timings": stage_timings,
            "config": app_cfg.to_metadata_dict(),
            "chunk_counts": chunk_counts,
            "telemetry": {
                "total_llm_calls": total_llm_calls,
                "retrieval_llm_calls": retrieval_telemetry["llm_calls"],
                "retrieval_feature_llm_calls": retrieval_telemetry["feature_llm_calls"],
                "validation_llm_calls": pipeline_res.total_validation_calls,
                "validation_bypasses": pipeline_res.total_bypasses,
                "router_calls": int(retrieval_telemetry["router_calls"]) + int(pipeline_res.router_calls),
                "router_errors": int(retrieval_telemetry["router_errors"]) + int(pipeline_res.router_errors),
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
            },
            "final_metrics": metrics_by_variant.get("6_final_with_validation_and_merger"),
            "metrics_6variants": metrics_by_variant,
            "stage_attrition_summary": {
                "validation_acceptance_rate_pct": attrition["validation_acceptance_rate_pct"]
                if attrition
                else None,
                "merger_retention_rate_pct": attrition["merger_retention_rate_pct"]
                if attrition
                else None,
            },
            "run_dir": str(run_dir),
        }
        (run_dir / "run_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        _emit("7_complete", 1, 1, f"Experiment '{experiment_id}' completed in {total_runtime_s:.2f}s.")
        return summary

    except ExperimentCancelledError as exc:
        cancelled_summary = {
            "experiment_id": experiment_id,
            "status": "cancelled",
            "profile_name": profile_name,
            "started_utc": started_utc,
            "completed_utc": _utc_now_iso(),
            "total_runtime_s": round(time.perf_counter() - t_run_start, 4),
            "stage_timings": stage_timings,
            "reason": str(exc),
            "config": app_cfg.to_metadata_dict(),
            "run_dir": str(run_dir),
        }
        (run_dir / "run_summary.json").write_text(
            json.dumps(cancelled_summary, indent=2), encoding="utf-8"
        )
        return cancelled_summary
    except Exception as exc:
        failed_summary = {
            "experiment_id": experiment_id,
            "status": "failed",
            "profile_name": profile_name,
            "started_utc": started_utc,
            "completed_utc": _utc_now_iso(),
            "total_runtime_s": round(time.perf_counter() - t_run_start, 4),
            "stage_timings": stage_timings,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "config": app_cfg.to_metadata_dict(),
            "run_dir": str(run_dir),
        }
        (run_dir / "run_summary.json").write_text(
            json.dumps(failed_summary, indent=2), encoding="utf-8"
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Agent-OM replication experiment.")
    parser.add_argument("--experiment-id", required=True, help="Unique experiment identifier.")
    parser.add_argument(
        "--profile",
        default="local_adapted",
        choices=[p for p in VALID_PROFILES if p != "upstream_product_reference"],
        help="Execution configuration profile.",
    )
    parser.add_argument("--source", type=Path, default=None, help="Path to source ontology.")
    parser.add_argument("--target", type=Path, default=None, help="Path to target ontology.")
    parser.add_argument("--reference", type=Path, default=None, help="Path to reference alignment XML.")
    parser.add_argument("--db-name", default=None, help="Optional isolated PostgreSQL DB name override.")
    parser.add_argument("--max-entities", type=int, default=None, help="Optional cap per ontology side.")
    parser.add_argument("--skip-retrieval", action="store_true", help="Reuse populated DB tables for matching rerun.")
    parser.add_argument("--similarity-threshold", type=float, default=None)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--rrf-k", type=int, default=None)
    parser.add_argument("--tool-routing-mode", choices=["deterministic", "llm_json"], default=None)
    parser.add_argument("--predicate-scope", choices=["head", "pvl_v1"], default=None)
    parser.add_argument("--o1-is-code", action="store_true")
    parser.add_argument("--o2-is-code", action="store_true")
    parser.add_argument("--no-validate", action="store_true")
    parser.add_argument("--no-merger", action="store_true")
    args = parser.parse_args()

    cancel_flag = {"cancelled": False}

    def _sig_handler(signum: int, frame: Any) -> None:
        cancel_flag["cancelled"] = True

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    summary = run_local_experiment(
        experiment_id=args.experiment_id,
        profile_name=args.profile,
        source_ontology_path=args.source,
        target_ontology_path=args.target,
        reference_alignment_path=args.reference,
        db_name_override=args.db_name,
        max_entities_per_side=args.max_entities,
        skip_retrieval=args.skip_retrieval,
        similarity_threshold=args.similarity_threshold,
        top_k=args.top_k,
        rrf_k=args.rrf_k,
        tool_routing_mode=args.tool_routing_mode,
        predicate_scope=args.predicate_scope,
        o1_is_code=True if args.o1_is_code else None,
        o2_is_code=True if args.o2_is_code else None,
        validate_matches=not args.no_validate,
        reciprocal_merger=not args.no_merger,
        should_cancel=lambda: cancel_flag["cancelled"],
    )
    print(json.dumps(summary.get("final_metrics") or {"status": summary["status"]}, indent=2))
    return 0 if summary["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

