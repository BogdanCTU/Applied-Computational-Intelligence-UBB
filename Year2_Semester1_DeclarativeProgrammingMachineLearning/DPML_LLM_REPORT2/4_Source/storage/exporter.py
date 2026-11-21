"""Multi-format exporter (JSONL, JSON, CSV, Parquet) for research tables."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

import jsonlines
import pandas as pd
from sqlalchemy import text

from source.config.settings import get_project_root
from source.storage.database import DatabaseManager


class DataExporter:
    """Exports SQLite tables and structured records to JSONL, JSON, CSV, and Parquet."""

    def __init__(self, db: DatabaseManager, export_dir: Optional[str | Path] = None):
        self.db = db
        root = get_project_root()
        target = Path(export_dir) if export_dir else root / "5_Data" / "exports"
        self.export_dir = target if target.is_absolute() else root / target
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_records(
        self,
        name: str,
        records: list[dict],
        formats: Iterable[str] = ("jsonl", "json", "csv", "parquet"),
    ) -> dict[str, Path]:
        """Export a list of dictionaries to requested formats."""
        outputs: dict[str, Path] = {}
        fmt_set = {f.lower() for f in formats}

        if "json" in fmt_set:
            p = self.export_dir / f"{name}.json"
            p.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")
            outputs["json"] = p

        if "jsonl" in fmt_set:
            p = self.export_dir / f"{name}.jsonl"
            with jsonlines.open(p, mode="w") as writer:
                for row in records:
                    writer.write(json.loads(json.dumps(row, default=str)))
            outputs["jsonl"] = p

        df = pd.DataFrame(records)
        if "csv" in fmt_set:
            p = self.export_dir / f"{name}.csv"
            df.to_csv(p, index=False)
            outputs["csv"] = p

        if "parquet" in fmt_set:
            p = self.export_dir / f"{name}.parquet"
            if df.empty:
                df = pd.DataFrame({"_empty": pd.Series(dtype="string")})
            df.to_parquet(p, index=False)
            outputs["parquet"] = p

        return outputs

    def export_table(
        self,
        table_name: str,
        formats: Iterable[str] = ("jsonl", "json", "csv", "parquet"),
    ) -> dict[str, Path]:
        """Export an entire SQLite table by name."""
        with self.db.engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table_name}"))
            columns = list(result.keys())
            records = [dict(zip(columns, row)) for row in result.fetchall()]
        return self.export_records(table_name, records, formats=formats)
