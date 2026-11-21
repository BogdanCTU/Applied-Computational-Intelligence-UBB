"""Alignment evaluation metrics, stage-by-stage candidate attrition, and OAEI/CSV exporters."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from xml.sax.saxutils import escape

import pandas as pd
import rdflib


def load_reference_pairs(ref_xml_path: str | Path) -> List[Tuple[str, str]]:
    """Load sorted 1:1 equivalence (`=`) URI pairs from an OAEI Alignment API RDF/XML file."""
    path = Path(ref_xml_path)
    g = rdflib.Graph()
    g.parse(str(path))
    align_cell = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#Cell")
    align_e1 = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#entity1")
    align_e2 = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#entity2")
    align_rel = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#relation")

    pairs: Set[Tuple[str, str]] = set()
    for cell in g.subjects(rdflib.RDF.type, align_cell):
        rel = str(g.value(cell, align_rel, None) or "=")
        if rel == "=":
            e1 = str(g.value(cell, align_e1, None) or "").strip()
            e2 = str(g.value(cell, align_e2, None) or "").strip()
            if e1 and e2:
                pairs.add((e1, e2))
    return sorted(pairs)


def load_alignment_csv_pairs(
    csv_path: str | Path,
    reverse_columns: bool = False,
) -> Set[Tuple[str, str]]:
    """
    Load `(Source, Target)` URI pairs from an alignment CSV (`Source,Target` header).
    Handles UTF-8 and Windows-1250 encodings cleanly and ignores misplaced header rows.
    """
    path = Path(csv_path)
    if not path.is_file():
        return set()

    rows: List[List[str]] = []
    for enc in ("utf-8", "cp1250", "latin-1"):
        try:
            with path.open("r", encoding=enc, newline="") as fh:
                rows = list(csv.reader(fh))
            break
        except UnicodeDecodeError:
            continue

    pairs: Set[Tuple[str, str]] = set()
    for row in rows:
        if len(row) < 2:
            continue
        c0, c1 = row[0].strip(), row[1].strip()
        if not c0 or not c1:
            continue
        if (c0.lower(), c1.lower()) in (("source", "target"), ("target", "source")):
            continue
        if reverse_columns:
            pairs.add((c1, c0))
        else:
            pairs.add((c0, c1))
    return pairs


def compute_alignment_metrics(
    predicted_pairs: Iterable[Tuple[str, str]],
    reference_pairs: Iterable[Tuple[str, str]],
) -> Dict[str, Any]:
    """
    Compute TP, FP, FN, Precision, Recall, and F1 (both exact unrounded and
    upstream `util.calculate_metrics` 2-decimal rounded percentages).
    """
    pred_set: Set[Tuple[str, str]] = {(str(a).strip(), str(b).strip()) for a, b in predicted_pairs}
    ref_set: Set[Tuple[str, str]] = {(str(a).strip(), str(b).strip()) for a, b in reference_pairs}

    tp_set = pred_set & ref_set
    fp_set = pred_set - ref_set
    fn_set = ref_set - pred_set

    tp = len(tp_set)
    fp = len(fp_set)
    fn = len(fn_set)

    p_exact = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else 0.0
    r_exact = (tp / (tp + fn) * 100.0) if (tp + fn) > 0 else 0.0
    f1_exact = (2.0 * p_exact * r_exact / (p_exact + r_exact)) if (p_exact + r_exact) > 0 else 0.0

    # Upstream util.calculate_metrics() formula rounds P and R to 2 decimals before computing F1
    p_upstream = round(p_exact, 2)
    r_upstream = round(r_exact, 2)
    f1_upstream = (
        round(2.0 * p_upstream * r_upstream / (p_upstream + r_upstream), 2)
        if (p_upstream + r_upstream) > 0
        else 0.0
    )

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "predicted_count": len(pred_set),
        "reference_count": len(ref_set),
        "precision_pct": p_upstream,
        "recall_pct": r_upstream,
        "f1_pct": f1_upstream,
        "precision_exact_pct": round(p_exact, 6),
        "recall_exact_pct": round(r_exact, 6),
        "f1_exact_pct": round(f1_exact, 6),
        "tp_pairs": sorted(tp_set),
        "fp_pairs": sorted(fp_set),
        "fn_pairs": sorted(fn_set),
    }


def compute_stage_attrition(
    reference_pairs: Sequence[Tuple[str, str]],
    source_entity_uris: Iterable[str],
    target_entity_uris: Iterable[str],
    s2t_candidates: Sequence[Dict[str, Any]],
    t2s_candidates: Sequence[Dict[str, Any]],
    s2t_unvalidated_pairs: Iterable[Tuple[str, str]],
    t2s_unvalidated_pairs: Iterable[Tuple[str, str]],
    s2t_validated_pairs: Iterable[Tuple[str, str]],
    t2s_validated_pairs: Iterable[Tuple[str, str]],
    final_merged_pairs: Iterable[Tuple[str, str]],
    validation_records: Optional[Sequence[Any]] = None,
    id_to_uri: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Compute complete stage-by-stage candidate recall and TP/FP attrition across:
      1. Reference alignment
      2. Entity extraction coverage
      3. Syntactic / Lexical / Semantic per-strategy candidate pools
      4. Combined RRF top-k candidate pools (S->T, T->S, and reciprocal S->T ∩ T->S ceiling)
      5. RRF top-1 score group without LLM validation (S->T, T->S, merged)
      6. Post-LLM validation + exact-name bypass (S->T, T->S)
      7. Post-Reciprocal Merger final alignment
    """
    ref_set = {(str(a), str(b)) for a, b in reference_pairs}
    ref_count = len(ref_set)
    src_uris = set(source_entity_uris)
    tgt_uris = set(target_entity_uris)

    extractable_ref = {(s, t) for s, t in ref_set if s in src_uris and t in tgt_uris}

    def _resolve_ranking_pairs(
        cand_items: Sequence[Dict[str, Any]],
        key: str,
        is_s2t: bool,
    ) -> Set[Tuple[str, str]]:
        pool: Set[Tuple[str, str]] = set()
        for item in cand_items:
            q_uri = str(item.get("query_entity_uri", ""))
            for cid in item.get(key, []):
                if cid == "Entity-Dummy":
                    continue
                c_uri = (id_to_uri or {}).get(cid, "")
                if not c_uri:
                    continue
                if is_s2t:
                    pool.add((q_uri, c_uri))
                else:
                    pool.add((c_uri, q_uri))
        return pool

    s2t_rrf_pool: Set[Tuple[str, str]] = set()
    for item in s2t_candidates:
        q_uri = str(item.get("query_entity_uri", ""))
        for c_uri in item.get("candidate_uris", []):
            s2t_rrf_pool.add((q_uri, str(c_uri)))

    t2s_rrf_pool: Set[Tuple[str, str]] = set()
    for item in t2s_candidates:
        q_uri = str(item.get("query_entity_uri", ""))
        for c_uri in item.get("candidate_uris", []):
            t2s_rrf_pool.add((str(c_uri), q_uri))

    recip_rrf_ceiling = s2t_rrf_pool & t2s_rrf_pool

    strat_pools: Dict[str, Dict[str, Any]] = {}
    if id_to_uri is not None:
        for strat_label, key in (
            ("syntactic", "syntactic_ranking"),
            ("lexical", "lexical_ranking"),
            ("semantic", "semantic_ranking"),
        ):
            p_s2t = _resolve_ranking_pairs(s2t_candidates, key, True)
            p_t2s = _resolve_ranking_pairs(t2s_candidates, key, False)
            p_recip = p_s2t & p_t2s
            strat_pools[strat_label] = {
                "s2t_pool_size": len(p_s2t),
                "s2t_tp_ceiling": len(p_s2t & ref_set),
                "s2t_recall_pct": round(len(p_s2t & ref_set) / ref_count * 100.0, 2) if ref_count else 0.0,
                "t2s_pool_size": len(p_t2s),
                "t2s_tp_ceiling": len(p_t2s & ref_set),
                "t2s_recall_pct": round(len(p_t2s & ref_set) / ref_count * 100.0, 2) if ref_count else 0.0,
                "reciprocal_pool_size": len(p_recip),
                "reciprocal_tp_ceiling": len(p_recip & ref_set),
                "reciprocal_recall_pct": round(len(p_recip & ref_set) / ref_count * 100.0, 2) if ref_count else 0.0,
            }

    s2t_unval = set(s2t_unvalidated_pairs)
    t2s_unval = set(t2s_unvalidated_pairs)
    merged_unval = s2t_unval & t2s_unval

    s2t_val = set(s2t_validated_pairs)
    t2s_val = set(t2s_validated_pairs)
    final_merged = set(final_merged_pairs)

    val_total = len(validation_records) if validation_records is not None else 0
    val_bypass = sum(1 for r in (validation_records or []) if getattr(r, "bypassed", False))
    val_llm_calls = val_total - val_bypass
    val_accepted = sum(1 for r in (validation_records or []) if getattr(r, "decision", "") == "yes")
    val_acceptance_rate_pct = round(val_accepted / val_total * 100.0, 2) if val_total > 0 else 0.0

    union_val = s2t_val | t2s_val
    merger_retention_rate_pct = (
        round(len(final_merged) / len(union_val) * 100.0, 2) if union_val else 0.0
    )

    stages = [
        {
            "stage": "1_reference_alignment",
            "label": "Reference Alignment",
            "candidate_pairs": ref_count,
            "tp": ref_count,
            "fp": 0,
            "recall_ceiling_pct": 100.0 if ref_count else 0.0,
        },
        {
            "stage": "2_entity_extraction",
            "label": "Entity Extraction Coverage",
            "candidate_pairs": len(src_uris) * len(tgt_uris),
            "tp": len(extractable_ref),
            "fp": 0,
            "recall_ceiling_pct": round(len(extractable_ref) / ref_count * 100.0, 2) if ref_count else 0.0,
        },
        {
            "stage": "3_rrf_pool_s2t",
            "label": "RRF Top-k Pool (S->T)",
            "candidate_pairs": len(s2t_rrf_pool),
            "tp": len(s2t_rrf_pool & ref_set),
            "fp": len(s2t_rrf_pool - ref_set),
            "recall_ceiling_pct": round(len(s2t_rrf_pool & ref_set) / ref_count * 100.0, 2) if ref_count else 0.0,
        },
        {
            "stage": "4_rrf_pool_t2s",
            "label": "RRF Top-k Pool (T->S)",
            "candidate_pairs": len(t2s_rrf_pool),
            "tp": len(t2s_rrf_pool & ref_set),
            "fp": len(t2s_rrf_pool - ref_set),
            "recall_ceiling_pct": round(len(t2s_rrf_pool & ref_set) / ref_count * 100.0, 2) if ref_count else 0.0,
        },
        {
            "stage": "5_rrf_reciprocal_ceiling",
            "label": "RRF Reciprocal Pool (S->T ∩ T->S)",
            "candidate_pairs": len(recip_rrf_ceiling),
            "tp": len(recip_rrf_ceiling & ref_set),
            "fp": len(recip_rrf_ceiling - ref_set),
            "recall_ceiling_pct": round(len(recip_rrf_ceiling & ref_set) / ref_count * 100.0, 2) if ref_count else 0.0,
        },
        {
            "stage": "6_rrf_top1_merged_no_val",
            "label": "RRF Top-1 Merged (No Validation)",
            "candidate_pairs": len(merged_unval),
            "tp": len(merged_unval & ref_set),
            "fp": len(merged_unval - ref_set),
            "recall_ceiling_pct": round(len(merged_unval & ref_set) / ref_count * 100.0, 2) if ref_count else 0.0,
        },
        {
            "stage": "7_validated_s2t",
            "label": "LLM Validated (S->T)",
            "candidate_pairs": len(s2t_val),
            "tp": len(s2t_val & ref_set),
            "fp": len(s2t_val - ref_set),
            "recall_ceiling_pct": round(len(s2t_val & ref_set) / ref_count * 100.0, 2) if ref_count else 0.0,
        },
        {
            "stage": "8_validated_t2s",
            "label": "LLM Validated (T->S)",
            "candidate_pairs": len(t2s_val),
            "tp": len(t2s_val & ref_set),
            "fp": len(t2s_val - ref_set),
            "recall_ceiling_pct": round(len(t2s_val & ref_set) / ref_count * 100.0, 2) if ref_count else 0.0,
        },
        {
            "stage": "9_final_reciprocal_merged",
            "label": "Final Reciprocal Merger",
            "candidate_pairs": len(final_merged),
            "tp": len(final_merged & ref_set),
            "fp": len(final_merged - ref_set),
            "recall_ceiling_pct": round(len(final_merged & ref_set) / ref_count * 100.0, 2) if ref_count else 0.0,
        },
    ]

    return {
        "reference_count": ref_count,
        "strategy_pools": strat_pools,
        "validation_total_evaluated": val_total,
        "validation_bypasses": val_bypass,
        "validation_llm_calls": val_llm_calls,
        "validation_accepted": val_accepted,
        "validation_acceptance_rate_pct": val_acceptance_rate_pct,
        "merger_union_candidates": len(union_val),
        "merger_retained_count": len(final_merged),
        "merger_retention_rate_pct": merger_retention_rate_pct,
        "stages": stages,
    }


def export_alignment_rdf_xml(
    pairs: Iterable[Tuple[str, str]],
    output_path: str | Path,
    onto1_uri: str = "http://cmt",
    onto2_uri: str = "http://confOf",
) -> Path:
    """Export predicted `(Source, Target)` pairs in standard OAEI Alignment API RDF/XML format."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    sorted_pairs = sorted({(str(a), str(b)) for a, b in pairs})

    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<rdf:RDF xmlns="http://knowledgeweb.semanticweb.org/heterogeneity/alignment"',
        '         xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"',
        '         xmlns:xsd="http://www.w3.org/2001/XMLSchema#">',
        "  <Alignment>",
        "    <xml>yes</xml>",
        "    <level>0</level>",
        "    <type>??</type>",
        f"    <onto1>{escape(onto1_uri)}</onto1>",
        f"    <onto2>{escape(onto2_uri)}</onto2>",
    ]
    for s_uri, t_uri in sorted_pairs:
        lines.extend(
            [
                "    <map>",
                "      <Cell>",
                f'        <entity1 rdf:resource="{escape(s_uri)}"/>',
                f'        <entity2 rdf:resource="{escape(t_uri)}"/>',
                '        <measure rdf:datatype="xsd:float">1.0</measure>',
                "        <relation>=</relation>",
                "      </Cell>",
                "    </map>",
            ]
        )
    lines.extend(["  </Alignment>", "</rdf:RDF>", ""])
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_pairs_csv(pairs: Iterable[Tuple[str, str]], csv_path: str | Path) -> Path:
    """Write `(Source, Target)` pairs deterministically to a CSV with `Source,Target` header."""
    out = Path(csv_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    sorted_pairs = sorted({(str(a), str(b)) for a, b in pairs})
    df = pd.DataFrame(sorted_pairs, columns=["Source", "Target"])
    df.to_csv(out, index=False, encoding="utf-8")
    return out

