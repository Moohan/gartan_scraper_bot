"""Logging configuration for Gartan Scraper Bot."""

import logging
from logging.handlers import RotatingFileHandler
from typing import Optional
import os

from config import config


def setup_logging(log_level: int = logging.DEBUG) -> None:
    """Configure logging with file and console handlers."""
    # Create logger
    logger = logging.getLogger("gartan_scraper")
    logger.setLevel(log_level)

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")

    # Create the log directory if it doesn't exist
    log_dir = os.path.dirname(config.log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        config.log_file, maxBytes=config.max_log_size, backupCount=3
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def get_logger() -> logging.Logger:
    """Get the configured logger instance."""
    return logging.getLogger("gartan_scraper")
