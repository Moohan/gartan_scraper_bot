#!/usr/bin/env python3
"""
Direct API function testing without web server

This tests the core API logic directly without Flask's web server
"""

import sqlite3
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Database configuration
DB_PATH = "gartan_availability.db"


def get_db_connection():
    """Get database connection with row factory for easier access"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_current_time():
    """Get current UTC time"""
    return datetime.now(timezone.utc)


def format_duration(hours: float) -> str:
    """Format duration in hours as string (e.g., '12.5h')"""
    return f"{hours:.1f}h" if hours != int(hours) else f"{int(hours)}h"


def get_crew_list_data():
    """Get list of all crew members with their IDs and names"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM crew ORDER BY name")
    crew = cursor.fetchall()
    conn.close()

    result = [{"id": row["id"], "name": row["name"]} for row in crew]
    return result


def get_crew_available_data(crew_id: int):
    """Check if crew member is available right now"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if crew exists
    cursor.execute("SELECT name FROM crew WHERE id = ?", (crew_id,))
    crew = cursor.fetchone()
    if not crew:
        conn.close()
        return {"error": f"Crew member with ID {crew_id} not found"}

    # Check current availability
    current_time = get_current_time()
    cursor.execute(
        """
        SELECT COUNT(*) as count 
        FROM crew_availability 
        WHERE crew_id = ? 
        AND start_time <= ? 
        AND end_time > ?
    """,
        (crew_id, current_time, current_time),
    )

    result = cursor.fetchone()
    conn.close()

    is_available = result["count"] > 0
    return {"crew_id": crew_id, "name": crew["name"], "available": is_available}


def get_crew_duration_data(crew_id: int):
    """How long is crew member available for (from now)?"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if crew exists
    cursor.execute("SELECT name FROM crew WHERE id = ?", (crew_id,))
    crew = cursor.fetchone()
    if not crew:
        conn.close()
        return {"error": f"Crew member with ID {crew_id} not found"}

    # Find current availability block
    current_time = get_current_time()
    cursor.execute(
        """
        SELECT end_time 
        FROM crew_availability 
        WHERE crew_id = ? 
        AND start_time <= ? 
        AND end_time > ?
        ORDER BY end_time DESC
        LIMIT 1
    """,
        (crew_id, current_time, current_time),
    )

    result = cursor.fetchone()
    conn.close()

    if not result:
        return {"crew_id": crew_id, "name": crew["name"], "duration": None}

    # Calculate duration in hours
    end_time_str = result["end_time"]
    # Database times are stored without timezone, assume UTC
    end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=timezone.utc)
    duration_seconds = (end_time - current_time).total_seconds()
    duration_hours = duration_seconds / 3600

    duration_str = format_duration(duration_hours)
    return {"crew_id": crew_id, "name": crew["name"], "duration": duration_str}


def get_appliance_available_data(appliance_name: str):
    """Check if appliance is available right now"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if appliance exists
    cursor.execute("SELECT id FROM appliance WHERE name = ?", (appliance_name,))
    appliance = cursor.fetchone()
    if not appliance:
        conn.close()
        return {"error": f"Appliance '{appliance_name}' not found"}

    # Check current availability
    current_time = get_current_time()
    cursor.execute(
        """
        SELECT COUNT(*) as count 
        FROM appliance_availability 
        WHERE appliance_id = ? 
        AND start_time <= ? 
        AND end_time > ?
    """,
        (appliance["id"], current_time, current_time),
    )

    result = cursor.fetchone()
    conn.close()

    is_available = result["count"] > 0
    return {"appliance_name": appliance_name, "available": is_available}


def get_appliance_duration_data(appliance_name: str):
    """Get appliance's current availability duration"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if appliance exists
    cursor.execute("SELECT id FROM appliance WHERE name = ?", (appliance_name,))
    appliance = cursor.fetchone()
    if not appliance:
        conn.close()
        return {"error": f"Appliance '{appliance_name}' not found"}

    # Find current availability block
    current_time = get_current_time()
    cursor.execute(
        """
        SELECT end_time 
        FROM appliance_availability 
        WHERE appliance_id = ? 
        AND start_time <= ? 
        AND end_time > ?
        ORDER BY start_time ASC
        LIMIT 1
    """,
        (appliance["id"], current_time, current_time),
    )

    block = cursor.fetchone()
    conn.close()

    if not block:
        return {"appliance_name": appliance_name, "duration": None}

    # Calculate duration from now until end of availability
    end_time = datetime.fromisoformat(block["end_time"].replace("Z", "+00:00"))
    duration_seconds = (end_time - current_time).total_seconds()
    duration_hours = duration_seconds / 3600

    if duration_hours <= 0:
        return {"appliance_name": appliance_name, "duration": None}

    duration_str = format_duration(duration_hours)
    return {"appliance_name": appliance_name, "duration": duration_str}


def run_tests():
    """Run all direct API tests"""
    print("🚀 Testing API Functions Directly")
    print(f"Current time: {get_current_time().isoformat()}")
    print("=" * 60)

    tests = [
        ("GET /crew", get_crew_list_data, []),
        ("GET /crew/1/available", get_crew_available_data, [1]),
        ("GET /crew/5/available", get_crew_available_data, [5]),
        ("GET /crew/999/available", get_crew_available_data, [999]),
        ("GET /crew/1/duration", get_crew_duration_data, [1]),
        ("GET /crew/5/duration", get_crew_duration_data, [5]),
        ("GET /appliances/P22P6/available", get_appliance_available_data, ["P22P6"]),
        (
            "GET /appliances/INVALID/available",
            get_appliance_available_data,
            ["INVALID"],
        ),
    ]

    for test_name, test_func, args in tests:
        print(f"\nTesting: {test_name}")
        print("-" * 40)
        try:
            result = test_func(*args) if args else test_func()
            print(f"✅ Success: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "=" * 60)
    print("✨ Direct function tests completed!")


if __name__ == "__main__":
    run_tests()
