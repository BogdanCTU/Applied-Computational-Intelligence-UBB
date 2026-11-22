"""Unified CLI for the Local LLM Adversarial Safety Testing, Fine-Tuning & Mitigation Platform."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from source.analytics.full_evaluation_pipeline import FullEvaluationPackageGenerator
from source.analytics.metrics import compute_safety_metrics
from source.analytics.statistics import compare_experiments
from source.analytics.visualizations import generate_baseline_charts, generate_comparative_charts
from source.classification.classifier import ResponseClassifier
from source.config.settings import get_project_root, load_config
from source.execution.runner import PenetrationRunner
from source.fine_tuning.dataset_builder import MitigationDatasetBuilder
from source.fine_tuning.trainer import SafetyLoRATrainer
from source.models.verifier import ModelVerifier
from source.penetration.taxonomy import CATEGORIES
from source.reporting.academic_reports import AcademicReportGenerator
from source.storage.database import DatabaseManager
from source.storage.exporter import DataExporter
from source.storage.models import ComparativeResult, EvaluationRun, TestCaseRecord, TestCategory
from source.test_generation.diversity import compute_diversity_report
from source.test_generation.generator import PenetrationTestGenerator
from source.utils.hashing import sha256_text
from source.utils.logging_utils import get_logger

logger = get_logger("cli")


def _parse_categories(raw: Optional[str]) -> Optional[List[str]]:
    if not raw:
        return None
    return [c.strip() for c in raw.split(",") if c.strip()]


def cmd_check_environment(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    db = DatabaseManager(cfg.storage.sqlite_path)
    db.init_db(export_schema=True)
    verifier = ModelVerifier(cfg)
    status = verifier.check_environment(get_project_root())
    out = {
        "python_version": status.python_version,
        "platform_machine": status.platform_machine,
        "total_memory_gb": round((status.total_memory_bytes or 0) / (1024**3), 2),
        "free_disk_gb": status.free_disk_gb,
        "ollama_reachable": status.ollama_reachable,
        "ollama_version": status.ollama_version,
        "available_models": status.available_models,
        "baseline_model": status.baseline_model.__dict__,
        "mitigated_model": status.mitigated_model.__dict__,
        "mlx_available": status.mlx_available,
        "mlx_lm_version": status.mlx_lm_version,
        "sqlite_tables": db.get_table_counts(),
    }
    env_file = get_project_root() / "8_Build" / "outputs" / "environment_check.json"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if status.ollama_reachable and status.baseline_model.available else 1


def cmd_generate_tests(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    db = DatabaseManager(cfg.storage.sqlite_path)
    db.init_db()
    count = args.count_per_category or cfg.penetration.minimum_tests_per_category
    gen = PenetrationTestGenerator(seed=cfg.penetration.random_seed, dataset_version=cfg.project.dataset_version)
    cases = gen.generate(count_per_category=count)

    if args.dry_run:
        print(json.dumps({"dry_run": True, "planned_total_cases": len(cases), "categories": len(CATEGORIES)}, indent=2))
        return 0

    save_info = gen.save_dataset(cases)
    div_path = get_project_root() / "1_Penetration" / "02_Test_Cases" / "diversity_report.json"
    diversity = compute_diversity_report(cases, output_path=div_path)

    with db.session() as sess:
        for cat in CATEGORIES:
            existing = sess.query(TestCategory).filter(TestCategory.id == cat.category_id).one_or_none()
            if existing is None:
                sess.add(
                    TestCategory(
                        id=cat.category_id,
                        name=cat.display_name,
                        description=cat.description,
                        risk_domain=cat.risk_domain,
                        target_count=count,
                    )
                )
        sess.flush()

        for c in cases:
            conv_json = json.dumps(c.conversation)
            existing_tc = sess.query(TestCaseRecord).filter(TestCaseRecord.test_id == c.test_id).one_or_none()
            if existing_tc is None:
                sess.add(
                    TestCaseRecord(
                        test_id=c.test_id,
                        category_id=c.category,
                        subcategory=c.subcategory,
                        severity=c.severity,
                        risk_type=c.risk_type,
                        attack_pattern=c.attack_pattern,
                        expected_behavior=c.expected_behavior,
                        expected_risk=c.expected_risk,
                        split=c.split,
                        template_family=c.template_family,
                        dataset_version=c.dataset_version,
                        conversation_json=conv_json,
                        evaluation_criteria_json=json.dumps(c.evaluation_criteria),
                        tags_json=json.dumps(c.tags),
                        prompt_hash=sha256_text(conv_json),
                    )
                )

    print(json.dumps({"saved": save_info, "diversity_summary": {k: v for k, v in diversity.items() if k != "categories"}}, indent=2))
    return 0


def cmd_run_baseline(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    db = DatabaseManager(cfg.storage.sqlite_path)
    db.init_db()
    runner = PenetrationRunner(cfg, db)
    exp_id = args.experiment_id or "exp_baseline_v1"
    split = None if args.split == "all" else (args.split or cfg.penetration.eval_split)
    res = runner.run_experiment(
        experiment_id=exp_id,
        model_identifier=cfg.model.baseline,
        phase="baseline",
        split=split,
        categories=_parse_categories(args.categories),
        limit_per_category=args.count_per_category,
        resume=args.resume,
        dry_run=args.dry_run,
    )
    print(json.dumps(res, indent=2))
    return 0


def cmd_analyze_baseline(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    db = DatabaseManager(cfg.storage.sqlite_path)
    db.init_db()
    root = get_project_root()
    exp_id = args.experiment_id or "exp_baseline_v1"

    classifier = ResponseClassifier(cfg, db)
    eval_run_id, records = classifier.classify_experiment(
        experiment_id=exp_id,
        output_dir=root / "1_Penetration" / "05_Processed_Results",
    )
    # Also persist classification copy into 1_Penetration/06_Classification & 3_Comparative_Analysis/01_Baseline
    (root / "1_Penetration" / "06_Classification" / f"{exp_id}_classifications.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )
    (root / "3_Comparative_Analysis" / "01_Baseline" / f"{exp_id}_classifications.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )

    stats_path = root / "1_Penetration" / "07_Statistics" / "baseline_metrics.json"
    metrics = compute_safety_metrics(records, confidence_level=cfg.evaluation.confidence_level, output_path=stats_path)
    (root / "3_Comparative_Analysis" / "01_Baseline" / "baseline_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    with db.session() as sess:
        er = sess.query(EvaluationRun).filter(EvaluationRun.id == eval_run_id).one()
        er.metrics_json = json.dumps(metrics)

    charts_1 = generate_baseline_charts(records, metrics, root / "1_Penetration" / "08_Visualizations", prefix="baseline")
    charts_2 = generate_baseline_charts(records, metrics, root / "9_Results" / "baseline", prefix="baseline")
    print(json.dumps({"eval_run_id": eval_run_id, "metrics": metrics["metrics"], "charts": [str(c) for c in charts_1]}, indent=2))
    return 0


def cmd_generate_mitigation_data(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    db = DatabaseManager(cfg.storage.sqlite_path)
    db.init_db()
    builder = MitigationDatasetBuilder(cfg, db)
    manifest = builder.build_datasets(baseline_experiment_id=args.experiment_id or "exp_baseline_v1")
    print(json.dumps(manifest, indent=2))
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    db = DatabaseManager(cfg.storage.sqlite_path)
    db.init_db()
    trainer = SafetyLoRATrainer(cfg, db)
    summary = trainer.train_and_deploy(run_id=args.run_id, dry_run=args.dry_run)
    print(json.dumps(summary, indent=2))
    return 0


def cmd_run_mitigated(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    db = DatabaseManager(cfg.storage.sqlite_path)
    db.init_db()
    runner = PenetrationRunner(cfg, db)
    exp_id = args.experiment_id or "exp_mitigated_v1"
    split = None if args.split == "all" else (args.split or cfg.penetration.eval_split)
    res = runner.run_experiment(
        experiment_id=exp_id,
        model_identifier=cfg.model.mitigated,
        phase="mitigated",
        split=split,
        categories=_parse_categories(args.categories),
        limit_per_category=args.count_per_category,
        resume=args.resume,
        dry_run=args.dry_run,
    )
    print(json.dumps(res, indent=2))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    db = DatabaseManager(cfg.storage.sqlite_path)
    db.init_db()
    root = get_project_root()

    base_exp = args.baseline_experiment or "exp_baseline_v1"
    mit_exp = args.mitigated_experiment or "exp_mitigated_v1"

    classifier = ResponseClassifier(cfg, db)
    base_eval_id, base_records = classifier.classify_experiment(
        base_exp, output_dir=root / "3_Comparative_Analysis" / "01_Baseline"
    )
    mit_eval_id, mit_records = classifier.classify_experiment(
        mit_exp, output_dir=root / "3_Comparative_Analysis" / "02_Mitigated"
    )

    base_metrics = compute_safety_metrics(
        base_records,
        confidence_level=cfg.evaluation.confidence_level,
        output_path=root / "3_Comparative_Analysis" / "01_Baseline" / "baseline_metrics.json",
    )
    mit_metrics = compute_safety_metrics(
        mit_records,
        confidence_level=cfg.evaluation.confidence_level,
        output_path=root / "3_Comparative_Analysis" / "02_Mitigated" / "mitigated_metrics.json",
    )

    comparison = compare_experiments(
        base_records,
        mit_records,
        confidence_level=cfg.evaluation.confidence_level,
        output_path=root / "3_Comparative_Analysis" / "03_Comparison" / "comparative_metrics.json",
    )
    (root / "3_Comparative_Analysis" / "04_Statistics" / "comparative_metrics.json").write_text(
        json.dumps(comparison, indent=2), encoding="utf-8"
    )
    (root / "9_Results" / "final" / "comparative_metrics.json").write_text(
        json.dumps(comparison, indent=2), encoding="utf-8"
    )

    with db.session() as sess:
        sess.query(EvaluationRun).filter(EvaluationRun.id == base_eval_id).one().metrics_json = json.dumps(base_metrics)
        sess.query(EvaluationRun).filter(EvaluationRun.id == mit_eval_id).one().metrics_json = json.dumps(mit_metrics)
        comp_id = f"comp_{base_exp}_vs_{mit_exp}"
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

    charts_comp = generate_comparative_charts(
        base_metrics, mit_metrics, comparison, root / "3_Comparative_Analysis" / "05_Visualizations"
    )
    generate_comparative_charts(base_metrics, mit_metrics, comparison, root / "9_Results" / "final")

    print(json.dumps({"overall": comparison["overall"], "charts": [str(c) for c in charts_comp]}, indent=2))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    db = DatabaseManager(cfg.storage.sqlite_path)
    db.init_db()
    root = get_project_root()

    env_path = root / "8_Build" / "outputs" / "environment_check.json"
    env_info = json.loads(env_path.read_text(encoding="utf-8")) if env_path.exists() else {}

    div_path = root / "1_Penetration" / "02_Test_Cases" / "diversity_report.json"
    diversity = json.loads(div_path.read_text(encoding="utf-8")) if div_path.exists() else {}

    base_metrics_path = root / "1_Penetration" / "07_Statistics" / "baseline_metrics.json"
    base_metrics = json.loads(base_metrics_path.read_text(encoding="utf-8"))

    base_rec_path = root / "1_Penetration" / "05_Processed_Results" / f"{args.baseline_experiment or 'exp_baseline_v1'}_classified.json"
    base_records = json.loads(base_rec_path.read_text(encoding="utf-8")) if base_rec_path.exists() else []

    base_charts = sorted((root / "1_Penetration" / "08_Visualizations").glob("*.png"))
    reporter = AcademicReportGenerator(cfg)
    paths: dict[str, str] = {}

    r1 = reporter.generate_baseline_report(env_info, diversity, base_metrics, base_records, base_charts)
    paths.update({k: str(v) for k, v in r1.items()})

    manifest_path = root / "2_FineTune" / "01_Dataset_Generation" / "dataset_manifest.json"
    train_summaries = sorted((root / "2_FineTune" / "09_Evaluation").glob("*_training_summary.json"))
    if manifest_path.exists() and train_summaries:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        train_summary = json.loads(train_summaries[-1].read_text(encoding="utf-8"))
        r2 = reporter.generate_finetuning_report(manifest, train_summary)
        paths.update({k: str(v) for k, v in r2.items()})

    comp_path = root / "3_Comparative_Analysis" / "03_Comparison" / "comparative_metrics.json"
    mit_metrics_path = root / "3_Comparative_Analysis" / "02_Mitigated" / "mitigated_metrics.json"
    if comp_path.exists() and mit_metrics_path.exists():
        comp = json.loads(comp_path.read_text(encoding="utf-8"))
        mit_metrics = json.loads(mit_metrics_path.read_text(encoding="utf-8"))
        comp_charts = sorted((root / "3_Comparative_Analysis" / "05_Visualizations").glob("*.png"))
        r3 = reporter.generate_comparative_report(base_metrics, mit_metrics, comp, comp_charts)
        paths.update({k: str(v) for k, v in r3.items()})

    # Export key SQLite tables & create database backup
    exporter = DataExporter(db, cfg.storage.export_dir)
    for tbl in ("test_cases", "test_executions", "safety_evaluations", "comparative_results", "training_runs"):
        exporter.export_table(tbl)
    backup_path = db.backup(cfg.storage.backup_dir, label="post_report")
    paths["sqlite_backup"] = str(backup_path)

    print(json.dumps(paths, indent=2))
    return 0


def cmd_full_package(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    db = DatabaseManager(cfg.storage.sqlite_path)
    db.init_db()
    pkg = FullEvaluationPackageGenerator(cfg, db)
    summary = pkg.run_all(
        baseline_exp_id=args.baseline_experiment or "exp_baseline_full_v3",
        mitigated_exp_id=args.mitigated_experiment or "exp_mitigated_full_v3",
    )
    print(json.dumps(summary, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m source.cli",
        description="Local LLM Adversarial Safety Testing, Fine-Tuning & Mitigation Platform",
    )
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check-environment", help="Verify local Python, Ollama, MLX, and SQLite")

    p_gen = sub.add_parser("generate-tests", help="Generate >=100 test cases per category across 12 categories")
    p_gen.add_argument("--count-per-category", type=int, default=None)
    p_gen.add_argument("--dry-run", action="store_true")

    for name in ("run-baseline", "run-mitigated"):
        p_run = sub.add_parser(name, help=f"Execute penetration tests ({name})")
        p_run.add_argument("--experiment-id", default=None)
        p_run.add_argument("--split", default=None, help="held_out_eval | train_pool | val_pool | all")
        p_run.add_argument("--categories", default=None, help="Comma-separated category IDs")
        p_run.add_argument("--count-per-category", type=int, default=None)
        p_run.add_argument("--resume", action="store_true", default=True)
        p_run.add_argument("--no-resume", dest="resume", action="store_false")
        p_run.add_argument("--dry-run", action="store_true")

    p_ab = sub.add_parser("analyze-baseline", help="Classify and analyze baseline penetration results")
    p_ab.add_argument("--experiment-id", default=None)

    p_gm = sub.add_parser("generate-mitigation-data", help="Generate leakage-free SFT mitigation datasets")
    p_gm.add_argument("--experiment-id", default=None)

    p_tr = sub.add_parser("train", help="Run MLX-LM LoRA fine-tuning, fuse weights, and register in Ollama")
    p_tr.add_argument("--run-id", default=None)
    p_tr.add_argument("--dry-run", action="store_true")

    p_cmp = sub.add_parser("compare", help="Compare baseline and mitigated experiments statistically")
    p_cmp.add_argument("--baseline-experiment", default=None)
    p_cmp.add_argument("--mitigated-experiment", default=None)

    p_rep = sub.add_parser("report", help="Generate Markdown/PDF reports, charts, exports, and DB backup")
    p_rep.add_argument("--baseline-experiment", default=None)

    p_fp = sub.add_parser("full-package", help="Run full v2 classification, stats, 12 charts, human review, and Reports A/B/C")
    p_fp.add_argument("--baseline-experiment", default="exp_baseline_full_v3")
    p_fp.add_argument("--mitigated-experiment", default="exp_mitigated_full_v3")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch = {
        "check-environment": cmd_check_environment,
        "generate-tests": cmd_generate_tests,
        "run-baseline": cmd_run_baseline,
        "analyze-baseline": cmd_analyze_baseline,
        "generate-mitigation-data": cmd_generate_mitigation_data,
        "train": cmd_train,
        "run-mitigated": cmd_run_mitigated,
        "compare": cmd_compare,
        "report": cmd_report,
        "full-package": cmd_full_package,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
