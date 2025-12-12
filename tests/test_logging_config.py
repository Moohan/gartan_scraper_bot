import logging
from unittest.mock import MagicMock, patch

from logging_config import get_logger, setup_logging


@patch("logging.getLogger")
def test_setup_logging(mock_get_logger):
    """Test that the logger is configured correctly."""
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    setup_logging()
    mock_logger.setLevel.assert_called_with(logging.DEBUG)
    assert mock_logger.addHandler.call_count == 2


@patch("logging.getLogger")
def test_get_logger(mock_get_logger):
    """Test that the correct logger is returned."""
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    logger = get_logger()
    assert logger == mock_logger
