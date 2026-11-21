"""Shared pytest fixtures for offline and integration tests."""

from __future__ import annotations

from pathlib import Path
import pytest

from source.config.settings import AppConfig, load_config
from source.storage.database import DatabaseManager


@pytest.fixture
def app_config() -> AppConfig:
    return load_config()


@pytest.fixture
def temp_db(tmp_path: Path) -> DatabaseManager:
    db = DatabaseManager(tmp_path / "test_research.db")
    db.init_db(export_schema=False)
    return db
