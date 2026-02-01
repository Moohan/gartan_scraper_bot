#!/usr/bin/env python3
"""Simplified Flask API server for Gartan availability."""

import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, render_template_string

from config import config
from gartan_fetch import fetch_station_feed_html
from parse_grid import parse_station_feed_html

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_url_path="/static", static_folder="static")

# Database configuration
DB_PATH = config.db_path
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_converter("DATETIME", lambda b: datetime.fromisoformat(b.decode()))
sqlite3.register_converter("datetime", lambda b: datetime.fromisoformat(b.decode()))


def get_db():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def parse_dt(val):
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        return datetime.fromisoformat(val)
    return val


# --- Data Helpers ---


def get_week_boundaries() -> Tuple[datetime, datetime]:
    now = datetime.now()
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday


def merge_periods(
    periods: List[Tuple[datetime, datetime]],
) -> List[Tuple[datetime, datetime]]:
    if not periods:
        return []
    sorted_p = sorted(periods, key=lambda x: x[0])
    merged = [sorted_p[0]]
    for curr_s, curr_e in sorted_p[1:]:
        last_s, last_e = merged[-1]
        if curr_s <= last_e:
            merged[-1] = (last_s, max(last_e, curr_e))
        else:
            merged.append((curr_s, curr_e))
    return merged


def format_hours(minutes: Optional[int]) -> Optional[str]:
    if minutes is None or minutes <= 0:
        return None
    return f"{minutes / 60.0:.2f}h"


def get_crew_list() -> List[Dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM crew ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def get_availability(entity_id: int, table: str, now: datetime) -> Dict:
    col = "crew_id" if table == "crew_availability" else "appliance_id"
    with get_db() as conn:
        curr = conn.execute(
            f"SELECT end_time FROM {table} WHERE {col} = ? AND start_time <= ? AND end_time > ? LIMIT 1",
            (entity_id, now, now),
        ).fetchone()
        if not curr:
            return {"available": False, "duration": None, "end_time_display": None}

        end_time = parse_dt(curr["end_time"])
        duration_min = int((end_time - now).total_seconds() / 60)

        display = end_time.strftime("%H:%M")
        if end_time.date() == now.date():
            display += " today"
        elif end_time.date() == (now + timedelta(days=1)).date():
            display += " tomorrow"
        else:
            display += end_time.strftime(" on %d/%m")

        return {
            "available": True,
            "duration": format_hours(duration_min),
            "end_time_display": display,
        }


def get_weekly_stats(crew_id: int) -> Dict:
    start, end = get_week_boundaries()
    now = datetime.now()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT start_time, end_time FROM crew_availability WHERE crew_id = ? AND end_time > ? AND start_time < ?",
            (crew_id, start, end),
        ).fetchall()
        planned, achieved = [], []
        for r in rows:
            s, e = parse_dt(r[0]), parse_dt(r[1])
            planned.append((max(s, start), min(e, end)))
            if e <= now:
                achieved.append((max(s, start), e))
            elif s < now:
                achieved.append((max(s, start), now))

        def total_hrs(p):
            return sum((e - s).total_seconds() / 3600 for s, e in merge_periods(p))

        crew = conn.execute(
            "SELECT contract_hours FROM crew WHERE id = ?", (crew_id,)
        ).fetchone()
        if not crew:
            return {"error": "Not found"}

        achieved_val = total_hrs(achieved)
        contract_str = crew["contract_hours"] or "0"
        contract = (
            float(contract_str.split()[0])
            if contract_str and contract_str[0].isdigit()
            else 0
        )
        return {
            "hours_planned_week": round(total_hrs(planned), 2),
            "hours_achieved": round(achieved_val, 2),
            "hours_this_week": round(achieved_val, 2),
            "hours_remaining": round(max(0, contract - achieved_val), 2),
            "contract_hours": contract_str,
        }


def check_rules(available_ids: List[int]) -> Dict:
    if not available_ids:
        return {
            "rules_pass": False,
            "rules": {},
            "skill_counts": {"TTR": 0, "LGV": 0, "BA": 0},
            "ba_non_ttr": 0,
        }
    with get_db() as conn:
        placeholders = ",".join("?" * len(available_ids))
        rows = conn.execute(
            f"SELECT role, skills FROM crew WHERE id IN ({placeholders})", available_ids
        ).fetchall()

    skills = {"TTR": 0, "LGV": 0, "BA": 0}
    ba_non_ttr, ffc_ba = 0, False
    for r in rows:
        c_skills = (r["skills"] or "").split()
        role = r["role"]

        # Enhanced skill mapping
        # 1. LGV mapping include ERD
        if "LGV" in c_skills or "ERD" in c_skills:
            skills["LGV"] += 1

        # 2. TTR mapping include IC or CC role
        if "TTR" in c_skills or "IC" in c_skills or role in ["FFC", "CC", "WC", "CM"]:
            skills["TTR"] += 1

        if "BA" in c_skills:
            skills["BA"] += 1
            if (
                "TTR" not in c_skills
                and "IC" not in c_skills
                and role not in ["FFC", "CC", "WC", "CM"]
            ):
                ba_non_ttr += 1
            if role in ["FFC", "CC", "WC", "CM"]:
                ffc_ba = True

    rules = {
        "total_crew_ok": len(rows) >= 4,
        "ttr_present": skills["TTR"] > 0,
        "lgv_present": skills["LGV"] > 0,
        "ba_non_ttr_ok": ba_non_ttr >= 2,
        "ffc_with_ba": ffc_ba,
    }
    return {
        "rules_pass": all(rules.values()),
        "rules": rules,
        "skill_counts": skills,
        "ba_non_ttr": ba_non_ttr,
    }


# --- Routes ---


@app.route("/health")
def health():
    try:
        with get_db() as conn:
            conn.execute("SELECT 1")
        return jsonify(
            {
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except:
        return jsonify({"status": "degraded"}), 503


@app.route("/")
def root():
    try:
        now = datetime.now()
        crew = get_crew_list()
        crew_data = []
        for c in crew:
            avail = get_availability(c["id"], "crew_availability", now)
            crew_data.append({**c, **avail})

        ranks = {"WC": 1, "CM": 2, "CC": 3, "FFC": 4, "FFD": 5, "FFT": 6}
        crew_data.sort(
            key=lambda x: (not x["available"], ranks.get(x["role"], 99), x["name"])
        )

        avail_ids = [c["id"] for c in crew_data if c["available"]]
        rules_res = check_rules(avail_ids)

        p22p6_base = {"available": False, "duration": None}
        with get_db() as conn:
            app_p22 = conn.execute(
                "SELECT id FROM appliance WHERE name = 'P22P6'"
            ).fetchone()
            if app_p22:
                p22p6_base = get_availability(
                    app_p22["id"], "appliance_availability", now
                )

        p22p6_avail = p22p6_base["available"] and rules_res["rules_pass"]

        return render_template_string(
            DASHBOARD_TEMPLATE,
            crew_data=crew_data,
            now=now,
            total_available=len(avail_ids),
            p22p6_avail=p22p6_avail,
            p22p6_duration=p22p6_base["duration"] if p22p6_avail else None,
            rules=rules_res["rules"],
            skill_counts=rules_res["skill_counts"],
        )
    except Exception as e:
        logger.error(f"Root error: {e}")
        return (
            jsonify({"error": "Internal Server Error", "Dashboard": "Unavailable"}),
            500,
        )


@app.route("/crew")
def list_crew():
    try:
        return jsonify(get_crew_list())
    except:
        return jsonify({"error": "DB error"}), 500


@app.route("/crew/<int:id>/available")
def crew_avail(id):
    try:
        res = get_availability(id, "crew_availability", datetime.now())
        with get_db() as conn:
            if not conn.execute("SELECT 1 FROM crew WHERE id = ?", (id,)).fetchone():
                return jsonify({"error": "Not found"}), 404
        return jsonify(res["available"])
    except:
        return jsonify({"error": "DB error"}), 500


@app.route("/crew/<int:id>/duration")
def crew_dur(id):
    try:
        res = get_availability(id, "crew_availability", datetime.now())
        with get_db() as conn:
            if not conn.execute("SELECT 1 FROM crew WHERE id = ?", (id,)).fetchone():
                return jsonify({"error": "Not found"}), 404
        return jsonify(res["duration"])
    except:
        return jsonify({"error": "DB error"}), 500


@app.route("/crew/<int:id>/hours-this-week")
def crew_hrs_this(id):
    try:
        res = get_weekly_stats(id)
        return jsonify(res) if "error" not in res else (jsonify(res), 404)
    except:
        return jsonify({"error": "DB error"}), 500


@app.route("/crew/<int:id>/hours-planned-week")
def crew_hrs_planned(id):
    try:
        res = get_weekly_stats(id)
        return (
            jsonify({"hours_planned_week": res["hours_planned_week"]})
            if "error" not in res
            else (jsonify(res), 404)
        )
    except:
        return jsonify({"error": "DB error"}), 500


@app.route("/crew/<int:id>/contract-hours")
def crew_contract(id):
    try:
        res = get_weekly_stats(id)
        return (
            jsonify({"contract_hours": res["contract_hours"]})
            if "error" not in res
            else (jsonify(res), 404)
        )
    except:
        return jsonify({"error": "DB error"}), 500


@app.route("/crew/<int:id>/hours-achieved")
def crew_hrs_achieved(id):
    try:
        res = get_weekly_stats(id)
        return (
            jsonify({"hours_achieved": res["hours_achieved"]})
            if "error" not in res
            else (jsonify(res), 404)
        )
    except:
        return jsonify({"error": "DB error"}), 500


@app.route("/crew/<int:id>/hours-remaining")
def crew_hrs_rem(id):
    try:
        res = get_weekly_stats(id)
        return (
            jsonify({"hours_remaining": res["hours_remaining"]})
            if "error" not in res
            else (jsonify(res), 404)
        )
    except:
        return jsonify({"error": "DB error"}), 500


@app.route("/appliances/<name>/available")
def app_avail(name):
    try:
        now = datetime.now()
        with get_db() as conn:
            app = conn.execute(
                "SELECT id FROM appliance WHERE name = ?", (name,)
            ).fetchone()
            if not app:
                return jsonify({"error": "Not found"}), 404
            base = get_availability(app["id"], "appliance_availability", now)
            if name == "P22P6":
                avail_ids = [
                    r[0]
                    for r in conn.execute(
                        "SELECT crew_id FROM crew_availability WHERE start_time <= ? AND end_time > ?",
                        (now, now),
                    ).fetchall()
                ]
                return jsonify(
                    base["available"] and check_rules(avail_ids)["rules_pass"]
                )
            return jsonify(base["available"])
    except:
        return jsonify({"error": "DB error"}), 500


@app.route("/appliances/<name>/duration")
def app_dur(name):
    try:
        now = datetime.now()
        with get_db() as conn:
            app = conn.execute(
                "SELECT id FROM appliance WHERE name = ?", (name,)
            ).fetchone()
            if not app:
                return jsonify({"error": "Not found"}), 404
            base = get_availability(app["id"], "appliance_availability", now)
            if name == "P22P6":
                avail_ids = [
                    r[0]
                    for r in conn.execute(
                        "SELECT crew_id FROM crew_availability WHERE start_time <= ? AND end_time > ?",
                        (now, now),
                    ).fetchall()
                ]
                if not (base["available"] and check_rules(avail_ids)["rules_pass"]):
                    return jsonify(None)
            return jsonify(base["duration"])
    except:
        return jsonify({"error": "DB error"}), 500


@app.route("/station/now")
def station_now():
    try:
        html = fetch_station_feed_html(None)
        data = parse_station_feed_html(html) if html else None
        return jsonify(data) if data else (jsonify({"error": "Failed"}), 500)
    except:
        return jsonify({"error": "DB error"}), 500


# --- Compatibility Helpers for Tests ---
def get_crew_list_data():
    return get_crew_list()


def get_crew_available_data(id):
    return get_availability(id, "crew_availability", datetime.now())


def get_crew_duration_data(id):
    return get_availability(id, "crew_availability", datetime.now())


def get_appliance_available_data(name):
    now = datetime.now()
    with get_db() as conn:
        app = conn.execute(
            "SELECT id FROM appliance WHERE name = ?", (name,)
        ).fetchone()
        if not app:
            return {"error": "Not found"}
        base = get_availability(app["id"], "appliance_availability", now)
        if name == "P22P6":
            avail_ids = [
                r[0]
                for r in conn.execute(
                    "SELECT crew_id FROM crew_availability WHERE start_time <= ? AND end_time > ?",
                    (now, now),
                ).fetchall()
            ]
            return {
                "available": base["available"] and check_rules(avail_ids)["rules_pass"]
            }
        return {"available": base["available"]}


def get_appliance_duration_data(name):
    now = datetime.now()
    with get_db() as conn:
        app = conn.execute(
            "SELECT id FROM appliance WHERE name = ?", (name,)
        ).fetchone()
        if not app:
            return {"error": "Not found"}
        return get_availability(app["id"], "appliance_availability", now)


def get_crew_hours_this_week_data(id):
    return get_weekly_stats(id)


def get_crew_hours_planned_week_data(id):
    return get_weekly_stats(id)


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "object-src 'none'; frame-ancestors 'none'; base-uri 'self'; "
        "form-action 'self'; img-src 'self' data:"
    )
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gartan Scraper Bot - Dashboard</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="container">
        <h1>Managing Station: P22</h1>
        <div class="timestamp">Updated: {{ now.strftime('%H:%M:%S on %d/%m/%Y') }}</div>

        <div class="summary-stats">
            <div class="stat"><div class="stat-number">{{ total_available }}</div><div class="stat-label">Crew</div></div>
            <div class="stat"><div class="stat-number">{{ skill_counts.TTR }}</div><div class="stat-label">Officer</div></div>
            <div class="stat"><div class="stat-number">{{ skill_counts.LGV }}</div><div class="stat-label">Driver</div></div>
            <div class="stat"><div class="stat-number">{{ skill_counts.BA }}</div><div class="stat-label">BA</div></div>
        </div>

        <div class="appliance-section">
            <h2>🚒 P22P6 Status</h2>
            <div class="appliance-status {{ 'operational' if p22p6_avail else 'unavailable' }}">
                {{ 'OPERATIONAL' if p22p6_avail else 'NOT AVAILABLE' }}
            </div>
            {% if p22p6_duration %}<div>Available for: {{ p22p6_duration }}</div>{% endif %}

            <div class="business-rules">
                <div class="rule {{ 'pass' if rules.total_crew_ok else 'fail' }}">Min Crew (≥4): {{ 'PASS' if rules.total_crew_ok else 'FAIL' }}</div>
                <div class="rule {{ 'pass' if rules.ttr_present else 'fail' }}">Officer: {{ 'PASS' if rules.ttr_present else 'FAIL' }}</div>
                <div class="rule {{ 'pass' if rules.lgv_present else 'fail' }}">Driver: {{ 'PASS' if rules.lgv_present else 'FAIL' }}</div>
            </div>
        </div>

        <div class="section">
            <h2>Individual Crew</h2>
            <div class="grid">
                {% for crew in crew_data %}
                <div class="card {{ 'available' if crew.available else 'unavailable' }}">
                    <div class="crew-name">{{ crew.name }}</div>
                    <div class="crew-details">
                        <strong>Role:</strong> {{ crew.role }} | <strong>Skills:</strong> {{ crew.skills }}<br>
                        <strong>Status:</strong> {{ 'AVAILABLE' if crew.available else 'OFF' }}<br>
                        {% if crew.available and crew.duration %}<strong>Until:</strong> {{ crew.end_time_display }}<br>{% endif %}
                        <strong>Contract:</strong> {{ crew.contract_hours }}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    # Prevent running the development server in production
    if os.environ.get("FLASK_ENV") == "production":
        logger.error("Flask development server should not be used in production.")
        print("Error: Flask development server should not be used in production.")
        import sys
        sys.exit(1)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
