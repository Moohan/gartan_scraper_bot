import logging


from utils import delay, log_debug


def test_log_debug_creates_log_entry(tmp_path):
    """Test that log_debug creates log entries via the logging system."""
    # Setup logging with a temporary log file
    temp_log = tmp_path / "test_gartan_debug.log"

    # Clear any existing handlers
    logger = logging.getLogger("gartan_scraper")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add file handler for testing
    handler = logging.FileHandler(str(temp_log))
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    # Test the function
    log_debug("info", "Test message")

    # Ensure the log is written
    handler.flush()

    # Check if file exists and contains the message
    assert temp_log.exists()
    content = temp_log.read_text(encoding="utf-8")
    assert "Test message" in content


def test_log_debug_empty_message(tmp_path):
    """Test that log_debug handles empty messages."""
    temp_log = tmp_path / "test_gartan_debug.log"

    # Clear any existing handlers
    logger = logging.getLogger("gartan_scraper")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add file handler for testing
    handler = logging.FileHandler(str(temp_log))
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    # Test with empty message
    log_debug("info", "")
    handler.flush()

    # Check content - "info" maps to DEBUG level in log_debug function
    content = temp_log.read_text(encoding="utf-8")
    assert "DEBUG" in content
    assert "[info]" in content


def test_log_debug_long_message(tmp_path):
    """Test that log_debug handles long messages."""
    temp_log = tmp_path / "test_gartan_debug.log"

    # Clear any existing handlers
    logger = logging.getLogger("gartan_scraper")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add file handler for testing
    handler = logging.FileHandler(str(temp_log))
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    # Test with long message
    long_msg = "A" * 10000
    log_debug("info", long_msg)
    handler.flush()

    # Check content
    content = temp_log.read_text(encoding="utf-8")
    assert long_msg in content


def test_log_debug_non_utf8(tmp_path):
    """Test that log_debug handles unicode characters."""
    temp_log = tmp_path / "test_gartan_debug.log"

    # Clear any existing handlers
    logger = logging.getLogger("gartan_scraper")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add file handler for testing
    handler = logging.FileHandler(str(temp_log), encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    # Test with unicode
    msg = "Test with emoji 🚒"
    log_debug("info", msg)
    handler.flush()

    # Check content
    content = temp_log.read_text(encoding="utf-8")
    assert "🚒" in content


def test_log_debug_different_levels(tmp_path):
    """Test that log_debug handles different log levels correctly."""
    temp_log = tmp_path / "test_gartan_debug.log"

    # Clear any existing handlers
    logger = logging.getLogger("gartan_scraper")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add file handler for testing
    handler = logging.FileHandler(str(temp_log))
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    # Test different levels
    log_debug("error", "Error message")
    log_debug("warning", "Warning message")
    log_debug("info", "Info message")
    log_debug("debug", "Debug message")

    # Ensure the log is written
    handler.flush()

    # Check content
    content = temp_log.read_text(encoding="utf-8")
    assert "ERROR" in content
    assert "WARNING" in content
    assert "DEBUG" in content
    assert "Error message" in content
    assert "Warning message" in content
    assert "Info message" in content


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


def test_delay_no_max_delay(monkeypatch):
    """Test delay function when max_delay is None."""
    sleep_calls = []
    monkeypatch.setattr("time.sleep", lambda x: sleep_calls.append(x))

    # When max_delay is None, should use min_delay directly (line 92)
    delay(min_delay=1.5, max_delay=None)  # Use < 2 to avoid countdown loop

    # Should have called sleep once with min_delay
    assert len(sleep_calls) == 1
    assert sleep_calls[0] == 1.5
