"""Utility functions for Gartan Scraper Bot."""

import time
import random
from typing import Optional, Union
from logging_config import get_logger

logger = get_logger()


def log_debug(category: str, message: str) -> None:
    """
    Centralized debug logger for Gartan Scraper Bot.
    This is a compatibility wrapper for the new logging system.

    Args:
        category: The log category/component
        message: The message to log
    """
    if category.lower() == "error":
        logger.error(f"[{category}] {message}")
    elif category.lower() == "warning":
        logger.warning(f"[{category}] {message}")
    else:
        logger.debug(f"[{category}] {message}")


def delay(
    min_delay: Union[int, float],
    max_delay: Optional[Union[int, float]] = None,
    base: float = 1.5,
    day_offset: int = 0,
) -> None:
    """
    Implements delay with optional exponential backoff.

    Args:
        min_delay: Minimum delay time in seconds
        max_delay: Maximum delay time in seconds (optional)
        base: Base for exponential backoff (default: 1.5)
        day_offset: Current day offset for backoff calculation
    """
    if max_delay is None:
        actual_delay = min_delay
    else:
        delay = min(max_delay, min_delay * (base ** max(0, day_offset)))
        actual_delay = random.uniform(min_delay, delay)

    if actual_delay >= 2:
        logger.debug(f"Waiting {actual_delay:.1f}s before next operation.")
        for i in range(int(actual_delay), 0, -1):
            logger.debug(f"{i} seconds left.")
            time.sleep(1)
        leftover = actual_delay - int(actual_delay)
        if leftover > 0:
            time.sleep(leftover)
    else:
        time.sleep(actual_delay)
