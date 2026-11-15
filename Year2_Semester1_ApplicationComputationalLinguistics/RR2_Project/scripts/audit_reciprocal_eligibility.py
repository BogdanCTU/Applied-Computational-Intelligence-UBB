"""
Step 7C Task 1: Reciprocal Candidate Eligibility Audit Script.

Computes the exact directional retrieval, similarity eligibility,
LLM validation acceptance, and reciprocal merger retention
for all 16 reference correspondences across thresholds 0.800, 0.850, 0.875, and 0.900.
Outputs agent_om_local/output/step7c_reciprocal_eligibility_audit.csv.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pandas as pd
import rdflib

# Project root in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import config
from src.db.database_manager import DatabaseManager
from src.utils.text_processing import uri_to_name


def load_reference_alignment(ref_path: Path) -> List[Tuple[str, str]]:
    g = rdflib.Graph().parse(ref_path)
    align_cell = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#Cell")
    align_e1 = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#entity1")
    align_e2 = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#entity2")
    align_rel = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#relation")

    ref_pairs = []
    for s in g.subjects(rdflib.RDF.type, align_cell):
        rel = str(g.value(s, align_rel, None))
        if rel == "=":
            e1 = str(g.value(s, align_e1, None))
            e2 = str(g.value(s, align_e2, None))
            ref_pairs.append((e1, e2))
    return sorted(ref_pairs, key=lambda x: uri_to_name(x[0]))


def main():
    db = DatabaseManager()
    output_dir = PROJECT_ROOT / "output"
    ref_path = PROJECT_ROOT.parent / "original_repo/data/conference/cmt-confof/component/reference.xml"
    ref_pairs = load_reference_alignment(ref_path)

    # 1. Map URIs to entity_ids
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT entity_id, entity_uri, source_or_target, entity_type FROM ontology_matching;")
            db_rows = cur.fetchall()

    uri_to_eid = {r[1]: r[0] for r in db_rows}
    eid_to_type = {r[0]: r[3] for r in db_rows}

    # 2. Load existing historical results
    # Step 7B summary (has 0.850, 0.875, 0.900)
    step7b_summary = json.load(open(output_dir / "step7b_summary.json", encoding="utf-8"))
    step7a_summary = json.load(open(output_dir / "step7a_threshold_sensitivity.json", encoding="utf-8"))
    step7b_decisions = pd.read_csv(output_dir / "step7b_validation_decisions.csv")

    # Step 7A predictions for 0.800
    pred_800_df = pd.read_csv(output_dir / "step7a_predictions_tau_800.csv")
    pred_800_set = set(zip(pred_800_df["Entity1"], pred_800_df["Entity2"]))

    # Step 7B predictions for 0.850, 0.875, 0.900
    pred_850_df = pd.read_csv(output_dir / "step7a_predictions_tau_850.csv")
    pred_850_set = set(zip(pred_850_df["Entity1"], pred_850_df["Entity2"]))

    pred_875_df = pd.read_csv(output_dir / "step7b_predictions_tau_875.csv")
    pred_875_set = set(zip(pred_875_df["Entity1"], pred_875_df["Entity2"]))

    pred_900_df = pd.read_csv(output_dir / "step7a_predictions_tau_900.csv")
    pred_900_set = set(zip(pred_900_df["Entity1"], pred_900_df["Entity2"]))

    recip_sets = {
        0.800: pred_800_set,
        0.850: pred_850_set,
        0.875: pred_875_set,
        0.900: pred_900_set,
    }

    # Load directional predictions from summaries
    # 0.800 from step7a
    s2t_800_tps = set(tuple(p) for p in step7a_summary["phase2_full_pipeline_analysis"]["0.8"]["source_to_target_metrics"]["tp_pairs"])
    t2s_800_tps = set(tuple(p) for p in step7a_summary["phase2_full_pipeline_analysis"]["0.8"]["target_to_source_metrics"]["tp_pairs"])

    # 0.850, 0.875, 0.900 from step7b
    s2t_tps_by_tau = {
        0.800: s2t_800_tps,
        0.850: set(tuple(p) for p in step7b_summary["0.85"]["source_to_target"]["tp_pairs"]),
        0.875: set(tuple(p) for p in step7b_summary["0.875"]["source_to_target"]["tp_pairs"]),
        0.900: set(tuple(p) for p in step7b_summary["0.9"]["source_to_target"]["tp_pairs"]),
    }

    t2s_tps_by_tau = {
        0.800: t2s_800_tps,
        0.850: set(tuple(p) for p in step7b_summary["0.85"]["target_to_source"]["tp_pairs"]),
        0.875: set(tuple(p) for p in step7b_summary["0.875"]["target_to_source"]["tp_pairs"]),
        0.900: set(tuple(p) for p in step7b_summary["0.9"]["target_to_source"]["tp_pairs"]),
    }

    # Strategies to query
    strategies = ["syntactic_matching", "lexical_matching", "semantic_matching"]

    def get_actual_retrieval(query_eid: str, target_eid: str, tau: float) -> Tuple[bool, float]:
        """Checks if query_eid actually retrieves target_eid in any of the 3 strategies at threshold tau."""
        max_sim = 0.0
        retrieved = False
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                for strat in strategies:
                    cur.execute(f"SELECT embedding FROM {strat} WHERE entity_id = %s;", (query_eid,))
                    q_row = cur.fetchone()
                    if not q_row:
                        continue
                    q_emb = q_row[0]
                    cur.execute(f"SELECT 1 - (embedding <=> %s) FROM {strat} WHERE entity_id = %s;", (q_emb, target_eid))
                    t_rows = cur.fetchall()
                    if t_rows:
                        strat_max = max(r[0] for r in t_rows)
                        if strat_max > max_sim:
                            max_sim = strat_max
                        if strat_max >= tau:
                            retrieved = True
        return retrieved, round(max_sim, 4)

    audit_rows = []
    thresholds = [0.900, 0.875, 0.850, 0.800]

    for src_uri, tgt_uri in ref_pairs:
        s_name = uri_to_name(src_uri)
        t_name = uri_to_name(tgt_uri)
        s_eid = uri_to_eid.get(src_uri, "")
        t_eid = uri_to_eid.get(tgt_uri, "")
        etype = eid_to_type.get(s_eid, "Unknown")

        row: Dict[str, Any] = {
            "source_name": s_name,
            "target_name": t_name,
            "source_uri": src_uri,
            "target_uri": tgt_uri,
            "entity_type": etype,
        }

        # Check retrieval and metrics across all 4 thresholds
        for tau in thresholds:
            tau_str = f"{tau:.3f}"
            ret_s2t, sim_s2t = get_actual_retrieval(s_eid, t_eid, tau)
            ret_t2s, sim_t2s = get_actual_retrieval(t_eid, s_eid, tau)

            pair = (src_uri, tgt_uri)
            val_s2t = pair in s2t_tps_by_tau[tau]
            val_t2s = pair in t2s_tps_by_tau[tau]
            retained = pair in recip_sets[tau]

            # In directional set
            in_both_sets = ret_s2t and ret_t2s

            # Status determination
            if not ret_s2t and not ret_t2s:
                status = "Below_Threshold"
            elif ret_s2t != ret_t2s:
                status = "Directional_Retrieval_Asymmetry"
            elif not val_s2t and not val_t2s:
                status = "LLM_Validation_Rejected_Both"
            elif not val_s2t:
                status = "LLM_Validation_Rejected_S2T"
            elif not val_t2s:
                status = "LLM_Validation_Rejected_T2S"
            elif not retained:
                status = "Reciprocal_Merger_Dropped"
            else:
                status = "Retained_TP"

            row[f"sim_s2t_{tau_str}"] = sim_s2t
            row[f"sim_t2s_{tau_str}"] = sim_t2s
            row[f"eligible_s2t_{tau_str}"] = sim_s2t >= tau
            row[f"eligible_t2s_{tau_str}"] = sim_t2s >= tau
            row[f"retrieved_s2t_{tau_str}"] = ret_s2t
            row[f"retrieved_t2s_{tau_str}"] = ret_t2s
            row[f"in_both_candidate_sets_{tau_str}"] = in_both_sets
            row[f"validated_s2t_{tau_str}"] = val_s2t
            row[f"validated_t2s_{tau_str}"] = val_t2s
            row[f"reciprocal_retained_{tau_str}"] = retained
            row[f"stage_outcome_{tau_str}"] = status

        audit_rows.append(row)

    df_out = pd.DataFrame(audit_rows)
    out_csv = output_dir / "step7c_reciprocal_eligibility_audit.csv"
    df_out.to_csv(out_csv, index=False)
    print(f"Saved reciprocal candidate eligibility audit for {len(df_out)} reference pairs to {out_csv}", flush=True)


if __name__ == "__main__":
    main()

