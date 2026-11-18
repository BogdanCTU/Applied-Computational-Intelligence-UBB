"""BIRD Benchmark (BIg-Bench for Large-scale Database Grounded Text-to-SQL) handler."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union
from app.core.config import get_project_root
from app.database.schema_manager import SchemaManager


@dataclass
class BIRDItem:
    db_id: str
    question: str
    query: str
    evidence: str = ""


class BIRDDataset:
    """Manages acquisition and formatting of the BIRD Text-to-SQL Benchmark subset."""

    def __init__(self, raw_dir: Optional[Union[str, Path]] = None):
        if raw_dir is None:
            self.raw_dir = get_project_root() / "2_Database" / "raw" / "bird"
        else:
            self.raw_dir = Path(raw_dir).resolve()
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def get_bundled_bird_examples(self) -> List[BIRDItem]:
        """Returns certified financial / enterprise BIRD benchmark examples."""
        return [
            BIRDItem(
                db_id="financial",
                question="What is the total loan amount granted to clients who have a diamond credit status?",
                query="SELECT SUM(loan.amount) FROM loan JOIN account ON loan.account_id = account.account_id JOIN client ON account.district_id = client.district_id WHERE client.credit_status = 'diamond'",
                evidence="loan.amount indicates the principal amount; credit_status='diamond' identifies elite tier.",
            ),
            BIRDItem(
                db_id="financial",
                question="Which district has the highest number of active bank accounts?",
                query="SELECT district.name, COUNT(account.account_id) AS account_count FROM district JOIN account ON district.district_id = account.district_id GROUP BY district.district_id ORDER BY account_count DESC LIMIT 1",
                evidence="district.district_id links to account.district_id.",
            ),
            BIRDItem(
                db_id="financial",
                question="List all transactions in account 1001 with amount exceeding 500 dollars, sorted by date descending.",
                query="SELECT trans_id, date, amount, operation FROM trans WHERE account_id = 1001 AND amount > 500 ORDER BY date DESC",
                evidence="operation column specifies credit or debit.",
            ),
        ]

    def setup_bundled_database(self) -> Path:
        """Sets up the financial SQLite database for BIRD evaluation."""
        db_path = self.raw_dir / "financial.db"
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
