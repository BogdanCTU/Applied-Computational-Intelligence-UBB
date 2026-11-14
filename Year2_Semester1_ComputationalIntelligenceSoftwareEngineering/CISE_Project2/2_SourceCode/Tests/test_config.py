"""Tests for application configuration."""
import subprocess
import sys
from core.settings import get_settings, AppSettings, register_unpickle_aliases


def test_settings_initialization(tmp_path):
    settings = get_settings()
    assert isinstance(settings, AppSettings)
    assert settings.app_name == "C# Defect Predictor"
    assert settings.storage.database_path is not None
    assert settings.ml.default_n_estimators == 100
    assert settings.ml.default_random_state == 42


def test_register_unpickle_aliases():
    """Verify that unpickle aliases register correctly without raising exceptions."""
    register_unpickle_aliases()
    assert "src" in sys.modules
    assert "src.ml.preprocessing" in sys.modules
    assert "src.database" in sys.modules


def test_isolated_import_order_regression():
    """Regression test ensuring ml.preprocessing imports cleanly in a fresh process without circular import failure."""
    code = (
        "import sys; from pathlib import Path; "
        "sys.path.insert(0, str(Path('2_SourceCode/Python').resolve())); "
        "from ml.preprocessing import DataPreprocessor; "
        "from core.settings import get_settings; "
        "assert DataPreprocessor is not None; "
        "assert get_settings() is not None; "
        "print('SUCCESS')"
    )
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert res.returncode == 0, f"Import order failed: {res.stderr}"
    assert "SUCCESS" in res.stdout


