#!/usr/bin/env python3
"""
Test weekly availability API endpoints

Tests the new weekly availability hour tracking endpoints
"""

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

import pytest

from api_server import (
    DB_PATH,
    get_crew_hours_planned_week_data,
    get_crew_hours_this_week_data,
    get_week_boundaries,
)


class TestWeeklyAPI:
    """Test weekly availability calculations"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        # Create temporary database file
        fd, temp_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # Store original DB_PATH
        import api_server

        original_path = api_server.DB_PATH
        api_server.DB_PATH = temp_path

        # Create test database schema
        conn = sqlite3.connect(temp_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE crew (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)

        cursor.execute("""
            CREATE TABLE crew_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crew_id INTEGER NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME NOT NULL,
                FOREIGN KEY (crew_id) REFERENCES crew (id)
            )
        """)

        # Insert test crew
        cursor.execute("INSERT INTO crew (id, name) VALUES (1, 'TEST CREW')")

        conn.commit()
        conn.close()

        yield temp_path

        # Cleanup
        api_server.DB_PATH = original_path
        # On Windows the SQLite file can remain locked briefly; ignore if still in use
        try:
            os.unlink(temp_path)
        except PermissionError:
            pass

    def test_week_boundaries(self):
        """Test week boundary calculation"""
        start, end = get_week_boundaries()

        # Should be Monday 00:00:00
        assert start.weekday() == 0  # Monday
        assert start.hour == 0
        assert start.minute == 0
        assert start.second == 0

        # Should be Sunday 23:59:59
        assert end.weekday() == 6  # Sunday
        assert end.hour == 23
        assert end.minute == 59
        assert end.second == 59

        # Should be 6 days, 23:59:59 apart
        duration = end - start
        expected_duration = timedelta(days=6, hours=23, minutes=59, seconds=59)
        assert abs(duration.total_seconds() - expected_duration.total_seconds()) < 1

    def test_crew_not_found(self, temp_db):
        """Test error handling for non-existent crew"""
        result = get_crew_hours_this_week_data(999)
        assert "error" in result
        assert "not found" in result["error"]

        result = get_crew_hours_planned_week_data(999)
        assert "error" in result
        assert "not found" in result["error"]

    def test_no_availability_data(self, temp_db):
        """Test with crew but no availability blocks"""
        result = get_crew_hours_this_week_data(1)
        assert result == {"hours_this_week": 0.0}

        result = get_crew_hours_planned_week_data(1)
        assert result == {"hours_planned_week": 0.0}

    def test_partial_week_availability(self, temp_db):
        """Test availability that started earlier in the week"""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Get week boundaries
        week_start, week_end = get_week_boundaries()

        # Add availability from Tuesday 10:00 to Wednesday 14:00 (28 hours)
        tuesday_10 = week_start + timedelta(days=1, hours=10)  # Tuesday 10:00
        wednesday_14 = week_start + timedelta(days=2, hours=14)  # Wednesday 14:00

        cursor.execute(
            """
            INSERT INTO crew_availability (crew_id, start_time, end_time)
            VALUES (1, ?, ?)
        """,
            (tuesday_10.isoformat(), wednesday_14.isoformat()),
        )

        conn.commit()
        conn.close()

        # Test hours this week (should be full 28 hours if we're past Wednesday 14:00)
        result = get_crew_hours_this_week_data(1)
        now = datetime.now()

        if now > wednesday_14:
            # Past the end time, should get full 28 hours
            assert result["hours_this_week"] == 28.0
        elif now < tuesday_10:
            # Before the block has started this week
            assert result["hours_this_week"] == 0.0
        else:
            # During the availability period so far
            assert 0.0 <= result["hours_this_week"] <= 28.0

        # Test planned hours for week (should always be 28)
        result = get_crew_hours_planned_week_data(1)
        assert result["hours_planned_week"] == 28.0

    def test_cross_week_availability(self, temp_db):
        """Test availability that spans multiple weeks"""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Get week boundaries
        week_start, week_end = get_week_boundaries()

        # Add availability from previous Sunday to next Tuesday
        prev_sunday = week_start - timedelta(days=1)
        next_tuesday = week_end + timedelta(days=2)

        cursor.execute(
            """
            INSERT INTO crew_availability (crew_id, start_time, end_time)
            VALUES (1, ?, ?)
        """,
            (prev_sunday.isoformat(), next_tuesday.isoformat()),
        )

        conn.commit()
        conn.close()

        # Should only count hours within current week
        result = get_crew_hours_planned_week_data(1)

        # Should be exactly 7 days (168 hours)
        assert result["hours_planned_week"] == 168.0

    def test_multiple_availability_blocks(self, temp_db):
        """Test multiple separate availability blocks"""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Get week boundaries
        week_start, week_end = get_week_boundaries()

        # Add two separate 12-hour blocks
        # Monday 08:00 - 20:00 (12 hours)
        monday_8 = week_start + timedelta(hours=8)
        monday_20 = week_start + timedelta(hours=20)

        # Wednesday 09:00 - 21:00 (12 hours)
        wednesday_9 = week_start + timedelta(days=2, hours=9)
        wednesday_21 = week_start + timedelta(days=2, hours=21)

        cursor.execute(
            """
            INSERT INTO crew_availability (crew_id, start_time, end_time)
            VALUES (1, ?, ?)
        """,
            (monday_8.isoformat(), monday_20.isoformat()),
        )

        cursor.execute(
            """
            INSERT INTO crew_availability (crew_id, start_time, end_time)
            VALUES (1, ?, ?)
        """,
            (wednesday_9.isoformat(), wednesday_21.isoformat()),
        )

        conn.commit()
        conn.close()

        # Should total 24 hours for the week
        result = get_crew_hours_planned_week_data(1)
        assert result["hours_planned_week"] == 24.0

    def test_hours_precision(self, temp_db):
        """Test that hours are calculated with proper precision"""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Get week boundaries
        week_start, week_end = get_week_boundaries()

        # Add 90 minute block (1.5 hours)
        start_time = week_start + timedelta(hours=10)
        end_time = start_time + timedelta(minutes=90)

        cursor.execute(
            """
            INSERT INTO crew_availability (crew_id, start_time, end_time)
            VALUES (1, ?, ?)
        """,
            (start_time.isoformat(), end_time.isoformat()),
        )

        conn.commit()
        conn.close()

        result = get_crew_hours_planned_week_data(1)
        assert result["hours_planned_week"] == 1.5


if __name__ == "__main__":
    pytest.main([__file__])
