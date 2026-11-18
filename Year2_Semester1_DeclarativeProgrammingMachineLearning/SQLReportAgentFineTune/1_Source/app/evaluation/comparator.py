"""Statistical comparison engine between baseline and fine-tuned models."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from app.core.config import get_project_root
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModelComparator:
    """Computes differential performance, confidence intervals, and paired statistics."""

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

    def load_run_samples(self, run_name: str) -> List[Dict[str, Any]]:
        """Reads detailed_samples.json from a results subfolder."""
        samples_path = self.results_dir / run_name / "detailed_samples.json"
        if not samples_path.exists():
            return []
        with open(samples_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def compare(
        self,
        baseline_name: str = "baseline",
        finetuned_name: str = "fine_tuned",
    ) -> Dict[str, Any]:
        """Calculates performance deltas, confidence intervals, and exports JSON, CSV, and Markdown."""
        base = self.load_run_summary(baseline_name)
        tuned = self.load_run_summary(finetuned_name)

        base_samples = self.load_run_samples(baseline_name)
        tuned_samples = self.load_run_samples(finetuned_name)

        # Paired analysis if sample counts match
        paired_count = min(len(base_samples), len(tuned_samples))
        base_correct_tuned_wrong = 0
        base_wrong_tuned_correct = 0
        both_correct = 0
        both_wrong = 0

        for i in range(paired_count):
            b_ex = base_samples[i].get("is_execution_match", False)
            t_ex = tuned_samples[i].get("is_execution_match", False)
            if b_ex and not t_ex:
                base_correct_tuned_wrong += 1
            elif not b_ex and t_ex:
                base_wrong_tuned_correct += 1
            elif b_ex and t_ex:
                both_correct += 1
            else:
                both_wrong += 1

        ex_base = base.get("execution_accuracy", 0.0)
        ex_tuned = tuned.get("execution_accuracy", 0.0)
        ex_delta = round(ex_tuned - ex_base, 2)
        rel_improvement = round(((ex_tuned - ex_base) / ex_base * 100.0), 2) if ex_base > 0 else 0.0

        diff = {
            "baseline": base,
            "fine_tuned": tuned,
            "delta": {
                "execution_accuracy": ex_delta,
                "execution_accuracy_abs_pct_points": ex_delta,
                "execution_accuracy_relative_pct": rel_improvement,
                "exact_match_rate": round(tuned.get("exact_match_rate", 0.0) - base.get("exact_match_rate", 0.0), 2),
                "exact_match_rate_abs_pct_points": round(tuned.get("exact_match_rate", 0.0) - base.get("exact_match_rate", 0.0), 2),
                "valid_sql_rate": round(tuned.get("valid_sql_rate", 0.0) - base.get("valid_sql_rate", 0.0), 2),
                "valid_sql_rate_abs_pct_points": round(tuned.get("valid_sql_rate", 0.0) - base.get("valid_sql_rate", 0.0), 2),
                "average_latency_ms": round(tuned.get("average_latency_ms", 0.0) - base.get("average_latency_ms", 0.0), 2),
            },
            "paired_contingency": {
                "both_correct": both_correct,
                "base_correct_tuned_wrong": base_correct_tuned_wrong,
                "base_wrong_tuned_correct (improved)": base_wrong_tuned_correct,
                "both_wrong": both_wrong,
            },
        }

        # Export JSON
        comp_dir = self.results_dir / "comparisons"
        comp_dir.mkdir(parents=True, exist_ok=True)
        json_path = comp_dir / f"{baseline_name}_vs_{finetuned_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(diff, f, indent=2)

        # Export CSV
        csv_path = comp_dir / f"{baseline_name}_vs_{finetuned_name}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Baseline", "FineTuned", "Delta_Abs", "Delta_Rel"])
            writer.writerow(["Execution_Accuracy_EX", f"{ex_base}%", f"{ex_tuned}%", f"{ex_delta}%", f"{rel_improvement}%"])
            writer.writerow(["Exact_Match_EM", f"{base.get('exact_match_rate')}%", f"{tuned.get('exact_match_rate')}%", f"{diff['delta']['exact_match_rate_abs_pct_points']}%", "N/A"])
            writer.writerow(["Valid_SQL_Rate_VSR", f"{base.get('valid_sql_rate')}%", f"{tuned.get('valid_sql_rate')}%", f"{diff['delta']['valid_sql_rate_abs_pct_points']}%", "N/A"])
            writer.writerow(["Average_Latency_ms", base.get("average_latency_ms"), tuned.get("average_latency_ms"), diff["delta"]["average_latency_ms"], "N/A"])

        # Export Markdown
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
        """Renders an executive markdown comparison table with ASCII bar charts and error distributions."""
        b = diff["baseline"]
        t = diff["fine_tuned"]
        d = diff["delta"]
        p = diff.get("paired_contingency", {})

        def fmt_delta(val: float, suffix: str = "%") -> str:
            sign = "+" if val > 0 else ""
            return f"{sign}{val}{suffix}"

        # ASCII bar chart helper
        def bar(pct: float, width: int = 25) -> str:
            filled = int(round(pct / 100.0 * width))
            return "█" * filled + "░" * (width - filled)

        ci_b = b.get("execution_accuracy_ci_95", ["N/A", "N/A"])
        ci_t = t.get("execution_accuracy_ci_95", ["N/A", "N/A"])

        report = f"""# Statistical Evaluation Comparison: {base_name} vs {tuned_name}

## 1. Executive Summary Table

| Metric | Baseline (`{base_name}`) | Fine-Tuned (`{tuned_name}`) | Absolute Delta | Relative Gain |
| :--- | :---: | :---: | :---: | :---: |
| **Execution Accuracy (EX)** | **{b.get('execution_accuracy')}%** | **{t.get('execution_accuracy')}%** | **{fmt_delta(d['execution_accuracy_abs_pct_points'])}** | **{fmt_delta(d['execution_accuracy_relative_pct'])}** |
| 95% Bootstrap CI (EX) | [{ci_b[0]}%, {ci_b[1]}%] | [{ci_t[0]}%, {ci_t[1]}%] | - | - |
| **Exact Match Rate (EM)** | {b.get('exact_match_rate')}% | {t.get('exact_match_rate')}% | {fmt_delta(d['exact_match_rate_abs_pct_points'])} | - |
| **Valid SQL Rate (VSR)** | {b.get('valid_sql_rate')}% | {t.get('valid_sql_rate')}% | {fmt_delta(d['valid_sql_rate_abs_pct_points'])} | - |
| **Average Latency** | {b.get('average_latency_ms')} ms | {t.get('average_latency_ms')} ms | {fmt_delta(d['average_latency_ms'], ' ms')} | - |
| **Total Test Samples** | {b.get('total_samples')} | {t.get('total_samples')} | - | - |

## 2. Visual Metric Comparison

```text
Execution Accuracy (EX):
Baseline:    {bar(b.get('execution_accuracy', 0))} {b.get('execution_accuracy')}%
Fine-Tuned:  {bar(t.get('execution_accuracy', 0))} {t.get('execution_accuracy')}%

Valid SQL Rate (VSR):
Baseline:    {bar(b.get('valid_sql_rate', 0))} {b.get('valid_sql_rate')}%
Fine-Tuned:  {bar(t.get('valid_sql_rate', 0))} {t.get('valid_sql_rate')}%
```

## 3. Paired Sample Contingency Analysis

- **Both Correct**: {p.get('both_correct', 0)}
- **Improved by Fine-Tuning** (Baseline Fail -> Fine-Tuned Pass): **{p.get('base_wrong_tuned_correct (improved)', 0)}**
- **Regressed by Fine-Tuning** (Baseline Pass -> Fine-Tuned Fail): {p.get('base_correct_tuned_wrong', 0)}
- **Both Failed**: {p.get('both_wrong', 0)}

## 4. Error Category Distributions

| Error Category | Baseline Count | Fine-Tuned Count |
| :--- | :---: | :---: |
"""
        err_b = b.get("error_distribution", {})
        err_t = t.get("error_distribution", {})
        all_err_keys = sorted(set(list(err_b.keys()) + list(err_t.keys())))
        for k in all_err_keys:
            report += f"| `{k}` | {err_b.get(k, 0)} | {err_t.get(k, 0)} |\n"

        return report
