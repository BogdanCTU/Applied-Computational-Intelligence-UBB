"""Report and artifact bundle export service for CSV, JSON, RDF XML, Markdown, and PNG charts."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ...evaluation.charts import save_figure
from ..paths import ProjectPaths, resolve_project_paths
from .evaluation_service import EvaluationService


class ReportGenerationService:
    """Exports non-destructive timestamped bundles inside `agent_om_local/output/exports/`."""

    def __init__(
        self,
        paths: ProjectPaths | None = None,
        eval_service: EvaluationService | None = None,
    ):
        self.paths = paths or resolve_project_paths()
        self.eval_service = eval_service or EvaluationService(self.paths)

    def export_full_bundle(
        self,
        export_name: Optional[str] = None,
        selected_experiment_id: Optional[str] = None,
        target_parent_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Export CSVs, JSON summaries, Markdown report, RDF alignment, and PNG charts."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        folder_name = export_name or f"export_{ts}"
        base_parent = Path(target_parent_dir or self.paths.exports_dir).resolve()
        export_dir = base_parent / folder_name
        if export_dir.exists() and any(export_dir.iterdir()):
            export_dir = base_parent / f"{folder_name}_{ts}"
        export_dir.mkdir(parents=True, exist_ok=True)

        exported_files: List[str] = []

        # 1. Benchmark comparison CSV & JSON
        rows = self.eval_service.get_benchmark_comparison_rows()
        bench_csv = export_dir / "benchmark_comparison.csv"
        pd.DataFrame(rows).to_csv(bench_csv, index=False, encoding="utf-8")
        exported_files.append(str(bench_csv))

        bench_json = export_dir / "benchmark_comparison.json"
        bench_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        exported_files.append(str(bench_json))

        # 2. High-DPI PNG charts
        charts_dir = export_dir / "charts"
        figs = self.eval_service.build_all_figures()
        for chart_key, fig in figs.items():
            png_path = save_figure(fig, charts_dir / f"{chart_key}.png", dpi=200)
            exported_files.append(str(png_path))

        # 3. Copy selected experiment's alignments & summary if specified
        if selected_experiment_id:
            src_run_dir = self.paths.replication_runs_dir / selected_experiment_id
            if src_run_dir.is_dir():
                run_sub = export_dir / f"run_{selected_experiment_id}"
                run_sub.mkdir(parents=True, exist_ok=True)
                for fname in (
                    "run_summary.json",
                    "config_snapshot.json",
                    "metrics_6variants.csv",
                    "stage_attrition.csv",
                    "validation_records.csv",
                    "ontology_matching.csv",
                ):
                    src_f = src_run_dir / fname
                    if src_f.is_file():
                        dst_f = run_sub / fname
                        shutil.copy2(src_f, dst_f)
                        exported_files.append(str(dst_f))
                align_sub = src_run_dir / "alignments"
                if align_sub.is_dir():
                    dst_align = run_sub / "alignments"
                    shutil.copytree(align_sub, dst_align, dirs_exist_ok=True)
                    for f in sorted(dst_align.iterdir()):
                        exported_files.append(str(f))

        # 4. Generate Markdown summary report (+ copy full final_replication_report.md if present)
        md_lines = [
            "# Agent-OM Replication Workbench — Exported Summary Report",
            "",
            f"- **Generated (UTC):** `{datetime.now(timezone.utc).isoformat()}`",
            f"- **Export Directory:** `{export_dir}`",
            "",
            "## Benchmark Comparison Summary",
            "",
            "| Experiment | Profile | TP | FP | FN | Precision (%) | Recall (%) | F1 (%) | Runtime (s) | LLM Calls |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
        for r in rows:
            md_lines.append(
                f"| `{r['short_label']}` | `{r['profile']}` | {r['tp']} | {r['fp']} | {r['fn']} | "
                f"{r['precision_pct']:.2f} | {r['recall_pct']:.2f} | {r['f1_pct']:.2f} | "
                f"{r['runtime_s']:.2f} | {r['llm_calls']} |"
            )
        md_path = export_dir / "replication_export_report.md"
        md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        exported_files.append(str(md_path))

        full_sci_report = self.paths.docs_dir / "final_replication_report.md"
        if full_sci_report.is_file():
            dst_full = export_dir / "final_replication_report.md"
            shutil.copy2(full_sci_report, dst_full)
            exported_files.append(str(dst_full))

        return {"export_dir": str(export_dir), "files": exported_files}

