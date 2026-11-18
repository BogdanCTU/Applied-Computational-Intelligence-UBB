"""Full Spider Benchmark (Yale) loader, schema parser, and database linker."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from app.core.config import get_project_root
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SpiderRecord:
    db_id: str
    question: str
    query: str
    split: str  # 'train' or 'dev'


class SpiderDataset:
    """Manages the official Yale Spider Text-to-SQL Benchmark and its SQLite databases."""

    def __init__(self, raw_dir: Optional[Union[str, Path]] = None):
        if raw_dir is None:
            self.raw_dir = get_project_root() / "2_Database" / "raw" / "spider"
        else:
            self.raw_dir = Path(raw_dir).resolve()

        self.spider_data_dir = self.raw_dir / "spider_data"
        self.db_dir = self.spider_data_dir / "database"

    def is_available(self) -> bool:
        """Checks if the official Spider files exist locally."""
        train_file = self.spider_data_dir / "train_spider.json"
        dev_file = self.spider_data_dir / "dev.json"
        return train_file.exists() and dev_file.exists() and self.db_dir.exists()

    def get_database_path(self, db_id: str) -> Optional[Path]:
        """Locates the SQLite database file for a given db_id."""
        sqlite_file = self.db_dir / db_id / f"{db_id}.sqlite"
        if sqlite_file.exists():
            return sqlite_file
        # Check fallback extension
        db_file = self.db_dir / db_id / f"{db_id}.db"
        if db_file.exists():
            return db_file
        return None

    def load_train_records(self, limit: Optional[int] = None) -> List[SpiderRecord]:
        """Loads official Spider training records."""
        train_file = self.spider_data_dir / "train_spider.json"
        if not train_file.exists():
            return []
        with open(train_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = [
            SpiderRecord(
                db_id=item["db_id"],
                question=item["question"],
                query=item["query"],
                split="train",
            )
            for item in data
        ]
        return records[:limit] if limit else records

    def load_dev_records(self, limit: Optional[int] = None) -> List[SpiderRecord]:
        """Loads official Spider held-out development records (20 unseen databases)."""
        dev_file = self.spider_data_dir / "dev.json"
        if not dev_file.exists():
            return []
        with open(dev_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = [
            SpiderRecord(
                db_id=item["db_id"],
                question=item["question"],
                query=item["query"],
                split="dev",
            )
            for item in data
        ]
        return records[:limit] if limit else records

    def get_available_database_map(self) -> Dict[str, Path]:
        """Maps all db_ids to their verified SQLite database files."""
        db_map = {}
        if self.db_dir.exists():
            for sub in self.db_dir.iterdir():
                if sub.is_dir():
                    candidate = sub / f"{sub.name}.sqlite"
                    if candidate.exists():
                        db_map[sub.name] = candidate
        return db_map
