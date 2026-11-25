"""Screen 10: Export View — Non-destructive export of CSV, JSON, RDF XML, PNG charts, and reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState
from ..styles import PALETTE, SPACE_SM
from ..widgets import (
    create_button,
    create_page_header,
    show_error_dialog,
)


class ReportExportView(QWidget):
    """Exports timestamped, non-destructive replication bundles into `output/replication_runs/exports/`."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._build_ui()
        self.state.runs_updated.connect(self.refresh_runs)
        self.refresh_runs()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        header_w, _ = create_page_header(
            "Export",
            "Export benchmark tables, evaluation charts, RDF/XML alignments, and summary reports.",
        )
        root.addWidget(header_w)

        grp_cfg = QGroupBox("Export Settings")
        form = QFormLayout(grp_cfg)
        form.setSpacing(10)

        self.cmb_run = QComboBox()
        self.cmb_run.setAccessibleName("Experiment run to include in export")
        form.addRow("Experiment Run:", self.cmb_run)

        self.txt_bundle_name = QLineEdit(f"replication_bundle_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.txt_bundle_name.setAccessibleName("Export folder name")
        form.addRow("Folder Name:", self.txt_bundle_name)

        dir_lay = QHBoxLayout()
        dir_lay.setSpacing(SPACE_SM)
        self.txt_parent_dir = QLineEdit(str(self.state.paths.exports_dir))
        self.txt_parent_dir.setToolTip(str(self.state.paths.exports_dir))
        self.txt_parent_dir.setAccessibleName("Output directory path")
        btn_browse = create_button(
            "Browse",
            role="secondary",
            tooltip="Select destination folder for exported results",
            accessible_name="Browse Output Directory",
        )
        btn_browse.clicked.connect(self._on_browse_dir)
        dir_lay.addWidget(self.txt_parent_dir, stretch=1)
        dir_lay.addWidget(btn_browse)
        form.addRow("Output Directory:", dir_lay)

        included_lbl = QLabel(
            "- benchmark_comparison.csv and benchmark_comparison.json\n"
            "- High-DPI PNG charts (Precision/Recall/F1, Scatter, Stage Attrition, Threshold Sensitivity)\n"
            "- Selected run alignments (RDF/XML, CSV predictions), validation logs, and JSON snapshots\n"
            "- replication_export_report.md (plus final_replication_report.md when present)"
        )
        included_lbl.setProperty("labelRole", "meta")
        included_lbl.setWordWrap(True)
        form.addRow("Included Files:", included_lbl)
        root.addWidget(grp_cfg)

        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(SPACE_SM)
        btn_refresh = create_button(
            "Refresh",
            role="secondary",
            tooltip="Reload available experiment runs",
            accessible_name="Refresh Export Runs",
        )
        btn_refresh.clicked.connect(self.refresh_runs)
        self.btn_export = create_button(
            "Export Results",
            role="primary",
            tooltip="Create a timestamped export bundle in the output directory",
            accessible_name="Export Results",
        )
        self.btn_export.clicked.connect(self._on_export)
        btn_lay.addWidget(btn_refresh)
        btn_lay.addStretch(1)
        btn_lay.addWidget(self.btn_export)
        root.addLayout(btn_lay)

        grp_out = QGroupBox("Export Log")
        out_lay = QVBoxLayout(grp_out)
        self.txt_manifest = QPlainTextEdit()
        self.txt_manifest.setReadOnly(True)
        self.txt_manifest.setPlaceholderText("Exported directory path and file manifest will appear here.")
        out_lay.addWidget(self.txt_manifest)
        root.addWidget(grp_out, stretch=1)

    def refresh_runs(self) -> None:
        self.cmb_run.clear()
        self.cmb_run.addItem("(Benchmark summary, charts, and reports only)", "")
        for rec in self.state.history_service.list_runs(include_historical=False):
            exp_id = str(rec.get("experiment_id", ""))
            label = f"{rec.get('display_name', exp_id)} (F1={float(rec.get('f1_pct', 0.0)):.2f}%)"
            self.cmb_run.addItem(label, exp_id)
        if self.cmb_run.count() > 1:
            self.cmb_run.setCurrentIndex(1)

    def _on_browse_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.txt_parent_dir.text()
        )
        if chosen:
            chosen_path = Path(chosen).resolve()
            orig_dir = self.state.paths.original_repo_dir.resolve()
            if chosen_path == orig_dir or orig_dir in chosen_path.parents:
                show_error_dialog(
                    self,
                    "Read-Only Restriction",
                    "Exporting into original_repo/ is not permitted.",
                    "Choose a directory under output/replication_runs/exports/ or another writable location.",
                )
                return
            self.txt_parent_dir.setText(str(chosen_path))

    def _on_export(self) -> None:
        parent_dir = Path(self.txt_parent_dir.text().strip() or str(self.state.paths.exports_dir)).resolve()
        orig_dir = self.state.paths.original_repo_dir.resolve()
        if parent_dir == orig_dir or orig_dir in parent_dir.parents:
            show_error_dialog(
                self,
                "Read-Only Restriction",
                "Exporting into original_repo/ is not permitted.",
                "Choose a directory under output/replication_runs/exports/ or another writable location.",
            )
            return

        bundle_name = self.txt_bundle_name.text().strip() or None
        selected_exp = str(self.cmb_run.currentData() or "") or None
        try:
            result = self.state.report_service.export_full_bundle(
                export_name=bundle_name,
                selected_experiment_id=selected_exp,
                target_parent_dir=parent_dir,
            )
            lines = [
                "Completed: Export bundle created.",
                f"Directory: {result['export_dir']}",
                f"Files written: {len(result['files'])}",
                "",
                "Files:",
            ]
            for fpath in result["files"]:
                lines.append(f"  - {fpath}")
            self.txt_manifest.setPlainText("\n".join(lines))
            self.txt_bundle_name.setText(f"replication_bundle_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        except Exception as exc:
            show_error_dialog(
                self,
                "Export Failed",
                exc,
                "Verify write permissions for the output directory.",
            )
