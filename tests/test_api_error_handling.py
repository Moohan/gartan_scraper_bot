#!/usr/bin/env python3
"""Enhanced tests for API server error handling and edge cases."""

import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

sys.path.insert(0, ".")
# flake8: noqa: E402
import api_server
from api_server import app


class TestAPIServerErrorHandling:
    """Test API server error conditions and edge cases."""

    def setup_method(self):
        """Set up test database and Flask test client for each test."""
        # Create temporary database
        fd, self.temp_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        api_server.DB_PATH = self.temp_path

        # Create test database schema
        conn = sqlite3.connect(self.temp_path)
        c = conn.cursor()

        # Create all required tables
        c.execute(
            "CREATE TABLE crew (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, role TEXT, contact TEXT, skills TEXT, contract_hours TEXT)"
        )
        c.execute(
            "CREATE TABLE crew_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, crew_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)"
        )
        c.execute(
            "CREATE TABLE appliance (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)"
        )
        c.execute(
            "CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, appliance_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)"
        )
        conn.commit()
        conn.close()

        # Set up Flask test client
        app.config["TESTING"] = True
        self.client = app.test_client()

    def teardown_method(self):
        """Clean up after each test."""
        try:
            os.unlink(self.temp_path)
        except (OSError, FileNotFoundError):
            pass

    @patch("api_server.sqlite3.connect")
    def test_is_crew_available_database_error(self, mock_connect):
        """Test is_crew_available with database connection error."""
        mock_connect.side_effect = sqlite3.Error("Database connection failed")

        response = self.client.get("/crew/999/available")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data
        assert data["error"] == "Internal server error"

    @patch("api_server.sqlite3.connect")
    def test_get_crew_duration_database_error(self, mock_connect):
        """Test get_crew_duration with database error."""
        mock_connect.side_effect = sqlite3.Error("Database error")

        response = self.client.get("/crew/999/duration")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data
        assert data["error"] == "Internal server error"

    def test_get_crew_duration_no_availability(self):
        """Test get_crew_duration when crew has no availability."""
        # Insert crew without availability
        conn = sqlite3.connect(self.temp_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO crew (id, name, role, skills, contact, contract_hours) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "TEST, A", "FFC", "BA", "", "56"),
        )
        conn.commit()
        conn.close()

        response = self.client.get("/crew/1/duration")
        assert response.status_code == 200

        data = json.loads(response.data)
        # API returns null for no availability
        assert data is None

    def test_get_crew_duration_edge_time_formats(self):
        """Test get_crew_duration with various time edge cases."""
        # Insert crew with availability ending tomorrow
        conn = sqlite3.connect(self.temp_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO crew (id, name, role, skills, contact, contract_hours) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "TEST, A", "FFC", "BA", "", "56"),
        )

        # Add availability ending tomorrow
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).replace(
            hour=14, minute=30, second=0, microsecond=0
        )
        c.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            (1, now, tomorrow),
        )
        conn.commit()
        conn.close()

        response = self.client.get("/crew/1/duration")
        assert response.status_code == 200

        data = json.loads(response.data)
        # API returns duration string like "22.45h"
        assert isinstance(data, str)
        assert data.endswith("h")

    def test_get_crew_duration_future_date(self):
        """Test get_crew_duration with availability ending in future date."""
        # Insert crew with availability ending in 3 days
        conn = sqlite3.connect(self.temp_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO crew (id, name, role, skills, contact, contract_hours) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "TEST, A", "FFC", "BA", "", "56"),
        )

        # Add availability ending in 3 days
        now = datetime.now()
        future = (now + timedelta(days=3)).replace(
            hour=14, minute=30, second=0, microsecond=0
        )
        c.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            (1, now, future),
        )
        conn.commit()
        conn.close()

        response = self.client.get("/crew/1/duration")
        assert response.status_code == 200

        data = json.loads(response.data)
        # API returns duration string like "70.45h"
        assert isinstance(data, str)
        assert data.endswith("h")

    @patch("api_server.sqlite3.connect")
    def test_is_appliance_available_database_error(self, mock_connect):
        """Test is_appliance_available with database error."""
        mock_connect.side_effect = sqlite3.Error("Database error")

        response = self.client.get("/appliances/P22P6/available")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data
        assert data["error"] == "Internal server error"

    @patch("api_server.sqlite3.connect")
    def test_get_appliance_duration_database_error(self, mock_connect):
        """Test get_appliance_duration with database error."""
        mock_connect.side_effect = sqlite3.Error("Database error")

        response = self.client.get("/appliances/P22P6/duration")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data
        assert data["error"] == "Internal server error"

    def test_get_appliance_duration_no_availability(self):
        """Test get_appliance_duration when appliance has no availability."""
        # Insert appliance without availability
        conn = sqlite3.connect(self.temp_path)
        c = conn.cursor()
        c.execute("INSERT INTO appliance (id, name) VALUES (?, ?)", (1, "P22P6"))
        conn.commit()
        conn.close()

        response = self.client.get("/appliances/P22P6/duration")
        assert response.status_code == 200

        data = json.loads(response.data)
        # API returns null for no availability
        assert data is None

    def test_format_duration_minutes_edge_cases(self):
        """Test _format_duration_minutes_to_hours_string edge cases."""
        # Import the function directly
        from api_server import _format_duration_minutes_to_hours_string

        # Test None input
        assert _format_duration_minutes_to_hours_string(None) is None

        # Test zero and negative
        assert _format_duration_minutes_to_hours_string(0) is None
        assert _format_duration_minutes_to_hours_string(-10) is None

        # Test fractional hours
        assert _format_duration_minutes_to_hours_string(90) == "1.5h"
        assert _format_duration_minutes_to_hours_string(30) == "0.5h"
        assert _format_duration_minutes_to_hours_string(75) == "1.25h"

        # Test whole hours (no decimal)
        assert _format_duration_minutes_to_hours_string(60) == "1h"
        assert _format_duration_minutes_to_hours_string(120) == "2h"

    @patch("api_server.sqlite3.connect")
    def test_get_crew_database_error(self, mock_connect):
        """Test get_crew with database error."""
        mock_connect.side_effect = sqlite3.Error("Database error")

        response = self.client.get("/crew")
        # The crew endpoint returns 200 even with database errors, just empty list
        assert response.status_code == 200

        data = json.loads(response.data)
        # When there's a database error, returns empty list
        assert isinstance(data, list)
        assert len(data) == 0

    def test_nonexistent_crew_endpoints(self):
        """Test endpoints with non-existent crew IDs."""
        # Test available endpoint - returns 404 for non-existent crew
        response = self.client.get("/crew/999/available")
        assert response.status_code == 404

        # Test duration endpoint - returns 404 for non-existent crew
        response = self.client.get("/crew/999/duration")
        assert response.status_code == 404

    def test_nonexistent_appliance_endpoints(self):
        """Test endpoints with non-existent appliance IDs."""
        # Test available endpoint - returns 404 for non-existent appliance
        response = self.client.get("/appliances/NONEXISTENT/available")
        assert response.status_code == 404

        # Test duration endpoint - returns 404 for non-existent appliance
        response = self.client.get("/appliances/NONEXISTENT/duration")
        assert response.status_code == 404

    def test_health_endpoint_database_check(self):
        """Test health endpoint database connectivity check."""
        response = self.client.get("/health")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "database" in data
        assert data["database"] == "connected"

    @patch("api_server.sqlite3.connect")
    def test_health_endpoint_database_error(self, mock_connect):
        """Test health endpoint with database connection error."""
        mock_connect.side_effect = sqlite3.Error("Connection failed")

        response = self.client.get("/health")
        assert response.status_code == 503  # Service unavailable

        data = json.loads(response.data)
        assert data["status"] == "degraded"  # API returns "degraded" not "unhealthy"
        assert "database" in data
        # Database status should indicate error
        assert data["database"] != "connected"


class TestAPIServerWeeklyEndpoints:
    """Test weekly API endpoints error handling."""

    def setup_method(self):
        """Set up test environment."""
        fd, self.temp_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        api_server.DB_PATH = self.temp_path

        # Create minimal schema
        conn = sqlite3.connect(self.temp_path)
        c = conn.cursor()
        c.execute(
            "CREATE TABLE crew (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, role TEXT, contact TEXT, skills TEXT, contract_hours TEXT)"
        )
        c.execute(
            "CREATE TABLE crew_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, crew_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)"
        )
        c.execute(
            "CREATE TABLE appliance (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)"
        )
        c.execute(
            "CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, appliance_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)"
        )
        conn.commit()
        conn.close()

        app.config["TESTING"] = True
        self.client = app.test_client()

    def teardown_method(self):
        """Clean up after each test."""
        try:
            os.unlink(self.temp_path)
        except (OSError, FileNotFoundError):
            pass

    @patch("api_server.sqlite3.connect")
    def test_weekly_crew_hours_database_error(self, mock_connect):
        """Test weekly crew hours with database error."""
        mock_connect.side_effect = sqlite3.Error("Database error")

        response = self.client.get("/crew/1/hours-this-week")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data

    @patch("api_server.sqlite3.connect")
    def test_weekly_appliance_hours_database_error(self, mock_connect):
        """Test weekly appliance hours with database error."""
        mock_connect.side_effect = sqlite3.Error("Database error")

        response = self.client.get("/appliances/P22P6/hours-this-week")
        assert response.status_code == 404  # No such route exists

        # Note: This endpoint doesn't exist in the API

    def test_weekly_hours_nonexistent_ids(self):
        """Test weekly hours endpoints with non-existent IDs."""
        # Test crew - returns 404 for non-existent crew
        response = self.client.get("/crew/999/hours-this-week")
        assert response.status_code == 404

        # Test appliance - returns 404 for non-existent appliance
        response = self.client.get("/appliances/NONEXISTENT/hours-this-week")
        assert response.status_code == 404
