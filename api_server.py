#!/usr/bin/env python3
"""Production Flask API server exposing availability endpoints.

Endpoints:
    /health                               — service + DB status
    /crew                                 — list crew ids/names
    /crew/<id>/available                  — boolean current availability
    /crew/<id>/duration                   — remaining duration string or null
    /crew/<id>/hours-this-week            — hours available since Monday
    /crew/<id>/hours-planned-week         — total planned hours this week
    /crew/<id>/contract-hours             — contract hours info (e.g., "61 (159)")
    /crew/<id>/hours-achieved             — hours worked so far this week
    /crew/<id>/hours-remaining            — hours remaining to fulfill contract
    /appliances/<name>/available          — appliance availability
    /appliances/<name>/duration           — appliance availability duration

Design notes:
    * Database reads are short-lived connections (no global pool needed yet).
    * Business logic is delegated to helper functions for testability.
    * Responses conform to simple spec: primitives or small JSON objects.
"""

import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, render_template_string

from config import config

# Configure sqlite3 datetime adapters for Python 3.12+ compatibility
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_converter("DATETIME", lambda b: datetime.fromisoformat(b.decode()))


def merge_time_periods(
    periods: List[Tuple[datetime, datetime]],
) -> List[Tuple[datetime, datetime]]:
    """Merge overlapping time periods to avoid double-counting hours."""
    if not periods:
        return []

    # Sort periods by start time
    sorted_periods = sorted(periods, key=lambda x: x[0])
    merged = [sorted_periods[0]]

    for current_start, current_end in sorted_periods[1:]:
        last_start, last_end = merged[-1]

        # If current period overlaps with the last merged period
        if current_start <= last_end:
            # Merge by extending the end time if necessary
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            # No overlap, add as new period
            merged.append((current_start, current_end))

    return merged


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Database path
DB_PATH = config.db_path


def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_crew_list_data() -> List[Dict[str, Any]]:
    """Get list of all crew members with display names and enhanced details."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, contact, role, skills, contract_hours FROM crew ORDER BY name"
            )
            rows = cursor.fetchall()

            crew_list = []
            for row in rows:
                crew_data = {
                    "id": row["id"],
                    "name": row["name"],
                    "role": row["role"],
                    "skills": row["skills"],
                    "contract_hours": row["contract_hours"],
                }

                # Extract display name from contact field if available
                if row["contact"]:
                    contact_parts = row["contact"].split("|")
                    if len(contact_parts) >= 1 and contact_parts[0]:
                        crew_data["display_name"] = contact_parts[0]

                crew_list.append(crew_data)

            return crew_list
    except Exception as e:
        logger.error(f"Error getting crew list: {e}")
        return []


def get_crew_available_data(crew_id: int) -> Dict[str, Any]:
    """Check if crew member is available right now."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if crew exists
            cursor.execute("SELECT name FROM crew WHERE id = ?", (crew_id,))
            crew = cursor.fetchone()
            if not crew:
                return {"error": f"Crew ID {crew_id} not found"}

            # Check current availability with data quality filters
            now = datetime.now()
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM crew_availability
                WHERE crew_id = ?
                AND datetime(start_time) <= datetime(?)
                AND datetime(end_time) > datetime(?)
                AND (julianday(end_time) - julianday(start_time)) <= 7.0
                AND date(start_time) >= date('now', '-7 days')
            """,
                (crew_id, now, now),
            )

            result = cursor.fetchone()
            count = result["count"]
            is_available = count > 0

            return {"available": is_available}
    except Exception as e:
        logger.error(f"Error checking crew availability: {e}")
        return {"error": "Internal server error"}


def _format_duration_minutes_to_hours_string(minutes: int | None) -> Optional[str]:
    """Convert duration in minutes to spec hours string (e.g. 59.25h) or None."""
    if minutes is None:
        return None
    if minutes <= 0:
        return None
    hours = minutes / 60.0
    # Keep up to 2 decimal places without trailing zeros
    formatted = f"{hours:.2f}".rstrip("0").rstrip(".")
    return f"{formatted}h"


def get_crew_duration_data(crew_id: int) -> Dict[str, Any]:
    """Get how long crew member is available for (string hours or null)."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if crew exists
            cursor.execute("SELECT name FROM crew WHERE id = ?", (crew_id,))
            crew = cursor.fetchone()
            if not crew:
                return {"error": f"Crew ID {crew_id} not found"}

            # Get next availability block with data quality filters
            now = datetime.now()
            cursor.execute(
                """
                SELECT start_time, end_time FROM crew_availability
                WHERE crew_id = ?
                AND datetime(start_time) <= datetime(?)
                AND datetime(end_time) > datetime(?)
                AND (julianday(end_time) - julianday(start_time)) <= 7.0
                AND date(start_time) >= date('now', '-7 days')
                ORDER BY start_time LIMIT 1
            """,
                (crew_id, now, now),
            )

            result = cursor.fetchone()
            if result:
                end_time = datetime.fromisoformat(result[1])
                duration_minutes = int((end_time - now).total_seconds() / 60)

                # Format end time for display
                end_time_str = end_time.strftime("%H:%M")
                if end_time.date() == now.date():
                    end_time_display = f"{end_time_str} today"
                elif end_time.date() == (now + timedelta(days=1)).date():
                    end_time_display = f"{end_time_str} tomorrow"
                else:
                    end_time_display = end_time.strftime("%H:%M on %d/%m")

                return {
                    "duration": _format_duration_minutes_to_hours_string(
                        max(0, duration_minutes)
                    ),
                    "end_time_display": end_time_display,
                }
            else:
                return {"duration": None, "end_time_display": None}
    except Exception as e:
        logger.error(f"Error getting crew duration: {e}")
        return {"error": "Internal server error"}


def get_week_boundaries() -> tuple[datetime, datetime]:
    """Get start (Monday 00:00) and end (Sunday 23:59:59) of current week."""
    now = datetime.now()

    # Get Monday of current week (weekday 0=Monday, 6=Sunday)
    days_since_monday = now.weekday()
    monday = now - timedelta(days=days_since_monday)
    week_start = monday.replace(hour=0, minute=0, second=0, microsecond=0)

    # Get Sunday of current week
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

    return week_start, week_end


def get_crew_hours_this_week_data(crew_id: int) -> Dict[str, Any]:
    """Get how many hours crew member has been available since Monday."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if crew exists
            cursor.execute("SELECT name FROM crew WHERE id = ?", (crew_id,))
            crew = cursor.fetchone()
            if not crew:
                return {"error": f"Crew ID {crew_id} not found"}

            week_start, _ = get_week_boundaries()
            now = datetime.now()

            # Get all availability blocks from Monday to now with relaxed filters for weekly calculations
            cursor.execute(
                """
                SELECT start_time, end_time FROM crew_availability
                WHERE crew_id = ? AND end_time > ? AND start_time < ?
                AND (julianday(end_time) - julianday(start_time)) <= 14.0
                AND date(start_time) >= date('now', '-30 days')
                ORDER BY start_time
            """,
                (crew_id, week_start, now),
            )

            blocks = cursor.fetchall()

            # Convert to datetime objects and clamp to boundaries
            time_periods = []
            for block in blocks:
                block_start = datetime.fromisoformat(block[0])
                block_end = datetime.fromisoformat(block[1])

                # Clamp block to week boundaries and current time
                effective_start = max(block_start, week_start)
                effective_end = min(block_end, now)

                # Only include if there's actual overlap
                if effective_end > effective_start:
                    time_periods.append((effective_start, effective_end))

            # Merge overlapping periods to avoid double-counting
            if not time_periods:
                return {"hours_this_week": 0.0}

            merged_periods = merge_time_periods(time_periods)

            # Calculate total hours from merged periods
            total_hours = 0.0
            for start, end in merged_periods:
                duration = end - start
                total_hours += duration.total_seconds() / 3600

            return {"hours_this_week": round(total_hours, 2)}
    except Exception as e:
        logger.error(f"Error getting crew weekly hours: {e}")
        return {"error": "Internal server error"}


def get_crew_hours_planned_week_data(crew_id: int) -> Dict[str, Any]:
    """Get total planned + actual availability hours for the current week."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if crew exists
            cursor.execute("SELECT name FROM crew WHERE id = ?", (crew_id,))
            crew = cursor.fetchone()
            if not crew:
                return {"error": f"Crew ID {crew_id} not found"}

            week_start, week_end = get_week_boundaries()

            # Get all availability blocks for the entire week with relaxed filters for weekly calculations
            cursor.execute(
                """
                SELECT start_time, end_time FROM crew_availability
                WHERE crew_id = ? AND end_time > ? AND start_time < ?
                AND (julianday(end_time) - julianday(start_time)) <= 14.0
                AND date(start_time) >= date('now', '-30 days')
                ORDER BY start_time
            """,
                (crew_id, week_start, week_end),
            )

            blocks = cursor.fetchall()

            # Convert to datetime objects and clamp to boundaries
            time_periods = []
            for block in blocks:
                block_start = datetime.fromisoformat(block[0])
                block_end = datetime.fromisoformat(block[1])

                # Clamp block to week boundaries
                effective_start = max(block_start, week_start)
                effective_end = min(block_end, week_end)

                # Only include if there's actual overlap
                if effective_end > effective_start:
                    time_periods.append((effective_start, effective_end))

            # Merge overlapping periods to avoid double-counting
            if not time_periods:
                return {"hours_planned_week": 0.0}

            merged_periods = merge_time_periods(time_periods)

            # Calculate total hours from merged periods
            total_hours = 0.0
            for start, end in merged_periods:
                duration = end - start
                total_hours += duration.total_seconds() / 3600

            return {"hours_planned_week": round(total_hours, 2)}
    except Exception as e:
        logger.error(f"Error getting crew planned weekly hours: {e}")
        return {"error": "Internal server error"}


def check_p22p6_business_rules() -> Dict[str, Any]:
    """Check P22P6 business rules against available crew."""
    try:
        # Get all crew data
        crew_data = get_crew_list_data()

        # Check availability for each crew member and build available crew list
        available_crew = []
        for crew in crew_data:
            crew_availability = get_crew_available_data(crew["id"])
            if crew_availability.get("available", False):
                available_crew.append(crew)

        # Count skills for available crew
        skill_counts = {"TTR": 0, "LGV": 0, "BA": 0}
        for crew in available_crew:
            skills = (
                crew["skills"].split()
                if crew["skills"] and crew["skills"] != "None"
                else []
            )
            for skill in skills:
                if skill in skill_counts:
                    skill_counts[skill] += 1

        # Business rules calculations
        total_available = len(available_crew)
        ttr_present = skill_counts["TTR"] > 0
        lgv_present = skill_counts["LGV"] > 0
        ba_non_ttr = sum(
            1
            for c in available_crew
            if "BA" in (c["skills"] or "") and "TTR" not in (c["skills"] or "")
        )
        ffc_with_ba = any(
            c["role"] in ["FFC", "CC", "WC", "CM"] and "BA" in (c["skills"] or "")
            for c in available_crew
        )

        business_rules = {
            "total_crew_ok": total_available >= 4,
            "ttr_present": ttr_present,
            "lgv_present": lgv_present,
            "ba_non_ttr_ok": ba_non_ttr >= 2,
            "ffc_with_ba": ffc_with_ba,
        }

        all_rules_pass = all(business_rules.values())

        return {
            "rules_pass": all_rules_pass,
            "rules": business_rules,
            "details": {
                "total_available": total_available,
                "skill_counts": skill_counts,
                "ba_non_ttr": ba_non_ttr,
                "ffc_with_ba": ffc_with_ba,
            },
        }
    except Exception as e:
        logger.error(f"Error checking P22P6 business rules: {e}")
        return {"rules_pass": False, "error": "Error checking business rules"}


def get_appliance_available_data(appliance_name: str) -> Dict[str, Any]:
    """Check if appliance is available right now."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if appliance exists
            cursor.execute("SELECT id FROM appliance WHERE name = ?", (appliance_name,))
            appliance = cursor.fetchone()
            if not appliance:
                return {"error": f"Appliance {appliance_name} not found"}

            appliance_id = appliance[0]  # id is first column

            # Check basic appliance availability with data quality filters
            now = datetime.now()
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM appliance_availability
                WHERE appliance_id = ?
                AND datetime(start_time) <= datetime(?)
                AND datetime(end_time) > datetime(?)
                AND (julianday(end_time) - julianday(start_time)) <= 7.0
                AND date(start_time) >= date('now', '-7 days')
            """,
                (appliance_id, now, now),
            )

            result = cursor.fetchone()
            appliance_physically_available = result[0] > 0  # count is first column

            # For P22P6, apply business rules
            if appliance_name == "P22P6":
                if not appliance_physically_available:
                    # If appliance itself isn't available, don't bother checking crew
                    return {"available": False}

                # Check business rules for crew capability
                business_rules = check_p22p6_business_rules()
                if "error" in business_rules:
                    return {"error": business_rules["error"]}

                # P22P6 is only available if both appliance is available AND crew rules pass
                return {"available": business_rules["rules_pass"]}
            else:
                # For other appliances, just check basic availability
                return {"available": appliance_physically_available}

    except Exception as e:
        logger.error(f"Error checking appliance availability: {e}")
        return {"error": "Internal server error"}


def get_appliance_duration_data(appliance_name: str) -> Dict[str, Any]:
    """Get how long appliance is available for (string hours or null)."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if appliance exists
            cursor.execute("SELECT id FROM appliance WHERE name = ?", (appliance_name,))
            appliance = cursor.fetchone()
            if not appliance:
                return {"error": f"Appliance {appliance_name} not found"}

            appliance_id = appliance[0]  # id is first column

            # Get next availability block with data quality filters
            now = datetime.now()
            cursor.execute(
                """
                SELECT start_time, end_time FROM appliance_availability
                WHERE appliance_id = ?
                AND datetime(start_time) <= datetime(?)
                AND datetime(end_time) > datetime(?)
                AND (julianday(end_time) - julianday(start_time)) <= 7.0
                AND date(start_time) >= date('now', '-7 days')
                ORDER BY start_time LIMIT 1
            """,
                (appliance_id, now, now),
            )

            result = cursor.fetchone()
            if result:
                # For P22P6, check business rules before returning duration
                if appliance_name == "P22P6":
                    business_rules = check_p22p6_business_rules()
                    if "error" in business_rules:
                        return {"error": business_rules["error"]}

                    # If business rules don't pass, P22P6 is not operationally available
                    if not business_rules["rules_pass"]:
                        return {"duration": None}

                # Calculate duration for available appliance
                end_time = datetime.fromisoformat(result[1])
                duration_minutes = int((end_time - now).total_seconds() / 60)
                return {
                    "duration": _format_duration_minutes_to_hours_string(
                        max(0, duration_minutes)
                    )
                }
            else:
                return {"duration": None}
    except Exception as e:
        logger.error(f"Error getting appliance duration: {e}")
        return {"error": "Internal server error"}


def get_crew_contract_hours_data(crew_id: int) -> Dict[str, Any]:
    """Get crew member's contract hours information."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if crew exists and get contract hours
            cursor.execute(
                "SELECT name, contract_hours FROM crew WHERE id = ?", (crew_id,)
            )
            crew = cursor.fetchone()
            if not crew:
                return {"error": f"Crew ID {crew_id} not found"}

            return {"contract_hours": crew[1]}
    except Exception as e:
        logger.error(f"Error getting crew contract hours: {e}")
        return {"error": "Internal server error"}


def get_crew_hours_achieved_data(crew_id: int) -> Dict[str, Any]:
    """Get hours worked by crew member so far this week."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if crew exists
            cursor.execute("SELECT name FROM crew WHERE id = ?", (crew_id,))
            crew = cursor.fetchone()
            if not crew:
                return {"error": f"Crew ID {crew_id} not found"}

            # Get week boundaries
            week_start, week_end = get_week_boundaries()

            # Calculate hours achieved this week (availability periods that have ended)
            cursor.execute(
                """
                SELECT start_time, end_time FROM crew_availability
                WHERE crew_id = ?
                AND datetime(start_time) >= datetime(?)
                AND datetime(end_time) <= datetime(?)
                AND datetime(end_time) <= datetime('now')
                AND (julianday(end_time) - julianday(start_time)) <= 14.0
                ORDER BY start_time
            """,
                (crew_id, week_start, week_end),
            )

            periods = []
            for row in cursor.fetchall():
                start_time = datetime.fromisoformat(row[0])
                end_time = datetime.fromisoformat(row[1])
                periods.append((start_time, end_time))

            # Merge overlapping periods and calculate total hours
            merged_periods = merge_time_periods(periods)
            total_hours = sum(
                (end_time - start_time).total_seconds() / 3600.0
                for start_time, end_time in merged_periods
            )

            return {"hours_achieved": round(total_hours, 2)}
    except Exception as e:
        logger.error(f"Error getting crew hours achieved: {e}")
        return {"error": "Internal server error"}


def get_crew_hours_remaining_data(crew_id: int) -> Dict[str, Any]:
    """Get hours remaining for crew member to fulfill contract this week."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if crew exists and get contract hours
            cursor.execute(
                "SELECT name, contract_hours FROM crew WHERE id = ?", (crew_id,)
            )
            crew = cursor.fetchone()
            if not crew:
                return {"error": f"Crew ID {crew_id} not found"}

            contract_hours_str = crew[1]
            if not contract_hours_str:
                return {"hours_remaining": None}

            # Parse contract hours (format: "61 (159)" -> extract first number)
            try:
                contract_hours = float(contract_hours_str.split()[0])
            except (ValueError, IndexError):
                return {"hours_remaining": None}

            # Get hours achieved this week
            achieved_result = get_crew_hours_achieved_data(crew_id)
            if "error" in achieved_result:
                return achieved_result

            hours_achieved = achieved_result.get("hours_achieved", 0)
            hours_remaining = max(0, contract_hours - hours_achieved)

            return {"hours_remaining": round(hours_remaining, 2)}
    except Exception as e:
        logger.error(f"Error getting crew hours remaining: {e}")
        return {"error": "Internal server error"}


# Database configuration


def db_exists():
    """Check if database exists and is accessible"""
    try:
        logger.debug(f"Checking database at: {DB_PATH}")

        if not os.path.exists(DB_PATH):
            logger.debug(f"Database file does not exist at {DB_PATH}")
            return False

        # Try to open and read the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Simple check - if we can execute a basic query, the DB is good
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        conn.close()

        # If we have any tables, consider it healthy
        has_tables = len(tables) > 0
        logger.debug(f"Database has {len(tables)} tables: {[t[0] for t in tables]}")

        return has_tables
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return False


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        db_status = db_exists()
        return jsonify(
            {
                "status": "healthy" if db_status else "degraded",
                "database": "connected" if db_status else "no_data",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ), (200 if db_status else 503)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "error": "Health check failed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            500,
        )


@app.route("/", methods=["GET"])
def root():
    """Root endpoint - Visual dashboard of all API data"""
    try:
        # Get all crew data
        crew_list = get_crew_list_data()
        current_time = datetime.now()

        # Collect all crew availability and duration data
        crew_data = []
        for crew in crew_list:
            if isinstance(crew, dict) and "id" in crew:
                crew_id = crew["id"]
                availability_data = get_crew_available_data(crew_id)
                duration_data = get_crew_duration_data(crew_id)

                crew_info = {
                    "id": crew_id,
                    "name": crew.get("name", "Unknown"),
                    "display_name": crew.get(
                        "display_name", crew.get("name", "Unknown")
                    ),
                    "role": crew.get("role", "Unknown"),
                    "skills": crew.get("skills", "None"),
                    "available": (
                        availability_data.get("available", False)
                        if "available" in availability_data
                        else False
                    ),
                    "duration": (
                        duration_data.get("duration")
                        if "duration" in duration_data
                        else None
                    ),
                    "end_time_display": (
                        duration_data.get("end_time_display")
                        if "end_time_display" in duration_data
                        else None
                    ),
                    "contract_hours": crew.get("contract_hours", "Unknown"),
                }
                crew_data.append(crew_info)

        # Sort crew data: 1st by availability (available first), 2nd by role, 3rd by surname
        def sort_crew_key(crew):
            # Extract surname from name (format: "SURNAME, INITIALS")
            surname = (
                crew["name"].split(",")[0] if "," in crew["name"] else crew["name"]
            )
            # Define role hierarchy for sorting (higher rank = lower sort value)
            role_hierarchy = {"WC": 1, "CM": 2, "CC": 3, "FFC": 4, "FFD": 5, "FFT": 6}
            role_sort = role_hierarchy.get(crew["role"], 99)

            # Sort tuple: available (False=0, True=1, but we want available first so negate), role rank, surname
            return (not crew["available"], role_sort, surname)

        crew_data.sort(key=sort_crew_key)

        # Get appliance data
        p22p6_available_data = get_appliance_available_data("P22P6")
        p22p6_duration_data = get_appliance_duration_data("P22P6")

        appliance_data = {
            "available": (
                p22p6_available_data.get("available", False)
                if "available" in p22p6_available_data
                else False
            ),
            "duration": (
                p22p6_duration_data.get("duration")
                if "duration" in p22p6_duration_data
                else None
            ),
        }

        # Calculate dashboard statistics
        available_crew = [crew for crew in crew_data if crew["available"]]
        total_available = len(available_crew)

        # Count skills
        skill_counts = {"TTR": 0, "LGV": 0, "BA": 0}
        for crew in available_crew:
            skills = (
                crew["skills"].split()
                if crew["skills"] and crew["skills"] != "None"
                else []
            )
            for skill in skills:
                if skill in skill_counts:
                    skill_counts[skill] += 1

        # Calculate BA non-TTR count
        ba_non_ttr = sum(
            1
            for c in available_crew
            if "BA" in (c["skills"] or "") and "TTR" not in (c["skills"] or "")
        )

        # Get business rules results
        business_rules_result = check_p22p6_business_rules()
        business_rules = business_rules_result.get("rules", {})
        all_rules_pass = business_rules_result.get("rules_pass", False)

        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gartan Scraper Bot - Crew Availability Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }
        .header h1 {
            color: #2c3e50;
            margin: 0;
            font-size: 2.5em;
        }
        .timestamp {
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 10px;
        }
        .section {
            margin-bottom: 30px;
        }
        .section h2 {
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-bottom: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }
        .card {
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 15px;
            background: #fafafa;
        }
        .available {
            background: #d4edda;
            border-color: #c3e6cb;
        }
        .unavailable {
            background: #f8d7da;
            border-color: #f5c6cb;
        }
        .crew-name {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 5px;
        }
        .crew-details {
            font-size: 0.9em;
            color: #666;
        }
        .status {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.8em;
        }
        .status.yes {
            background: #28a745;
            color: white;
        }
        .status.no {
            background: #dc3545;
            color: white;
        }
        .appliance-section {
            text-align: center;
            background: #e8f4fd;
            border: 2px solid #3498db;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        .appliance-status {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        .appliance-status.operational {
            color: #28a745;
        }
        .appliance-status.unavailable {
            color: #dc3545;
        }
        .business-rules {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 10px;
            margin: 20px 0;
        }
        .rule {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            border-left: 4px solid #6c757d;
        }
        .rule.pass {
            border-left-color: #28a745;
        }
        .rule.fail {
            border-left-color: #dc3545;
        }
        .summary-stats {
            display: flex;
            justify-content: space-around;
            background: #e9ecef;
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
        }
        .stat {
            text-align: center;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #495057;
        }
        .stat-label {
            font-size: 0.9em;
            color: #6c757d;
        }
        .refresh-note {
            text-align: center;
            color: #6c757d;
            font-style: italic;
            margin-top: 30px;
        }
        @media (max-width: 768px) {
            .summary-stats {
                flex-direction: column;
                gap: 10px;
            }
            .header h1 {
                font-size: 2em;
            }
        }
    </style>
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => window.location.reload(), 30000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚒 Gartan Crew Availability Dashboard</h1>
            <div class="timestamp">Last updated: {{ current_time.strftime('%H:%M:%S on %d/%m/%Y') }}</div>
        </div>

        <div class="summary-stats">
            <div class="stat">
                <div class="stat-number">{{ total_available }}</div>
                <div class="stat-label">Available Crew</div>
            </div>
            <div class="stat">
                <div class="stat-number">{{ skill_counts.TTR }}</div>
                <div class="stat-label">Officer(s)</div>
            </div>
            <div class="stat">
                <div class="stat-number">{{ skill_counts.LGV }}</div>
                <div class="stat-label">Driver(s)</div>
            </div>
            <div class="stat">
                <div class="stat-number">{{ skill_counts.BA }}</div>
                <div class="stat-label">BA Qualified</div>
            </div>
        </div>

        <div class="appliance-section">
            <h2>🚒 P22P6 Fire Appliance</h2>
            <div class="appliance-status {{ 'operational' if appliance_data.available else 'unavailable' }}">
                {{ 'OPERATIONAL' if appliance_data.available else 'NOT AVAILABLE' }}
            </div>
            {% if appliance_data.duration %}
            <div>Available for: {{ appliance_data.duration }}</div>
            {% endif %}

            <div class="business-rules">
                <div class="rule {{ 'pass' if business_rules.total_crew_ok else 'fail' }}">
                    <strong>Minimum Crew (≥4):</strong>
                    <span class="status {{ 'yes' if business_rules.total_crew_ok else 'no' }}">
                        {{ 'PASS' if business_rules.total_crew_ok else 'FAIL' }}
                    </span>
                    <br><small>{{ total_available }} crew available</small>
                </div>
                <div class="rule {{ 'pass' if business_rules.ttr_present else 'fail' }}">
                    <strong>Officer available:</strong>
                    <span class="status {{ 'yes' if business_rules.ttr_present else 'no' }}">
                        {{ 'PASS' if business_rules.ttr_present else 'FAIL' }}
                    </span>
                    <br><small>{{ skill_counts.TTR }} officer(s) available</small>
                </div>
                <div class="rule {{ 'pass' if business_rules.lgv_present else 'fail' }}">
                    <strong>Driver available:</strong>
                    <span class="status {{ 'yes' if business_rules.lgv_present else 'no' }}">
                        {{ 'PASS' if business_rules.lgv_present else 'FAIL' }}
                    </span>
                    <br><small>{{ skill_counts.LGV }} driver(s) available</small>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>👥 Individual Crew Status</h2>
            <div class="grid">
                {% for crew in crew_data %}
                <div class="card {{ 'available' if crew.available else 'unavailable' }}">
                    <div class="crew-name">{{ crew.display_name }}</div>
                    <div class="crew-details">
                        <strong>Role:</strong> {{ crew.role }}<br>
                        <strong>Skills:</strong> {{ crew.skills }}<br>
                        <strong>Status:</strong>
                        <span class="status {{ 'yes' if crew.available else 'no' }}">
                            {{ 'AVAILABLE' if crew.available else 'UNAVAILABLE' }}
                        </span><br>
                        {% if crew.available and crew.duration %}
                        <strong>Duration:</strong> {{ crew.duration }}{% if crew.end_time_display %} ({{ crew.end_time_display }}){% endif %}<br>
                        {% endif %}
                        <strong>Contract:</strong> {{ crew.contract_hours }} hours
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="refresh-note">
            This page automatically refreshes every 30 seconds
        </div>

        <div class="section">
            <h2>🔗 API Endpoints</h2>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 15px;">
                    <div>
                        <h3 style="margin-top: 0; color: #495057;">Service Information</h3>
                        <ul style="list-style: none; padding: 0;">
                            <li style="margin: 8px 0;"><a href="/health" style="text-decoration: none; color: #007bff;">/health</a> - Service and database status</li>
                        </ul>

                        <h3 style="color: #495057;">Crew Information</h3>
                        <ul style="list-style: none; padding: 0;">
                            <li style="margin: 8px 0;"><a href="/crew" style="text-decoration: none; color: #007bff;">/crew</a> - List all crew members with details</li>
                            <li style="margin: 8px 0;"><span style="color: #007bff;">/crew/{id}/available</span> - Check if crew member is available now</li>
                            <li style="margin: 8px 0;"><span style="color: #007bff;">/crew/{id}/duration</span> - How long crew member is available for</li>
                            <li style="margin: 8px 0;"><span style="color: #007bff;">/crew/{id}/hours-this-week</span> - Hours available since Monday</li>
                            <li style="margin: 8px 0;"><span style="color: #007bff;">/crew/{id}/contract-hours</span> - Contract hours information</li>
                        </ul>
                    </div>
                    <div>
                        <h3 style="margin-top: 0; color: #495057;">Appliance Information</h3>
                        <ul style="list-style: none; padding: 0;">
                            <li style="margin: 8px 0;"><a href="/appliances/P22P6/available" style="text-decoration: none; color: #007bff;">/appliances/P22P6/available</a> - Check if P22P6 is operational</li>
                            <li style="margin: 8px 0;"><a href="/appliances/P22P6/duration" style="text-decoration: none; color: #007bff;">/appliances/P22P6/duration</a> - How long P22P6 is available for</li>
                        </ul>

                        <h3 style="color: #495057;">Weekly Hours Tracking</h3>
                        <ul style="list-style: none; padding: 0;">
                            <li style="margin: 8px 0;"><span style="color: #007bff;">/crew/{id}/hours-planned-week</span> - Total planned hours this week</li>
                            <li style="margin: 8px 0;"><span style="color: #007bff;">/crew/{id}/hours-achieved</span> - Hours worked so far this week</li>
                            <li style="margin: 8px 0;"><span style="color: #007bff;">/crew/{id}/hours-remaining</span> - Hours remaining to fulfill contract</li>
                        </ul>

                        <p style="margin-top: 15px; font-size: 0.9em; color: #6c757d;">
                            <strong>Note:</strong> Replace {id} with actual crew member ID (e.g., /crew/1/available)
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
        """

        return render_template_string(
            html_template,
            crew_data=crew_data,
            appliance_data=appliance_data,
            current_time=current_time,
            total_available=total_available,
            skill_counts=skill_counts,
            business_rules=business_rules,
            ba_non_ttr=ba_non_ttr,
            all_rules_pass=all_rules_pass,
        )

    except Exception as e:
        logger.error(f"Error generating dashboard: {e}")
        # Fallback to JSON response
        return jsonify(
            {
                "service": "Gartan Scraper Bot API",
                "version": "1.0",
                "error": "Dashboard temporarily unavailable",
                "endpoints": {
                    "health": "/health",
                    "crew": "/crew",
                    "crew_available": "/crew/<id>/available",
                    "crew_duration": "/crew/<id>/duration",
                    "appliance_available": "/appliances/<name>/available",
                    "appliance_duration": "/appliances/<name>/duration",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


@app.route("/crew", methods=["GET"])
def get_crew():
    """Get list of all crew members"""
    try:
        crew_data = get_crew_list_data()
        return jsonify(crew_data)
    except Exception as e:
        logger.error(f"Error getting crew list: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/crew/<int:crew_id>/available", methods=["GET"])
def get_crew_available(crew_id: int):
    """Check if crew member is available right now"""
    try:
        result = get_crew_available_data(crew_id)

        if "error" in result:
            if "not found" in result["error"]:
                return jsonify({"error": f"Crew ID {crew_id} not found"}), 404
            else:
                return jsonify({"error": "Internal server error"}), 500

        return jsonify(result["available"])
    except Exception as e:
        logger.error(f"Error checking crew {crew_id} availability: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/crew/<int:crew_id>/duration", methods=["GET"])
def get_crew_duration(crew_id: int):
    """Get crew member's current availability duration"""
    try:
        result = get_crew_duration_data(crew_id)

        if "error" in result:
            if "not found" in result["error"]:
                return jsonify({"error": f"Crew ID {crew_id} not found"}), 404
            else:
                return jsonify({"error": "Internal server error"}), 500
        # Return string hours or null directly
        return jsonify(result.get("duration"))
    except Exception as e:
        logger.error(f"Error getting crew {crew_id} duration: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/crew/<int:crew_id>/hours-this-week", methods=["GET"])
def get_crew_hours_this_week(crew_id: int):
    """Get crew member's availability hours since Monday"""
    try:
        result = get_crew_hours_this_week_data(crew_id)

        if "error" in result:
            if "not found" in result["error"]:
                return jsonify({"error": f"Crew ID {crew_id} not found"}), 404
            else:
                return jsonify({"error": "Internal server error"}), 500
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting crew {crew_id} weekly hours: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/crew/<int:crew_id>/hours-planned-week", methods=["GET"])
def get_crew_hours_planned_week(crew_id: int):
    """Get crew member's total planned weekly availability hours"""
    try:
        result = get_crew_hours_planned_week_data(crew_id)

        if "error" in result:
            if "not found" in result["error"]:
                return jsonify({"error": f"Crew ID {crew_id} not found"}), 404
            else:
                return jsonify({"error": "Internal server error"}), 500
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting crew {crew_id} planned weekly hours: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/crew/<int:crew_id>/contract-hours", methods=["GET"])
def get_crew_contract_hours(crew_id: int):
    """Get crew member's contract hours information"""
    try:
        result = get_crew_contract_hours_data(crew_id)

        if "error" in result:
            if "not found" in result["error"]:
                return jsonify({"error": f"Crew ID {crew_id} not found"}), 404
            else:
                return jsonify({"error": "Internal server error"}), 500
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting crew {crew_id} contract hours: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/crew/<int:crew_id>/hours-achieved", methods=["GET"])
def get_crew_hours_achieved(crew_id: int):
    """Get hours worked by crew member so far this week"""
    try:
        result = get_crew_hours_achieved_data(crew_id)

        if "error" in result:
            if "not found" in result["error"]:
                return jsonify({"error": f"Crew ID {crew_id} not found"}), 404
            else:
                return jsonify({"error": "Internal server error"}), 500
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting crew {crew_id} hours achieved: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/crew/<int:crew_id>/hours-remaining", methods=["GET"])
def get_crew_hours_remaining(crew_id: int):
    """Get hours remaining for crew member to fulfill contract this week"""
    try:
        result = get_crew_hours_remaining_data(crew_id)

        if "error" in result:
            if "not found" in result["error"]:
                return jsonify({"error": f"Crew ID {crew_id} not found"}), 404
            else:
                return jsonify({"error": "Internal server error"}), 500
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting crew {crew_id} hours remaining: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/appliances/<appliance_name>/available", methods=["GET"])
def get_appliance_available(appliance_name: str):
    """Check if appliance is available right now"""
    try:
        result = get_appliance_available_data(appliance_name)

        if "error" in result:
            if "not found" in result["error"]:
                return (
                    jsonify({"error": f"Appliance '{appliance_name}' not found"}),
                    404,
                )
            else:
                return jsonify({"error": "Internal server error"}), 500
        return jsonify(result["available"])
    except Exception as e:
        logger.error(f"Error checking appliance {appliance_name} availability: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/appliances/<appliance_name>/duration", methods=["GET"])
def get_appliance_duration(appliance_name: str):
    """Get appliance's current availability duration"""
    try:
        result = get_appliance_duration_data(appliance_name)

        if "error" in result:
            if "not found" in result["error"]:
                return (
                    jsonify({"error": f"Appliance '{appliance_name}' not found"}),
                    404,
                )
            else:
                return jsonify({"error": "Internal server error"}), 500
        return jsonify(result.get("duration"))
    except Exception as e:
        logger.error(f"Error getting appliance {appliance_name} duration: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


if __name__ == "__main__":
    # Production configuration
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    logger.info(f"Starting Gartan API Server on port {port}")
    logger.info(
        f"Database status: {'Ready' if db_exists() else 'No data - waiting for scraper'}"
    )

    app.run(host="0.0.0.0", port=port, debug=debug)
