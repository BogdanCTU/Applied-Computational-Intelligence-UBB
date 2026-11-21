"""Dataset Exporter module for saving versioned CSV datasets, metadata, and SHA-256 manifests."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from database.repository import RepositoryDB
from services.dataset.dataset_builder import CLASS_FEATURE_DEFINITIONS, DatasetBuilder
from utils.logger import setup_logger

logger = setup_logger("exporter")


class DatasetExporter:
    """Exports dataset snapshots to reproducible CSV files, metadata JSONs, and manifests."""

    def __init__(self, db: RepositoryDB, exports_dir: Path | str) -> None:
        self.db = db
        self.exports_dir = Path(exports_dir)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.builder = DatasetBuilder(db)

    def export_to_csv(
        self,
        dataset_id: int,
        filename_prefix: Optional[str] = None,
        overwrite: bool = False,
        duplicate_analysis: Optional[Dict[str, Any]] = None,
        excluded_repositories: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Export dataset snapshot to CSV with companion metadata and manifest JSON."""
        ds = self.db.get_dataset(dataset_id)
        if not ds:
            raise ValueError(f"Dataset #{dataset_id} does not exist.")

        name = ds["name"]
        version = ds["version"]
        granularity = ds.get("granularity", "method")
        prefix = filename_prefix or f"{name}_v{version}"
        csv_file = self.exports_dir / f"{prefix}.csv"
        meta_file = self.exports_dir / f"{prefix}_metadata.json"

        if csv_file.exists() and not overwrite:
            raise FileExistsError(f"Export file {csv_file} already exists. Set overwrite=True to replace.")

        records = self.db.get_dataset_dataframe_records(dataset_id)
        if not records:
            raise ValueError(f"No records available in dataset #{dataset_id}")

        df = pd.DataFrame(records)
        df.to_csv(csv_file, index=False, encoding="utf-8")
        csv_sha256 = hashlib.sha256(csv_file.read_bytes()).hexdigest()

        feature_names = json.loads(ds["feature_names"]) if ds.get("feature_names") else []
        stats = self.builder.compute_dataset_statistics(dataset_id, feature_names)

        metadata = {
            "dataset_id": dataset_id,
            "name": name,
            "version": version,
            "granularity": granularity,
            "description": ds.get("description"),
            "created_at": ds.get("created_at"),
            "collection_date": datetime.now(timezone.utc).isoformat(),
            "repository_count": stats.get("repository_count", len(stats.get("repository_distribution", {}))),
            "total_observations": len(df),
            "positive_count": stats.get("buggy_count", 0),
            "negative_count": stats.get("clean_count", 0),
            "feature_names": feature_names,
            "feature_count": len(feature_names),
            "feature_schema_version": ds.get("feature_schema_version", "3.0.0" if granularity == "class" else "1.0.0"),
            "sha256_checksum": csv_sha256,
            "statistics": stats,
            "csv_path": str(csv_file),
        }

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        manifest_path_str: Optional[str] = None
        if granularity == "class":
            manifest_file = self.exports_dir / f"{prefix}_manifest.json"
            manifest = {
                "dataset_version": version,
                "dataset_name": name,
                "granularity": "class",
                "collection_date": datetime.now(timezone.utc).isoformat(),
                "repository_count": stats.get("repository_count", 0),
                "observation_count": len(df),
                "positive_count": stats.get("buggy_count", 0),
                "negative_count": stats.get("clean_count", 0),
                "positive_rate": stats.get("buggy_ratio", 0.0),
                "feature_count": len(feature_names),
                "feature_schema_version": ds.get("feature_schema_version", "3.0.0"),
                "feature_definitions": {
                    fname: CLASS_FEATURE_DEFINITIONS.get(fname, "Roslyn static class metric")
                    for fname in feature_names
                },
                "repository_distribution": stats.get("repository_distribution", {}),
                "labeling_methodology": {
                    "positive_label": (
                        "1 (Defect-prone class): Mapped via SZZ (git blame -w -M -C) from heuristic "
                        "bug-fixing commits on production C# files to the innermost enclosing class/struct/record "
                        "in the pre-fix parent revision."
                    ),
                    "negative_label": (
                        "0 (Candidate-clean class): Substantive production classes sampled from HEAD files "
                        "with zero recorded bug-fixing commits or SZZ traces in the mined commit window, "
                        "interpreted under the Open-World Assumption (not confirmed defect-free)."
                    ),
                    "leakage_and_filtering": (
                        "All test directories, test fixtures, build directories (bin/obj), and auto-generated "
                        "files are excluded via is_production_csharp_file()."
                    ),
                },
                "duplicate_analysis": duplicate_analysis or {},
                "exclusions": excluded_repositories or [],
                "sha256_checksum": csv_sha256,
                "csv_path": str(csv_file),
            }
            with open(manifest_file, "w", encoding="utf-8") as mf:
                json.dump(manifest, mf, indent=2)
            manifest_path_str = str(manifest_file)

        self.db.update_dataset_export_metadata(
            dataset_id=dataset_id,
            export_path=str(csv_file),
            manifest_path=manifest_path_str,
            sha256_checksum=csv_sha256,
        )

        logger.info(f"Exported dataset #{dataset_id} to {csv_file} (SHA-256: {csv_sha256[:12]}...).")
        return {
            "csv_path": str(csv_file),
            "metadata_path": str(meta_file),
            "manifest_path": manifest_path_str,
            "sha256_checksum": csv_sha256,
            "rows_exported": len(df),
            "columns_exported": len(df.columns),
        }
