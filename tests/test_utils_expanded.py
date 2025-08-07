import pytest
from utils import log_debug, delay
import os
import tempfile
import logging
from logging_config import setup_logging, get_logger


def test_log_debug_creates_file(tmp_path):
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
    assert "info" in content


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


def test_delay_function_exists():
    """Test that the delay function exists and can be called."""
    # Should not raise an exception - test with very small delay
    delay(0.01, 0.01, 1.0)
    assert True


@pytest.mark.parametrize(
    "min_delay,max_delay,base,day_offset",
    [
        (0, 0, 1.0, 0),
        (0.01, 0.02, 1.5, 0),
        (0.01, 0.05, 2.0, 1),
    ],
)
def test_delay_logic(monkeypatch, min_delay, max_delay, base, day_offset):
    """Test delay function with mocked time.sleep."""
    # Mock time.sleep to prevent actual delays in tests
    sleep_calls = []
    def mock_sleep(seconds):
        sleep_calls.append(seconds)
    
    monkeypatch.setattr("time.sleep", mock_sleep)
    
    # Call delay function
    delay(min_delay, max_delay, base, day_offset)
    
    # Verify sleep was called with appropriate duration
    assert len(sleep_calls) > 0
    total_sleep = sum(sleep_calls)
    
    # For delays with max_delay, verify result is within expected range
    if max_delay is not None:
        expected_max = min(max_delay, min_delay * (base ** max(0, day_offset)))
        assert min_delay <= total_sleep <= expected_max
    else:
        assert total_sleep == min_delay
