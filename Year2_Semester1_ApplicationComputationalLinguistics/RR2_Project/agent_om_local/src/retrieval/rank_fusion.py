"""Reciprocal Rank Fusion (RRF) module reproducing Agent-OM ranking logic."""

from __future__ import annotations

import collections
import itertools
from typing import Any, Dict, List, Sequence, Tuple


def reciprocal_rank_fusion(
    *rankings: Sequence[Any],
    k: int = 0,
    exclude_items: Sequence[Any] | None = None,
) -> List[Tuple[float, List[Any]]]:
    """
    Computes Reciprocal Rank Fusion over multiple ranking lists.
    
    Faithful reproduction of om_database_matching.py's
    reciprocal_rank_fusion_all_with_grouped_scores_exclude_none.
    
    Args:
        *rankings: Arbitrary number of ranking sequences (e.g., [cand1, cand2, cand3]).
        k: The RRF smoothing constant. Original Agent-OM uses k = 0 (1 / position).
           Standard academic IR RRF uses k = 60.
        exclude_items: Items to ignore (e.g. ['Entity-Dummy'] or null placeholders).
        
    Returns:
        List of tuples: [(score, [item1, item2, ...]), ...] grouped by score in
        descending order, with items of identical score sorted lexicographically.
    """
    excluded = set(exclude_items) if exclude_items is not None else set()
    reciprocal_ranks: Dict[Any, float] = collections.defaultdict(float)

    for ranking in rankings:
        if ranking is None:
            continue
        if not isinstance(ranking, (list, tuple)):
            ranking = [ranking]
            
        position = 1
        for item in ranking:
            if item in excluded or item is None:
                continue
            reciprocal_ranks[item] += 1.0 / (k + position)
            position += 1

    if not reciprocal_ranks:
        return []

    # Sort primarily by score (descending), tie-broken by item name (ascending)
    fused_ranking_with_scores = sorted(
        reciprocal_ranks.items(),
        key=lambda x: (-x[1], str(x[0]))
    )

    # Group items sharing the identical fused score
    grouped_items_by_score = [
        (score, [item for item, _ in items])
        for score, items in itertools.groupby(fused_ranking_with_scores, key=lambda x: x[1])
    ]

    return grouped_items_by_score

