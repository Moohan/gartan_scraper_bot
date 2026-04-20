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

        c.execute(
            "CREATE TABLE crew (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, role TEXT, skills TEXT, contract_hours TEXT)"
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
        c.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, must_change_password INTEGER DEFAULT 1)"
        )
        conn.commit()
        conn.close()

        # Set up Flask test client
        app.config["TESTING"] = True
        self.client = app.test_client()

    def _login(self):
        """Helper to authenticate the client and change default password."""
        from werkzeug.security import generate_password_hash

        conn = sqlite3.connect(self.temp_path)
        c = conn.cursor()
        # Clean start for users
        c.execute("DELETE FROM users")
        hashed = generate_password_hash("Admin123!")
        c.execute(
            "INSERT INTO users (username, password_hash, must_change_password) VALUES (?, ?, 1)",
            ("admin", hashed),
        )
        conn.commit()
        conn.close()

        # 1. Login with default credentials
        self.client.post("/login", data={"username": "admin", "password": "Admin123!"})
        # 2. Change password as required
        self.client.post(
            "/change-password",
            data={"new_password": "NewAdmin123!", "confirm_password": "NewAdmin123!"},
        )

    def teardown_method(self):
        """Clean up after each test."""
        try:
            os.unlink(self.temp_path)
        except (OSError, FileNotFoundError):
            pass

    def _insert_crew_member(
        self, crew_id, name, role="FFC", skills="BA", available=True
    ):
        """Helper to insert crew member with availability."""
        conn = sqlite3.connect(self.temp_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO crew (id, name, role, skills, contract_hours) VALUES (?, ?, ?, ?, ?)",
            (crew_id, name, role, skills, "56"),
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
        """Test the /health endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert "database" in data

    def test_root_dashboard_endpoint(self):
        self._login()
        """Test the / endpoint (dashboard)."""
        # Insert some test data first
        self._insert_crew_member(1, "John Smith", role="WC", skills="TTR, LGV, BA")
        self._insert_crew_member(2, "Jane Doe", role="FFC", skills="BA")
        self._insert_appliance(1, "P22P6")

        response = self.client.get("/")
        assert response.status_code == 200
        # Check for key dashboard elements
        html = response.get_data(as_text=True)
        assert "Managing Station: P22" in html
        assert "John Smith" in html
        assert "Jane Doe" in html
        assert "P22P6 Status" in html
        assert "Retrieve More Data" in html

    def test_crew_list_endpoint(self):
        self._login()
        """Test the /crew endpoint."""
        self._insert_crew_member(1, "John Smith")
        response = self.client.get("/crew")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) >= 1
        assert any(c["name"] == "John Smith" for c in data)

    def test_crew_available_endpoint(self):
        self._login()
        """Test the /crew/<id>/available endpoint."""
        self._insert_crew_member(1, "John Smith", available=True)
        self._insert_crew_member(2, "Jane Doe", available=False)

        # Test available member
        response = self.client.get("/crew/1/available")
        assert response.status_code == 200
        assert response.get_json() is True

        # Test unavailable member
        response = self.client.get("/crew/2/available")
        assert response.status_code == 200
        assert response.get_json() is False

    def test_crew_duration_endpoint(self):
        self._login()
        """Test the /crew/<id>/duration endpoint."""
        self._insert_crew_member(1, "John Smith")
        response = self.client.get("/crew/1/duration")
        assert response.status_code == 200
        data = response.get_json()
        assert "h" in data  # e.g. "8.00h"

    def test_crew_hours_this_week_endpoint(self):
        self._login()
        """Test the /crew/<id>/hours-this-week endpoint."""
        self._insert_crew_member(1, "John Smith")
        response = self.client.get("/crew/1/hours-this-week")
        assert response.status_code == 200
        data = response.get_json()
        assert "hours_achieved" in data

    def test_crew_hours_planned_week_endpoint(self):
        self._login()
        """Test the /crew/<id>/hours-planned-week endpoint."""
        self._insert_crew_member(1, "John Smith")
        response = self.client.get("/crew/1/hours-planned-week")
        assert response.status_code == 200
        data = response.get_json()
        assert "hours_planned_week" in data

    def test_crew_contract_hours_endpoint(self):
        self._login()
        """Test the /crew/<id>/contract-hours endpoint."""
        self._insert_crew_member(1, "John Smith")
        response = self.client.get("/crew/1/contract-hours")
        assert response.status_code == 200
        assert response.get_json()["contract_hours"] == "56"

    def test_crew_hours_achieved_endpoint(self):
        self._login()
        """Test the /crew/<id>/hours-achieved endpoint."""
        self._insert_crew_member(1, "John Smith")
        response = self.client.get("/crew/1/hours-achieved")
        assert response.status_code == 200
        assert "hours_achieved" in response.get_json()

    def test_crew_hours_remaining_endpoint(self):
        self._login()
        """Test the /crew/<id>/hours-remaining endpoint."""
        self._insert_crew_member(1, "John Smith")
        response = self.client.get("/crew/1/hours-remaining")
        assert response.status_code == 200
        assert "hours_remaining" in response.get_json()

    def test_week_boundaries_logic(self):
        """Test get_week_boundaries internal helper."""
        monday, sunday = api_server.get_week_boundaries()
        assert monday.weekday() == 0  # Monday
        assert sunday.weekday() == 6  # Sunday
        assert (sunday - monday).days == 6

    def test_hours_precision_logic(self):
        """Test format_hours precision."""
        assert api_server.format_hours(60) == "1.00h"
        assert api_server.format_hours(90) == "1.50h"
        assert api_server.format_hours(45) == "0.75h"

    def test_appliance_available_endpoint(self):
        self._login()
        """Test /appliances/<name>/available endpoint."""
        self._insert_appliance(1, "P22P6", available=True)
        response = self.client.get("/appliances/P22P6/available")
        assert response.status_code == 200
        # This endpoint returns a boolean directly
        assert response.get_json() is False  # False because no crew yet

    def test_appliance_duration_endpoint(self):
        self._login()
        """Test /appliances/<name>/duration endpoint."""
        self._insert_appliance(1, "P22P6")
        response = self.client.get("/appliances/P22P6/duration")
        assert response.status_code == 200
        # This returns None/null if rules don't pass
        assert response.get_json() is None

    def test_p22p6_business_rules_integration(self):
        self._login()
        """Test if P22P6 status respects crew rules."""
        # Insert ONLY appliance, no crew (should fail rules)
        self._insert_appliance(1, "P22P6")
        response = self.client.get("/appliances/P22P6/available")
        assert response.get_json() is False

        # Insert 4 crew members with correct skills (should pass rules)
        self._insert_crew_member(1, "Officer", role="WC", skills="TTR BA")
        self._insert_crew_member(2, "Driver", role="FFD", skills="LGV BA")
        self._insert_crew_member(3, "FF1", role="FFD", skills="BA")
        self._insert_crew_member(4, "FF2", role="FFD", skills="BA")

        response = self.client.get("/appliances/P22P6/available")
        assert response.get_json() is True

    def test_http_methods_not_allowed(self):
        self._login()
        """Test that disallowed HTTP methods return 405."""
        response = self.client.post("/crew")
        assert response.status_code == 405

        response = self.client.put("/health")
        assert response.status_code == 405

    def test_content_type_headers(self):
        self._login()
        """Test that JSON endpoints return correct Content-Type."""
        response = self.client.get("/crew")
        assert response.headers["Content-Type"] == "application/json"

        response = self.client.get("/health")
        assert response.headers["Content-Type"] == "application/json"

    def test_error_handling_robustness(self):
        self._login()
        """Test behavior for non-existent IDs."""
        response = self.client.get("/crew/999/available")
        assert response.status_code == 404

    def test_empty_database_handling(self):
        self._login()
        """Test behavior with an initialized but empty database."""
        # Database was initialized in setup_method but remains empty here
        response = self.client.get("/crew")
        assert response.status_code == 200
        assert response.get_json() == []

        response = self.client.get("/crew/1/available")
        assert response.status_code == 404

        # Health should still work
        response = self.client.get("/health")
        assert response.status_code == 200

    def test_database_connection_error_handling(self):
        self._login()
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

    def test_retrieve_more_endpoint(self):
        self._login()
        """Test the /retrieve_more POST endpoint."""
        # First call should succeed
        resp = self.client.post("/retrieve_more")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "Fetch started" in data["message"]

        # Second call while in progress should fail
        resp2 = self.client.post("/retrieve_more")
        assert resp2.status_code == 400
        assert resp2.get_json()["message"] == "Fetch already in progress"

        # Reset state for other tests
        with api_server.fetch_lock:
            api_server.fetch_state = {"in_progress": False, "error": None}

    def test_fetch_status_endpoint(self):
        self._login()
        """Test the /fetch_status GET endpoint."""
        resp = self.client.get("/fetch_status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "in_progress" in data


if __name__ == "__main__":
    pytest.main([__file__])
