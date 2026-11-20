"""Error-driven synthetic query generation for schema-grounded Text-to-SQL training."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.config import get_project_root
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GroundedSyntheticExample:
    example_id: str
    db_id: str
    question: str
    query: str
    target_failure_mode: str
    difficulty: str
    track: str = "track1_known"
    source: str = "synthetic_grounded"


class ErrorDrivenSyntheticGenerator:
    """Generates targeted, SQLite-validated synthetic Text-to-SQL examples addressing Phase I failure modes."""

    def __init__(self, synthetic_db_dir: Path):
        self.db_dir = synthetic_db_dir

    def generate_and_validate(self) -> List[GroundedSyntheticExample]:
        """Generates all targeted synthetic examples and validates execution on actual SQLite databases."""
        raw_candidates = self._define_targeted_candidates()
        validated: List[GroundedSyntheticExample] = []

        for cand in raw_candidates:
            db_path = self.db_dir / f"{cand.db_id}.db"
            if not db_path.exists():
                logger.warning(f"Synthetic DB not found: {db_path}")
                continue

            # Execute and validate query
            conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
            cursor = conn.cursor()
            try:
                cursor.execute(cand.query)
                rows = cursor.fetchall()
                if rows is not None:
                    validated.append(cand)
            except Exception as e:
                logger.error(f"Validation failed for {cand.example_id}: {e}")
            finally:
                conn.close()

        logger.info(f"Generated and validated {len(validated)}/{len(raw_candidates)} error-driven synthetic queries.")
        return validated

    def _define_targeted_candidates(self) -> List[GroundedSyntheticExample]:
        """Constructs curated examples explicitly designed to counter Phase I failure modes."""
        return [
            # -------------------------------------------------------------
            # Target 1: Minimal 2-Table Join (Resisting 4-5 Distractor Tables)
            # -------------------------------------------------------------
            GroundedSyntheticExample(
                example_id="synth_err_1",
                db_id="ecommerce",
                question="What is the department and category name for the product 'Wireless Mouse'?",
                query="SELECT c.department, c.category_name FROM products p JOIN categories c ON p.category_id = c.category_id WHERE p.product_name = 'Wireless Mouse';",
                target_failure_mode="unnecessary_multi_table_joins",
                difficulty="medium",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_2",
                db_id="ecommerce",
                question="List all product names and their category names in the Electronics department.",
                query="SELECT p.product_name, c.category_name FROM products p JOIN categories c ON p.category_id = c.category_id WHERE c.department = 'Electronics';",
                target_failure_mode="unnecessary_multi_table_joins",
                difficulty="medium",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_3",
                db_id="ecommerce",
                question="Find the customer name and order date for all orders that are completed.",
                query="SELECT c.customer_name, o.order_date FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE o.order_status = 'completed';",
                target_failure_mode="unnecessary_multi_table_joins",
                difficulty="medium",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_4",
                db_id="finance",
                question="What is the branch name and city for account number 101?",
                query="SELECT b.branch_name, b.city FROM accounts a JOIN branches b ON a.branch_id = b.branch_id WHERE a.account_id = 101;",
                target_failure_mode="unnecessary_multi_table_joins",
                difficulty="medium",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_5",
                db_id="healthcare",
                question="What is the doctor name and department name for doctors with a salary over 150000?",
                query="SELECT d.doctor_name, dep.dept_name FROM doctors d JOIN departments dep ON d.dept_id = dep.dept_id WHERE d.salary > 150000;",
                target_failure_mode="unnecessary_multi_table_joins",
                difficulty="medium",
            ),

            # -------------------------------------------------------------
            # Target 2: Disambiguating Ambiguous Column Names (e.g. status, name)
            # -------------------------------------------------------------
            GroundedSyntheticExample(
                example_id="synth_err_6",
                db_id="ecommerce",
                question="Show the order id, order status, and payment status for payment amount greater than 100.",
                query="SELECT o.order_id, o.order_status, p.payment_status FROM orders o JOIN payments p ON o.order_id = p.order_id WHERE p.amount > 100;",
                target_failure_mode="ambiguous_columns",
                difficulty="hard",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_7",
                db_id="finance",
                question="Show the loan id, loan status, and transaction status for transactions associated with loan accounts.",
                query="SELECT l.loan_id, l.status AS loan_status, t.status AS trans_status FROM loans l JOIN accounts a ON l.customer_id = a.customer_id JOIN transactions t ON a.account_id = t.account_id WHERE l.status = 'approved';",
                target_failure_mode="ambiguous_columns",
                difficulty="hard",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_8",
                db_id="healthcare",
                question="List the patient name, city, and doctor name for all scheduled appointments.",
                query="SELECT p.patient_name, p.city, d.doctor_name FROM appointments a JOIN patients p ON a.patient_id = p.patient_id JOIN doctors d ON a.doctor_id = d.doctor_id WHERE a.status = 'scheduled';",
                target_failure_mode="ambiguous_columns",
                difficulty="hard",
            ),

            # -------------------------------------------------------------
            # Target 3: Strict Aggregation with GROUP BY and DISTINCT
            # -------------------------------------------------------------
            GroundedSyntheticExample(
                example_id="synth_err_9",
                db_id="ecommerce",
                question="How many distinct categories of products were purchased in completed orders?",
                query="SELECT count(DISTINCT p.category_id) FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id WHERE o.order_status = 'completed';",
                target_failure_mode="distinct_aggregation",
                difficulty="hard",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_10",
                db_id="healthcare",
                question="How many different patients visited each department building?",
                query="SELECT dep.building, count(DISTINCT a.patient_id) FROM appointments a JOIN doctors d ON a.doctor_id = d.doctor_id JOIN departments dep ON d.dept_id = dep.dept_id GROUP BY dep.building;",
                target_failure_mode="distinct_aggregation",
                difficulty="hard",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_11",
                db_id="inventory",
                question="What is the average unit cost of parts supplied by each country?",
                query="SELECT s.country, avg(p.unit_cost) FROM parts p JOIN suppliers s ON p.supplier_id = s.supplier_id GROUP BY s.country;",
                target_failure_mode="aggregation_groupby",
                difficulty="medium",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_12",
                db_id="inventory",
                question="Which supplier has supplied parts with a total quantity on hand exceeding 500?",
                query="SELECT s.supplier_name, sum(st.quantity_on_hand) FROM suppliers s JOIN parts p ON s.supplier_id = p.supplier_id JOIN stock st ON p.part_id = st.part_id GROUP BY s.supplier_name HAVING sum(st.quantity_on_hand) > 500;",
                target_failure_mode="aggregation_groupby",
                difficulty="hard",
            ),

            # -------------------------------------------------------------
            # Target 4: Foreign-Key Navigation & Single-Table Query Protection
            # -------------------------------------------------------------
            GroundedSyntheticExample(
                example_id="synth_err_13",
                db_id="ecommerce",
                question="List all distinct states where customers reside.",
                query="SELECT DISTINCT state FROM customers;",
                target_failure_mode="unnecessary_joins_on_single_table",
                difficulty="easy",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_14",
                db_id="finance",
                question="What is the total balance of all checking accounts?",
                query="SELECT sum(balance) FROM accounts WHERE account_type = 'checking';",
                target_failure_mode="unnecessary_joins_on_single_table",
                difficulty="easy",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_15",
                db_id="logistics",
                question="Find all warehouse names located in 'Chicago'.",
                query="SELECT warehouse_name FROM warehouses WHERE city = 'Chicago';",
                target_failure_mode="unnecessary_joins_on_single_table",
                difficulty="easy",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_16",
                db_id="logistics",
                question="What is the driver name and vehicle license plate for shipment number 1001?",
                query="SELECT d.driver_name, v.license_plate FROM shipments s JOIN drivers d ON s.driver_id = d.driver_id JOIN vehicles v ON s.vehicle_id = v.vehicle_id WHERE s.shipment_id = 1001;",
                target_failure_mode="foreign_key_navigation",
                difficulty="medium",
            ),

            # -------------------------------------------------------------
            # Target 5: Subqueries & CTEs
            # -------------------------------------------------------------
            GroundedSyntheticExample(
                example_id="synth_err_17",
                db_id="ecommerce",
                question="Find the customer names who have never placed an order.",
                query="SELECT customer_name FROM customers WHERE customer_id NOT IN (SELECT customer_id FROM orders);",
                target_failure_mode="subquery_not_in",
                difficulty="hard",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_18",
                db_id="finance",
                question="Find bank customers whose net worth is above the average net worth of all customers.",
                query="SELECT customer_name, net_worth FROM bank_customers WHERE net_worth > (SELECT avg(net_worth) FROM bank_customers);",
                target_failure_mode="subquery_comparison",
                difficulty="hard",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_19",
                db_id="healthcare",
                question="Using a CTE, find doctors who have higher than average doctor fees.",
                query="WITH avg_fee AS (SELECT avg(fee) AS val FROM appointments) SELECT d.doctor_name, a.fee FROM appointments a JOIN doctors d ON a.doctor_id = d.doctor_id, avg_fee WHERE a.fee > avg_fee.val;",
                target_failure_mode="cte_query",
                difficulty="extra_hard",
            ),
            GroundedSyntheticExample(
                example_id="synth_err_20",
                db_id="logistics",
                question="Find the driver name and years of experience for drivers assigned to in-transit shipments.",
                query="SELECT DISTINCT d.driver_name, d.years_experience FROM shipments s JOIN drivers d ON s.driver_id = d.driver_id WHERE s.status = 'in_transit';",
                target_failure_mode="distinct_aggregation",
                difficulty="medium",
            ),
        ]
