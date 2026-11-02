"""Complete 17-point intermediate artifact comparator for Agent-OM replication runs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

from .metrics import compute_alignment_metrics, load_alignment_csv_pairs


def _tokenize_words(text: str) -> Set[str]:
    return set(re.findall(r"[a-z0-9]+", str(text or "").lower()))


def _jaccard(a: Set[Any], b: Set[Any]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def load_features_csv(csv_path: str | Path) -> pd.DataFrame:
    """Load an `ontology_matching.csv` file handling UTF-8/CP1250 and normalizing upstream column names."""
    path = Path(csv_path)
    if not path.is_file():
        return pd.DataFrame()
    df: pd.DataFrame | None = None
    for enc in ("utf-8", "cp1250", "latin-1"):
        try:
            df = pd.read_csv(path, encoding=enc).fillna("")
            break
        except UnicodeDecodeError:
            continue
    if df is None:
        df = pd.read_csv(path, encoding="latin-1").fillna("")

    if not df.empty:
        if "entity_uri" not in df.columns and "entity" in df.columns:
            df["entity_uri"] = df["entity"].astype(str)
        if "entity_id" not in df.columns and "entity_uri" in df.columns:
            synth_ids: List[str] = []
            for idx, row in df.iterrows():
                side = str(row.get("source_or_target", ""))
                etype = str(row.get("entity_type", ""))
                syn_first = str(row.get("syntactic_matching", "")).split(",")[0].strip()
                synth_ids.append(f"{side}-{etype}-{idx}-{syn_first}")
            df.insert(0, "entity_id", synth_ids)
    return df


def compare_two_runs_17_points(
    run_a_label: str,
    run_a_data: Dict[str, Any],
    run_b_label: str,
    run_b_data: Dict[str, Any],
    reference_pairs: Optional[Sequence[Tuple[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Compare all 17 intermediate and final artifacts between two replication runs (`run_a` vs `run_b`).

    Expected keys in `run_*_data` (missing keys are gracefully reported as unavailable):
      - `features_df`: DataFrame (`entity_id`, `entity_uri`, `source_or_target`, `entity_type`,
        `syntactic_matching`, `lexical_matching`, `semantic_matching`)
      - `entity_metadata`: Optional dict `{(source_or_target, uri): {...}}`
      - `chunk_counts`: Optional dict `{"syntactic_chunks": int, "lexical_chunks": int, "semantic_chunks": int}`
      - `embedding_dim`: Optional int
      - `candidates`: Optional dict `{"s2t": [...], "t2s": [...]}` (per-entity retrieval dictionaries)
      - `validation_records`: Optional list of dicts (`source_uri`, `target_uri`, `bypassed`, `decision`, `prompt`, `raw_response`)
      - `predictions`: Dict with `s2t_no_val`, `t2s_no_val`, `merged_no_val`, `s2t_val`, `t2s_val`, `final_merged` sets/lists of `(src_uri, tgt_uri)`
    """
    df_a: pd.DataFrame = run_a_data.get("features_df", pd.DataFrame())
    df_b: pd.DataFrame = run_b_data.get("features_df", pd.DataFrame())

    # Align entities by (source_or_target, entity_uri, row_occurrence) to support punning safely
    def _index_features(df: pd.DataFrame) -> Dict[Tuple[str, str, int], Dict[str, Any]]:
        out: Dict[Tuple[str, str, int], Dict[str, Any]] = {}
        seen_counts: Dict[Tuple[str, str], int] = {}
        if df is None or df.empty:
            return out
        for _, row in df.iterrows():
            side = str(row.get("source_or_target", ""))
            uri = str(row.get("entity_uri", ""))
            occ = seen_counts.get((side, uri), 0)
            seen_counts[(side, uri)] = occ + 1
            out[(side, uri, occ)] = dict(row)
        return out

    idx_a = _index_features(df_a)
    idx_b = _index_features(df_b)
    keys_a = set(idx_a.keys())
    keys_b = set(idx_b.keys())
    shared_keys = sorted(keys_a & keys_b)

    # 1. Extracted source and target entities
    src_a = {u for s, u, _ in keys_a if s == "Source"}
    src_b = {u for s, u, _ in keys_b if s == "Source"}
    tgt_a = {u for s, u, _ in keys_a if s == "Target"}
    tgt_b = {u for s, u, _ in keys_b if s == "Target"}

    p1_entities = {
        "a_source_count": len(src_a),
        "b_source_count": len(src_b),
        "source_uri_jaccard": round(_jaccard(src_a, src_b), 6),
        "source_only_in_a": sorted(src_a - src_b),
        "source_only_in_b": sorted(src_b - src_a),
        "a_target_count": len(tgt_a),
        "b_target_count": len(tgt_b),
        "target_uri_jaccard": round(_jaccard(tgt_a, tgt_b), 6),
        "target_only_in_a": sorted(tgt_a - tgt_b),
        "target_only_in_b": sorted(tgt_b - tgt_a),
        "a_total_rows": len(idx_a),
        "b_total_rows": len(idx_b),
    }

    # 2. Entity IDs
    id_matches = 0
    id_mismatches: List[Dict[str, str]] = []
    for k in shared_keys:
        eid_a = str(idx_a[k].get("entity_id", ""))
        eid_b = str(idx_b[k].get("entity_id", ""))
        if eid_a == eid_b:
            id_matches += 1
        else:
            id_mismatches.append(
                {"side": k[0], "uri": k[1], "a_entity_id": eid_a, "b_entity_id": eid_b}
            )
    p2_entity_ids = {
        "shared_entities": len(shared_keys),
        "exact_entity_id_matches": id_matches,
        "exact_entity_id_match_pct": round(id_matches / len(shared_keys) * 100.0, 2)
        if shared_keys
        else 0.0,
        "mismatch_count": len(id_mismatches),
        "sample_mismatches": id_mismatches[:20],
    }

    # 3. Entity names (suffix of entity_id)
    name_matches = 0
    for k in shared_keys:
        na = str(idx_a[k].get("entity_id", "")).split("-", 3)[-1]
        nb = str(idx_b[k].get("entity_id", "")).split("-", 3)[-1]
        if na == nb:
            name_matches += 1
    p3_entity_names = {
        "exact_name_matches": name_matches,
        "exact_name_match_pct": round(name_matches / len(shared_keys) * 100.0, 2)
        if shared_keys
        else 0.0,
    }

    # 4. Extracted annotations & structural metadata
    meta_a = run_a_data.get("entity_metadata", {}) or {}
    meta_b = run_b_data.get("entity_metadata", {}) or {}
    p4_metadata = {
        "a_metadata_records": len(meta_a),
        "b_metadata_records": len(meta_b),
        "a_non_null_semantic_entities": sum(
            1
            for k in keys_a
            if str(idx_a[k].get("semantic_matching", "")).strip()
            not in ("", "Information is not available.")
        ),
        "b_non_null_semantic_entities": sum(
            1
            for k in keys_b
            if str(idx_b[k].get("semantic_matching", "")).strip()
            not in ("", "Information is not available.")
        ),
    }

    # 5. Cleaned syntactic names
    syn_exact = 0
    syn_diffs: List[Dict[str, str]] = []
    for k in shared_keys:
        sa = str(idx_a[k].get("syntactic_matching", "")).strip()
        sb = str(idx_b[k].get("syntactic_matching", "")).strip()
        if sa == sb:
            syn_exact += 1
        else:
            syn_diffs.append({"uri": k[1], "a": sa, "b": sb})
    p5_syntactic_text = {
        "exact_matches": syn_exact,
        "exact_match_pct": round(syn_exact / len(shared_keys) * 100.0, 2) if shared_keys else 0.0,
        "diff_count": len(syn_diffs),
        "sample_diffs": syn_diffs[:10],
    }

    # 6. Lexical verbalizations
    lex_exact = 0
    lex_jaccards: List[float] = []
    for k in shared_keys:
        la = str(idx_a[k].get("lexical_matching", "")).strip()
        lb = str(idx_b[k].get("lexical_matching", "")).strip()
        if la == lb:
            lex_exact += 1
        lex_jaccards.append(_jaccard(_tokenize_words(la), _tokenize_words(lb)))
    p6_lexical_text = {
        "exact_matches": lex_exact,
        "exact_match_pct": round(lex_exact / len(shared_keys) * 100.0, 2) if shared_keys else 0.0,
        "mean_word_jaccard": round(float(np.mean(lex_jaccards)), 4) if lex_jaccards else 0.0,
        "a_mean_char_len": round(
            float(np.mean([len(str(idx_a[k].get("lexical_matching", ""))) for k in shared_keys])), 1
        )
        if shared_keys
        else 0.0,
        "b_mean_char_len": round(
            float(np.mean([len(str(idx_b[k].get("lexical_matching", ""))) for k in shared_keys])), 1
        )
        if shared_keys
        else 0.0,
    }

    # 7. Semantic verbalizations
    sem_exact = 0
    sem_null_agree = 0
    sem_jaccards: List[float] = []
    for k in shared_keys:
        sa = str(idx_a[k].get("semantic_matching", "")).strip()
        sb = str(idx_b[k].get("semantic_matching", "")).strip()
        if sa == sb:
            sem_exact += 1
        na_null = sa in ("", "Information is not available.")
        nb_null = sb in ("", "Information is not available.")
        if na_null == nb_null:
            sem_null_agree += 1
        sem_jaccards.append(_jaccard(_tokenize_words(sa), _tokenize_words(sb)))
    p7_semantic_text = {
        "exact_matches": sem_exact,
        "exact_match_pct": round(sem_exact / len(shared_keys) * 100.0, 2) if shared_keys else 0.0,
        "null_vs_non_null_agreement_pct": round(sem_null_agree / len(shared_keys) * 100.0, 2)
        if shared_keys
        else 0.0,
        "mean_word_jaccard": round(float(np.mean(sem_jaccards)), 4) if sem_jaccards else 0.0,
        "a_mean_char_len": round(
            float(np.mean([len(str(idx_a[k].get("semantic_matching", ""))) for k in shared_keys])), 1
        )
        if shared_keys
        else 0.0,
        "b_mean_char_len": round(
            float(np.mean([len(str(idx_b[k].get("semantic_matching", ""))) for k in shared_keys])), 1
        )
        if shared_keys
        else 0.0,
    }

    # 8. Text chunk counts
    chunks_a = run_a_data.get("chunk_counts", {}) or {}
    chunks_b = run_b_data.get("chunk_counts", {}) or {}
    p8_chunk_counts = {
        "a": chunks_a,
        "b": chunks_b,
    }

    # 9. Embedding dimensions
    p9_embedding_dims = {
        "a_embedding_dim": run_a_data.get("embedding_dim"),
        "b_embedding_dim": run_b_data.get("embedding_dim"),
        "dimensions_equal": run_a_data.get("embedding_dim") == run_b_data.get("embedding_dim"),
    }

    # Helper to compare candidate rankings per direction
    cands_a = run_a_data.get("candidates", {}) or {}
    cands_b = run_b_data.get("candidates", {}) or {}
    all_cands_a = {
        (d, str(item.get("query_entity_uri", ""))): item
        for d in ("s2t", "t2s")
        for item in cands_a.get(d, [])
    }
    all_cands_b = {
        (d, str(item.get("query_entity_uri", ""))): item
        for d in ("s2t", "t2s")
        for item in cands_b.get(d, [])
    }
    shared_cand_keys = sorted(set(all_cands_a.keys()) & set(all_cands_b.keys()))

    # Build id->uri maps from features_df so candidate entity_ids compare on canonical URIs
    id_to_uri_a = {
        str(r.get("entity_id", "")): str(r.get("entity_uri", ""))
        for r in idx_a.values()
    }
    id_to_uri_b = {
        str(r.get("entity_id", "")): str(r.get("entity_uri", ""))
        for r in idx_b.values()
    }

    def _summarize_scores(cand_map: Dict[Any, Dict[str, Any]], score_key: str) -> Dict[str, float]:
        vals: List[float] = []
        for item in cand_map.values():
            entries = item.get(score_key, [])
            if entries:
                vals.append(float(entries[0].get("similarity", 0.0)))
        if not vals:
            return {"count_with_hits": 0, "mean_top1_sim": 0.0, "min_top1_sim": 0.0, "max_top1_sim": 0.0}
        return {
            "count_with_hits": len(vals),
            "mean_top1_sim": round(float(np.mean(vals)), 5),
            "min_top1_sim": round(float(np.min(vals)), 5),
            "max_top1_sim": round(float(np.max(vals)), 5),
        }

    # 10. Similarity scores
    p10_similarity_scores = {
        "a": {
            "syntactic": _summarize_scores(all_cands_a, "syntactic_scores"),
            "lexical": _summarize_scores(all_cands_a, "lexical_scores"),
            "semantic": _summarize_scores(all_cands_a, "semantic_scores"),
        },
        "b": {
            "syntactic": _summarize_scores(all_cands_b, "syntactic_scores"),
            "lexical": _summarize_scores(all_cands_b, "lexical_scores"),
            "semantic": _summarize_scores(all_cands_b, "semantic_scores"),
        },
    }

    def _compare_strategy_rankings(ranking_key: str) -> Dict[str, Any]:
        if not shared_cand_keys:
            return {"comparable_queries": 0, "top1_uri_match_pct": None, "mean_set_jaccard": None}
        top1_eq = 0
        jacc: List[float] = []
        for ck in shared_cand_keys:
            ra = [
                id_to_uri_a.get(eid, eid)
                for eid in all_cands_a[ck].get(ranking_key, [])
                if eid != "Entity-Dummy"
            ]
            rb = [
                id_to_uri_b.get(eid, eid)
                for eid in all_cands_b[ck].get(ranking_key, [])
                if eid != "Entity-Dummy"
            ]
            top_a = ra[0] if ra else None
            top_b = rb[0] if rb else None
            if top_a == top_b:
                top1_eq += 1
            jacc.append(_jaccard(set(ra), set(rb)))
        return {
            "comparable_queries": len(shared_cand_keys),
            "top1_uri_match_pct": round(top1_eq / len(shared_cand_keys) * 100.0, 2),
            "mean_set_jaccard": round(float(np.mean(jacc)), 4),
        }

    # 11, 12, 13. Per-strategy top-k candidates
    p11_syntactic_cands = _compare_strategy_rankings("syntactic_ranking")
    p12_lexical_cands = _compare_strategy_rankings("lexical_ranking")
    p13_semantic_cands = _compare_strategy_rankings("semantic_ranking")

    # 14 & 15. Combined candidate unions & RRF fused rankings
    union_jacc: List[float] = []
    rrf_top1_eq = 0
    for ck in shared_cand_keys:
        ua = [str(u) for u in all_cands_a[ck].get("candidate_uris", [])]
        ub = [str(u) for u in all_cands_b[ck].get("candidate_uris", [])]
        union_jacc.append(_jaccard(set(ua), set(ub)))
        if (ua[0] if ua else None) == (ub[0] if ub else None):
            rrf_top1_eq += 1

    p14_candidate_unions = {
        "comparable_queries": len(shared_cand_keys),
        "mean_union_uri_jaccard": round(float(np.mean(union_jacc)), 4) if union_jacc else None,
        "a_non_empty_queries": sum(1 for v in all_cands_a.values() if v.get("candidate_uris")),
        "b_non_empty_queries": sum(1 for v in all_cands_b.values() if v.get("candidate_uris")),
    }
    p15_rrf_rankings = {
        "comparable_queries": len(shared_cand_keys),
        "rrf_top1_uri_agreement_pct": round(rrf_top1_eq / len(shared_cand_keys) * 100.0, 2)
        if shared_cand_keys
        else None,
    }

    # 16. Validation decisions
    val_a = run_a_data.get("validation_records", []) or []
    val_b = run_b_data.get("validation_records", []) or []
    map_val_a = {
        (str(r.get("direction", "")), str(r.get("source_uri", "")), str(r.get("target_uri", ""))): r
        for r in val_a
    }
    map_val_b = {
        (str(r.get("direction", "")), str(r.get("source_uri", "")), str(r.get("target_uri", ""))): r
        for r in val_b
    }
    shared_val_keys = sorted(set(map_val_a.keys()) & set(map_val_b.keys()))
    val_decision_agree = sum(
        1
        for vk in shared_val_keys
        if map_val_a[vk].get("decision") == map_val_b[vk].get("decision")
    )
    p16_validation = {
        "a_total_validations": len(val_a),
        "a_bypasses": sum(1 for r in val_a if r.get("bypassed")),
        "a_accepted": sum(1 for r in val_a if r.get("decision") == "yes"),
        "b_total_validations": len(val_b),
        "b_bypasses": sum(1 for r in val_b if r.get("bypassed")),
        "b_accepted": sum(1 for r in val_b if r.get("decision") == "yes"),
        "shared_evaluated_pairs": len(shared_val_keys),
        "decision_agreement_pct": round(val_decision_agree / len(shared_val_keys) * 100.0, 2)
        if shared_val_keys
        else None,
    }

    # 17. Reciprocal merger results and final alignment
    preds_a = run_a_data.get("predictions", {}) or {}
    preds_b = run_b_data.get("predictions", {}) or {}

    def _pair_set(items: Any) -> Set[Tuple[str, str]]:
        return {(str(x[0]), str(x[1])) for x in (items or [])}

    final_a = _pair_set(preds_a.get("final_merged"))
    final_b = _pair_set(preds_b.get("final_merged"))
    s2t_a = _pair_set(preds_a.get("s2t_val"))
    s2t_b = _pair_set(preds_b.get("s2t_val"))
    t2s_a = _pair_set(preds_a.get("t2s_val"))
    t2s_b = _pair_set(preds_b.get("t2s_val"))

    p17_final_alignment: Dict[str, Any] = {
        "s2t_validated_jaccard": round(_jaccard(s2t_a, s2t_b), 4),
        "t2s_validated_jaccard": round(_jaccard(t2s_a, t2s_b), 4),
        "final_merged_jaccard": round(_jaccard(final_a, final_b), 4),
        "a_final_count": len(final_a),
        "b_final_count": len(final_b),
        "shared_final_pairs": sorted(final_a & final_b),
        "only_in_a_final_pairs": sorted(final_a - final_b),
        "only_in_b_final_pairs": sorted(final_b - final_a),
    }
    if reference_pairs is not None:
        p17_final_alignment["a_metrics"] = compute_alignment_metrics(final_a, reference_pairs)
        p17_final_alignment["b_metrics"] = compute_alignment_metrics(final_b, reference_pairs)

    return {
        "run_a_label": run_a_label,
        "run_b_label": run_b_label,
        "1_extracted_entities": p1_entities,
        "2_entity_ids": p2_entity_ids,
        "3_entity_names": p3_entity_names,
        "4_annotations_and_metadata": p4_metadata,
        "5_cleaned_syntactic_names": p5_syntactic_text,
        "6_lexical_verbalizations": p6_lexical_text,
        "7_semantic_verbalizations": p7_semantic_text,
        "8_text_chunk_counts": p8_chunk_counts,
        "9_embedding_dimensions": p9_embedding_dims,
        "10_similarity_scores": p10_similarity_scores,
        "11_syntactic_candidates": p11_syntactic_cands,
        "12_lexical_candidates": p12_lexical_cands,
        "13_semantic_candidates": p13_semantic_cands,
        "14_combined_candidate_unions": p14_candidate_unions,
        "15_rrf_rankings": p15_rrf_rankings,
        "16_validation_decisions": p16_validation,
        "17_reciprocal_merger_and_final_alignment": p17_final_alignment,
    }
