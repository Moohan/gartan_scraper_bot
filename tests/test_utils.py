import os
import pytest
from utils import log_debug, delay


def cleanup_log():
    log_path = "gartan_debug.log"
    if os.path.exists(log_path):
        os.remove(log_path)


# --- log_debug tests ---
def test_log_debug_creates_and_truncates_file():
    cleanup_log()
    msg = "Test message"
    level = "info"
    for _ in range(3000):
        log_debug(level, msg)
    size = os.path.getsize("gartan_debug.log")
    assert size <= 2 * 1024 * 1024  # Should be truncated to 1MB after exceeding 2MB
    with open("gartan_debug.log", "r", encoding="utf-8") as f:
        content = f.read()
        assert msg in content
    cleanup_log()


def test_log_debug_empty_message():
    cleanup_log()
    log_debug("info", "")
    with open("gartan_debug.log", "r", encoding="utf-8") as f:
        content = f.read()
    assert "info" in content
    cleanup_log()


def test_log_debug_long_message():
    cleanup_log()
    long_msg = "A" * 10000
    log_debug("info", long_msg)
    with open("gartan_debug.log", "r", encoding="utf-8") as f:
        content = f.read()
    assert long_msg in content
    cleanup_log()


def test_log_debug_non_utf8():
    cleanup_log()
    msg = "Test with emoji 🚒"
    log_debug("info", msg)
    with open("gartan_debug.log", "r", encoding="utf-8") as f:
        content = f.read()
    assert "🚒" in content
    cleanup_log()


def test_log_debug_readonly_file():
    cleanup_log()
    log_path = "gartan_debug.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("Initial log\n")
    os.chmod(log_path, 0o444)  # Read-only
    raised = False
    try:
        log_debug("info", "Should fail")
    except Exception:
        raised = True
    finally:
        os.chmod(log_path, 0o666)  # Restore permissions
        os.remove(log_path)
    assert raised


# --- delay tests ---
def test_delay_logic(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda x: None)
    delay(1, 2, 1.5)
    delay(0, 0, 1.0)
    delay(5, 10, 2.0)


def test_delay_min_greater_than_max(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda x: None)
    delay(5, 2, 1.0)  # Should not sleep or error


def test_delay_negative(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda x: None)
    delay(-1, -2, 1.0)  # Should not sleep or error


def test_delay_zero_base(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda x: None)
    delay(1, 2, 0)  # Should not sleep or error


def test_delay_float(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda x: None)
    delay(0.5, 1.5, 1.2)  # Should not error
