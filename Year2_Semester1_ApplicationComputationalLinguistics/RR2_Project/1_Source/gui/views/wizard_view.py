"""Screen 5: Run Pipeline View — 14-stage ontology matching execution and monitoring."""

from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ..services.experiment_runner_service import WIZARD_14_STAGES
from ..state import WorkbenchState
from ..styles import PALETTE, SPACE_SM
from ..widgets import (
    configure_table,
    confirm_destructive_action,
    create_button,
    create_page_header,
    make_status_item,
    show_error_dialog,
    show_warning_dialog,
)


class ReplicationWizardView(QWidget):
    """Guides execution across all 14 Agent-OM pipeline stages with safe cancellation."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._build_ui()
        self._connect_signals()
        self._refresh_summary_banner()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header_w, _ = create_page_header(
            "Run Pipeline",
            "Run the 14-stage ontology matching pipeline and monitor stage progress.",
        )
        root.addWidget(header_w)

        banner_frame = QFrame()
        banner_frame.setObjectName("SummaryBanner")
        ban_lay = QVBoxLayout(banner_frame)
        ban_lay.setContentsMargins(10, 6, 10, 6)
        self.lbl_banner = QLabel("")
        self.lbl_banner.setWordWrap(True)
        self.lbl_banner.setStyleSheet(f"color: {PALETTE.text_primary}; font-size: 12px; background: transparent;")
        ban_lay.addWidget(self.lbl_banner)
        root.addWidget(banner_frame)

        # Execution controls (two responsive rows to prevent clipping)
        grp_ctrl = QGroupBox("Execution Controls")
        ctrl_outer = QVBoxLayout(grp_ctrl)
        ctrl_outer.setSpacing(10)

        row_opts = QHBoxLayout()
        row_opts.setSpacing(SPACE_SM)
        self.txt_exp_id = QLineEdit(f"gui_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.txt_exp_id.setPlaceholderText("Unique experiment run ID")
        self.txt_exp_id.setAccessibleName("Experiment ID")
        self.chk_cap = QCheckBox("Limit entities per side:")
        self.spn_cap = QSpinBox()
        self.spn_cap.setRange(1, 500)
        self.spn_cap.setValue(4)
        self.spn_cap.setAccessibleName("Maximum entities per side")
        self.chk_skip_ret = QCheckBox("Reuse indexed database")

        row_opts.addWidget(QLabel("Experiment ID:"))
        row_opts.addWidget(self.txt_exp_id, stretch=1)
        row_opts.addWidget(self.chk_cap)
        row_opts.addWidget(self.spn_cap)
        row_opts.addWidget(self.chk_skip_ret)
        ctrl_outer.addLayout(row_opts)

        row_actions = QHBoxLayout()
        row_actions.setSpacing(SPACE_SM)
        self.btn_run_local = create_button(
            "Run Matching",
            role="primary",
            tooltip="Start the local Agent-OM ontology matching pipeline",
            accessible_name="Run Matching",
        )
        self.btn_run_local.clicked.connect(self._on_start_local)

        self.btn_run_upstream = create_button(
            "Run Baseline",
            role="secondary",
            tooltip="Execute the isolated upstream Agent-OM-Lite baseline runner",
            accessible_name="Run Upstream Baseline",
        )
        self.btn_run_upstream.clicked.connect(self._on_start_upstream)

        self.btn_cancel = create_button(
            "Cancel Run",
            role="destructive",
            tooltip="Stop the running experiment at the next safe checkpoint",
            accessible_name="Cancel Active Run",
        )
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setAccessibleName("Pipeline progress")

        row_actions.addWidget(self.btn_run_local)
        row_actions.addWidget(self.btn_run_upstream)
        row_actions.addWidget(self.btn_cancel)
        row_actions.addWidget(self.progress, stretch=1)
        ctrl_outer.addLayout(row_actions)
        root.addWidget(grp_ctrl)

        # 14-Stage table
        grp_stages = QGroupBox("Pipeline Stages")
        lay_stages = QVBoxLayout(grp_stages)
        self.tbl_stages = QTableWidget(len(WIZARD_14_STAGES), 3)
        self.tbl_stages.setHorizontalHeaderLabels(["Stage", "Status", "Progress Details"])
        configure_table(self.tbl_stages, stretch_last=False)
        self.tbl_stages.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_stages.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_stages.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._reset_stage_table()
        lay_stages.addWidget(self.tbl_stages)
        root.addWidget(grp_stages, stretch=2)

        # Compact live log tail
        grp_log = QGroupBox("Execution Log")
        lay_log = QVBoxLayout(grp_log)
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(400)
        self.txt_log.setPlaceholderText("Stage telemetry and progress logs appear here during execution.")
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
            f"Dataset: {ds_label}  |  Profile: {cfg.profile_name}  |  "
            f"Chat: {cfg.default_llm}  |  Embeddings: {cfg.default_embedding_model}  |  "
            f"DB: {cfg.db_name}  |  Threshold: {cfg.similarity_threshold:.2f}  |  Routing: {cfg.tool_routing_mode}"
        )

    def _reset_stage_table(self) -> None:
        from PySide6.QtWidgets import QTableWidgetItem

        for i, st in enumerate(WIZARD_14_STAGES):
            it0 = QTableWidgetItem(st["title"])
            it1 = make_status_item("Ready" if i < 3 else "Pending", level="success" if i < 3 else "neutral")
            it2 = QTableWidgetItem("Configured" if i < 3 else "-")
            self.tbl_stages.setItem(i, 0, it0)
            self.tbl_stages.setItem(i, 1, it1)
            self.tbl_stages.setItem(i, 2, it2)

    def _set_stage_row(self, row: int, status: str, detail: str) -> None:
        lvl_map = {
            "Ready": "success",
            "Completed": "success",
            "Running": "info",
            "Cancelled": "warning",
            "Failed": "error",
            "Pending": "neutral",
        }
        self.tbl_stages.setItem(row, 1, make_status_item(status, level=lvl_map.get(status, "neutral")))
        if detail:
            it2 = self.tbl_stages.item(row, 2)
            if it2:
                it2.setText(detail)
                it2.setToolTip(detail)

    def _on_cancel_clicked(self) -> None:
        if confirm_destructive_action(
            self,
            "Cancel Experiment",
            "Stop the running experiment at the next safe checkpoint?",
        ):
            self.state.runner_service.cancel_active_run()

    def _on_start_local(self) -> None:
        cfg = self.state.active_config
        check = self.state.config_service.validate_for_execution(cfg)
        if not check["valid"]:
            show_warning_dialog(self, "Configuration Blocked", "\n".join(check["issues"]))
            return
        ds = self.state.selected_dataset
        if ds is None:
            show_warning_dialog(self, "No Dataset Selected", "Select a dataset on the Datasets screen before running.")
            return
        exp_id = self.txt_exp_id.text().strip()
        if not exp_id:
            show_warning_dialog(self, "Missing Experiment ID", "Enter a unique Experiment ID.")
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
            show_error_dialog(
                self,
                "Launch Failed",
                exc,
                "Verify that PostgreSQL and Ollama are reachable on 127.0.0.1.",
            )

    def _on_start_upstream(self) -> None:
        exp_id = self.txt_exp_id.text().strip()
        if not exp_id:
            show_warning_dialog(self, "Missing Experiment ID", "Enter a unique Experiment ID.")
            return
        cap = int(self.spn_cap.value()) if self.chk_cap.isChecked() else None
        self._reset_stage_table()
        try:
            self.state.runner_service.start_upstream_isolated_run(
                experiment_id=exp_id, max_entities=cap
            )
        except Exception as exc:
            show_error_dialog(self, "Launch Failed", exc)

    def _on_run_started(self, exp_id: str) -> None:
        self.btn_run_local.setEnabled(False)
        self.btn_run_upstream.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress.setValue(5)
        self.txt_log.appendPlainText(f"Started experiment: {exp_id}")

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
                self._set_stage_row(prev, "Completed", "")
            self._set_stage_row(row_idx, "Running", f"({cur}/{tot}) {msg}")
            self.progress.setValue(base_pct)

    def _restore_buttons(self) -> None:
        self.btn_run_local.setEnabled(True)
        self.btn_run_upstream.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.txt_exp_id.setText(f"gui_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    def _on_run_finished(self, summary: dict) -> None:
        for i in range(len(WIZARD_14_STAGES)):
            self._set_stage_row(i, "Completed", "")
        fm = summary.get("final_metrics") or {}
        self._set_stage_row(
            13,
            "Completed",
            f"F1={fm.get('f1_pct', 0.0):.2f}% (P={fm.get('precision_pct', 0.0):.2f}%, R={fm.get('recall_pct', 0.0):.2f}%)",
        )
        self.progress.setValue(100)
        self._restore_buttons()

    def _on_run_cancelled(self, summary: dict) -> None:
        self._set_stage_row(13, "Cancelled", "Stopped cleanly by user")
        self._restore_buttons()

    def _on_run_failed(self, err: str) -> None:
        self._set_stage_row(13, "Failed", err)
        self._restore_buttons()
        show_error_dialog(self, "Experiment Failed", err, "Inspect the execution log for details.")
