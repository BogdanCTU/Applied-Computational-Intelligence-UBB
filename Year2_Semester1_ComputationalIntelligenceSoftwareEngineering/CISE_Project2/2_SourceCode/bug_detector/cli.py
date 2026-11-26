"""Command-line interface for all CISE Bug Detector v5.0.0 workflows."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from bug_detector.collection import (
    DatasetBuilder,
    GitHubBugFixCollector,
    HardNegativeCollector,
    InferredBugsIngestor,
)
from bug_detector.config import EXPERIMENT_DEFINITIONS, load_config
from bug_detector.db import BugDetectorRepository, DatabaseManager, run_migrations
from bug_detector.ml import (
    BugDetectorPredictor,
    ExperimentSuiteRunner,
    build_repository_splits,
    save_model_bundle,
    train_random_forest_with_cv,
)
from bug_detector.ml.evaluator import compute_classification_metrics
from bug_detector.ml.registry import load_model_bundle
from bug_detector.ml.trainer import load_dataset_records_from_db


def _cmd_init_db(_: argparse.Namespace) -> int:
    cfg = load_config()
    applied = run_migrations(cfg.db_path)
    print(json.dumps({"db_path": str(cfg.db_path), "applied_migrations": applied}, indent=2))
    return 0


def _cmd_collect_inferredbugs(args: argparse.Namespace) -> int:
    cfg = load_config()
    ingestor = InferredBugsIngestor(cfg)
    samples, exclusions, repos = ingestor.ingest(max_records=args.max_records)
    print(json.dumps({"samples": len(samples), "exclusions": len(exclusions), "repos": len(repos)}, indent=2))
    return 0


def _cmd_collect_github(args: argparse.Namespace) -> int:
    cfg = load_config()
    collector = GitHubBugFixCollector(cfg)
    if args.repos:
        samples, exclusions, repos = collector.collect_from_github_api(
            repo_full_names=args.repos,
            max_commits_per_repo=args.max_commits,
            max_pairs_per_repo=args.max_pairs,
        )
    else:
        samples, exclusions, repos = collector.collect_from_local_mirrors(
            max_repos=args.max_repos,
            max_commits_per_repo=args.max_commits,
            max_pairs_per_repo=args.max_pairs,
            resume=args.resume,
        )
    print(json.dumps({"samples": len(samples), "exclusions": len(exclusions), "repos": len(repos)}, indent=2))
    return 0


def _cmd_collect_hard_negatives(args: argparse.Namespace) -> int:
    cfg = load_config()
    collector = HardNegativeCollector(cfg)
    samples, exclusions, repos = collector.collect(max_repos=args.max_repos, max_per_repo=args.max_per_repo)
    print(json.dumps({"samples": len(samples), "exclusions": len(exclusions), "repos": len(repos)}, indent=2))
    return 0


def _cmd_build_dataset(args: argparse.Namespace) -> int:
    cfg = load_config()
    audit = DatasetBuilder(cfg).build(
        dataset_version=args.dataset_version,
        inferredbugs_max=args.inferredbugs_max,
        github_max_repos=args.github_max_repos,
        hard_negatives_max_repos=args.hard_negatives_max_repos,
        resume_github=args.resume_github,
    )
    print(audit.model_dump_json(indent=2))
    return 0


def _cmd_run_experiments(args: argparse.Namespace) -> int:
    cfg = load_config()
    summary = ExperimentSuiteRunner(cfg).run_all(dataset_version=args.dataset_version)
    print(json.dumps(
        {
            "champion_model_version": summary["champion_model_version"],
            "selected_experiment": summary["selected_champion_experiment"],
            "independent_test": summary["champion_independent_test_metrics"],
            "hard_negative_test": summary["champion_hard_negative_metrics"],
        },
        indent=2,
    ))
    return 0


def _cmd_train(args: argparse.Namespace) -> int:
    cfg = load_config()
    dver = args.dataset_version or cfg.dataset_version
    records, ds_meta = load_dataset_records_from_db(dver, cfg)
    splits = build_repository_splits(
        records,
        independent_test_fraction=cfg.validation.independent_test_repo_fraction,
        temporal_test_fraction=cfg.validation.temporal_test_fraction,
        random_state=cfg.validation.random_state,
    )
    exp_code = args.experiment
    groups = EXPERIMENT_DEFINITIONS[exp_code]
    if args.n_estimators:
        cfg.random_forest.n_estimators = args.n_estimators
    if args.max_depth is not None:
        cfg.random_forest.max_depth = args.max_depth

    bundle = train_random_forest_with_cv(
        dev_records=splits["dev"],
        dataset_version=dver,
        dataset_sha256=ds_meta.get("dataset_sha256"),
        experiment_code=exp_code,
        feature_groups=groups,
        config=cfg,
        tune_hyperparameters=not args.no_tune,
        tune_calibration=not args.no_tune,
    )
    X_test, _ = bundle["feature_pipeline"].transform(splits["independent_test"])
    y_test = [int(r["label"]) for r in splits["independent_test"]]
    probs_test = bundle["estimator"].predict_proba(X_test)[:, 1]
    import numpy as np

    test_m = compute_classification_metrics(
        np.array(y_test),
        probs_test,
        bundle["threshold_low"],
        bundle["threshold_center"],
        bundle["threshold_high"],
        repository_ids=[str(r["repository_id"]) for r in splits["independent_test"]],
    )
    mver = f"rf_{exp_code}_{dver}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    bundle["model_version"] = mver
    bundle["experiment_id"] = f"train_{uuid.uuid4().hex[:8]}"
    bundle["independent_test_metrics"] = test_m
    save_model_bundle(mver, bundle, config=cfg, activate=args.activate)
    print(json.dumps({"model_version": mver, "cv_metrics": bundle["cv_metrics"], "test_metrics": test_m}, indent=2))
    return 0


def _cmd_evaluate(args: argparse.Namespace) -> int:
    cfg = load_config()
    bundle = load_model_bundle(args.model, cfg)
    dver = args.dataset_version or bundle["dataset_version"]
    records, _ = load_dataset_records_from_db(dver, cfg)
    splits = build_repository_splits(records, random_state=cfg.validation.random_state)
    target_recs = splits.get(args.split, splits["independent_test"])
    X, _ = bundle["feature_pipeline"].transform(target_recs)
    import numpy as np

    y = np.array([int(r["label"]) for r in target_recs], dtype=int)
    probs = bundle["estimator"].predict_proba(X)[:, 1]
    metrics = compute_classification_metrics(
        y,
        probs,
        bundle["threshold_low"],
        bundle["threshold_center"],
        bundle["threshold_high"],
        repository_ids=[str(r["repository_id"]) for r in target_recs],
    )
    print(json.dumps(metrics, indent=2))
    return 0


def _cmd_detect(args: argparse.Namespace) -> int:
    cfg = load_config()
    predictor = BugDetectorPredictor(model_path_or_version=args.model, config=cfg)
    results = []
    for fpath_str in args.files:
        fpath = Path(fpath_str)
        src = fpath.read_text(encoding="utf-8", errors="replace")
        res = predictor.predict_source(
            source_code=src,
            file_name=fpath.name,
            input_mode="cli",
            persist_run=not args.no_persist,
        )
        results.append(res)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for res in results:
            print(f"File: {res['file_name']} | Status: {res['analysis_status']} | Model: {res['model_version']}")
            if res.get("error_message"):
                print(f"  Error: {res['error_message']}")
            for m in res["methods"]:
                prob_str = f"{m['probability']:.4f}" if m["probability"] is not None else "N/A"
                print(
                    f"  L{m['start_line']}-{m['end_line']} {m['class_name']}.{m['method_name']}: "
                    f"{m['classification']} (p={prob_str}, {m['uncertainty_status']}, rank={m['suspicious_rank']})"
                )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bug_detector", description="CISE v5.0.0 C# Source-Code Bug Detector CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Initialize SQLite database and apply migrations").set_defaults(func=_cmd_init_db)

    p_ib = sub.add_parser("collect-inferredbugs", help="Clone/ingest Microsoft InferredBugs C# pairs")
    p_ib.add_argument("--max-records", type=int, default=None)
    p_ib.set_defaults(func=_cmd_collect_inferredbugs)

    p_gh = sub.add_parser("collect-github", help="Collect verified GitHub bug-fix pairs")
    p_gh.add_argument("--repos", nargs="*", help="Optional owner/repo list to query via GitHub REST API")
    p_gh.add_argument("--max-repos", type=int, default=None)
    p_gh.add_argument("--max-commits", type=int, default=300)
    p_gh.add_argument("--max-pairs", type=int, default=20)
    p_gh.add_argument("--resume", action="store_true")
    p_gh.set_defaults(func=_cmd_collect_github)

    p_hn = sub.add_parser("collect-hard-negatives", help="Collect complex test-backed correct C# methods")
    p_hn.add_argument("--max-repos", type=int, default=None)
    p_hn.add_argument("--max-per-repo", type=int, default=None)
    p_hn.set_defaults(func=_cmd_collect_hard_negatives)

    p_bd = sub.add_parser("build-dataset", help="Build, validate, deduplicate, audit, and export dataset")
    p_bd.add_argument("--dataset-version", default=None)
    p_bd.add_argument("--inferredbugs-max", type=int, default=None)
    p_bd.add_argument("--github-max-repos", type=int, default=None)
    p_bd.add_argument("--hard-negatives-max-repos", type=int, default=None)
    p_bd.add_argument("--resume-github", action="store_true")
    p_bd.set_defaults(func=_cmd_build_dataset)

    p_ex = sub.add_parser("run-experiments", help="Run Experiments A-I, ablation, baselines, and independent evaluation")
    p_ex.add_argument("--dataset-version", default=None)
    p_ex.set_defaults(func=_cmd_run_experiments)

    p_tr = sub.add_parser("train", help="Train a Random Forest model on a chosen experiment configuration")
    p_tr.add_argument("--dataset-version", default=None)
    p_tr.add_argument("--experiment", choices=list(EXPERIMENT_DEFINITIONS.keys()), default="I")
    p_tr.add_argument("--n-estimators", type=int, default=None)
    p_tr.add_argument("--max-depth", type=int, default=None)
    p_tr.add_argument("--no-tune", action="store_true")
    p_tr.add_argument("--activate", action="store_true")
    p_tr.set_defaults(func=_cmd_train)

    p_ev = sub.add_parser("evaluate", help="Evaluate a saved model version on a split")
    p_ev.add_argument("--model", default=None)
    p_ev.add_argument("--dataset-version", default=None)
    p_ev.add_argument("--split", choices=["dev", "independent_test", "hard_negative_test", "temporal_test"], default="independent_test")
    p_ev.set_defaults(func=_cmd_evaluate)

    p_det = sub.add_parser("detect", help="Detect bugs at method level in one or more .cs files")
    p_det.add_argument("files", nargs="+", help="Paths to C# source files")
    p_det.add_argument("--model", default=None)
    p_det.add_argument("--json", action="store_true")
    p_det.add_argument("--no-persist", action="store_true")
    p_det.set_defaults(func=_cmd_detect)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
