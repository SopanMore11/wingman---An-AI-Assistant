"""Unit tests for configuration."""

import pytest
from pathlib import Path

from src.config import Settings


def test_settings_instantiation():
    """Test Settings can be instantiated."""
    settings = Settings.from_env()
    assert settings is not None
    assert settings.app_name == "wingman"
    assert settings.database is not None
    assert settings.llm is not None
    assert settings.calendar is not None
    assert settings.telegram is not None


def test_database_config():
    """Test database configuration."""
    config = Settings().database
    assert config.db_path == "dataset/wingmandb.db"
    assert config.expense_csv_path == "dataset/my_expences.csv"
