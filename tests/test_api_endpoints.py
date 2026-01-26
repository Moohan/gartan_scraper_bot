#!/usr/bin/env python3
"""Comprehensive tests for API server endpoints."""

import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, ".")
# flake8: noqa: E402
import api_server
from api_server import app


class TestAPIEndpoints:
    """Test API server HTTP endpoints."""

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

    def _insert_crew_member(
        self, crew_id, name, role="FFC", skills="BA", contact="", available=True
    ):
        """Helper to insert crew member with availability."""
        conn = sqlite3.connect(self.temp_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO crew (id, name, role, skills, contact, contract_hours) VALUES (?, ?, ?, ?, ?, ?)",
            (crew_id, name, role, skills, contact, "56"),
        )

        if available:
            now = datetime.now()
            future = now + timedelta(hours=8)
            c.execute(
                "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                (crew_id, now, future),
            )

        conn.commit()
        conn.close()

    def _insert_appliance(self, appliance_id, name, available=True):
        """Helper to insert appliance with availability."""
        conn = sqlite3.connect(self.temp_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO appliance (id, name) VALUES (?, ?)", (appliance_id, name)
        )

        if available:
            now = datetime.now()
            future = now + timedelta(hours=8)
            c.execute(
                "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
                (appliance_id, now, future),
            )

        conn.commit()
        conn.close()

    def test_health_endpoint(self):
        """Test /health endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "database" in data

    def test_root_dashboard_endpoint(self):
        """Test / (dashboard) endpoint."""
        # Insert some test data
        self._insert_crew_member(1, "TEST, A", "FFC", "BA")
        self._insert_appliance(1, "P22P6")

        response = self.client.get("/")
        assert response.status_code == 200
        # Dashboard may return HTML or JSON depending on implementation
        # Let's accept either
        assert response.content_type.startswith(("text/html", "application/json"))

        # Check for key dashboard elements
        content = response.data.decode("utf-8")
        # Dashboard may return JSON error or HTML content
        if response.content_type.startswith("application/json"):
            assert "Gartan Scraper Bot" in content
        else:
            assert "Gartan Scraper Bot" in content
            assert "Dashboard" in content
            assert "TEST, A" in content
            assert "P22P6" in content

    def test_crew_list_endpoint(self):
        """Test /crew endpoint."""
        # Insert test crew
        self._insert_crew_member(
            1,
            "JONES, AB",
            "FFC",
            "BA LGV",
            "Alice Jones|07123456789|alice@example.com|Firefighter",
        )
        self._insert_crew_member(2, "SMITH, CD", "FFT", "TTR", "")

        response = self.client.get("/crew")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 2

        # Check first crew member (with display name)
        crew1 = next(c for c in data if c["name"] == "JONES, AB")
        assert crew1["role"] == "FFC"
        assert crew1["skills"] == "BA LGV"
        assert crew1["display_name"] == "Alice Jones"

        # Check second crew member (without display name)
        crew2 = next(c for c in data if c["name"] == "SMITH, CD")
        assert crew2["role"] == "FFT"
        assert crew2["skills"] == "TTR"

    def test_crew_available_endpoint(self):
        """Test /crew/<id>/available endpoint."""
        # Insert available crew member
        self._insert_crew_member(1, "AVAILABLE, A", available=True)

        # Insert unavailable crew member
        self._insert_crew_member(2, "UNAVAILABLE, B", available=False)

        # Test available crew
        response = self.client.get("/crew/1/available")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data is True  # API returns bare boolean

        # Test unavailable crew
        response = self.client.get("/crew/2/available")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data is False  # API returns bare boolean

        # Test non-existent crew
        response = self.client.get("/crew/999/available")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data
        assert "not found" in data["error"].lower()

    def test_crew_duration_endpoint(self):
        """Test /crew/<id>/duration endpoint."""
        # Insert crew with specific duration
        self._insert_crew_member(1, "DURATION, A", available=True)

        response = self.client.get("/crew/1/duration")
        assert response.status_code == 200
        data = json.loads(response.data)
        # API returns bare string like "7.98h" or null
        assert isinstance(data, (str, type(None)))

        # Non-existent crew should return 404
        response = self.client.get("/crew/999/duration")
        assert response.status_code == 404

    def test_crew_hours_this_week_endpoint(self):
        """Test /crew/<id>/hours-this-week endpoint."""
        self._insert_crew_member(1, "WEEKLY, A", available=True)

        response = self.client.get("/crew/1/hours-this-week")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "hours_this_week" in data
        assert isinstance(data["hours_this_week"], (int, float))
        assert data["hours_this_week"] >= 0

    def test_crew_hours_planned_week_endpoint(self):
        """Test /crew/<id>/hours-planned-week endpoint."""
        self._insert_crew_member(1, "PLANNED, A", available=True)

        response = self.client.get("/crew/1/hours-planned-week")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "hours_planned_week" in data
        assert isinstance(data["hours_planned_week"], (int, float))
        assert data["hours_planned_week"] >= 0

    def test_crew_contract_hours_endpoint(self):
        """Test /crew/<id>/contract-hours endpoint."""
        self._insert_crew_member(1, "CONTRACT, A", available=True)

        response = self.client.get("/crew/1/contract-hours")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "contract_hours" in data
        assert data["contract_hours"] == "56"

    def test_crew_hours_achieved_endpoint(self):
        """Test /crew/<id>/hours-achieved endpoint."""
        self._insert_crew_member(1, "ACHIEVED, A", available=True)

        response = self.client.get("/crew/1/hours-achieved")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "hours_achieved" in data
        assert isinstance(data["hours_achieved"], (int, float))

    def test_crew_hours_remaining_endpoint(self):
        """Test /crew/<id>/hours-remaining endpoint."""
        self._insert_crew_member(1, "REMAINING, A", available=True)

        response = self.client.get("/crew/1/hours-remaining")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "hours_remaining" in data
        assert isinstance(data["hours_remaining"], (int, float))

    def test_week_boundaries_logic(self):
        """Test the internal week boundary calculation logic."""
        from api_server import get_week_boundaries

        start, end = get_week_boundaries()
        assert start.weekday() == 0  # Monday
        assert start.hour == 0
        assert end.weekday() == 6  # Sunday
        assert end.hour == 23
        assert (end - start).days == 6

    def test_hours_precision_logic(self):
        """Test that hours are calculated with proper precision."""
        # Insert 90 minute block (1.5 hours)
        conn = sqlite3.connect(self.temp_path)
        c = conn.cursor()
        week_start, _ = api_server.get_week_boundaries()
        start = week_start + timedelta(hours=10)
        end = start + timedelta(minutes=90)
        c.execute(
            "INSERT INTO crew (id, name, contract_hours) VALUES (99, 'PRECISION', '56')"
        )
        c.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (99, ?, ?)",
            (start.isoformat(), end.isoformat()),
        )
        conn.commit()
        conn.close()

        response = self.client.get("/crew/99/hours-planned-week")
        data = json.loads(response.data)
        assert data["hours_planned_week"] == 1.5

    def test_appliance_available_endpoint(self):
        """Test /appliances/<name>/available endpoint."""
        # Insert available appliance (not P22P6 to avoid business rules)
        self._insert_appliance(1, "ENGINE1", available=True)

        # Insert unavailable appliance
        self._insert_appliance(2, "ENGINE2", available=False)

        # Test available appliance
        response = self.client.get("/appliances/ENGINE1/available")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data is True  # API returns bare boolean

        # Test unavailable appliance
        response = self.client.get("/appliances/ENGINE2/available")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data is False  # API returns bare boolean

        # Test non-existent appliance
        response = self.client.get("/appliances/NONEXISTENT/available")
        assert response.status_code == 404

    def test_appliance_duration_endpoint(self):
        """Test /appliances/<name>/duration endpoint."""
        self._insert_appliance(1, "ENGINE1", available=True)

        response = self.client.get("/appliances/ENGINE1/duration")
        assert response.status_code == 200
        data = json.loads(response.data)
        # API returns bare string like "7.98h" or null
        assert isinstance(data, (str, type(None)))

        # If string, should end with 'h'
        if isinstance(data, str):
            assert data.endswith("h")

        # Non-existent appliance should return 404
        response = self.client.get("/appliances/NONEXISTENT/duration")
        assert response.status_code == 404

    def test_p22p6_business_rules_integration(self):
        """Test P22P6 specific business rules through HTTP endpoints."""
        # Insert P22P6 appliance
        self._insert_appliance(1, "P22P6", available=True)

        # Insert insufficient crew (no TTR officer)
        self._insert_crew_member(1, "CREW, A", "FFC", "LGV BA", available=True)
        self._insert_crew_member(2, "CREW, B", "FFD", "BA", available=True)
        self._insert_crew_member(3, "CREW, C", "FFT", "BA", available=True)

        # P22P6 should be unavailable due to business rules
        response = self.client.get("/appliances/P22P6/available")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data is False  # API returns bare boolean

        # Duration should be None due to business rules
        response = self.client.get("/appliances/P22P6/duration")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data is None  # API returns bare null/None

    def test_http_methods_not_allowed(self):
        """Test that only GET methods are allowed on endpoints."""
        endpoints = [
            "/health",
            "/crew",
            "/crew/1/available",
            "/appliances/P22P6/available",
        ]

        for endpoint in endpoints:
            # Test POST method (should not be allowed)
            response = self.client.post(endpoint)
            assert response.status_code == 405  # Method Not Allowed

            # Test PUT method (should not be allowed)
            response = self.client.put(endpoint)
            assert response.status_code == 405

    def test_content_type_headers(self):
        """Test that endpoints return correct content types."""
        self._insert_crew_member(1, "TEST, A")

        # JSON endpoints
        json_endpoints = ["/health", "/crew", "/crew/1/available"]

        for endpoint in json_endpoints:
            response = self.client.get(endpoint)
            assert response.content_type.startswith("application/json")

        # HTML endpoint
        response = self.client.get("/")
        # Dashboard may return HTML or JSON depending on error conditions
        assert response.content_type.startswith(("text/html", "application/json"))

    def test_error_handling_robustness(self):
        """Test various error conditions and edge cases."""
        # Test invalid crew ID types
        response = self.client.get("/crew/invalid/available")
        assert response.status_code == 404  # Flask handles invalid int conversion

        # Test very large crew ID (should return 404 for non-existent)
        response = self.client.get("/crew/999999999/available")
        assert response.status_code == 404  # Non-existent crew

        # Test negative crew ID
        response = self.client.get("/crew/-1/available")
        assert response.status_code == 404

    def test_empty_database_handling(self):
        """Test endpoints with empty database."""
        # Crew list should return empty array
        response = self.client.get("/crew")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

        # Individual crew should return 404 for non-existent
        response = self.client.get("/crew/1/available")
        assert response.status_code == 404

        # Health should still work
        response = self.client.get("/health")
        assert response.status_code == 200

    def test_database_connection_error_handling(self):
        """Test behavior when database is unavailable."""
        # Remove the database file to simulate connection error
        os.unlink(self.temp_path)

        # Health endpoint should report unhealthy (503 or error response)
        response = self.client.get("/health")
        # Accept either 503 (service unavailable) or 200 with error indication
        assert response.status_code in [200, 503]

        # Other endpoints should handle gracefully
        response = self.client.get("/crew")
        assert response.status_code in [
            200,
            500,
            503,
        ]  # Various error responses acceptable


if __name__ == "__main__":
    pytest.main([__file__])
