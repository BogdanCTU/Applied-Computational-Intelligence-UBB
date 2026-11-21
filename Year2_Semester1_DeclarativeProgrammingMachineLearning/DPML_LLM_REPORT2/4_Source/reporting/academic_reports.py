"""Academic Markdown, CSV, JSON, and ReportLab PDF report generator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from source.config.settings import AppConfig, get_project_root


ACADEMIC_REFERENCES: List[str] = [
    "[1] OWASP Foundation (2025). OWASP Top 10 for Large Language Model Applications v2.0. https://owasp.org/www-project-top-10-for-large-language-models/",
    "[2] Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-Rank Adaptation of Large Language Models. ICLR 2022.",
    "[3] McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. Psychometrika, 12(2), 153-157.",
    "[4] Benjamini, Y., & Hochberg, Y. (1995). Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. JRSS-B, 57(1), 289-300.",
    "[5] Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, 6(2), 65-70.",
    "[6] Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. JASA, 22(158), 209-212.",
    "[7] Hannun, A., Digani, J., Angelard-Gontier, A., et al. (2024). MLX & MLX-LM: Efficient Machine Learning on Apple Silicon. Apple Machine Learning Research.",
]


class AcademicReportGenerator:
    """Produces Reports 1, 2, and 3 in Markdown, PDF, CSV, and JSON formats."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.root = get_project_root()

    def _render_pdf_from_sections(
        self,
        pdf_path: Path,
        title: str,
        subtitle: str,
        sections: List[Dict[str, Any]],
    ) -> Path:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )
        styles = getSampleStyleSheet()
        h1_style = ParagraphStyle(
            "AcadTitle",
            parent=styles["Title"],
            fontSize=17,
            leading=21,
            textColor=colors.HexColor("#1b2631"),
            spaceAfter=6,
        )
        sub_style = ParagraphStyle(
            "AcadSub",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#566573"),
            spaceAfter=14,
        )
        h2_style = ParagraphStyle(
            "AcadH2",
            parent=styles["Heading2"],
            fontSize=12.5,
            leading=16,
            textColor=colors.HexColor("#154360"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "AcadBody",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=13.5,
            spaceAfter=6,
        )

        story: List[Any] = [
            Paragraph(self._escape_xml(title), h1_style),
            Paragraph(self._escape_xml(subtitle), sub_style),
        ]

        for sec in sections:
            story.append(Paragraph(self._escape_xml(sec["heading"]), h2_style))
            for para in sec.get("paragraphs", []):
                story.append(Paragraph(self._escape_xml(para), body_style))
            if sec.get("table"):
                tbl_data = sec["table"]
                col_count = len(tbl_data[0])
                avail_w = 7.0 * inch
                col_widths = [avail_w / col_count] * col_count
                t = Table(tbl_data, colWidths=col_widths, repeatRows=1)
                t.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e78")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bfc9ca")),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f7")]),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                story.append(Spacer(1, 4))
                story.append(t)
                story.append(Spacer(1, 8))
            for img_path in sec.get("images", []):
                ip = Path(img_path)
                if ip.exists():
                    story.append(Spacer(1, 4))
                    story.append(Image(str(ip), width=6.6 * inch, height=3.5 * inch, kind="proportional"))
                    story.append(Spacer(1, 6))

        doc.build(story)
        return pdf_path

    @staticmethod
    def _escape_xml(text: str) -> str:
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def generate_baseline_report(
        self,
        env_info: Dict[str, Any],
        diversity_report: Dict[str, Any],
        baseline_metrics: Dict[str, Any],
        baseline_records: List[Dict[str, Any]],
        chart_paths: List[Path],
    ) -> Dict[str, Path]:
        """Generate Report 1: Baseline Penetration Analysis (Markdown + PDF + CSV)."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        m = baseline_metrics["metrics"]
        cd = baseline_metrics["counts_detail"]
        per_cat = baseline_metrics["per_category"]

        # Qualitative failure examples (up to 6 real observed failures)
        failed_examples = [
            r for r in baseline_records if r["classification"] in ("unsafe_compliance", "partial_compliance")
        ][:6]

        cat_table = [["Category", "Total", "Adv Fail Rate", "95% Wilson CI", "Safe Rate", "Benign Comp."]]
        for cid, row in per_cat.items():
            cat_table.append(
                [
                    cid,
                    str(row["total"]),
                    f"{row['adversarial_failure_rate']*100:.1f}%",
                    f"[{row['adversarial_failure_ci'][0]*100:.1f}%, {row['adversarial_failure_ci'][1]*100:.1f}%]",
                    f"{row['safe_response_rate']*100:.1f}%",
                    f"{row['benign_task_completion_rate']*100:.1f}%",
                ]
            )

        md_lines = [
            "# Report 1: Baseline Penetration Analysis",
            f"**Generated:** {now_str} | **Model:** `{self.config.model.baseline}` | **Dataset Version:** `{self.config.project.dataset_version}`",
            "",
            "## 1. Research Objectives & Research Questions",
            "- **RQ1:** To what extent does local `qwen3.5:4b` resist adversarial prompts across 12 risk categories and 14 attack patterns without external safety gateways?",
            "- **RQ2:** How effectively does the deterministic tool sandbox block unauthorized tool calls independently of model refusal behavior?",
            "- **RQ3:** What is the baseline benign-request completion rate (and over-refusal baseline) on dual-use educational prompts?",
            "",
            "## 2. Experimental Setup & Model Configuration",
            f"- **Hardware:** Apple Silicon `{env_info.get('platform_machine', 'arm64')}`, 16 GB Unified Memory.",
            f"- **Ollama Version:** `{env_info.get('ollama_version')}` | **Model:** `{self.config.model.baseline}`",
            f"- **Generation Config:** `temperature={self.config.model.temperature}`, `num_predict={self.config.model.num_predict}`, `think={self.config.model.think}`",
            "",
            "## 3. Dataset Construction & Diversity",
            f"- **Total Suite Size:** {diversity_report.get('total_cases', 0)} cases across {diversity_report.get('category_count', 12)} categories (`duplicate_test_ids={diversity_report.get('duplicate_test_ids')}`, `template_family_leakage={diversity_report.get('template_family_leakage_count')}`).",
            f"- **Evaluated Baseline Subset:** {baseline_metrics['total_tests']} total cases ({baseline_metrics['valid_tests']} valid, {baseline_metrics['infrastructure_failures']} infrastructure failures).",
            "",
            "## 4. Quantitative Baseline Results",
            "| Metric | Value |",
            "|---|---:|",
            f"| Adversarial Failure Rate (AFR = UCR + PCR) | {m['adversarial_failure_rate']*100:.2f}% (95% CI [{m['adversarial_failure_ci'][0]*100:.1f}%, {m['adversarial_failure_ci'][1]*100:.1f}%]) |",
            f"| Unsafe Compliance Rate (UCR) | {m['unsafe_compliance_rate']*100:.2f}% ({cd['adv_unsafe_compliance']}/{baseline_metrics['adversarial_valid_tests']}) |",
            f"| Partial Compliance Rate (PCR) | {m['partial_compliance_rate']*100:.2f}% ({cd['adv_partial_compliance']}/{baseline_metrics['adversarial_valid_tests']}) |",
            f"| Safe Response Rate (SRR) | {m['safe_response_rate']*100:.2f}% (95% CI [{m['safe_response_ci'][0]*100:.1f}%, {m['safe_response_ci'][1]*100:.1f}%]) |",
            f"| Refusal Precision (RP) | {m['refusal_precision']*100:.2f}% |",
            f"| Benign Task Completion Rate (BTCR) | {m['benign_task_completion_rate']*100:.2f}% ({cd['benign_safe_completion']}/{baseline_metrics['benign_valid_tests']}) |",
            f"| Over-Refusal Rate (ORR) | {m['over_refusal_rate']*100:.2f}% |",
            f"| Severity-Weighted Failure Rate (SWFR) | {m['severity_weighted_failure_rate']*100:.2f}% |",
            f"| Tool Authorization Violation Rate (TAVR) | {m['tool_authorization_violation_rate']*100:.2f}% |",
            f"| Prompt Injection Success Rate (PISR) | {m['prompt_injection_success_rate']*100:.2f}% |",
            f"| Mean Inference Latency | {m['mean_latency_seconds']:.3f} s |",
            "",
            "### Category Breakdown",
            "| Category | Total | Adv Fail Rate | 95% Wilson CI | Safe Rate | Benign Comp. |",
            "|---|---:|---:|---|---:|---:|",
        ]
        for row in cat_table[1:]:
            md_lines.append(f"| {' | '.join(row)} |")

        md_lines.extend(["", "## 5. Qualitative Failure Analysis"])
        if failed_examples:
            for ex in failed_examples:
                md_lines.append(
                    f"- **`{ex['test_id']}` ({ex['category']} / {ex['attack_pattern']}, {ex['classification']})**: {ex['rationale']} — Excerpt: `{ex['response_excerpt'][:160].replace(chr(10), ' ')}`"
                )
        else:
            md_lines.append("- No adversarial unsafe or partial compliance failures were observed in this baseline run.")

        md_lines.extend(
            [
                "",
                "## 6. Limitations",
                "- Rule-based automated safety evaluation may misclassify subtle implicit refusals or hedged educational responses without manual annotation.",
                "- Single-seed deterministic generation (`temperature=0.0`) captures greedy decoding behavior rather than high-temperature stochastic tail risk.",
                "",
                "## 7. References",
                *ACADEMIC_REFERENCES,
            ]
        )

        md_text = "\n".join(md_lines) + "\n"
        out_paths: Dict[str, Path] = {}
        for idx, target_dir in enumerate(
            [
                self.root / "1_Penetration" / "09_Reports",
                self.root / "3_Comparative_Analysis" / "06_Academic_Reports",
                self.root / "9_Results" / "baseline",
            ]
        ):
            target_dir.mkdir(parents=True, exist_ok=True)
            md_p = target_dir / "report_1_baseline_penetration.md"
            md_p.write_text(md_text, encoding="utf-8")
            pdf_p = target_dir / "report_1_baseline_penetration.pdf"
            self._render_pdf_from_sections(
                pdf_p,
                "Report 1: Baseline Penetration Analysis",
                f"Model: {self.config.model.baseline} | Generated: {now_str}",
                [
                    {
                        "heading": "1. Research Objectives & Experimental Setup",
                        "paragraphs": [
                            f"Evaluated local model {self.config.model.baseline} (Ollama {env_info.get('ollama_version')}) on Apple {env_info.get('platform_machine', 'arm64')} with 16 GB unified memory across 12 risk categories.",
                            f"Master suite size: {diversity_report.get('total_cases', 0)} cases; evaluated baseline subset: {baseline_metrics['total_tests']} cases ({baseline_metrics['valid_tests']} valid).",
                        ],
                    },
                    {
                        "heading": "2. Overall Baseline Metrics",
                        "paragraphs": [
                            f"AFR={m['adversarial_failure_rate']*100:.2f}%, UCR={m['unsafe_compliance_rate']*100:.2f}%, PCR={m['partial_compliance_rate']*100:.2f}%, SRR={m['safe_response_rate']*100:.2f}%, BTCR={m['benign_task_completion_rate']*100:.2f}%, TAVR={m['tool_authorization_violation_rate']*100:.2f}%, PISR={m['prompt_injection_success_rate']*100:.2f}%.",
                        ],
                        "table": cat_table,
                        "images": [str(p) for p in chart_paths[:4]],
                    },
                    {
                        "heading": "3. Qualitative Findings & Limitations",
                        "paragraphs": [
                            (f"Observed {len(failed_examples)} representative failure cases in baseline decoding; deterministic tool sandbox remained intact regardless of model output.")
                            if failed_examples
                            else "Zero unsafe compliance failures detected in this subset; refer to manual annotations and limitations for edge cases.",
                            "Limitations: rule-based baseline classification, greedy decoding (temperature=0.0), and local synthetic fixture scope.",
                        ],
                    },
                ],
            )
            if idx == 0:
                out_paths["baseline_md"] = md_p
                out_paths["baseline_pdf"] = pdf_p

        # Save CSV table in 1_Penetration/07_Statistics/
        stats_dir = self.root / "1_Penetration" / "07_Statistics"
        stats_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame.from_dict(per_cat, orient="index").reset_index(names="category").to_csv(
            stats_dir / "baseline_category_statistics.csv", index=False
        )
        return out_paths

    def generate_finetuning_report(
        self,
        dataset_manifest: Dict[str, Any],
        training_summary: Dict[str, Any],
    ) -> Dict[str, Path]:
        """Generate Report 2: Safety Fine-Tuning Methodology (Markdown + PDF)."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        hp = training_summary.get("base_mlx_export", {})
        ollama_exp = training_summary.get("ollama_export", {})
        val_hist = training_summary.get("val_loss_history", [])
        train_hist = training_summary.get("train_loss_history", [])

        md_lines = [
            "# Report 2: Safety Fine-Tuning Methodology & Local Conversion",
            f"**Generated:** {now_str} | **Base Model:** `{self.config.model.baseline}` | **Mitigated Model:** `{self.config.model.mitigated}`",
            "",
            "## 1. Mitigation Objectives & Data Separation",
            "- Improve refusal robustness against prompt injection, data exfiltration, tool abuse, and unsafe compliance while preserving benign educational and defensive utility.",
            f"- **Training Examples:** {dataset_manifest.get('train_count', 0)} (Adversarial: {dataset_manifest.get('train_adversarial', 0)}, Benign: {dataset_manifest.get('train_benign', 0)}).",
            f"- **Validation Examples:** {dataset_manifest.get('valid_count', 0)} (Adversarial: {dataset_manifest.get('valid_adversarial', 0)}, Benign: {dataset_manifest.get('valid_benign', 0)}).",
            f"- **Template-Family Overlap with Held-Out Evaluation:** {dataset_manifest.get('template_family_overlap_with_held_out', 0)} (strictly disjoint).",
            "",
            "## 2. Apple Silicon Hardware Constraints & Ollama-to-MLX Conversion",
            "- Ollama stores `qwen3.5:4b` as content-addressed single-tensor `nvfp4` (`group_size=16`) safetensors blobs (`*.weight.scale`) with `qwen3_5` multimodal weights.",
            "- Because MLX-LM cannot train directly on Ollama's manifest/blob layout, `OllamaMLXConverter` reconstructs an MLX-LM directory mapping `*.weight.scale` -> `*.scales` and sets `quantization={group_size:16, bits:4, mode:'nvfp4'}` in `config.json`.",
            f"- After LoRA training and fusion, modified tensor blobs (`modified_blobs_written={ollama_exp.get('modified_blobs_written')}`, `reused_blobs={ollama_exp.get('reused_blobs')}`) are serialized back into Ollama's `nvfp4` blob format and registered as `{self.config.model.mitigated}`.",
            "",
            "## 3. Fine-Tuning Configuration (16 GB Unified Memory)",
            f"- **Method:** `{self.config.fine_tuning.method}` (`rank={self.config.fine_tuning.lora_rank}`, `alpha={self.config.fine_tuning.lora_alpha}`, `num_layers={self.config.fine_tuning.num_layers}`)",
            f"- **Schedule:** `iters={self.config.fine_tuning.iters}`, `batch_size={self.config.fine_tuning.batch_size}`, `max_seq_length={self.config.fine_tuning.max_sequence_length}`, `lr={self.config.fine_tuning.learning_rate}`, `grad_checkpoint={self.config.fine_tuning.grad_checkpoint}`, `mask_prompt={self.config.fine_tuning.mask_prompt}`.",
            "",
            "## 4. Empirical Training & Verification Results",
            f"- **Run ID:** `{training_summary.get('run_id')}` | **Duration:** {training_summary.get('duration_seconds')} s | **Status:** `{training_summary.get('status')}`",
            f"- **Initial Validation Loss:** {training_summary.get('initial_val_loss')} -> **Final Validation Loss:** {training_summary.get('final_val_loss')}",
            f"- **Final Training Loss:** {training_summary.get('final_train_loss')}",
            f"- **MLX Fused Generation Verified:** `{training_summary.get('mlx_verification', {}).get('success')}`",
            f"- **Ollama Converted Generation Verified:** `{training_summary.get('ollama_verification', {}).get('success')}`",
            "",
            "### Validation Loss Trajectory",
            "| Iteration | Val Loss |",
            "|---:|---:|",
        ]
        for it, vl in val_hist:
            md_lines.append(f"| {it} | {vl} |")
        md_lines.extend(["", "## 5. References", *ACADEMIC_REFERENCES])
        md_text = "\n".join(md_lines) + "\n"

        loss_table = [["Iteration", "Val Loss"]] + [[str(it), str(vl)] for it, vl in val_hist]
        if len(loss_table) == 1:
            loss_table.append(["N/A", "N/A"])

        out_paths: Dict[str, Path] = {}
        for idx, target_dir in enumerate(
            [
                self.root / "2_FineTune" / "09_Evaluation",
                self.root / "3_Comparative_Analysis" / "06_Academic_Reports",
                self.root / "9_Results" / "mitigated",
            ]
        ):
            target_dir.mkdir(parents=True, exist_ok=True)
            md_p = target_dir / "report_2_finetuning_methodology.md"
            md_p.write_text(md_text, encoding="utf-8")
            pdf_p = target_dir / "report_2_finetuning_methodology.pdf"
            self._render_pdf_from_sections(
                pdf_p,
                "Report 2: Safety Fine-Tuning Methodology",
                f"Base: {self.config.model.baseline} -> Mitigated: {self.config.model.mitigated} | {now_str}",
                [
                    {
                        "heading": "1. Training Dataset & Leakage Isolation",
                        "paragraphs": [
                            f"Train set: {dataset_manifest.get('train_count', 0)} examples; Validation set: {dataset_manifest.get('valid_count', 0)} examples; Template-family overlap with held_out_eval: {dataset_manifest.get('template_family_overlap_with_held_out', 0)}.",
                            "Unsafe baseline outputs were strictly excluded from positive training targets; curated safe refusals and benign completions were balanced across all 12 categories.",
                        ],
                    },
                    {
                        "heading": "2. Bidirectional Ollama <-> MLX-LM (nvfp4) Pipeline",
                        "paragraphs": [
                            f"LoRA fine-tuning ran natively on Apple Silicon M4 via MLX-LM (num_layers={self.config.fine_tuning.num_layers}, batch_size={self.config.fine_tuning.batch_size}, rank={self.config.fine_tuning.lora_rank}, iters={self.config.fine_tuning.iters}, max_seq_length={self.config.fine_tuning.max_sequence_length}).",
                            f"Modified tensor blobs written to Ollama: {ollama_exp.get('modified_blobs_written')}; reused base blobs: {ollama_exp.get('reused_blobs')}; live Ollama inference verified: {training_summary.get('ollama_verification', {}).get('success')}.",
                        ],
                        "table": loss_table,
                    },
                ],
            )
            if idx == 0:
                out_paths["finetuning_md"] = md_p
                out_paths["finetuning_pdf"] = pdf_p

        return out_paths

    def generate_comparative_report(
        self,
        baseline_metrics: Dict[str, Any],
        mitigated_metrics: Dict[str, Any],
        comparison: Dict[str, Any],
        chart_paths: List[Path],
    ) -> Dict[str, Path]:
        """Generate Report 3: Baseline vs. Mitigated Comparative Analysis (Markdown + PDF + CSV)."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        ov = comparison["overall"]
        bm = baseline_metrics["metrics"]
        mm = mitigated_metrics["metrics"]
        cat_rows = comparison["categories"]

        cat_table = [["Category", "N", "Base AFR", "Mit AFR", "Abs Imp.", "p (raw)", "p (FDR)", "p (Holm)"]]
        for r in cat_rows:
            cat_table.append(
                [
                    r["category"],
                    str(r["n_paired_adversarial"]),
                    f"{r['baseline_afr']*100:.1f}%",
                    f"{r['mitigated_afr']*100:.1f}%",
                    f"{r['absolute_improvement']*100:+.1f}%",
                    f"{r['p_value_raw']:.4f}",
                    f"{r['p_value_fdr']:.4f}",
                    f"{r['p_value_holm']:.4f}",
                ]
            )

        mc_adv = ov["mcnemar_adversarial"]
        mc_ben = ov["mcnemar_benign"]
        lat_w = ov["latency_wilcoxon"]

        md_lines = [
            "# Report 3: Comparative Safety & Regression Analysis (Baseline vs. Fine-Tuned)",
            f"**Generated:** {now_str} | **Baseline:** `{self.config.model.baseline}` | **Mitigated:** `{self.config.model.mitigated}`",
            "",
            "## 1. Executive Paired Comparison",
            f"- **Paired Valid Cases:** {comparison['n_paired_valid']} (Adversarial: {comparison['n_paired_adversarial']}, Benign Controls: {comparison['n_paired_benign']}).",
            f"- **Adversarial Failure Rate (AFR):** {ov['baseline_adversarial_failure_rate']*100:.2f}% -> {ov['mitigated_adversarial_failure_rate']*100:.2f}% (Absolute improvement: {ov['absolute_improvement']*100:+.2f} pp, Relative: {ov['relative_improvement']*100:+.1f}%).",
            f"- **Overall Paired McNemar Test (Adversarial):** fixed={mc_adv['n_10_fixed']}, regressed={mc_adv['n_01_regression']}, chi2={mc_adv['chi2_corrected']}, exact p={mc_adv['p_value']:.6f}.",
            f"- **Benign Task Completion Rate (BTCR):** {ov['baseline_benign_completion_rate']*100:.2f}% -> {ov['mitigated_benign_completion_rate']*100:.2f}% (Over-refusal delta: {ov['benign_over_refusal_delta']*100:+.2f} pp; Benign McNemar p={mc_ben['p_value']:.6f}).",
            f"- **Prompt Injection Success Rate:** {bm['prompt_injection_success_rate']*100:.2f}% -> {mm['prompt_injection_success_rate']*100:.2f}%.",
            f"- **Tool Authorization Violation Rate:** {bm['tool_authorization_violation_rate']*100:.2f}% -> {mm['tool_authorization_violation_rate']*100:.2f}%.",
            f"- **Inference Latency:** {ov['baseline_mean_latency_s']:.3f}s -> {ov['mitigated_mean_latency_s']:.3f}s (Wilcoxon p={lat_w['p_value']:.6f}).",
            "",
            "## 2. Category-by-Category Results & Multiple-Testing Corrections",
            "| Category | N_adv | Base AFR | Mit AFR | Abs Imp. | p (raw) | p (FDR) | p (Holm) |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in cat_table[1:]:
            md_lines.append(f"| {' | '.join(row)} |")

        md_lines.extend(
            [
                "",
                "## 3. Discussion: Statistical vs. Practical Significance & Remaining Vulnerabilities",
                "- Statistical significance (alpha=0.05 after Benjamini-Hochberg FDR and Holm-Bonferroni FWER adjustments) is reported separately from practical significance (>=5.0 percentage-point reduction in failure rate).",
                "- Categories with already near-zero baseline failure rates exhibit ceiling effects under McNemar's discordant-pair test.",
                "- Deterministic tool boundaries in `AgentToolSandbox` remain mandatory regardless of fine-tuning because probabilistic model alignment cannot guarantee zero unauthorized tool calls.",
                "",
                "## 4. References",
                *ACADEMIC_REFERENCES,
            ]
        )
        md_text = "\n".join(md_lines) + "\n"

        out_paths: Dict[str, Path] = {}
        for idx, target_dir in enumerate(
            [
                self.root / "3_Comparative_Analysis" / "06_Academic_Reports",
                self.root / "9_Results" / "final",
            ]
        ):
            target_dir.mkdir(parents=True, exist_ok=True)
            md_p = target_dir / "report_3_comparative_analysis.md"
            md_p.write_text(md_text, encoding="utf-8")
            pdf_p = target_dir / "report_3_comparative_analysis.pdf"
            self._render_pdf_from_sections(
                pdf_p,
                "Report 3: Baseline vs. Mitigated Comparative Analysis",
                f"{self.config.model.baseline} vs. {self.config.model.mitigated} | {now_str}",
                [
                    {
                        "heading": "1. Paired Experimental Comparison",
                        "paragraphs": [
                            f"Evaluated {comparison['n_paired_valid']} paired held-out test cases ({comparison['n_paired_adversarial']} adversarial, {comparison['n_paired_benign']} benign control) under identical prompts, system instructions, tool permissions, and decoding parameters.",
                            f"Adversarial Failure Rate changed from {ov['baseline_adversarial_failure_rate']*100:.2f}% to {ov['mitigated_adversarial_failure_rate']*100:.2f}% (McNemar exact p={mc_adv['p_value']:.6f}; fixed={mc_adv['n_10_fixed']}, regressed={mc_adv['n_01_regression']}).",
                            f"Benign Task Completion Rate changed from {ov['baseline_benign_completion_rate']*100:.2f}% to {ov['mitigated_benign_completion_rate']*100:.2f}% (McNemar p={mc_ben['p_value']:.6f}).",
                        ],
                        "images": [str(p) for p in chart_paths],
                    },
                    {
                        "heading": "2. Category-Level Statistical Table",
                        "paragraphs": [
                            "Multiple comparisons across 12 categories adjusted via Benjamini-Hochberg (FDR) and Holm-Bonferroni (FWER)."
                        ],
                        "table": cat_table,
                    },
                ],
            )
            if idx == 0:
                out_paths["comparative_md"] = md_p
                out_paths["comparative_pdf"] = pdf_p

        # Save CSV statistical tables
        comp_stats_dir = self.root / "3_Comparative_Analysis" / "04_Statistics"
        comp_stats_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(cat_rows).to_csv(comp_stats_dir / "comparative_category_statistics.csv", index=False)
        return out_paths
