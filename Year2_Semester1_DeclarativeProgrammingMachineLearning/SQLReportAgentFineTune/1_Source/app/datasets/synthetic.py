"""Independent synthetic Text-to-SQL dataset generator with validated SQLite databases."""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from app.core.config import get_project_root
from app.core.logging import get_logger
from app.database.schema_manager import DatabaseSchema, SchemaManager
from app.database.sqlite_executor import SQLiteExecutor

logger = get_logger(__name__)


@dataclass
class SyntheticSample:
    db_id: str
    question: str
    query: str
    difficulty: str
    category: str


class SyntheticDatasetGenerator:
    """Generates independent schemas, test databases, and validated SQL query pairs."""

    def __init__(self, output_dir: Optional[Union[str, Path]] = None):
        if output_dir is None:
            self.output_dir = get_project_root() / "2_Database" / "synthetic"
        else:
            self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def setup_retail_database(self) -> Path:
        """Initializes retail_analytics SQLite database."""
        db_path = self.output_dir / "retail_analytics.db"
        ddl = """
        CREATE TABLE categories (
            category_id INTEGER PRIMARY KEY,
            category_name TEXT NOT NULL,
            department TEXT NOT NULL
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            cost_price REAL NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        );

        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            signup_date TEXT NOT NULL
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            order_status TEXT NOT NULL,
            shipping_fee REAL DEFAULT 0.0,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE order_items (
            item_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_sale_price REAL NOT NULL,
            discount_amount REAL DEFAULT 0.0,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );

        CREATE TABLE payments (
            payment_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
        """

        seed_data = """
        INSERT INTO categories VALUES (1, 'Electronics', 'Tech'), (2, 'Apparel', 'Clothing'), (3, 'Home Goods', 'Home');
        INSERT INTO products VALUES 
            (101, 'Pro Laptop 15', 1, 1200.0, 900.0),
            (102, 'Wireless Headphones', 1, 150.0, 80.0),
            (103, 'Cotton Hoodie', 2, 60.0, 25.0),
            (104, 'Denim Jeans', 2, 80.0, 35.0),
            (105, 'Espresso Machine', 3, 300.0, 180.0);
        INSERT INTO customers VALUES 
            (1, 'Alice Smith', 'Seattle', 'WA', '2023-01-15'),
            (2, 'Bob Jones', 'Austin', 'TX', '2023-03-22'),
            (3, 'Charlie Brown', 'Denver', 'CO', '2023-05-10'),
            (4, 'Diana Prince', 'New York', 'NY', '2023-07-04');
        INSERT INTO orders VALUES 
            (1001, 1, '2024-01-10', 'delivered', 15.0),
            (1002, 1, '2024-02-14', 'delivered', 10.0),
            (1003, 2, '2024-02-20', 'delivered', 0.0),
            (1004, 3, '2024-03-01', 'shipped', 20.0),
            (1005, 4, '2024-03-15', 'cancelled', 0.0);
        INSERT INTO order_items VALUES 
            (1, 1001, 101, 1, 1200.0, 50.0),
            (2, 1001, 102, 2, 150.0, 0.0),
            (3, 1002, 103, 3, 60.0, 10.0),
            (4, 1003, 105, 1, 300.0, 0.0),
            (5, 1004, 104, 2, 80.0, 0.0);
        INSERT INTO payments VALUES 
            (501, 1001, 'credit_card', 'captured', 1465.0, '2024-01-10'),
            (502, 1002, 'paypal', 'captured', 180.0, '2024-02-14'),
            (503, 1003, 'credit_card', 'captured', 300.0, '2024-02-20'),
            (504, 1004, 'bank_transfer', 'authorized', 180.0, '2024-03-01');
        """
        return SchemaManager.create_database_from_ddl(db_path, ddl, seed_data)

    def setup_hospital_database(self) -> Path:
        """Initializes hospital_management SQLite database."""
        db_path = self.output_dir / "hospital_management.db"
        ddl = """
        CREATE TABLE departments (
            dept_id INTEGER PRIMARY KEY,
            dept_name TEXT NOT NULL,
            building TEXT NOT NULL
        );

        CREATE TABLE doctors (
            doctor_id INTEGER PRIMARY KEY,
            doctor_name TEXT NOT NULL,
            dept_id INTEGER NOT NULL,
            specialty TEXT NOT NULL,
            salary REAL NOT NULL,
            FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
        );

        CREATE TABLE patients (
            patient_id INTEGER PRIMARY KEY,
            patient_name TEXT NOT NULL,
            birth_year INTEGER NOT NULL,
            gender TEXT NOT NULL,
            city TEXT NOT NULL
        );

        CREATE TABLE appointments (
            appointment_id INTEGER PRIMARY KEY,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            status TEXT NOT NULL,
            fee REAL NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
        );
        """
        seed_data = """
        INSERT INTO departments VALUES (1, 'Cardiology', 'Wing A'), (2, 'Neurology', 'Wing B'), (3, 'Pediatrics', 'Wing C');
        INSERT INTO doctors VALUES 
            (10, 'Dr. Sarah Connor', 1, 'Cardiologist', 180000.0),
            (20, 'Dr. Gregory House', 2, 'Diagnostic Neurology', 220000.0),
            (30, 'Dr. Allison Cameron', 3, 'Pediatrician', 150000.0);
        INSERT INTO patients VALUES 
            (101, 'John Doe', 1980, 'M', 'Chicago'),
            (102, 'Jane Roe', 1995, 'F', 'Evanston'),
            (103, 'Billy Bob', 2012, 'M', 'Naperville');
        INSERT INTO appointments VALUES 
            (1001, 101, 10, '2024-01-15', 'completed', 250.0),
            (1002, 102, 20, '2024-02-01', 'completed', 350.0),
            (1003, 103, 30, '2024-02-10', 'completed', 150.0),
            (1004, 101, 20, '2024-03-05', 'scheduled', 300.0);
        """
        return SchemaManager.create_database_from_ddl(db_path, ddl, seed_data)

    def get_retail_samples(self) -> List[SyntheticSample]:
        """Curated query pairs for retail_analytics."""
        return [
            # Basic aggregations
            SyntheticSample(
                db_id="retail_analytics",
                question="What is the total quantity of products ordered across all orders?",
                query="SELECT SUM(quantity) FROM order_items",
                difficulty="easy",
                category="aggregation",
            ),
            SyntheticSample(
                db_id="retail_analytics",
                question="List all customers located in Seattle.",
                query="SELECT customer_name FROM customers WHERE city = 'Seattle'",
                difficulty="easy",
                category="filtering",
            ),
            # 2-table Joins
            SyntheticSample(
                db_id="retail_analytics",
                question="Find the total revenue captured for each payment method.",
                query="SELECT payment_method, SUM(amount) FROM payments WHERE payment_status = 'captured' GROUP BY payment_method",
                difficulty="medium",
                category="aggregation_grouping",
            ),
            SyntheticSample(
                db_id="retail_analytics",
                question="List each customer name along with their order ids.",
                query="SELECT customers.customer_name, orders.order_id FROM customers JOIN orders ON customers.customer_id = orders.customer_id",
                difficulty="medium",
                category="join_2way",
            ),
            # 3-table Joins
            SyntheticSample(
                db_id="retail_analytics",
                question="Show each customer's name and the names of the products they ordered.",
                query="SELECT customers.customer_name, products.product_name FROM customers JOIN orders ON customers.customer_id = orders.customer_id JOIN order_items ON orders.order_id = order_items.order_id JOIN products ON order_items.product_id = products.product_id",
                difficulty="hard",
                category="join_3way",
            ),
            SyntheticSample(
                db_id="retail_analytics",
                question="Find the total spending per customer, ordering by total spent descending.",
                query="SELECT customers.customer_name, SUM(order_items.quantity * order_items.unit_sale_price - order_items.discount_amount) AS total_spent FROM customers JOIN orders ON customers.customer_id = orders.customer_id JOIN order_items ON orders.order_id = order_items.order_id GROUP BY customers.customer_id ORDER BY total_spent DESC",
                difficulty="hard",
                category="aggregation_join",
            ),
            # 4-table Joins (Addressing Small Model Multi-Table Weakness)
            SyntheticSample(
                db_id="retail_analytics",
                question="Calculate the total gross sales by category name for all delivered orders.",
                query="SELECT categories.category_name, SUM(order_items.quantity * order_items.unit_sale_price) AS gross_sales FROM categories JOIN products ON categories.category_id = products.category_id JOIN order_items ON products.product_id = order_items.product_id JOIN orders ON order_items.order_id = orders.order_id WHERE orders.order_status = 'delivered' GROUP BY categories.category_name",
                difficulty="extra_hard",
                category="join_4way",
            ),
            SyntheticSample(
                db_id="retail_analytics",
                question="Which product category generated the highest profit, where profit is unit sale price minus cost price multiplied by quantity?",
                query="SELECT categories.category_name, SUM((order_items.unit_sale_price - products.cost_price) * order_items.quantity) AS total_profit FROM categories JOIN products ON categories.category_id = products.category_id JOIN order_items ON products.product_id = order_items.product_id GROUP BY categories.category_name ORDER BY total_profit DESC LIMIT 1",
                difficulty="extra_hard",
                category="join_multi_calc",
            ),
            # Date Arithmetic & CTEs
            SyntheticSample(
                db_id="retail_analytics",
                question="List monthly order counts formatted as YYYY-MM.",
                query="SELECT strftime('%Y-%m', order_date) AS order_month, COUNT(order_id) AS total_orders FROM orders GROUP BY order_month ORDER BY order_month ASC",
                difficulty="medium",
                category="date_formatting",
            ),
            SyntheticSample(
                db_id="retail_analytics",
                question="Find all customers who have never placed an order.",
                query="SELECT customers.customer_name FROM customers LEFT JOIN orders ON customers.customer_id = orders.customer_id WHERE orders.order_id IS NULL",
                difficulty="medium",
                category="null_handling",
            ),
            SyntheticSample(
                db_id="retail_analytics",
                question="Using a CTE, find products whose unit price is higher than the average product unit price.",
                query="WITH avg_price AS (SELECT AVG(unit_price) AS avg_p FROM products) SELECT products.product_name, products.unit_price FROM products, avg_price WHERE products.unit_price > avg_price.avg_p",
                difficulty="hard",
                category="cte_subquery",
            ),
        ]

    def get_hospital_samples(self) -> List[SyntheticSample]:
        """Curated query pairs for hospital_management."""
        return [
            SyntheticSample(
                db_id="hospital_management",
                question="How many doctors work in each department?",
                query="SELECT departments.dept_name, COUNT(doctors.doctor_id) AS doctor_count FROM departments LEFT JOIN doctors ON departments.dept_id = doctors.dept_id GROUP BY departments.dept_name",
                difficulty="medium",
                category="group_by_left_join",
            ),
            SyntheticSample(
                db_id="hospital_management",
                question="What is the average doctor salary by specialty?",
                query="SELECT specialty, AVG(salary) FROM doctors GROUP BY specialty",
                difficulty="easy",
                category="aggregation",
            ),
            SyntheticSample(
                db_id="hospital_management",
                question="Find the total appointment fees collected by Dr. Gregory House.",
                query="SELECT SUM(appointments.fee) FROM appointments JOIN doctors ON appointments.doctor_id = doctors.doctor_id WHERE doctors.doctor_name = 'Dr. Gregory House' AND appointments.status = 'completed'",
                difficulty="medium",
                category="join_2way",
            ),
            SyntheticSample(
                db_id="hospital_management",
                question="List each patient name, their doctor name, and their appointment date.",
                query="SELECT patients.patient_name, doctors.doctor_name, appointments.appointment_date FROM patients JOIN appointments ON patients.patient_id = appointments.patient_id JOIN doctors ON appointments.doctor_id = doctors.doctor_id",
                difficulty="hard",
                category="join_3way",
            ),
            SyntheticSample(
                db_id="hospital_management",
                question="Which patient has had the most appointments?",
                query="SELECT patients.patient_name, COUNT(appointments.appointment_id) AS num_appts FROM patients JOIN appointments ON patients.patient_id = appointments.patient_id GROUP BY patients.patient_id ORDER BY num_appts DESC LIMIT 1",
                difficulty="medium",
                category="ranking",
            ),
        ]

    def generate_all(self) -> Tuple[List[SyntheticSample], Dict[str, Path]]:
        """Sets up SQLite databases, validates every query, and returns verified samples."""
        retail_db = self.setup_retail_database()
        hospital_db = self.setup_hospital_database()
        db_map = {
            "retail_analytics": retail_db,
            "hospital_management": hospital_db,
        }

        all_samples = self.get_retail_samples() + self.get_hospital_samples()
        verified_samples = []

        for sample in all_samples:
            db_path = db_map[sample.db_id]
            executor = SQLiteExecutor(db_path)
            res = executor.execute(sample.query)
            if not res.success:
                logger.error(f"Failed query validation for {sample.question}: {res.error}")
            else:
                verified_samples.append(sample)

        logger.info(f"Verified {len(verified_samples)} synthetic SQL samples against independent SQLite databases.")
        return verified_samples, db_map
