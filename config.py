"""Configuration management for Gartan Scraper Bot."""

from dataclasses import dataclass
from typing import Dict, Optional
import os
from pathlib import Path


@dataclass
class ScraperConfig:
    """Configuration settings for the Gartan Scraper Bot."""

    cache_dir: str = "_cache"
    max_workers: int = 4
    log_file: str = "gartan_debug.log"
    max_log_size: int = 10 * 1024 * 1024  # 10MB
    db_file: str = "gartan_availability.db"
    crew_details_file: str = "crew_details.local"

    # Cache expiry times in minutes for different day offsets
    cache_minutes: Dict[int, int] | None = None

    def __post_init__(self):
        if self.cache_minutes is None:
            self.cache_minutes = {
                0: 15,  # Today
                1: 60,  # Tomorrow
                2: 360,  # Next week
                8: 1440,  # Beyond
            }

        # Ensure cache directory exists
        Path(self.cache_dir).mkdir(exist_ok=True)

    @property
    def gartan_username(self) -> Optional[str]:
        """Get Gartan username from environment variables."""
        return os.getenv("GARTAN_USERNAME")

    @property
    def gartan_password(self) -> Optional[str]:
        """Get Gartan password from environment variables."""
        return os.getenv("GARTAN_PASSWORD")

    def get_cache_minutes(self, day_offset: int) -> int:
        """Get cache expiry time in minutes for a given day offset."""
        if not self.cache_minutes:
            # This shouldn't happen due to __post_init__, but just in case
            self.cache_minutes = {
                0: 15,  # Today
                1: 60,  # Tomorrow
                2: 360,  # Next week
                8: 1440,  # Beyond
            }

        # Return the cache time for the smallest threshold that is >= day_offset
        for threshold, minutes in sorted(self.cache_minutes.items()):
            if day_offset <= threshold:
                return minutes
        # If no threshold matches, use the largest threshold's value
        return self.cache_minutes[max(self.cache_minutes.keys())]


# Global config instance
config = ScraperConfig()
