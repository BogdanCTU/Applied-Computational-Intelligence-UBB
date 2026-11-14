"""Phase 2: Controlled Dataset Expansion Script.

Expands the empirical C# defect prediction dataset by ingesting:
- serilog/serilog
- App-vNext/Polly

Combines these with Humanizer, MediatR, and FluentValidation to generate
Dataset Snapshot #2 (csharp_empirical_v2 v2.0.0) across 5 distinct training repositories.
Strictly preserves Dataset Snapshot #1 (csharp_empirical_v1) and strictly quarantines Newtonsoft.Json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from src.collection.commit_collector import CommitCollector
from src.collection.repository_manager import RepositoryManager
from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.dataset.dataset_builder import DatasetBuilder
from src.dataset.exporter import DatasetExporter
from src.dataset.feature_extractor import FeatureExtractor
from src.labeling.label_manager import LabelManager
from src.mining.bug_fix_detector import BugFixDetector
from src.mining.szz_analyzer import SZZAnalyzer
from src.utils.logger import setup_logger
from src.utils.source_classifier import is_production_csharp_file

logger = setup_logger("dataset_expansion")


def process_repository(
    repo_meta: Dict[str, Any],
    repo_db: RepositoryDB,
    repo_mgr: RepositoryManager,
    max_commits: int = 350,
) -> Dict[str, Any]:
    full_name = repo_meta["full_name"]
    print(f"\n{'='*70}\nProcessing Repository: {full_name}\n{'='*70}")
    t0 = time.time()

    # 1. Register
    repo_id = repo_db.upsert_repository(repo_meta)
    print(f"Registered repo ID #{repo_id}: {full_name}")

    # 2. Clone or update
    print(f"Cloning/updating {full_name} from {repo_meta['url']} (branch: {repo_meta['default_branch']})...")
    clone_res = repo_mgr.clone_or_update(
        url=repo_meta["url"],
        owner=repo_meta["owner"],
        name=repo_meta["name"],
        default_branch=repo_meta["default_branch"],
    )
    local_path = Path(clone_res["local_path"])
    print(f"Local path: {local_path} (status: {clone_res['status']})")

    # 3. Mine commits
    print(f"Mining commit history (max: {max_commits})...")
    collector = CommitCollector(repo_db)
    commit_res = collector.extract_and_persist(repo_id, local_path, max_commits=max_commits)
    print(f"Mined {commit_res['new_extracted']} new commits (total in repo: {commit_res['total_in_repo']})")

    # 4. Detect bug fixes
    print("Running bug-fixing commit detection (threshold = 0.50)...")
    detector = BugFixDetector(repo_db, default_threshold=0.50)
    fix_res = detector.detect_in_repository(repo_id, threshold=0.50)
    print(f"Classified {fix_res['classified_bug_fixes']} bug-fixing commits out of {fix_res['total_commits']} commits")

    # 5. SZZ Tracing
    print("Running SZZ line blame tracing...")
    szz_analyzer = SZZAnalyzer(repo_db)
    szz_res = szz_analyzer.run_repository_szz(repo_id, local_path)
    print(f"SZZ found {szz_res['total_bic_traces']} BIC line traces across {szz_res['unique_bug_inducing_commits']} unique BICs")

    # 6. Method-level labeling
    print("Extracting SZZ-derived buggy methods (Label 1)...")
    label_mgr = LabelManager(repo_db)
    buggy_obs = label_mgr.create_observations_from_szz(repo_id, local_path)
    print(f"Created {len(buggy_obs)} buggy method observations")

    # 7. Sample matching candidate-clean methods from HEAD (1:1 balance)
    target_clean = len(buggy_obs)
    print(f"Sampling {target_clean} candidate-clean methods (Label 0) from HEAD...")
    clean_obs = label_mgr.sample_candidate_clean_methods(repo_id, local_path, target_count=target_clean)
    print(f"Sampled {len(clean_obs)} clean method observations")

    # 8. Extract Roslyn static metrics
    print("Extracting Roslyn static metrics for new observations...")
    feat_extractor = FeatureExtractor(repo_db)
    feat_res = feat_extractor.batch_extract(repository_id=repo_id)
    print(f"Features extracted: {feat_res['success']} succeeded, {feat_res['failed']} failed")

    elapsed = round(time.time() - t0, 2)
    return {
        "repository_id": repo_id,
        "full_name": full_name,
        "commits_mined": commit_res["new_extracted"] + commit_res["already_present"],
        "bug_fixing_commits": fix_res["classified_bug_fixes"],
        "szz_traces": szz_res["total_bic_traces"],
        "unique_bics": szz_res["unique_bug_inducing_commits"],
        "buggy_methods": len(buggy_obs),
        "clean_methods": len(clean_obs),
        "total_methods": len(buggy_obs) + len(clean_obs),
        "features_extracted": feat_res["success"],
        "duration_seconds": elapsed,
    }


def main() -> None:
    print("======================================================================")
    print("PHASE 2: CONTROLLED DATASET EXPANSION (Serilog & Polly)")
    print("======================================================================")
    start_time = time.time()
    settings = get_settings()
    settings.ensure_directories()
    db = Database(settings.storage.database_path)
    repo_db = RepositoryDB(db)
    repo_mgr = RepositoryManager(settings.storage.repositories_dir, db=repo_db)

    # -----------------------------------------------------------------
    # Baseline Pre-check
    # -----------------------------------------------------------------
    with db.session() as conn:
        ds1 = conn.execute("SELECT id, name, version, total_count, buggy_count, non_buggy_count FROM datasets WHERE id = 1").fetchone()
        assert ds1 is not None, "Dataset Snapshot #1 missing!"
        ds1_dict = dict(ds1)
        print(f"Baseline Snapshot #1 in DB: {ds1_dict}")

        # Check existing repos
        existing_repos = conn.execute("SELECT id, full_name FROM repositories ORDER BY id").fetchall()
        print(f"Existing Repositories: {[dict(r) for r in existing_repos]}")

    # -----------------------------------------------------------------
    # Repository Definitions
    # -----------------------------------------------------------------
    targets = [
        {
            "full_name": "serilog/serilog",
            "name": "serilog",
            "owner": "serilog",
            "url": "https://github.com/serilog/serilog.git",
            "description": "Simple .NET logging with fully-structured events",
            "license": "Apache-2.0",
            "default_branch": "dev",
            "stars": 7200,
            "status": "registered",
        },
        {
            "full_name": "App-vNext/Polly",
            "name": "Polly",
            "owner": "App-vNext",
            "url": "https://github.com/App-vNext/Polly.git",
            "description": "Polly is a .NET resilience and transient-fault-handling library.",
            "license": "BSD-3-Clause",
            "default_branch": "main",
            "stars": 13500,
            "status": "registered",
        },
    ]

    results: List[Dict[str, Any]] = []
    for target in targets:
        res = process_repository(target, repo_db, repo_mgr, max_commits=350)
        results.append(res)

    # -----------------------------------------------------------------
    # Build Dataset Snapshot #2
    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("CONSTRUCTING DATASET SNAPSHOT #2 (csharp_empirical_v2 v2.0.0)")
    print("=" * 70)

    # Training repositories: Humanizer (4), MediatR (3), FluentValidation (14), plus the 2 new ones
    with db.session() as conn:
        repo_lookup = {r["full_name"]: r["id"] for r in conn.execute("SELECT id, full_name FROM repositories").fetchall()}

    training_repo_names = [
        "Humanizr/Humanizer",
        "LuckyPennySoftware/MediatR",
        "FluentValidation/FluentValidation",
        "serilog/serilog",
        "App-vNext/Polly",
    ]

    training_repo_ids = [repo_lookup[name] for name in training_repo_names if name in repo_lookup]
    print(f"Training Repository IDs ({len(training_repo_ids)} repos): {training_repo_ids}")
    assert len(training_repo_ids) == 5, f"Expected 5 training repositories, found: {training_repo_ids}"

    builder = DatasetBuilder(repo_db)
    ds2_id, ds2_stats = builder.generate_dataset_snapshot(
        name="csharp_empirical_v2",
        version="2.0.0",
        description="Expanded empirical C# dataset covering 5 training repositories with 1:1 balanced production method observations for 5-fold GroupKFold cross-validation.",
        exclude_uncertain=True,
        repository_ids=training_repo_ids,
    )
    print(f"Generated Dataset Snapshot #2 (ID #{ds2_id}) successfully!")
    print(f"Snapshot #2 Stats: {ds2_stats}")

    # Export CSVs to data/processed/
    exporter = DatasetExporter(repo_db, settings.storage.processed_dir)
    ds2_export = exporter.export_to_csv(ds2_id, filename_prefix="csharp_empirical_v2_v2.0.0", overwrite=True)
    print(f"Exported Dataset Snapshot #2 to {ds2_export['csv_path']}")

    # Export Snapshot #1 to CSV as well to ensure concrete preservation
    ds1_export = exporter.export_to_csv(1, filename_prefix="csharp_empirical_v1_v1.0.0", overwrite=True)
    print(f"Exported Dataset Snapshot #1 to {ds1_export['csv_path']}")

    # -----------------------------------------------------------------
    # Integrity Verification
    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("POST-EXPANSION INTEGRITY AUDIT")
    print("=" * 70)

    with db.session() as conn:
        # Check Snapshot #1 unchanged
        ds1_post = conn.execute("SELECT id, name, version, total_count, buggy_count, non_buggy_count FROM datasets WHERE id = 1").fetchone()
        assert dict(ds1_post) == ds1_dict, f"Dataset #1 was modified! Before: {ds1_dict}, After: {dict(ds1_post)}"
        print("[PASS] Dataset Snapshot #1 remains identical and untouched in database.")

        # Check Newtonsoft.Json quarantine
        nw_repo = conn.execute("SELECT * FROM repositories WHERE full_name LIKE '%Newtonsoft%'").fetchall()
        assert len(nw_repo) == 0, "VIOLATION: Newtonsoft.Json was touched in Phase 2!"
        print("[PASS] Newtonsoft.Json quarantine strictly maintained (0 records in database).")

        # Check Snapshot #2 observations by repo
        ds2_obs = conn.execute(
            """
            SELECT r.full_name, o.label, COUNT(*) as cnt
            FROM dataset_observations do
            JOIN observations o ON do.observation_id = o.id
            JOIN repositories r ON o.repository_id = r.id
            WHERE do.dataset_id = :did
            GROUP BY r.full_name, o.label
            ORDER BY r.full_name, o.label
            """,
            {"did": ds2_id}
        ).fetchall()
        print("\nDataset Snapshot #2 Composition by Repository & Label:")
        for r in ds2_obs:
            label_str = "Buggy (1)" if r["label"] == 1 else "Clean (0)"
            print(f"  - {r['full_name']}: {label_str} = {r['cnt']}")

        # Verify no test files in Dataset Snapshot #2
        ds2_files = conn.execute(
            """
            SELECT o.file_path
            FROM dataset_observations do
            JOIN observations o ON do.observation_id = o.id
            WHERE do.dataset_id = :did
            """,
            {"did": ds2_id}
        ).fetchall()
        leaked_tests = [f["file_path"] for f in ds2_files if not is_production_csharp_file(f["file_path"])]
        assert len(leaked_tests) == 0, f"VIOLATION: Found leaked test files in Dataset #2: {leaked_tests}"
        print(f"[PASS] Zero test files detected in Dataset #2 ({len(ds2_files)} production methods verified).")

    # -----------------------------------------------------------------
    # Save Expansion Summary Artifact
    # -----------------------------------------------------------------
    total_elapsed = round(time.time() - start_time, 2)
    summary_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "expansion_duration_s": total_elapsed,
        "processed_repositories": results,
        "dataset_snapshot_1": ds1_dict,
        "dataset_snapshot_2": {
            "id": ds2_id,
            "name": "csharp_empirical_v2",
            "version": "2.0.0",
            "csv_path": str(ds2_export["csv_path"]),
            "metadata_path": str(ds2_export["metadata_path"]),
            "statistics": ds2_stats,
            "training_repositories": training_repo_names,
        },
    }

    reports_dir = PROJECT_ROOT / "reports" / "dataset_expansion"
    reports_dir.mkdir(parents=True, exist_ok=True)
    summary_path = reports_dir / "dataset_expansion_summary.json"
    summary_path.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
    print(f"\nExpansion summary artifact written to: {summary_path}")
    print(f"Phase 2 completed in {total_elapsed}s.")


if __name__ == "__main__":
    main()

