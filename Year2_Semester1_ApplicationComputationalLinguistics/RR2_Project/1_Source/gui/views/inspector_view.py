"""Screen 6: Inspector View — Searchable entity representations, candidate scores, and decisions."""

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
    QSplitter,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState
from ..styles import SPACE_SM
from ..widgets import configure_table, create_button, create_page_header


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
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        btn_reload = create_button(
            "Refresh",
            role="secondary",
            tooltip="Reload available experiment runs and inspection data",
            accessible_name="Refresh Runs",
        )
        btn_reload.clicked.connect(self.refresh_run_list)
        header_w, _ = create_page_header(
            "Inspector",
            "Examine extracted entity representations, candidate similarity scores, and validation decisions.",
            right_widget=btn_reload,
        )
        root.addWidget(header_w)

        top = QHBoxLayout()
        top.setSpacing(SPACE_SM)
        self.cmb_run = QComboBox()
        self.cmb_run.setAccessibleName("Experiment Run Selector")
        self.cmb_run.currentIndexChanged.connect(self._on_load_selected_run)
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Filter by entity ID, URI, type, or target")
        self.txt_filter.setAccessibleName("Filter entities")
        top.addWidget(QLabel("Experiment:"))
        top.addWidget(self.cmb_run, stretch=1)
        top.addWidget(QLabel("Filter:"))
        top.addWidget(self.txt_filter, stretch=1)
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
                "Candidates",
                "Validations",
                "Final Match",
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
        configure_table(self.table, stretch_last=False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.selectionModel().selectionChanged.connect(self._on_row_selected)
        splitter.addWidget(self.table)

        # Detail tabs
        self.tabs = QTabWidget()
        self.txt_reps = QPlainTextEdit()
        self.txt_reps.setReadOnly(True)
        self.txt_reps.setPlaceholderText("Select a row above to view its syntactic, lexical, and semantic representations.")
        self.txt_cands = QPlainTextEdit()
        self.txt_cands.setReadOnly(True)
        self.txt_cands.setPlaceholderText("Select a row above to view retrieval similarity scores and RRF rankings.")
        self.txt_vals = QPlainTextEdit()
        self.txt_vals.setReadOnly(True)
        self.txt_vals.setPlaceholderText("Select a row above to view LLM validation prompts and decisions.")

        self.tabs.addTab(self.txt_reps, "Entity Representations")
        self.tabs.addTab(self.txt_cands, "Retrieval && RRF Scores")
        self.tabs.addTab(self.txt_vals, "Validation Decisions")
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
            final_uris = str(row["final_matched_uris"])
            it_id = QStandardItem(str(row["entity_id"]))
            it_id.setToolTip(str(row["entity_uri"]))
            it_side = QStandardItem(str(row["side"]))
            it_type = QStandardItem(str(row["entity_type"]))
            it_syn = QStandardItem(str(row["syntactic_text"]))
            it_cand = QStandardItem(str(row["candidate_count"]))
            it_cand.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_val = QStandardItem(str(row["validation_attempts"]))
            it_val.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_match = QStandardItem(final_uris)
            if final_uris:
                it_match.setToolTip(final_uris)

            items = [it_id, it_side, it_type, it_syn, it_cand, it_val, it_match]
            items[0].setData(idx, Qt.UserRole)
            self.model.appendRow(items)
        if self.proxy.rowCount() > 0:
            self.table.selectRow(0)

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
            f"Entity URI:  {r['entity_uri']} ({r['side']} - {r['entity_type']})\n"
            f"Final Match: {r['final_matched_uris'] or '(None)'}\n\n"
            f"--- SYNTACTIC REPRESENTATION ---\n{r['syntactic_text']}\n\n"
            f"--- LEXICAL EXPLANATION ---\n{r['lexical_text']}\n\n"
            f"--- SEMANTIC SUBGRAPH VERBALIZATION ---\n{r['semantic_text']}\n"
        )
        self.txt_reps.setPlainText(rep_txt)
        self.txt_cands.setPlainText(json.dumps(r["candidate_detail"], indent=2))
        self.txt_vals.setPlainText(json.dumps(r["validation_detail"], indent=2))
