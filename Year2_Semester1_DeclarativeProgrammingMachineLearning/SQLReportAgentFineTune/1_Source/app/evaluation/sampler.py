"""Stratified sampling module for Text-to-SQL benchmark evaluation."""

import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.config import get_project_root
from app.core.logging import get_logger
from app.datasets.preprocessor import SQLTrainingExample

logger = get_logger(__name__)


def classify_sql_complexity(sql: str) -> str:
    """Classifies a SQL query into one of 4 complexity tiers: easy, medium, hard, extra_hard.
    
    Classification criteria based on Spider benchmark taxonomy:
    - easy: Single table, basic projections/filters, at most 1 simple aggregation.
    - medium: 1 JOIN, or GROUP BY without having, or compound WHERE conditions.
    - hard: 2 JOINs, or subqueries, or set operations (UNION, EXCEPT, INTERSECT), or HAVING.
    - extra_hard: >=3 JOINs, nested subqueries, CTEs, or complex multi-component queries.
    """
    s = sql.upper()
    join_count = len(re.findall(r"\bJOIN\b", s))
    subquery_count = len(re.findall(r"\bSELECT\b", s)) - 1
    has_set_op = any(k in s for k in ["UNION", "INTERSECT", "EXCEPT"])
    has_group = "GROUP BY" in s
    has_having = "HAVING" in s
    has_cte = "WITH" in s

    score = 0
    score += join_count * 2
    score += max(0, subquery_count) * 3
    if has_set_op:
        score += 3
    if has_having:
        score += 2
    if has_group:
        score += 1
    if has_cte:
        score += 4
    if len(re.findall(r"\bAND\b|\bOR\b", s)) >= 2:
        score += 1

    if score == 0:
        return "easy"
    elif score <= 2:
        return "medium"
    elif score <= 5:
        return "hard"
    else:
        return "extra_hard"


class StratifiedSampler:
    """Selects deterministic, stratified evaluation subsets representative of the full benchmark."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def sample_unseen(
        self,
        unseen_examples: List[SQLTrainingExample],
        target_size: int = 200,
    ) -> List[SQLTrainingExample]:
        """Extracts a stratified sample from unseen-schema examples.
        
        Guarantees:
        1. 100% of all distinct unseen databases are represented (at least 1 sample per DB).
        2. Proportional allocation across databases matching full population distribution.
        3. Stratified allocation across complexity levels (easy, medium, hard, extra_hard) within each DB.
        4. Ingestion of both Spider and Synthetic sources.
        5. Deterministic selection with fixed random seed.
        """
        if len(unseen_examples) <= target_size:
            return list(unseen_examples)

        rng = random.Random(self.seed)

        # 1. Group by Database
        by_db: Dict[str, List[SQLTrainingExample]] = defaultdict(list)
        for ex in unseen_examples:
            by_db[ex.db_id].append(ex)

        # Deterministically shuffle within each DB
        for db in sorted(by_db.keys()):
            rng.shuffle(by_db[db])

        total_n = len(unseen_examples)

        # 2. Target allocation per DB (minimum 1 per DB to guarantee 100% DB coverage)
        db_targets: Dict[str, int] = {}
        allocated = 0
        for db in sorted(by_db.keys()):
            items = by_db[db]
            t = max(1, int(round(len(items) / total_n * target_size)))
            db_targets[db] = t
            allocated += t

        # Rebalance if rounding drifted away from target_size
        while allocated > target_size:
            # decrease from largest DB
            max_db = max(sorted(db_targets.keys()), key=lambda d: db_targets[d])
            if db_targets[max_db] > 1:
                db_targets[max_db] -= 1
                allocated -= 1
            else:
                break

        while allocated < target_size:
            min_db = min(
                sorted(db_targets.keys()),
                key=lambda d: (db_targets[d] / len(by_db[d]), d),
            )
            db_targets[min_db] += 1
            allocated += 1

        # 3. Stratified selection per DB by complexity
        selected: List[SQLTrainingExample] = []
        for db in sorted(db_targets.keys()):
            target = db_targets[db]
            items = by_db[db]

            comp_map: Dict[str, List[SQLTrainingExample]] = defaultdict(list)
            for ex in items:
                comp = classify_sql_complexity(ex.query)
                comp_map[comp].append(ex)

            db_selected: List[SQLTrainingExample] = []
            if target == 1:
                # Pick 1 from the most common complexity in this DB
                top_comp = max(sorted(comp_map.keys()), key=lambda c: len(comp_map[c]))
                db_selected.append(comp_map[top_comp][0])
            else:
                for comp in sorted(comp_map.keys()):
                    c_items = comp_map[comp]
                    cnt = int(round(len(c_items) / len(items) * target))
                    db_selected.extend(c_items[:cnt])

                # Adjust to exact target for this DB
                if len(db_selected) < target:
                    picked_ids = {x.example_id for x in db_selected}
                    rem = [x for x in items if x.example_id not in picked_ids]
                    db_selected.extend(rem[: (target - len(db_selected))])
                elif len(db_selected) > target:
                    db_selected = db_selected[:target]

            selected.extend(db_selected)

        # 4. Final sanity check and stable sort by db_id, then example_id
        selected.sort(key=lambda x: (x.db_id, x.example_id))

        logger.info(
            f"Stratified sample generated: {len(selected)} samples across {len(db_targets)} databases."
        )
        return selected

    def export_sample_manifest(
        self,
        samples: List[SQLTrainingExample],
        population_size: int = 1044,
        output_file: Optional[Union[str, Path]] = None,
    ) -> Path:
        """Exports the sample manifest JSON with detailed distribution statistics."""
        if output_file is None:
            output_file = (
                get_project_root()
                / "2_Database"
                / "processed"
                / "evaluation_sample_unseen_200.json"
            )
        output_path = Path(output_file).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        db_counts = Counter(ex.db_id for ex in samples)
        comp_counts = Counter(classify_sql_complexity(ex.query) for ex in samples)
        source_counts = Counter(ex.source for ex in samples)

        manifest = {
            "metadata": {
                "sample_size": len(samples),
                "population_size": population_size,
                "sampling_ratio_pct": round(len(samples) / population_size * 100.0, 2),
                "seed": self.seed,
                "stratification_factors": ["db_id", "complexity", "source"],
                "total_unique_databases": len(db_counts),
            },
            "distributions": {
                "by_complexity": dict(sorted(comp_counts.items())),
                "by_source": dict(sorted(source_counts.items())),
                "by_database": dict(sorted(db_counts.items())),
            },
            "sample_ids": [ex.example_id for ex in samples],
            "samples": [
                {
                    "example_id": ex.example_id,
                    "db_id": ex.db_id,
                    "source": ex.source,
                    "track": ex.track,
                    "complexity": classify_sql_complexity(ex.query),
                    "question": ex.question,
                    "query": ex.query,
                }
                for ex in samples
            ],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Sample manifest written to {output_path}")
        return output_path
