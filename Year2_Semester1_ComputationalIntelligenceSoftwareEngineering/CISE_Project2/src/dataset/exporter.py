"""Dataset Exporter module for saving versioned CSV datasets and provenance metadata."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd

from src.database.repository import RepositoryDB
from src.dataset.dataset_builder import DatasetBuilder
from src.utils.logger import setup_logger

logger = setup_logger("exporter")


class DatasetExporter:
    """Exports dataset snapshots to reproducible CSV files and metadata JSON companions."""

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
    ) -> Dict[str, Any]:
        """Export dataset snapshot to CSV with companion metadata JSON."""
        ds = self.db.get_dataset(dataset_id)
        if not ds:
            raise ValueError(f"Dataset #{dataset_id} does not exist.")

        name = ds["name"]
        version = ds["version"]
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

        feature_names = json.loads(ds["feature_names"]) if ds.get("feature_names") else []
        stats = self.builder.compute_dataset_statistics(dataset_id, feature_names)

        metadata = {
            "dataset_id": dataset_id,
            "name": name,
            "version": version,
            "description": ds.get("description"),
            "created_at": ds.get("created_at"),
            "total_observations": len(df),
            "feature_names": feature_names,
            "feature_count": len(feature_names),
            "statistics": stats,
            "csv_path": str(csv_file),
        }

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Exported dataset #{dataset_id} to {csv_file} and metadata to {meta_file}.")
        return {
            "csv_path": str(csv_file),
            "metadata_path": str(meta_file),
            "rows_exported": len(df),
            "columns_exported": len(df.columns),
        }

