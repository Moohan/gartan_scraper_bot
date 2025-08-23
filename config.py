"""Minimal configuration for Gartan Scraper Bot."""

import os


class Config:
    """Configuration class with attribute access."""

    def __init__(self):
        self.log_level = "DEBUG"
        # Use container path if running in container, local path otherwise
        if os.path.exists("/app"):
            self.db_path = "/app/data/gartan_availability.db"
        else:
            self.db_path = "gartan_availability.db"
        self.cache_dir = "_cache"
        self.max_cache_minutes = 60 * 24 * 7  # 1 week
        self.gartan_username = os.environ.get("GARTAN_USERNAME", "")
        self.gartan_password = os.environ.get("GARTAN_PASSWORD", "")
        # Use container path if running in container, local path otherwise
        if os.path.exists("/app"):
            self.log_file = "/app/logs/gartan_debug.log"
        else:
            self.log_file = "gartan_debug.log"
        self.max_log_size = 10 * 1024 * 1024  # 10MB
        self.max_workers = 4  # For concurrent processing

    def get_cache_minutes(self, day_offset: int) -> int:
        """
        Get cache expiry minutes based on day offset from today.

        Args:
            day_offset: Days relative to today (negative = historic, 0 = today, positive = future)

        Returns:
            Cache expiry minutes (or -1 for infinite cache for historic data)
        """
        if day_offset < 0:  # Historic data - never expires
            return -1  # Special value indicating infinite cache
        elif day_offset == 0:  # Today
            return 15  # 15 minutes
        elif day_offset == 1:  # Tomorrow
            return 60  # 1 hour
        else:  # Future days
            return 60 * 24  # 24 hours


# Global config instance
config = Config()
