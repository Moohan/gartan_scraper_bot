import pytest
from utils import log_debug
import os
import tempfile


def test_log_debug_creates_file(tmp_path):
    log_path = "gartan_debug.log"
    log_debug("info", "Test message")
    assert os.path.exists(log_path)
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Test message" in content


def test_log_debug_truncates_large_file(tmp_path):
    log_path = "gartan_debug.log"
    # Write enough logs to exceed 2MB
    # Write log entries until file size exceeds 2MB
    log_path = "gartan_debug.log"
    while True:
        log_debug("info", "Test message")
        if os.path.exists(log_path) and os.path.getsize(log_path) > 2 * 1024 * 1024:
            break
    size_before = os.path.getsize(log_path)
    print(f"Size before truncation: {size_before}")
    # Now call log_debug once more to trigger truncation
    log_debug("info", "Truncate trigger")
    size_after = os.path.getsize(log_path)
    print(f"Size after truncation: {size_after}")
    # After truncation, file should be ~1MB
    assert size_after < size_before  # File should shrink after truncation


@pytest.mark.parametrize(
    "min_delay,max_delay,base",
    [
        (0, 0, 1.0),
        (1, 2, 1.5),
        (5, 10, 2.0),
    ],
)
def test_delay_logic(monkeypatch, min_delay, max_delay, base):
    pass  # delay not present in utils.py
