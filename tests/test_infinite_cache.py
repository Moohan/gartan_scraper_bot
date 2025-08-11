#!/usr/bin/env python3
"""Clean infinite cache tests (fully replaced to remove corruption)."""

import os
import sys
import tempfile
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, ".")
from config import config  # noqa: E402
from gartan_fetch import _is_cache_valid  # noqa: E402


class TestInfiniteCache:
    def test_get_cache_minutes_historic(self):
        for day_offset in [-1, -2, -7, -30]:
            assert config.get_cache_minutes(day_offset) == -1

    def test_get_cache_minutes_current(self):
        assert config.get_cache_minutes(0) == 15

    def test_get_cache_minutes_future(self):
        assert config.get_cache_minutes(1) == 60
        for day_offset in [2, 3, 7, 30]:
            assert config.get_cache_minutes(day_offset) == 60 * 24

    def test_is_cache_valid_infinite(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write("<html>Test cache</html>")
            path = f.name
        try:
            assert _is_cache_valid(path, -1) is True
            assert _is_cache_valid("nonexistent.html", -1) is False
        finally:
            os.unlink(path)

    def test_is_cache_valid_time_based(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write("<html>Test cache</html>")
            path = f.name
        try:
            assert _is_cache_valid(path, 15) is True
            assert _is_cache_valid(path, 60) is True
            assert _is_cache_valid(path, 0) is False
        finally:
            os.unlink(path)

    def test_week_aligned_cache_strategy(self):
        from utils import get_week_aligned_date_range
        today = datetime.now()
        start_date, effective_max_days = get_week_aligned_date_range(3)
        hist = cur = fut = 0
        for offset in range(effective_max_days):
            current_date = start_date + timedelta(days=offset)
            days_from_today = (current_date.date() - today.date()).days
            minutes = config.get_cache_minutes(days_from_today)
            if minutes == -1:
                hist += 1
            elif days_from_today == 0:
                cur += 1
                assert minutes == 15
            else:
                fut += 1
                assert minutes in [60, 60 * 24]
        if today.weekday() > 0:
            assert hist > 0
        assert cur == 1


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
