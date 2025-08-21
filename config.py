"""Minimal configuration for Gartan Scraper Bot."""

import os


class Config:
    """Configuration class with attribute access."""

    def __init__(self):
        self.log_level = "DEBUG"
        
        # Get media directory from environment, default to current directory
        self.media_dir = os.environ.get("MEDIA", ".")
        
        # Ensure media directory exists
        if not os.path.exists(self.media_dir):
            os.makedirs(self.media_dir, exist_ok=True)
        
        # Configure all persistent file paths relative to media directory
        self.db_path = os.path.join(self.media_dir, "gartan_availability.db")
        self.cache_dir = os.path.join(self.media_dir, "_cache")
        self.log_file = os.path.join(self.media_dir, "gartan_debug.log")
        self.crew_details_file = os.path.join(self.media_dir, "crew_details.local")
        
        # Other configuration
        self.max_cache_minutes = 60 * 24 * 7  # 1 week
        self.gartan_username = os.environ.get("GARTAN_USERNAME", "")
        self.gartan_password = os.environ.get("GARTAN_PASSWORD", "")
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
