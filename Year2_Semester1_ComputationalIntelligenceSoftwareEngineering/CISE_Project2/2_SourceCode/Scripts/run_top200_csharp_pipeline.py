"""Resumable Top-200 Star-Ranked C# Bug Detection Corpus & Method Localization Pipeline.

Discovers public C# repositories sorted strictly by GitHub stars descending,
filters out forks, archived, empty, and unsuitable projects, clones full Git
history (no shallow depth truncation), identifies bug-fixing commits and SZZ
line-blame traces, records class/method/line-range localizations, extracts
40 Roslyn class features, collects method-level localization training records,
and exports Dataset #4 (csharp_class_top200_v4 v4.0.0) without disturbing
Datasets #1, #2, or #3.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PYTHON_SRC = PROJECT_ROOT / "2_SourceCode" / "Python"
if str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))

from core.settings import get_settings
from database.connection import Database
from database.repository import CLASS_FEATURE_NAMES, RepositoryDB
from repositories.commit_collector import CommitCollector
from repositories.github_client import GitHubClient
from repositories.repository_manager import RepositoryManager
from services.analyzer.roslyn_client import RoslynClient
from services.dataset.dataset_builder import DatasetBuilder
from services.dataset.exporter import DatasetExporter
from services.dataset.feature_extractor import FeatureExtractor
from services.labeling.label_manager import LabelManager
from services.mining.bug_fix_detector import BugFixDetector
from services.mining.szz_analyzer import SZZAnalyzer
from utils.logger import setup_logger
from utils.source_classifier import is_production_csharp_file

logger = setup_logger("top200_pipeline")


def load_or_discover_top_candidates(
    gh_client: GitHubClient,
    cache_path: Path,
    max_discover: int = 500,
    min_stars: int = 100,
    max_size_kb: int = 120000,
    refresh: bool = False,
) -> Dict[str, Any]:
    """Load cached star-ranked candidates or query GitHub Search API sorted by stars descending."""
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if len(cached.get("selected", [])) >= min(250, max_discover // 2):
            logger.info(f"Loaded {len(cached['selected'])} cached star-ranked candidates from {cache_path}.")
            return cached

    logger.info(f"Discovering top public C# repositories sorted by GitHub stars descending (target pool={max_discover})...")
    discovered = gh_client.discover_top_csharp_repositories_by_stars(
        target_discovery=max_discover,
        min_stars=min_stars,
        min_size_kb=50,
        max_size_kb=max_size_kb,
        exclude_forks=True,
        exclude_archived=True,
        max_pages=8,
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(discovered, indent=2), encoding="utf-8")
    return discovered


def count_production_cs_files(local_path: Path) -> int:
    """Count tracked production C# files in the local git repository."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(local_path), "ls-files"],
            capture_output=True,
            text=True,
            timeout=20,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            return 0
        return sum(1 for f in proc.stdout.splitlines() if is_production_csharp_file(f))
    except Exception:
        return 0


def process_single_repository(
    repo_meta: Dict[str, Any],
    repo_db: RepositoryDB,
    repo_mgr: RepositoryManager,
    roslyn_client: RoslynClient,
    run_id: str,
    max_commits: int = 200,
    max_fixes: int = 35,
    clone_timeout: int = 150,
) -> Dict[str, Any]:
    """Clone/reuse repository, mine commits, run SZZ with method+line localization, and extract class features."""
    full_name = repo_meta["full_name"]
    owner = repo_meta["owner"]
    name = repo_meta["name"]
    t0 = time.time()

    existing = repo_db.get_repository_by_full_name(full_name)
    repo_payload = {
        "full_name": full_name,
        "name": name,
        "owner": owner,
        "url": repo_meta.get("url") or f"https://github.com/{full_name}",
        "description": repo_meta.get("description"),
        "license": repo_meta.get("license", "Unknown"),
        "language": repo_meta.get("language") or "C#",
        "default_branch": repo_meta.get("default_branch", "main"),
        "stars": repo_meta.get("stars", 0),
        "forks": repo_meta.get("forks", 0),
        "size_kb": repo_meta.get("size_kb", 0),
        "selection_score": repo_meta.get("selection_score", 0.0),
        "selection_rank": repo_meta.get("selection_rank"),
        "selection_reason": repo_meta.get("selection_reason"),
        "exclusion_reason": None,
        "is_selected": True,
        "is_fork": repo_meta.get("is_fork", False),
        "is_archived": repo_meta.get("is_archived", False),
        "pushed_at": repo_meta.get("pushed_at"),
        "created_at_gh": repo_meta.get("created_at_gh") or repo_meta.get("created_at"),
        "collection_run_id": run_id,
    }
    if existing:
        repo_payload["is_cloned"] = existing.get("is_cloned", 0)
        repo_payload["local_path"] = existing.get("local_path")
        repo_payload["status"] = existing.get("status", "registered")

    repo_id = repo_db.upsert_repository(repo_payload)

    # 1. Clone (skip network pull if already validly cloned locally)
    clone_url = repo_meta.get("clone_url") or f"https://github.com/{full_name}.git"
    clone_res = repo_mgr.clone_or_update(
        url=clone_url,
        owner=owner,
        name=name,
        default_branch=repo_meta.get("default_branch", "main"),
        skip_update_if_valid=True,
        timeout_seconds=clone_timeout,
    )
    local_path = Path(clone_res["local_path"])

    # 2. Check production C# files
    prod_cs_count = count_production_cs_files(local_path)
    repo_db.update_repository_metrics(repo_id, {"production_cs_files_count": prod_cs_count})
    if prod_cs_count < 5:
        reason = f"insufficient_production_csharp_files:{prod_cs_count}"
        repo_db.update_repository_metrics(repo_id, {"exclusion_reason": reason, "is_selected": 0, "status": "excluded"})
        return {"status": "excluded", "full_name": full_name, "stars": repo_meta.get("stars", 0), "url": repo_payload["url"], "repository_id": repo_id, "reason": reason}

    # 3. Fast commit mining (reuses already persisted commits if present)
    existing_commits_cnt = repo_db.get_commits_count(repo_id)
    if existing_commits_cnt >= 15:
        total_commits = existing_commits_cnt
    else:
        collector = CommitCollector(repo_db)
        commit_res = collector.extract_and_persist_fast(repo_id, local_path, max_commits=max_commits)
        total_commits = commit_res["total_in_repo"]

    if total_commits < 15:
        reason = f"insufficient_commit_history:{total_commits}"
        repo_db.update_repository_metrics(repo_id, {"exclusion_reason": reason, "is_selected": 0, "status": "excluded"})
        return {"status": "excluded", "full_name": full_name, "stars": repo_meta.get("stars", 0), "url": repo_payload["url"], "repository_id": repo_id, "reason": reason}

    # 4. Strict bug-fix detection
    detector = BugFixDetector(repo_db, default_threshold=0.50)
    fix_res = detector.detect_in_repository(repo_id, threshold=0.50, force=False, strict_mode=True)
    if fix_res["classified_bug_fixes"] == 0:
        reason = "no_bug_fixing_commits_detected"
        repo_db.update_repository_metrics(repo_id, {"exclusion_reason": reason, "is_selected": 0, "status": "excluded"})
        return {"status": "excluded", "full_name": full_name, "stars": repo_meta.get("stars", 0), "url": repo_payload["url"], "repository_id": repo_id, "reason": reason}

    # 5. Fast cached SZZ analysis
    szz_analyzer = SZZAnalyzer(repo_db)
    existing_szz = repo_db.list_szz_results(repo_id)
    if existing_szz:
        szz_traces_count = len(existing_szz)
    else:
        szz_res = szz_analyzer.run_repository_szz(
            repo_id,
            local_path,
            max_fixes=max_fixes,
            max_files_per_fix=6,
            max_deleted_lines_per_file=20,
        )
        szz_traces_count = szz_res["total_bic_traces"]

    if szz_traces_count == 0:
        reason = "no_szz_traces_on_production_csharp"
        repo_db.update_repository_metrics(repo_id, {"exclusion_reason": reason, "is_selected": 0, "status": "excluded"})
        return {"status": "excluded", "full_name": full_name, "stars": repo_meta.get("stars", 0), "url": repo_payload["url"], "repository_id": repo_id, "reason": reason}

    # 6. Class-level observations, SZZ method/line localizations & Roslyn 40-metric extraction
    label_mgr = LabelManager(repo_db, roslyn_client=roslyn_client)
    existing_buggy = repo_db.list_class_observations(repository_id=repo_id, label=1)
    if existing_buggy:
        buggy_obs = existing_buggy
        label_mgr.backfill_class_localizations(repo_id, local_path)
    else:
        buggy_obs = label_mgr.create_class_observations_from_szz(repo_id, local_path, max_traces=400)

    if len(buggy_obs) == 0:
        reason = "no_substantive_buggy_classes"
        repo_db.update_repository_metrics(repo_id, {"exclusion_reason": reason, "is_selected": 0, "status": "excluded"})
        return {"status": "excluded", "full_name": full_name, "stars": repo_meta.get("stars", 0), "url": repo_payload["url"], "repository_id": repo_id, "reason": reason}

    existing_clean = repo_db.list_class_observations(repository_id=repo_id, label=0)
    target_clean = max(8, min(35, 2 * len(buggy_obs) + 4))
    if len(existing_clean) >= target_clean // 2:
        clean_obs = existing_clean
    else:
        clean_obs = label_mgr.sample_candidate_clean_classes(
            repo_id,
            local_path,
            target_count=target_clean,
            candidate_file_limit=100,
        )

    if len(clean_obs) == 0:
        reason = "no_candidate_clean_classes"
        repo_db.update_repository_metrics(repo_id, {"exclusion_reason": reason, "is_selected": 0, "status": "excluded"})
        return {"status": "excluded", "full_name": full_name, "stars": repo_meta.get("stars", 0), "url": repo_payload["url"], "repository_id": repo_id, "reason": reason}

    # 7. Extract method localization records inside BUG classes
    method_loc_rows = label_mgr.extract_method_localization_examples(repo_id, local_path, max_classes=60)

    total_cls = len(buggy_obs) + len(clean_obs)
    repo_db.update_repository_metrics(
        repo_id,
        {
            "commits_mined_count": total_commits,
            "bug_fixes_count": fix_res["classified_bug_fixes"],
            "szz_traces_count": szz_traces_count,
            "class_observations_count": total_cls,
            "status": "processed",
            "is_selected": 1,
        },
    )

    elapsed = round(time.time() - t0, 2)
    return {
        "status": "processed",
        "full_name": full_name,
        "url": repo_payload["url"],
        "stars": repo_meta.get("stars", 0),
        "language": repo_payload["language"],
        "repository_id": repo_id,
        "prod_cs_files": prod_cs_count,
        "commits": total_commits,
        "bug_fixes": fix_res["classified_bug_fixes"],
        "szz_traces": szz_traces_count,
        "buggy_classes": len(buggy_obs),
        "clean_classes": len(clean_obs),
        "total_classes": total_cls,
        "method_loc_rows": method_loc_rows,
        "duration_s": elapsed,
    }


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect top 200 star-ranked public C# repositories.")
    parser.add_argument("--target-repos", type=int, default=200, help="Target processed repositories.")
    parser.add_argument("--max-discover", type=int, default=500, help="Discovery candidate pool size.")
    parser.add_argument("--max-commits", type=int, default=200, help="Max commits mined per repo.")
    parser.add_argument("--refresh-discovery", action="store_true", help="Ignore cached discovery results.")
    args = parser.parse_args()

    settings = get_settings()
    settings.ensure_directories()
    db = Database(settings.storage.database_path)
    repo_db = RepositoryDB(db)
    repo_mgr = RepositoryManager(settings.storage.repositories_dir, db=repo_db)
    gh_client = GitHubClient(token=settings.github.token)
    roslyn_client = RoslynClient()

    run_id = f"top200_v4_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    cache_path = settings.storage.processed_dir / "discovered_top200_csharp_repos_v4.json"
    checkpoint_path = settings.storage.processed_dir / "collection_checkpoint_top200_v4.json"
    method_loc_csv_path = settings.storage.processed_dir / "method_localization_top200_v4.csv"

    discovery = load_or_discover_top_candidates(
        gh_client=gh_client,
        cache_path=cache_path,
        max_discover=args.max_discover,
        min_stars=100,
        max_size_kb=settings.collection.max_repo_size_kb,
        refresh=args.refresh_discovery,
    )

    excluded_discovery: List[Dict[str, Any]] = [
        {
            "full_name": r["full_name"],
            "url": r.get("url"),
            "stars": r.get("stars", 0),
            "language": r.get("language"),
            "reason": r.get("exclusion_reason"),
        }
        for r in discovery.get("excluded", [])
    ]

    checkpoint: Dict[str, Any] = {
        "run_id": run_id,
        "target_repos": args.target_repos,
        "processed": {},
        "excluded": {},
        "failed": {},
    }
    if checkpoint_path.exists():
        loaded_cp = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        checkpoint["processed"] = loaded_cp.get("processed", {})
        checkpoint["excluded"] = loaded_cp.get("excluded", {})
        checkpoint["failed"] = loaded_cp.get("failed", {})

    selected_candidates = discovery["selected"]
    repo_db.upsert_collection_run({
        "run_id": run_id,
        "target_repositories": args.target_repos,
        "discovered_count": discovery["discovered_total"],
        "selected_count": len(selected_candidates),
        "processed_count": len(checkpoint["processed"]),
        "excluded_count": len(checkpoint["excluded"]) + len(excluded_discovery),
        "failed_count": len(checkpoint["failed"]),
        "status": "running",
        "config": {
            "ranking": "stars_descending",
            "max_commits": args.max_commits,
            "target_repos": args.target_repos,
            "clone_strategy": "full_history_no_tags",
        },
        "checkpoint_path": str(checkpoint_path),
    })

    print(f"Top-starred C# discovery: {discovery['discovered_total']} discovered, {len(selected_candidates)} eligible candidates.")
    print(f"Resuming with {len(checkpoint['processed'])} already processed repositories.")

    for idx, repo_meta in enumerate(selected_candidates, 1):
        if len(checkpoint["processed"]) >= args.target_repos:
            break

        free_gb = shutil.disk_usage(settings.storage.repositories_dir).free / (1024 ** 3)
        if free_gb < 3.0:
            logger.warning(f"Low disk space ({free_gb:.2f} GiB free). Stopping collection cleanly.")
            break

        full_name = repo_meta["full_name"]
        if full_name in checkpoint["processed"] or full_name in checkpoint["excluded"]:
            continue

        stars = repo_meta.get("stars", 0)
        size_kb = repo_meta.get("size_kb", 0)
        print(f"[{len(checkpoint['processed'])}/{args.target_repos} ok | rank #{idx}/{len(selected_candidates)}] {full_name} (stars={stars}, size={size_kb}KB)...")

        try:
            res = process_single_repository(
                repo_meta=repo_meta,
                repo_db=repo_db,
                repo_mgr=repo_mgr,
                roslyn_client=roslyn_client,
                run_id=run_id,
                max_commits=args.max_commits,
            )
            method_rows = res.pop("method_loc_rows", [])
            if res["status"] == "processed":
                checkpoint["processed"][full_name] = res
                if method_rows:
                    df_m = pd.DataFrame(method_rows)
                    header = not method_loc_csv_path.exists()
                    df_m.to_csv(method_loc_csv_path, mode="a", header=header, index=False, encoding="utf-8")
                print(
                    f"  -> OK: +{res['buggy_classes']} BUG, +{res['clean_classes']} CLEAN, "
                    f"+{len(method_rows)} method loc rows ({res['duration_s']}s)"
                )
            else:
                checkpoint["excluded"][full_name] = res
                print(f"  -> EXCLUDED: {res['reason']}")
        except Exception as e:
            err_msg = str(e)[:400]
            logger.warning(f"Repository {full_name} failed: {err_msg}")
            existing_r = repo_db.get_repository_by_full_name(full_name)
            if existing_r:
                repo_db.update_repository_metrics(
                    existing_r["id"],
                    {"status": "failed", "processing_error": err_msg, "is_selected": 0},
                )
            checkpoint["failed"][full_name] = {
                "full_name": full_name,
                "url": repo_meta.get("url"),
                "stars": stars,
                "error": err_msg,
            }
            print(f"  -> FAILED: {err_msg[:120]}")

        if (idx % 3 == 0) or (len(checkpoint["processed"]) >= args.target_repos):
            save_json(checkpoint_path, checkpoint)
            repo_db.upsert_collection_run({
                "run_id": run_id,
                "target_repositories": args.target_repos,
                "discovered_count": discovery["discovered_total"],
                "selected_count": len(selected_candidates),
                "processed_count": len(checkpoint["processed"]),
                "excluded_count": len(checkpoint["excluded"]) + len(excluded_discovery),
                "failed_count": len(checkpoint["failed"]),
                "status": "running",
                "checkpoint_path": str(checkpoint_path),
            })

    save_json(checkpoint_path, checkpoint)

    # Deduplicate method localization CSV across resumed runs if it exists
    if method_loc_csv_path.exists():
        df_mloc = pd.read_csv(method_loc_csv_path)
        df_mloc = df_mloc.drop_duplicates(subset=["class_observation_id", "method_signature", "start_line"])
        df_mloc.to_csv(method_loc_csv_path, index=False, encoding="utf-8")

    processed_ids = sorted({int(v["repository_id"]) for v in checkpoint["processed"].values() if v.get("repository_id")})
    if not processed_ids:
        raise RuntimeError("Zero repositories processed; cannot build Top-200 dataset.")

    extractor = FeatureExtractor(repo_db, roslyn_client=roslyn_client)
    sweep_res = extractor.batch_extract_classes(force=False)
    print(f"Post-collection feature sweep: {sweep_res}")

    builder = DatasetBuilder(repo_db)
    n_proc = len(checkpoint["processed"])
    dataset_id, ds_stats = builder.generate_class_dataset_snapshot(
        name="csharp_class_top200_v4",
        version="4.0.0",
        description=(
            f"Class-level C# bug detection classifier corpus mined from {n_proc} "
            "top-starred public GitHub C# repositories with SZZ method/line localizations and 40 Roslyn class features."
        ),
        exclude_uncertain=True,
        feature_names=list(CLASS_FEATURE_NAMES),
        repository_ids=processed_ids,
        deduplicate_exact_source=True,
        deduplicate_repeated_revisions=True,
        overwrite=True,
    )

    all_exclusions = excluded_discovery + [
        {
            "full_name": k,
            "url": v.get("url"),
            "stars": v.get("stars", 0),
            "reason": v.get("reason") or v.get("error"),
        }
        for k, v in {**checkpoint["excluded"], **checkpoint["failed"]}.items()
    ]

    exporter = DatasetExporter(repo_db, settings.storage.processed_dir)
    export_res = exporter.export_to_csv(
        dataset_id=dataset_id,
        overwrite=True,
        duplicate_analysis=ds_stats.get("duplicate_analysis"),
        excluded_repositories=all_exclusions,
    )

    summary_payload = {
        "run_id": run_id,
        "ranking_strategy": "stars_descending",
        "target_repositories": args.target_repos,
        "discovered_repositories": discovery["discovered_total"],
        "selected_candidates": len(selected_candidates),
        "processed_repositories": len(checkpoint["processed"]),
        "excluded_repositories": len(checkpoint["excluded"]) + len(excluded_discovery),
        "excluded_after_discovery": len(checkpoint["excluded"]),
        "failed_repositories": len(checkpoint["failed"]),
        "dataset_id": dataset_id,
        "dataset_stats": ds_stats,
        "method_localization_rows": len(pd.read_csv(method_loc_csv_path)) if method_loc_csv_path.exists() else 0,
        "export": export_res,
    }
    save_json(settings.storage.processed_dir / "collection_summary_top200_v4.json", summary_payload)
    repo_db.upsert_collection_run({
        "run_id": run_id,
        "target_repositories": args.target_repos,
        "discovered_count": discovery["discovered_total"],
        "selected_count": len(selected_candidates),
        "processed_count": len(checkpoint["processed"]),
        "excluded_count": len(checkpoint["excluded"]) + len(excluded_discovery),
        "failed_count": len(checkpoint["failed"]),
        "status": "completed",
        "checkpoint_path": str(checkpoint_path),
    })

    print("\n=== TOP-200 STAR-RANKED C# COLLECTION COMPLETE ===")
    print(json.dumps({
        "processed_repos": len(checkpoint["processed"]),
        "dataset_repos": ds_stats["repository_count"],
        "total_classes": ds_stats["total_observations"],
        "bug_classes": ds_stats["buggy_count"],
        "clean_classes": ds_stats["clean_count"],
        "sha256": export_res["sha256_checksum"],
        "method_localization_rows": summary_payload["method_localization_rows"],
    }, indent=2))


if __name__ == "__main__":
    main()
