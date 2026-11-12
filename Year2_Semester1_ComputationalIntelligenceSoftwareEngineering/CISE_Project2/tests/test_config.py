"""Tests for application configuration."""
from config.settings import get_settings, AppSettings


def test_settings_initialization(tmp_path):
    settings = get_settings()
    assert isinstance(settings, AppSettings)
    assert settings.app_name == "C# Defect Predictor"
    assert settings.storage.database_path is not None
    assert settings.ml.default_n_estimators == 100
    assert settings.ml.default_random_state == 42

