"""Entry point for the Agent-OM Guided Replication & Validation Windows Desktop GUI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _bootstrap_paths() -> Path:
    """Ensure `agent_om_local/` is on `sys.path` in both source and PyInstaller frozen modes."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass and meipass not in sys.path:
            sys.path.insert(0, str(meipass))
        exe_dir = Path(sys.executable).resolve().parent
        if str(exe_dir) not in sys.path:
            sys.path.insert(0, str(exe_dir))
        return exe_dir
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root


def run_self_test(
    smoke_run_id: str | None = None,
    smoke_db_name: str = "agent_om_exe_test",
    export_bundle_name: str | None = None,
) -> int:
    """Deterministic headless/offscreen verification for CI and standalone `.exe` validation."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication
    from src.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.processEvents()

    # Step through all 10 screens and verify rendering
    visited_screens: list[str] = []
    for idx in range(window.nav_list.count()):
        window.navigate_to(idx)
        app.processEvents()
        visited_screens.append(window.NAV_ITEMS[idx])

    pg_health = window.state.db_service.check_server_health()
    ollama_health = window.state.ollama_service.check_health()
    datasets = window.state.dataset_service.discover_datasets()

    result: dict = {
        "is_frozen": window.state.paths.is_frozen,
        "project_root": str(window.state.paths.project_root),
        "screens_verified": len(visited_screens),
        "screen_names": visited_screens,
        "postgresql_reachable": bool(pg_health.get("reachable")),
        "postgresql_version": pg_health.get("server_version"),
        "ollama_reachable": bool(ollama_health.get("reachable")),
        "ollama_models_count": len(ollama_health.get("models", [])),
        "datasets_discovered": len(datasets),
    }

    # Optional end-to-end mini experiment run via ExperimentRunnerService (QThread)
    if smoke_run_id:
        if not datasets:
            raise RuntimeError("No datasets discovered for --smoke-run-id verification.")
        ds = datasets[0]
        loop = QEventLoop()
        run_outcome: dict = {}

        def _on_done(summary: dict) -> None:
            run_outcome["status"] = "completed"
            run_outcome["summary"] = summary
            loop.quit()

        def _on_err(err: str) -> None:
            run_outcome["status"] = "failed"
            run_outcome["error"] = err
            loop.quit()

        window.state.runner_service.run_finished.connect(_on_done)
        window.state.runner_service.run_failed.connect(_on_err)
        QTimer.singleShot(300_000, loop.quit)  # 5 min safety timeout

        window.state.runner_service.start_local_run(
            experiment_id=smoke_run_id,
            profile_name="local_adapted",
            source_ontology_path=ds.source_path,
            target_ontology_path=ds.target_path,
            reference_alignment_path=ds.reference_path,
            db_name_override=smoke_db_name,
            max_entities_per_side=2,
            skip_retrieval=False,
        )
        loop.exec()
        app.processEvents()
        if run_outcome.get("status") != "completed":
            raise RuntimeError(f"Smoke run failed or timed out: {run_outcome}")
        result["smoke_run"] = {
            "experiment_id": smoke_run_id,
            "status": run_outcome["status"],
            "runtime_s": run_outcome["summary"].get("total_runtime_s"),
        }

    # Optional full report export bundle verification
    if export_bundle_name:
        exp_res = window.state.report_service.export_full_bundle(
            export_name=export_bundle_name,
            selected_experiment_id=smoke_run_id,
        )
        result["export_bundle"] = {
            "export_dir": exp_res["export_dir"],
            "file_count": len(exp_res["files"]),
        }

    window.close()
    app.processEvents()
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    _bootstrap_paths()

    parser = argparse.ArgumentParser(
        description="Agent-OM Guided Replication & Validation Workbench (Windows Desktop GUI)"
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run offscreen automated self-verification across all 10 GUI screens and exit.",
    )
    parser.add_argument(
        "--smoke-run-id",
        type=str,
        default=None,
        help="In --self-test mode, execute a real 2-entity/side end-to-end experiment into replication_runs/.",
    )
    parser.add_argument(
        "--smoke-db-name",
        type=str,
        default="agent_om_exe_test",
        help="Isolated PostgreSQL database for --smoke-run-id (default: agent_om_exe_test).",
    )
    parser.add_argument(
        "--export-bundle-name",
        type=str,
        default=None,
        help="In --self-test mode, also export a complete report bundle into output/exports/.",
    )
    args, qt_args = parser.parse_known_args()

    if args.self_test:
        return run_self_test(
            smoke_run_id=args.smoke_run_id,
            smoke_db_name=args.smoke_db_name,
            export_bundle_name=args.export_bundle_name,
        )

    from PySide6.QtWidgets import QApplication
    from src.gui.main_window import MainWindow

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Agent-OM Replication Workbench")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

