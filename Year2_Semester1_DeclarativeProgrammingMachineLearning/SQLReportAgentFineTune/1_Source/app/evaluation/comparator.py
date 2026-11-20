"""Statistical comparison engine between baseline and fine-tuned models."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from app.core.config import get_project_root
from app.core.logging import get_logger
from app.evaluation.metrics import compute_mcnemar_test, compute_paired_bootstrap_ci

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

        # Build ID-aligned paired outcomes if possible
        paired_count = min(len(base_samples), len(tuned_samples))
        base_by_id = {s["example_id"]: s for s in base_samples}
        tuned_by_id = {s["example_id"]: s for s in tuned_samples}

        common_ids = [s["example_id"] for s in base_samples if s["example_id"] in tuned_by_id]
        if len(common_ids) == paired_count and paired_count > 0:
            aligned_base_outcomes = [int(base_by_id[ex_id].get("is_execution_match", False)) for ex_id in common_ids]
            aligned_tuned_outcomes = [int(tuned_by_id[ex_id].get("is_execution_match", False)) for ex_id in common_ids]
        else:
            aligned_base_outcomes = [int(base_samples[i].get("is_execution_match", False)) for i in range(paired_count)]
            aligned_tuned_outcomes = [int(tuned_samples[i].get("is_execution_match", False)) for i in range(paired_count)]

        # Statistical paired tests
        mcnemar = compute_mcnemar_test(aligned_base_outcomes, aligned_tuned_outcomes)
        paired_ci_low, paired_ci_high = compute_paired_bootstrap_ci(
            aligned_base_outcomes, aligned_tuned_outcomes, num_bootstrap=1000, seed=42
        )

        ex_base = base.get("execution_accuracy", 0.0)
        ex_tuned = tuned.get("execution_accuracy", 0.0)
        ex_delta = round(ex_tuned - ex_base, 2)
        rel_improvement = round(((ex_tuned - ex_base) / ex_base * 100.0), 2) if ex_base > 0 else 0.0

        # Complexity breakdowns
        base_comp = base.get("accuracy_by_complexity", {})
        tuned_comp = tuned.get("accuracy_by_complexity", {})
        all_comps = sorted(set(list(base_comp.keys()) + list(tuned_comp.keys())))
        comp_deltas = {
            c: round(tuned_comp.get(c, 0.0) - base_comp.get(c, 0.0), 2)
            for c in all_comps
        }

        diff = {
            "baseline": base,
            "fine_tuned": tuned,
            "delta": {
                "execution_accuracy": ex_delta,
                "execution_accuracy_abs_pct_points": ex_delta,
                "execution_accuracy_relative_pct": rel_improvement,
                "paired_bootstrap_ci_95": [paired_ci_low, paired_ci_high],
                "exact_match_rate": round(tuned.get("exact_match_rate", 0.0) - base.get("exact_match_rate", 0.0), 2),
                "exact_match_rate_abs_pct_points": round(tuned.get("exact_match_rate", 0.0) - base.get("exact_match_rate", 0.0), 2),
                "valid_sql_rate": round(tuned.get("valid_sql_rate", 0.0) - base.get("valid_sql_rate", 0.0), 2),
                "valid_sql_rate_abs_pct_points": round(tuned.get("valid_sql_rate", 0.0) - base.get("valid_sql_rate", 0.0), 2),
                "average_latency_ms": round(tuned.get("average_latency_ms", 0.0) - base.get("average_latency_ms", 0.0), 2),
                "median_latency_ms": round(tuned.get("median_latency_ms", 0.0) - base.get("median_latency_ms", 0.0), 2),
                "p90_latency_ms": round(tuned.get("p90_latency_ms", 0.0) - base.get("p90_latency_ms", 0.0), 2),
                "complexity_deltas": comp_deltas,
            },
            "mcnemar_test": mcnemar,
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
            writer.writerow(["Paired_Bootstrap_CI_95", "N/A", "N/A", f"[{paired_ci_low}%, {paired_ci_high}%]", "N/A"])
            writer.writerow(["McNemar_p_value", "N/A", "N/A", mcnemar["p_value"], f"stat={mcnemar['chi2_statistic']}"])
            writer.writerow(["Exact_Match_EM", f"{base.get('exact_match_rate')}%", f"{tuned.get('exact_match_rate')}%", f"{diff['delta']['exact_match_rate_abs_pct_points']}%", "N/A"])
            writer.writerow(["Valid_SQL_Rate_VSR", f"{base.get('valid_sql_rate')}%", f"{tuned.get('valid_sql_rate')}%", f"{diff['delta']['valid_sql_rate_abs_pct_points']}%", "N/A"])
            writer.writerow(["Average_Latency_ms", base.get("average_latency_ms"), tuned.get("average_latency_ms"), diff["delta"]["average_latency_ms"], "N/A"])
            writer.writerow(["Median_Latency_ms", base.get("median_latency_ms"), tuned.get("median_latency_ms"), diff["delta"]["median_latency_ms"], "N/A"])
            writer.writerow(["P90_Latency_ms", base.get("p90_latency_ms"), tuned.get("p90_latency_ms"), diff["delta"]["p90_latency_ms"], "N/A"])

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
        mcnemar = diff.get("mcnemar_test", {})
        p = mcnemar.get("contingency_matrix", {})

        def fmt_delta(val: float, suffix: str = "%") -> str:
            sign = "+" if val > 0 else ""
            return f"{sign}{val}{suffix}"

        def bar(pct: float, width: int = 25) -> str:
            filled = int(round(pct / 100.0 * width))
            return "█" * filled + "░" * (width - filled)

        ci_b = b.get("execution_accuracy_ci_95", ["N/A", "N/A"])
        ci_t = t.get("execution_accuracy_ci_95", ["N/A", "N/A"])
        paired_ci = d.get("paired_bootstrap_ci_95", ["N/A", "N/A"])

        report = f"""# Statistical Evaluation Comparison: {base_name} vs {tuned_name}

## 1. Executive Summary Table

| Metric | Baseline (`{base_name}`) | Fine-Tuned (`{tuned_name}`) | Absolute Delta | Relative Gain |
| :--- | :---: | :---: | :---: | :---: |
| **Execution Accuracy (EX)** | **{b.get('execution_accuracy')}%** | **{t.get('execution_accuracy')}%** | **{fmt_delta(d['execution_accuracy_abs_pct_points'])}** | **{fmt_delta(d['execution_accuracy_relative_pct'])}** |
| 95% Bootstrap CI (EX) | [{ci_b[0]}%, {ci_b[1]}%] | [{ci_t[0]}%, {ci_t[1]}%] | [{paired_ci[0]}%, {paired_ci[1]}%] (Paired) | - |
| **McNemar's Test** | - | - | $\\chi^2 = {mcnemar.get('chi2_statistic')}$, $p = {mcnemar.get('p_value')}$ | {'Significant (p < 0.05)' if mcnemar.get('significant') else 'Not Significant'} |
| **Exact Match Rate (EM)** | {b.get('exact_match_rate')}% | {t.get('exact_match_rate')}% | {fmt_delta(d['exact_match_rate_abs_pct_points'])} | - |
| **Format Valid Rate (FVR)** | {b.get('valid_sql_rate')}% | {t.get('valid_sql_rate')}% | {fmt_delta(d['valid_sql_rate_abs_pct_points'])} | - |
| **Executable SQL Rate (ESR)**| {b.get('executable_sql_rate', b.get('valid_sql_rate'))}% | {t.get('executable_sql_rate', t.get('valid_sql_rate'))}% | {fmt_delta(round(t.get('executable_sql_rate', t.get('valid_sql_rate', 0.0)) - b.get('executable_sql_rate', b.get('valid_sql_rate', 0.0)), 2))} | - |
| **Average Latency** | {b.get('average_latency_ms')} ms | {t.get('average_latency_ms')} ms | {fmt_delta(d['average_latency_ms'], ' ms')} | - |
| **Median Latency** | {b.get('median_latency_ms')} ms | {t.get('median_latency_ms')} ms | {fmt_delta(d['median_latency_ms'], ' ms')} | - |
| **P90 Latency** | {b.get('p90_latency_ms')} ms | {t.get('p90_latency_ms')} ms | {fmt_delta(d['p90_latency_ms'], ' ms')} | - |
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

## 3. Paired McNemar Contingency Matrix

| | Tuned Correct (1) | Tuned Incorrect (0) | Total |
| :--- | :---: | :---: | :---: |
| **Baseline Correct (1)** | {p.get('both_correct', 0)} (Both Pass) | **{p.get('base_correct_tuned_wrong', 0)} (Regressed)** | {p.get('both_correct', 0) + p.get('base_correct_tuned_wrong', 0)} |
| **Baseline Incorrect (0)** | **{p.get('base_wrong_tuned_correct', 0)} (Improved)** | {p.get('both_wrong', 0)} (Both Fail) | {p.get('base_wrong_tuned_correct', 0) + p.get('both_wrong', 0)} |
| **Total** | {p.get('both_correct', 0) + p.get('base_wrong_tuned_correct', 0)} | {p.get('base_correct_tuned_wrong', 0) + p.get('both_wrong', 0)} | {p.get('total_pairs', 0)} |

- McNemar $\\chi^2$: **{mcnemar.get('chi2_statistic')}**
- Two-tailed $p$-value: **{mcnemar.get('p_value')}**
- Statistical significance: **{'YES (p < 0.05)' if mcnemar.get('significant') else 'NO (p >= 0.05)'}**
"""
        if "schema_grounding" in t:
            sg = t["schema_grounding"]
            sc = sg.get("contingency", {})
            report += f"""
## 4. Schema Grounding Quality & Contingency Analysis

| Metric | Precision | Recall | F1 Score |
| :--- | :---: | :---: | :---: |
| **Table Selection** | {sg.get('table_precision')}% | {sg.get('table_recall')}% | **{sg.get('table_f1')}%** |
| **Column Selection** | {sg.get('col_precision')}% | {sg.get('col_recall')}% | **{sg.get('col_f1')}%** |

### Schema Selection vs SQL Execution Contingency:
- **Schema Correct & SQL Correct**: **{sc.get('schema_correct_sql_correct', 0)}**
- **Schema Correct but SQL Wrong**: {sc.get('schema_correct_sql_wrong', 0)}
- **Schema Wrong but SQL Correct**: {sc.get('schema_wrong_sql_correct', 0)}
- **Schema Wrong & SQL Wrong**: {sc.get('schema_wrong_sql_wrong', 0)}
"""

        report += """
## 5. Breakdown by SQL Complexity

| Complexity Tier | Baseline EX | Fine-Tuned EX | Absolute Delta |
| :--- | :---: | :---: | :---: |
"""
        base_c = b.get("accuracy_by_complexity", {})
        tuned_c = t.get("accuracy_by_complexity", {})
        comp_keys = ["easy", "medium", "hard", "extra_hard"]
        for c in comp_keys:
            if c in base_c or c in tuned_c:
                b_val = base_c.get(c, 0.0)
                t_val = tuned_c.get(c, 0.0)
                report += f"| `{c}` | {b_val}% | {t_val}% | {fmt_delta(round(t_val - b_val, 2))} |\n"

        report += """
## 5. Error Category Distributions

| Error Category | Baseline Count | Fine-Tuned Count | Delta |
| :--- | :---: | :---: | :---: |
"""
        err_b = b.get("error_distribution", {})
        err_t = t.get("error_distribution", {})
        all_err_keys = sorted(set(list(err_b.keys()) + list(err_t.keys())))
        for k in all_err_keys:
            cnt_b = err_b.get(k, 0)
            cnt_t = err_t.get(k, 0)
            diff_cnt = cnt_t - cnt_b
            sign = "+" if diff_cnt > 0 else ""
            report += f"| `{k}` | {cnt_b} | {cnt_t} | {sign}{diff_cnt} |\n"

        return report
