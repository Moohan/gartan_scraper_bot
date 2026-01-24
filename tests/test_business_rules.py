#!/usr/bin/env python3
"""Tests for P22P6 business rules and API validation scenarios."""

import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, ".")
# flake8: noqa: E402
import api_server
from api_server import get_appliance_available_data, get_dashboard_data


def setup_temp_db():
    """Set up a temporary database for testing."""
    fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    api_server.DB_PATH = temp_path
    conn = sqlite3.connect(temp_path)
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
    return temp_path, conn


def teardown_temp_db(temp_path):
    """Clean up temporary database."""
    try:
        os.unlink(temp_path)
    except (OSError, FileNotFoundError):
        pass


class TestP22P6BusinessRules:
    """Test P22P6 appliance business rules scenarios."""

    def setup_method(self):
        """Set up test database for each test."""
        self.temp_path, self.conn = setup_temp_db()

    def teardown_method(self):
        """Clean up after each test."""
        self.conn.close()
        teardown_temp_db(self.temp_path)

    def _insert_crew_member(self, name, role, skills, available=True):
        """Helper to insert crew member with availability."""
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
            (name, role, skills, "56"),
        )
        crew_id = c.lastrowid

        if available:
            # Make them available for next 24 hours
            now = datetime.now()
            future = now + timedelta(hours=24)
            c.execute(
                "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                (crew_id, now, future),
            )

        self.conn.commit()
        return crew_id

    def _insert_appliance(self, name, available=True):
        """Helper to insert appliance with availability."""
        c = self.conn.cursor()
        c.execute("INSERT INTO appliance (name) VALUES (?)", (name,))
        appliance_id = c.lastrowid

        if available:
            # Make it available for next 24 hours
            now = datetime.now()
            future = now + timedelta(hours=24)
            c.execute(
                "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
                (appliance_id, now, future),
            )

        self.conn.commit()
        return appliance_id

    def test_p22p6_all_rules_pass(self):
        """Test P22P6 available when all business rules are satisfied."""
        # Insert crew that satisfies all rules:
        # - 4+ crew (minimum crew)
        # - 1 TTR (officer)
        # - 1+ LGV (driver)
        # - 2+ BA excluding TTR (breathing apparatus crew)
        # - 1+ FFC with BA (senior BA crew)
        self._insert_crew_member("OFFICER, A", "WC", "TTR BA")  # Officer with BA
        self._insert_crew_member(
            "DRIVER, B", "FFC", "LGV BA"
        )  # Driver with BA (FFC rank)
        self._insert_crew_member("CREW, C", "FFD", "BA")  # BA crew
        self._insert_crew_member("CREW, D", "FFT", "BA")  # BA crew

        # Insert P22P6 appliance
        self._insert_appliance("P22P6")

        # Check appliance is available
        result = get_appliance_available_data("P22P6")
        assert (
            result["available"] is True
        ), "P22P6 should be available when all business rules pass"

    def test_p22p6_insufficient_crew(self):
        """Test P22P6 unavailable with less than 4 crew members."""
        # Only 3 crew members (below minimum of 4)
        self._insert_crew_member("OFFICER, A", "WC", "TTR BA")
        self._insert_crew_member("DRIVER, B", "FFC", "LGV BA")
        self._insert_crew_member("CREW, C", "FFD", "BA")

        # Insert P22P6 appliance
        self._insert_appliance("P22P6")

        # Check appliance is unavailable
        result = get_appliance_available_data("P22P6")
        assert (
            result["available"] is False
        ), "P22P6 should be unavailable with less than 4 crew"

    def test_p22p6_no_ttr_officer(self):
        """Test P22P6 unavailable without TTR-qualified officer."""
        # 4 crew but no TTR skill
        self._insert_crew_member("CREW, A", "WC", "BA")  # No TTR
        self._insert_crew_member("DRIVER, B", "FFC", "LGV BA")
        self._insert_crew_member("CREW, C", "FFD", "BA")
        self._insert_crew_member("CREW, D", "FFT", "BA")

        # Insert P22P6 appliance
        self._insert_appliance("P22P6")

        # Check appliance is unavailable
        result = get_appliance_available_data("P22P6")
        assert (
            result["available"] is False
        ), "P22P6 should be unavailable without TTR officer"

    def test_p22p6_no_lgv_driver(self):
        """Test P22P6 unavailable without LGV-qualified driver."""
        # 4 crew but no LGV skill
        self._insert_crew_member("OFFICER, A", "WC", "TTR BA")
        self._insert_crew_member("CREW, B", "FFC", "BA")  # No LGV
        self._insert_crew_member("CREW, C", "FFD", "BA")
        self._insert_crew_member("CREW, D", "FFT", "BA")

        # Insert P22P6 appliance
        self._insert_appliance("P22P6")

        # Check appliance is unavailable
        result = get_appliance_available_data("P22P6")
        assert (
            result["available"] is False
        ), "P22P6 should be unavailable without LGV driver"

    def test_p22p6_insufficient_ba_crew(self):
        """Test P22P6 unavailable with less than 2 BA crew (excluding TTR)."""
        # TTR officer has BA but only 1 additional BA crew member
        self._insert_crew_member(
            "OFFICER, A", "WC", "TTR BA"
        )  # BA but has TTR (excluded)
        self._insert_crew_member("DRIVER, B", "FFC", "LGV BA")  # 1 BA without TTR
        self._insert_crew_member("CREW, C", "FFD", "")  # No BA
        self._insert_crew_member("CREW, D", "FFT", "")  # No BA

        # Insert P22P6 appliance
        self._insert_appliance("P22P6")

        # Check appliance is unavailable
        result = get_appliance_available_data("P22P6")
        assert (
            result["available"] is False
        ), "P22P6 should be unavailable with insufficient BA crew"

    def test_p22p6_no_senior_ba_crew(self):
        """Test P22P6 unavailable without FFC+ ranked crew with BA."""
        # All crew are FFT/FFD rank (no FFC or higher with BA)
        self._insert_crew_member("OFFICER, A", "FFT", "TTR")  # TTR but low rank, no BA
        self._insert_crew_member("DRIVER, B", "FFT", "LGV")  # LGV but low rank, no BA
        self._insert_crew_member("CREW, C", "FFT", "BA")  # BA but low rank
        self._insert_crew_member("CREW, D", "FFD", "BA")  # BA but low rank

        # Insert P22P6 appliance
        self._insert_appliance("P22P6")

        # Check appliance is unavailable
        result = get_appliance_available_data("P22P6")
        assert (
            result["available"] is False
        ), "P22P6 should be unavailable without senior BA crew"

    def test_p22p6_minimal_valid_configuration(self):
        """Test P22P6 available with exactly minimum required crew configuration."""
        # Exactly 4 crew with minimal qualifications to pass all rules
        self._insert_crew_member("OFFICER, A", "FFC", "TTR")  # TTR officer (FFC rank)
        self._insert_crew_member(
            "DRIVER, B", "FFC", "LGV BA"
        )  # LGV driver with BA (FFC = senior)
        self._insert_crew_member("CREW, C", "FFT", "BA")  # BA crew member 1
        self._insert_crew_member("CREW, D", "FFT", "BA")  # BA crew member 2

        # Insert P22P6 appliance
        self._insert_appliance("P22P6")

        # Check appliance is available
        result = get_appliance_available_data("P22P6")
        assert (
            result["available"] is True
        ), "P22P6 should be available with minimal valid configuration"

    def test_p22p6_appliance_physically_unavailable(self):
        """Test P22P6 unavailable when appliance itself is not available."""
        # Perfect crew configuration
        self._insert_crew_member("OFFICER, A", "WC", "TTR BA")
        self._insert_crew_member("DRIVER, B", "FFC", "LGV BA")
        self._insert_crew_member("CREW, C", "FFD", "BA")
        self._insert_crew_member("CREW, D", "FFT", "BA")

        # Insert P22P6 appliance but mark as unavailable
        self._insert_appliance("P22P6", available=False)

        # Check appliance is unavailable
        result = get_appliance_available_data("P22P6")
        assert (
            result["available"] is False
        ), "P22P6 should be unavailable when appliance itself is unavailable"


class TestAPIValidationScenarios:
    """Test API validation scenarios based on real operational data."""

    def setup_method(self):
        """Set up test database for each test."""
        self.temp_path, self.conn = setup_temp_db()

    def teardown_method(self):
        """Clean up after each test."""
        self.conn.close()
        teardown_temp_db(self.temp_path)

    def _insert_crew_member(
        self, name, role, skills, contact="", available=True, availability_hours=24
    ):
        """Helper to insert crew member with availability."""
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO crew (name, role, skills, contact, contract_hours) VALUES (?, ?, ?, ?, ?)",
            (name, role, skills, contact, "56"),
        )
        crew_id = c.lastrowid

        if available:
            now = datetime.now()
            future = now + timedelta(hours=availability_hours)
            c.execute(
                "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                (crew_id, now, future),
            )

        self.conn.commit()
        return crew_id

    def test_crew_list_with_display_names(self):
        """Test crew list API returns display names when available."""
        # Insert crew with contact information including display name
        self._insert_crew_member(
            "MCMAHON, JA",
            "FFC",
            "LGV BA",
            "James McMahon|07123456789|james@example.com|Firefighter",
        )

        crew_list = get_dashboard_data()
        assert len(crew_list) == 1

        crew = crew_list[0]
        assert crew["name"] == "MCMAHON, JA"
        assert crew["display_name"] == "James McMahon"
        assert crew["role"] == "FFC"
        assert crew["skills"] == "LGV BA"

    def test_crew_list_without_display_names(self):
        """Test crew list API handles missing display names gracefully."""
        # Insert crew without contact information
        self._insert_crew_member("SMITH, AB", "FFT", "BA")

        crew_list = get_dashboard_data()
        assert len(crew_list) == 1

        crew = crew_list[0]
        assert crew["name"] == "SMITH, AB"
        assert "display_name" in crew and crew.get("display_name") == crew["name"]

    def test_skill_counting_accuracy(self):
        """Test accurate skill counting for business rules."""
        # Create specific crew configuration for skill testing
        self._insert_crew_member(
            "OFFICER, A", "WC", "TTR BA", available=True
        )  # TTR: 1, BA: 1
        self._insert_crew_member(
            "DRIVER, B", "FFC", "LGV BA", available=True
        )  # LGV: 1, BA: 2
        self._insert_crew_member("CREW, C", "FFD", "BA", available=True)  # BA: 3
        self._insert_crew_member("TRAINEE, D", "FFT", "", available=True)  # No skills
        self._insert_crew_member(
            "OFF_DUTY, E", "FFC", "TTR LGV BA", available=False
        )  # Unavailable (shouldn't count)

        crew_list = get_dashboard_data()
        available_crew = [c for c in crew_list if c.get("available")]

        # Count skills
        skill_counts = {"TTR": 0, "LGV": 0, "BA": 0}
        for crew in available_crew:
            skills = crew["skills"].split() if crew["skills"] else []
            for skill in skills:
                if skill in skill_counts:
                    skill_counts[skill] += 1

        assert (
            skill_counts["TTR"] == 1
        ), "Should count exactly 1 TTR from available crew"
        assert (
            skill_counts["LGV"] == 1
        ), "Should count exactly 1 LGV from available crew"
        assert skill_counts["BA"] == 3, "Should count exactly 3 BA from available crew"

    def test_mixed_availability_scenarios(self):
        """Test mixed crew availability scenarios."""
        # Scenario from validation data: some available, some unavailable
        self._insert_crew_member("CASELY, CH", "FFC", "LGV BA", available=True)
        self._insert_crew_member("MCMAHON, JA", "FFC", "LGV BA", available=True)
        self._insert_crew_member("MUNRO, MA", "FFD", "BA", available=True)
        self._insert_crew_member(
            "COUTIE, JA", "FFT", "TTR", available=False
        )  # Off duty
        self._insert_crew_member(
            "GIBB, OL", "FFT", "LGV", available=False
        )  # Working elsewhere
        self._insert_crew_member(
            "MACDONALD, RO", "FFT", "BA", available=False
        )  # Working elsewhere
        self._insert_crew_member(
            "SABA, JA", "FFT", "LGV BA", available=False
        )  # Working elsewhere

        crew_list = get_dashboard_data()
        assert len(crew_list) == 7, "Should have all 7 crew members in list"

        # Verify available crew count matches expected scenario
        available_count = sum(1 for crew in crew_list if crew.get("available"))
        assert available_count == 3, "Should have exactly 3 available crew members"

    def test_reason_code_edge_cases(self):
        """Test that reason codes (O, W, F, T) are handled correctly."""
        # These scenarios test that unavailable crew are properly marked
        # Note: Reason codes are typically handled in parsing, but availability should be correct

        # Crew member who should be unavailable (equivalent to 'O' - Off duty)
        off_duty_id = self._insert_crew_member(
            "OFF_DUTY, A", "FFC", "TTR", available=False
        )

        # Crew member who should be unavailable (equivalent to 'W' - Working elsewhere)
        working_id = self._insert_crew_member(
            "WORKING, B", "FFC", "LGV", available=False
        )

        # Crew member who should be available (no reason code)
        available_id = self._insert_crew_member(
            "AVAILABLE, C", "FFC", "BA", available=True
        )

        # Test API responses
        from api_server import get_crew_available_data

        off_duty_result = get_crew_available_data(off_duty_id)
        working_result = get_crew_available_data(working_id)
        available_result = get_crew_available_data(available_id)

        assert (
            off_duty_result["available"] is False
        ), "Off duty crew should be unavailable"
        assert (
            working_result["available"] is False
        ), "Working elsewhere crew should be unavailable"
        assert (
            available_result["available"] is True
        ), "Available crew should be available"

    def test_duration_reasonableness(self):
        """Test that duration calculations are reasonable."""
        from api_server import get_crew_duration_data

        # Short availability (1 hour)
        short_id = self._insert_crew_member(
            "SHORT, A", "FFC", "BA", available=True, availability_hours=1
        )

        # Long availability (7 days = 168 hours, our filter limit)
        long_id = self._insert_crew_member(
            "LONG, B", "FFC", "BA", available=True, availability_hours=168
        )

        # Very long availability (should be filtered out by quality controls)
        very_long_id = self._insert_crew_member(
            "VERY_LONG, C", "FFC", "BA", available=True, availability_hours=200
        )

        short_result = get_crew_duration_data(short_id)
        long_result = get_crew_duration_data(long_id)
        very_long_result = get_crew_duration_data(very_long_id)

        # Short duration should be returned
        assert (
            short_result["duration"] is not None
        ), "Short duration should be calculated"
        assert (
            "1.0h" in short_result["duration"] or "0.9" in short_result["duration"]
        ), "Short duration should be ~1 hour"

        # Long but valid duration should be returned
        assert (
            long_result["duration"] is not None
        ), "Long valid duration should be calculated"

        # Very long duration should be filtered out by quality controls
        # Note: This tests the 7-day filter in the API
        assert (
            very_long_result["duration"] is None
        ), "Very long duration should be filtered out"

    def test_time_boundary_edge_cases(self):
        """Test edge cases around time boundaries."""
        from api_server import get_crew_available_data

        # Crew available right now (started 1 minute ago, ends in 1 hour)
        now = datetime.now()
        recent_start = now - timedelta(minutes=1)
        near_future = now + timedelta(hours=1)

        c = self.conn.cursor()
        c.execute(
            "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
            ("EDGE_CASE, A", "FFC", "BA", "56"),
        )
        crew_id = c.lastrowid
        c.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            (crew_id, recent_start, near_future),
        )
        self.conn.commit()

        result = get_crew_available_data(crew_id)
        assert result["available"] is True, "Crew should be available right now"

        # Test crew who just became unavailable (ended 1 minute ago)
        c.execute(
            "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
            ("JUST_ENDED, B", "FFC", "BA", "56"),
        )
        ended_crew_id = c.lastrowid
        past_start = now - timedelta(hours=2)
        recent_end = now - timedelta(minutes=1)
        c.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            (ended_crew_id, past_start, recent_end),
        )
        self.conn.commit()

        ended_result = get_crew_available_data(ended_crew_id)
        assert (
            ended_result["available"] is False
        ), "Crew should be unavailable after end time"


class TestDataQualityValidation:
    """Test data quality and consistency checks."""

    def setup_method(self):
        """Set up test database for each test."""
        self.temp_path, self.conn = setup_temp_db()

    def teardown_method(self):
        """Clean up after each test."""
        self.conn.close()
        teardown_temp_db(self.temp_path)

    def test_crew_endpoint_existence(self):
        """Test that all crew members have working API endpoints."""
        from api_server import get_crew_available_data, get_crew_duration_data

        # Insert a few crew members
        c = self.conn.cursor()
        for i in range(3):
            c.execute(
                "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
                (f"CREW_{i}, A", "FFC", "BA", "56"),
            )
        self.conn.commit()

        crew_list = get_dashboard_data()

        # Test that all crew endpoints respond without errors
        for crew in crew_list:
            crew_id = crew["id"]

            # Test availability endpoint
            avail_result = get_crew_available_data(crew_id)
            assert (
                "error" not in avail_result
            ), f"Crew {crew_id} availability endpoint should not error"
            assert (
                "available" in avail_result
            ), f"Crew {crew_id} should have availability status"
            assert isinstance(
                avail_result["available"], bool
            ), f"Crew {crew_id} availability should be boolean"

            # Test duration endpoint
            duration_result = get_crew_duration_data(crew_id)
            assert (
                "error" not in duration_result
            ), f"Crew {crew_id} duration endpoint should not error"
            assert (
                "duration" in duration_result
            ), f"Crew {crew_id} should have duration field"

    def test_nonexistent_crew_handling(self):
        """Test handling of requests for non-existent crew members."""
        from api_server import get_crew_available_data, get_crew_duration_data

        # Test with a crew ID that doesn't exist
        nonexistent_id = 99999

        avail_result = get_crew_available_data(nonexistent_id)
        assert "error" in avail_result, "Non-existent crew should return error"
        assert (
            "not found" in avail_result["error"].lower()
        ), "Error should mention not found"

        duration_result = get_crew_duration_data(nonexistent_id)
        assert (
            "error" in duration_result
        ), "Non-existent crew duration should return error"
        assert (
            "not found" in duration_result["error"].lower()
        ), "Error should mention not found"

    def test_appliance_endpoint_consistency(self):
        """Test that appliance endpoints are consistent."""
        from api_server import get_appliance_available_data, get_appliance_duration_data

        # Test P22P6 appliance
        c = self.conn.cursor()
        c.execute("INSERT INTO appliance (name) VALUES (?)", ("P22P6",))
        self.conn.commit()

        # Test both endpoints
        avail_result = get_appliance_available_data("P22P6")
        duration_result = get_appliance_duration_data("P22P6")

        assert "error" not in avail_result, "P22P6 availability should not error"
        assert "available" in avail_result, "P22P6 should have availability status"
        assert isinstance(
            avail_result["available"], bool
        ), "P22P6 availability should be boolean"

        assert "error" not in duration_result, "P22P6 duration should not error"
        assert "duration" in duration_result, "P22P6 should have duration field"

    def test_data_freshness_filters(self):
        """Test that old/stale data is properly filtered out."""
        from api_server import get_crew_available_data

        # Insert crew with very old availability data (should be filtered out)
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
            ("OLD_DATA, A", "FFC", "BA", "56"),
        )
        crew_id = c.lastrowid

        # Availability from 10 days ago (should be filtered by 7-day recency filter)
        old_start = datetime.now() - timedelta(days=10)
        old_end = old_start + timedelta(hours=8)
        c.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            (crew_id, old_start, old_end),
        )
        self.conn.commit()

        result = get_crew_available_data(crew_id)
        assert (
            result["available"] is False
        ), "Old data should be filtered out, showing as unavailable"


if __name__ == "__main__":
    pytest.main([__file__])
