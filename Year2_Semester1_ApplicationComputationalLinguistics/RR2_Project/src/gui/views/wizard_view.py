"""Screen 5: Replication Wizard View — 14-stage guided execution with safe cancellation."""

from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..services.experiment_runner_service import WIZARD_14_STAGES
from ..state import WorkbenchState


class ReplicationWizardView(QWidget):
    """Guides the user through all 14 replication stages with live status and safe Cancel."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._build_ui()
        self._connect_signals()
        self._refresh_summary_banner()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel("14-Stage Guided Replication Wizard")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        root.addWidget(title)

        self.lbl_banner = QLabel("")
        self.lbl_banner.setWordWrap(True)
        self.lbl_banner.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px; padding: 6px;"
        )
        root.addWidget(self.lbl_banner)

        # Execution controls
        grp_ctrl = QGroupBox("Run Parameters & Execution Mode")
        ctrl_lay = QHBoxLayout(grp_ctrl)
        self.txt_exp_id = QLineEdit(f"gui_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.chk_cap = QCheckBox("Cap entities/side (smoke):")
        self.spn_cap = QSpinBox()
        self.spn_cap.setRange(1, 500)
        self.spn_cap.setValue(4)
        self.chk_skip_ret = QCheckBox("Matching-only (reuse DB hybrid memory)")

        self.btn_run_local = QPushButton("Run End-to-End Local Replication")
        self.btn_run_local.setStyleSheet(
            "background-color: #2563EB; color: white; font-weight: bold; padding: 6px 12px;"
        )
        self.btn_run_local.clicked.connect(self._on_start_local)

        self.btn_run_upstream = QPushButton("Run Isolated Upstream Agent-OM-Lite")
        self.btn_run_upstream.clicked.connect(self._on_start_upstream)

        self.btn_cancel = QPushButton("Cancel Active Run")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet(
            "background-color: #DC2626; color: white; font-weight: bold; padding: 6px 12px;"
        )
        self.btn_cancel.clicked.connect(self.state.runner_service.cancel_active_run)

        ctrl_lay.addWidget(QLabel("Experiment ID:"))
        ctrl_lay.addWidget(self.txt_exp_id, stretch=1)
        ctrl_lay.addWidget(self.chk_cap)
        ctrl_lay.addWidget(self.spn_cap)
        ctrl_lay.addWidget(self.chk_skip_ret)
        ctrl_lay.addWidget(self.btn_run_local)
        ctrl_lay.addWidget(self.btn_run_upstream)
        ctrl_lay.addWidget(self.btn_cancel)
        root.addWidget(grp_ctrl)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        root.addWidget(self.progress)

        # 14-Stage table
        grp_stages = QGroupBox("Replication Pipeline Stages (1–14)")
        lay_stages = QVBoxLayout(grp_stages)
        self.tbl_stages = QTableWidget(len(WIZARD_14_STAGES), 3)
        self.tbl_stages.setHorizontalHeaderLabels(["Stage", "Status", "Live Progress / Evidence"])
        self.tbl_stages.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_stages.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_stages.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_stages.setEditTriggers(QTableWidget.NoEditTriggers)
        self._reset_stage_table()
        lay_stages.addWidget(self.tbl_stages)
        root.addWidget(grp_stages, stretch=2)

        # Compact live log tail
        grp_log = QGroupBox("Live Stage Telemetry")
        lay_log = QVBoxLayout(grp_log)
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(400)
        self.txt_log.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        lay_log.addWidget(self.txt_log)
        root.addWidget(grp_log, stretch=1)

    def _connect_signals(self) -> None:
        self.state.dataset_changed.connect(lambda _: self._refresh_summary_banner())
        self.state.config_changed.connect(lambda _: self._refresh_summary_banner())
        r = self.state.runner_service
        r.run_started.connect(self._on_run_started)
        r.stage_updated.connect(self._on_stage_updated)
        r.log_emitted.connect(self.txt_log.appendPlainText)
        r.run_finished.connect(self._on_run_finished)
        r.run_cancelled.connect(self._on_run_cancelled)
        r.run_failed.connect(self._on_run_failed)

    def _refresh_summary_banner(self) -> None:
        ds = self.state.selected_dataset
        cfg = self.state.active_config
        ds_label = ds.dataset_id if ds else "None"
        self.lbl_banner.setText(
            f"Active Dataset: {ds_label}  |  Profile: {cfg.profile_name}  |  "
            f"LLM: {cfg.default_llm}  |  Embeddings: {cfg.default_embedding_model}  |  "
            f"Isolated DB: {cfg.db_name}  |  Threshold: {cfg.similarity_threshold:.2f}  |  Routing: {cfg.tool_routing_mode}"
        )

    def _reset_stage_table(self) -> None:
        for i, st in enumerate(WIZARD_14_STAGES):
            it0 = QTableWidgetItem(st["title"])
            it1 = QTableWidgetItem("READY" if i < 3 else "PENDING")
            it1.setTextAlignment(Qt.AlignCenter)
            if i < 3:
                it1.setBackground(QColor("#DCFCE7"))
            it2 = QTableWidgetItem("Configured in Workbench" if i < 3 else "—")
            self.tbl_stages.setItem(i, 0, it0)
            self.tbl_stages.setItem(i, 1, it1)
            self.tbl_stages.setItem(i, 2, it2)

    def _set_stage_row(self, row: int, status: str, detail: str) -> None:
        it1 = self.tbl_stages.item(row, 1)
        it2 = self.tbl_stages.item(row, 2)
        if it1:
            it1.setText(status)
            if status == "COMPLETED":
                it1.setBackground(QColor("#DCFCE7"))
            elif status == "RUNNING":
                it1.setBackground(QColor("#DBEAFE"))
            elif status in ("FAILED", "CANCELLED"):
                it1.setBackground(QColor("#FEE2E2"))
        if it2 and detail:
            it2.setText(detail)

    def _on_start_local(self) -> None:
        cfg = self.state.active_config
        check = self.state.config_service.validate_for_execution(cfg)
        if not check["valid"]:
            QMessageBox.warning(
                self, "Configuration Blocked", "\n".join(check["issues"])
            )
            return
        ds = self.state.selected_dataset
        if ds is None:
            QMessageBox.warning(self, "No Dataset", "Select an ontology dataset first.")
            return
        exp_id = self.txt_exp_id.text().strip()
        if not exp_id:
            QMessageBox.warning(self, "Missing ID", "Provide a unique Experiment ID.")
            return

        self._reset_stage_table()
        cap = int(self.spn_cap.value()) if self.chk_cap.isChecked() else None
        try:
            self.state.runner_service.start_local_run(
                experiment_id=exp_id,
                profile_name=cfg.profile_name,
                source_ontology_path=ds.source_path,
                target_ontology_path=ds.target_path,
                reference_alignment_path=ds.reference_path,
                db_name_override=cfg.db_name,
                max_entities_per_side=cap,
                skip_retrieval=self.chk_skip_ret.isChecked(),
                similarity_threshold=cfg.similarity_threshold,
                top_k=cfg.top_k,
                rrf_k=cfg.rrf_k,
                tool_routing_mode=cfg.tool_routing_mode,
                predicate_scope=cfg.predicate_scope,
                o1_is_code=cfg.o1_is_code,
                o2_is_code=cfg.o2_is_code,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Launch Failed", str(exc))

    def _on_start_upstream(self) -> None:
        exp_id = self.txt_exp_id.text().strip()
        cap = int(self.spn_cap.value()) if self.chk_cap.isChecked() else None
        self._reset_stage_table()
        try:
            self.state.runner_service.start_upstream_isolated_run(
                experiment_id=exp_id, max_entities=cap
            )
        except Exception as exc:
            QMessageBox.critical(self, "Launch Failed", str(exc))

    def _on_run_started(self, exp_id: str) -> None:
        self.btn_run_local.setEnabled(False)
        self.btn_run_upstream.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress.setValue(5)
        self.txt_log.appendPlainText(f"=== Started Experiment: {exp_id} ===")

    def _on_stage_updated(self, stage_key: str, cur: int, tot: int, msg: str) -> None:
        stage_map = {
            "1_ontology_loading": (3, 15),
            "2_entity_extraction": (4, 25),
            "3_source_retrieval": (5, 45),
            "4_target_retrieval": (7, 65),
            "5_vector_ingestion": (8, 80),
            "6_matching_validation": (11, 92),
            "7_complete": (13, 100),
        }
        if stage_key in stage_map:
            row_idx, base_pct = stage_map[stage_key]
            for prev in range(3, row_idx):
                self._set_stage_row(prev, "COMPLETED", "")
            self._set_stage_row(row_idx, "RUNNING", f"({cur}/{tot}) {msg}")
            self.progress.setValue(base_pct)

    def _restore_buttons(self) -> None:
        self.btn_run_local.setEnabled(True)
        self.btn_run_upstream.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.txt_exp_id.setText(f"gui_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    def _on_run_finished(self, summary: dict) -> None:
        for i in range(len(WIZARD_14_STAGES)):
            self._set_stage_row(i, "COMPLETED", "")
        fm = summary.get("final_metrics") or {}
        self._set_stage_row(
            13,
            "COMPLETED",
            f"F1={fm.get('f1_pct', 0.0):.2f}% (P={fm.get('precision_pct', 0.0):.2f}%, R={fm.get('recall_pct', 0.0):.2f}%)",
        )
        self.progress.setValue(100)
        self._restore_buttons()

    def _on_run_cancelled(self, summary: dict) -> None:
        self._set_stage_row(13, "CANCELLED", "Stopped cleanly by user")
        self._restore_buttons()

    def _on_run_failed(self, err: str) -> None:
        self._set_stage_row(13, "FAILED", err)
        self._restore_buttons()
        QMessageBox.critical(self, "Experiment Failed", err)

