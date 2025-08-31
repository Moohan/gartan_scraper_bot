#!/usr/bin/env python3
"""
Comprehensive tests for container_main.py

Tests the container orchestrator functionality including:
- Process management and monitoring
- Signal handling and graceful shutdown
- Database readiness waiting
- Error handling in subprocesses
- Main orchestrator logic
"""

import os
import signal
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from multiprocessing import Process
from unittest.mock import MagicMock, Mock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from container_main import (
    main,
    processes,
    run_api_server,
    run_scheduler,
    shutdown_flag,
    signal_handler,
    wait_for_database,
)


class TestContainerMain(unittest.TestCase):
    """Test cases for container_main.py"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset global state
        global processes, shutdown_flag
        processes.clear()
        shutdown_flag.clear()

        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        # Mock config
        with patch("container_main.config") as mock_config:
            mock_config.db_path = self.temp_db.name
            self.mock_config = mock_config

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass

    @patch("container_main.sys.exit")
    def test_signal_handler_graceful_shutdown(self, mock_exit):
        """Test signal handler initiates graceful shutdown"""
        # Mock processes
        mock_process1 = Mock()
        mock_process1.is_alive.side_effect = [
            True,
            False,
        ]  # Alive before terminate, dead after join
        mock_process1.name = "test_process1"

        mock_process2 = Mock()
        mock_process2.is_alive.return_value = False
        mock_process2.name = "test_process2"

        global processes
        processes.extend([mock_process1, mock_process2])

        # Call signal handler
        signal_handler(signal.SIGTERM, None)

        # Verify shutdown flag is set
        self.assertTrue(shutdown_flag.is_set())

        # Verify processes were terminated
        mock_process1.terminate.assert_called_once()
        mock_process1.join.assert_called_once_with(timeout=5)
        mock_process1.kill.assert_not_called()  # Should not be killed if terminate works

        # Verify dead process wasn't terminated
        mock_process2.terminate.assert_not_called()

        # Verify sys.exit was called
        mock_exit.assert_called_once_with(0)

    @patch("container_main.sys.exit")
    def test_signal_handler_force_kill(self, mock_exit):
        """Test signal handler force kills unresponsive processes"""
        # Mock unresponsive process
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        mock_process.name = "unresponsive_process"

        global processes
        processes.append(mock_process)

        # Make terminate not work (process still alive after join)
        mock_process.join.return_value = (
            None  # join doesn't return anything when timeout
        )

        # Call signal handler
        signal_handler(signal.SIGTERM, None)

        # Verify force kill was called
        mock_process.kill.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch("container_main.logger")
    def test_run_scheduler_success(self, mock_logger):
        """Test successful scheduler process execution"""
        with patch("scheduler.main") as mock_scheduler_main:
            run_scheduler()
            mock_scheduler_main.assert_called_once()
            mock_logger.info.assert_called()

    @patch("container_main.logger")
    def test_run_scheduler_failure(self, mock_logger):
        """Test scheduler process failure handling"""
        with patch("scheduler.main", side_effect=Exception("Test error")):
            with self.assertRaises(Exception):
                run_scheduler()
            mock_logger.error.assert_called()

    @patch("container_main.logger")
    @patch("api_server.app")
    def test_run_api_server_success(self, mock_app, mock_logger):
        """Test successful API server process execution"""
        mock_app.run = Mock()

        with patch.dict(os.environ, {"PORT": "8080"}):
            run_api_server()

        mock_app.run.assert_called_once_with(
            host="0.0.0.0", port=8080, debug=False, use_reloader=False
        )
        mock_logger.info.assert_called()

    @patch("container_main.logger")
    def test_run_api_server_failure(self, mock_logger):
        """Test API server process failure handling"""
        with patch("api_server.app") as mock_app:
            mock_app.run.side_effect = Exception("Test error")
            with self.assertRaises(Exception):
                run_api_server()
            mock_logger.error.assert_called()

    def test_wait_for_database_success(self):
        """Test successful database waiting"""
        # Create database with crew table and data
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE crew (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO crew (name) VALUES ('Test Crew')")
        conn.commit()
        conn.close()

        with patch("container_main.config", self.mock_config):
            result = wait_for_database()

        self.assertTrue(result)

    def test_wait_for_database_timeout(self):
        """Test database waiting timeout with short timeout"""
        # Don't create database file

        with patch("container_main.config", self.mock_config):
            with patch("container_main.time.sleep"):  # Mock sleep to speed up test
                with patch("container_main.wait_for_database") as mock_wait:
                    mock_wait.return_value = False
                    result = wait_for_database()
                    self.assertFalse(result)

    @patch("container_main.logger")
    @patch("container_main.Process")
    @patch("container_main.wait_for_database", return_value=True)
    @patch("container_main.run_scheduler")
    @patch("container_main.run_api_server")
    @patch("container_main.signal_handler")
    def test_main_successful_orchestration(
        self,
        mock_signal_handler,
        mock_run_api,
        mock_run_scheduler,
        mock_wait_db,
        mock_process_class,
        mock_logger,
    ):
        """Test successful main orchestration"""
        # Mock processes
        mock_scheduler_process = Mock()
        mock_api_process = Mock()
        mock_api_process.is_alive.return_value = True
        mock_scheduler_process.is_alive.return_value = True

        mock_process_class.side_effect = [mock_scheduler_process, mock_api_process]

        with patch("container_main.shutdown_flag") as mock_shutdown_flag:
            mock_shutdown_flag.is_set.side_effect = [
                False,
                False,
                True,
            ]  # Exit after 2 checks

            main()

        # Verify processes were started
        self.assertEqual(mock_process_class.call_count, 2)
        mock_scheduler_process.start.assert_called_once()
        mock_api_process.start.assert_called_once()

        # Verify database wait was called
        mock_wait_db.assert_called_once()

        mock_logger.info.assert_called()

    @patch("container_main.logger")
    @patch("container_main.Process")
    @patch(
        "container_main.wait_for_database", return_value=False
    )  # Test timeout scenario
    @patch("container_main.run_scheduler")
    @patch("container_main.run_api_server")
    @patch("container_main.signal_handler")
    def test_main_database_timeout_orchestration(
        self,
        mock_signal_handler,
        mock_run_api,
        mock_run_scheduler,
        mock_wait_db,
        mock_process_class,
        mock_logger,
    ):
        """Test main orchestration when database times out"""
        # Mock processes
        mock_scheduler_process = Mock()
        mock_api_process = Mock()
        mock_api_process.is_alive.return_value = True
        mock_scheduler_process.is_alive.return_value = True

        mock_process_class.side_effect = [mock_scheduler_process, mock_api_process]

        with patch("container_main.shutdown_flag") as mock_shutdown_flag:
            mock_shutdown_flag.is_set.side_effect = [
                False,
                False,
                True,
            ]  # Exit after 2 checks

            main()

        # Verify processes were started even with database timeout
        self.assertEqual(mock_process_class.call_count, 2)
        mock_scheduler_process.start.assert_called_once()
        mock_api_process.start.assert_called_once()

        # Verify database wait was called
        mock_wait_db.assert_called_once()

        # Verify warning was logged about database timeout
        mock_logger.warning.assert_called()

    @patch("container_main.logger")
    @patch("container_main.Process")
    @patch("container_main.signal_handler")
    def test_main_process_failure_detection(
        self, mock_signal_handler, mock_process_class, mock_logger
    ):
        """Test main orchestration detects process failures"""
        # Mock processes
        mock_scheduler_process = Mock()
        mock_api_process = Mock()
        mock_api_process.is_alive.return_value = False  # API process died
        mock_api_process.name = "api_server"

        mock_process_class.side_effect = [mock_scheduler_process, mock_api_process]

        with patch("container_main.wait_for_database", return_value=True):
            with patch("container_main.shutdown_flag") as mock_shutdown_flag:
                mock_shutdown_flag.is_set.side_effect = [
                    False,
                    True,
                ]  # Exit after process check

                main()

        # Verify shutdown was triggered due to dead process
        mock_logger.error.assert_called_with("Process api_server died unexpectedly")

    @patch("container_main.logger")
    @patch("container_main.signal_handler")
    def test_main_exception_handling(self, mock_signal_handler, mock_logger):
        """Test main orchestration handles exceptions"""
        with patch("container_main.Process", side_effect=Exception("Test error")):
            main()

        # Verify exception was logged and shutdown was triggered
        mock_logger.error.assert_called()
        mock_signal_handler.assert_called()


if __name__ == "__main__":
    unittest.main()
