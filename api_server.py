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
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, render_template_string

from config import config
from fetch_station_display import fetch_station_display_html
from parse_station_display import parse_station_display_html

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
app = Flask(__name__, static_url_path="/static", static_folder="static")

# Database path
DB_PATH = config.db_path


def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_dashboard_data() -> List[Dict[str, Any]]:
    """
    ⚡ Bolt: Fetches all data required for the dashboard in a single, optimized query.
    This replaces three separate functions (`get_crew_list_data`,
    `get_all_crew_availability_data`, `get_all_crew_duration_data`) and fixes an
    N+1-style query problem, significantly speeding up the dashboard load time.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now()
            cursor.execute(
                """
                WITH CurrentAvailability AS (
                    SELECT
                        crew_id,
                        start_time,
                        end_time,
                        -- Rank availability blocks to find the one that is currently active
                        ROW_NUMBER() OVER(PARTITION BY crew_id ORDER BY start_time) as rn
                    FROM crew_availability
                    WHERE
                        datetime(start_time) <= datetime(?)
                        AND datetime(end_time) > datetime(?)
                        -- Data quality filters to exclude excessively long or old blocks
                        AND (julianday(end_time) - julianday(start_time)) <= 7.0
                        AND date(start_time) >= date('now', '-7 days')
                )
                SELECT
                    c.id,
                    c.name,
                    c.contact,
                    c.role,
                    c.skills,
                    c.contract_hours,
                    ca.end_time
                FROM
                    crew c
                LEFT JOIN
                    CurrentAvailability ca ON c.id = ca.crew_id AND ca.rn = 1
                ORDER BY
                    c.name
            """,
                (now, now),
            )

            crew_list = []
            for row in cursor.fetchall():
                crew_data = {
                    "id": row["id"],
                    "name": row["name"],
                    "role": row["role"],
                    "skills": row["skills"],
                    "contract_hours": row["contract_hours"],
                    "available": False,
                    "duration": None,
                    "end_time_display": None,
                }

                # Use name as a fallback for display_name
                display_name = row["name"]
                if row["contact"]:
                    contact_parts = row["contact"].split("|")
                    if len(contact_parts) >= 1 and contact_parts[0]:
                        display_name = contact_parts[0]
                crew_data["display_name"] = display_name

                if row["end_time"]:
                    crew_data["available"] = True
                    end_time = datetime.fromisoformat(row["end_time"])
                    duration_minutes = int((end_time - now).total_seconds() / 60)
                    crew_data["duration"] = _format_duration_minutes_to_hours_string(
                        max(0, duration_minutes)
                    )

                    # Format end time for display
                    end_time_str = end_time.strftime("%H:%M")
                    if end_time.date() == now.date():
                        crew_data["end_time_display"] = f"{end_time_str} today"
                    elif end_time.date() == (now + timedelta(days=1)).date():
                        crew_data["end_time_display"] = f"{end_time_str} tomorrow"
                    else:
                        crew_data["end_time_display"] = end_time.strftime(
                            "%H:%M on %d/%m"
                        )

                crew_list.append(crew_data)

            return crew_list
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
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


def check_p22p6_business_rules(
    available_crew: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Check P22P6 business rules against available crew.
    - If `available_crew` is provided, it's used directly.
    - Otherwise, crew data is fetched from the database.
    """
    try:
        # --- Performance Optimization ---
        # If available_crew isn't provided, fetch it from the database.
        if available_crew is None:
            # ⚡ Bolt: Use the optimized `get_dashboard_data` to get all crew info at once.
            all_crew_data = get_dashboard_data()
            available_crew = [crew for crew in all_crew_data if crew.get("available")]

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


def get_appliance_available_data(
    appliance_name: str,
    available_crew: Optional[List[Dict[str, Any]]] = None,
    business_rules_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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

                # --- Performance Optimization ---
                # Use pre-calculated business rules if available, otherwise compute them.
                if business_rules_result is None:
                    business_rules_result = check_p22p6_business_rules(
                        available_crew=available_crew
                    )

                if "error" in business_rules_result:
                    return {"error": business_rules_result["error"]}

                # P22P6 is only available if both appliance is available AND crew rules pass
                return {"available": business_rules_result["rules_pass"]}
            else:
                # For other appliances, just check basic availability
                return {"available": appliance_physically_available}

    except Exception as e:
        logger.error(f"Error checking appliance availability: {e}")
        return {"error": "Internal server error"}


def get_appliance_duration_data(
    appliance_name: str,
    available_crew: Optional[List[Dict[str, Any]]] = None,
    business_rules_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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
                    # --- Performance Optimization ---
                    # Use pre-calculated business rules if available, otherwise compute them.
                    if business_rules_result is None:
                        business_rules_result = check_p22p6_business_rules(
                            available_crew=available_crew
                        )

                    if "error" in business_rules_result:
                        return {"error": business_rules_result["error"]}

                    # If business rules don't pass, P22P6 is not operationally available
                    if not business_rules_result["rules_pass"]:
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
    """
    Get hours remaining for crew to fulfill contract this week.
    - Performance: Calculates achieved hours using the same DB connection to avoid a second DB call.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if crew exists and get contract hours in one go
            cursor.execute(
                "SELECT name, contract_hours FROM crew WHERE id = ?", (crew_id,)
            )
            crew = cursor.fetchone()
            if not crew:
                return {"error": f"Crew ID {crew_id} not found"}

            contract_hours_str = crew[1]  # Access by index
            if not contract_hours_str:
                return {"hours_remaining": None}

            # Parse contract hours (e.g., "61 (159)" -> 61.0)
            try:
                contract_hours = float(contract_hours_str.split()[0])
            except (ValueError, IndexError):
                return {"hours_remaining": None}

            # --- Start of inlined `get_crew_hours_achieved_data` logic ---
            week_start, week_end = get_week_boundaries()

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

            periods = [
                (datetime.fromisoformat(row[0]), datetime.fromisoformat(row[1]))
                for row in cursor.fetchall()
            ]

            merged_periods = merge_time_periods(periods)
            hours_achieved = sum(
                (end - start).total_seconds() / 3600.0 for start, end in merged_periods
            )
            # --- End of inlined logic ---

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
    start_time_req = time.time()
    try:
        # ⚡ Bolt: Use the optimized single-query function to fetch all dashboard data.
        crew_data = get_dashboard_data()
        current_time = datetime.now()

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

        # Calculate dashboard statistics
        available_crew = [crew for crew in crew_data if crew["available"]]
        total_available = len(available_crew)

        # --- Performance Optimization: Calculate business rules once ---
        # The business rules result is required by multiple components on the dashboard.
        # We calculate it once here and pass it to the relevant functions to avoid
        # redundant computations, improving dashboard load time.
        business_rules_result = check_p22p6_business_rules(
            available_crew=available_crew
        )

        # Get appliance data, passing in the pre-calculated business rules
        p22p6_available_data = get_appliance_available_data(
            "P22P6",
            available_crew=available_crew,
            business_rules_result=business_rules_result,
        )
        p22p6_duration_data = get_appliance_duration_data(
            "P22P6",
            available_crew=available_crew,
            business_rules_result=business_rules_result,
        )

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

        # Extract details from the pre-calculated business rules result
        business_rules_details = business_rules_result.get("details", {})
        skill_counts = business_rules_details.get("skill_counts", {})
        ba_non_ttr = business_rules_details.get("ba_non_ttr", 0)
        business_rules = business_rules_result.get("rules", {})
        all_rules_pass = business_rules_result.get("rules_pass", False)

        # --- Performance Logging ---
        end_time_req = time.time()
        duration_ms = (end_time_req - start_time_req) * 1000
        logger.info(f"Dashboard generated in {duration_ms:.2f} ms")

        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gartan Scraper Bot - Crew Availability Dashboard</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <script src="/static/js/refresh.js"></script>
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
            <div class="api-endpoints-container">
                <div class="api-endpoints-grid">
                    <div>
                        <h3 class="api-endpoints-heading">Service Information</h3>
                        <ul class="api-endpoints-list">
                            <li class="api-endpoints-list-item"><a href="/health" class="api-endpoints-link">/health</a> - Service and database status</li>
                        </ul>

                        <h3 class="api-endpoints-heading">Crew Information</h3>
                        <ul class="api-endpoints-list">
                            <li class="api-endpoints-list-item"><a href="/crew" class="api-endpoints-link">/crew</a> - List all crew members with details</li>
                            <li class="api-endpoints-list-item"><span class="api-endpoints-path">/crew/{id}/available</span> - Check if crew member is available now</li>
                            <li class="api-endpoints-list-item"><span class="api-endpoints-path">/crew/{id}/duration</span> - How long crew member is available for</li>
                            <li class="api-endpoints-list-item"><span class="api-endpoints-path">/crew/{id}/hours-this-week</span> - Hours available since Monday</li>
                            <li class="api-endpoints-list-item"><span class="api-endpoints-path">/crew/{id}/contract-hours</span> - Contract hours information</li>
                        </ul>
                    </div>
                    <div>
                        <h3 class="api-endpoints-heading">Appliance Information</h3>
                        <ul class="api-endpoints-list">
                            <li class="api-endpoints-list-item"><a href="/appliances/P22P6/available" class="api-endpoints-link">/appliances/P22P6/available</a> - Check if P22P6 is operational</li>
                            <li class="api-endpoints-list-item"><a href="/appliances/P22P6/duration" class="api-endpoints-link">/appliances/P22P6/duration</a> - How long P22P6 is available for</li>
                        </ul>

                        <h3 class="api-endpoints-heading">Weekly Hours Tracking</h3>
                        <ul class="api-endpoints-list">
                            <li class="api-endpoints-list-item"><span class="api-endpoints-path">/crew/{id}/hours-planned-week</span> - Total planned hours this week</li>
                            <li class="api-endpoints-list-item"><span class="api-endpoints-path">/crew/{id}/hours-achieved</span> - Hours worked so far this week</li>
                            <li class="api-endpoints-list-item"><span class="api-endpoints-path">/crew/{id}/hours-remaining</span> - Hours remaining to fulfill contract</li>
                        </ul>

                        <p class="api-endpoints-note">
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
        # ⚡ Bolt: Use the optimized `get_dashboard_data` to ensure this endpoint
        # benefits from the single-query optimization, even though it doesn't need
        # the availability data directly. This keeps data fetching consistent.
        crew_data = get_dashboard_data()
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


@app.route("/station/now", methods=["GET"])
def get_station_now():
    """Get real-time station data."""
    try:
        html = fetch_station_display_html()
        if not html:
            return jsonify({"error": "Failed to fetch station display HTML"}), 500

        data = parse_station_display_html(html)
        if not data:
            return jsonify({"error": "Failed to parse station display HTML"}), 500

        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting real-time station data: {e}")
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
    # SECURE: Add CSP to protect against XSS. Allows inline styles and the auto-refresh script.
    # SECURE: Add CSP to protect against XSS. Allows only self-hosted styles.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
    )
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
