"""
Comprehensive Step 6 Experiment Runner for Agent-OM Local Reproduction.

Executes:
1. E1: Full pipeline (Validation enabled, Reciprocal Merger enabled)
2. E5: No LLM Validation ablation (Validation disabled, Reciprocal Merger enabled)
3. E6: No Reciprocal Merger ablation (Validation enabled, Reciprocal Merger disabled -> Source->Target)
4. E7: Full pipeline repeated runs (Runs 1, 2, 3) to test determinism at temperature=0.0

Logs:
- Stage-by-stage metrics (Directional S->T, Directional T->S, Reciprocal Merger)
- Validation records (prompt, response, decision, bypass, latency, tokens)
- Precision, Recall, F1, TP, FP, FN at every stage
- Reconciliation against Reference Alignment, committed predict.csv, and published baseline.
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
from langchain_ollama import ChatOllama, OllamaEmbeddings

# Ensure project root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.matching_agent import MatchingAgent, PipelineResult
from src.config import config
from src.db.database_manager import DatabaseManager
from src.matching.merger import ReciprocalMerger
from src.matching.validator import MatchingValidator, ValidationRecord
from src.utils.text_processing import uri_to_name


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


def ensure_database_populated(db: DatabaseManager) -> None:
    """Verifies that the 162 entities and 768-dim embeddings exist in PostgreSQL."""
    db.init_extensions()
    entity_count = 0
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM ontology_matching;")
                entity_count = cur.fetchone()[0]
    except Exception:
        entity_count = 0

    if entity_count < 162:
        print(f"Database contains {entity_count} entities (< 162). Ingesting full CMT-ConfOf dataset...", flush=True)
        csv_path = PROJECT_ROOT.parent / "original_repo/alignment/conference/cmt-confof/component/ontology_matching.csv"
        df_full = pd.read_csv(csv_path)
        num_digits = len(str(df_full.index.max() + 1))
        df_full["entity_id"] = (
            (df_full.index + 1).astype(str).str.zfill(num_digits)
            + "-"
            + df_full["source_or_target"].astype(str)
            + "-"
            + df_full["entity_type"].astype(str)
            + "-"
            + df_full["entity"].apply(uri_to_name)
        )
        df_full = df_full.rename(columns={"entity": "entity_uri"})
        df_full = df_full.fillna("")
        df_full.replace(config.null_value_sentence, "", inplace=True)

        emb_service = OllamaEmbeddings(model="nomic-embed-text")
        db.create_ontology_matching_table(df_full)
        print("Created ontology_matching table (162 entities).", flush=True)
        syn_c = db.create_embedding_table("syntactic_matching", df_full, emb_service, vector_length=768)
        print(f"Created syntactic_matching table ({syn_c} chunks).", flush=True)
        lex_c = db.create_embedding_table("lexical_matching", df_full, emb_service, vector_length=768)
        print(f"Created lexical_matching table ({lex_c} chunks).", flush=True)
        sem_c = db.create_embedding_table("semantic_matching", df_full, emb_service, vector_length=768)
        print(f"Created semantic_matching table ({sem_c} chunks).", flush=True)
    else:
        print(f"Database verified with {entity_count} entities.", flush=True)


def export_predictions_csv(pairs: Set[Tuple[str, str]], filepath: Path) -> None:
    """Exports predicted correspondences in standard CSV format: Entity1,Entity2."""
    rows = [{"Entity1": p[0], "Entity2": p[1]} for p in sorted(list(pairs))]
    df = pd.DataFrame(rows)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"Saved {len(rows)} predictions to {filepath}", flush=True)


def run_experiment(
    agent: MatchingAgent,
    exp_id: str,
    validate: bool,
    reciprocal_merger: bool,
    reference_pairs: Set[Tuple[str, str]],
    output_dir: Path,
) -> Dict[str, Any]:
    """Runs a single matching experiment and evaluates all intermediate and final outputs."""
    print(f"\n==========================================", flush=True)
    print(f"Running Experiment {exp_id} (Validate={validate}, Merger={reciprocal_merger})", flush=True)
    print(f"==========================================", flush=True)

    result: PipelineResult = agent.run_pipeline(
        experiment_id=exp_id,
        validate=validate,
        reciprocal_merger=reciprocal_merger,
    )

    # Calculate metrics at each stage
    s2t_metrics = calculate_metrics(result.source_to_target.predicted_pairs, reference_pairs)
    t2s_metrics = calculate_metrics(result.target_to_source.predicted_pairs, reference_pairs)
    final_metrics = calculate_metrics(result.final_predictions, reference_pairs)

    print(f"[{exp_id}] Source->Target: {s2t_metrics['predicted_count']} pairs | TP={s2t_metrics['tp']}, FP={s2t_metrics['fp']}, FN={s2t_metrics['fn']} | P={s2t_metrics['precision']}%, R={s2t_metrics['recall']}%, F1={s2t_metrics['f1']}%", flush=True)
    print(f"[{exp_id}] Target->Source: {t2s_metrics['predicted_count']} pairs | TP={t2s_metrics['tp']}, FP={t2s_metrics['fp']}, FN={t2s_metrics['fn']} | P={t2s_metrics['precision']}%, R={t2s_metrics['recall']}%, F1={t2s_metrics['f1']}%", flush=True)
    print(f"[{exp_id}] Final Result  : {final_metrics['predicted_count']} pairs | TP={final_metrics['tp']}, FP={final_metrics['fp']}, FN={final_metrics['fn']} | P={final_metrics['precision']}%, R={final_metrics['recall']}%, F1={final_metrics['f1']}%", flush=True)
    print(f"[{exp_id}] Time: {result.total_duration_s:.2f}s | LLM calls: {result.total_validation_calls} | Bypasses: {result.total_bypasses}", flush=True)

    # Save prediction CSV
    pred_csv = output_dir / f"{exp_id.lower()}_predictions.csv"
    export_predictions_csv(result.final_predictions, pred_csv)

    return {
        "experiment_id": exp_id,
        "validation_enabled": validate,
        "reciprocal_merger_enabled": reciprocal_merger,
        "duration_seconds": round(result.total_duration_s, 2),
        "validation_calls": result.total_validation_calls,
        "bypasses": result.total_bypasses,
        "total_prompt_tokens": result.total_prompt_tokens,
        "total_completion_tokens": result.total_completion_tokens,
        "source_to_target_metrics": s2t_metrics,
        "target_to_source_metrics": t2s_metrics,
        "final_metrics": final_metrics,
        "merger_details": result.merger_details,
        "validation_records": [asdict(r) for r in (result.source_to_target.validation_records + result.target_to_source.validation_records)],
    }


def main():
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    ref_path = PROJECT_ROOT.parent / "original_repo/data/conference/cmt-confof/component/reference.xml"
    reference_pairs = load_reference_alignment(ref_path)
    print(f"Loaded {len(reference_pairs)} reference correspondences from reference.xml", flush=True)

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
    agent = MatchingAgent(db_manager=db, validator=validator, merger=merger)

    all_experiments: Dict[str, Any] = {}
    all_validation_records: List[Dict[str, Any]] = []

    # 1. Run E1 (Full Pipeline)
    e1_data = run_experiment(agent, "E1", validate=True, reciprocal_merger=True, reference_pairs=reference_pairs, output_dir=output_dir)
    all_experiments["E1"] = e1_data
    for r in e1_data["validation_records"]:
        r["experiment_id"] = "E1"
        all_validation_records.append(r)

    # 2. Run E5 (No LLM Validation Ablation)
    e5_data = run_experiment(agent, "E5", validate=False, reciprocal_merger=True, reference_pairs=reference_pairs, output_dir=output_dir)
    all_experiments["E5"] = e5_data

    # 3. Run E6 (No Reciprocal Merger Ablation)
    e6_data = run_experiment(agent, "E6", validate=True, reciprocal_merger=False, reference_pairs=reference_pairs, output_dir=output_dir)
    all_experiments["E6"] = e6_data
    for r in e6_data["validation_records"]:
        r["experiment_id"] = "E6"
        all_validation_records.append(r)

    # 4. Run E7 (Repeated Determinism Evaluation: 3 runs)
    print("\n==========================================", flush=True)
    print("Running E7 Repeated Runs (Testing Determinism at temp=0.0)", flush=True)
    print("==========================================", flush=True)
    e7_runs = []
    for run_idx in range(1, 4):
        run_name = f"E7_Run{run_idx}"
        e7_run_data = run_experiment(agent, run_name, validate=True, reciprocal_merger=True, reference_pairs=reference_pairs, output_dir=output_dir)
        e7_runs.append(e7_run_data)
        for r in e7_run_data["validation_records"]:
            r["experiment_id"] = run_name
            all_validation_records.append(r)

    all_experiments["E7"] = {
        "runs": e7_runs,
        "is_deterministic": (
            e7_runs[0]["final_metrics"]["predicted_count"] == e7_runs[1]["final_metrics"]["predicted_count"] == e7_runs[2]["final_metrics"]["predicted_count"]
            and e7_runs[0]["final_metrics"]["f1"] == e7_runs[1]["final_metrics"]["f1"] == e7_runs[2]["final_metrics"]["f1"]
            and e7_runs[0]["validation_calls"] == e7_runs[1]["validation_calls"] == e7_runs[2]["validation_calls"]
        ),
    }

    # Save validation records to CSV
    if all_validation_records:
        val_df = pd.DataFrame(all_validation_records)
        val_csv_path = output_dir / "step6_validation_logs.csv"
        val_df.to_csv(val_csv_path, index=False)
        print(f"\nSaved {len(val_df)} validation records to {val_csv_path}", flush=True)

    # Strip raw validation records from summary JSON for conciseness
    summary_data = {}
    for k, v in all_experiments.items():
        if k == "E7":
            summary_data[k] = {
                "is_deterministic": v["is_deterministic"],
                "runs": [
                    {rk: rv for rk, rv in run_d.items() if rk != "validation_records"}
                    for run_d in v["runs"]
                ]
            }
        else:
            summary_data[k] = {rk: rv for rk, rv in v.items() if rk != "validation_records"}

    summary_json_path = output_dir / "step6_experiments_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Saved complete experiments summary to {summary_json_path}", flush=True)


if __name__ == "__main__":
    main()
