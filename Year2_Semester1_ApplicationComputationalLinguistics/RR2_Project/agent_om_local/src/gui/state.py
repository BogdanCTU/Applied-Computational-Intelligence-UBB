"""Shared application state container connecting the 11 services and 10 PySide6 screens."""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import QObject, Signal

from ..config import AppConfig
from .paths import ProjectPaths, resolve_project_paths
from .services import (
    ArtifactComparisonService,
    ConfigurationService,
    DatabaseService,
    DatasetService,
    EnvironmentService,
    EvaluationService,
    ExperimentHistoryService,
    ExperimentRunnerService,
    OllamaService,
    PipelineInspectionService,
    ReportGenerationService,
)
from .services.dataset_service import DatasetDescriptor


class WorkbenchState(QObject):
    """Centralized state and service registry for the Agent-OM Replication Workbench."""

    dataset_changed = Signal(object)
    config_changed = Signal(object)
    runs_updated = Signal()
    navigate_requested = Signal(int)

    def __init__(self, paths: Optional[ProjectPaths] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.paths = paths or resolve_project_paths()

        # Instantiate all 11 services
        self.env_service = EnvironmentService(self.paths)
        self.db_service = DatabaseService()
        self.ollama_service = OllamaService()
        self.dataset_service = DatasetService(self.paths)
        self.config_service = ConfigurationService(self.paths)
        self.runner_service = ExperimentRunnerService(self.paths, parent=self)
        self.inspection_service = PipelineInspectionService(self.paths)
        self.comparison_service = ArtifactComparisonService(self.paths, self.inspection_service)
        self.history_service = ExperimentHistoryService(self.paths)
        self.evaluation_service = EvaluationService(self.paths, self.history_service)
        self.report_service = ReportGenerationService(self.paths, self.evaluation_service)

        # Default dataset (CMT-ConfOf if available) and configuration profile
        discovered = self.dataset_service.discover_datasets()
        self.selected_dataset: Optional[DatasetDescriptor] = discovered[0] if discovered else None
        self.active_config: AppConfig = self.config_service.build_config("local_adapted")

        self.runner_service.run_finished.connect(lambda _: self.runs_updated.emit())
        self.runner_service.run_cancelled.connect(lambda _: self.runs_updated.emit())

    def set_dataset(self, descriptor: DatasetDescriptor) -> None:
        self.selected_dataset = descriptor
        self.active_config.context = descriptor.context_hint
        self.active_config.o1_is_code = descriptor.o1_is_code_hint
        self.active_config.o2_is_code = descriptor.o2_is_code_hint
        self.dataset_changed.emit(descriptor)
        self.config_changed.emit(self.active_config)

    def set_config(self, cfg: AppConfig) -> None:
        self.active_config = cfg
        self.config_changed.emit(cfg)

