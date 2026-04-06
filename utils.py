"""Utility functions for Gartan Scraper Bot."""

import random
import time
import zoneinfo
from datetime import datetime, timedelta
from typing import Optional, Union

from logging_config import get_logger

logger = get_logger()

LONDON_TZ = zoneinfo.ZoneInfo("Europe/London")

def log_debug(module: str, message: str):
    """Log a debug message or severity-mapped message."""
    module_upper = module.upper()
    if module_upper == "ERROR":
        logger.error(f"[{module_upper}] {message}")
    elif module_upper in ["WARN", "WARNING"]:
        logger.warning(f"[{module_upper}] {message}")
    else:
        logger.debug(f"[{module_upper}] {message}")

def get_now() -> datetime:
    """Get the current time in Europe/London timezone."""
    return datetime.now(LONDON_TZ)

def parse_uk_datetime(dt_str: str, dt_format: str = "%d/%m/%Y %H%M") -> datetime:
    """Parse a datetime string assuming it's in Europe/London timezone."""
    naive_dt = datetime.strptime(dt_str, dt_format)
    return naive_dt.replace(tzinfo=LONDON_TZ)

def parse_uk_date(date_str: str, dt_format: str = "%d/%m/%Y") -> datetime:
    """Parse a date string assuming it's in Europe/London timezone."""
    naive_dt = datetime.strptime(date_str, dt_format)
    return naive_dt.replace(tzinfo=LONDON_TZ)

def ensure_london(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure a datetime is aware and in Europe/London timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=LONDON_TZ)
    return dt.astimezone(LONDON_TZ)

def get_now_iso() -> str:
    """Get the current time in Europe/London timezone as ISO string."""
    return get_now().isoformat()

def get_week_aligned_date_range(max_days: int) -> tuple[datetime, int]:
    """Get start date and effective max days, aligned to current week start."""
    now = get_now()
    # Start from Monday of current week
    start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    # Adjust max_days to include days from Monday to today
    effective_max_days = max_days + now.weekday()
    return start_date, effective_max_days
