"""Cache utilities for Gartan Scraper Bot."""

import os
import re
from datetime import datetime, timedelta
from typing import Optional

from logging_config import get_logger

logger = get_logger()


def cache_file_name(booking_date: str) -> str:
    """
    Generate cache filename from booking date.

    Args:
        booking_date: Date string in DD/MM/YYYY format

    Returns:
        Cache filename in grid_DD-MM-YYYY.html format
        If date is invalid, returns a default filename with current date
    """
    try:
        date_obj = datetime.strptime(booking_date, "%d/%m/%Y")
    except ValueError:
        logger.warning(f"Invalid date format '{booking_date}', using current date")
        date_obj = datetime.now()
    return f"grid_{date_obj.strftime('%d-%m-%Y')}.html"


def is_cache_expired(
    cache_file: str, expiry_minutes: int, now: Optional[datetime] = None
) -> bool:
    """
    Check if cache file is expired.

    Args:
        cache_file: Path to cache file
        expiry_minutes: Cache expiry time in minutes
        now: Current time (for testing)

    Returns:
        True if cache is expired or doesn't exist
    """
    if not os.path.exists(cache_file):
        return True

    if now is None:
        now = datetime.now()

    mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
    expiry = mtime + timedelta(minutes=expiry_minutes)

    return now > expiry


def cleanup_cache_files(cache_dir: str, expiry_minutes: int = 43200) -> list[str]:
    """
    Clean up old cache files.

    Args:
        cache_dir: Cache directory path
        expiry_minutes: Maximum age of cache files in minutes

    Returns:
        List of removed file paths
    """
    if not os.path.exists(cache_dir):
        return []

    now = datetime.now()
    pattern = re.compile(r"grid_(\d{2}-\d{2}-\d{4})\.html")
    removed = []

    for fname in os.listdir(cache_dir):
        match = pattern.match(fname)
        if not match:
            continue

        try:
            file_date = datetime.strptime(match.group(1), "%d-%m-%Y")
            file_path = os.path.join(cache_dir, fname)

            # Age is computed in whole days to avoid prematurely deleting yesterday's
            # file during the current day (matches test expectations). This treats
            # any time within the same calendar day as age 0.
            age_days = (now.date() - file_date.date()).days
            file_age_minutes = age_days * 24 * 60

            if file_age_minutes > expiry_minutes:
                os.remove(file_path)
                removed.append(file_path)
                logger.info(f"Deleted old cache file: {fname}")
        except Exception as e:
            logger.warning(f"Failed to process cache file {fname}: {e}")

    return removed
