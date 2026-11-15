"""Pipeline intermediate artifact inspection service for searchable/sortable GUI tables."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from ...evaluation.comparator import load_features_csv
from ...evaluation.metrics import load_alignment_csv_pairs
from ..paths import ProjectPaths, resolve_project_paths


class PipelineInspectionService:
    """Loads per-entity intermediate artifacts from local, upstream isolated, or reference runs."""

    def __init__(self, paths: ProjectPaths | None = None):
        self.paths = paths or resolve_project_paths()

    def resolve_run_artifacts_dir(self, run_dir_or_id: str | Path) -> Path:
        p = Path(run_dir_or_id)
        if p.is_dir():
            return p
        cand = self.paths.replication_runs_dir / str(run_dir_or_id)
        if cand.is_dir():
            return cand
        if str(run_dir_or_id) == "ref_upstream_gpt4o_cmt_confof":
            return (
                self.paths.original_repo_dir / "alignment" / "conference" / "cmt-confof" / "component"
            )
        return p

    def load_run_bundle(self, run_dir_or_id: str | Path) -> Dict[str, Any]:
        """Load unified dictionary compatible with `compare_two_runs_17_points` and GUI Inspector."""
        base = self.resolve_run_artifacts_dir(run_dir_or_id)

        # Locate DB snapshot or ontology_matching.csv (local layout vs upstream nested layout)
        csv_candidates = [
            base / "db_ontology_matching_snapshot.csv",
            base / "ontology_matching.csv",
            base / "alignment" / "conference" / "cmt-confof" / "component" / "ontology_matching.csv",
        ]
        if base.is_dir() and not any(c.is_file() for c in csv_candidates):
            found_csvs = list(base.rglob("ontology_matching.csv"))
            if found_csvs:
                csv_candidates.insert(0, found_csvs[0])

        features_df = pd.DataFrame()
        for c in csv_candidates:
            if c.is_file():
                features_df = load_features_csv(c)
                break

        # Locate alignment directory
        align_dir = base / "alignments"
        if not align_dir.is_dir():
            nested = base / "alignment" / "conference" / "cmt-confof" / "component"
            align_dir = nested if nested.is_dir() else base

        # Load candidates JSON if present
        cands_s2t = []
        cands_t2s = []
        if (base / "candidates_s2t.json").is_file():
            cands_s2t = json.loads((base / "candidates_s2t.json").read_text(encoding="utf-8"))
        if (base / "candidates_t2s.json").is_file():
            cands_t2s = json.loads((base / "candidates_t2s.json").read_text(encoding="utf-8"))

        # Load validation records if present
        val_records = []
        if (base / "validation_records.json").is_file():
            val_records = json.loads((base / "validation_records.json").read_text(encoding="utf-8"))

        # Load chunk counts & config
        chunk_counts = {}
        if (base / "chunk_counts.json").is_file():
            chunk_counts = json.loads((base / "chunk_counts.json").read_text(encoding="utf-8"))
        elif (base / "run_summary.json").is_file():
            rs = json.loads((base / "run_summary.json").read_text(encoding="utf-8"))
            db_rc = (rs.get("database_snapshot") or {}).get("row_counts") or {}
            if db_rc:
                chunk_counts = {
                    "total_entities": db_rc.get("ontology_matching", 0),
                    "syntactic_chunks": db_rc.get("syntactic_matching", 0),
                    "lexical_chunks": db_rc.get("lexical_matching", 0),
                    "semantic_chunks": db_rc.get("semantic_matching", 0),
                }
            else:
                chunk_counts = rs.get("chunk_counts") or rs.get("db_row_counts") or {}

        embedding_dim = None
        if (base / "config_snapshot.json").is_file():
            cs = json.loads((base / "config_snapshot.json").read_text(encoding="utf-8"))
            embedding_dim = (cs.get("config") or {}).get("vector_length")
        elif (base / "run_summary.json").is_file():
            rs = json.loads((base / "run_summary.json").read_text(encoding="utf-8"))
            embedding_dim = (
                (rs.get("config") or {}).get("vector_length")
                or (rs.get("configuration") or {}).get("vector_length")
                or rs.get("embedding_dim")
            )
        elif "original_repo" in str(base):
            embedding_dim = 1536

        # Note: in upstream om_database_matching.py, predict_target_to_source*.csv stores (Source, Target) or (Target, Source)?
        # Let's check: in upstream om_database_matching.py, Target->Source writes Source column first or Target column first?
        # load_alignment_csv_pairs reads (col0, col1); normalize if col0 starts with confOf and col1 starts with cmt!
        def _load_normalized_pairs(csv_file: Path) -> Set[Tuple[str, str]]:
            raw_pairs = load_alignment_csv_pairs(csv_file)
            src_uris = (
                set(features_df[features_df["source_or_target"] == "Source"]["entity_uri"].astype(str))
                if not features_df.empty and "source_or_target" in features_df.columns
                else set()
            )
            tgt_uris = (
                set(features_df[features_df["source_or_target"] == "Target"]["entity_uri"].astype(str))
                if not features_df.empty and "source_or_target" in features_df.columns
                else set()
            )
            normalized: Set[Tuple[str, str]] = set()
            for a, b in raw_pairs:
                if src_uris and tgt_uris and (a in tgt_uris and b in src_uris):
                    normalized.add((b, a))
                else:
                    normalized.add((a, b))
            return normalized

        predictions = {
            "s2t_no_val": _load_normalized_pairs(
                align_dir / "predict_source_to_target_without_validation.csv"
            ),
            "t2s_no_val": _load_normalized_pairs(
                align_dir / "predict_target_to_source_without_validation.csv"
            ),
            "merged_no_val": _load_normalized_pairs(
                align_dir / "predict_merge_without_validation.csv"
            ),
            "s2t_val": _load_normalized_pairs(align_dir / "predict_source_to_target.csv"),
            "t2s_val": _load_normalized_pairs(align_dir / "predict_target_to_source.csv"),
            "final_merged": _load_normalized_pairs(align_dir / "predict.csv"),
        }

        return {
            "base_dir": str(base),
            "features_df": features_df,
            "chunk_counts": chunk_counts,
            "embedding_dim": embedding_dim,
            "candidates": {"s2t": cands_s2t, "t2s": cands_t2s},
            "validation_records": val_records,
            "predictions": predictions,
        }

    def build_entity_inspection_rows(self, run_dir_or_id: str | Path) -> List[Dict[str, Any]]:
        """Join per-entity features, candidates, validations, and final match status for GUI table."""
        bundle = self.load_run_bundle(run_dir_or_id)
        df: pd.DataFrame = bundle["features_df"]
        if df.empty:
            return []

        cand_by_id: Dict[str, Dict[str, Any]] = {}
        for item in bundle["candidates"]["s2t"] + bundle["candidates"]["t2s"]:
            cand_by_id[str(item.get("query_entity_id", ""))] = item

        vals_by_query_uri: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for v in bundle["validation_records"]:
            d_raw = str(v.get("direction", "Source->Target"))
            side = "Source" if "Source->" in d_raw else "Target"
            q_uri = str(v.get("source_uri", ""))
            vals_by_query_uri.setdefault((side, q_uri), []).append(v)

        final_pairs = bundle["predictions"]["final_merged"]
        final_by_src: Dict[str, List[str]] = {}
        final_by_tgt: Dict[str, List[str]] = {}
        for s_u, t_u in sorted(final_pairs):
            final_by_src.setdefault(s_u, []).append(t_u)
            final_by_tgt.setdefault(t_u, []).append(s_u)

        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            eid = str(row.get("entity_id", ""))
            uri = str(row.get("entity_uri", ""))
            side = str(row.get("source_or_target", ""))
            etype = str(row.get("entity_type", ""))
            syn = str(row.get("syntactic_matching", ""))
            lex = str(row.get("lexical_matching", ""))
            sem = str(row.get("semantic_matching", ""))

            cand_info = cand_by_id.get(eid, {})
            val_list = vals_by_query_uri.get((side, uri), [])
            matched_uris = (
                final_by_src.get(uri, []) if side == "Source" else final_by_tgt.get(uri, [])
            )

            rows.append(
                {
                    "entity_id": eid,
                    "entity_uri": uri,
                    "side": side,
                    "entity_type": etype,
                    "syntactic_text": syn,
                    "lexical_text": lex,
                    "semantic_text": sem,
                    "top_candidate_uri": cand_info.get("top_candidate_uri") or "",
                    "candidate_count": len(cand_info.get("candidate_uris", [])),
                    "validation_attempts": len(val_list),
                    "final_matched_uris": ", ".join(matched_uris),
                    "has_final_match": bool(matched_uris),
                    "candidate_detail": cand_info,
                    "validation_detail": val_list,
                }
            )
        return rows
