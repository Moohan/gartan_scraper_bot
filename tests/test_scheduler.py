#!/usr/bin/env python3
"""
Comprehensive tests for scheduler.py

Tests the background scheduler functionality including:
- Database health checking
- Scraper execution with subprocess
- Scheduled scraping logic
- Initial data check on startup
- Main scheduler loop
- Error handling and timeouts
"""

import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler import (
    check_database_health,
    initial_data_check,
    main,
    run_scraper,
    scheduled_scrape,
)


class TestScheduler(unittest.TestCase):
    """Test cases for scheduler.py"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        # Mock config
        with patch("scheduler.config") as mock_config:
            mock_config.db_path = self.temp_db.name
            self.mock_config = mock_config

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass

    def test_check_database_health_success(self):
        """Test successful database health check"""
        # Create database with crew and availability data
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()

        # Create tables
        cursor.execute("CREATE TABLE crew (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("""
            CREATE TABLE crew_availability (
                id INTEGER PRIMARY KEY,
                crew_id INTEGER,
                start_time TEXT,
                end_time TEXT
            )
        """)

        # Add test data
        cursor.execute("INSERT INTO crew (name) VALUES ('Test Crew')")
        recent_time = (datetime.now() + timedelta(hours=1)).isoformat()
        cursor.execute(
            """
            INSERT INTO crew_availability (crew_id, start_time, end_time)
            VALUES (1, '2025-01-01T10:00:00', ?)
        """,
            (recent_time,),
        )

        conn.commit()
        conn.close()

        with patch("scheduler.DB_PATH", self.temp_db.name):
            result = check_database_health()

        self.assertTrue(result)

    def test_check_database_health_no_database(self):
        """Test database health check when database doesn't exist"""
        # Remove the temp file
        os.unlink(self.temp_db.name)

        with patch("scheduler.DB_PATH", self.temp_db.name):
            result = check_database_health()

        self.assertFalse(result)

    def test_check_database_health_empty_database(self):
        """Test database health check with empty database"""
        # Create database but no tables
        conn = sqlite3.connect(self.temp_db.name)
        conn.close()

        with patch("scheduler.DB_PATH", self.temp_db.name):
            result = check_database_health()

        self.assertFalse(result)

    def test_check_database_health_no_recent_data(self):
        """Test database health check with no recent availability data"""
        # Create database with crew but old availability data
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE crew (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("""
            CREATE TABLE crew_availability (
                id INTEGER PRIMARY KEY,
                crew_id INTEGER,
                start_time TEXT,
                end_time TEXT
            )
        """)

        # Add old data (more than 1 day ago)
        cursor.execute("INSERT INTO crew (name) VALUES ('Test Crew')")
        old_time = (datetime.now() - timedelta(days=2)).isoformat()
        cursor.execute(
            """
            INSERT INTO crew_availability (crew_id, start_time, end_time)
            VALUES (1, '2025-01-01T10:00:00', ?)
        """,
            (old_time,),
        )

        conn.commit()
        conn.close()

        with patch("scheduler.DB_PATH", self.temp_db.name):
            result = check_database_health()

        self.assertFalse(result)

    @patch("scheduler.logger")
    @patch("scheduler.subprocess.run")
    def test_run_scraper_success(self, mock_subprocess_run, mock_logger):
        """Test successful scraper execution"""
        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Scraper output"
        mock_subprocess_run.return_value = mock_result

        result = run_scraper(3)

        self.assertTrue(result)
        mock_subprocess_run.assert_called_once()
        mock_logger.info.assert_called()

    @patch("scheduler.logger")
    @patch("scheduler.subprocess.run")
    def test_run_scraper_failure(self, mock_subprocess_run, mock_logger):
        """Test scraper execution failure"""
        # Mock failed subprocess run
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Scraper error"
        mock_subprocess_run.return_value = mock_result

        result = run_scraper(3)

        self.assertFalse(result)
        mock_logger.error.assert_called()

    @patch("scheduler.logger")
    @patch(
        "scheduler.subprocess.run",
        side_effect=subprocess.TimeoutExpired("run_bot.py", 300),
    )
    def test_run_scraper_timeout(self, mock_subprocess_run, mock_logger):
        """Test scraper execution timeout"""
        result = run_scraper(3)

        self.assertFalse(result)
        mock_logger.error.assert_called_with("Scraper run timed out after 5 minutes")

    @patch("scheduler.logger")
    @patch("scheduler.subprocess.run", side_effect=Exception("Test error"))
    def test_run_scraper_exception(self, mock_subprocess_run, mock_logger):
        """Test scraper execution with general exception"""
        result = run_scraper(3)

        self.assertFalse(result)
        mock_logger.error.assert_called()

    @patch("scheduler.logger")
    @patch("scheduler.check_database_health", return_value=False)
    @patch("scheduler.run_scraper", return_value=True)
    def test_scheduled_scrape_comprehensive(
        self, mock_run_scraper, mock_check_health, mock_logger
    ):
        """Test scheduled scrape with comprehensive parameters when no recent data"""
        scheduled_scrape()

        # Should run with 7 days when database unhealthy
        mock_run_scraper.assert_called_with(7)
        mock_logger.info.assert_called()

    @patch("scheduler.logger")
    @patch("scheduler.check_database_health", return_value=True)
    @patch("scheduler.run_scraper", return_value=True)
    def test_scheduled_scrape_update(
        self, mock_run_scraper, mock_check_health, mock_logger
    ):
        """Test scheduled scrape with update parameters when database is healthy"""
        scheduled_scrape()

        # Should run with 3 days when database healthy
        mock_run_scraper.assert_called_with(3)
        mock_logger.info.assert_called()

    @patch("scheduler.logger")
    @patch("scheduler.check_database_health", side_effect=[True, False])
    @patch("scheduler.run_scraper", return_value=True)
    def test_scheduled_scrape_health_check_failure(
        self, mock_run_scraper, mock_check_health, mock_logger
    ):
        """Test scheduled scrape when post-run health check fails"""
        scheduled_scrape()

        mock_logger.warning.assert_called_with(
            "Scrape completed but database health check failed"
        )

    @patch("scheduler.logger")
    @patch("scheduler.check_database_health", return_value=True)
    @patch("scheduler.run_scraper", return_value=False)
    def test_scheduled_scrape_run_failure(
        self, mock_run_scraper, mock_check_health, mock_logger
    ):
        """Test scheduled scrape when scraper run fails"""
        scheduled_scrape()

        mock_logger.error.assert_called_with("Scheduled scrape failed")

    @patch("scheduler.logger")
    @patch("scheduler.check_database_health", return_value=False)
    @patch("scheduler.run_scraper", return_value=True)
    def test_initial_data_check_needed(
        self, mock_run_scraper, mock_check_health, mock_logger
    ):
        """Test initial data check when data is needed"""
        initial_data_check()

        # Should run comprehensive scrape (7 days)
        mock_run_scraper.assert_called_with(7)
        mock_logger.info.assert_called()

    @patch("scheduler.logger")
    @patch("scheduler.check_database_health", return_value=True)
    @patch("scheduler.run_scraper")
    def test_initial_data_check_not_needed(
        self, mock_run_scraper, mock_check_health, mock_logger
    ):
        """Test initial data check when data already exists"""
        initial_data_check()

        # Should not run scraper
        mock_run_scraper.assert_not_called()
        mock_logger.info.assert_called_with(
            "Database contains valid data - skipping initial scrape"
        )

    @patch("scheduler.logger")
    @patch("scheduler.check_database_health", return_value=False)
    @patch("scheduler.run_scraper", return_value=False)
    def test_initial_data_check_failure(
        self, mock_run_scraper, mock_check_health, mock_logger
    ):
        """Test initial data check when scraper fails"""
        initial_data_check()

        mock_logger.error.assert_called_with(
            "Initial scrape failed - will retry on next scheduled run"
        )

    @patch("scheduler.logger")
    @patch("scheduler.schedule")
    @patch("scheduler.initial_data_check")
    @patch("scheduler.scheduled_scrape")
    def test_main_successful_startup(
        self, mock_scheduled_scrape, mock_initial_check, mock_schedule, mock_logger
    ):
        """Test successful main scheduler startup"""
        # Mock schedule to exit quickly
        mock_schedule.run_pending.return_value = None

        with patch("scheduler.time.sleep", side_effect=KeyboardInterrupt()):
            main()

        mock_initial_check.assert_called_once()
        mock_logger.info.assert_called()

    @patch("scheduler.logger")
    @patch("scheduler.schedule")
    @patch("scheduler.initial_data_check")
    def test_main_keyboard_interrupt(
        self, mock_initial_check, mock_schedule, mock_logger
    ):
        """Test main scheduler handles keyboard interrupt"""
        with patch("scheduler.time.sleep", side_effect=KeyboardInterrupt()):
            main()

        mock_logger.info.assert_called_with("Scheduler stopped by user")

    @patch("scheduler.logger")
    @patch("scheduler.schedule")
    @patch("scheduler.initial_data_check")
    def test_main_exception_handling(
        self, mock_initial_check, mock_schedule, mock_logger
    ):
        """Test main scheduler handles general exceptions"""
        with patch("scheduler.time.sleep", side_effect=Exception("Test error")):
            with self.assertRaises(Exception):
                main()

        mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()
