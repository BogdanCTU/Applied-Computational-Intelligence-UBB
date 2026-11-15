"""Screen 2: Environment View — Live diagnostics for Python/.exe, GPU, PostgreSQL, and Ollama."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState


class EnvironmentView(QWidget):
    """Displays comprehensive environment, database, and local Ollama model diagnostics."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel("Environment, Database & Local Inference Diagnostics")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        btn_refresh = QPushButton("Run Full Health Check")
        btn_refresh.clicked.connect(self.refresh)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(btn_refresh)
        root.addLayout(top)

        # System & service checks
        grp_checks = QGroupBox("System & Loopback Service Checks")
        lay_checks = QVBoxLayout(grp_checks)
        self.tbl_checks = QTableWidget(0, 3)
        self.tbl_checks.setHorizontalHeaderLabels(["Component", "Status", "Details"])
        self.tbl_checks.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_checks.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_checks.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_checks.setEditTriggers(QTableWidget.NoEditTriggers)
        lay_checks.addWidget(self.tbl_checks)
        root.addWidget(grp_checks)

        # PostgreSQL databases inspector + isolated DB provisioning
        grp_db = QGroupBox("PostgreSQL Databases & pgvector Dimension Inspector (127.0.0.1:5432)")
        lay_db = QVBoxLayout(grp_db)
        self.tbl_dbs = QTableWidget(0, 6)
        self.tbl_dbs.setHorizontalHeaderLabels(
            [
                "Database",
                "Protection",
                "ontology_matching",
                "syntactic_matching",
                "lexical_matching",
                "semantic_matching",
            ]
        )
        self.tbl_dbs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_dbs.setEditTriggers(QTableWidget.NoEditTriggers)
        lay_db.addWidget(self.tbl_dbs)

        create_row = QHBoxLayout()
        create_row.addWidget(QLabel("Provision New Isolated Database:"))
        self.txt_new_db = QLineEdit()
        self.txt_new_db.setPlaceholderText("e.g. agent_om_gui_run")
        btn_create_db = QPushButton("Create Isolated DB + Enable pgvector")
        btn_create_db.clicked.connect(self._on_create_db)
        create_row.addWidget(self.txt_new_db)
        create_row.addWidget(btn_create_db)
        lay_db.addLayout(create_row)
        root.addWidget(grp_db)

        # Installed Ollama models
        grp_models = QGroupBox("Installed Local Ollama Models (127.0.0.1:11434 — Zero Cloud APIs)")
        lay_models = QVBoxLayout(grp_models)
        self.tbl_models = QTableWidget(0, 5)
        self.tbl_models.setHorizontalHeaderLabels(
            ["Model Name", "Family", "Parameters", "Quantization", "Size (GiB)"]
        )
        self.tbl_models.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_models.setEditTriggers(QTableWidget.NoEditTriggers)
        lay_models.addWidget(self.tbl_models)
        root.addWidget(grp_models)

    def _on_create_db(self) -> None:
        name = self.txt_new_db.text().strip()
        if not name:
            return
        try:
            self.state.db_service.create_isolated_database(name)
            QMessageBox.information(
                self, "Database Ready", f"Isolated database '{name}' is ready with pgvector enabled."
            )
            self.txt_new_db.clear()
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Database Creation Error", str(exc))

    def refresh(self) -> None:
        diag = self.state.env_service.run_full_diagnostics(
            db_service=self.state.db_service,
            ollama_service=self.state.ollama_service,
        )
        checks = diag.get("checks", [])
        self.tbl_checks.setRowCount(len(checks))
        for r, item in enumerate(checks):
            status = str(item.get("status", ""))
            c0 = QTableWidgetItem(str(item.get("component", "")))
            c1 = QTableWidgetItem(status)
            c1.setTextAlignment(Qt.AlignCenter)
            if status == "OK":
                c1.setBackground(QColor("#DCFCE7"))
            elif status == "ERROR":
                c1.setBackground(QColor("#FEE2E2"))
            else:
                c1.setBackground(QColor("#FEF3C7"))
            c2 = QTableWidgetItem(str(item.get("detail", "")))
            self.tbl_checks.setItem(r, 0, c0)
            self.tbl_checks.setItem(r, 1, c1)
            self.tbl_checks.setItem(r, 2, c2)

        pg = diag.get("postgresql", {})
        db_names = [
            d for d in pg.get("databases", []) if d.startswith("agent_om")
        ]
        self.tbl_dbs.setRowCount(len(db_names))
        for r, dname in enumerate(db_names):
            info = self.state.db_service.inspect_database(dname)
            rc = info.get("row_counts", {})
            vt = info.get("vector_types", {})
            prot = "PROTECTED (Read-Only)" if info.get("protected") else "Isolated (Writable)"
            vals = [
                dname,
                prot,
                str(rc.get("ontology_matching", 0)),
                f"{rc.get('syntactic_matching', 0)} ({vt.get('syntactic_matching') or '-'})",
                f"{rc.get('lexical_matching', 0)} ({vt.get('lexical_matching') or '-'})",
                f"{rc.get('semantic_matching', 0)} ({vt.get('semantic_matching') or '-'})",
            ]
            for col, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if col >= 2:
                    it.setTextAlignment(Qt.AlignCenter)
                self.tbl_dbs.setItem(r, col, it)

        ol = diag.get("ollama", {})
        models = ol.get("model_details", [])
        self.tbl_models.setRowCount(len(models))
        for r, m in enumerate(models):
            vals = [
                str(m.get("name", "")),
                str(m.get("family", "")),
                str(m.get("parameter_size", "")),
                str(m.get("quantization", "")),
                str(m.get("size_gb", "")),
            ]
            for col, v in enumerate(vals):
                self.tbl_models.setItem(r, col, QTableWidgetItem(v))

