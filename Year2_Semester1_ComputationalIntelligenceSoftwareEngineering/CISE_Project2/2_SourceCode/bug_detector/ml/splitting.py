"""Repository-grouped, pair-preserving, zero-leakage dataset partitioning."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold


def build_repository_splits(
    records: list[dict[str, Any]],
    independent_test_fraction: float = 0.22,
    temporal_test_fraction: float = 0.25,
    random_state: int = 42,
) -> dict[str, list[dict[str, Any]]]:
    """
    Partition dataset records into strict repository-isolated sets:
      - hard_negative_test: records pre-assigned to 'hard_negative_test' (disjoint repos)
      - independent_test: untouched holdout repositories stratified across sources/labels
      - dev: training + nested grouped CV repositories
      - temporal_train / temporal_test: chronological repository-separated split over dated commits
    """
    hard_neg_test = [r for r in records if r.get("split_partition") == "hard_negative_test"]
    hn_repos = {r["repository_id"] for r in hard_neg_test}

    pool = [r for r in records if r["repository_id"] not in hn_repos]
    pool_repos = sorted({r["repository_id"] for r in pool})

    # Compute per-repo stats for stratified repo selection
    repo_stats: dict[str, dict[str, Any]] = {}
    for rid in pool_repos:
        r_recs = [r for r in pool if r["repository_id"] == rid]
        n_bug = sum(1 for r in r_recs if int(r["label"]) == 1)
        origins = sorted({str(r.get("label_source", "")) for r in r_recs})
        primary_origin = "inferredbugs" if any("inferredbugs" in o for o in origins) else (
            "github_bugfix" if any("github" in o for o in origins) else "hard_negative"
        )
        repo_stats[rid] = {
            "count": len(r_recs),
            "bug_count": n_bug,
            "origin": primary_origin,
        }

    # Group pool repositories by origin and sort deterministically before selecting test repos
    rng = np.random.default_rng(random_state)
    test_repos: set[str] = set()
    by_origin: dict[str, list[str]] = defaultdict(list)
    for rid in pool_repos:
        by_origin[repo_stats[rid]["origin"]].append(rid)

    for origin, rids in sorted(by_origin.items()):
        shuffled = list(rids)
        rng.shuffle(shuffled)
        n_test = max(1, int(round(len(shuffled) * independent_test_fraction))) if len(shuffled) >= 3 else 0
        test_repos.update(shuffled[:n_test])

    dev = [r for r in pool if r["repository_id"] not in test_repos]
    independent_test = [r for r in pool if r["repository_id"] in test_repos]

    for r in dev:
        r["split_partition"] = "dev"
    for r in independent_test:
        r["split_partition"] = "independent_test"

    # Temporal evaluation split across dated GitHub repositories (repository-grouped)
    dated_repos: dict[str, str] = {}
    for r in pool:
        ts = r.get("commit_timestamp")
        if ts:
            rid = r["repository_id"]
            if rid not in dated_repos or str(ts) > dated_repos[rid]:
                dated_repos[rid] = str(ts)

    temporal_train: list[dict[str, Any]] = []
    temporal_test: list[dict[str, Any]] = []
    if len(dated_repos) >= 6:
        ordered_dated = sorted(dated_repos.items(), key=lambda kv: kv[1])
        cutoff = max(2, int(round(len(ordered_dated) * (1.0 - temporal_test_fraction))))
        t_train_repos = {rid for rid, _ in ordered_dated[:cutoff]}
        t_test_repos = {rid for rid, _ in ordered_dated[cutoff:]}
        temporal_train = [r for r in pool if r["repository_id"] in t_train_repos]
        temporal_test = [r for r in pool if r["repository_id"] in t_test_repos]

    splits = {
        "dev": dev,
        "independent_test": independent_test,
        "hard_negative_test": hard_neg_test,
        "temporal_train": temporal_train,
        "temporal_test": temporal_test,
    }
    verify_zero_leakage(dev, independent_test, hard_neg_test)
    return splits


def verify_zero_leakage(
    dev: list[dict[str, Any]],
    independent_test: list[dict[str, Any]],
    hard_negative_test: list[dict[str, Any]],
) -> None:
    """Assert zero overlap of repositories, pair_ids, and source_hashes across partitions."""
    partitions = {
        "dev": dev,
        "independent_test": independent_test,
        "hard_negative_test": hard_negative_test,
    }
    names = list(partitions.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a_name, b_name = names[i], names[j]
            a_recs, b_recs = partitions[a_name], partitions[b_name]

            a_repos = {r["repository_id"] for r in a_recs}
            b_repos = {r["repository_id"] for r in b_recs}
            repo_overlap = a_repos & b_repos
            if repo_overlap:
                raise AssertionError(f"Repository leakage between {a_name} and {b_name}: {sorted(repo_overlap)[:5]}")

            a_pairs = {r["pair_id"] for r in a_recs if r.get("pair_id")}
            b_pairs = {r["pair_id"] for r in b_recs if r.get("pair_id")}
            pair_overlap = a_pairs & b_pairs
            if pair_overlap:
                raise AssertionError(f"Bug-fix pair leakage between {a_name} and {b_name}: {sorted(pair_overlap)[:5]}")

            a_hashes = {r["source_hash"] for r in a_recs if r.get("source_hash")}
            b_hashes = {r["source_hash"] for r in b_recs if r.get("source_hash")}
            hash_overlap = a_hashes & b_hashes
            if hash_overlap:
                raise AssertionError(
                    f"Normalized source_hash leakage between {a_name} and {b_name}: {len(hash_overlap)} shared hashes"
                )


def make_grouped_cv_splits(
    records: list[dict[str, Any]],
    n_splits: int = 5,
    random_state: int = 42,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Create StratifiedGroupKFold indices grouped strictly by repository_id."""
    y = np.array([int(r["label"]) for r in records], dtype=int)
    groups = np.array([str(r["repository_id"]) for r in records])
    unique_groups = len(np.unique(groups))
    effective_splits = min(n_splits, max(2, unique_groups))
    cv = StratifiedGroupKFold(n_splits=effective_splits, shuffle=True, random_state=random_state)
    return list(cv.split(np.zeros(len(y)), y, groups))
