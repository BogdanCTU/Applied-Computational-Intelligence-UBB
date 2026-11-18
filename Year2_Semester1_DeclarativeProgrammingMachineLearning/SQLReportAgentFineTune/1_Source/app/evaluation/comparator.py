"""Compares baseline vs fine-tuned evaluation runs and formats comparative reports."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
from app.core.config import get_project_root
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModelComparator:
    """Computes differential performance between baseline and fine-tuned checkpoints."""

    def __init__(self, results_dir: Optional[Union[str, Path]] = None):
        if results_dir is None:
            self.results_dir = get_project_root() / "7_Results"
        else:
            self.results_dir = Path(results_dir).resolve()

    def load_run_summary(self, run_name: str) -> Dict[str, Any]:
        """Reads summary.json from a results subfolder."""
        summary_path = self.results_dir / run_name / "summary.json"
        if not summary_path.exists():
            raise FileNotFoundError(f"Run summary not found: {summary_path}")
        with open(summary_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def compare(
        self,
        baseline_name: str = "baseline",
        finetuned_name: str = "fine_tuned",
    ) -> Dict[str, Any]:
        """Calculates performance deltas between two evaluation runs."""
        base = self.load_run_summary(baseline_name)
        tuned = self.load_run_summary(finetuned_name)

        diff = {
            "baseline": base,
            "fine_tuned": tuned,
            "delta": {
                "execution_accuracy": round(tuned["execution_accuracy"] - base["execution_accuracy"], 2),
                "exact_match_rate": round(tuned["exact_match_rate"] - base["exact_match_rate"], 2),
                "valid_sql_rate": round(tuned["valid_sql_rate"] - base["valid_sql_rate"], 2),
                "average_latency_ms": round(tuned["average_latency_ms"] - base["average_latency_ms"], 2),
            },
        }

        # Save comparison JSON
        comp_dir = self.results_dir / "comparisons"
        comp_dir.mkdir(parents=True, exist_ok=True)
        comp_path = comp_dir / f"{baseline_name}_vs_{finetuned_name}.json"
        with open(comp_path, "w", encoding="utf-8") as f:
            json.dump(diff, f, indent=2)

        # Generate markdown report
        md_report = self.generate_markdown_report(diff, baseline_name, finetuned_name)
        md_path = comp_dir / f"{baseline_name}_vs_{finetuned_name}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_report)

        logger.info(f"Comparison report saved: {md_path}")
        return diff

    def generate_markdown_report(
        self,
        diff: Dict[str, Any],
        base_name: str,
        tuned_name: str,
    ) -> str:
        """Renders an executive markdown comparison table."""
        b = diff["baseline"]
        t = diff["fine_tuned"]
        d = diff["delta"]

        def fmt_delta(val: float, suffix: str = "%") -> str:
            sign = "+" if val > 0 else ""
            return f"{sign}{val}{suffix}"

        return f"""# Evaluation Comparison: {base_name} vs {tuned_name}

| Metric | Baseline ({base_name}) | Fine-Tuned ({tuned_name}) | Delta |
| :--- | :---: | :---: | :---: |
| **Execution Accuracy (EX)** | {b['execution_accuracy']}% | {t['execution_accuracy']}% | **{fmt_delta(d['execution_accuracy'])}** |
| **Exact Match Rate (EM)** | {b['exact_match_rate']}% | {t['exact_match_rate']}% | {fmt_delta(d['exact_match_rate'])} |
| **Valid SQL Rate (VSR)** | {b['valid_sql_rate']}% | {t['valid_sql_rate']}% | {fmt_delta(d['valid_sql_rate'])} |
| **Average Latency** | {b['average_latency_ms']} ms | {t['average_latency_ms']} ms | {fmt_delta(d['average_latency_ms'], ' ms')} |
| **Total Test Samples** | {b['total_samples']} | {t['total_samples']} | - |
"""
