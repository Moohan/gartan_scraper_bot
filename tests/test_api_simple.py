#!/usr/bin/env python3
"""Tests for API server error handling and edge cases."""

import sqlite3
from datetime import datetime
from unittest.mock import patch

from api_server import get_crew_list_data, merge_time_periods


class TestAPIErrorHandling:
    """Test error handling in API endpoints."""

    def test_get_crew_list_data_database_error(self):
        """Test get_crew_list_data with database connection error."""
        with patch('api_server.sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database connection failed")
            
            result = get_crew_list_data()
            
            # Should return empty list on database error
            assert result == []

    def test_merge_time_periods_empty_list(self):
        """Test merge_time_periods with empty list."""
        assert merge_time_periods([]) == []

    def test_merge_time_periods_single_period(self):
        """Test merge_time_periods with single period."""
        dt1 = datetime(2025, 8, 26, 10, 0)
        dt2 = datetime(2025, 8, 26, 12, 0)
        assert merge_time_periods([(dt1, dt2)]) == [(dt1, dt2)]

    def test_merge_time_periods_overlapping(self):
        """Test merge_time_periods with overlapping periods."""
        dt1 = datetime(2025, 8, 26, 10, 0)
        dt2 = datetime(2025, 8, 26, 12, 0)
        dt3 = datetime(2025, 8, 26, 11, 0)
        dt4 = datetime(2025, 8, 26, 13, 0)
        
        # Overlapping periods should be merged
        periods = [(dt1, dt2), (dt3, dt4)]
        result = merge_time_periods(periods)
        
        # Should result in one merged period
        assert len(result) == 1
        assert result[0] == (dt1, dt4)

    def test_merge_time_periods_non_overlapping(self):
        """Test merge_time_periods with non-overlapping periods."""
        dt1 = datetime(2025, 8, 26, 10, 0)
        dt2 = datetime(2025, 8, 26, 11, 0)
        dt3 = datetime(2025, 8, 26, 13, 0)
        dt4 = datetime(2025, 8, 26, 14, 0)
        
        # Non-overlapping periods should remain separate
        periods = [(dt1, dt2), (dt3, dt4)]
        result = merge_time_periods(periods)
        
        # Should result in two separate periods
        assert len(result) == 2
        assert result == [(dt1, dt2), (dt3, dt4)]
