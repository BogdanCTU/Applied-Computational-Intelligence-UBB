"""Screen 3: Dataset Manager View — OAEI benchmark selector and custom ontology pair configuration."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
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

from ..services.dataset_service import DatasetDescriptor
from ..state import WorkbenchState
from ..styles import SPACE_SM
from ..widgets import create_button, create_page_header, show_error_dialog


class DatasetView(QWidget):
    """Selects OAEI benchmark datasets or custom local ontology pairs and previews entity counts."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._datasets: list[DatasetDescriptor] = []
        self._build_ui()
        self.refresh_datasets()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        header_w, _ = create_page_header(
            "Datasets",
            "Select an OAEI benchmark dataset or configure a custom local ontology pair.",
        )
        root.addWidget(header_w)

        # Discovered OAEI datasets
        grp_oaei = QGroupBox("OAEI Benchmark Dataset")
        lay_oaei = QHBoxLayout(grp_oaei)
        lay_oaei.setSpacing(SPACE_SM)
        lay_oaei.addWidget(QLabel("Benchmark:"))
        self.cmb_datasets = QComboBox()
        self.cmb_datasets.setAccessibleName("OAEI Benchmark Selector")
        btn_select_oaei = create_button(
            "Load Dataset",
            role="primary",
            tooltip="Set the selected benchmark as the active ontology pair",
            accessible_name="Load Selected Benchmark",
        )
        btn_select_oaei.clicked.connect(self._on_select_benchmark)
        lay_oaei.addWidget(self.cmb_datasets, stretch=1)
        lay_oaei.addWidget(btn_select_oaei)
        root.addWidget(grp_oaei)

        # Custom ontology selector
        grp_custom = QGroupBox("Custom Ontology Pair")
        form = QFormLayout(grp_custom)
        form.setSpacing(10)

        self.txt_src = QLineEdit()
        self.txt_src.setPlaceholderText("Path to source ontology (.xml, .owl, .rdf, .ttl)")
        self.txt_src.setAccessibleName("Source ontology file path")
        btn_src = create_button(
            "Browse",
            role="secondary",
            tooltip="Choose source ontology file",
            accessible_name="Browse Source Ontology",
        )
        btn_src.clicked.connect(lambda: self._browse_into(self.txt_src))
        r_src = QHBoxLayout()
        r_src.setSpacing(SPACE_SM)
        r_src.addWidget(self.txt_src, stretch=1)
        r_src.addWidget(btn_src)
        form.addRow("Source Ontology:", r_src)

        self.txt_tgt = QLineEdit()
        self.txt_tgt.setPlaceholderText("Path to target ontology (.xml, .owl, .rdf, .ttl)")
        self.txt_tgt.setAccessibleName("Target ontology file path")
        btn_tgt = create_button(
            "Browse",
            role="secondary",
            tooltip="Choose target ontology file",
            accessible_name="Browse Target Ontology",
        )
        btn_tgt.clicked.connect(lambda: self._browse_into(self.txt_tgt))
        r_tgt = QHBoxLayout()
        r_tgt.setSpacing(SPACE_SM)
        r_tgt.addWidget(self.txt_tgt, stretch=1)
        r_tgt.addWidget(btn_tgt)
        form.addRow("Target Ontology:", r_tgt)

        self.txt_ref = QLineEdit()
        self.txt_ref.setPlaceholderText("Optional reference alignment (.xml) for Precision/Recall/F1")
        self.txt_ref.setAccessibleName("Reference alignment file path")
        btn_ref = create_button(
            "Browse",
            role="secondary",
            tooltip="Choose optional OAEI reference alignment file",
            accessible_name="Browse Reference Alignment",
        )
        btn_ref.clicked.connect(lambda: self._browse_into(self.txt_ref))
        r_ref = QHBoxLayout()
        r_ref.setSpacing(SPACE_SM)
        r_ref.addWidget(self.txt_ref, stretch=1)
        r_ref.addWidget(btn_ref)
        form.addRow("Reference Alignment:", r_ref)

        opts = QHBoxLayout()
        opts.setSpacing(SPACE_SM)
        self.txt_ctx = QLineEdit("conference")
        self.txt_ctx.setMinimumHeight(34)
        self.txt_ctx.setMaximumWidth(160)
        self.txt_ctx.setAccessibleName("Domain context")
        self.chk_o1_code = QCheckBox("Source uses code IRIs")
        self.chk_o2_code = QCheckBox("Target uses code IRIs")
        btn_apply_custom = create_button(
            "Apply Custom Pair",
            role="secondary",
            tooltip="Load and preview the custom source, target, and reference files",
            accessible_name="Apply Custom Ontology Pair",
        )
        btn_apply_custom.clicked.connect(self._on_apply_custom)
        opts.addWidget(QLabel("Context:"))
        opts.addWidget(self.txt_ctx)
        opts.addWidget(self.chk_o1_code)
        opts.addWidget(self.chk_o2_code)
        opts.addStretch(1)
        opts.addWidget(btn_apply_custom)
        form.addRow("Options:", opts)
        root.addWidget(grp_custom)

        # Live preview box
        grp_prev = QGroupBox("Dataset Summary")
        lay_prev = QVBoxLayout(grp_prev)
        self.txt_preview = QPlainTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setAccessibleName("Dataset Summary Preview")
        lay_prev.addWidget(self.txt_preview)
        root.addWidget(grp_prev, stretch=1)

    def _browse_into(self, target_edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Ontology or Alignment File",
            "",
            "Ontology Files (*.xml *.owl *.rdf *.ttl *.n3);;All Files (*)",
        )
        if path:
            target_edit.setText(path)

    def refresh_datasets(self) -> None:
        self._datasets = self.state.dataset_service.discover_datasets()
        self.cmb_datasets.clear()
        for d in self._datasets:
            self.cmb_datasets.addItem(f"[{d.track}] {d.pair_name} ({d.dataset_id})")
        if self._datasets:
            self._preview_descriptor(self._datasets[0])

    def _on_select_benchmark(self) -> None:
        idx = self.cmb_datasets.currentIndex()
        if 0 <= idx < len(self._datasets):
            desc = self._datasets[idx]
            self.state.set_dataset(desc)
            self._preview_descriptor(desc)

    def _on_apply_custom(self) -> None:
        try:
            desc = self.state.dataset_service.build_custom_descriptor(
                source_path=self.txt_src.text().strip(),
                target_path=self.txt_tgt.text().strip(),
                reference_path=self.txt_ref.text().strip() or None,
                context=self.txt_ctx.text().strip() or "conference",
                o1_is_code=self.chk_o1_code.isChecked(),
                o2_is_code=self.chk_o2_code.isChecked(),
            )
            self.state.set_dataset(desc)
            self._preview_descriptor(desc)
        except Exception as exc:
            show_error_dialog(
                self,
                "Dataset Error",
                exc,
                "Verify that both source and target ontology file paths exist and are valid RDF/OWL files.",
            )

    def _preview_descriptor(self, desc: DatasetDescriptor) -> None:
        try:
            info = self.state.dataset_service.preview_dataset(desc)
            src = info["source"]
            tgt = info["target"]
            lines = [
                f"Dataset ID:       {info['dataset_id']}",
                f"Track / Pair:     {info['track']} / {info['pair_name']}",
                f"Domain Context:   {info['context_hint']} (o1_is_code={info['o1_is_code_hint']}, o2_is_code={info['o2_is_code_hint']})",
                "",
                f"Source Ontology:  {src['path']}",
                f"  Triples: {src['triples']} | Classes: {src['classes']} | ObjProps: {src['object_properties']} | DataProps: {src['datatype_properties']} | Total Entities: {src['total_entities']}",
                f"  Sample URIs: {', '.join(src['sample_entities'][:5])}",
                "",
                f"Target Ontology:  {tgt['path']}",
                f"  Triples: {tgt['triples']} | Classes: {tgt['classes']} | ObjProps: {tgt['object_properties']} | DataProps: {tgt['datatype_properties']} | Total Entities: {tgt['total_entities']}",
                f"  Sample URIs: {', '.join(tgt['sample_entities'][:5])}",
                "",
                f"Reference Pairs:  {info['reference_count']} 1:1 equivalence mappings",
            ]
            for s_u, t_u in info["reference_pairs"][:20]:
                lines.append(f"  {s_u} = {t_u}")
            if info["committed_gpt4o_predict_present"]:
                lines.append("")
                lines.append(
                    f"Committed Reference Alignment (GPT-4o): Present ({info['committed_gpt4o_predict_count']} pairs)"
                )
            self.txt_preview.setPlainText("\n".join(lines))
        except Exception as exc:
            self.txt_preview.setPlainText(f"Failed to preview dataset: {exc}")
