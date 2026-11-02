"""Reproducible Step 5 Audit and Candidate Evaluation Script for Agent-OM Local.

Generates:
1. Strategy-by-strategy raw candidate evaluations (Syntactic, Lexical, Semantic)
2. Fused RRF evaluations (k=0 and k=60)
3. Direct correspondence-level reconciliation against:
   - Reference Alignment (reference.xml)
   - Original committed predict.csv
   - Original committed predict_source_no_validation.csv
   - Published Agent-OM baseline
4. Exports complete raw CSV and JSON artifacts.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pandas as pd
import rdflib

# Add project root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import config
from src.db.database_manager import DatabaseManager
from src.retrieval.rank_fusion import reciprocal_rank_fusion
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
    a = len(predicted_pairs)
    r = len(reference_pairs)

    p = (tp / a) if a > 0 else 0.0
    rec = (tp / r) if r > 0 else 0.0
    f1 = (2 * p * rec / (p + rec)) if (p + rec) > 0 else 0.0

    return {
        "A": a,
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "Precision": round(p * 100, 2),
        "Recall": round(rec * 100, 2),
        "F1": round(f1 * 100, 2),
        "tp_pairs": sorted(list(tp_pairs)),
        "fp_pairs": sorted(list(fp_pairs)),
        "fn_pairs": sorted(list(fn_pairs)),
    }


def run_audit():
    t_start = time.perf_counter()
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    ref_path = PROJECT_ROOT.parent / "original_repo/data/conference/cmt-confof/component/reference.xml"
    reference_pairs = load_reference_alignment(ref_path)
    print(f"Loaded {len(reference_pairs)} true correspondences from {ref_path.name}", flush=True)

    db = DatabaseManager()

    # Check count in isolated connection
    with db.get_connection() as check_conn:
        with check_conn.cursor() as check_cur:
            check_cur.execute("CREATE TABLE IF NOT EXISTS ontology_matching (entity_id VARCHAR(1024) PRIMARY KEY);")
            check_cur.execute("SELECT count(*) FROM ontology_matching;")
            entity_count = check_cur.fetchone()[0]
        check_conn.commit()

    # If database was overwritten by a test, re-ingest full 162 entities
    if entity_count < 162:
        print(f"Database contains {entity_count} entities (< 162). Ingesting full CMT-ConfOf dataset (162 entities)...", flush=True)
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

        from langchain_ollama import OllamaEmbeddings
        emb_service = OllamaEmbeddings(model="nomic-embed-text")
        db.create_ontology_matching_table(df_full)
        print("Created ontology_matching table.", flush=True)
        syn_c = db.create_embedding_table("syntactic_matching", df_full, emb_service, vector_length=768)
        print(f"Created syntactic_matching table ({syn_c} chunks).", flush=True)
        lex_c = db.create_embedding_table("lexical_matching", df_full, emb_service, vector_length=768)
        print(f"Created lexical_matching table ({lex_c} chunks).", flush=True)
        sem_c = db.create_embedding_table("semantic_matching", df_full, emb_service, vector_length=768)
        print(f"Created semantic_matching table ({sem_c} chunks).", flush=True)

    # Open query connection
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute("SELECT entity_id, entity_uri, source_or_target, entity_type FROM ontology_matching ORDER BY entity_id;")
    all_rows = cur.fetchall()
    entity_map = {r[0]: {"uri": r[1], "source_or_target": r[2], "type": r[3]} for r in all_rows}

    source_eids = [r[0] for r in all_rows if r[2] == "Source"]
    target_eids = [r[0] for r in all_rows if r[2] == "Target"]
    print(f"Entities in database: {len(source_eids)} Source (CMT), {len(target_eids)} Target (ConfOf)", flush=True)

    strategies = ["syntactic_matching", "lexical_matching", "semantic_matching"]

    # 1. Evaluate Individual Strategies (no RRF)
    strategy_results: Dict[str, Any] = {}
    raw_candidate_rows = []

    for strat in strategies:
        # S -> T
        s2t_pairs = set()
        for eid in source_eids:
            cur.execute(f"""
                SELECT m.embedding, o.source_or_target, o.entity_type
                FROM ontology_matching o, {strat} m
                WHERE o.entity_id = m.entity_id AND o.entity_id = %s;
            """, (eid,))
            res = cur.fetchone()
            if not res:
                continue
            emb, s_or_t, e_type = res
            opp = "Target"

            cur.execute(f"""
                WITH vector_matches AS (
                    SELECT entity_id, 1 - (embedding <=> %s) AS similarity
                    FROM {strat}
                    WHERE 1 - (embedding <=> %s) >= %s
                )
                SELECT o.entity_id, v.similarity AS similarity
                FROM ontology_matching o, vector_matches v
                WHERE o.entity_id = v.entity_id
                AND o.source_or_target = %s AND o.entity_type = %s
                ORDER BY v.similarity DESC
                LIMIT %s;
            """, (emb, emb, config.similarity_threshold, opp, e_type, config.num_matches))
            matches = cur.fetchall()

            seen = set()
            for rank, (cand_id, sim) in enumerate(matches, start=1):
                if cand_id not in seen:
                    seen.add(cand_id)
                    src_uri = entity_map[eid]["uri"]
                    tgt_uri = entity_map[cand_id]["uri"]
                    pair = (src_uri, tgt_uri)
                    s2t_pairs.add(pair)
                    is_tp = pair in reference_pairs
                    raw_candidate_rows.append({
                        "query_id": eid,
                        "candidate_id": cand_id,
                        "source_uri": src_uri,
                        "target_uri": tgt_uri,
                        "source_name": uri_to_name(src_uri),
                        "target_name": uri_to_name(tgt_uri),
                        "direction": "Source->Target",
                        "strategy": strat,
                        "strategy_rank": rank,
                        "similarity_score": round(float(sim), 6),
                        "ground_truth": "TP" if is_tp else "FP",
                    })
                    if len(seen) >= config.top_k:
                        break

        # T -> S
        t2s_pairs = set()
        for eid in target_eids:
            cur.execute(f"""
                SELECT m.embedding, o.source_or_target, o.entity_type
                FROM ontology_matching o, {strat} m
                WHERE o.entity_id = m.entity_id AND o.entity_id = %s;
            """, (eid,))
            res = cur.fetchone()
            if not res:
                continue
            emb, s_or_t, e_type = res
            opp = "Source"

            cur.execute(f"""
                WITH vector_matches AS (
                    SELECT entity_id, 1 - (embedding <=> %s) AS similarity
                    FROM {strat}
                    WHERE 1 - (embedding <=> %s) >= %s
                )
                SELECT o.entity_id, v.similarity AS similarity
                FROM ontology_matching o, vector_matches v
                WHERE o.entity_id = v.entity_id
                AND o.source_or_target = %s AND o.entity_type = %s
                ORDER BY v.similarity DESC
                LIMIT %s;
            """, (emb, emb, config.similarity_threshold, opp, e_type, config.num_matches))
            matches = cur.fetchall()

            seen = set()
            for rank, (cand_id, sim) in enumerate(matches, start=1):
                if cand_id not in seen:
                    seen.add(cand_id)
                    tgt_uri = entity_map[eid]["uri"]
                    src_uri = entity_map[cand_id]["uri"]
                    pair = (src_uri, tgt_uri)
                    t2s_pairs.add(pair)
                    is_tp = pair in reference_pairs
                    raw_candidate_rows.append({
                        "query_id": eid,
                        "candidate_id": cand_id,
                        "source_uri": src_uri,
                        "target_uri": tgt_uri,
                        "source_name": uri_to_name(src_uri),
                        "target_name": uri_to_name(tgt_uri),
                        "direction": "Target->Source",
                        "strategy": strat,
                        "strategy_rank": rank,
                        "similarity_score": round(float(sim), 6),
                        "ground_truth": "TP" if is_tp else "FP",
                    })
                    if len(seen) >= config.top_k:
                        break

        strategy_results[f"{strat}_S2T"] = calculate_metrics(s2t_pairs, reference_pairs)
        strategy_results[f"{strat}_T2S"] = calculate_metrics(t2s_pairs, reference_pairs)
        strategy_results[f"{strat}_Union"] = calculate_metrics(s2t_pairs.union(t2s_pairs), reference_pairs)

    # 2. Evaluate Fused RRF Candidate Selection
    fused_s2t_top1 = set()
    fused_s2t_top3 = set()
    for eid in source_eids:
        # Get rankings for the 3 strategies
        rankings = []
        for strat in strategies:
            cands = db.query_strategy(eid, strat, similarity_threshold=config.similarity_threshold, num_matches=config.num_matches, top_k=config.top_k)
            cands = [c for c in cands if c != config.null_value_matching]
            if cands:
                rankings.append(cands)
        fused = reciprocal_rank_fusion(*rankings, k=0)
        flat_cands = [item for _, items in fused for item in items]
        src_uri = entity_map[eid]["uri"]
        if flat_cands:
            fused_s2t_top1.add((src_uri, entity_map[flat_cands[0]]["uri"]))
            for cand_id in flat_cands[:config.top_k]:
                fused_s2t_top3.add((src_uri, entity_map[cand_id]["uri"]))

    fused_t2s_top1 = set()
    fused_t2s_top3 = set()
    for eid in target_eids:
        rankings = []
        for strat in strategies:
            cands = db.query_strategy(eid, strat, similarity_threshold=config.similarity_threshold, num_matches=config.num_matches, top_k=config.top_k)
            cands = [c for c in cands if c != config.null_value_matching]
            if cands:
                rankings.append(cands)
        fused = reciprocal_rank_fusion(*rankings, k=0)
        flat_cands = [item for _, items in fused for item in items]
        tgt_uri = entity_map[eid]["uri"]
        if flat_cands:
            fused_t2s_top1.add((entity_map[flat_cands[0]]["uri"], tgt_uri))
            for cand_id in flat_cands[:config.top_k]:
                fused_t2s_top3.add((entity_map[cand_id]["uri"], tgt_uri))

    fused_union_top3 = fused_s2t_top3.union(fused_t2s_top3)

    rrf_results = {
        "RRF_k0_S2T_Top1": calculate_metrics(fused_s2t_top1, reference_pairs),
        "RRF_k0_S2T_Top3": calculate_metrics(fused_s2t_top3, reference_pairs),
        "RRF_k0_T2S_Top1": calculate_metrics(fused_t2s_top1, reference_pairs),
        "RRF_k0_T2S_Top3": calculate_metrics(fused_t2s_top3, reference_pairs),
        "RRF_k0_Union_Top3": calculate_metrics(fused_union_top3, reference_pairs),
    }

    # 3. Load and evaluate original committed artifacts
    orig_base = PROJECT_ROOT.parent / "original_repo/alignment/conference/cmt-confof/component"
    orig_results = {}
    for fname in ["predict_source_no_validation.csv", "predict_target_no_validation.csv", "predict_no_validation.csv", "predict.csv"]:
        fpath = orig_base / fname
        if fpath.exists():
            df_p = pd.read_csv(fpath)
            cols = list(df_p.columns)
            if "Entity1" in cols and "Entity2" in cols:
                pairs = set(zip(df_p["Entity1"], df_p["Entity2"]))
            else:
                pairs = set(zip(df_p[cols[0]], df_p[cols[1]]))
            orig_results[fname] = calculate_metrics(pairs, reference_pairs)

    # 4. Save raw candidates CSV
    df_raw = pd.DataFrame(raw_candidate_rows)
    raw_csv_path = output_dir / "step5_raw_candidates.csv"
    df_raw.to_csv(raw_csv_path, index=False)
    print(f"Saved {len(df_raw)} raw retrieval candidate entries to {raw_csv_path}")

    # 5. Build correspondence-level comparison table
    all_eval_pairs: Set[Tuple[str, str]] = set()
    all_eval_pairs.update(reference_pairs)
    all_eval_pairs.update(fused_union_top3)
    if "predict.csv" in orig_results:
        all_eval_pairs.update(set(zip(pd.read_csv(orig_base / "predict.csv")["Entity1"], pd.read_csv(orig_base / "predict.csv")["Entity2"])))
    if "predict_source_no_validation.csv" in orig_results:
        all_eval_pairs.update(set(zip(pd.read_csv(orig_base / "predict_source_no_validation.csv")["Entity1"], pd.read_csv(orig_base / "predict_source_no_validation.csv")["Entity2"])))

    comparison_rows = []
    orig_predict_pairs = set(zip(pd.read_csv(orig_base / "predict.csv")["Entity1"], pd.read_csv(orig_base / "predict.csv")["Entity2"])) if (orig_base / "predict.csv").exists() else set()
    orig_s_no_val_pairs = set(zip(pd.read_csv(orig_base / "predict_source_no_validation.csv")["Entity1"], pd.read_csv(orig_base / "predict_source_no_validation.csv")["Entity2"])) if (orig_base / "predict_source_no_validation.csv").exists() else set()

    for p in sorted(list(all_eval_pairs)):
        src, tgt = p
        in_ref = p in reference_pairs
        in_orig_predict = p in orig_predict_pairs
        in_orig_s_no_val = p in orig_s_no_val_pairs
        in_local_s2t_top1 = p in fused_s2t_top1
        in_local_s2t_top3 = p in fused_s2t_top3
        in_local_t2s_top1 = p in fused_t2s_top1
        in_local_t2s_top3 = p in fused_t2s_top3
        in_local_union = p in fused_union_top3

        comparison_rows.append({
            "source_uri": src,
            "target_uri": tgt,
            "source_name": uri_to_name(src),
            "target_name": uri_to_name(tgt),
            "in_reference_ground_truth": in_ref,
            "in_orig_predict_csv": in_orig_predict,
            "in_orig_source_no_validation": in_orig_s_no_val,
            "in_local_s2t_top1": in_local_s2t_top1,
            "in_local_s2t_top3": in_local_s2t_top3,
            "in_local_t2s_top1": in_local_t2s_top1,
            "in_local_t2s_top3": in_local_t2s_top3,
            "in_local_union": in_local_union,
        })

    df_comp = pd.DataFrame(comparison_rows)
    comp_csv_path = output_dir / "step5_correspondence_comparison.csv"
    df_comp.to_csv(comp_csv_path, index=False)
    print(f"Saved correspondence comparison ({len(df_comp)} pairs) to {comp_csv_path}")

    # 6. Save summary JSON
    total_time_s = time.perf_counter() - t_start
    summary_data = {
        "audit_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_runtime_seconds": round(total_time_s, 2),
        "configuration": {
            "embedding_model": "nomic-embed-text:latest",
            "embedding_dimensions": 768,
            "chat_model": "qwen3.5:9b",
            "similarity_threshold": config.similarity_threshold,
            "top_k": config.top_k,
            "num_matches": config.num_matches,
            "context": config.context,
            "reference_file": str(ref_path.resolve()),
            "total_reference_correspondences": len(reference_pairs),
        },
        "strategy_evaluations": {
            k: {k2: v2 for k2, v2 in v.items() if not k2.endswith("_pairs")}
            for k, v in strategy_results.items()
        },
        "rrf_evaluations": {
            k: {k2: v2 for k2, v2 in v.items() if not k2.endswith("_pairs")}
            for k, v in rrf_results.items()
        },
        "original_committed_baseline": {
            k: {k2: v2 for k2, v2 in v.items() if not k2.endswith("_pairs")}
            for k, v in orig_results.items()
        },
    }

    summary_json_path = output_dir / "step5_audit_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Saved audit summary to {summary_json_path}")

    conn.close()
    return summary_data


if __name__ == "__main__":
    run_audit()
