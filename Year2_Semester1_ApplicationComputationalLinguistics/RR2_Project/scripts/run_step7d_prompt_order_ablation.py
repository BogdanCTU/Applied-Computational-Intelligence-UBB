"""
Step 7D: Experiment A2 - Directional Prompt Sensitivity Ablation.

Evaluates three prompt-order variants on the Step 7B candidate sets at tau = 0.850:
- A2.1: Original ordering (Is {query} equivalent to {candidate}?)
- A2.2: Reversed ordering (Is {candidate} equivalent to {query}?)
- A2.3: Canonical source-target ordering (Is {source} equivalent to {target}?)

Maintains all other parameters strictly invariant:
- Model: qwen3.5:9b (Ollama local, temperature=0.0, num_ctx=2048, reasoning=False)
- Threshold: 0.850
- Top-k: 3, RRF k: 0
- Exact-name bypass: Enabled
- Reciprocal merger: Enabled
- Evaluation: Canonical 16 reference correspondences from reference.xml

Outputs:
- output/step7d_prompt_order_comparison.csv
- output/step7d_validation_decisions.csv
- output/step7d_summary.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
import rdflib
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

# Ensure project root in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import config
from src.db.database_manager import DatabaseManager
from src.matching.merger import ReciprocalMerger
from src.matching.validator import MatchingValidator, ValidationRecord
from src.retrieval.rank_fusion import reciprocal_rank_fusion
from src.utils.text_processing import cleaning, uri_to_name
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


class DirectionalOrderValidator(MatchingValidator):
    """
    Subclass of MatchingValidator allowing controlled candidate order in prompts:
    - mode='original': Is {query} equivalent to {candidate}?
    - mode='reversed': Is {candidate} equivalent to {query}?
    - mode='canonical': Is {source} equivalent to {target}? (always source first)
    """

    def __init__(
        self,
        mode: str = "original",
        llm: Optional[BaseChatModel] = None,
        context: str = config.context,
    ):
        super().__init__(llm=llm, context=context)
        if mode not in {"original", "reversed", "canonical"}:
            raise ValueError(f"Unknown prompt order mode: {mode}")
        self.mode = mode

    def validate_candidate_pair(
        self,
        source_uri: str,
        target_uri: str,
        source_name: Optional[str] = None,
        target_name: Optional[str] = None,
        context: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> ValidationRecord:
        s_name = source_name or uri_to_name(source_uri)
        t_name = target_name or uri_to_name(target_uri)
        ctx = context or self.context

        # Check exact-name bypass first (reproducing production pipeline)
        is_bypass, clean_s, clean_t = self.check_name_bypass(s_name, t_name)

        if is_bypass:
            return ValidationRecord(
                source_uri=source_uri,
                target_uri=target_uri,
                source_name=s_name,
                target_name=t_name,
                cleaned_source_name=clean_s,
                cleaned_target_name=clean_t,
                bypassed=True,
                direction=direction,
                prompt="BYPASSED",
                raw_response="BYPASSED: Identical cleaned names",
                decision="yes",
                duration_ms=0.0,
            )

        # Determine prompt argument ordering
        # Here: s_name is the query entity, t_name is the candidate entity
        if self.mode == "original":
            # Is {query} equivalent to {candidate}?
            term_a, term_b = clean_s, clean_t
        elif self.mode == "reversed":
            # Is {candidate} equivalent to {query}?
            term_a, term_b = clean_t, clean_s
        elif self.mode == "canonical":
            # Always source ontology entity first, target ontology entity second
            if direction == "Target->Source":
                # In T->S: query is target, cand is source -> swap so source is first
                term_a, term_b = clean_t, clean_s
            else:
                # In S->T: query is source, cand is target -> source is already first
                term_a, term_b = clean_s, clean_t

        prompt_text = self.PROMPT_TEMPLATE.format(a=term_a, b=term_b, context=ctx)
        llm = self._ensure_llm()

        t0 = time.perf_counter()
        try:
            response = llm.invoke(prompt_text)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            raw_text = str(response.content).strip()
            parsed = self.extract_yes_no(raw_text)
            decision = parsed if parsed else "no"

            prompt_toks = getattr(response, "usage_metadata", {}).get("input_tokens", 0) if hasattr(response, "usage_metadata") and response.usage_metadata else 0
            comp_toks = getattr(response, "usage_metadata", {}).get("output_tokens", 0) if hasattr(response, "usage_metadata") and response.usage_metadata else 0

            return ValidationRecord(
                source_uri=source_uri,
                target_uri=target_uri,
                source_name=s_name,
                target_name=t_name,
                cleaned_source_name=clean_s,
                cleaned_target_name=clean_t,
                bypassed=False,
                direction=direction,
                prompt=prompt_text,
                raw_response=raw_text,
                decision=decision,
                duration_ms=duration_ms,
                prompt_tokens=prompt_toks,
                completion_tokens=comp_toks,
                total_tokens=prompt_toks + comp_toks,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return ValidationRecord(
                source_uri=source_uri,
                target_uri=target_uri,
                source_name=s_name,
                target_name=t_name,
                cleaned_source_name=clean_s,
                cleaned_target_name=clean_t,
                bypassed=False,
                direction=direction,
                prompt=prompt_text,
                raw_response="",
                decision="error",
                duration_ms=duration_ms,
                error_message=str(e),
            )


def extract_candidate_snapshot(
    db: DatabaseManager,
    tau: float = 0.850,
    top_k: int = 3,
    rrf_k: int = 0,
) -> Dict[str, Dict[str, List[Tuple[float, List[str]]]]]:
    """
    Extracts and freezes candidate score groups for all Source and Target entities
    at threshold tau using RRF k=0. Reuses these exact rankings across all variants.
    """
    strategies = ["syntactic_matching", "lexical_matching", "semantic_matching"]

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT entity_id, entity_uri, source_or_target FROM ontology_matching ORDER BY entity_id ASC;")
            all_rows = cur.fetchall()

    source_eids = [r[0] for r in all_rows if r[2] == "Source"]
    target_eids = [r[0] for r in all_rows if r[2] == "Target"]

    snapshot: Dict[str, Dict[str, List[Tuple[float, List[str]]]]] = {
        "Source": {},
        "Target": {},
    }

    print(f"Freezing candidate snapshots at tau = {tau:.3f} (RRF k={rrf_k}, top_k={top_k})...", flush=True)

    for direction, eids in [("Source", source_eids), ("Target", target_eids)]:
        for eid in eids:
            rankings = []
            for strat in strategies:
                cands = db.query_strategy(
                    entity_id=eid,
                    table_name=strat,
                    similarity_threshold=tau,
                    num_matches=config.num_matches,
                    top_k=top_k,
                )
                valid = [c for c in cands if c != config.null_value_matching]
                if valid:
                    rankings.append(valid)
            if rankings:
                fused = reciprocal_rank_fusion(*rankings, k=rrf_k, exclude_items=[config.null_value_matching])
                # Slice to top_k score groups
                snapshot[direction][eid] = fused[:top_k]
            else:
                snapshot[direction][eid] = []

    print(f"Snapshot ready: {len(snapshot['Source'])} Source entities, {len(snapshot['Target'])} Target entities.\n", flush=True)
    return snapshot


def run_variant_on_snapshot(
    db: DatabaseManager,
    validator: DirectionalOrderValidator,
    merger: ReciprocalMerger,
    candidate_snapshot: Dict[str, Dict[str, List[Tuple[float, List[str]]]]],
    variant_name: str,
    top_k: int = 3,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Set[Tuple[str, str]]]:
    """
    Executes validation and reciprocal merger on the frozen candidate snapshot.
    """
    t0 = time.perf_counter()
    all_val_records: List[ValidationRecord] = []

    # Map entity_id -> URI and name
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT entity_id, entity_uri FROM ontology_matching;")
            eid_to_uri = dict(cur.fetchall())

    # 1. Source -> Target validation
    s2t_predictions: Set[Tuple[str, str]] = set()
    s2t_calls = 0
    s2t_bypasses = 0

    for q_eid, score_groups in candidate_snapshot["Source"].items():
        q_uri = eid_to_uri[q_eid]
        q_name = uri_to_name(q_uri)

        matched_in_entity = []
        for score, cand_ids in score_groups:
            accepted_in_group = []
            for c_id in cand_ids:
                c_uri = eid_to_uri[c_id]
                c_name = uri_to_name(c_uri)

                rec = validator.validate_candidate_pair(
                    source_uri=q_uri,
                    target_uri=c_uri,
                    source_name=q_name,
                    target_name=c_name,
                    context=config.context,
                    direction="Source->Target",
                )
                all_val_records.append(rec)
                if rec.bypassed:
                    s2t_bypasses += 1
                else:
                    s2t_calls += 1

                if rec.decision == "yes":
                    accepted_in_group.append(c_uri)

            if accepted_in_group:
                matched_in_entity.extend(accepted_in_group)
                break  # Score-group break rule

        for t_uri in matched_in_entity:
            s2t_predictions.add((q_uri, t_uri))

    # 2. Target -> Source validation
    t2s_predictions: Set[Tuple[str, str]] = set()
    t2s_calls = 0
    t2s_bypasses = 0

    for q_eid, score_groups in candidate_snapshot["Target"].items():
        q_uri = eid_to_uri[q_eid]
        q_name = uri_to_name(q_uri)

        matched_in_entity = []
        for score, cand_ids in score_groups:
            accepted_in_group = []
            for c_id in cand_ids:
                c_uri = eid_to_uri[c_id]
                c_name = uri_to_name(c_uri)

                rec = validator.validate_candidate_pair(
                    source_uri=q_uri,
                    target_uri=c_uri,
                    source_name=q_name,
                    target_name=c_name,
                    context=config.context,
                    direction="Target->Source",
                )
                all_val_records.append(rec)
                if rec.bypassed:
                    t2s_bypasses += 1
                else:
                    t2s_calls += 1

                if rec.decision == "yes":
                    accepted_in_group.append(c_uri)

            if accepted_in_group:
                matched_in_entity.extend(accepted_in_group)
                break

        for s_uri in matched_in_entity:
            # Normalize to canonical (Source_URI, Target_URI)
            t2s_predictions.add((s_uri, q_uri))

    # 3. Reciprocal Merger
    final_predictions = merger.merge_alignments(s2t_predictions, t2s_predictions)
    duration_s = time.perf_counter() - t0

    # Token accounting
    prompt_tokens = sum(r.prompt_tokens for r in all_val_records)
    completion_tokens = sum(r.completion_tokens for r in all_val_records)

    llm_accepts = sum(1 for r in all_val_records if not r.bypassed and r.decision == "yes")
    llm_rejects = sum(1 for r in all_val_records if not r.bypassed and r.decision == "no")

    stats = {
        "variant": variant_name,
        "duration_s": round(duration_s, 2),
        "total_validation_records": len(all_val_records),
        "llm_calls": s2t_calls + t2s_calls,
        "bypasses": s2t_bypasses + t2s_bypasses,
        "llm_accepts": llm_accepts,
        "llm_rejects": llm_rejects,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "s2t_predicted_pairs": s2t_predictions,
        "t2s_predicted_pairs": t2s_predictions,
        "final_predicted_pairs": final_predictions,
    }

    # Format records for export
    record_dicts = []
    for r in all_val_records:
        d = asdict(r)
        d["variant"] = variant_name
        record_dicts.append(d)

    return stats, record_dicts, final_predictions


def main():
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    ref_path = PROJECT_ROOT.parent / "original_repo/data/conference/cmt-confof/component/reference.xml"
    reference_pairs = load_reference_alignment(ref_path)
    print(f"Loaded {len(reference_pairs)} reference correspondences from reference.xml", flush=True)

    db = DatabaseManager()
    ensure_database_populated(db)

    # 1. Freeze candidate snapshot at tau = 0.850
    candidate_snapshot = extract_candidate_snapshot(db, tau=0.850, top_k=3, rrf_k=0)

    # 2. Setup Ollama LLM
    llm = ChatOllama(
        model=config.default_llm,
        temperature=config.temperature,
        num_ctx=config.num_ctx,
        reasoning=False,
    )
    merger = ReciprocalMerger()

    variants = [
        ("A2.1_Original", "original"),
        ("A2.2_Reversed", "reversed"),
        ("A2.3_Canonical", "canonical"),
    ]

    all_summaries: Dict[str, Any] = {}
    all_decisions: List[Dict[str, Any]] = []
    comparison_rows = []

    for v_name, v_mode in variants:
        print(f"========================================================", flush=True)
        print(f"Executing Variant: {v_name} (Mode: {v_mode})", flush=True)
        print(f"========================================================", flush=True)

        validator = DirectionalOrderValidator(mode=v_mode, llm=llm, context=config.context)
        stats, rec_dicts, final_preds = run_variant_on_snapshot(
            db=db,
            validator=validator,
            merger=merger,
            candidate_snapshot=candidate_snapshot,
            variant_name=v_name,
            top_k=3,
        )

        all_decisions.extend(rec_dicts)

        s2t_m = calculate_metrics(stats["s2t_predicted_pairs"], reference_pairs)
        t2s_m = calculate_metrics(stats["t2s_predicted_pairs"], reference_pairs)
        rec_m = calculate_metrics(final_preds, reference_pairs)

        print(f"[{v_name}] S->T : {s2t_m['predicted_count']} pairs | TP={s2t_m['tp']}, FP={s2t_m['fp']} | P={s2t_m['precision']}%, R={s2t_m['recall']}%, F1={s2t_m['f1']}%", flush=True)
        print(f"[{v_name}] T->S : {t2s_m['predicted_count']} pairs | TP={t2s_m['tp']}, FP={t2s_m['fp']} | P={t2s_m['precision']}%, R={t2s_m['recall']}%, F1={t2s_m['f1']}%", flush=True)
        print(f"[{v_name}] Recip: {rec_m['predicted_count']} pairs | TP={rec_m['tp']}, FP={rec_m['fp']} | P={rec_m['precision']}%, R={rec_m['recall']}%, F1={rec_m['f1']}%", flush=True)
        print(f"[{v_name}] Calls: {stats['llm_calls']} ({stats['llm_accepts']} yes, {stats['llm_rejects']} no), Bypasses: {stats['bypasses']}, Time: {stats['duration_s']}s\n", flush=True)

        comparison_rows.append({
            "variant": v_name,
            "mode": v_mode,
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
        })

        all_summaries[v_name] = {
            "stats": {k: v for k, v in stats.items() if not k.endswith("_pairs")},
            "source_to_target_metrics": s2t_m,
            "target_to_source_metrics": t2s_m,
            "reciprocal_metrics": rec_m,
        }

    # Export comparison CSV
    df_comp = pd.DataFrame(comparison_rows)
    comp_csv = output_dir / "step7d_prompt_order_comparison.csv"
    df_comp.to_csv(comp_csv, index=False)
    print(f"Saved comparison to {comp_csv}", flush=True)

    # Export validation decisions CSV
    df_decisions = pd.DataFrame(all_decisions)
    dec_csv = output_dir / "step7d_validation_decisions.csv"
    df_decisions.to_csv(dec_csv, index=False)
    print(f"Saved {len(df_decisions)} validation decisions to {dec_csv}", flush=True)

    # Export summary JSON
    sum_json = output_dir / "step7d_summary.json"
    with open(sum_json, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)
    print(f"Saved summary JSON to {sum_json}", flush=True)


if __name__ == "__main__":
    main()

