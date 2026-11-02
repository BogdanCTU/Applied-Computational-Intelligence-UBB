"""
Step 7A: Similarity Threshold Sensitivity Analysis for Agent-OM Local.

Systematically evaluates cosine similarity thresholds:
[0.800, 0.825, 0.850, 0.875, 0.900, 0.925, 0.950]

Phase 1: Retrieval-Only Analysis (All 7 thresholds, 0 LLM calls)
- Evaluates Syntactic, Lexical, Semantic, Candidate Union, and RRF-fused rankings.
- Tracks candidate count, TP, FP, FN, Precision, Recall, F1.
- Identifies which reference correspondences become retrievable as threshold decreases.

Phase 2: Full Pipeline Analysis (Selected informative thresholds + 0.900 reference)
- Runs full pipeline with local Qwen 3.5 9B validation and reciprocal merger.
- Measures final impact on Precision, Recall, and F1.
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
from src.matching.validator import MatchingValidator
from src.retrieval.rank_fusion import reciprocal_rank_fusion
from src.utils.text_processing import uri_to_name


THRESHOLDS = [0.800, 0.825, 0.850, 0.875, 0.900, 0.925, 0.950]
REFERENCE_THRESHOLD = 0.900


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


def run_phase1_retrieval(
    db: DatabaseManager,
    reference_pairs: Set[Tuple[str, str]],
    thresholds: List[float],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Phase 1: Evaluates candidate retrieval across all thresholds without LLM validation.
    """
    print("\n========================================================", flush=True)
    print("PHASE 1: RETRIEVAL-ONLY ANALYSIS ACROSS ALL 7 THRESHOLDS", flush=True)
    print("========================================================", flush=True)

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT entity_id, entity_uri, source_or_target, entity_type FROM ontology_matching ORDER BY entity_id;")
            all_rows = cur.fetchall()

    entity_map = {r[0]: {"uri": r[1], "source_or_target": r[2], "type": r[3]} for r in all_rows}
    source_eids = [r[0] for r in all_rows if r[2] == "Source"]
    target_eids = [r[0] for r in all_rows if r[2] == "Target"]

    strategies = ["syntactic_matching", "lexical_matching", "semantic_matching"]
    results_tabular: List[Dict[str, Any]] = []
    threshold_details: Dict[str, Any] = {}

    for tau in thresholds:
        t0 = time.perf_counter()
        print(f"\n--- Evaluating Threshold tau = {tau:.3f} ---", flush=True)

        # 1. Strategy-by-strategy retrieval
        strat_candidates: Dict[str, Dict[str, Set[Tuple[str, str]]]] = {
            s: {"S2T": set(), "T2S": set(), "Union": set()} for s in strategies
        }
        all_retrieved_pairs_s2t: Set[Tuple[str, str]] = set()
        all_retrieved_pairs_t2s: Set[Tuple[str, str]] = set()

        # Source -> Target retrieval
        s2t_strategy_rankings: Dict[str, Dict[str, List[str]]] = {eid: {} for eid in source_eids}
        for eid in source_eids:
            for strat in strategies:
                cands = db.query_strategy(
                    entity_id=eid,
                    table_name=strat,
                    similarity_threshold=tau,
                    num_matches=config.num_matches,
                    top_k=config.top_k,
                )
                valid = [c for c in cands if c != config.null_value_matching]
                s2t_strategy_rankings[eid][strat] = valid
                for cid in valid:
                    src_uri = entity_map[eid]["uri"]
                    tgt_uri = entity_map[cid]["uri"]
                    pair = (src_uri, tgt_uri)
                    strat_candidates[strat]["S2T"].add(pair)
                    all_retrieved_pairs_s2t.add(pair)

        # Target -> Source retrieval
        t2s_strategy_rankings: Dict[str, Dict[str, List[str]]] = {eid: {} for eid in target_eids}
        for eid in target_eids:
            for strat in strategies:
                cands = db.query_strategy(
                    entity_id=eid,
                    table_name=strat,
                    similarity_threshold=tau,
                    num_matches=config.num_matches,
                    top_k=config.top_k,
                )
                valid = [c for c in cands if c != config.null_value_matching]
                t2s_strategy_rankings[eid][strat] = valid
                for cid in valid:
                    src_uri = entity_map[cid]["uri"]
                    tgt_uri = entity_map[eid]["uri"]
                    pair = (src_uri, tgt_uri)
                    strat_candidates[strat]["T2S"].add(pair)
                    all_retrieved_pairs_t2s.add(pair)

        # Strategy unions
        for strat in strategies:
            strat_candidates[strat]["Union"] = strat_candidates[strat]["S2T"].union(strat_candidates[strat]["T2S"])

        # Candidate Union across all strategies
        candidate_union_s2t = all_retrieved_pairs_s2t
        candidate_union_t2s = all_retrieved_pairs_t2s
        candidate_union_bidirectional = candidate_union_s2t.union(candidate_union_t2s)

        # 2. RRF-fused rankings (k=0)
        # Source -> Target
        rrf_s2t_top1 = set()
        rrf_s2t_top3 = set()
        for eid in source_eids:
            rankings = [s2t_strategy_rankings[eid][s] for s in strategies if s2t_strategy_rankings[eid][s]]
            if rankings:
                fused = reciprocal_rank_fusion(*rankings, k=0, exclude_items=[config.null_value_matching])
                flat = [item for _, items in fused for item in items]
                src_uri = entity_map[eid]["uri"]
                if flat:
                    rrf_s2t_top1.add((src_uri, entity_map[flat[0]]["uri"]))
                    for cid in flat[:config.top_k]:
                        rrf_s2t_top3.add((src_uri, entity_map[cid]["uri"]))

        # Target -> Source
        rrf_t2s_top1 = set()
        rrf_t2s_top3 = set()
        for eid in target_eids:
            rankings = [t2s_strategy_rankings[eid][s] for s in strategies if t2s_strategy_rankings[eid][s]]
            if rankings:
                fused = reciprocal_rank_fusion(*rankings, k=0, exclude_items=[config.null_value_matching])
                flat = [item for _, items in fused for item in items]
                tgt_uri = entity_map[eid]["uri"]
                if flat:
                    rrf_t2s_top1.add((entity_map[flat[0]]["uri"], tgt_uri))
                    for cid in flat[:config.top_k]:
                        rrf_t2s_top3.add((entity_map[cid]["uri"], tgt_uri))

        # Reciprocal merger of RRF Top-1 (E5 logic: RRF Top-1 with reciprocal intersection)
        rrf_top1_reciprocal = rrf_s2t_top1.intersection(rrf_t2s_top1)
        rrf_top3_reciprocal = rrf_s2t_top3.intersection(rrf_t2s_top3)

        elapsed = time.perf_counter() - t0

        # Calculate metrics for each view
        def record_row(cat: str, subcat: str, pairs: Set[Tuple[str, str]]):
            m = calculate_metrics(pairs, reference_pairs)
            row = {
                "threshold": tau,
                "category": cat,
                "sub_category": subcat,
                "candidate_count": m["predicted_count"],
                "tp": m["tp"],
                "fp": m["fp"],
                "fn": m["fn"],
                "precision": m["precision"],
                "recall": m["recall"],
                "f1": m["f1"],
                "duration_s": round(elapsed, 2),
            }
            results_tabular.append(row)
            return m

        # Log individual strategies
        for strat in strategies:
            record_row(strat, "Source->Target", strat_candidates[strat]["S2T"])
            record_row(strat, "Target->Source", strat_candidates[strat]["T2S"])
            record_row(strat, "Union", strat_candidates[strat]["Union"])

        # Log Candidate Union
        record_row("Candidate_Union", "Source->Target", candidate_union_s2t)
        record_row("Candidate_Union", "Target->Source", candidate_union_t2s)
        m_cu_union = record_row("Candidate_Union", "Bidirectional_Union", candidate_union_bidirectional)

        # Log RRF-fused
        record_row("RRF_k0", "Top1_S2T", rrf_s2t_top1)
        record_row("RRF_k0", "Top1_T2S", rrf_t2s_top1)
        m_top1_recip = record_row("RRF_k0", "Top1_Reciprocal_Merger", rrf_top1_reciprocal)

        record_row("RRF_k0", "Top3_S2T", rrf_s2t_top3)
        record_row("RRF_k0", "Top3_T2S", rrf_t2s_top3)
        record_row("RRF_k0", "Top3_Reciprocal_Merger", rrf_top3_reciprocal)

        retrievable_tps = sorted([fmt_pair(p) for p in m_cu_union["tp_pairs"]])
        print(f"[tau={tau:.3f}] Candidate Union Recall: {m_cu_union['recall']}% ({m_cu_union['tp']}/16 TPs) | Candidates: {m_cu_union['predicted_count']}", flush=True)
        print(f"[tau={tau:.3f}] RRF Top-1 Reciprocal F1: {m_top1_recip['f1']}% (TP={m_top1_recip['tp']}, FP={m_top1_recip['fp']})", flush=True)
        print(f"[tau={tau:.3f}] Retrievable Reference TPs ({len(retrievable_tps)}): {retrievable_tps}", flush=True)

        threshold_details[str(tau)] = {
            "threshold": tau,
            "duration_s": round(elapsed, 2),
            "candidate_union_metrics": m_cu_union,
            "rrf_top1_reciprocal_metrics": m_top1_recip,
            "retrievable_reference_correspondences": retrievable_tps,
        }

    return results_tabular, threshold_details


def run_phase2_full_pipeline(
    db: DatabaseManager,
    reference_pairs: Set[Tuple[str, str]],
    selected_thresholds: List[float],
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Phase 2: Runs full matching pipeline (validation + merger) on selected thresholds.
    """
    print("\n========================================================", flush=True)
    print("PHASE 2: FULL PIPELINE ANALYSIS ON SELECTED THRESHOLDS", flush=True)
    print("========================================================", flush=True)

    llm = ChatOllama(
        model=config.default_llm,
        temperature=config.temperature,
        num_ctx=config.num_ctx,
        reasoning=False,
    )
    validator = MatchingValidator(llm=llm, context=config.context)
    merger = ReciprocalMerger()

    phase2_results: Dict[str, Any] = {}

    for tau in selected_thresholds:
        print(f"\n========================================================", flush=True)
        print(f"Running Full Pipeline at tau = {tau:.3f} (LLM Validation + Reciprocal Merger)", flush=True)
        print(f"========================================================", flush=True)

        agent = MatchingAgent(
            db_manager=db,
            validator=validator,
            merger=merger,
            similarity_threshold=tau,
            top_k=config.top_k,
            num_matches=config.num_matches,
            rrf_k=0,
        )

        res: PipelineResult = agent.run_pipeline(
            experiment_id=f"FullPipeline_tau_{tau:.3f}",
            validate=True,
            reciprocal_merger=True,
        )

        s2t_m = calculate_metrics(res.source_to_target.predicted_pairs, reference_pairs)
        t2s_m = calculate_metrics(res.target_to_source.predicted_pairs, reference_pairs)
        final_m = calculate_metrics(res.final_predictions, reference_pairs)

        print(f"[tau={tau:.3f}] Source->Target: {s2t_m['predicted_count']} pairs | TP={s2t_m['tp']}, FP={s2t_m['fp']} | P={s2t_m['precision']}%, R={s2t_m['recall']}%, F1={s2t_m['f1']}%", flush=True)
        print(f"[tau={tau:.3f}] Target->Source: {t2s_m['predicted_count']} pairs | TP={t2s_m['tp']}, FP={t2s_m['fp']} | P={t2s_m['precision']}%, R={t2s_m['recall']}%, F1={t2s_m['f1']}%", flush=True)
        print(f"[tau={tau:.3f}] Final Result  : {final_m['predicted_count']} pairs | TP={final_m['tp']}, FP={final_m['fp']} | P={final_m['precision']}%, R={final_m['recall']}%, F1={final_m['f1']}%", flush=True)
        print(f"[tau={tau:.3f}] Time: {res.total_duration_s:.2f}s | LLM calls: {res.total_validation_calls} | Bypasses: {res.total_bypasses}", flush=True)

        # Export predictions
        pred_csv = output_dir / f"step7a_predictions_tau_{int(tau * 1000)}.csv"
        rows = [{"Entity1": p[0], "Entity2": p[1]} for p in sorted(list(res.final_predictions))]
        pd.DataFrame(rows).to_csv(pred_csv, index=False)

        phase2_results[str(tau)] = {
            "threshold": tau,
            "duration_s": round(res.total_duration_s, 2),
            "validation_calls": res.total_validation_calls,
            "bypasses": res.total_bypasses,
            "prompt_tokens": res.total_prompt_tokens,
            "completion_tokens": res.total_completion_tokens,
            "source_to_target_metrics": s2t_m,
            "target_to_source_metrics": t2s_m,
            "final_metrics": final_m,
            "merger_details": res.merger_details,
        }

    return phase2_results


def main():
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    ref_path = PROJECT_ROOT.parent / "original_repo/data/conference/cmt-confof/component/reference.xml"
    reference_pairs = load_reference_alignment(ref_path)
    print(f"Loaded {len(reference_pairs)} reference correspondences from reference.xml", flush=True)

    db = DatabaseManager()

    # PHASE 1: Retrieval-Only Analysis
    tabular_rows, phase1_details = run_phase1_retrieval(db, reference_pairs, THRESHOLDS)

    # Export Phase 1 Tabular CSV
    df_tabular = pd.DataFrame(tabular_rows)
    csv_out_path = output_dir / "step7a_threshold_sensitivity.csv"
    df_tabular.to_csv(csv_out_path, index=False)
    print(f"\nSaved {len(df_tabular)} retrieval evaluation rows to {csv_out_path}", flush=True)

    # Determine informative thresholds for Phase 2:
    # 1. 0.900 (Reference configuration)
    # 2. 0.850 (Threshold where ProgramCommitteeMember = Member_PC becomes retrievable)
    # 3. 0.800 (Lower bound testing maximum recall expansion)
    selected_thresholds = [0.800, 0.850, 0.900]
    print(f"\nSelected Informative Thresholds for Phase 2: {selected_thresholds}", flush=True)
    print("Reason: 0.900 is reference baseline; 0.850 captures ProgramCommitteeMember; 0.800 evaluates lower-bound recall limit.")

    # PHASE 2: Full Pipeline Analysis
    phase2_details = run_phase2_full_pipeline(db, reference_pairs, selected_thresholds, output_dir)

    # Save comprehensive JSON output
    summary_data = {
        "dataset": "cmt-confof",
        "embedding_model": "nomic-embed-text",
        "reference_threshold": REFERENCE_THRESHOLD,
        "evaluated_thresholds": THRESHOLDS,
        "selected_full_pipeline_thresholds": selected_thresholds,
        "phase1_retrieval_analysis": phase1_details,
        "phase2_full_pipeline_analysis": phase2_details,
    }

    json_out_path = output_dir / "step7a_threshold_sensitivity.json"
    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Saved complete Step 7A sensitivity JSON to {json_out_path}", flush=True)


if __name__ == "__main__":
    main()

