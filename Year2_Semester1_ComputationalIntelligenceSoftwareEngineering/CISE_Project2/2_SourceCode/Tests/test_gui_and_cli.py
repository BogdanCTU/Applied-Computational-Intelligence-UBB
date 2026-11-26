"""Tests for CLI entrypoints, Streamlit page compilation, and headless AppTest page smoke checks."""

from __future__ import annotations

import py_compile
import subprocess
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

from bug_detector.config import get_project_root


def test_all_gui_pages_compile() -> None:
    root = get_project_root()
    gui_files = [
        root / "app.py",
        root / "2_SourceCode" / "gui" / "app.py",
        root / "2_SourceCode" / "gui" / "components.py",
        *sorted((root / "2_SourceCode" / "gui" / "pages").glob("*.py")),
    ]
    for f in gui_files:
        py_compile.compile(str(f), doraise=True)


def test_cli_init_db_and_help() -> None:
    root = get_project_root()
    proc = subprocess.run(
        [sys.executable, "-m", "bug_detector", "--help"],
        cwd=str(root),
        env={"PYTHONPATH": str(root / "2_SourceCode"), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "detect" in proc.stdout
    assert "run-experiments" in proc.stdout


def test_streamlit_pages_render_without_exceptions() -> None:
    root = get_project_root()
    pages_dir = root / "2_SourceCode" / "gui" / "pages"
    for page_name in [
        "dashboard.py",
        "manual_detection.py",
        "results.py",
        "dataset_explorer.py",
        "model_training.py",
        "model_configuration.py",
    ]:
        at = AppTest.from_file(str(pages_dir / page_name), default_timeout=20)
        at.run()
        assert not at.exception, f"Streamlit exception on {page_name}: {at.exception}"
