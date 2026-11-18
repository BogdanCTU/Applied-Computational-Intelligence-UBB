"""BIRD Benchmark (BIg-Bench for Large-scale Database Grounded Text-to-SQL) loader."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from app.core.config import get_project_root
from app.core.logging import get_logger
from app.database.schema_manager import SchemaManager

logger = get_logger(__name__)


@dataclass
class BIRDRecord:
    db_id: str
    question: str
    query: str
    evidence: str
    difficulty: str


class BIRDDataset:
    """Manages acquisition and formatting of the BIRD Benchmark subset."""

    def __init__(self, raw_dir: Optional[Union[str, Path]] = None):
        if raw_dir is None:
            self.raw_dir = get_project_root() / "2_Database" / "raw" / "bird"
        else:
            self.raw_dir = Path(raw_dir).resolve()

    def is_available(self) -> bool:
        """Checks if BIRD raw files exist."""
        return (self.raw_dir / "mini_dev_sqlite.jsonl").exists()

    def load_mini_dev_records(self, limit: Optional[int] = None) -> List[BIRDRecord]:
        """Loads records from mini_dev_sqlite.jsonl."""
        fpath = self.raw_dir / "mini_dev_sqlite.jsonl"
        if not fpath.exists():
            return []
        records = []
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                records.append(
                    BIRDRecord(
                        db_id=item.get("db_id", "unknown"),
                        question=item.get("question", ""),
                        query=item.get("SQL", ""),
                        evidence=item.get("evidence", ""),
                        difficulty=item.get("difficulty", "medium"),
                    )
                )
        return records[:limit] if limit else records

    def setup_financial_database(self) -> Path:
        """Sets up the financial SQLite database for BIRD evaluation."""
        db_path = self.raw_dir / "financial.db"
        if db_path.exists():
            return db_path
        ddl = """
        CREATE TABLE district (
            district_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            region TEXT NOT NULL
        );
        CREATE TABLE client (
            client_id INTEGER PRIMARY KEY,
            district_id INTEGER NOT NULL,
            credit_status TEXT NOT NULL,
            birth_date TEXT NOT NULL,
            FOREIGN KEY (district_id) REFERENCES district(district_id)
        );
        CREATE TABLE account (
            account_id INTEGER PRIMARY KEY,
            district_id INTEGER NOT NULL,
            created_date TEXT NOT NULL,
            account_type TEXT NOT NULL,
            FOREIGN KEY (district_id) REFERENCES district(district_id)
        );
        CREATE TABLE loan (
            loan_id INTEGER PRIMARY KEY,
            account_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            duration INTEGER NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES account(account_id)
        );
        CREATE TABLE trans (
            trans_id INTEGER PRIMARY KEY,
            account_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            operation TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES account(account_id)
        );
        """
        data = """
        INSERT INTO district VALUES (1, 'Downtown Metro', 'Central'), (2, 'North Suburbs', 'North'), (3, 'Harbor District', 'South');
        INSERT INTO client VALUES 
            (10, 1, 'diamond', '1975-04-12'),
            (20, 2, 'standard', '1988-11-23'),
            (30, 1, 'diamond', '1992-02-18');
        INSERT INTO account VALUES 
            (1001, 1, '2020-01-10', 'savings'),
            (1002, 1, '2021-06-15', 'checking'),
            (1003, 2, '2022-03-20', 'checking');
        INSERT INTO loan VALUES 
            (501, 1001, 25000.0, 36, 'active'),
            (502, 1003, 10000.0, 24, 'active');
        INSERT INTO trans VALUES 
            (9001, 1001, '2024-01-05', 1200.0, 'credit'),
            (9002, 1001, '2024-01-12', 350.0, 'debit'),
            (9003, 1001, '2024-02-01', 800.0, 'credit');
        """
        return SchemaManager.create_database_from_ddl(db_path, ddl, data)
