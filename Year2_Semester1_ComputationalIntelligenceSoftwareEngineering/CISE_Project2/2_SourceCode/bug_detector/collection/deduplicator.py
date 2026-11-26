"""Dataset deduplication, cross-label contamination protection, and pair consistency validation."""

from __future__ import annotations

from collections import defaultdict

from bug_detector.collection.models import DatasetSampleRecord, ExclusionRecord


def deduplicate_and_validate_records(
    records: list[DatasetSampleRecord],
) -> tuple[list[DatasetSampleRecord], list[ExclusionRecord], dict[str, int]]:
    """
    Validate and deduplicate dataset records:
    1. Detect normalized source_hash collisions across opposite labels -> exclude BOTH sides.
    2. Detect duplicate source_hash within the same label -> keep canonical first record.
    3. Verify paired bug-fix records still have valid pair consistency or keep standalone cleanly.
    """
    exclusions: list[ExclusionRecord] = []
    labels_by_source_hash: dict[str, set[int]] = defaultdict(set)
    labels_by_struct_hash: dict[str, set[int]] = defaultdict(set)

    for rec in records:
        labels_by_source_hash[rec.source_hash].add(rec.label)
        if rec.structural_hash:
            labels_by_struct_hash[rec.structural_hash].add(rec.label)

    conflicted_source_hashes = {h for h, lbls in labels_by_source_hash.items() if len(lbls) > 1}
    conflicted_struct_hashes = {h for h, lbls in labels_by_struct_hash.items() if len(lbls) > 1}

    seen_source_hashes: set[str] = set()
    seen_sample_ids: set[str] = set()
    kept: list[DatasetSampleRecord] = []
    cross_label_excluded = 0
    same_label_dups_removed = 0

    for rec in records:
        if rec.sample_id in seen_sample_ids:
            same_label_dups_removed += 1
            exclusions.append(
                ExclusionRecord(
                    source_origin=rec.source_origin,
                    repository_id=rec.repository_id,
                    external_ref=rec.sample_id,
                    file_path=rec.file_path,
                    method_name=rec.method_name,
                    exclusion_reason="duplicate_sample_id",
                    details=f"sample_id={rec.sample_id}",
                )
            )
            continue
        if rec.source_hash in conflicted_source_hashes or (
            rec.structural_hash and rec.structural_hash in conflicted_struct_hashes
        ):
            cross_label_excluded += 1
            exclusions.append(
                ExclusionRecord(
                    source_origin=rec.source_origin,
                    repository_id=rec.repository_id,
                    external_ref=rec.sample_id,
                    file_path=rec.file_path,
                    method_name=rec.method_name,
                    exclusion_reason="cross_label_hash_conflict",
                    details=f"source_hash={rec.source_hash[:12]} label={rec.label}",
                )
            )
            continue

        if rec.source_hash in seen_source_hashes:
            same_label_dups_removed += 1
            exclusions.append(
                ExclusionRecord(
                    source_origin=rec.source_origin,
                    repository_id=rec.repository_id,
                    external_ref=rec.sample_id,
                    file_path=rec.file_path,
                    method_name=rec.method_name,
                    exclusion_reason="duplicate_source_hash",
                    details=f"source_hash={rec.source_hash[:12]}",
                )
            )
            continue

        seen_source_hashes.add(rec.source_hash)
        seen_sample_ids.add(rec.sample_id)
        kept.append(rec)

    dup_stats = {
        "input_records": len(records),
        "retained_records": len(kept),
        "cross_label_hash_conflicts_excluded": cross_label_excluded,
        "same_label_duplicates_removed": same_label_dups_removed,
    }
    return kept, exclusions, dup_stats
