"""Regression tests for macOS startup, frozen packaging, and diagnostics."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.main import _show_fatal_error_dialog, main
from config.paths import app_root, is_frozen, resolve_path, resource_root
from memory.migrations import get_default_migrations_dir
from run_app import _fallback_log_fatal


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_smoke_test_mode(qapp: QApplication) -> None:
    """Verify that main with --smoke-test initializes GUI and closes cleanly."""
    exit_code = main(["--smoke-test"])
    assert exit_code == 0


def test_migrations_dir_resolution_source() -> None:
    """Verify that get_default_migrations_dir finds the SQL migrations in source mode."""
    mig_dir = get_default_migrations_dir()
    assert mig_dir.exists()
    sql_files = list(mig_dir.glob("*.sql"))
    assert len(sql_files) >= 3
    assert any("001_initial_schema.sql" in f.name for f in sql_files)


def test_migrations_dir_resolution_frozen_fallback(tmp_path: Path) -> None:
    """Verify that get_default_migrations_dir resolves to resource_root when frozen."""
    fake_res = tmp_path / "bundle_res"
    fake_migs = fake_res / "memory" / "migrations"
    fake_migs.mkdir(parents=True)
    (fake_migs / "001_initial_schema.sql").write_text("-- test", encoding="utf-8")

    with patch("config.paths.is_frozen", return_value=True), \
         patch("config.paths.resource_root", return_value=fake_res):
        resolved = get_default_migrations_dir()
        assert resolved == fake_migs


def test_skill_manager_frozen_resolution(tmp_path: Path) -> None:
    """Verify that SkillManager prefers resource_root/skills when running frozen."""
    from agent.skill_manager import SkillManager

    fake_res = tmp_path / "bundle_res"
    fake_skills = fake_res / "skills"
    fake_skill_a = fake_skills / "test_skill"
    fake_skill_a.mkdir(parents=True)
    (fake_skill_a / "metadata.yaml").write_text(
        "skill_id: test_skill\nname: Test Skill\nversion: '1.0.0'\ncategory: sql\ndescription: test",
        encoding="utf-8",
    )
    (fake_skill_a / "SKILL.md").write_text("# Test Skill\nContent", encoding="utf-8")

    with patch("config.paths.is_frozen", return_value=True), \
         patch("config.paths.resource_root", return_value=fake_res):
        mgr = SkillManager(repository=MagicMock(), auto_sync_repo=False)
        assert mgr.skills_dir == fake_skills


def test_spec_file_packaging_configuration() -> None:
    """Verify that ReportSQLAgent.spec bundles all required assets and excludes mcp.cli."""
    spec_path = resolve_path("ReportSQLAgent.spec")
    assert spec_path.exists()
    content = spec_path.read_text(encoding="utf-8")

    # 1. memory package included in submodule collection
    assert '"memory"' in content

    # 2. memory/migrations SQL files bundled
    assert "memory/migrations" in content
    assert "*.sql" in content

    # 3. skills bundled
    assert "skills" in content
    assert "SKILL.md" in content or "skills_dir" in content

    # 4. mcp.cli excluded to avoid typer dependency warning
    assert "mcp.cli" in content


def test_fatal_error_dialog_handling(qapp: QApplication) -> None:
    """Verify that _show_fatal_error_dialog instantiates QMessageBox with diagnostic text."""
    with patch.dict(os.environ, {"QT_QPA_PLATFORM": "cocoa"}), \
         patch("PySide6.QtGui.QGuiApplication.platformName", return_value="cocoa"), \
         patch("PySide6.QtWidgets.QMessageBox.exec") as mock_exec:
        test_exc = RuntimeError("Simulated startup failure")
        _show_fatal_error_dialog(test_exc, log_file_path=Path("/tmp/test_agent.log"))
        assert mock_exec.called


def test_launcher_fallback_crash_logger(tmp_path: Path) -> None:
    """Verify that run_app._fallback_log_fatal creates crash log on uncaught error."""
    with patch("config.paths.user_data_root", return_value=tmp_path):
        test_exc = ImportError("Missing critical module")
        _fallback_log_fatal(test_exc)

        crash_file = tmp_path / "logs" / "startup_crash.log"
        assert crash_file.exists()
        content = crash_file.read_text(encoding="utf-8")
        assert "Startup Crash (ImportError)" in content
