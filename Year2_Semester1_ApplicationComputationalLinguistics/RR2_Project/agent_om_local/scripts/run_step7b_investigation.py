"""
Step 7B Investigation: Final Threshold Validation (tau=0.875) & LLM Validator Loss Analysis.

Runs:
- Full matching pipeline at tau = 0.875
- Detailed validation logging for tau = [0.850, 0.875, 0.900]
- Direct comparative accounting across tau = 0.850, 0.875, 0.900
- LLM validation loss analysis (acceptances, rejections, directional asymmetries, bypass traps)
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pandas as pd
import rdflib
from langchain_ollama import ChatOllama

# Ensure project root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.matching_agent import MatchingAgent, PipelineResult
from src.config import config
from src.db.database_manager import DatabaseManager
from src.matching.merger import ReciprocalMerger
from src.matching.validator import MatchingValidator, ValidationRecord
from src.retrieval.rank_fusion import reciprocal_rank_fusion
from src.utils.text_processing import uri_to_name
from scripts.run_experiments_step6 import ensure_database_populated


def load_reference_alignment(ref_path: Path) -> Set[Tuple[str, str]]:
    """Loads 1:1 equivalence correspondences from reference.xml."""
    g = rdflib.Graph().parse(ref_path)
    align_cell = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#Cell")
    align_e1 = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#entity1")
    align_e2 = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#entity2")
    align_rel = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#relation")

    reference_pairs = set()
    for s in g.subjects(rdflib.RDF.type, align_cell):
        rel = str(g.value(s, align_rel, None))
        if rel == "=":
            e1 = str(g.value(s, align_e1, None))
            e2 = str(g.value(s, align_e2, None))
            reference_pairs.add((e1, e2))
    return reference_pairs


def calculate_metrics(predicted_pairs: Set[Tuple[str, str]], reference_pairs: Set[Tuple[str, str]]) -> Dict[str, Any]:
    """Calculates TP, FP, FN, Precision, Recall, and F1."""
    tp_pairs = reference_pairs.intersection(predicted_pairs)
    fp_pairs = predicted_pairs - reference_pairs
    fn_pairs = reference_pairs - predicted_pairs

    tp = len(tp_pairs)
    fp = len(fp_pairs)
    fn = len(fn_pairs)

    precision = round(tp / (tp + fp) * 100, 2) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn) * 100, 2) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 2) if (precision + recall) > 0 else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "predicted_count": len(predicted_pairs),
        "reference_count": len(reference_pairs),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp_pairs": sorted(list(tp_pairs)),
        "fp_pairs": sorted(list(fp_pairs)),
        "fn_pairs": sorted(list(fn_pairs)),
    }


def fmt_pair(p: Tuple[str, str]) -> str:
    """Format URI pair as Name = Name."""
    return f"{p[0].split('#')[-1]} = {p[1].split('#')[-1]}"


def run_pipeline_for_threshold(
    db: DatabaseManager,
    validator: MatchingValidator,
    merger: ReciprocalMerger,
    tau: float,
    reference_pairs: Set[Tuple[str, str]],
) -> Tuple[PipelineResult, Dict[str, Any], List[Dict[str, Any]]]:
    """Runs the full matching pipeline at a given threshold tau and returns results and logs."""
    agent = MatchingAgent(
        db_manager=db,
        validator=validator,
        merger=merger,
        similarity_threshold=tau,
        top_k=config.top_k,
        num_matches=config.num_matches,
        rrf_k=0,
    )

    t0 = time.perf_counter()
    res: PipelineResult = agent.run_pipeline(
        experiment_id=f"FullPipeline_tau_{tau:.3f}",
        validate=True,
        reciprocal_merger=True,
    )
    duration = time.perf_counter() - t0

    s2t_m = calculate_metrics(res.source_to_target.predicted_pairs, reference_pairs)
    t2s_m = calculate_metrics(res.target_to_source.predicted_pairs, reference_pairs)
    final_m = calculate_metrics(res.final_predictions, reference_pairs)

    # Collect validation logs
    val_rows: List[Dict[str, Any]] = []
    for rec in res.source_to_target.validation_records:
        rdict = asdict(rec)
        rdict["experiment_tau"] = tau
        val_rows.append(rdict)
    for rec in res.target_to_source.validation_records:
        rdict = asdict(rec)
        rdict["experiment_tau"] = tau
        val_rows.append(rdict)

    # Validation stats
    llm_records = [r for r in val_rows if not r["bypassed"]]
    accept_count = sum(1 for r in llm_records if r["decision"] == "yes")
    reject_count = sum(1 for r in llm_records if r["decision"] == "no")
    error_count = sum(1 for r in llm_records if r["decision"] == "error")

    summary = {
        "threshold": tau,
        "duration_s": round(duration, 2),
        "validation_calls": res.total_validation_calls,
        "bypasses": res.total_bypasses,
        "llm_accepts": accept_count,
        "llm_rejects": reject_count,
        "llm_errors": error_count,
        "prompt_tokens": res.total_prompt_tokens,
        "completion_tokens": res.total_completion_tokens,
        "source_to_target": s2t_m,
        "target_to_source": t2s_m,
        "reciprocal": final_m,
        "merger_details": res.merger_details,
    }

    return res, summary, val_rows


def main():
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    ref_path = PROJECT_ROOT.parent / "original_repo/data/conference/cmt-confof/component/reference.xml"
    reference_pairs = load_reference_alignment(ref_path)
    print(f"Loaded {len(reference_pairs)} reference correspondences from {ref_path.name}\n", flush=True)

    db = DatabaseManager()
    ensure_database_populated(db)

    llm = ChatOllama(
        model=config.default_llm,
        temperature=config.temperature,
        num_ctx=config.num_ctx,
        reasoning=False,
    )
    validator = MatchingValidator(llm=llm, context=config.context)
    merger = ReciprocalMerger()

    thresholds_to_run = [0.875, 0.850, 0.900]
    all_summaries: Dict[str, Any] = {}
    all_val_rows: List[Dict[str, Any]] = []

    for tau in thresholds_to_run:
        print(f"========================================================", flush=True)
        print(f"Executing Full Pipeline at tau = {tau:.3f}", flush=True)
        print(f"========================================================", flush=True)

        res, summary, val_rows = run_pipeline_for_threshold(db, validator, merger, tau, reference_pairs)
        all_summaries[str(tau)] = summary
        all_val_rows.extend(val_rows)

        s2t = summary["source_to_target"]
        t2s = summary["target_to_source"]
        rec = summary["reciprocal"]

        print(f"Result for tau = {tau:.3f}:", flush=True)
        print(f"  Source->Target: {s2t['predicted_count']} pairs | TP={s2t['tp']}, FP={s2t['fp']}, FN={s2t['fn']} | P={s2t['precision']}%, R={s2t['recall']}%, F1={s2t['f1']}%", flush=True)
        print(f"  Target->Source: {t2s['predicted_count']} pairs | TP={t2s['tp']}, FP={t2s['fp']}, FN={t2s['fn']} | P={t2s['precision']}%, R={t2s['recall']}%, F1={t2s['f1']}%", flush=True)
        print(f"  Reciprocal    : {rec['predicted_count']} pairs | TP={rec['tp']}, FP={rec['fp']}, FN={rec['fn']} | P={rec['precision']}%, R={rec['recall']}%, F1={rec['f1']}%", flush=True)
        print(f"  Workload      : {summary['validation_calls']} LLM calls ({summary['llm_accepts']} yes, {summary['llm_rejects']} no), {summary['bypasses']} bypasses", flush=True)
        print(f"  Efficiency    : {summary['prompt_tokens']} prompt tokens, {summary['completion_tokens']} completion tokens, {summary['duration_s']}s\n", flush=True)

        # If tau == 0.875, save specific predictions CSV
        if tau == 0.875:
            pred_875_path = output_dir / "step7b_predictions_tau_875.csv"
            pred_rows = [{"Entity1": p[0], "Entity2": p[1]} for p in sorted(list(res.final_predictions))]
            pd.DataFrame(pred_rows).to_csv(pred_875_path, index=False)
            print(f"Saved tau=0.875 predictions to {pred_875_path}", flush=True)

    # Save all validation logs
    df_val = pd.DataFrame(all_val_rows)
    val_logs_path = output_dir / "step7b_validation_logs.csv"
    df_val.to_csv(val_logs_path, index=False)
    print(f"Saved {len(df_val)} validation log entries to {val_logs_path}", flush=True)

    # Build Comparison Table for 0.850, 0.875, 0.900
    comparison_rows = []
    for tau in [0.850, 0.875, 0.900]:
        s = all_summaries[str(tau)]
        comparison_rows.append({
            "threshold": tau,
            "s2t_pred": s["source_to_target"]["predicted_count"],
            "s2t_tp": s["source_to_target"]["tp"],
            "s2t_fp": s["source_to_target"]["fp"],
            "s2t_fn": s["source_to_target"]["fn"],
            "s2t_precision": s["source_to_target"]["precision"],
            "s2t_recall": s["source_to_target"]["recall"],
            "s2t_f1": s["source_to_target"]["f1"],
            "t2s_pred": s["target_to_source"]["predicted_count"],
            "t2s_tp": s["target_to_source"]["tp"],
            "t2s_fp": s["target_to_source"]["fp"],
            "t2s_fn": s["target_to_source"]["fn"],
            "t2s_precision": s["target_to_source"]["precision"],
            "t2s_recall": s["target_to_source"]["recall"],
            "t2s_f1": s["target_to_source"]["f1"],
            "recip_pred": s["reciprocal"]["predicted_count"],
            "recip_tp": s["reciprocal"]["tp"],
            "recip_fp": s["reciprocal"]["fp"],
            "recip_fn": s["reciprocal"]["fn"],
            "recip_precision": s["reciprocal"]["precision"],
            "recip_recall": s["reciprocal"]["recall"],
            "recip_f1": s["reciprocal"]["f1"],
            "llm_calls": s["validation_calls"],
            "bypasses": s["bypasses"],
            "llm_accepts": s["llm_accepts"],
            "llm_rejects": s["llm_rejects"],
            "prompt_tokens": s["prompt_tokens"],
            "completion_tokens": s["completion_tokens"],
            "duration_s": s["duration_s"],
        })

    df_comp = pd.DataFrame(comparison_rows)
    comp_path = output_dir / "step7b_threshold_comparison.csv"
    df_comp.to_csv(comp_path, index=False)
    print(f"Saved comparison table to {comp_path}", flush=True)

    # Build Detailed Validation Decisions CSV
    val_decision_rows = []
    ref_norm_set = set(reference_pairs)
    for r in all_val_rows:
        s_uri = r["source_uri"]
        t_uri = r["target_uri"]
        is_gt = (s_uri, t_uri) in ref_norm_set
        dec = r["decision"]
        bypassed = r["bypassed"]

        failure_type = "None"
        if is_gt and dec == "no":
            failure_type = "False Negative (GT Rejected)"
        elif not is_gt and dec == "yes":
            failure_type = "False Positive (Non-GT Accepted)"
        elif dec == "error":
            failure_type = "Parsing/Execution Error"

        val_decision_rows.append({
            "threshold": r["experiment_tau"],
            "direction": r["direction"],
            "source_name": r["source_name"],
            "target_name": r["target_name"],
            "source_uri": s_uri,
            "target_uri": t_uri,
            "bypassed": bypassed,
            "is_ground_truth": is_gt,
            "decision": dec,
            "failure_type": failure_type,
            "prompt": r["prompt"] or "Bypassed by exact-name rule",
            "raw_response": r["raw_response"] or "Bypassed",
            "duration_ms": r["duration_ms"],
            "prompt_tokens": r["prompt_tokens"],
            "completion_tokens": r["completion_tokens"],
        })

    df_decisions = pd.DataFrame(val_decision_rows)
    decisions_path = output_dir / "step7b_validation_decisions.csv"
    df_decisions.to_csv(decisions_path, index=False)
    print(f"Saved {len(df_decisions)} validation decisions to {decisions_path}", flush=True)

    # Build Similarity Analysis CSV for all 16 reference correspondences
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT entity_id, entity_uri, source_or_target, entity_type FROM ontology_matching;")
            db_rows = cur.fetchall()

    uri_to_eid = {r[1]: r[0] for r in db_rows}
    eid_to_type = {r[0]: r[3] for r in db_rows}
    strategies = ["syntactic_matching", "lexical_matching", "semantic_matching"]

    def get_directional_sim(query_eid: str, target_eid: str, table_name: str) -> float:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT embedding FROM {table_name} WHERE entity_id = %s;", (query_eid,))
                q_row = cur.fetchone()
                if not q_row:
                    return 0.0
                q_emb = q_row[0]
                cur.execute(f"SELECT 1 - (embedding <=> %s) FROM {table_name} WHERE entity_id = %s;", (q_emb, target_eid))
                t_rows = cur.fetchall()
                if not t_rows:
                    return 0.0
                return max(r[0] for r in t_rows)

    sim_analysis_rows = []
    for src_uri, tgt_uri in sorted(list(reference_pairs), key=lambda x: uri_to_name(x[0])):
        s_eid = uri_to_eid.get(src_uri, "")
        t_eid = uri_to_eid.get(tgt_uri, "")
        s_name = uri_to_name(src_uri)
        t_name = uri_to_name(tgt_uri)

        sim_row = {
            "source_name": s_name,
            "target_name": t_name,
            "source_uri": src_uri,
            "target_uri": tgt_uri,
            "entity_type": eid_to_type.get(s_eid, "Unknown"),
        }

        for strat in strategies:
            prefix = strat.split("_")[0]
            s2t = get_directional_sim(s_eid, t_eid, strat)
            t2s = get_directional_sim(t_eid, s_eid, strat)
            sim_row[f"{prefix}_sim_s2t"] = round(s2t, 4)
            sim_row[f"{prefix}_sim_t2s"] = round(t2s, 4)

        max_s2t = max(sim_row["syntactic_sim_s2t"], sim_row["lexical_sim_s2t"], sim_row["semantic_sim_s2t"])
        max_t2s = max(sim_row["syntactic_sim_t2s"], sim_row["lexical_sim_t2s"], sim_row["semantic_sim_t2s"])
        sim_row["max_sim_s2t"] = round(max_s2t, 4)
        sim_row["max_sim_t2s"] = round(max_t2s, 4)
        sim_row["min_eligible_threshold_s2t"] = round(max_s2t, 4)
        sim_row["min_eligible_threshold_t2s"] = round(max_t2s, 4)
        sim_row["retrievable_at_800_s2t"] = max_s2t >= 0.800
        sim_row["retrievable_at_800_t2s"] = max_t2s >= 0.800
        sim_row["reciprocal_retrievable_at_800"] = (max_s2t >= 0.800) and (max_t2s >= 0.800)
        sim_row["unretrieved_reason"] = (
            "All directional representations < 0.800" if (max_s2t < 0.800 or max_t2s < 0.800) else "Retrievable at tau <= " + str(min(max_s2t, max_t2s))
        )
        sim_analysis_rows.append(sim_row)

    df_sim = pd.DataFrame(sim_analysis_rows)
    sim_path = output_dir / "step7b_similarity_analysis.csv"
    df_sim.to_csv(sim_path, index=False)
    print(f"Saved similarity analysis for {len(df_sim)} reference pairs to {sim_path}", flush=True)

    # Save summary JSON
    json_path = output_dir / "step7b_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)
    print(f"Saved step7b summary JSON to {json_path}", flush=True)


if __name__ == "__main__":
    main()
