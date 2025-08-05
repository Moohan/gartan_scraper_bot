import pytest
from cache_utils import cache_file_name, is_cache_expired, cleanup_cache_files
import tempfile
import os
from datetime import datetime, timedelta


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
    # Create some cache files
    files = []
    for i in range(3):
        f = tmp_path / f"grid_0{i}-08-2025.html"
        f.write_text("test")
        files.append(str(f))
    # Expire one file
    old_time = datetime.now() - timedelta(days=2)
    os.utime(files[0], (old_time.timestamp(), old_time.timestamp()))
    removed = cleanup_cache_files(str(tmp_path), expiry_minutes=60 * 24)
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
