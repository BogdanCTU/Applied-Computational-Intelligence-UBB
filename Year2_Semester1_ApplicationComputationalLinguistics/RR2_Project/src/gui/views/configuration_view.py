"""Screen 4: Configuration View — Explicit replication profile selector and parameter editor."""

from __future__ import annotations

import json
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...config import VALID_PROFILES
from ..state import WorkbenchState


class ConfigurationView(QWidget):
    """Configures the 4 explicit Agent-OM profiles, hyperparameters, parity toggles, and JSON presets."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._build_ui()
        self._load_from_config(self.state.active_config)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel("Replication Configuration Profiles & Algorithmic Parity Parameters")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        root.addWidget(title)

        # Profile selector
        grp_prof = QGroupBox("1. Scientific Replication Profile")
        lay_prof = QVBoxLayout(grp_prof)
        row_prof = QHBoxLayout()
        self.cmb_profile = QComboBox()
        for p in VALID_PROFILES:
            self.cmb_profile.addItem(p)
        self.cmb_profile.currentTextChanged.connect(self._on_profile_selected)
        btn_save = QPushButton("Export JSON Preset...")
        btn_save.clicked.connect(self._on_export_preset)
        btn_load = QPushButton("Import JSON Preset...")
        btn_load.clicked.connect(self._on_import_preset)
        row_prof.addWidget(QLabel("Active Profile:"))
        row_prof.addWidget(self.cmb_profile, stretch=1)
        row_prof.addWidget(btn_load)
        row_prof.addWidget(btn_save)
        lay_prof.addLayout(row_prof)

        self.lbl_prof_desc = QLabel("")
        self.lbl_prof_desc.setWordWrap(True)
        self.lbl_prof_desc.setStyleSheet("color: #334155; font-style: italic;")
        lay_prof.addWidget(self.lbl_prof_desc)
        root.addWidget(grp_prof)

        # Parameters form
        grp_params = QGroupBox("2. Models, Isolated PostgreSQL Database & Hyperparameters")
        form = QFormLayout(grp_params)

        self.txt_db = QLineEdit()
        self.txt_llm = QLineEdit()
        self.txt_emb = QLineEdit()
        form.addRow("Isolated PostgreSQL DB Name:", self.txt_db)
        form.addRow("Local Ollama Chat Model:", self.txt_llm)
        form.addRow("Local Embedding Model:", self.txt_emb)

        row_nums = QHBoxLayout()
        self.spn_sim = QDoubleSpinBox()
        self.spn_sim.setRange(0.0, 1.0)
        self.spn_sim.setSingleStep(0.05)
        self.spn_sim.setDecimals(2)

        self.spn_topk = QSpinBox()
        self.spn_topk.setRange(1, 20)

        self.spn_rrfk = QSpinBox()
        self.spn_rrfk.setRange(0, 100)

        self.spn_seed = QSpinBox()
        self.spn_seed.setRange(0, 999999)

        self.spn_temp = QDoubleSpinBox()
        self.spn_temp.setRange(0.0, 2.0)
        self.spn_temp.setSingleStep(0.1)
        self.spn_temp.setDecimals(2)

        row_nums.addWidget(QLabel("Sim Threshold:"))
        row_nums.addWidget(self.spn_sim)
        row_nums.addWidget(QLabel("Top-k:"))
        row_nums.addWidget(self.spn_topk)
        row_nums.addWidget(QLabel("RRF k:"))
        row_nums.addWidget(self.spn_rrfk)
        row_nums.addWidget(QLabel("Temp:"))
        row_nums.addWidget(self.spn_temp)
        row_nums.addWidget(QLabel("Seed:"))
        row_nums.addWidget(self.spn_seed)
        form.addRow("Retrieval & Sampling:", row_nums)

        row_parity = QHBoxLayout()
        self.cmb_routing = QComboBox()
        self.cmb_routing.addItems(["deterministic", "llm_json"])
        self.cmb_scope = QComboBox()
        self.cmb_scope.addItems(["head", "pvl_v1"])
        self.chk_skip_empty = QCheckBox("Skip empty chunks (0 rows)")
        self.chk_comb_props = QCheckBox("Combined URI property sort")
        self.chk_indent = QCheckBox("28-space prompt indent")
        row_parity.addWidget(QLabel("Tool Routing:"))
        row_parity.addWidget(self.cmb_routing)
        row_parity.addWidget(QLabel("Predicates:"))
        row_parity.addWidget(self.cmb_scope)
        row_parity.addWidget(self.chk_skip_empty)
        row_parity.addWidget(self.chk_comb_props)
        row_parity.addWidget(self.chk_indent)
        form.addRow("Parity Toggles:", row_parity)

        btn_apply = QPushButton("Validate & Activate Configuration")
        btn_apply.clicked.connect(self._on_apply)
        form.addRow("", btn_apply)
        root.addWidget(grp_params)

        # Validation & JSON preview
        grp_val = QGroupBox("3. Safety Validation & Effective Configuration Snapshot")
        lay_val = QVBoxLayout(grp_val)
        self.lbl_validation = QLabel("")
        self.lbl_validation.setWordWrap(True)
        self.txt_json = QPlainTextEdit()
        self.txt_json.setReadOnly(True)
        self.txt_json.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        lay_val.addWidget(self.lbl_validation)
        lay_val.addWidget(self.txt_json)
        root.addWidget(grp_val, stretch=1)

    def _on_profile_selected(self, profile_name: str) -> None:
        if not profile_name:
            return
        cfg = self.state.config_service.build_config(profile_name)
        if self.state.selected_dataset:
            cfg.context = self.state.selected_dataset.context_hint
            cfg.o1_is_code = self.state.selected_dataset.o1_is_code_hint
            cfg.o2_is_code = self.state.selected_dataset.o2_is_code_hint
        self._load_from_config(cfg)
        self.state.set_config(cfg)

    def _load_from_config(self, cfg) -> None:
        self.cmb_profile.blockSignals(True)
        self.cmb_profile.setCurrentText(cfg.profile_name)
        self.cmb_profile.blockSignals(False)

        self.lbl_prof_desc.setText(
            self.state.config_service.PROFILE_DESCRIPTIONS.get(cfg.profile_name, "")
        )
        self.txt_db.setText(cfg.db_name)
        self.txt_llm.setText(cfg.default_llm)
        self.txt_emb.setText(cfg.default_embedding_model)
        self.spn_sim.setValue(float(cfg.similarity_threshold))
        self.spn_topk.setValue(int(cfg.top_k))
        self.spn_rrfk.setValue(int(cfg.rrf_k))
        self.spn_temp.setValue(float(cfg.temperature))
        self.spn_seed.setValue(int(cfg.seed or 42))
        self.cmb_routing.setCurrentText(cfg.tool_routing_mode)
        self.cmb_scope.setCurrentText(cfg.predicate_scope)
        self.chk_skip_empty.setChecked(bool(cfg.skip_empty_chunks))
        self.chk_comb_props.setChecked(bool(cfg.combine_properties_sort))
        self.chk_indent.setChecked(bool(cfg.indent_validation_prompt))
        self._refresh_validation_panel(cfg)

    def _build_current_from_ui(self):
        prof = self.cmb_profile.currentText()
        return self.state.config_service.build_config(
            prof,
            db_name=self.txt_db.text().strip(),
            default_llm=self.txt_llm.text().strip(),
            default_embedding_model=self.txt_emb.text().strip(),
            embedding_dim=None,
            similarity_threshold=float(self.spn_sim.value()),
            top_k=int(self.spn_topk.value()),
            rrf_k=int(self.spn_rrfk.value()),
            temperature=float(self.spn_temp.value()),
            seed=int(self.spn_seed.value()),
            tool_routing_mode=self.cmb_routing.currentText(),
            predicate_scope=self.cmb_scope.currentText(),
            skip_empty_chunks=self.chk_skip_empty.isChecked(),
            combine_properties_sort=self.chk_comb_props.isChecked(),
            indent_validation_prompt=self.chk_indent.isChecked(),
        )

    def _on_apply(self) -> None:
        try:
            cfg = self._build_current_from_ui()
            self.state.set_config(cfg)
            self._refresh_validation_panel(cfg)
        except Exception as exc:
            QMessageBox.critical(self, "Invalid Configuration", str(exc))

    def _refresh_validation_panel(self, cfg) -> None:
        res = self.state.config_service.validate_for_execution(cfg)
        if res["valid"]:
            self.lbl_validation.setText(
                f"VALID FOR LOCAL EXECUTION — Vector length={cfg.vector_length}, DB={cfg.db_name}"
            )
            self.lbl_validation.setStyleSheet("color: #059669; font-weight: bold;")
        else:
            self.lbl_validation.setText("EXECUTION BLOCKED: " + " | ".join(res["issues"]))
            self.lbl_validation.setStyleSheet("color: #D97706; font-weight: bold;")
        self.txt_json.setPlainText(json.dumps(res["metadata"], indent=2))

    def _on_export_preset(self) -> None:
        cfg = self._build_current_from_ui()
        default_dir = str(self.state.paths.replication_runs_dir / "configs")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration Preset", default_dir, "JSON Files (*.json)"
        )
        if path:
            saved = self.state.config_service.save_preset(cfg, path)
            QMessageBox.information(self, "Preset Saved", f"Saved configuration to:\n{saved}")

    def _on_import_preset(self) -> None:
        default_dir = str(self.state.paths.replication_runs_dir / "configs")
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration Preset", default_dir, "JSON Files (*.json)"
        )
        if path:
            try:
                cfg = self.state.config_service.load_preset(path)
                self._load_from_config(cfg)
                self.state.set_config(cfg)
            except Exception as exc:
                QMessageBox.critical(self, "Preset Load Error", str(exc))

