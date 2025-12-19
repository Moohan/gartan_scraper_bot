"""Utility functions for Gartan Scraper Bot."""

import random
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, Union

from logging_config import get_logger

logger = get_logger()


def get_week_aligned_date_range(max_days: int) -> Tuple[datetime, int]:
    """
    Calculate week-aligned date range for data fetching.

    Ensures we always fetch from Monday of current week onwards,
    which is required for weekly availability tracking.

    Args:
        max_days: Maximum days to fetch from command line

    Returns:
        Tuple of (start_date, effective_max_days) where:
        - start_date: Monday of current week at 00:00:00
        - effective_max_days: Adjusted max_days to cover full period
    """
    now = datetime.now()

    # Get Monday of current week (weekday 0=Monday, 6=Sunday)
    days_since_monday = now.weekday()
    monday_start = now - timedelta(days=days_since_monday)
    week_start = monday_start.replace(hour=0, minute=0, second=0, microsecond=0)

    # Calculate how many days we need to fetch
    days_from_monday_to_today = days_since_monday
    days_from_today_forward = max_days

    # Ensure we cover at least through next Sunday
    total_days_needed = days_from_monday_to_today + days_from_today_forward
    min_days_for_full_week = days_since_monday + (
        7 - days_since_monday
    )  # To next Sunday

    effective_max_days = max(total_days_needed, min_days_for_full_week)

    logger.info(
        f"Week-aligned fetching: Start from {week_start.strftime('%Y-%m-%d')} (Monday), "
        f"fetch {effective_max_days} days total"
    )
    logger.info(
        f"This covers {days_from_monday_to_today} historic days + "
        f"{effective_max_days - days_from_monday_to_today} future days"
    )

    return week_start, effective_max_days


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
    Implements an efficient delay with optional exponential backoff.

    Args:
        min_delay: Minimum delay time in seconds.
        max_delay: Maximum delay time in seconds (optional).
        base: Base for exponential backoff (default: 1.5).
        day_offset: Current day offset for backoff calculation.
    """
    if max_delay is None:
        actual_delay = min_delay
    else:
        # Calculate delay with exponential backoff and add jitter
        backoff_delay = min_delay * (base**max(0, day_offset))
        capped_delay = min(max_delay, backoff_delay)
        actual_delay = random.uniform(min_delay, capped_delay)

    # Bolt ⚡: Replaced an inefficient countdown loop with a single time.sleep() call.
    # The previous implementation woke the CPU every second, leading to unnecessary
    # context switching. This change reduces CPU usage and improves timer accuracy
    # by sleeping for the entire duration in one go.
    if actual_delay > 0:
        logger.debug(f"Waiting {actual_delay:.2f}s before next operation.")
        time.sleep(actual_delay)
