"""Automated tests for the 11 GUI services, 10 PySide6 screens, MainWindow, DB mutex, and safe cancellation."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow
from src.gui.paths import resolve_project_paths
from src.gui.services import (
    ConfigurationService,
    DatabaseService,
    DatasetService,
    EnvironmentService,
    EvaluationService,
    ExperimentHistoryService,
    ReportGenerationService,
)
from src.gui.state import WorkbenchState


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_project_paths_resolution() -> None:
    paths = resolve_project_paths()
    assert paths.project_root.name == "agent_om_local"
    assert paths.original_repo_dir.name == "original_repo"
    assert paths.original_repo_dir.is_dir()


def test_environment_and_dataset_services() -> None:
    paths = resolve_project_paths()
    env_svc = EnvironmentService(paths)
    rt = env_svc.get_runtime_summary()
    assert "python_version" in rt
    orig = env_svc.check_original_repo_status()
    assert orig["exists"] is True

    ds_svc = DatasetService(paths)
    datasets = ds_svc.discover_datasets()
    assert len(datasets) >= 1
    cmt = next((d for d in datasets if "cmt-confof" in d.dataset_id.lower()), datasets[0])
    preview = ds_svc.preview_dataset(cmt)
    assert preview["source"]["classes"] == 29
    assert preview["source"]["total_entities"] == 88
    assert preview["target"]["classes"] == 38
    assert preview["target"]["total_entities"] == 74
    assert preview["reference_count"] == 16


def test_configuration_service_profiles_and_guardrails(tmp_path: Path) -> None:
    cfg_svc = ConfigurationService()
    profiles = cfg_svc.list_profiles()
    assert len(profiles) == 4

    # Reference profile must be blocked from execution
    ref_cfg = cfg_svc.build_config("upstream_product_reference")
    ref_val = cfg_svc.validate_for_execution(ref_cfg)
    assert ref_val["valid"] is False

    # Protected DB agent_om_local must be blocked from destructive execution
    prot_cfg = cfg_svc.build_config("local_adapted", db_name="agent_om_local")
    prot_val = cfg_svc.validate_for_execution(prot_cfg)
    assert prot_val["valid"] is False

    # Valid isolated parity profile
    par_cfg = cfg_svc.build_config("upstream_lite_parity", similarity_threshold=0.91)
    par_val = cfg_svc.validate_for_execution(par_cfg)
    assert par_val["valid"] is True
    assert par_cfg.vector_length == 4096

    # Preset save/load round-trip
    preset_file = tmp_path / "preset_parity.json"
    cfg_svc.save_preset(par_cfg, preset_file)
    loaded = cfg_svc.load_preset(preset_file)
    assert loaded.profile_name == "upstream_lite_parity"
    assert loaded.similarity_threshold == pytest.approx(0.91)
    assert loaded.vector_length == 4096


def test_database_service_mutex_and_protection() -> None:
    db_svc = DatabaseService()
    # Non-blocking mutex must block concurrent acquisition on the same DB name
    assert DatabaseService.acquire_db_lock("unit_test_mutex_db", blocking=False) is True
    try:
        assert DatabaseService.acquire_db_lock("unit_test_mutex_db", blocking=False) is False
    finally:
        DatabaseService.release_db_lock("unit_test_mutex_db")
    assert DatabaseService.acquire_db_lock("unit_test_mutex_db", blocking=False) is True
    DatabaseService.release_db_lock("unit_test_mutex_db")

    # Protected DB creation/overwrite must raise PermissionError
    with pytest.raises(PermissionError):
        db_svc.create_isolated_database("agent_om_local")


def test_evaluation_and_report_export_services(tmp_path: Path) -> None:
    paths = resolve_project_paths()
    hist_svc = ExperimentHistoryService(paths)
    runs = hist_svc.list_runs(include_historical=True)
    assert any(r["experiment_id"] == "ref_upstream_gpt4o_cmt_confof" for r in runs)

    eval_svc = EvaluationService(paths, hist_svc)
    rows = eval_svc.get_benchmark_comparison_rows()
    assert len(rows) >= 2

    rep_svc = ReportGenerationService(paths, eval_svc)
    bundle = rep_svc.export_full_bundle(
        export_name="pytest_export_bundle",
        target_parent_dir=tmp_path,
    )
    export_dir = Path(bundle["export_dir"])
    assert export_dir.is_dir()
    assert (export_dir / "benchmark_comparison.csv").is_file()
    assert (export_dir / "benchmark_comparison.json").is_file()
    assert (export_dir / "replication_export_report.md").is_file()
    assert len(list((export_dir / "charts").glob("*.png"))) >= 4


def test_main_window_all_10_screens_and_navigation(qapp: QApplication) -> None:
    state = WorkbenchState()
    win = MainWindow(state=state)
    win.show()
    qapp.processEvents()

    assert win.nav_list.count() == 10
    assert win.stack.count() == 10

    for idx in range(10):
        state.navigate_requested.emit(idx)
        qapp.processEvents()
        assert win.nav_list.currentRow() == idx
        assert win.stack.currentIndex() == idx

    win.close()
    qapp.processEvents()


def test_runner_service_cooperative_cancellation(qapp: QApplication) -> None:
    state = WorkbenchState()
    runner = state.runner_service

    def _fake_slow_experiment(**kwargs):
        cb = kwargs.get("stage_callback")
        should_cancel = kwargs.get("should_cancel")
        for step in range(20):
            if cb:
                cb("3_source_retrieval", step + 1, 20, f"Simulated step {step + 1}")
            if should_cancel and should_cancel():
                return {"experiment_id": kwargs["experiment_id"], "status": "cancelled"}
            time.sleep(0.03)
        return {"experiment_id": kwargs["experiment_id"], "status": "completed", "total_runtime_s": 0.6}

    loop = QEventLoop()
    outcomes: dict = {}

    runner.run_cancelled.connect(lambda s: (outcomes.setdefault("cancelled", s), loop.quit()))
    runner.run_failed.connect(lambda e: (outcomes.setdefault("failed", e), loop.quit()))
    QTimer.singleShot(80, runner.cancel_active_run)
    QTimer.singleShot(5000, loop.quit)

    with patch("scripts.run_local_replication.run_local_experiment", side_effect=_fake_slow_experiment):
        runner.start_local_run(
            experiment_id="pytest_cancel_check",
            profile_name="local_adapted",
            db_name_override="agent_om_cancel_test",
        )
        loop.exec()
        qapp.processEvents()

    assert "cancelled" in outcomes
    assert outcomes["cancelled"]["status"] == "cancelled"
