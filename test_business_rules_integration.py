#!/usr/bin/env python3
"""Quick verification script to test business rules in API endpoints."""

import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, ".")
# flake8: noqa: E402
import api_server
from api_server import get_appliance_available_data, get_appliance_duration_data


def setup_test_scenario():
    """Set up a test scenario with insufficient crew."""
    # Create temporary database
    fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    api_server.DB_PATH = temp_path

    conn = sqlite3.connect(temp_path)
    c = conn.cursor()

    # Create tables
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

    # Insert crew with insufficient qualifications (missing TTR)
    c.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)", ("CREW, A", "FFC", "LGV BA", "56"))
    c.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)", ("CREW, B", "FFD", "BA", "56"))
    c.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)", ("CREW, C", "FFT", "BA", "56"))
    c.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)", ("CREW, D", "FFT", "BA", "56"))

    # Make all crew available
    now = datetime.now()
    future = now + timedelta(hours=8)
    for crew_id in range(1, 5):
        c.execute("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)", (crew_id, now, future))

    # Insert P22P6 appliance and make it physically available
    c.execute("INSERT INTO appliance (name) VALUES (?)", ("P22P6",))
    c.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)", (1, now, future))

    conn.commit()
    return temp_path, conn


def test_business_rules_enforcement():
    """Test that business rules are enforced in API endpoints."""
    print("Setting up test scenario with insufficient crew qualifications...")
    temp_path, conn = setup_test_scenario()

    try:
        print("\n=== Testing P22P6 Availability API ===")
        result = get_appliance_available_data("P22P6")
        print(f"P22P6 availability result: {result}")

        # Should be False because no TTR-qualified crew
        expected = False
        actual = result.get("available", None)
        assert actual == expected, f"Expected {expected}, got {actual}"
        print("✅ P22P6 correctly shows as unavailable due to missing TTR officer")

        print("\n=== Testing P22P6 Duration API ===")
        duration_result = get_appliance_duration_data("P22P6")
        print(f"P22P6 duration result: {duration_result}")

        # Should be None because business rules don't pass
        expected_duration = None
        actual_duration = duration_result.get("duration", "undefined")
        assert actual_duration == expected_duration, f"Expected {expected_duration}, got {actual_duration}"
        print("✅ P22P6 correctly shows no duration due to business rules")

        print("\n=== Adding TTR Officer ===")
        # Add a TTR officer
        c = conn.cursor()
        c.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)", ("OFFICER, E", "WC", "TTR", "56"))
        now = datetime.now()
        future = now + timedelta(hours=8)
        c.execute("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)", (5, now, future))
        conn.commit()

        # Test again
        result_with_ttr = get_appliance_available_data("P22P6")
        print(f"P22P6 availability with TTR: {result_with_ttr}")

        # Should now be True because all rules pass
        expected_with_ttr = True
        actual_with_ttr = result_with_ttr.get("available", None)
        assert actual_with_ttr == expected_with_ttr, f"Expected {expected_with_ttr}, got {actual_with_ttr}"
        print("✅ P22P6 correctly shows as available when all business rules pass")

        print("\n🎉 All business rule enforcement tests passed!")

    finally:
        conn.close()
        try:
            os.unlink(temp_path)
        except (OSError, FileNotFoundError):
            pass


if __name__ == "__main__":
    test_business_rules_enforcement()
