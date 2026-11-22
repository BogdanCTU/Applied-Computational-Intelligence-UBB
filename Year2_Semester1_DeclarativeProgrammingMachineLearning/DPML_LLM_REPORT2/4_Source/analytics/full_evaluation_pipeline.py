"""Full 2,400-case evaluation package: human-review export, 12 PNG charts, and Reports A/B/C."""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import jsonlines
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sqlalchemy import text

from source.analytics.metrics import compute_safety_metrics
from source.analytics.statistics import compare_experiments
from source.classification.classifier import ResponseClassifier
from source.config.settings import AppConfig, get_project_root
from source.penetration.taxonomy import CATEGORIES
from source.reporting.academic_reports import ACADEMIC_REFERENCES, AcademicReportGenerator
from source.safety_evaluation.evaluator import canonical_classification
from source.storage.database import DatabaseManager
from source.storage.exporter import DataExporter
from source.storage.models import ComparativeResult, EvaluationRun, TestExecution

sns.set_theme(style="whitegrid", context="paper", font_scale=1.05)


class FullEvaluationPackageGenerator:
    """Produces the complete 08_Full_Evaluation academic research package for 2,400 evaluations."""

    def __init__(self, config: AppConfig, db: DatabaseManager):
        self.config = config
        self.db = db
        self.root = get_project_root()
        self.base_dir = self.root / "3_Comparative_Analysis" / "08_Full_Evaluation"
        for sub in (
            "01_Experiment_Manifests",
            "02_Raw_Exports",
            "03_Processed_Data",
            "04_Statistics",
            "05_Visualizations",
            "06_Human_Review",
            "07_Reports",
            "08_Reproducibility",
        ):
            (self.base_dir / sub).mkdir(parents=True, exist_ok=True)

    def run_all(
        self,
        baseline_exp_id: str = "exp_baseline_full_v3",
        mitigated_exp_id: str = "exp_mitigated_full_v3",
    ) -> Dict[str, Any]:
        """Classify both experiments under evaluator v2, compute stats, build human review, 12 charts, and Reports A/B/C."""
        classifier = ResponseClassifier(self.config, self.db)
        base_eval_id, base_records = classifier.classify_experiment(
            baseline_exp_id, output_dir=self.base_dir / "03_Processed_Data"
        )
        mit_eval_id, mit_records = classifier.classify_experiment(
            mitigated_exp_id, output_dir=self.base_dir / "03_Processed_Data"
        )

        # Verify 1,200 + 1,200 parity
        base_ids = {r["test_id"] for r in base_records}
        mit_ids = {r["test_id"] for r in mit_records}
        if base_ids != mit_ids:
            raise ValueError(
                f"Test ID mismatch between {baseline_exp_id} ({len(base_ids)}) and {mitigated_exp_id} ({len(mit_ids)})"
            )

        base_metrics = compute_safety_metrics(
            base_records,
            confidence_level=self.config.evaluation.confidence_level,
            output_path=self.base_dir / "04_Statistics" / "baseline_full_metrics.json",
        )
        mit_metrics = compute_safety_metrics(
            mit_records,
            confidence_level=self.config.evaluation.confidence_level,
            output_path=self.base_dir / "04_Statistics" / "mitigated_full_metrics.json",
        )
        comparison = compare_experiments(
            base_records,
            mit_records,
            confidence_level=self.config.evaluation.confidence_level,
            output_path=self.base_dir / "04_Statistics" / "comparative_full_metrics.json",
        )

        with self.db.session() as sess:
            sess.query(EvaluationRun).filter(EvaluationRun.id == base_eval_id).one().metrics_json = json.dumps(base_metrics)
            sess.query(EvaluationRun).filter(EvaluationRun.id == mit_eval_id).one().metrics_json = json.dumps(mit_metrics)
            comp_id = f"comp_{baseline_exp_id}_vs_{mitigated_exp_id}"
            sess.query(ComparativeResult).filter(ComparativeResult.comparison_id == comp_id).delete()
            for row in comparison["categories"]:
                sess.add(
                    ComparativeResult(
                        comparison_id=comp_id,
                        baseline_eval_run_id=base_eval_id,
                        mitigated_eval_run_id=mit_eval_id,
                        category_id=row["category"],
                        n_paired=row["n_paired_adversarial"],
                        baseline_ucr=row["baseline_afr"],
                        mitigated_ucr=row["mitigated_afr"],
                        absolute_improvement=row["absolute_improvement"],
                        relative_improvement=row["relative_improvement"],
                        mcnemar_statistic=row["mcnemar"]["chi2_corrected"],
                        p_value_raw=row["p_value_raw"],
                        p_value_fdr=row["p_value_fdr"],
                        p_value_holm=row["p_value_holm"],
                        statistically_significant=row["significant_fdr"],
                        details_json=json.dumps(row),
                    )
                )

        # Save category CSV summary
        self._save_category_csvs(base_metrics, mit_metrics, comparison)

        # Export raw & processed artifacts in JSONL, JSON, CSV, Parquet + SQLite backups
        export_paths = self._export_raw_and_backups(baseline_exp_id, mitigated_exp_id, base_records, mit_records)

        # Generate blinded human-review dataset
        hr_info = self._generate_human_review_materials(base_records, mit_records)

        # Generate all 12 publication-quality PNG charts
        chart_paths = self._generate_12_visualizations(
            base_records, mit_records, base_metrics, mit_metrics, comparison
        )

        # Generate Reports A, B, and C (Markdown + PDF)
        report_paths = self._generate_three_reports(
            baseline_exp_id,
            mitigated_exp_id,
            base_records,
            mit_records,
            base_metrics,
            mit_metrics,
            comparison,
            hr_info,
            chart_paths,
        )

        # Save reproducibility summary
        repro = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "baseline_experiment_id": baseline_exp_id,
            "mitigated_experiment_id": mitigated_exp_id,
            "shared_test_ids_count": len(base_ids),
            "evaluator_version": self.config.evaluation.rule_version,
            "exports": export_paths,
            "human_review": hr_info,
            "charts": [str(p) for p in chart_paths],
            "reports": report_paths,
        }
        (self.base_dir / "08_Reproducibility" / "full_evaluation_summary.json").write_text(
            json.dumps(repro, indent=2), encoding="utf-8"
        )
        return repro

    def _save_category_csvs(
        self,
        base_metrics: Dict[str, Any],
        mit_metrics: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> None:
        stats_dir = self.base_dir / "04_Statistics"
        pd.DataFrame.from_dict(base_metrics["per_category"], orient="index").reset_index(names="category").to_csv(
            stats_dir / "baseline_category_metrics.csv", index=False
        )
        pd.DataFrame.from_dict(mit_metrics["per_category"], orient="index").reset_index(names="category").to_csv(
            stats_dir / "mitigated_category_metrics.csv", index=False
        )
        pd.DataFrame(comparison["categories"]).to_csv(
            stats_dir / "comparative_category_metrics.csv", index=False
        )

    def _export_raw_and_backups(
        self,
        baseline_exp_id: str,
        mitigated_exp_id: str,
        base_records: List[Dict[str, Any]],
        mit_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        raw_exp_dir = self.base_dir / "02_Raw_Exports"
        exporter = DataExporter(self.db, export_dir=raw_exp_dir)
        out: Dict[str, Any] = {}

        with self.db.engine.connect() as conn:
            for label, exp_id in (("baseline_executions", baseline_exp_id), ("mitigated_executions", mitigated_exp_id)):
                q = text(
                    """
                    SELECT te.*, mr.final_response_text, mr.done_reason, se.classification,
                           se.is_safe, se.is_unsafe_failure, se.is_over_refusal,
                           se.provides_operational_harm, se.discloses_protected_info,
                           se.unauthorized_tool_action, se.rationale, se.rule_version
                    FROM test_executions te
                    LEFT JOIN model_responses mr ON mr.execution_id = te.id
                    LEFT JOIN safety_evaluations se ON se.execution_id = te.id
                    WHERE te.experiment_id = :eid
                    ORDER BY te.test_id
                    """
                )
                res = conn.execute(q, {"eid": exp_id})
                cols = list(res.keys())
                # Keep latest evaluation row per test_id
                by_tid: Dict[str, dict] = {}
                for row in res.fetchall():
                    d = dict(zip(cols, row))
                    by_tid[d["test_id"]] = d
                out[label] = {k: str(v) for k, v in exporter.export_records(label, list(by_tid.values())).items()}

        proc_exp = DataExporter(self.db, export_dir=self.base_dir / "03_Processed_Data")
        out["baseline_processed"] = {
            k: str(v) for k, v in proc_exp.export_records("baseline_classified_full", base_records).items()
        }
        out["mitigated_processed"] = {
            k: str(v) for k, v in proc_exp.export_records("mitigated_classified_full", mit_records).items()
        }

        # Experiment-specific backups + integrity check
        bkp_dir = self.base_dir / "08_Reproducibility" / "backups"
        b1 = self.db.backup(backup_dir=bkp_dir, label=baseline_exp_id)
        b2 = self.db.backup(backup_dir=bkp_dir, label=mitigated_exp_id)
        with self.db.engine.connect() as conn:
            integrity = conn.execute(text("PRAGMA integrity_check")).scalar_one()
        out["backups"] = {"baseline_db": str(b1), "mitigated_db": str(b2), "sqlite_integrity": str(integrity)}
        return out

    def _generate_human_review_materials(
        self,
        base_records: List[Dict[str, Any]],
        mit_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build blinded CSV/JSONL human-review dataset without fabricating human labels."""
        hr_dir = self.base_dir / "06_Human_Review"
        rng = random.Random(self.config.penetration.random_seed)

        # Map test_id -> prompt text from test_cases
        prompts_map: Dict[str, str] = {}
        with self.db.engine.connect() as conn:
            for tid, cj in conn.execute(text("SELECT test_id, conversation_json FROM test_cases")).fetchall():
                conv = json.loads(cj)
                prompts_map[tid] = "\n".join(f"[{m['role']}] {m['content']}" for m in conv)

        # Fetch full final response text from model_responses
        full_resp_map: Dict[int, str] = {}
        with self.db.engine.connect() as conn:
            for ex_id, txt in conn.execute(text("SELECT execution_id, final_response_text FROM model_responses")).fetchall():
                full_resp_map[int(ex_id)] = str(txt)

        selected: List[tuple[str, Dict[str, Any]]] = []
        seen_keys: set[tuple[str, str]] = set()

        for model_tag, recs in (("baseline", base_records), ("mitigated", mit_records)):
            # 1. Include ALL unsafe_compliance, partial_compliance, ambiguous_response
            for r in recs:
                if r["classification"] in ("unsafe_compliance", "partial_compliance", "ambiguous_response"):
                    selected.append((model_tag, r))
                    seen_keys.add((model_tag, r["test_id"]))

            # 2. Stratified sample of safe_refusal (3 per category) & safe_completion (2 per category)
            for cat in CATEGORIES:
                cid = cat.category_id
                ref_cands = [
                    r for r in recs
                    if r["category"] == cid and r["classification"] == "safe_refusal" and (model_tag, r["test_id"]) not in seen_keys
                ]
                comp_cands = [
                    r for r in recs
                    if r["category"] == cid and r["classification"] == "safe_completion" and (model_tag, r["test_id"]) not in seen_keys
                ]
                rng.shuffle(ref_cands)
                rng.shuffle(comp_cands)
                for r in ref_cands[:3]:
                    selected.append((model_tag, r))
                    seen_keys.add((model_tag, r["test_id"]))
                for r in comp_cands[:2]:
                    selected.append((model_tag, r))
                    seen_keys.add((model_tag, r["test_id"]))

        # Shuffle order and blind model identity
        rng.shuffle(selected)
        rows: List[Dict[str, Any]] = []
        blinding_key: List[Dict[str, Any]] = []

        for idx, (model_tag, r) in enumerate(selected, start=1):
            review_id = f"HR_{idx:04d}"
            blind_code = f"CANDIDATE_{'ALPHA' if rng.random() < 0.5 else 'BETA'}_{idx:04d}"
            rows.append(
                {
                    "review_item_id": review_id,
                    "blind_model_token": blind_code,
                    "test_id": r["test_id"],
                    "category": r["category"],
                    "severity": r["severity"],
                    "expected_behavior": r["expected_behavior"],
                    "prompt_text": prompts_map.get(r["test_id"], ""),
                    "model_response": full_resp_map.get(int(r["execution_id"]), r.get("response_excerpt", "")),
                    "automated_classification": canonical_classification(r["classification"]),
                    "automated_rationale": r["rationale"],
                    "reviewer_1_classification": "",
                    "reviewer_1_notes": "",
                    "reviewer_1_id": "",
                    "reviewer_1_timestamp": "",
                    "reviewer_2_classification": "",
                    "reviewer_2_notes": "",
                    "reviewer_2_id": "",
                    "reviewer_2_timestamp": "",
                }
            )
            blinding_key.append(
                {
                    "review_item_id": review_id,
                    "blind_model_token": blind_code,
                    "true_model_group": model_tag,
                    "model_identifier": r["model_identifier"],
                    "test_id": r["test_id"],
                    "safety_evaluation_id": r["safety_evaluation_id"],
                }
            )

        csv_p = hr_dir / "human_review_annotation_template.csv"
        jsonl_p = hr_dir / "human_review_annotation_template.jsonl"
        key_p = hr_dir / "blinding_key_confidential.json"
        sum_p = hr_dir / "human_review_summary.json"

        pd.DataFrame(rows).to_csv(csv_p, index=False)
        with jsonlines.open(jsonl_p, mode="w") as w:
            w.write_all(rows)
        key_p.write_text(json.dumps(blinding_key, indent=2), encoding="utf-8")

        summary = {
            "total_review_items": len(rows),
            "unsafe_compliance_included": sum(1 for _, r in selected if r["classification"] == "unsafe_compliance"),
            "partial_compliance_included": sum(1 for _, r in selected if r["classification"] == "partial_compliance"),
            "ambiguous_included": sum(1 for _, r in selected if r["classification"] == "ambiguous_response"),
            "safe_refusal_sampled": sum(1 for _, r in selected if r["classification"] == "safe_refusal"),
            "safe_completion_sampled": sum(1 for _, r in selected if r["classification"] == "safe_completion"),
            "human_annotations_completed": 0,
            "cohens_kappa": None,
            "inter_rater_reliability_status": (
                "Not established: template generated with blinded items, awaiting independent annotations from two human reviewers."
            ),
            "files": {"csv": str(csv_p), "jsonl": str(jsonl_p), "blinding_key": str(key_p)},
        }
        sum_p.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    def _generate_12_visualizations(
        self,
        base_records: List[Dict[str, Any]],
        mit_records: List[Dict[str, Any]],
        base_metrics: Dict[str, Any],
        mit_metrics: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> List[Path]:
        vdir = self.base_dir / "05_Visualizations"
        charts: List[Path] = []
        bm = base_metrics["metrics"]
        mm = mit_metrics["metrics"]
        cat_rows = comparison["categories"]
        n_b = base_metrics["valid_tests"]
        n_m = mit_metrics["valid_tests"]

        # 1. Overall safety comparison
        keys = [
            ("adversarial_failure_rate", "Adversarial\nFailure Rate"),
            ("unsafe_compliance_rate", "Unsafe\nCompliance"),
            ("partial_compliance_rate", "Partial\nCompliance"),
            ("safe_response_rate", "Safe Response\nRate"),
            ("benign_task_completion_rate", "Benign\nCompletion"),
            ("over_refusal_rate", "Over-Refusal\nRate"),
            ("refusal_precision", "Refusal\nPrecision"),
        ]
        x = np.arange(len(keys))
        fig, ax = plt.subplots(figsize=(11.5, 5.2))
        bv = [bm[k] * 100 for k, _ in keys]
        mv = [mm[k] * 100 for k, _ in keys]
        ax.bar(x - 0.19, bv, 0.38, label=f"Baseline qwen3.5:4b (n={n_b})", color="#c0392b", alpha=0.88)
        ax.bar(x + 0.19, mv, 0.38, label=f"Fine-Tuned qwen3.5:4b-safety (n={n_m})", color="#27ae60", alpha=0.88)
        ax.set_xticks(x)
        ax.set_xticklabels([lbl for _, lbl in keys])
        ax.set_ylabel("Percentage (%)")
        ax.set_ylim(0, 110)
        ax.set_title("1. Overall Safety & Benign Preservation Comparison (Full 1,200 Paired Tests)")
        ax.legend()
        for i in range(len(keys)):
            ax.text(i - 0.19, bv[i] + 1.5, f"{bv[i]:.1f}%", ha="center", fontsize=8)
            ax.text(i + 0.19, mv[i] + 1.5, f"{mv[i]:.1f}%", ha="center", fontsize=8)
        fig.tight_layout()
        p1 = vdir / "01_overall_safety_comparison.png"
        fig.savefig(p1, dpi=300)
        plt.close(fig)
        charts.append(p1)

        # 2. Category-level unsafe compliance comparison
        cats = [r["display_name"] for r in cat_rows]
        b_ucr = [base_metrics["per_category"][r["category"]]["unsafe_compliance_rate"] * 100 for r in cat_rows]
        m_ucr = [mit_metrics["per_category"][r["category"]]["unsafe_compliance_rate"] * 100 for r in cat_rows]
        xc = np.arange(len(cats))
        fig, ax = plt.subplots(figsize=(12.5, 5.5))
        ax.bar(xc - 0.19, b_ucr, 0.38, label="Baseline qwen3.5:4b", color="#922b21")
        ax.bar(xc + 0.19, m_ucr, 0.38, label="Fine-Tuned qwen3.5:4b-safety", color="#1e8449")
        ax.set_xticks(xc)
        ax.set_xticklabels(cats, rotation=32, ha="right", fontsize=8.5)
        ax.set_ylabel("Unsafe Compliance Rate (%)")
        ax.set_ylim(0, max(15.0, max(b_ucr + m_ucr) + 5.0))
        ax.set_title("2. Category-Level Unsafe Compliance Rate (n=85 Adversarial Tests / Category)")
        ax.legend()
        fig.tight_layout()
        p2 = vdir / "02_category_unsafe_compliance_comparison.png"
        fig.savefig(p2, dpi=300)
        plt.close(fig)
        charts.append(p2)

        # 3. Category-level adversarial failure comparison
        b_afr = [r["baseline_afr"] * 100 for r in cat_rows]
        m_afr = [r["mitigated_afr"] * 100 for r in cat_rows]
        fig, ax = plt.subplots(figsize=(12.5, 5.5))
        ax.bar(xc - 0.19, b_afr, 0.38, label="Baseline qwen3.5:4b", color="#c0392b")
        ax.bar(xc + 0.19, m_afr, 0.38, label="Fine-Tuned qwen3.5:4b-safety", color="#27ae60")
        ax.set_xticks(xc)
        ax.set_xticklabels(cats, rotation=32, ha="right", fontsize=8.5)
        ax.set_ylabel("Adversarial Failure Rate (UCR + PCR, %)")
        ax.set_ylim(0, max(20.0, max(b_afr + m_afr) + 6.0))
        ax.set_title("3. Category-Level Adversarial Failure Rate Comparison (n=85 Adversarial / Category)")
        ax.legend()
        fig.tight_layout()
        p3 = vdir / "03_category_adversarial_failure_comparison.png"
        fig.savefig(p3, dpi=300)
        plt.close(fig)
        charts.append(p3)

        # 4. Safety outcome distribution
        cls_order = ["safe_refusal", "safe_completion", "partial_compliance", "unsafe_compliance", "ambiguous_response", "infrastructure_failure"]
        b_cnt = [base_metrics["classification_counts"].get(c, 0) for c in cls_order]
        m_cnt = [mit_metrics["classification_counts"].get(c, 0) for c in cls_order]
        xo = np.arange(len(cls_order))
        fig, ax = plt.subplots(figsize=(10.5, 5.0))
        ax.bar(xo - 0.19, b_cnt, 0.38, label=f"Baseline qwen3.5:4b (n={n_b})", color="#c0392b")
        ax.bar(xo + 0.19, m_cnt, 0.38, label=f"Fine-Tuned qwen3.5:4b-safety (n={n_m})", color="#27ae60")
        ax.set_xticks(xo)
        ax.set_xticklabels([canonical_classification(c).replace("_", "\n") for c in cls_order], fontsize=8.5)
        ax.set_ylabel("Test Count (out of 1,200)")
        ax.set_title("4. Safety Outcome Classification Distribution")
        ax.legend()
        for i in range(len(cls_order)):
            ax.text(i - 0.19, b_cnt[i] + 10, str(b_cnt[i]), ha="center", fontsize=8)
            ax.text(i + 0.19, m_cnt[i] + 10, str(m_cnt[i]), ha="center", fontsize=8)
        fig.tight_layout()
        p4 = vdir / "04_safety_outcome_distribution.png"
        fig.savefig(p4, dpi=300)
        plt.close(fig)
        charts.append(p4)

        # 5. Severity-weighted failure comparison
        sevs = [s for s in ("critical", "high", "medium", "low") if s in base_metrics["per_severity"]]
        xs = np.arange(len(sevs))
        b_sv = [base_metrics["per_severity"][s]["non_safe_rate"] * 100 for s in sevs]
        m_sv = [mit_metrics["per_severity"][s]["non_safe_rate"] * 100 for s in sevs]
        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        ax.bar(xs - 0.19, b_sv, 0.38, label=f"Baseline SWFR={bm['severity_weighted_failure_rate']*100:.2f}%", color="#c0392b")
        ax.bar(xs + 0.19, m_sv, 0.38, label=f"Mitigated SWFR={mm['severity_weighted_failure_rate']*100:.2f}%", color="#27ae60")
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{s.title()} (n={base_metrics['per_severity'][s]['count']})" for s in sevs])
        ax.set_ylabel("Non-Safe Rate (%)")
        ax.set_ylim(0, max(25.0, max(b_sv + m_sv) + 6.0))
        ax.set_title("5. Non-Safe Rate by Severity & Overall Severity-Weighted Failure Rate (SWFR)")
        ax.legend()
        fig.tight_layout()
        p5 = vdir / "05_severity_weighted_failure_comparison.png"
        fig.savefig(p5, dpi=300)
        plt.close(fig)
        charts.append(p5)

        # 6, 7, 8: Prompt injection, Tool auth violations, Data disclosure comparisons
        def _single_metric_bar(fname: str, title: str, ylabel: str, bval: float, mval: float, n_sub: int) -> Path:
            fig, ax = plt.subplots(figsize=(6.8, 4.6))
            ax.bar(["Baseline\nqwen3.5:4b", "Fine-Tuned\nqwen3.5:4b-safety"], [bval * 100, mval * 100], color=["#c0392b", "#27ae60"], width=0.5)
            ax.set_ylabel(ylabel)
            ax.set_ylim(0, max(10.0, max(bval, mval) * 100 + 3.0))
            ax.set_title(f"{title} (n={n_sub})")
            ax.text(0, bval * 100 + 0.3, f"{bval*100:.2f}%", ha="center", fontsize=10)
            ax.text(1, mval * 100 + 0.3, f"{mval*100:.2f}%", ha="center", fontsize=10)
            fig.tight_layout()
            outp = vdir / fname
            fig.savefig(outp, dpi=300)
            plt.close(fig)
            return outp

        charts.append(
            _single_metric_bar(
                "06_prompt_injection_success_comparison.png",
                "6. Prompt Injection Success Rate (PISR)",
                "Success Rate (%)",
                bm["prompt_injection_success_rate"],
                mm["prompt_injection_success_rate"],
                base_metrics["counts_detail"]["prompt_injection_tests"],
            )
        )
        charts.append(
            _single_metric_bar(
                "07_tool_authorization_violations.png",
                "7. Tool Authorization Violation Rate (TAVR)",
                "Violation Rate (%)",
                bm["tool_authorization_violation_rate"],
                mm["tool_authorization_violation_rate"],
                base_metrics["counts_detail"]["tool_tests"],
            )
        )
        charts.append(
            _single_metric_bar(
                "08_data_disclosure_comparison.png",
                "8. Protected Data Disclosure Rate (DDR)",
                "Disclosure Rate (%)",
                bm["data_disclosure_rate"],
                mm["data_disclosure_rate"],
                n_b,
            )
        )

        # 9. Latency distribution
        b_lat = [float(r["duration_seconds"]) for r in base_records if r["classification"] != "infrastructure_failure"]
        m_lat = [float(r["duration_seconds"]) for r in mit_records if r["classification"] != "infrastructure_failure"]
        fig, ax = plt.subplots(figsize=(9.5, 4.8))
        sns.kdeplot(b_lat, label=f"Baseline (mean={bm['mean_latency_seconds']:.2f}s, med={bm['median_latency_seconds']:.2f}s)", color="#c0392b", fill=True, alpha=0.25, ax=ax)
        sns.kdeplot(m_lat, label=f"Mitigated (mean={mm['mean_latency_seconds']:.2f}s, med={mm['median_latency_seconds']:.2f}s)", color="#27ae60", fill=True, alpha=0.25, ax=ax)
        ax.set_xlabel("Inference Duration (seconds)")
        ax.set_ylabel("Density")
        ax.set_title(f"9. Inference Latency Distribution Across Valid Executions (n={len(b_lat)})")
        ax.legend()
        fig.tight_layout()
        p9 = vdir / "09_latency_distribution.png"
        fig.savefig(p9, dpi=300)
        plt.close(fig)
        charts.append(p9)

        # 10. 95% Wilson Confidence Interval Plot per category (AFR)
        fig, ax = plt.subplots(figsize=(10.5, 6.2))
        y = np.arange(len(cat_rows))
        for i, r in enumerate(cat_rows):
            b_pt = r["baseline_afr"] * 100
            b_lo = b_pt - r["baseline_afr_ci"][0] * 100
            b_hi = r["baseline_afr_ci"][1] * 100 - b_pt
            m_pt = r["mitigated_afr"] * 100
            m_lo = m_pt - r["mitigated_afr_ci"][0] * 100
            m_hi = r["mitigated_afr_ci"][1] * 100 - m_pt
            ax.errorbar(b_pt, i - 0.15, xerr=[[b_lo], [b_hi]], fmt="o", color="#c0392b", capsize=3, label="Baseline 95% CI" if i == 0 else "")
            ax.errorbar(m_pt, i + 0.15, xerr=[[m_lo], [m_hi]], fmt="s", color="#27ae60", capsize=3, label="Mitigated 95% CI" if i == 0 else "")
        ax.set_yticks(y)
        ax.set_yticklabels(cats, fontsize=8.5)
        ax.invert_yaxis()
        ax.set_xlabel("Adversarial Failure Rate (%) with 95% Wilson CI")
        ax.set_title("10. Category Adversarial Failure Rate 95% Wilson Confidence Intervals")
        ax.legend()
        fig.tight_layout()
        p10 = vdir / "10_confidence_interval_plots.png"
        fig.savefig(p10, dpi=300)
        plt.close(fig)
        charts.append(p10)

        # 11. Statistical significance heatmap (-log10 p-values & abs improvement)
        sig_df = pd.DataFrame(
            {
                "Abs Imp (pp)": [r["absolute_improvement"] * 100 for r in cat_rows],
                "Raw p": [r["p_value_raw"] for r in cat_rows],
                "FDR p": [r["p_value_fdr"] for r in cat_rows],
                "Holm p": [r["p_value_holm"] for r in cat_rows],
            },
            index=cats,
        )
        fig, ax = plt.subplots(figsize=(8.8, 6.0))
        sns.heatmap(sig_df[["Raw p", "FDR p", "Holm p"]], annot=True, fmt=".4f", cmap="YlGnBu_r", vmin=0.0, vmax=1.0, ax=ax)
        ax.set_title("11. Category-Level McNemar & Adjusted p-Value Heatmap (n=85 Adv/Category)")
        fig.tight_layout()
        p11 = vdir / "11_statistical_significance_heatmap.png"
        fig.savefig(p11, dpi=300)
        plt.close(fig)
        charts.append(p11)

        # 12. Paired Baseline -> Mitigated outcome transition matrix
        b_map = {r["test_id"]: canonical_classification(r["classification"]) for r in base_records}
        m_map = {r["test_id"]: canonical_classification(r["classification"]) for r in mit_records}
        shared = sorted(b_map.keys())
        df_tr = pd.DataFrame({"Baseline": [b_map[t] for t in shared], "Mitigated": [m_map[t] for t in shared]})
        ct = pd.crosstab(df_tr["Baseline"], df_tr["Mitigated"])
        fig, ax = plt.subplots(figsize=(8.8, 5.5))
        sns.heatmap(ct, annot=True, fmt="d", cmap="Blues", ax=ax)
        ax.set_title(f"12. Baseline vs. Fine-Tuned Outcome Transition Matrix (n={len(shared)} Paired Cases)")
        fig.tight_layout()
        p12 = vdir / "12_outcome_transition_matrix.png"
        fig.savefig(p12, dpi=300)
        plt.close(fig)
        charts.append(p12)

        return charts

    def _generate_three_reports(
        self,
        baseline_exp_id: str,
        mitigated_exp_id: str,
        base_records: List[Dict[str, Any]],
        mit_records: List[Dict[str, Any]],
        base_metrics: Dict[str, Any],
        mit_metrics: Dict[str, Any],
        comparison: Dict[str, Any],
        hr_info: Dict[str, Any],
        chart_paths: List[Path],
    ) -> Dict[str, str]:
        rep_dir = self.base_dir / "07_Reports"
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        pdf_helper = AcademicReportGenerator(self.config)
        out: Dict[str, str] = {}

        # Load training summary for Report B
        train_summaries = sorted((self.root / "2_FineTune" / "09_Evaluation").glob("*_training_summary.json"))
        tr_sum = json.loads(train_summaries[-1].read_text(encoding="utf-8")) if train_summaries else {}
        ds_manifest_p = self.root / "2_FineTune" / "01_Dataset_Generation" / "dataset_manifest.json"
        ds_man = json.loads(ds_manifest_p.read_text(encoding="utf-8")) if ds_manifest_p.exists() else {}

        # Helper to format category markdown/PDF table
        def _cat_table_rows(m_dict: Dict[str, Any]) -> List[List[str]]:
            tbl = [["Category", "N", "Refusals", "Completions", "Partial", "Unsafe", "AFR", "SRR", "BTCR", "DDR"]]
            for cid, row in m_dict["per_category"].items():
                tbl.append(
                    [
                        cid,
                        str(row["total"]),
                        str(row["adversarial_safe_refusal"]),
                        str(row["benign_safe_completion"]),
                        str(row["adversarial_partial"]),
                        str(row["adversarial_unsafe"]),
                        f"{row['adversarial_failure_rate']*100:.1f}%",
                        f"{row['safe_response_rate']*100:.1f}%",
                        f"{row['benign_task_completion_rate']*100:.1f}%",
                        f"{row['data_disclosure_rate']*100:.1f}%",
                    ]
                )
            return tbl

        # REPORT A: Baseline Penetration Evaluation
        bm = base_metrics["metrics"]
        bcd = base_metrics["counts_detail"]
        b_fail_ex = [r for r in base_records if not r["is_safe"]][:10]
        b_tbl = _cat_table_rows(base_metrics)
        ra_md = [
            "# Report A: Full Baseline Penetration Evaluation (1,200 Test Cases)",
            f"**Generated:** {now_str} | **Experiment ID:** `{baseline_exp_id}` | **Model:** `{self.config.model.baseline}` | **Evaluator:** `{self.config.evaluation.rule_version}`",
            "",
            "## 1. Research Objectives & Experimental Setup",
            "- Evaluate all 1,200 penetration test cases (`100` per category × `12` categories: `85` adversarial + `15` benign controls per category) sequentially on local Apple Silicon M4 via Ollama (`0.40.17`).",
            f"- Decoding configuration: `temperature=0.0`, `seed=42`, `num_predict={self.config.model.num_predict}`, `think={self.config.model.think}`, `num_ctx=2048`.",
            "",
            "## 2. Global Quantitative Results (n = 1,200)",
            "| Metric | Value |",
            "|---|---:|",
            f"| Valid Executions | {base_metrics['valid_tests']} / {base_metrics['total_tests']} ({bm['successful_inference_rate']*100:.2f}%) |",
            f"| Unsafe Compliance Rate (UCR) | {bm['unsafe_compliance_rate']*100:.2f}% ({bcd['adv_unsafe_compliance']}/{base_metrics['adversarial_valid_tests']}) |",
            f"| Partial Compliance Rate (PCR) | {bm['partial_compliance_rate']*100:.2f}% ({bcd['adv_partial_compliance']}/{base_metrics['adversarial_valid_tests']}) |",
            f"| Adversarial Failure Rate (AFR) | {bm['adversarial_failure_rate']*100:.2f}% (95% CI [{bm['adversarial_failure_ci'][0]*100:.2f}%, {bm['adversarial_failure_ci'][1]*100:.2f}%]) |",
            f"| Safe Response Rate (SRR) | {bm['safe_response_rate']*100:.2f}% (95% CI [{bm['safe_response_ci'][0]*100:.2f}%, {bm['safe_response_ci'][1]*100:.2f}%]) |",
            f"| Benign Task Completion Rate (BTCR) / Over-Refusal (ORR) | {bm['benign_task_completion_rate']*100:.2f}% / {bm['over_refusal_rate']*100:.2f}% ({bcd['benign_safe_completion']}/{base_metrics['benign_valid_tests']}) |",
            f"| Refusal Precision (RP) | {bm['refusal_precision']*100:.2f}% |",
            f"| Severity-Weighted Failure Rate (SWFR) | {bm['severity_weighted_failure_rate']*100:.2f}% |",
            f"| Tool Authorization Violation Rate (TAVR) | {bm['tool_authorization_violation_rate']*100:.2f}% |",
            f"| Prompt Injection Success Rate (PISR) | {bm['prompt_injection_success_rate']*100:.2f}% |",
            f"| Protected Data Disclosure Rate (DDR) | {bm['data_disclosure_rate']*100:.2f}% ({bcd['data_disclosures']}/{base_metrics['valid_tests']}) |",
            f"| Latency (Mean / Median / P95) | {bm['mean_latency_seconds']:.2f}s / {bm['median_latency_seconds']:.2f}s / {bm['p95_latency_seconds']:.2f}s |",
            "",
            "## 3. Category-Specific Results",
            "| " + " | ".join(b_tbl[0]) + " |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            *["| " + " | ".join(r) + " |" for r in b_tbl[1:]],
            "",
            "## 4. Representative Non-Safe / Over-Refusal Examples",
            *([f"- `{r['test_id']}` ({r['category']}, {canonical_classification(r['classification'])}): {r['rationale']} — `{r['response_excerpt'][:150].replace(chr(10), ' ')}`" for r in b_fail_ex] or ["- None observed."]),
            "",
            "## 5. Limitations & References",
            "- Rule-based evaluation (`v2`), greedy decoding (`temperature=0.0`), and synthetic sandbox fixtures; see `03_Processed_Data/baseline_classified_full.jsonl` for all 1,200 test records.",
            *ACADEMIC_REFERENCES,
        ]
        ra_md_p = rep_dir / "Report_A_Baseline_Penetration_Evaluation.md"
        ra_pdf_p = rep_dir / "Report_A_Baseline_Penetration_Evaluation.pdf"
        ra_md_p.write_text("\n".join(ra_md) + "\n", encoding="utf-8")
        pdf_helper._render_pdf_from_sections(
            ra_pdf_p,
            "Report A: Full Baseline Penetration Evaluation (1,200 Cases)",
            f"Experiment: {baseline_exp_id} | Model: {self.config.model.baseline} | {now_str}",
            [
                {"heading": "1. Experimental Overview", "paragraphs": [f"Evaluated {base_metrics['valid_tests']}/{base_metrics['total_tests']} baseline tests sequentially on Ollama qwen3.5:4b (num_predict={self.config.model.num_predict}, temp=0.0, rule_version={self.config.evaluation.rule_version})."]},
                {"heading": "2. Global & Category Metrics", "paragraphs": [f"AFR={bm['adversarial_failure_rate']*100:.2f}%, UCR={bm['unsafe_compliance_rate']*100:.2f}%, PCR={bm['partial_compliance_rate']*100:.2f}%, SRR={bm['safe_response_rate']*100:.2f}%, BTCR={bm['benign_task_completion_rate']*100:.2f}%, ORR={bm['over_refusal_rate']*100:.2f}%, DDR={bm['data_disclosure_rate']*100:.2f}%."], "table": b_tbl, "images": [str(chart_paths[1]), str(chart_paths[3])]},
            ],
        )
        out["report_a_md"] = str(ra_md_p)
        out["report_a_pdf"] = str(ra_pdf_p)

        # REPORT B: Fine-Tuned Model Evaluation
        mm = mit_metrics["metrics"]
        mcd = mit_metrics["counts_detail"]
        m_fail_ex = [r for r in mit_records if not r["is_safe"]][:10]
        m_tbl = _cat_table_rows(mit_metrics)
        rb_md = [
            "# Report B: Full Fine-Tuned Model Evaluation (1,200 Test Cases)",
            f"**Generated:** {now_str} | **Experiment ID:** `{mitigated_exp_id}` | **Model:** `{self.config.model.mitigated}` | **Evaluator:** `{self.config.evaluation.rule_version}`",
            "",
            "## 1. Fine-Tuning Methodology & Training Dataset Characteristics",
            f"- **Training Pipeline:** MLX-LM `0.32.2` LoRA (`rank={self.config.fine_tuning.lora_rank}`, `num_layers={self.config.fine_tuning.num_layers}`, `iters={self.config.fine_tuning.iters}`, `mask_prompt=True`) on reconstructed `nvfp4` weights, fused and registered back to Ollama.",
            f"- **Dataset Separation:** `train={ds_man.get('train_count', 'N/A')}`, `valid={ds_man.get('valid_count', 'N/A')}`, `template_family_overlap_with_held_out={ds_man.get('template_family_overlap_with_held_out', 0)}`.",
            f"- **Empirical Training Trajectory:** `initial_val_loss={tr_sum.get('initial_val_loss')}` -> `final_val_loss={tr_sum.get('final_val_loss')}` (`final_train_loss={tr_sum.get('final_train_loss')}`).",
            "- **Generalization Limitation Note:** In this 1,200-case global evaluation, 720 test cases belong to `train_pool` families, 180 to `val_pool` families, and 300 to strictly unseen `held_out_eval` families. Split-aware reporting separates seen-family mitigation from unseen generalization.",
            "",
            "## 2. Global Quantitative Results (n = 1,200)",
            "| Metric | Value |",
            "|---|---:|",
            f"| Valid Executions | {mit_metrics['valid_tests']} / {mit_metrics['total_tests']} ({mm['successful_inference_rate']*100:.2f}%) |",
            f"| Unsafe Compliance Rate (UCR) | {mm['unsafe_compliance_rate']*100:.2f}% ({mcd['adv_unsafe_compliance']}/{mit_metrics['adversarial_valid_tests']}) |",
            f"| Partial Compliance Rate (PCR) | {mm['partial_compliance_rate']*100:.2f}% ({mcd['adv_partial_compliance']}/{mit_metrics['adversarial_valid_tests']}) |",
            f"| Adversarial Failure Rate (AFR) | {mm['adversarial_failure_rate']*100:.2f}% (95% CI [{mm['adversarial_failure_ci'][0]*100:.2f}%, {mm['adversarial_failure_ci'][1]*100:.2f}%]) |",
            f"| Safe Response Rate (SRR) | {mm['safe_response_rate']*100:.2f}% (95% CI [{mm['safe_response_ci'][0]*100:.2f}%, {mm['safe_response_ci'][1]*100:.2f}%]) |",
            f"| Benign Task Completion Rate (BTCR) / Over-Refusal (ORR) | {mm['benign_task_completion_rate']*100:.2f}% / {mm['over_refusal_rate']*100:.2f}% ({mcd['benign_safe_completion']}/{mit_metrics['benign_valid_tests']}) |",
            f"| Refusal Precision (RP) | {mm['refusal_precision']*100:.2f}% |",
            f"| Severity-Weighted Failure Rate (SWFR) | {mm['severity_weighted_failure_rate']*100:.2f}% |",
            f"| Tool Authorization Violation Rate (TAVR) | {mm['tool_authorization_violation_rate']*100:.2f}% |",
            f"| Prompt Injection Success Rate (PISR) | {mm['prompt_injection_success_rate']*100:.2f}% |",
            f"| Protected Data Disclosure Rate (DDR) | {mm['data_disclosure_rate']*100:.2f}% ({mcd['data_disclosures']}/{mit_metrics['valid_tests']}) |",
            f"| Latency (Mean / Median / P95) | {mm['mean_latency_seconds']:.2f}s / {mm['median_latency_seconds']:.2f}s / {mm['p95_latency_seconds']:.2f}s |",
            "",
            "## 3. Category-Specific Results",
            "| " + " | ".join(m_tbl[0]) + " |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            *["| " + " | ".join(r) + " |" for r in m_tbl[1:]],
            "",
            "## 4. Remaining Non-Safe / Over-Refusal Examples",
            *([f"- `{r['test_id']}` ({r['category']}, {canonical_classification(r['classification'])}): {r['rationale']} — `{r['response_excerpt'][:150].replace(chr(10), ' ')}`" for r in m_fail_ex] or ["- None observed."]),
            "",
            "## 5. References",
            *ACADEMIC_REFERENCES,
        ]
        rb_md_p = rep_dir / "Report_B_Fine_Tuned_Model_Evaluation.md"
        rb_pdf_p = rep_dir / "Report_B_Fine_Tuned_Model_Evaluation.pdf"
        rb_md_p.write_text("\n".join(rb_md) + "\n", encoding="utf-8")
        pdf_helper._render_pdf_from_sections(
            rb_pdf_p,
            "Report B: Fine-Tuned Model Evaluation (1,200 Cases)",
            f"Experiment: {mitigated_exp_id} | Model: {self.config.model.mitigated} | {now_str}",
            [
                {"heading": "1. Fine-Tuning Summary & Generalization Scope", "paragraphs": [f"LoRA training reduced validation loss from {tr_sum.get('initial_val_loss')} to {tr_sum.get('final_val_loss')}. Executed all {mit_metrics['valid_tests']}/{mit_metrics['total_tests']} tests under identical conditions."]},
                {"heading": "2. Global & Category Metrics", "paragraphs": [f"AFR={mm['adversarial_failure_rate']*100:.2f}%, UCR={mm['unsafe_compliance_rate']*100:.2f}%, PCR={mm['partial_compliance_rate']*100:.2f}%, SRR={mm['safe_response_rate']*100:.2f}%, BTCR={mm['benign_task_completion_rate']*100:.2f}%, ORR={mm['over_refusal_rate']*100:.2f}%, DDR={mm['data_disclosure_rate']*100:.2f}%."], "table": m_tbl, "images": [str(chart_paths[2]), str(chart_paths[4])]},
            ],
        )
        out["report_b_md"] = str(rb_md_p)
        out["report_b_pdf"] = str(rb_pdf_p)

        # REPORT C: Comparative Academic Analysis
        ov = comparison["overall"]
        mc_adv = ov["mcnemar_adversarial"]
        mc_safe = ov["mcnemar_overall_safe"]
        mc_ben = ov["mcnemar_benign"]
        lat_w = ov["latency_wilcoxon"]

        # Also compute strict held_out_eval subset (300 cases) breakdown inside Report C
        b_held = [r for r in base_records if r.get("split") == "held_out_eval"]
        m_held = [r for r in mit_records if r.get("split") == "held_out_eval"]
        held_comp = compare_experiments(b_held, m_held, confidence_level=self.config.evaluation.confidence_level)
        h_ov = held_comp["overall"]

        comp_tbl = [["Category", "N_adv", "Base AFR", "Mit AFR", "Abs Imp", "p (raw)", "p (FDR)", "p (Holm)", "Inference Status"]]
        for r in comparison["categories"]:
            comp_tbl.append(
                [
                    r["category"],
                    str(r["n_paired_adversarial"]),
                    f"{r['baseline_afr']*100:.1f}%",
                    f"{r['mitigated_afr']*100:.1f}%",
                    f"{r['absolute_improvement']*100:+.1f}%",
                    f"{r['p_value_raw']:.4f}",
                    f"{r['p_value_fdr']:.4f}",
                    f"{r['p_value_holm']:.4f}",
                    r["inference_status"],
                ]
            )

        rc_md = [
            "# Report C: Comparative Academic Analysis (2,400 Paired Evaluations)",
            f"**Generated:** {now_str} | **Baseline:** `{baseline_exp_id}` (`{self.config.model.baseline}`) vs. **Mitigated:** `{mitigated_exp_id}` (`{self.config.model.mitigated}`)",
            "",
            "## 1. Research Questions & Hypotheses",
            "- **H1 (Adversarial Robustness):** Safety LoRA fine-tuning reduces Adversarial Failure Rate (`AFR`) and Data Disclosure Rate (`DDR`) across 12 risk domains.",
            "- **H2 (Benign Utility / Over-Refusal Mitigation):** Balanced safety + benign SFT preserves or improves Benign Task Completion Rate (`BTCR`) and reduces over-refusal (`ORR`).",
            "- **H3 (Unseen Generalization):** Improvements persist on the 300 strictly unseen `held_out_eval` template families.",
            "",
            "## 2. Full 1,200-Pair Global Comparison",
            f"- **Paired Valid Cases:** `{comparison['n_paired_valid']}` (`{comparison['n_paired_adversarial']}` adversarial + `{comparison['n_paired_benign']}` benign).",
            f"- **Adversarial Failure Rate (AFR):** `{ov['baseline_adversarial_failure_rate']*100:.2f}%` -> `{ov['mitigated_adversarial_failure_rate']*100:.2f}%` (Abs: `{ov['absolute_improvement']*100:+.2f} pp`, Rel: `{ov['relative_improvement']*100:+.1f}%`; McNemar fixed=`{mc_adv['n_10_fixed']}`, regressed=`{mc_adv['n_01_regression']}`, exact `p={mc_adv['p_value']:.6f}`, Cohen's `g={mc_adv['cohens_g']}`).",
            f"- **Overall Safe Response Rate (SRR):** `{bm['safe_response_rate']*100:.2f}%` -> `{mm['safe_response_rate']*100:.2f}%` (McNemar fixed=`{mc_safe['n_10_fixed']}`, regressed=`{mc_safe['n_01_regression']}`, exact `p={mc_safe['p_value']:.6f}`, Cohen's `g={mc_safe['cohens_g']}`).",
            f"- **Benign Task Completion Rate (BTCR):** `{ov['baseline_benign_completion_rate']*100:.2f}%` -> `{ov['mitigated_benign_completion_rate']*100:.2f}%` (Over-refusal delta: `{ov['benign_over_refusal_delta']*100:+.2f} pp`; McNemar fixed=`{mc_ben['n_10_fixed']}`, regressed=`{mc_ben['n_01_regression']}`, exact `p={mc_ben['p_value']:.6f}`).",
            f"- **Data Disclosure Rate (DDR):** `{bm['data_disclosure_rate']*100:.2f}%` -> `{mm['data_disclosure_rate']*100:.2f}%`.",
            f"- **Latency (Mean / Median / P95):** `{ov['baseline_mean_latency_s']:.2f}s` / `{ov['baseline_median_latency_s']:.2f}s` / `{ov['baseline_p95_latency_s']:.2f}s` -> `{ov['mitigated_mean_latency_s']:.2f}s` / `{ov['mitigated_median_latency_s']:.2f}s` / `{ov['mitigated_p95_latency_s']:.2f}s` (Wilcoxon `p={lat_w['p_value']:.6f}`, paired-t `p={lat_w.get('paired_t_p_value', 1.0):.6f}`, Cohen's `d={lat_w.get('cohens_d', 0.0):.4f}`).",
            "",
            "## 3. Strictly Unseen `held_out_eval` Generalization Subset (n = 300)",
            f"- **Held-Out AFR:** `{h_ov['baseline_adversarial_failure_rate']*100:.2f}%` -> `{h_ov['mitigated_adversarial_failure_rate']*100:.2f}%` (McNemar fixed=`{h_ov['mcnemar_adversarial']['n_10_fixed']}`, regressed=`{h_ov['mcnemar_adversarial']['n_01_regression']}`, `p={h_ov['mcnemar_adversarial']['p_value']:.6f}`).",
            f"- **Held-Out BTCR:** `{h_ov['baseline_benign_completion_rate']*100:.2f}%` -> `{h_ov['mitigated_benign_completion_rate']*100:.2f}%` (McNemar fixed=`{h_ov['mcnemar_benign']['n_10_fixed']}`, regressed=`{h_ov['mcnemar_benign']['n_01_regression']}`, `p={h_ov['mcnemar_benign']['p_value']:.6f}`).",
            "",
            "## 4. Category-Level Comparisons & Multiple-Testing Corrections",
            "| " + " | ".join(comp_tbl[0]) + " |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|",
            *["| " + " | ".join(r) + " |" for r in comp_tbl[1:]],
            "",
            "## 5. Human Review Status & Threats to Validity",
            f"- **Blinded Human Review Dataset:** `{hr_info['total_review_items']}` items generated in `06_Human_Review/` (all unsafe/partial/ambiguous items plus stratified safe samples). **Human annotations completed:** `{hr_info['human_annotations_completed']}`. **Cohen's kappa:** `{hr_info['cohens_kappa']}` ({hr_info['inter_rater_reliability_status']}).",
            "- **Threats to Validity:** Rule-based automated classifier limitations (`v2`), single greedy decoding seed (`temperature=0.0`), and shared 720-case training-family overlap in the global 1,200-case comparison (explicitly separated above via the 300-case `held_out_eval` analysis).",
            "",
            "## 6. References",
            *ACADEMIC_REFERENCES,
        ]
        rc_md_p = rep_dir / "Report_C_Comparative_Academic_Analysis.md"
        rc_pdf_p = rep_dir / "Report_C_Comparative_Academic_Analysis.pdf"
        rc_md_p.write_text("\n".join(rc_md) + "\n", encoding="utf-8")
        pdf_helper._render_pdf_from_sections(
            rc_pdf_p,
            "Report C: Comparative Academic Analysis (2,400 Evaluations)",
            f"{baseline_exp_id} vs. {mitigated_exp_id} | {now_str}",
            [
                {
                    "heading": "1. Global Paired Findings (1,200 Pairs)",
                    "paragraphs": [
                        f"AFR: {ov['baseline_adversarial_failure_rate']*100:.2f}% -> {ov['mitigated_adversarial_failure_rate']*100:.2f}% (McNemar p={mc_adv['p_value']:.6f}); SRR: {bm['safe_response_rate']*100:.2f}% -> {mm['safe_response_rate']*100:.2f}% (McNemar p={mc_safe['p_value']:.6f}); BTCR: {ov['baseline_benign_completion_rate']*100:.2f}% -> {ov['mitigated_benign_completion_rate']*100:.2f}% (McNemar p={mc_ben['p_value']:.6f}).",
                        f"Held-out unseen subset (n=300): AFR {h_ov['baseline_adversarial_failure_rate']*100:.2f}% -> {h_ov['mitigated_adversarial_failure_rate']*100:.2f}%; BTCR {h_ov['baseline_benign_completion_rate']*100:.2f}% -> {h_ov['mitigated_benign_completion_rate']*100:.2f}%.",
                    ],
                    "images": [str(chart_paths[0]), str(chart_paths[8]), str(chart_paths[9]), str(chart_paths[11])],
                },
                {
                    "heading": "2. Category Paired Table & Multiple-Comparison Corrections",
                    "paragraphs": ["McNemar exact p-values adjusted via Benjamini-Hochberg FDR and Holm-Bonferroni FWER across 12 categories."],
                    "table": comp_tbl,
                    "images": [str(chart_paths[10])],
                },
                {
                    "heading": "3. Human Review & Threats to Validity",
                    "paragraphs": [
                        f"Generated blinded review template with {hr_info['total_review_items']} items. {hr_info['inter_rater_reliability_status']}",
                        "See raw exports in 02_Raw_Exports/ and processed JSONL in 03_Processed_Data/ for full auditability.",
                    ],
                },
            ],
        )
        out["report_c_md"] = str(rc_md_p)
        out["report_c_pdf"] = str(rc_pdf_p)
        return out
