"""Artifact comparison service powering the GUI Original-vs-Local Comparison View."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from ...evaluation.comparator import compare_two_runs_17_points
from ...evaluation.metrics import load_reference_pairs
from ..paths import ProjectPaths, resolve_project_paths
from .pipeline_inspection_service import PipelineInspectionService


class ArtifactComparisonService:
    """Compares intermediate and final artifacts across any 2 runs or the 4 benchmark configurations."""

    def __init__(
        self,
        paths: ProjectPaths | None = None,
        inspector: PipelineInspectionService | None = None,
    ):
        self.paths = paths or resolve_project_paths()
        self.inspector = inspector or PipelineInspectionService(self.paths)

    def default_reference_pairs(self) -> List[Tuple[str, str]]:
        ref_xml = (
            self.paths.original_repo_dir
            / "data"
            / "conference"
            / "cmt-confof"
            / "component"
            / "reference.xml"
        )
        return load_reference_pairs(ref_xml) if ref_xml.is_file() else []

    def compare_runs(
        self,
        run_a_id_or_dir: str | Path,
        run_a_label: str,
        run_b_id_or_dir: str | Path,
        run_b_label: str,
        reference_xml: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Run full 17-point comparison and build pair-by-pair diff rows for the GUI table."""
        bundle_a = self.inspector.load_run_bundle(run_a_id_or_dir)
        bundle_b = self.inspector.load_run_bundle(run_b_id_or_dir)
        ref_pairs = (
            load_reference_pairs(reference_xml)
            if reference_xml and reference_xml.is_file()
            else self.default_reference_pairs()
        )
        ref_set = set(ref_pairs)

        report_17 = compare_two_runs_17_points(
            run_a_label=run_a_label,
            run_a_data=bundle_a,
            run_b_label=run_b_label,
            run_b_data=bundle_b,
            reference_pairs=ref_pairs,
        )

        final_a: Set[Tuple[str, str]] = set(bundle_a["predictions"]["final_merged"])
        final_b: Set[Tuple[str, str]] = set(bundle_b["predictions"]["final_merged"])
        all_pairs = sorted(final_a | final_b | ref_set)

        pair_diff_rows: List[Dict[str, Any]] = []
        for s_uri, t_uri in all_pairs:
            in_ref = (s_uri, t_uri) in ref_set
            in_a = (s_uri, t_uri) in final_a
            in_b = (s_uri, t_uri) in final_b
            if in_a and in_b and in_ref:
                category = "Shared TP"
            elif in_a and in_b and not in_ref:
                category = "Shared FP"
            elif in_a and not in_b:
                category = "Only in A (TP)" if in_ref else "Only in A (FP)"
            elif in_b and not in_a:
                category = "Only in B (TP)" if in_ref else "Only in B (FP)"
            else:
                category = "Missed by Both (FN)"

            pair_diff_rows.append(
                {
                    "source_uri": s_uri,
                    "target_uri": t_uri,
                    "in_reference": in_ref,
                    "in_run_a": in_a,
                    "in_run_b": in_b,
                    "category": category,
                }
            )

        return {
            "report_17": report_17,
            "pair_diff_rows": pair_diff_rows,
        }

