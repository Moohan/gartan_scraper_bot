#!/usr/bin/env python3
"""Production Flask API server exposing availability endpoints.

Endpoints (v1):
    /health                               — service + DB status
    /v1/crew                              — list crew ids/names
    /v1/crew/<id>/available               — boolean current availability
    /v1/crew/<id>/duration                — remaining duration string or null
    /v1/crew/<id>/hours-this-week         — hours available since Monday
    /v1/crew/<id>/hours-planned-week      — total planned hours this week
    /v1/crew/<id>/contract-hours          — contract hours info (e.g., "61 (159)")
    /v1/crew/<id>/hours-achieved          — hours worked so far this week
    /v1/crew/<id>/hours-remaining         — hours remaining to fulfill contract
    /v1/appliances/<name>/available       — appliance availability
    /v1/appliances/<name>/duration        — appliance availability duration

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

from flask import Flask, jsonify

from config import config


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
            cursor.execute("SELECT id, name, contact, role, skills, contract_hours FROM crew ORDER BY name")
            rows = cursor.fetchall()

            crew_list = []
            for row in rows:
                crew_data = {
                    "id": row["id"], 
                    "name": row["name"],
                    "role": row["role"],
                    "skills": row["skills"],
                    "contract_hours": row["contract_hours"]
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
            is_available = result["count"] > 0

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
                return {
                    "duration": _format_duration_minutes_to_hours_string(
                        max(0, duration_minutes)
                    )
                }
            else:
                return {"duration": None}
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

            # Check current availability with data quality filters
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
            is_available = result[0] > 0  # count is first column

            return {"available": is_available}
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
            cursor.execute("SELECT name, contract_hours FROM crew WHERE id = ?", (crew_id,))
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
            cursor.execute("SELECT name, contract_hours FROM crew WHERE id = ?", (crew_id,))
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
    """Root endpoint - API information"""
    return jsonify(
        {
            "service": "Gartan Scraper Bot API",
            "version": "1.0",
            "endpoints": {
                "health": "/health",
                "crew": "/v1/crew",
                "crew_available": "/v1/crew/<id>/available",
                "crew_duration": "/v1/crew/<id>/duration",
                "crew_hours_week": "/v1/crew/<id>/hours-this-week",
                "crew_planned_week": "/v1/crew/<id>/hours-planned-week",
                "crew_contract_hours": "/v1/crew/<id>/contract-hours",
                "crew_hours_achieved": "/v1/crew/<id>/hours-achieved",
                "crew_hours_remaining": "/v1/crew/<id>/hours-remaining",
                "appliance_available": "/v1/appliances/<name>/available",
                "appliance_duration": "/v1/appliances/<name>/duration",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.route("/v1/crew", methods=["GET"])
def get_crew():
    """Get list of all crew members"""
    try:
        crew_data = get_crew_list_data()
        return jsonify(crew_data)
    except Exception as e:
        logger.error(f"Error getting crew list: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/v1/crew/<int:crew_id>/available", methods=["GET"])
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


@app.route("/v1/crew/<int:crew_id>/duration", methods=["GET"])
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


@app.route("/v1/crew/<int:crew_id>/hours-this-week", methods=["GET"])
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


@app.route("/v1/crew/<int:crew_id>/hours-planned-week", methods=["GET"])
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


@app.route("/v1/crew/<int:crew_id>/contract-hours", methods=["GET"])
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


@app.route("/v1/crew/<int:crew_id>/hours-achieved", methods=["GET"])
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


@app.route("/v1/crew/<int:crew_id>/hours-remaining", methods=["GET"])
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


@app.route("/v1/appliances/<appliance_name>/available", methods=["GET"])
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


@app.route("/v1/appliances/<appliance_name>/duration", methods=["GET"])
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


if __name__ == "__main__":
    # Production configuration
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    logger.info(f"Starting Gartan API Server on port {port}")
    logger.info(
        f"Database status: {'Ready' if db_exists() else 'No data - waiting for scraper'}"
    )

    app.run(host="0.0.0.0", port=port, debug=debug)
