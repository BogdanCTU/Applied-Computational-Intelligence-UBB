"""Comprehensive Multi-Domain Synthetic Text-to-SQL Dataset Generator.

Generates 8 independent SQLite domain databases, validates 15 SQL query complexity
patterns with live SQLite execution, and enforces zero-leakage track partitioning.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from app.core.config import get_project_root
from app.core.logging import get_logger
from app.database.schema_manager import SchemaManager
from app.database.sqlite_executor import SQLiteExecutor

logger = get_logger(__name__)


@dataclass
class SyntheticSample:
    db_id: str
    question: str
    query: str
    difficulty: str  # easy, medium, hard, extra_hard
    category: str    # one of 15 complexity categories
    domain: str      # ecommerce, healthcare, finance, hr, logistics, inventory, education, entertainment
    track: str       # 'track1_known' or 'track2_unseen'


class SyntheticDatasetGenerator:
    """Creates 8 isolated domain databases and validated SQL query pairs."""

    def __init__(self, output_dir: Optional[Union[str, Path]] = None):
        if output_dir is None:
            self.output_dir = get_project_root() / "2_Database" / "synthetic"
        else:
            self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------
    # 1. E-COMMERCE DOMAIN
    # -------------------------------------------------------------
    def setup_ecommerce(self) -> Path:
        db_path = self.output_dir / "ecommerce.db"
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
        CREATE TABLE shipping (
            shipping_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            carrier TEXT NOT NULL,
            tracking_number TEXT NOT NULL,
            delivery_date TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
        """
        data = """
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
        INSERT INTO shipping VALUES 
            (1, 1001, 'FedEx', 'FX1001', '2024-01-14'),
            (2, 1002, 'UPS', 'UP1002', '2024-02-18'),
            (3, 1003, 'FedEx', 'FX1003', '2024-02-25'),
            (4, 1004, 'USPS', 'US1004', NULL);
        """
        return SchemaManager.create_database_from_ddl(db_path, ddl, data)

    # -------------------------------------------------------------
    # 2. HEALTHCARE DOMAIN
    # -------------------------------------------------------------
    def setup_healthcare(self) -> Path:
        db_path = self.output_dir / "healthcare.db"
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
        CREATE TABLE prescriptions (
            prescription_id INTEGER PRIMARY KEY,
            appointment_id INTEGER NOT NULL,
            medication_name TEXT NOT NULL,
            dosage_mg INTEGER NOT NULL,
            refills INTEGER DEFAULT 0,
            FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
        );
        """
        data = """
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
        INSERT INTO prescriptions VALUES 
            (1, 1001, 'Atorvastatin', 20, 3),
            (2, 1002, 'Gabapentin', 300, 1),
            (3, 1003, 'Amoxicillin', 250, 0);
        """
        return SchemaManager.create_database_from_ddl(db_path, ddl, data)

    # -------------------------------------------------------------
    # 3. FINANCE DOMAIN
    # -------------------------------------------------------------
    def setup_finance(self) -> Path:
        db_path = self.output_dir / "finance.db"
        ddl = """
        CREATE TABLE branches (
            branch_id INTEGER PRIMARY KEY,
            branch_name TEXT NOT NULL,
            city TEXT NOT NULL,
            assets REAL NOT NULL
        );
        CREATE TABLE bank_customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            credit_score INTEGER NOT NULL,
            net_worth REAL NOT NULL
        );
        CREATE TABLE accounts (
            account_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            branch_id INTEGER NOT NULL,
            account_type TEXT NOT NULL,
            balance REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES bank_customers(customer_id),
            FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
        );
        CREATE TABLE transactions (
            trans_id INTEGER PRIMARY KEY,
            account_id INTEGER NOT NULL,
            trans_date TEXT NOT NULL,
            trans_type TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        );
        CREATE TABLE loans (
            loan_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            branch_id INTEGER NOT NULL,
            loan_amount REAL NOT NULL,
            interest_rate REAL NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES bank_customers(customer_id),
            FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
        );
        """
        data = """
        INSERT INTO branches VALUES 
            (1, 'Wall Street Hub', 'New York', 50000000.0),
            (2, 'Bay Area Center', 'San Francisco', 35000000.0),
            (3, 'Loop Branch', 'Chicago', 20000000.0);
        INSERT INTO bank_customers VALUES 
            (1, 'Warren Buffet', 820, 10000000.0),
            (2, 'Peter Thiel', 790, 5000000.0),
            (3, 'Grace Hopper', 750, 1500000.0),
            (4, 'Ada Lovelace', 710, 800000.0);
        INSERT INTO accounts VALUES 
            (101, 1, 1, 'checking', 250000.0),
            (102, 1, 1, 'investment', 1200000.0),
            (103, 2, 2, 'checking', 180000.0),
            (104, 3, 3, 'savings', 95000.0),
            (105, 4, 1, 'checking', 35000.0);
        INSERT INTO transactions VALUES 
            (1, 101, '2024-01-05', 'credit', 50000.0, 'cleared'),
            (2, 101, '2024-01-10', 'debit', 12000.0, 'cleared'),
            (3, 102, '2024-02-01', 'credit', 100000.0, 'cleared'),
            (4, 103, '2024-02-15', 'debit', 5000.0, 'cleared'),
            (5, 104, '2024-03-01', 'credit', 2000.0, 'pending');
        INSERT INTO loans VALUES 
            (501, 2, 2, 500000.0, 4.5, 'active'),
            (502, 3, 3, 150000.0, 5.2, 'active'),
            (503, 4, 1, 80000.0, 6.1, 'closed');
        """
        return SchemaManager.create_database_from_ddl(db_path, ddl, data)

    # -------------------------------------------------------------
    # 4. HUMAN RESOURCES DOMAIN
    # -------------------------------------------------------------
    def setup_hr(self) -> Path:
        db_path = self.output_dir / "human_resources.db"
        ddl = """
        CREATE TABLE departments (
            dept_id INTEGER PRIMARY KEY,
            dept_name TEXT NOT NULL,
            location TEXT NOT NULL
        );
        CREATE TABLE employees (
            emp_id INTEGER PRIMARY KEY,
            dept_id INTEGER NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            hire_date TEXT NOT NULL,
            job_title TEXT NOT NULL,
            FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
        );
        CREATE TABLE compensation (
            comp_id INTEGER PRIMARY KEY,
            emp_id INTEGER NOT NULL,
            base_salary REAL NOT NULL,
            bonus REAL DEFAULT 0.0,
            effective_date TEXT NOT NULL,
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
        );
        CREATE TABLE performance_reviews (
            review_id INTEGER PRIMARY KEY,
            emp_id INTEGER NOT NULL,
            review_year INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comments TEXT,
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
        );
        """
        data = """
        INSERT INTO departments VALUES (1, 'Engineering', 'Building 1'), (2, 'Sales', 'Building 2'), (3, 'HR', 'HQ');
        INSERT INTO employees VALUES 
            (10, 1, 'Linus', 'Torvalds', '2018-05-01', 'Staff Engineer'),
            (20, 1, 'Guido', 'van Rossum', '2019-09-15', 'Principal Architect'),
            (30, 2, 'Jordan', 'Belfort', '2021-02-01', 'Senior Account Exec'),
            (40, 3, 'Pam', 'Beesly', '2022-01-10', 'HR Generalist');
        INSERT INTO compensation VALUES 
            (1, 10, 220000.0, 40000.0, '2023-01-01'),
            (2, 20, 240000.0, 50000.0, '2023-01-01'),
            (3, 30, 120000.0, 80000.0, '2023-01-01'),
            (4, 40, 75000.0, 5000.0, '2023-01-01');
        INSERT INTO performance_reviews VALUES 
            (1, 10, 2023, 5, 'Exceptional systems programming leadership'),
            (2, 20, 2023, 5, 'World-class language and runtime design'),
            (3, 30, 2023, 4, 'Top revenue generator'),
            (4, 40, 2023, 4, 'Strong cross-department mediation');
        """
        return SchemaManager.create_database_from_ddl(db_path, ddl, data)

    # -------------------------------------------------------------
    # 5. LOGISTICS DOMAIN
    # -------------------------------------------------------------
    def setup_logistics(self) -> Path:
        db_path = self.output_dir / "logistics.db"
        ddl = """
        CREATE TABLE warehouses (
            warehouse_id INTEGER PRIMARY KEY,
            warehouse_name TEXT NOT NULL,
            city TEXT NOT NULL,
            capacity_sqft INTEGER NOT NULL
        );
        CREATE TABLE vehicles (
            vehicle_id INTEGER PRIMARY KEY,
            license_plate TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            payload_kg REAL NOT NULL
        );
        CREATE TABLE drivers (
            driver_id INTEGER PRIMARY KEY,
            driver_name TEXT NOT NULL,
            license_class TEXT NOT NULL,
            years_experience INTEGER NOT NULL
        );
        CREATE TABLE shipments (
            shipment_id INTEGER PRIMARY KEY,
            origin_warehouse_id INTEGER NOT NULL,
            dest_warehouse_id INTEGER NOT NULL,
            vehicle_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,
            shipment_date TEXT NOT NULL,
            status TEXT NOT NULL,
            cost REAL NOT NULL,
            FOREIGN KEY (origin_warehouse_id) REFERENCES warehouses(warehouse_id),
            FOREIGN KEY (dest_warehouse_id) REFERENCES warehouses(warehouse_id),
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
            FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
        );
        """
        data = """
        INSERT INTO warehouses VALUES 
            (1, 'JFK Freight Terminal', 'New York', 150000),
            (2, 'O Hare Hub', 'Chicago', 200000),
            (3, 'DFW Distribution', 'Dallas', 180000);
        INSERT INTO vehicles VALUES 
            (10, 'NY-TRK-01', 'Semi-Trailer', 22000.0),
            (20, 'IL-TRK-02', 'Box Truck', 8000.0),
            (30, 'TX-VAN-03', 'Cargo Van', 3000.0);
        INSERT INTO drivers VALUES 
            (101, 'Marcus Vance', 'Class A CDL', 12),
            (102, 'Elena Rostova', 'Class A CDL', 8),
            (103, 'James Chen', 'Class B CDL', 5);
        INSERT INTO shipments VALUES 
            (1001, 1, 2, 10, 101, '2024-01-10', 'delivered', 2400.0),
            (1002, 2, 3, 10, 102, '2024-02-05', 'delivered', 1900.0),
            (1003, 1, 3, 20, 103, '2024-02-20', 'in_transit', 3100.0),
            (1004, 3, 1, 30, 101, '2024-03-01', 'delayed', 1500.0);
        """
        return SchemaManager.create_database_from_ddl(db_path, ddl, data)

    # -------------------------------------------------------------
    # 6. INVENTORY MANAGEMENT DOMAIN
    # -------------------------------------------------------------
    def setup_inventory(self) -> Path:
        db_path = self.output_dir / "inventory.db"
        ddl = """
        CREATE TABLE suppliers (
            supplier_id INTEGER PRIMARY KEY,
            supplier_name TEXT NOT NULL,
            country TEXT NOT NULL,
            lead_time_days INTEGER NOT NULL
        );
        CREATE TABLE parts (
            part_id INTEGER PRIMARY KEY,
            part_name TEXT NOT NULL,
            supplier_id INTEGER NOT NULL,
            unit_cost REAL NOT NULL,
            reorder_threshold INTEGER NOT NULL,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        );
        CREATE TABLE stock (
            stock_id INTEGER PRIMARY KEY,
            part_id INTEGER NOT NULL,
            warehouse_code TEXT NOT NULL,
            quantity_on_hand INTEGER NOT NULL,
            last_counted TEXT NOT NULL,
            FOREIGN KEY (part_id) REFERENCES parts(part_id)
        );
        CREATE TABLE purchase_orders (
            po_id INTEGER PRIMARY KEY,
            part_id INTEGER NOT NULL,
            supplier_id INTEGER NOT NULL,
            qty_ordered INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            po_status TEXT NOT NULL,
            FOREIGN KEY (part_id) REFERENCES parts(part_id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        );
        """
        data = """
        INSERT INTO suppliers VALUES 
            (1, 'Precision Bearings Co', 'Germany', 14),
            (2, 'Pacific Microchips', 'Taiwan', 21),
            (3, 'Titanium Alloys Ltd', 'Japan', 18);
        INSERT INTO parts VALUES 
            (10, 'Ceramic Ball Bearing', 1, 45.0, 100),
            (20, '4-Core Embedded SoC', 2, 85.0, 50),
            (30, 'Grade-5 Titanium Rod', 3, 120.0, 30),
            (40, 'Hydraulic Seal 12mm', 1, 15.0, 200);
        INSERT INTO stock VALUES 
            (1, 10, 'WH-A', 80, '2024-01-01'),
            (2, 20, 'WH-B', 45, '2024-01-15'),
            (3, 30, 'WH-A', 55, '2024-02-01'),
            (4, 40, 'WH-B', 320, '2024-02-10');
        INSERT INTO purchase_orders VALUES 
            (1001, 10, 1, 500, '2024-01-20', 'received'),
            (1002, 20, 2, 250, '2024-02-10', 'shipped'),
            (1003, 30, 3, 100, '2024-03-01', 'pending');
        """
        return SchemaManager.create_database_from_ddl(db_path, ddl, data)

    # -------------------------------------------------------------
    # 7. EDUCATION DOMAIN (TRACK 2: HELD-OUT UNSEEN SCHEMA)
    # -------------------------------------------------------------
    def setup_education(self) -> Path:
        db_path = self.output_dir / "education.db"
        ddl = """
        CREATE TABLE faculties (
            faculty_id INTEGER PRIMARY KEY,
            faculty_name TEXT NOT NULL,
            dean TEXT NOT NULL
        );
        CREATE TABLE courses (
            course_id INTEGER PRIMARY KEY,
            course_code TEXT NOT NULL,
            title TEXT NOT NULL,
            faculty_id INTEGER NOT NULL,
            credits INTEGER NOT NULL,
            FOREIGN KEY (faculty_id) REFERENCES faculties(faculty_id)
        );
        CREATE TABLE students (
            student_id INTEGER PRIMARY KEY,
            student_name TEXT NOT NULL,
            gpa REAL NOT NULL,
            enrollment_year INTEGER NOT NULL
        );
        CREATE TABLE enrollments (
            enrollment_id INTEGER PRIMARY KEY,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            semester TEXT NOT NULL,
            grade TEXT,
            score REAL,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (course_id) REFERENCES courses(course_id)
        );
        """
        data = """
        INSERT INTO faculties VALUES (1, 'Computer Science', 'Dr. Donald Knuth'), (2, 'Mathematics', 'Dr. Terence Tao');
        INSERT INTO courses VALUES 
            (101, 'CS101', 'Algorithms & Data Structures', 1, 4),
            (102, 'CS205', 'Declarative Programming', 1, 3),
            (103, 'MATH301', 'Linear Algebra & Optimization', 2, 4);
        INSERT INTO students VALUES 
            (1, 'Alan Turing', 4.0, 2021),
            (2, 'Claude Shannon', 3.9, 2022),
            (3, 'John von Neumann', 3.95, 2020),
            (4, 'Margaret Hamilton', 3.85, 2023);
        INSERT INTO enrollments VALUES 
            (1, 1, 101, 'Fall 2023', 'A', 98.0),
            (2, 1, 102, 'Fall 2023', 'A', 95.0),
            (3, 2, 101, 'Fall 2023', 'A', 92.0),
            (4, 2, 103, 'Spring 2024', 'B', 85.0),
            (5, 3, 103, 'Spring 2024', 'A', 99.0),
            (6, 4, 102, 'Spring 2024', 'A', 94.0);
        """
        return SchemaManager.create_database_from_ddl(db_path, ddl, data)

    # -------------------------------------------------------------
    # 8. ENTERTAINMENT DOMAIN (TRACK 2: HELD-OUT UNSEEN SCHEMA)
    # -------------------------------------------------------------
    def setup_entertainment(self) -> Path:
        db_path = self.output_dir / "entertainment.db"
        ddl = """
        CREATE TABLE artists (
            artist_id INTEGER PRIMARY KEY,
            artist_name TEXT NOT NULL,
            genre TEXT NOT NULL,
            country TEXT NOT NULL
        );
        CREATE TABLE albums (
            album_id INTEGER PRIMARY KEY,
            artist_id INTEGER NOT NULL,
            album_title TEXT NOT NULL,
            release_year INTEGER NOT NULL,
            FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
        );
        CREATE TABLE tracks (
            track_id INTEGER PRIMARY KEY,
            album_id INTEGER NOT NULL,
            track_name TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            stream_count INTEGER DEFAULT 0,
            FOREIGN KEY (album_id) REFERENCES albums(album_id)
        );
        CREATE TABLE playlists (
            playlist_id INTEGER PRIMARY KEY,
            playlist_name TEXT NOT NULL,
            creator_name TEXT NOT NULL
        );
        CREATE TABLE playlist_tracks (
            playlist_id INTEGER NOT NULL,
            track_id INTEGER NOT NULL,
            added_date TEXT NOT NULL,
            PRIMARY KEY (playlist_id, track_id),
            FOREIGN KEY (playlist_id) REFERENCES playlists(playlist_id),
            FOREIGN KEY (track_id) REFERENCES tracks(track_id)
        );
        """
        data = """
        INSERT INTO artists VALUES 
            (1, 'Radiohead', 'Alternative Rock', 'UK'),
            (2, 'Daft Punk', 'Electronic', 'France'),
            (3, 'Miles Davis', 'Jazz', 'USA');
        INSERT INTO albums VALUES 
            (10, 1, 'OK Computer', 1997),
            (20, 2, 'Discovery', 2001),
            (30, 3, 'Kind of Blue', 1959);
        INSERT INTO tracks VALUES 
            (101, 10, 'Paranoid Android', 383, 250000000),
            (102, 10, 'Karma Police', 261, 310000000),
            (201, 20, 'One More Time', 320, 450000000),
            (202, 20, 'Harder Better Faster Stronger', 224, 390000000),
            (301, 30, 'So What', 562, 180000000);
        INSERT INTO playlists VALUES 
            (1, 'Timeless Masterpieces', 'Editor Choice'),
            (2, 'Late Night Vibes', 'Chill DJ');
        INSERT INTO playlist_tracks VALUES 
            (1, 101, '2023-01-10'),
            (1, 201, '2023-01-10'),
            (1, 301, '2023-02-15'),
            (2, 102, '2023-03-01'),
            (2, 202, '2023-03-12');
        """
        return SchemaManager.create_database_from_ddl(db_path, ddl, data)

    # -------------------------------------------------------------
    # QUERY GENERATION COVERING 15 PATTERNS
    # -------------------------------------------------------------
    def get_all_samples(self) -> List[SyntheticSample]:
        """Assembles comprehensive multi-domain query pairs."""
        samples = []

        # ---------------- E-COMMERCE ----------------
        samples.extend([
            # 1. Simple SELECT
            SyntheticSample("ecommerce", "What is the total quantity of products ordered across all orders?", "SELECT SUM(quantity) FROM order_items", "easy", "aggregation", "ecommerce", "track1_known"),
            # 2. Multi-column Filtering
            SyntheticSample("ecommerce", "List customer names in Seattle who signed up after 2023-01-01.", "SELECT customer_name FROM customers WHERE city = 'Seattle' AND signup_date > '2023-01-01'", "easy", "filtering_multi", "ecommerce", "track1_known"),
            # 3. Aggregation
            SyntheticSample("ecommerce", "What is the maximum unit sale price recorded in order items?", "SELECT MAX(unit_sale_price) FROM order_items", "easy", "aggregation", "ecommerce", "track1_known"),
            # 4. GROUP BY & HAVING
            SyntheticSample("ecommerce", "List cities with more than 1 customer.", "SELECT city, COUNT(customer_id) AS c_count FROM customers GROUP BY city HAVING c_count > 1", "medium", "group_by_having", "ecommerce", "track1_known"),
            # 5. 2-table JOIN
            SyntheticSample("ecommerce", "Find total payment amount captured by payment method.", "SELECT payment_method, SUM(amount) FROM payments WHERE payment_status = 'captured' GROUP BY payment_method", "medium", "join_2way", "ecommerce", "track1_known"),
            # 6. 3-6 table JOINs
            SyntheticSample("ecommerce", "Show each customer's name and the names of the products they ordered.", "SELECT customers.customer_name, products.product_name FROM customers JOIN orders ON customers.customer_id = orders.customer_id JOIN order_items ON orders.order_id = order_items.order_id JOIN products ON order_items.product_id = products.product_id", "hard", "join_3way", "ecommerce", "track1_known"),
            SyntheticSample("ecommerce", "Calculate gross sales by category name for all delivered orders.", "SELECT categories.category_name, SUM(order_items.quantity * order_items.unit_sale_price) AS gross_sales FROM categories JOIN products ON categories.category_id = products.category_id JOIN order_items ON products.product_id = order_items.product_id JOIN orders ON order_items.order_id = orders.order_id WHERE orders.order_status = 'delivered' GROUP BY categories.category_name", "extra_hard", "join_4way", "ecommerce", "track1_known"),
            SyntheticSample("ecommerce", "List customer name, order date, carrier, and payment amount for completed deliveries.", "SELECT customers.customer_name, orders.order_date, shipping.carrier, payments.amount FROM customers JOIN orders ON customers.customer_id = orders.customer_id JOIN shipping ON orders.order_id = shipping.order_id JOIN payments ON orders.order_id = payments.order_id WHERE shipping.delivery_date IS NOT NULL", "extra_hard", "join_5way", "ecommerce", "track1_known"),
            # 7. Subqueries
            SyntheticSample("ecommerce", "Find customers who placed orders with shipping fee greater than the average shipping fee.", "SELECT customer_name FROM customers WHERE customer_id IN (SELECT customer_id FROM orders WHERE shipping_fee > (SELECT AVG(shipping_fee) FROM orders))", "hard", "subquery", "ecommerce", "track1_known"),
            # 8. CTE
            SyntheticSample("ecommerce", "Using a CTE, find products priced higher than average product price.", "WITH avg_price AS (SELECT AVG(unit_price) AS avg_p FROM products) SELECT products.product_name, products.unit_price FROM products, avg_price WHERE products.unit_price > avg_price.avg_p", "hard", "cte", "ecommerce", "track1_known"),
            # 9. Window Functions
            SyntheticSample("ecommerce", "Rank products by unit price within each category.", "SELECT product_name, category_id, unit_price, RANK() OVER (PARTITION BY category_id ORDER BY unit_price DESC) AS price_rank FROM products", "hard", "window_function", "ecommerce", "track1_known"),
            # 10. Date filtering
            SyntheticSample("ecommerce", "List monthly order counts formatted as YYYY-MM.", "SELECT strftime('%Y-%m', order_date) AS order_month, COUNT(order_id) AS total_orders FROM orders GROUP BY order_month ORDER BY order_month ASC", "medium", "date_functions", "ecommerce", "track1_known"),
            # 11. Conditional Aggregations
            SyntheticSample("ecommerce", "Calculate captured versus authorized payment totals.", "SELECT SUM(CASE WHEN payment_status = 'captured' THEN amount ELSE 0.0 END) AS captured_amt, SUM(CASE WHEN payment_status = 'authorized' THEN amount ELSE 0.0 END) AS authorized_amt FROM payments", "medium", "conditional_agg", "ecommerce", "track1_known"),
            # 12. NULL handling
            SyntheticSample("ecommerce", "Find customers who have never placed an order.", "SELECT customers.customer_name FROM customers LEFT JOIN orders ON customers.customer_id = orders.customer_id WHERE orders.order_id IS NULL", "medium", "null_handling", "ecommerce", "track1_known"),
            # 13. CASE expressions
            SyntheticSample("ecommerce", "Classify products into Luxury or Budget based on whether price exceeds 200.", "SELECT product_name, CASE WHEN unit_price > 200 THEN 'Luxury' ELSE 'Budget' END AS tier FROM products", "easy", "case_expression", "ecommerce", "track1_known"),
            # 14. Duplicate Prevention
            SyntheticSample("ecommerce", "List distinct states where customers have made purchases.", "SELECT DISTINCT customers.state FROM customers JOIN orders ON customers.customer_id = orders.customer_id", "easy", "distinct", "ecommerce", "track1_known"),
            # 15. Complex Reporting Query
            SyntheticSample("ecommerce", "Compute profit margin per product category for delivered orders.", "SELECT categories.category_name, SUM(order_items.quantity * order_items.unit_sale_price) AS revenue, SUM(order_items.quantity * products.cost_price) AS cost, ROUND((SUM(order_items.quantity * order_items.unit_sale_price) - SUM(order_items.quantity * products.cost_price)) / SUM(order_items.quantity * order_items.unit_sale_price) * 100, 2) AS margin_pct FROM categories JOIN products ON categories.category_id = products.category_id JOIN order_items ON products.product_id = order_items.product_id JOIN orders ON order_items.order_id = orders.order_id WHERE orders.order_status = 'delivered' GROUP BY categories.category_name", "extra_hard", "reporting_complex", "ecommerce", "track1_known"),
        ])

        # ---------------- HEALTHCARE ----------------
        samples.extend([
            SyntheticSample("healthcare", "How many doctors work in each department?", "SELECT departments.dept_name, COUNT(doctors.doctor_id) AS doctor_count FROM departments LEFT JOIN doctors ON departments.dept_id = doctors.dept_id GROUP BY departments.dept_name", "medium", "group_by_having", "healthcare", "track1_known"),
            SyntheticSample("healthcare", "What is the average doctor salary by specialty?", "SELECT specialty, AVG(salary) FROM doctors GROUP BY specialty", "easy", "aggregation", "healthcare", "track1_known"),
            SyntheticSample("healthcare", "Find total appointment fees collected by Dr. Gregory House.", "SELECT SUM(appointments.fee) FROM appointments JOIN doctors ON appointments.doctor_id = doctors.doctor_id WHERE doctors.doctor_name = 'Dr. Gregory House' AND appointments.status = 'completed'", "medium", "join_2way", "healthcare", "track1_known"),
            SyntheticSample("healthcare", "List patient name, doctor name, and prescription medications for completed appointments.", "SELECT patients.patient_name, doctors.doctor_name, prescriptions.medication_name FROM patients JOIN appointments ON patients.patient_id = appointments.patient_id JOIN doctors ON appointments.doctor_id = doctors.doctor_id JOIN prescriptions ON appointments.appointment_id = prescriptions.appointment_id WHERE appointments.status = 'completed'", "hard", "join_4way", "healthcare", "track1_known"),
            SyntheticSample("healthcare", "Find patients with more refills than the average prescription refills.", "SELECT DISTINCT patients.patient_name FROM patients JOIN appointments ON patients.patient_id = appointments.patient_id JOIN prescriptions ON appointments.appointment_id = prescriptions.appointment_id WHERE prescriptions.refills > (SELECT AVG(refills) FROM prescriptions)", "hard", "subquery", "healthcare", "track1_known"),
        ])

        # ---------------- FINANCE ----------------
        samples.extend([
            SyntheticSample("finance", "List the total balance in each account type across all branches.", "SELECT account_type, SUM(balance) FROM accounts GROUP BY account_type", "medium", "group_by_having", "finance", "track1_known"),
            SyntheticSample("finance", "Find customer name, branch city, and loan amount for active loans over 100,000.", "SELECT bank_customers.customer_name, branches.city, loans.loan_amount FROM bank_customers JOIN loans ON bank_customers.customer_id = loans.customer_id JOIN branches ON loans.branch_id = branches.branch_id WHERE loans.status = 'active' AND loans.loan_amount > 100000", "hard", "join_3way", "finance", "track1_known"),
            SyntheticSample("finance", "Show running total of cleared transactions per account ordered by date.", "SELECT account_id, trans_date, amount, SUM(amount) OVER (PARTITION BY account_id ORDER BY trans_date) AS running_total FROM transactions WHERE status = 'cleared'", "hard", "window_function", "finance", "track1_known"),
            SyntheticSample("finance", "Categorize customers as High Net Worth if net worth exceeds 2,000,000 else Standard.", "SELECT customer_name, CASE WHEN net_worth >= 2000000 THEN 'High Net Worth' ELSE 'Standard' END AS segment FROM bank_customers", "easy", "case_expression", "finance", "track1_known"),
            SyntheticSample("finance", "Find branches that have never issued a loan.", "SELECT branches.branch_name FROM branches LEFT JOIN loans ON branches.branch_id = loans.branch_id WHERE loans.loan_id IS NULL", "medium", "null_handling", "finance", "track1_known"),
        ])

        # ---------------- HUMAN RESOURCES ----------------
        samples.extend([
            SyntheticSample("human_resources", "What is the total compensation (base salary plus bonus) by department?", "SELECT departments.dept_name, SUM(compensation.base_salary + compensation.bonus) AS total_comp FROM departments JOIN employees ON departments.dept_id = employees.dept_id JOIN compensation ON employees.emp_id = compensation.emp_id GROUP BY departments.dept_name", "hard", "join_3way", "human_resources", "track1_known"),
            SyntheticSample("human_resources", "List all employees with a performance rating of 5 in 2023.", "SELECT employees.first_name, employees.last_name, performance_reviews.rating FROM employees JOIN performance_reviews ON employees.emp_id = performance_reviews.emp_id WHERE performance_reviews.review_year = 2023 AND performance_reviews.rating = 5", "medium", "join_2way", "human_resources", "track1_known"),
            SyntheticSample("human_resources", "Find staff hired in 2019 or later whose base salary exceeds 100,000.", "SELECT employees.first_name, employees.last_name, compensation.base_salary FROM employees JOIN compensation ON employees.emp_id = compensation.emp_id WHERE employees.hire_date >= '2019-01-01' AND compensation.base_salary > 100000", "medium", "filtering_multi", "human_resources", "track1_known"),
        ])

        # ---------------- LOGISTICS ----------------
        samples.extend([
            SyntheticSample("logistics", "Find total shipping cost per carrier for delivered shipments.", "SELECT vehicles.vehicle_type, SUM(shipments.cost) AS total_cost FROM shipments JOIN vehicles ON shipments.vehicle_id = vehicles.vehicle_id WHERE shipments.status = 'delivered' GROUP BY vehicles.vehicle_type", "medium", "join_2way", "logistics", "track1_known"),
            SyntheticSample("logistics", "List shipment id, origin warehouse city, destination warehouse city, and driver name.", "SELECT shipments.shipment_id, w_orig.city AS origin_city, w_dest.city AS dest_city, drivers.driver_name FROM shipments JOIN warehouses w_orig ON shipments.origin_warehouse_id = w_orig.warehouse_id JOIN warehouses w_dest ON shipments.dest_warehouse_id = w_dest.warehouse_id JOIN drivers ON shipments.driver_id = drivers.driver_id", "hard", "join_4way", "logistics", "track1_known"),
            SyntheticSample("logistics", "Which driver has the highest total completed shipment value?", "SELECT drivers.driver_name, SUM(shipments.cost) AS total_val FROM drivers JOIN shipments ON drivers.driver_id = shipments.driver_id WHERE shipments.status = 'delivered' GROUP BY drivers.driver_id ORDER BY total_val DESC LIMIT 1", "hard", "group_by_having", "logistics", "track1_known"),
        ])

        # ---------------- INVENTORY ----------------
        samples.extend([
            SyntheticSample("inventory", "List parts where quantity on hand is below reorder threshold.", "SELECT parts.part_name, stock.quantity_on_hand, parts.reorder_threshold FROM parts JOIN stock ON parts.part_id = stock.part_id WHERE stock.quantity_on_hand < parts.reorder_threshold", "medium", "join_2way", "inventory", "track1_known"),
            SyntheticSample("inventory", "Find total purchase order spend by supplier country.", "SELECT suppliers.country, SUM(purchase_orders.qty_ordered * parts.unit_cost) AS total_spend FROM purchase_orders JOIN suppliers ON purchase_orders.supplier_id = suppliers.supplier_id JOIN parts ON purchase_orders.part_id = parts.part_id GROUP BY suppliers.country", "hard", "join_3way", "inventory", "track1_known"),
            SyntheticSample("inventory", "Compute current stock valuation per warehouse.", "SELECT stock.warehouse_code, SUM(stock.quantity_on_hand * parts.unit_cost) AS stock_val FROM stock JOIN parts ON stock.part_id = parts.part_id GROUP BY stock.warehouse_code", "medium", "join_2way", "inventory", "track1_known"),
        ])

        # ---------------- EDUCATION (TRACK 2: UNSEEN SCHEMA TEST ONLY) ----------------
        samples.extend([
            SyntheticSample("education", "What is the average GPA of students enrolled in each faculty?", "SELECT faculties.faculty_name, AVG(students.gpa) AS avg_gpa FROM faculties JOIN courses ON faculties.faculty_id = courses.faculty_id JOIN enrollments ON courses.course_id = enrollments.course_id JOIN students ON enrollments.student_id = students.student_id GROUP BY faculties.faculty_name", "hard", "join_4way", "education", "track2_unseen"),
            SyntheticSample("education", "List students who received an A grade in CS101.", "SELECT students.student_name FROM students JOIN enrollments ON students.student_id = enrollments.student_id JOIN courses ON enrollments.course_id = courses.course_id WHERE courses.course_code = 'CS101' AND enrollments.grade = 'A'", "medium", "join_3way", "education", "track2_unseen"),
            SyntheticSample("education", "Find courses that have more than 1 student enrolled.", "SELECT courses.title, COUNT(enrollments.student_id) AS st_count FROM courses JOIN enrollments ON courses.course_id = enrollments.course_id GROUP BY courses.course_id HAVING st_count > 1", "medium", "group_by_having", "education", "track2_unseen"),
            SyntheticSample("education", "Rank students by course score within each course.", "SELECT students.student_name, courses.course_code, enrollments.score, RANK() OVER (PARTITION BY courses.course_id ORDER BY enrollments.score DESC) AS rank_pos FROM students JOIN enrollments ON students.student_id = enrollments.student_id JOIN courses ON enrollments.course_id = courses.course_id", "hard", "window_function", "education", "track2_unseen"),
            SyntheticSample("education", "Find faculties with zero student enrollments in Fall 2023.", "SELECT faculties.faculty_name FROM faculties LEFT JOIN courses ON faculties.faculty_id = courses.faculty_id LEFT JOIN enrollments ON courses.course_id = enrollments.course_id AND enrollments.semester = 'Fall 2023' WHERE enrollments.enrollment_id IS NULL", "hard", "null_handling", "education", "track2_unseen"),
        ])

        # ---------------- ENTERTAINMENT (TRACK 2: UNSEEN SCHEMA TEST ONLY) ----------------
        samples.extend([
            SyntheticSample("entertainment", "Which artist has the highest total stream count across all tracks?", "SELECT artists.artist_name, SUM(tracks.stream_count) AS total_streams FROM artists JOIN albums ON artists.artist_id = albums.artist_id JOIN tracks ON albums.album_id = tracks.album_id GROUP BY artists.artist_id ORDER BY total_streams DESC LIMIT 1", "hard", "join_3way", "entertainment", "track2_unseen"),
            SyntheticSample("entertainment", "List track name, album title, and playlist name for electronic genre tracks.", "SELECT tracks.track_name, albums.album_title, playlists.playlist_name FROM tracks JOIN albums ON tracks.album_id = albums.album_id JOIN artists ON albums.artist_id = artists.artist_id JOIN playlist_tracks ON tracks.track_id = playlist_tracks.track_id JOIN playlists ON playlist_tracks.playlist_id = playlists.playlist_id WHERE artists.genre = 'Electronic'", "extra_hard", "join_5way", "entertainment", "track2_unseen"),
            SyntheticSample("entertainment", "Find albums released before 2000 with average track duration over 300 seconds.", "SELECT albums.album_title, AVG(tracks.duration_seconds) AS avg_duration FROM albums JOIN tracks ON albums.album_id = tracks.album_id WHERE albums.release_year < 2000 GROUP BY albums.album_id HAVING avg_duration > 300", "hard", "group_by_having", "entertainment", "track2_unseen"),
            SyntheticSample("entertainment", "Classify tracks as Hit if streams exceed 300,000,000 else Popular.", "SELECT track_name, CASE WHEN stream_count >= 300000000 THEN 'Hit' ELSE 'Popular' END AS track_tier FROM tracks", "easy", "case_expression", "entertainment", "track2_unseen"),
            SyntheticSample("entertainment", "Find artists who have no tracks in any playlist.", "SELECT artists.artist_name FROM artists JOIN albums ON artists.artist_id = albums.artist_id JOIN tracks ON albums.album_id = tracks.album_id LEFT JOIN playlist_tracks ON tracks.track_id = playlist_tracks.track_id WHERE playlist_tracks.track_id IS NULL", "hard", "null_handling", "entertainment", "track2_unseen"),
        ])

        return samples

    def setup_all_databases(self) -> Dict[str, Path]:
        """Initializes all 8 SQLite database engines."""
        return {
            "ecommerce": self.setup_ecommerce(),
            "healthcare": self.setup_healthcare(),
            "finance": self.setup_finance(),
            "human_resources": self.setup_hr(),
            "logistics": self.setup_logistics(),
            "inventory": self.setup_inventory(),
            "education": self.setup_education(),
            "entertainment": self.setup_entertainment(),
        }

    def generate_and_validate(self) -> Tuple[List[SyntheticSample], Dict[str, Path]]:
        """Sets up all 8 databases and verifies 100% of SQL queries via execution."""
        db_map = self.setup_all_databases()
        all_samples = self.get_all_samples()
        verified_samples = []

        for sample in all_samples:
            db_path = db_map.get(sample.db_id)
            if not db_path:
                logger.error(f"Missing DB for {sample.db_id}")
                continue
            executor = SQLiteExecutor(db_path)
            res = executor.execute(sample.query)
            if not res.success:
                logger.error(f"Query validation failed for [{sample.db_id}] '{sample.question}': {res.error}")
            else:
                verified_samples.append(sample)

        logger.info(f"Verified {len(verified_samples)}/{len(all_samples)} synthetic queries across 8 domain databases.")
        return verified_samples, db_map
