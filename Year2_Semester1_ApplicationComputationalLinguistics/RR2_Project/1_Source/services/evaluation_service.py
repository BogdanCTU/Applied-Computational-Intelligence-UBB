"""Evaluation metrics, stage attrition, threshold sensitivity, and chart generation service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd
from matplotlib.figure import Figure

from ...evaluation.charts import (
    build_precision_recall_scatter_figure,
    build_prf1_comparison_figure,
    build_runtime_and_calls_figure,
    build_stage_attrition_figure,
    build_threshold_sensitivity_figure,
)
from ..paths import ProjectPaths, resolve_project_paths
from .experiment_history_service import ExperimentHistoryService


class EvaluationService:
    """Aggregates run metrics, attrition data, and Matplotlib figures for GUI & reports."""

    def __init__(
        self,
        paths: ProjectPaths | None = None,
        history_service: ExperimentHistoryService | None = None,
    ):
        self.paths = paths or resolve_project_paths()
        self.history = history_service or ExperimentHistoryService(self.paths)

    def get_benchmark_comparison_rows(self) -> List[Dict[str, Any]]:
        """Return metrics rows across committed references and completed replication runs."""
        rows: List[Dict[str, Any]] = [
            {
                "experiment_id": "exp_a_upstream_gpt4o_head_csv",
                "short_label": "Exp A: GPT-4o (HEAD CSV)",
                "profile": "upstream_product_reference",
                "tp": 6,
                "fp": 2,
                "fn": 10,
                "precision_pct": 75.00,
                "recall_pct": 37.50,
                "f1_pct": 50.00,
                "runtime_s": 0.0,
                "llm_calls": 0,
            },
            {
                "experiment_id": "exp_a_upstream_gpt4o_pvl_v1",
                "short_label": "Exp A: GPT-4o (v1.0.1 CSV)",
                "profile": "upstream_product_reference",
                "tp": 6,
                "fp": 3,
                "fn": 10,
                "precision_pct": 66.67,
                "recall_pct": 37.50,
                "f1_pct": 48.00,
                "runtime_s": 0.0,
                "llm_calls": 0,
            },
            {
                "experiment_id": "ref_upstream_lite_committed",
                "short_label": "Upstream Lite (Ref Table)",
                "profile": "upstream_agent_om_lite_ref",
                "tp": 4,
                "fp": 3,
                "fn": 12,
                "precision_pct": 57.14,
                "recall_pct": 25.00,
                "f1_pct": 34.78,
                "runtime_s": 0.0,
                "llm_calls": 0,
            },
        ]

        for r in self.history.list_runs(include_historical=False):
            if r.get("is_readonly_reference") or r.get("status") != "completed":
                continue
            if "smoke" in str(r.get("experiment_id", "")).lower():
                continue
            rows.append(
                {
                    "experiment_id": r["experiment_id"],
                    "short_label": r["experiment_id"][:28],
                    "profile": r["profile_name"],
                    "tp": r["tp"],
                    "fp": r["fp"],
                    "fn": r["fn"],
                    "precision_pct": r["precision_pct"],
                    "recall_pct": r["recall_pct"],
                    "f1_pct": r["f1_pct"],
                    "runtime_s": r["runtime_s"],
                    "llm_calls": r["llm_calls"],
                }
            )
        return rows

    def load_stage_attrition_for_run(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        att_file = self.paths.replication_runs_dir / experiment_id / "stage_attrition.json"
        if att_file.is_file():
            return json.loads(att_file.read_text(encoding="utf-8"))
        return None

    def load_threshold_sensitivity_rows(self) -> List[Dict[str, Any]]:
        """Load threshold sensitivity CSV from replication runs or read-only historical output."""
        candidates = [
            self.paths.replication_runs_dir / "comparisons" / "threshold_sensitivity.csv",
            self.paths.output_dir / "step7a_threshold_sensitivity.csv",
            self.paths.output_dir / "step7c_threshold_sensitivity.csv",
        ]
        for c in candidates:
            if c.is_file():
                df = pd.read_csv(c)
                if "sub_category" in df.columns:
                    filtered = df[df["sub_category"] == "Top1_Reciprocal_Merger"]
                    if not filtered.empty:
                        df = filtered
                if "profile" in df.columns:
                    filtered_p = df[df["profile"] == "local_adapted"]
                    if not filtered_p.empty:
                        df = filtered_p
                out: List[Dict[str, Any]] = []
                for _, row in df.iterrows():
                    out.append(
                        {
                            "threshold": float(row.get("threshold", row.get("similarity_threshold", 0.90))),
                            "precision_pct": float(row.get("precision_pct", row.get("precision", row.get("final_precision", 0.0)))),
                            "recall_pct": float(row.get("recall_pct", row.get("recall", row.get("final_recall", 0.0)))),
                            "f1_pct": float(row.get("f1_pct", row.get("f1", row.get("final_f1", 0.0)))),
                        }
                    )
                if out:
                    return out
        return []

    def build_all_figures(self) -> Dict[str, Figure]:
        rows = self.get_benchmark_comparison_rows()
        figs: Dict[str, Figure] = {
            "prf1_bar": build_prf1_comparison_figure(rows),
            "pr_scatter": build_precision_recall_scatter_figure(rows),
            "runtime_and_calls": build_runtime_and_calls_figure(rows),
        }

        attrition_map: Dict[str, Sequence[Dict[str, Any]]] = {}
        for r in rows:
            att = self.load_stage_attrition_for_run(str(r["experiment_id"]))
            if att and att.get("stages"):
                attrition_map[str(r["short_label"])] = att["stages"]
        if attrition_map:
            figs["stage_attrition"] = build_stage_attrition_figure(attrition_map)

        thresh_rows = self.load_threshold_sensitivity_rows()
        if thresh_rows:
            figs["threshold_sensitivity"] = build_threshold_sensitivity_figure(thresh_rows)

        return figs
