"""Screen 10: Report & Artifact Export View — Non-destructive export of CSV, JSON, RDF XML, PNG, and Markdown."""

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
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState


class ReportExportView(QWidget):
    """Exports timestamped, non-destructive replication bundles into `agent_om_local/output/exports/`."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._build_ui()
        self.state.runs_updated.connect(self.refresh_runs)
        self.refresh_runs()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        title = QLabel("Replication Report & Artifact Export")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        subtitle = QLabel(
            "Exports non-destructive timestamped bundles containing benchmark CSV/JSON tables, "
            "200-DPI Matplotlib PNG charts, OAEI Alignment API RDF/XML & CSV predictions, and Markdown reports. "
            "Never overwrites existing outputs or modifies original_repo/."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #334155;")
        root.addWidget(title)
        root.addWidget(subtitle)

        grp_cfg = QGroupBox("Export Bundle Configuration")
        form = QFormLayout(grp_cfg)

        self.cmb_run = QComboBox()
        form.addRow("Include Run Artifacts:", self.cmb_run)

        self.txt_bundle_name = QLineEdit(f"replication_bundle_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        form.addRow("Bundle Folder Name:", self.txt_bundle_name)

        dir_lay = QHBoxLayout()
        self.txt_parent_dir = QLineEdit(str(self.state.paths.exports_dir))
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._on_browse_dir)
        dir_lay.addWidget(self.txt_parent_dir, stretch=1)
        dir_lay.addWidget(btn_browse)
        form.addRow("Target Parent Directory:", dir_lay)

        included_lbl = QLabel(
            "Included in bundle:\n"
            "  • benchmark_comparison.csv & benchmark_comparison.json\n"
            "  • High-DPI PNG charts (Precision/Recall/F1, Threshold Sensitivity, Stage Attrition, Runtime & Calls)\n"
            "  • Selected run's alignments (OAEI RDF/XML, 6 CSV variants), validation_records.csv, and JSON snapshots\n"
            "  • replication_export_report.md (+ final_replication_report.md if present in docs/)"
        )
        included_lbl.setStyleSheet("color: #475569; font-size: 11px;")
        form.addRow("Artifacts:", included_lbl)
        root.addWidget(grp_cfg)

        btn_lay = QHBoxLayout()
        btn_refresh = QPushButton("Refresh Runs")
        btn_refresh.clicked.connect(self.refresh_runs)
        self.btn_export = QPushButton("Export Full Replication Bundle")
        self.btn_export.setStyleSheet(
            "background-color: #059669; color: white; font-weight: bold; padding: 8px 18px;"
        )
        self.btn_export.clicked.connect(self._on_export)
        btn_lay.addWidget(btn_refresh)
        btn_lay.addStretch(1)
        btn_lay.addWidget(self.btn_export)
        root.addLayout(btn_lay)

        grp_out = QGroupBox("Export Manifest & Verification Log")
        out_lay = QVBoxLayout(grp_out)
        self.txt_manifest = QPlainTextEdit()
        self.txt_manifest.setReadOnly(True)
        self.txt_manifest.setPlaceholderText("Exported file paths will be listed here upon completion...")
        self.txt_manifest.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        out_lay.addWidget(self.txt_manifest)
        root.addWidget(grp_out, stretch=1)

    def refresh_runs(self) -> None:
        self.cmb_run.clear()
        self.cmb_run.addItem("(Benchmark summary + charts + reports only)", "")
        for rec in self.state.history_service.list_runs(include_historical=False):
            exp_id = str(rec.get("experiment_id", ""))
            label = f"{rec.get('display_name', exp_id)} — F1={float(rec.get('f1_pct', 0.0)):.2f}%"
            self.cmb_run.addItem(label, exp_id)
        if self.cmb_run.count() > 1:
            self.cmb_run.setCurrentIndex(1)

    def _on_browse_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Select Export Parent Directory", self.txt_parent_dir.text()
        )
        if chosen:
            chosen_path = Path(chosen).resolve()
            orig_dir = self.state.paths.original_repo_dir.resolve()
            if chosen_path == orig_dir or orig_dir in chosen_path.parents:
                QMessageBox.critical(
                    self,
                    "Read-Only Guardrail",
                    "Exporting into original_repo/ is strictly prohibited.",
                )
                return
            self.txt_parent_dir.setText(str(chosen_path))

    def _on_export(self) -> None:
        parent_dir = Path(self.txt_parent_dir.text().strip() or str(self.state.paths.exports_dir)).resolve()
        orig_dir = self.state.paths.original_repo_dir.resolve()
        if parent_dir == orig_dir or orig_dir in parent_dir.parents:
            QMessageBox.critical(
                self,
                "Read-Only Guardrail",
                "Exporting into original_repo/ is strictly prohibited.",
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
                f"Export completed successfully!",
                f"Export Directory: {result['export_dir']}",
                f"Total Files Written: {len(result['files'])}",
                "",
                "Files:",
            ]
            for fpath in result["files"]:
                lines.append(f"  - {fpath}")
            self.txt_manifest.setPlainText("\n".join(lines))
            self.txt_bundle_name.setText(f"replication_bundle_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"{type(exc).__name__}: {exc}")

