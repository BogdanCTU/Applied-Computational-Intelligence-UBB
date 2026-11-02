"""
Step 7D.1: Prompt-Order Reproducibility Check.

Verifies the reproducibility and stability of Experiment A2 results by executing
3 independent repetitions of:
1. A2.1 Original ordering (mode='original')
2. A2.3 Canonical ordering (mode='canonical')

All runs start from the identical frozen candidate snapshot at tau = 0.850.
Uses local Ollama qwen3.5:9b (temperature=0.0).

Outputs:
- output/step7d1_reproducibility.csv
- output/step7d1_summary.json
- output/step7d1_validation_decisions.csv
- docs/step7d1_reproducibility_report.md
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from langchain_ollama import ChatOllama

# Ensure project root in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import config
from src.db.database_manager import DatabaseManager
from src.matching.merger import ReciprocalMerger
from scripts.run_experiments_step6 import ensure_database_populated
from scripts.run_step7d_prompt_order_ablation import (
    DirectionalOrderValidator,
    calculate_metrics,
    extract_candidate_snapshot,
    load_reference_alignment,
    run_variant_on_snapshot,
)


def run_reproducibility_study(
    num_runs: int = 3,
    tau: float = 0.850,
    top_k: int = 3,
    rrf_k: int = 0,
) -> Tuple[pd.DataFrame, Dict[str, Any], pd.DataFrame]:
    """
    Executes num_runs repetitions for A2.1 (Original) and A2.3 (Canonical).
    """
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    ref_path = PROJECT_ROOT.parent / "original_repo/data/conference/cmt-confof/component/reference.xml"
    reference_pairs = load_reference_alignment(ref_path)
    print(f"Loaded {len(reference_pairs)} reference correspondences from reference.xml", flush=True)

    db = DatabaseManager()
    ensure_database_populated(db)

    # 1. Freeze single candidate snapshot at tau = 0.850
    candidate_snapshot = extract_candidate_snapshot(db, tau=tau, top_k=top_k, rrf_k=rrf_k)

    # 2. Setup Ollama LLM and Merger
    llm = ChatOllama(
        model=config.default_llm,
        temperature=config.temperature,
        num_ctx=config.num_ctx,
        reasoning=False,
    )
    merger = ReciprocalMerger()

    experiment_plan = [
        ("A2.1_Original", "original"),
        ("A2.3_Canonical", "canonical"),
    ]

    all_summaries: Dict[str, Any] = {
        "metadata": {
            "num_runs": num_runs,
            "tau": tau,
            "top_k": top_k,
            "rrf_k": rrf_k,
            "model": config.default_llm,
            "temperature": config.temperature,
            "reference_count": len(reference_pairs),
        },
        "runs": {},
        "stability_analysis": {},
    }

    all_decisions: List[Dict[str, Any]] = []
    comparison_rows = []

    for base_name, mode in experiment_plan:
        run_results_for_mode = []

        for run_idx in range(1, num_runs + 1):
            run_key = f"{base_name}_Run{run_idx}"
            print(f"\n========================================================", flush=True)
            print(f"Executing: {run_key} (Mode: {mode}, Run: {run_idx}/{num_runs})", flush=True)
            print(f"========================================================", flush=True)

            validator = DirectionalOrderValidator(mode=mode, llm=llm, context=config.context)
            stats, rec_dicts, final_preds = run_variant_on_snapshot(
                db=db,
                validator=validator,
                merger=merger,
                candidate_snapshot=candidate_snapshot,
                variant_name=run_key,
                top_k=top_k,
            )

            # Annotate decision records with run_index and mode
            for r in rec_dicts:
                r["base_variant"] = base_name
                r["mode"] = mode
                r["run_index"] = run_idx
            all_decisions.extend(rec_dicts)

            s2t_m = calculate_metrics(stats["s2t_predicted_pairs"], reference_pairs)
            t2s_m = calculate_metrics(stats["t2s_predicted_pairs"], reference_pairs)
            rec_m = calculate_metrics(final_preds, reference_pairs)

            print(f"[{run_key}] S->T : {s2t_m['predicted_count']} pairs | TP={s2t_m['tp']}, FP={s2t_m['fp']} | P={s2t_m['precision']}%, R={s2t_m['recall']}%, F1={s2t_m['f1']}%", flush=True)
            print(f"[{run_key}] T->S : {t2s_m['predicted_count']} pairs | TP={t2s_m['tp']}, FP={t2s_m['fp']} | P={t2s_m['precision']}%, R={t2s_m['recall']}%, F1={t2s_m['f1']}%", flush=True)
            print(f"[{run_key}] Recip: {rec_m['predicted_count']} pairs | TP={rec_m['tp']}, FP={rec_m['fp']} | P={rec_m['precision']}%, R={rec_m['recall']}%, F1={rec_m['f1']}%", flush=True)
            print(f"[{run_key}] LLM calls: {stats['llm_calls']} ({stats['llm_accepts']} yes, {stats['llm_rejects']} no), Bypasses: {stats['bypasses']}, Time: {stats['duration_s']}s", flush=True)

            # Check specific target pair ProgramCommitteeChair <-> Chair_PC
            pcc_s2t = ("http://cmt#ProgramCommitteeChair", "http://confOf#Chair_PC") in stats["s2t_predicted_pairs"]
            pcc_t2s = ("http://cmt#ProgramCommitteeChair", "http://confOf#Chair_PC") in stats["t2s_predicted_pairs"]
            pcc_recip = ("http://cmt#ProgramCommitteeChair", "http://confOf#Chair_PC") in final_preds

            stats_for_summary = dict(stats)
            stats_for_summary.pop("s2t_predicted_pairs")
            stats_for_summary.pop("t2s_predicted_pairs")
            stats_for_summary.pop("final_predicted_pairs")

            run_record = {
                "stats": stats_for_summary,
                "s2t_metrics": s2t_m,
                "t2s_metrics": t2s_m,
                "reciprocal_metrics": rec_m,
                "pcc_chair_pc_status": {
                    "source_to_target": pcc_s2t,
                    "target_to_source": pcc_t2s,
                    "reciprocal": pcc_recip,
                },
            }
            all_summaries["runs"][run_key] = run_record
            run_results_for_mode.append(run_record)

            comparison_rows.append({
                "run_key": run_key,
                "variant": base_name,
                "mode": mode,
                "run_index": run_idx,
                "llm_calls": stats["llm_calls"],
                "bypasses": stats["bypasses"],
                "llm_accepts": stats["llm_accepts"],
                "llm_rejects": stats["llm_rejects"],
                "prompt_tokens": stats["prompt_tokens"],
                "completion_tokens": stats["completion_tokens"],
                "duration_s": stats["duration_s"],
                "s2t_pred": s2t_m["predicted_count"],
                "s2t_tp": s2t_m["tp"],
                "s2t_fp": s2t_m["fp"],
                "s2t_fn": s2t_m["fn"],
                "s2t_precision": s2t_m["precision"],
                "s2t_recall": s2t_m["recall"],
                "s2t_f1": s2t_m["f1"],
                "t2s_pred": t2s_m["predicted_count"],
                "t2s_tp": t2s_m["tp"],
                "t2s_fp": t2s_m["fp"],
                "t2s_fn": t2s_m["fn"],
                "t2s_precision": t2s_m["precision"],
                "t2s_recall": t2s_m["recall"],
                "t2s_f1": t2s_m["f1"],
                "recip_pred": rec_m["predicted_count"],
                "recip_tp": rec_m["tp"],
                "recip_fp": rec_m["fp"],
                "recip_fn": rec_m["fn"],
                "recip_precision": rec_m["precision"],
                "recip_recall": rec_m["recall"],
                "recip_f1": rec_m["f1"],
                "pcc_s2t": pcc_s2t,
                "pcc_t2s": pcc_t2s,
                "pcc_recip": pcc_recip,
            })

        # Calculate stability for this mode
        f1_list = [r["reciprocal_metrics"]["f1"] for r in run_results_for_mode]
        pcc_recip_list = [r["pcc_chair_pc_status"]["reciprocal"] for r in run_results_for_mode]
        all_summaries["stability_analysis"][base_name] = {
            "reciprocal_f1_runs": f1_list,
            "f1_variance": round(max(f1_list) - min(f1_list), 4),
            "perfectly_consistent": (len(set(f1_list)) == 1),
            "pcc_chair_pc_all_matched": all(pcc_recip_list),
            "pcc_chair_pc_all_dropped": not any(pcc_recip_list),
        }

    df_comp = pd.DataFrame(comparison_rows)
    df_decisions = pd.DataFrame(all_decisions)

    # Save CSVs
    repro_csv = output_dir / "step7d1_reproducibility.csv"
    df_comp.to_csv(repro_csv, index=False)
    print(f"\nSaved reproducibility comparison table to {repro_csv}", flush=True)

    dec_csv = output_dir / "step7d1_validation_decisions.csv"
    df_decisions.to_csv(dec_csv, index=False)
    print(f"Saved {len(df_decisions)} validation decisions to {dec_csv}", flush=True)

    # Save summary JSON
    sum_json = output_dir / "step7d1_summary.json"
    with open(sum_json, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)
    print(f"Saved summary JSON to {sum_json}", flush=True)

    return df_comp, all_summaries, df_decisions


def main():
    run_reproducibility_study(num_runs=3, tau=0.850, top_k=3, rrf_k=0)


if __name__ == "__main__":
    main()

