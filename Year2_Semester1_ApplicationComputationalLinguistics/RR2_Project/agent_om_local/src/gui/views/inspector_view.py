"""Screen 6: Pipeline Inspector View — Searchable/sortable intermediate artifact explorer."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState


class PipelineInspectorView(QWidget):
    """Inspects per-entity representations, similarity scores, RRF groups, and validations."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._rows: List[Dict[str, Any]] = []
        self._build_ui()
        self.state.runs_updated.connect(self.refresh_run_list)
        self.refresh_run_list()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        title = QLabel("Pipeline Intermediate Output & Entity Alignment Inspector")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        root.addWidget(title)

        top = QHBoxLayout()
        self.cmb_run = QComboBox()
        self.cmb_run.currentIndexChanged.connect(self._on_load_selected_run)
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Filter by URI, entity_id, type, or matched target...")
        btn_reload = QPushButton("Reload Runs")
        btn_reload.clicked.connect(self.refresh_run_list)
        top.addWidget(QLabel("Select Run:"))
        top.addWidget(self.cmb_run, stretch=1)
        top.addWidget(QLabel("Search:"))
        top.addWidget(self.txt_filter, stretch=1)
        top.addWidget(btn_reload)
        root.addLayout(top)

        splitter = QSplitter(Qt.Vertical)

        # Sortable/filterable QTableView
        self.model = QStandardItemModel(0, 7, self)
        self.model.setHorizontalHeaderLabels(
            [
                "Entity ID",
                "Side",
                "Type",
                "Syntactic Name",
                "Cand Count",
                "Validations",
                "Final Reciprocal Match",
            ]
        )
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy.setFilterKeyColumn(-1)
        self.txt_filter.textChanged.connect(self.proxy.setFilterFixedString)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.selectionModel().selectionChanged.connect(self._on_row_selected)
        splitter.addWidget(self.table)

        # Detail tabs
        self.tabs = QTabWidget()
        self.txt_reps = QPlainTextEdit()
        self.txt_reps.setReadOnly(True)
        self.txt_cands = QPlainTextEdit()
        self.txt_cands.setReadOnly(True)
        self.txt_vals = QPlainTextEdit()
        self.txt_vals.setReadOnly(True)
        for t in (self.txt_reps, self.txt_cands, self.txt_vals):
            t.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        self.tabs.addTab(self.txt_reps, "1. Syntactic / Lexical / Semantic Representations")
        self.tabs.addTab(self.txt_cands, "2. Strategy Similarity Scores & RRF Rankings")
        self.tabs.addTab(self.txt_vals, "3. LLM Validation Prompts, Bypass & Decisions")
        splitter.addWidget(self.tabs)
        splitter.setSizes([360, 260])

        root.addWidget(splitter, stretch=1)

    def refresh_run_list(self) -> None:
        runs = self.state.history_service.list_runs(include_historical=False)
        self.cmb_run.blockSignals(True)
        self.cmb_run.clear()
        for r in runs:
            self.cmb_run.addItem(str(r["display_name"]), userData=str(r["experiment_id"]))
        self.cmb_run.blockSignals(False)
        if self.cmb_run.count() > 0:
            self._on_load_selected_run()

    def _on_load_selected_run(self) -> None:
        exp_id = self.cmb_run.currentData()
        if not exp_id:
            return
        self._rows = self.state.inspection_service.build_entity_inspection_rows(str(exp_id))
        self.model.removeRows(0, self.model.rowCount())
        for idx, row in enumerate(self._rows):
            items = [
                QStandardItem(str(row["entity_id"])),
                QStandardItem(str(row["side"])),
                QStandardItem(str(row["entity_type"])),
                QStandardItem(str(row["syntactic_text"])),
                QStandardItem(str(row["candidate_count"])),
                QStandardItem(str(row["validation_attempts"])),
                QStandardItem(str(row["final_matched_uris"])),
            ]
            items[0].setData(idx, Qt.UserRole)
            self.model.appendRow(items)

    def _on_row_selected(self) -> None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return
        src_index = self.proxy.mapToSource(indexes[0])
        raw_idx = self.model.item(src_index.row(), 0).data(Qt.UserRole)
        if raw_idx is None or not (0 <= int(raw_idx) < len(self._rows)):
            return
        r = self._rows[int(raw_idx)]
        rep_txt = (
            f"Entity ID:   {r['entity_id']}\n"
            f"Entity URI:  {r['entity_uri']} ({r['side']} — {r['entity_type']})\n"
            f"Final Match: {r['final_matched_uris'] or '(None)'}\n\n"
            f"--- SYNTACTIC REPRESENTATION ---\n{r['syntactic_text']}\n\n"
            f"--- LEXICAL EXPLANATION ---\n{r['lexical_text']}\n\n"
            f"--- SEMANTIC SUBGRAPH VERBALIZATION ---\n{r['semantic_text']}\n"
        )
        self.txt_reps.setPlainText(rep_txt)
        self.txt_cands.setPlainText(json.dumps(r["candidate_detail"], indent=2))
        self.txt_vals.setPlainText(json.dumps(r["validation_detail"], indent=2))

