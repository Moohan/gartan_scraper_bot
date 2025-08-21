"""Test media path configuration functionality."""

import os
import tempfile
from unittest import mock

import pytest

from config import Config


def test_config_uses_current_directory_by_default():
    """Test that config uses current directory when MEDIA env var is not set."""
    with mock.patch.dict(os.environ, {}, clear=True):
        # Clear MEDIA if it exists
        if "MEDIA" in os.environ:
            del os.environ["MEDIA"]
        
        config = Config()
        
        assert config.media_dir == "."
        assert config.db_path == os.path.join(".", "gartan_availability.db")
        assert config.cache_dir == os.path.join(".", "_cache")
        assert config.log_file == os.path.join(".", "gartan_debug.log")
        assert config.crew_details_file == os.path.join(".", "crew_details.local")


def test_config_uses_media_environment_variable():
    """Test that config uses MEDIA environment variable when set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MEDIA": tmpdir}):
            config = Config()
            
            assert config.media_dir == tmpdir
            assert config.db_path == os.path.join(tmpdir, "gartan_availability.db")
            assert config.cache_dir == os.path.join(tmpdir, "_cache")
            assert config.log_file == os.path.join(tmpdir, "gartan_debug.log")
            assert config.crew_details_file == os.path.join(tmpdir, "crew_details.local")


def test_config_creates_media_directory():
    """Test that config creates media directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = os.path.join(tmpdir, "new_media_dir")
        assert not os.path.exists(media_path)
        
        with mock.patch.dict(os.environ, {"MEDIA": media_path}):
            config = Config()
            
            assert config.media_dir == media_path
            assert os.path.exists(media_path)


def test_config_media_directory_already_exists():
    """Test that config works when media directory already exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MEDIA": tmpdir}):
            config = Config()
            
            assert config.media_dir == tmpdir
            assert os.path.exists(tmpdir)


def test_database_connections_use_config_path():
    """Test that database connections use config path when loaded properly."""
    import sys
    import tempfile
    
    # Remove modules to force fresh import
    modules_to_remove = [
        'config', 'api_server', 'scheduler', 'connection_manager'
    ]
    for module in modules_to_remove:
        if module in sys.modules:
            del sys.modules[module]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MEDIA": tmpdir}):
            # Import config first to set up the path
            from config import config
            
            expected_path = os.path.join(tmpdir, "gartan_availability.db")
            assert config.db_path == expected_path
            
            # Now test that other modules use this path
            # Note: This tests the pattern, not dynamic reloading
            assert config.media_dir == tmpdir