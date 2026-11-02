"""Experiment history discovery service across replication_runs/ and read-only historical runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..paths import ProjectPaths, resolve_project_paths


class ExperimentHistoryService:
    """Scans `output/replication_runs/` and read-only historical artifacts without modifying them."""

    def __init__(self, paths: ProjectPaths | None = None):
        self.paths = paths or resolve_project_paths()

    def list_runs(self, include_historical: bool = True) -> List[Dict[str, Any]]:
        runs: List[Dict[str, Any]] = []

        # 1. Replication runs (both local and upstream isolated runs)
        rep_root = self.paths.replication_runs_dir
        if rep_root.is_dir():
            for child in sorted(rep_root.iterdir()):
                if not child.is_dir() or child.name in ("manifests", "configs", "comparisons"):
                    continue
                summary_path = child / "run_summary.json"
                if not summary_path.is_file():
                    continue
                try:
                    raw = json.loads(summary_path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                runs.append(self._normalize_run_record(child, raw))

        # 2. Committed upstream reference entries (read-only metadata computed from actual files)
        orig = self.paths.original_repo_dir
        gpt4o_pred = orig / "alignment" / "conference" / "cmt-confof" / "component" / "predict.csv"
        ref_xml = orig / "data" / "conference" / "cmt-confof" / "component" / "reference.xml"
        if gpt4o_pred.is_file() and ref_xml.is_file():
            from ...evaluation.metrics import (
                compute_alignment_metrics,
                load_alignment_csv_pairs,
                load_reference_pairs,
            )

            gm = compute_alignment_metrics(
                load_alignment_csv_pairs(gpt4o_pred), load_reference_pairs(ref_xml)
            )
            runs.append(
                {
                    "experiment_id": "ref_upstream_gpt4o_cmt_confof",
                    "display_name": "[Upstream Reference] Agent-OM (GPT-4o + ada-002, HEAD CSV)",
                    "profile_name": "upstream_product_reference",
                    "status": "reference_readonly",
                    "started_utc": "2025-12-09T00:00:00Z",
                    "runtime_s": 0.0,
                    "llm_calls": 0,
                    "total_tokens": 0,
                    "tp": gm["tp"],
                    "fp": gm["fp"],
                    "fn": gm["fn"],
                    "precision_pct": gm["precision_pct"],
                    "recall_pct": gm["recall_pct"],
                    "f1_pct": gm["f1_pct"],
                    "run_dir": str(gpt4o_pred.parent),
                    "is_readonly_reference": True,
                }
            )

        # 3. Historical Step 6 local hybrid E1 run (read-only)
        if include_historical:
            step6_summary = self.paths.output_dir / "step6_experiments_summary.json"
            if step6_summary.is_file():
                try:
                    s6 = json.loads(step6_summary.read_text(encoding="utf-8"))
                    e1 = (s6.get("experiments") or {}).get("E1") or s6.get("E1") or {}
                    m = e1.get("final_metrics") or e1.get("metrics") or {}
                    if m:
                        runs.append(
                            {
                                "experiment_id": "historical_step6_E1_hybrid",
                                "display_name": "[Historical Step 6 — Hybrid CSV] E1 (qwen3.5:9b + nomic)",
                                "profile_name": "historical_hybrid_readonly",
                                "status": "historical_readonly",
                                "started_utc": "historical",
                                "runtime_s": float(e1.get("duration_seconds", e1.get("total_duration_s", 0.0)) or 0.0),
                                "llm_calls": int(e1.get("validation_calls", e1.get("total_validation_calls", 0)) or 0),
                                "total_tokens": int(e1.get("total_prompt_tokens", 0) or 0)
                                + int(e1.get("total_completion_tokens", 0) or 0),
                                "tp": int(m.get("tp", 0)),
                                "fp": int(m.get("fp", 0)),
                                "fn": int(m.get("fn", 0)),
                                "precision_pct": float(m.get("precision", 0.0)),
                                "recall_pct": float(m.get("recall", 0.0)),
                                "f1_pct": float(m.get("f1", 0.0)),
                                "run_dir": str(self.paths.output_dir),
                                "is_readonly_reference": True,
                            }
                        )
                except Exception:
                    pass

        runs.sort(key=lambda r: str(r.get("started_utc", "")), reverse=True)
        return runs

    def load_run_summary(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        summary_file = self.paths.replication_runs_dir / experiment_id / "run_summary.json"
        if summary_file.is_file():
            return json.loads(summary_file.read_text(encoding="utf-8"))
        return None

    def _normalize_run_record(self, run_dir: Path, raw: Dict[str, Any]) -> Dict[str, Any]:
        exp_id = str(raw.get("experiment_id", run_dir.name))
        # Handle both run_local_replication.py schema and run_upstream_isolated.py schema
        is_upstream_runner = "stages" in raw and ("metrics" in raw or "metrics_comparison" in raw)
        if is_upstream_runner:
            mc = raw.get("metrics") or raw.get("metrics_comparison") or {}
            final_m = (
                mc.get("llm_with_agent")
                or mc.get("final_predict_csv")
                or mc.get("final_merged")
                or {}
            )
            telem = raw.get("llm_telemetry") or raw.get("llm_telemetry_summary") or {}
            raw_status = str(raw.get("status", "completed")).lower()
            return {
                "experiment_id": exp_id,
                "display_name": f"[Upstream Isolated] {exp_id}",
                "profile_name": "upstream_agent_om_lite_isolated",
                "status": "completed" if raw_status == "completed" else raw_status,
                "started_utc": str(
                    raw.get("completed_at_utc", raw.get("started_utc", raw.get("timestamp_utc", "")))
                ),
                "runtime_s": round(
                    float(
                        raw.get(
                            "total_elapsed_sec",
                            raw.get("total_elapsed_s", raw.get("total_runtime_s", 0.0)),
                        )
                        or 0.0
                    ),
                    2,
                ),
                "llm_calls": int(telem.get("total_calls", raw.get("total_llm_calls", 0)) or 0),
                "total_tokens": int(telem.get("total_tokens", 0) or 0),
                "tp": int(final_m.get("tp", 0) or 0),
                "fp": int(final_m.get("fp", 0) or 0),
                "fn": int(final_m.get("fn", 0) or 0),
                "precision_pct": float(final_m.get("precision_pct", final_m.get("precision", 0.0)) or 0.0),
                "recall_pct": float(final_m.get("recall_pct", final_m.get("recall", 0.0)) or 0.0),
                "f1_pct": float(final_m.get("f1_pct", final_m.get("f1", 0.0)) or 0.0),
                "run_dir": str(run_dir),
                "is_readonly_reference": False,
                "raw": raw,
            }

        fm = raw.get("final_metrics") or {}
        telem = raw.get("telemetry") or {}
        prof = str(raw.get("profile_name", "local_adapted"))
        return {
            "experiment_id": exp_id,
            "display_name": f"[{prof}] {exp_id}",
            "profile_name": prof,
            "status": str(raw.get("status", "unknown")),
            "started_utc": str(raw.get("started_utc", "")),
            "runtime_s": round(float(raw.get("total_runtime_s", 0.0) or 0.0), 2),
            "llm_calls": int(telem.get("total_llm_calls", 0) or 0),
            "total_tokens": int(telem.get("total_tokens", 0) or 0),
            "tp": int(fm.get("tp", 0) or 0),
            "fp": int(fm.get("fp", 0) or 0),
            "fn": int(fm.get("fn", 0) or 0),
            "precision_pct": float(fm.get("precision_pct", 0.0) or 0.0),
            "recall_pct": float(fm.get("recall_pct", 0.0) or 0.0),
            "f1_pct": float(fm.get("f1_pct", 0.0) or 0.0),
            "run_dir": str(run_dir),
            "is_readonly_reference": False,
            "raw": raw,
        }
