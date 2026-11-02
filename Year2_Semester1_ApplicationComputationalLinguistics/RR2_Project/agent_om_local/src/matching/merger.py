"""Reciprocal matching merger reproducing Agent-OM strict bidirectional intersection."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set, Tuple


class ReciprocalMerger:
    """
    Computes strict reciprocal intersection between directional alignments.
    
    Reproduces merge() in om_database_matching.py:
    df_merge = pd.merge(df_source, df_target, on=['Entity1', 'Entity2'])
    """

    @staticmethod
    def normalize_pairs(
        pairs: Iterable[Tuple[str, str]],
        assumed_orientation: str = "Source->Target",
    ) -> Set[Tuple[str, str]]:
        """
        Ensures all pairs are canonicalized into (Source_URI, Target_URI) orientation.
        If assumed_orientation == 'Target->Source', swaps (Target, Source) to (Source, Target).
        """
        canonical: Set[Tuple[str, str]] = set()
        for a, b in pairs:
            if assumed_orientation == "Target->Source":
                canonical.add((b, a))
            else:
                canonical.add((a, b))
        return canonical

    def merge_alignments(
        self,
        source_to_target_pairs: Iterable[Tuple[str, str]],
        target_to_source_pairs: Iterable[Tuple[str, str]],
        target_to_source_is_reversed: bool = False,
    ) -> Set[Tuple[str, str]]:
        r"""
        Executes strict set intersection:
        M = M_{Source->Target} \cap M_{Target->Source}
        
        Only pairs confirmed in BOTH directions survive.
        """
        s2t = set(source_to_target_pairs)
        if target_to_source_is_reversed:
            t2s = self.normalize_pairs(target_to_source_pairs, assumed_orientation="Target->Source")
        else:
            t2s = set(target_to_source_pairs)

        return s2t.intersection(t2s)

    def analyze_merger(
        self,
        source_to_target_pairs: Iterable[Tuple[str, str]],
        target_to_source_pairs: Iterable[Tuple[str, str]],
        target_to_source_is_reversed: bool = False,
    ) -> Dict[str, Any]:
        """
        Detailed breakdown of reciprocal intersection including retained and dropped pairs.
        """
        s2t = set(source_to_target_pairs)
        if target_to_source_is_reversed:
            t2s = self.normalize_pairs(target_to_source_pairs, assumed_orientation="Target->Source")
        else:
            t2s = set(target_to_source_pairs)

        merged = s2t.intersection(t2s)
        dropped_s2t = s2t - t2s
        dropped_t2s = t2s - s2t

        return {
            "source_to_target_count": len(s2t),
            "target_to_source_count": len(t2s),
            "merged_count": len(merged),
            "merged_pairs": sorted(list(merged)),
            "dropped_from_source_count": len(dropped_s2t),
            "dropped_from_source_pairs": sorted(list(dropped_s2t)),
            "dropped_from_target_count": len(dropped_t2s),
            "dropped_from_target_pairs": sorted(list(dropped_t2s)),
        }
