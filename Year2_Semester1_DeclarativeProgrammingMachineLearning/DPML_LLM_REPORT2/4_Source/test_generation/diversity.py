"""Diversity, duplication, entropy, and semantic similarity metrics for generated test suites."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from source.test_generation.generator import TestCaseSpec
from source.utils.hashing import sha256_text


def _shannon_entropy(counts: List[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    ent = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            ent -= p * math.log2(p)
    return round(ent, 4)


def compute_diversity_report(cases: List[TestCaseSpec | Dict[str, Any]], output_path: Optional[Path] = None) -> Dict[str, Any]:
    """Verify unique IDs, detect duplicates, verify disjoint splits, and measure semantic diversity."""
    dicts = [c if isinstance(c, dict) else c.__dict__ for c in cases]
    test_ids = [d["test_id"] for d in dicts]
    unique_ids = len(set(test_ids))
    duplicate_ids = len(test_ids) - unique_ids

    prompts = ["\n".join(m["content"] for m in d["conversation"]) for d in dicts]
    prompt_hashes = [sha256_text(p.strip().lower()) for p in prompts]
    duplicate_prompts = len(prompt_hashes) - len(set(prompt_hashes))

    # Check template_family split isolation (no family should appear in >1 split)
    family_splits: Dict[str, set[str]] = {}
    for d in dicts:
        family_splits.setdefault(d["template_family"], set()).add(d["split"])
    leaked_families = [fam for fam, sp in family_splits.items() if len(sp) > 1]

    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for d in dicts:
        by_category.setdefault(d["category"], []).append(d)

    category_stats: Dict[str, Any] = {}
    for cat_id, items in sorted(by_category.items()):
        cat_prompts = ["\n".join(m["content"] for m in x["conversation"]) for x in items]
        sub_counts = Counter(x["subcategory"] for x in items)
        pat_counts = Counter(x["attack_pattern"] for x in items)
        sev_counts = Counter(x["severity"] for x in items)
        split_counts = Counter(x["split"] for x in items)

        # Pairwise TF-IDF cosine similarity (excluding diagonal)
        mean_sim = 0.0
        max_sim = 0.0
        if len(cat_prompts) >= 2:
            vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
            mat = vec.fit_transform(cat_prompts)
            sim = cosine_similarity(mat)
            np.fill_diagonal(sim, 0.0)
            n = len(cat_prompts)
            upper_vals = sim[np.triu_indices(n, k=1)]
            if len(upper_vals) > 0:
                mean_sim = round(float(np.mean(upper_vals)), 4)
                max_sim = round(float(np.max(upper_vals)), 4)

        category_stats[cat_id] = {
            "count": len(items),
            "unique_subcategories": len(sub_counts),
            "unique_attack_patterns": len(pat_counts),
            "subcategory_entropy_bits": _shannon_entropy(list(sub_counts.values())),
            "pattern_entropy_bits": _shannon_entropy(list(pat_counts.values())),
            "severity_distribution": dict(sev_counts),
            "split_distribution": dict(split_counts),
            "mean_pairwise_tfidf_similarity": mean_sim,
            "max_pairwise_tfidf_similarity": max_sim,
        }

    report = {
        "total_cases": len(dicts),
        "unique_test_ids": unique_ids,
        "duplicate_test_ids": duplicate_ids,
        "duplicate_prompts": duplicate_prompts,
        "template_family_leakage_count": len(leaked_families),
        "leaked_families": leaked_families,
        "category_count": len(by_category),
        "categories": category_stats,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report
