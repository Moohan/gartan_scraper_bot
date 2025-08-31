import os
import tempfile
from datetime import datetime, timedelta

import pytest

from cache_utils import cache_file_name, cleanup_cache_files, is_cache_expired


def test_cache_file_name():
    date = "05/08/2025"
    fname = cache_file_name(date)
    assert fname.startswith("grid_") and fname.endswith(".html")
    assert "05-08-2025" in fname


def test_is_cache_expired(tmp_path):
    cache_file = tmp_path / "grid_05-08-2025.html"
    cache_file.write_text("test")
    # Not expired if just created
    assert not is_cache_expired(str(cache_file), expiry_minutes=10)
    # Expired if mtime is old
    old_time = datetime.now() - timedelta(minutes=20)
    os.utime(str(cache_file), (old_time.timestamp(), old_time.timestamp()))
    assert is_cache_expired(str(cache_file), expiry_minutes=10)


def test_cleanup_cache_files(tmp_path):
    # Create some cache files with different dates - one old, two recent
    from datetime import datetime

    files = []

    # Create one file and force its mtime to 30 days ago
    old_date = datetime.now() - timedelta(days=30)
    f1 = tmp_path / f"grid_{old_date.strftime('%d-%m-%Y')}.html"
    f1.write_text("test")
    os.utime(str(f1), (old_date.timestamp(), old_date.timestamp()))
    files.append(str(f1))

    # Create two recent files (today and tomorrow)
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    f2 = tmp_path / f"grid_{today.strftime('%d-%m-%Y')}.html"
    f2.write_text("test")
    files.append(str(f2))

    f3 = tmp_path / f"grid_{tomorrow.strftime('%d-%m-%Y')}.html"
    f3.write_text("test")
    files.append(str(f3))

    # Clean up files older than 7 days
    removed = cleanup_cache_files(str(tmp_path), expiry_minutes=7 * 24 * 60)

    # The old file should be removed, recent ones should remain
    assert files[0] in removed
    assert os.path.exists(files[1]) and os.path.exists(files[2])


def test_cleanup_cache_files_no_expired(tmp_path):
    # Create cache files, none expired
    files = []
    for i in range(2):
        f = tmp_path / f"grid_1{i}-08-2025.html"
        f.write_text("test")
        files.append(str(f))
    removed = cleanup_cache_files(str(tmp_path), expiry_minutes=60 * 24)
    assert removed == []
    for f in files:
        assert os.path.exists(f)


def test_cleanup_cache_files_no_cache_files(tmp_path):
    removed = cleanup_cache_files(str(tmp_path), expiry_minutes=60 * 24)
    assert removed == []


def test_cache_file_name_invalid_date():
    date = "invalid-date"
    fname = cache_file_name(date)
    assert fname.startswith("grid_") and fname.endswith(".html")


def test_is_cache_expired_missing_file():
    missing_file = "not_a_real_file.html"
    assert is_cache_expired(missing_file, expiry_minutes=10)


def test_cleanup_cache_files_with_non_cache(tmp_path):
    # Create cache and non-cache files
    cache_file = tmp_path / "grid_05-08-2025.html"
    cache_file.write_text("test")
    non_cache_file = tmp_path / "other.txt"
    non_cache_file.write_text("test")
    # Expire cache file
    old_time = datetime.now() - timedelta(days=2)
    os.utime(str(cache_file), (old_time.timestamp(), old_time.timestamp()))
    removed = cleanup_cache_files(str(tmp_path), expiry_minutes=60 * 24)
    assert str(cache_file) in removed
    assert os.path.exists(str(non_cache_file))


def test_cleanup_cache_files_nonexistent_directory():
    """Test cleanup when cache directory doesn't exist."""
    # Test with non-existent directory (line 70)
    removed = cleanup_cache_files("/nonexistent/path", expiry_minutes=60)
    assert removed == []


def test_cleanup_cache_files_permission_error(tmp_path, monkeypatch):
    """Test cleanup with file permission errors."""
    # Create a cache file
    cache_file = tmp_path / "grid_05-08-2025.html"
    cache_file.write_text("test")

    # Make it old
    old_time = datetime.now() - timedelta(days=2)
    os.utime(str(cache_file), (old_time.timestamp(), old_time.timestamp()))

    # Mock os.remove to raise an exception (lines 88-89)
    def mock_remove(path):
        raise PermissionError("Access denied")

    monkeypatch.setattr("cache_utils.os.remove", mock_remove)

    # Should handle the exception gracefully
    removed = cleanup_cache_files(str(tmp_path), expiry_minutes=60)
    assert removed == []  # No files removed due to permission error
    assert cache_file.exists()  # File still exists
