"""Tests for configuration management."""

import os
import pytest
from config import ScraperConfig


def test_config_defaults():
    """Test default configuration values."""
    config = ScraperConfig()
    assert config.cache_dir == "_cache"
    assert config.max_workers == 4
    assert config.log_file == "gartan_debug.log"
    assert isinstance(config.cache_minutes, dict)
    assert config.cache_minutes[0] == 15  # Today
    assert config.cache_minutes[1] == 60  # Tomorrow


def test_cache_minutes_calculation():
    """Test cache expiry time calculation."""
    config = ScraperConfig()
    assert config.get_cache_minutes(0) == 15
    assert config.get_cache_minutes(1) == 60
    assert config.get_cache_minutes(3) == 360
    assert config.get_cache_minutes(10) == 1440


def test_environment_credentials(monkeypatch):
    """Test environment variable handling."""
    # Test with environment variables set
    monkeypatch.setenv("GARTAN_USERNAME", "test_user")
    monkeypatch.setenv("GARTAN_PASSWORD", "test_pass")

    config = ScraperConfig()
    assert config.gartan_username == "test_user"
    assert config.gartan_password == "test_pass"

    # Test with environment variables unset
    monkeypatch.delenv("GARTAN_USERNAME")
    monkeypatch.delenv("GARTAN_PASSWORD")

    config = ScraperConfig()
    assert config.gartan_username is None
    assert config.gartan_password is None


def test_custom_cache_minutes():
    """Test custom cache minutes configuration."""
    custom_cache = {
        0: 30,  # Today
        1: 120,  # Tomorrow
        2: 720,  # Next week
        8: 2880,  # Beyond
    }
    config = ScraperConfig(cache_minutes=custom_cache)
    assert config.get_cache_minutes(0) == 30
    assert config.get_cache_minutes(1) == 120
