#!/usr/bin/env python3
"""
Unit tests for infinite cache functionality

Tests the cache behavior for historic vs current/future data
"""

import pytest
import tempfile
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from gartan_fetch import _is_cache_valid
from config import config


class TestInfiniteCache:
    """Test infinite cache behavior for historic data."""

    def test_get_cache_minutes_historic(self):
        """Test that historic dates return infinite cache (-1)."""
        # Test various historic day offsets
        for day_offset in [-1, -2, -7, -30]:
            cache_minutes = config.get_cache_minutes(day_offset)
            assert cache_minutes == -1, f"Historic day offset {day_offset} should return -1 (infinite cache)"

    def test_get_cache_minutes_current(self):
        """Test that today returns 15 minutes cache."""
        cache_minutes = config.get_cache_minutes(0)
        assert cache_minutes == 15, "Today should return 15 minutes cache"

    def test_get_cache_minutes_future(self):
        """Test that future dates return appropriate cache durations."""
        # Tomorrow
        assert config.get_cache_minutes(1) == 60, "Tomorrow should return 60 minutes"
        
        # Future days
        for day_offset in [2, 3, 7, 30]:
            cache_minutes = config.get_cache_minutes(day_offset)
            assert cache_minutes == 60 * 24, f"Future day {day_offset} should return 24 hours"

    def test_is_cache_valid_infinite(self):
        """Test that infinite cache (-1) always returns True if file exists."""
        # Create temporary cache file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
            temp_file.write("<html>Test cache</html>")
            cache_file = temp_file.name

        try:
            # Test infinite cache
            assert _is_cache_valid(cache_file, -1) == True, "Infinite cache should always be valid"
            
            # Test non-existent file
            assert _is_cache_valid("nonexistent.html", -1) == False, "Non-existent file should not be valid"
            
        finally:
            os.unlink(cache_file)

    def test_is_cache_valid_time_based(self):
        """Test that time-based cache works correctly."""
        # Create temporary cache file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
            temp_file.write("<html>Test cache</html>")
            cache_file = temp_file.name

        try:
            # Test that fresh file is valid for any reasonable cache duration
            assert _is_cache_valid(cache_file, 15) == True, "Fresh cache should be valid"
            assert _is_cache_valid(cache_file, 60) == True, "Fresh cache should be valid"
            
            # Test zero cache duration (immediate expiry)
            assert _is_cache_valid(cache_file, 0) == False, "Zero cache duration should be invalid"
            
        finally:
            os.unlink(cache_file)

    def test_week_aligned_cache_strategy(self):
        """Test cache strategy for week-aligned date range."""
        from utils import get_week_aligned_date_range
        
        today = datetime.now()
        start_date, effective_max_days = get_week_aligned_date_range(3)
        
        historic_count = 0
        current_count = 0
        future_count = 0
        
        for day_offset in range(effective_max_days):
            current_date = start_date + timedelta(days=day_offset)
            days_from_today = (current_date.date() - today.date()).days
            cache_minutes = config.get_cache_minutes(days_from_today)
            
            if cache_minutes == -1:
                historic_count += 1
            elif days_from_today == 0:
                current_count += 1
                assert cache_minutes == 15, "Today should have 15 minute cache"
            else:
                future_count += 1
                assert cache_minutes in [60, 60*24], "Future should have 1hr or 24hr cache"
        
        # Should have some historic data (since we start from Monday)
        if today.weekday() > 0:  # Not Monday
            assert historic_count > 0, "Should have historic data when not running on Monday"
        
        # Should always have exactly one "today"
        assert current_count == 1, "Should have exactly one 'today' entry"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
