"""Screen 2: Environment View — Runtime checks, PostgreSQL inspector, and Ollama model compliance."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState
from ..styles import SPACE_MD, SPACE_SM
from ..widgets import (
    configure_table,
    create_button,
    create_page_header,
    make_status_item,
    show_error_dialog,
    show_info_dialog,
)


class EnvironmentView(QWidget):
    """Displays environment checks, PostgreSQL vector tables, and local Ollama model metadata."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        btn_refresh = create_button(
            "Check Status",
            role="primary",
            tooltip="Re-run runtime, PostgreSQL, and Ollama model diagnostics",
            accessible_name="Check Environment Status",
        )
        btn_refresh.clicked.connect(self.refresh)
        header_w, _ = create_page_header(
            "Environment",
            "Verify local runtime, PostgreSQL vector tables, and installed Ollama models.",
            right_widget=btn_refresh,
        )
        root.addWidget(header_w)

        # System & service checks
        grp_checks = QGroupBox("System Status")
        lay_checks = QVBoxLayout(grp_checks)
        self.tbl_checks = QTableWidget(0, 3)
        self.tbl_checks.setHorizontalHeaderLabels(["Component", "Status", "Details"])
        configure_table(self.tbl_checks, stretch_last=False)
        self.tbl_checks.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_checks.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_checks.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        lay_checks.addWidget(self.tbl_checks)
        root.addWidget(grp_checks, stretch=2)

        # PostgreSQL databases inspector + isolated DB provisioning
        grp_db = QGroupBox("PostgreSQL Databases (127.0.0.1:5432)")
        lay_db = QVBoxLayout(grp_db)
        lay_db.setSpacing(SPACE_SM)
        self.tbl_dbs = QTableWidget(0, 6)
        self.tbl_dbs.setHorizontalHeaderLabels(
            [
                "Database",
                "Access Mode",
                "ontology_matching",
                "syntactic_matching",
                "lexical_matching",
                "semantic_matching",
            ]
        )
        configure_table(self.tbl_dbs, stretch_last=False)
        self.tbl_dbs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_dbs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        for c in range(2, 6):
            self.tbl_dbs.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        lay_db.addWidget(self.tbl_dbs)

        create_row = QHBoxLayout()
        create_row.setSpacing(SPACE_SM)
        create_row.addWidget(QLabel("New Database:"))
        self.txt_new_db = QLineEdit()
        self.txt_new_db.setPlaceholderText("e.g. agent_om_custom")
        self.txt_new_db.setAccessibleName("New isolated database name")
        btn_create_db = create_button(
            "Create Database",
            role="secondary",
            tooltip="Create an isolated PostgreSQL database and enable pgvector",
            accessible_name="Create Isolated Database",
        )
        btn_create_db.clicked.connect(self._on_create_db)
        create_row.addWidget(self.txt_new_db, stretch=1)
        create_row.addWidget(btn_create_db)
        lay_db.addLayout(create_row)
        root.addWidget(grp_db, stretch=2)

        # Installed Ollama models
        grp_models = QGroupBox("Installed Ollama Models (127.0.0.1:11434)")
        lay_models = QVBoxLayout(grp_models)
        self.tbl_models = QTableWidget(0, 7)
        self.tbl_models.setHorizontalHeaderLabels(
            [
                "Model",
                "Family",
                "Tag Size",
                "Parameters",
                "<=4B Policy",
                "Quantization",
                "Size (GiB)",
            ]
        )
        configure_table(self.tbl_models, stretch_last=False)
        self.tbl_models.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, 7):
            self.tbl_models.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        lay_models.addWidget(self.tbl_models)
        root.addWidget(grp_models, stretch=2)

    def _on_create_db(self) -> None:
        name = self.txt_new_db.text().strip()
        if not name:
            return
        try:
            self.state.db_service.create_isolated_database(name)
            show_info_dialog(
                self,
                "Database Ready",
                f"Isolated database '{name}' has been initialized with pgvector.",
            )
            self.txt_new_db.clear()
            self.refresh()
        except Exception as exc:
            show_error_dialog(
                self,
                "Database Error",
                exc,
                "Use an alphanumeric name (letters, numbers, underscores) other than 'agent_om_local'.",
            )

    def refresh(self) -> None:
        diag = self.state.env_service.run_full_diagnostics(
            db_service=self.state.db_service,
            ollama_service=self.state.ollama_service,
        )
        checks = diag.get("checks", [])
        self.tbl_checks.setRowCount(len(checks))
        for r, item in enumerate(checks):
            status = str(item.get("status", ""))
            detail = str(item.get("detail", ""))
            c0 = QTableWidgetItem(str(item.get("component", "")))
            lvl = "success" if status == "OK" else ("error" if status == "ERROR" else ("info" if status == "INFO" else "warning"))
            c1 = make_status_item(status, level=lvl)
            c2 = QTableWidgetItem(detail)
            c2.setToolTip(detail)
            self.tbl_checks.setItem(r, 0, c0)
            self.tbl_checks.setItem(r, 1, c1)
            self.tbl_checks.setItem(r, 2, c2)

        pg = diag.get("postgresql", {})
        db_names = [d for d in pg.get("databases", []) if d.startswith("agent_om")]
        self.tbl_dbs.setRowCount(len(db_names))
        for r, dname in enumerate(db_names):
            info = self.state.db_service.inspect_database(dname)
            rc = info.get("row_counts", {})
            vt = info.get("vector_types", {})
            is_prot = bool(info.get("protected"))
            self.tbl_dbs.setItem(r, 0, QTableWidgetItem(dname))
            self.tbl_dbs.setItem(
                r,
                1,
                make_status_item(
                    "Protected (Read-Only)" if is_prot else "Isolated (Writable)",
                    level="info" if is_prot else "success",
                ),
            )
            vals = [
                str(rc.get("ontology_matching", 0)),
                f"{rc.get('syntactic_matching', 0)} ({vt.get('syntactic_matching') or '-'})",
                f"{rc.get('lexical_matching', 0)} ({vt.get('lexical_matching') or '-'})",
                f"{rc.get('semantic_matching', 0)} ({vt.get('semantic_matching') or '-'})",
            ]
            for offset, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl_dbs.setItem(r, 2 + offset, it)

        ol = diag.get("ollama", {})
        models = ol.get("model_details", [])
        self.tbl_models.setRowCount(len(models))
        for r, m in enumerate(models):
            t_params = m.get("total_parameter_count")
            t_params_str = f"{int(t_params):,}" if isinstance(t_params, int) else "-"
            comp = m.get("is_strict_4b_compliant")
            comp_str = "Compliant (<=4B)" if comp is True else ("Exceeds 4B" if comp is False else "Unknown")
            comp_lvl = "success" if comp is True else ("warning" if comp is False else "neutral")

            it_name = QTableWidgetItem(str(m.get("name", "")))
            it_fam = QTableWidgetItem(str(m.get("family", "")))
            it_tag = QTableWidgetItem(str(m.get("parameter_size", "")))
            it_tag.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_params = QTableWidgetItem(t_params_str)
            it_params.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_comp = make_status_item(comp_str, level=comp_lvl)
            it_quant = QTableWidgetItem(str(m.get("quantization", "")))
            it_quant.setTextAlignment(Qt.AlignCenter)
            it_gb = QTableWidgetItem(str(m.get("size_gb", "")))
            it_gb.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.tbl_models.setItem(r, 0, it_name)
            self.tbl_models.setItem(r, 1, it_fam)
            self.tbl_models.setItem(r, 2, it_tag)
            self.tbl_models.setItem(r, 3, it_params)
            self.tbl_models.setItem(r, 4, it_comp)
            self.tbl_models.setItem(r, 5, it_quant)
            self.tbl_models.setItem(r, 6, it_gb)
