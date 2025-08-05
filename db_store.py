CREW_DETAILS_TABLE = """
CREATE TABLE IF NOT EXISTS crew (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    role TEXT,
    contact TEXT,
    skills TEXT
);
"""

APPLIANCE_META_TABLE = """
CREATE TABLE IF NOT EXISTS appliance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
"""
import sqlite3
from typing import List, Dict, Any

DB_PATH = "gartan_availability.db"

CREW_TABLE = """
CREATE TABLE IF NOT EXISTS crew_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crew_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    available INTEGER NOT NULL,
    next_available TEXT,
    next_available_until TEXT,
    available_for TEXT,
    FOREIGN KEY (crew_id) REFERENCES crew(id)
);
"""

APPLIANCE_TABLE = """
CREATE TABLE IF NOT EXISTS appliance_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appliance_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    available INTEGER NOT NULL,
    available_now INTEGER,
    next_available TEXT,
    next_available_until TEXT,
    available_for TEXT,
    FOREIGN KEY (appliance_id) REFERENCES appliance(id)
);
"""


def init_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(CREW_DETAILS_TABLE)
    c.execute(APPLIANCE_META_TABLE)
    c.execute(CREW_TABLE)
    c.execute(APPLIANCE_TABLE)
    conn.commit()
    return conn


def insert_crew_details(crew_list: list, contact_map: dict = None, db_path=DB_PATH):
    """
    Insert or update crew details (name, role, contact) into crew table.
    crew_list: list of dicts with 'name' and 'role' keys
    contact_map: dict mapping name to contact info
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    for crew in crew_list:
        name = crew.get("name")
        role = crew.get("role")
        skills = crew.get("skills")
        contact = None
        if contact_map and name in contact_map:
            contact = contact_map[name]
        # Insert or update
        c.execute(
            """
            INSERT INTO crew (name, role, contact, skills) VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET role=excluded.role, contact=excluded.contact, skills=excluded.skills
            """,
            (name, role, contact, skills),
        )
    conn.commit()
    conn.close()


def insert_crew_availability(crew_list: List[Dict[str, Any]], db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    for crew in crew_list:
        name = crew["name"]
        # Get crew_id
        c.execute("SELECT id FROM crew WHERE name=?", (name,))
        row = c.fetchone()
        if not row:
            continue
        crew_id = row[0]
        availability = crew["availability"]
        next_available = crew.get("next_available")
        next_available_until = crew.get("next_available_until")
        available_for = crew.get("available_for")
        for dt_key, available in availability.items():
            date, time = dt_key.split()
            c.execute(
                """
                INSERT INTO crew_availability (crew_id, date, time, available, next_available, next_available_until, available_for)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    crew_id,
                    date,
                    time,
                    int(available),
                    next_available,
                    next_available_until,
                    available_for,
                ),
            )
    conn.commit()
    conn.close()


def insert_appliance_availability(appliance_obj: Dict[str, Any], db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    for appliance, info in appliance_obj.items():
        # Insert appliance if not exists
        c.execute("INSERT OR IGNORE INTO appliance (name) VALUES (?)", (appliance,))
        c.execute("SELECT id FROM appliance WHERE name=?", (appliance,))
        row = c.fetchone()
        if not row:
            continue
        appliance_id = row[0]
        availability = info["availability"]
        available_now = int(info.get("available_now", False))
        next_available = info.get("next_available")
        next_available_until = info.get("next_available_until")
        available_for = info.get("available_for")
        for dt_key, available in availability.items():
            date, time = dt_key.split()
            c.execute(
                """
                INSERT INTO appliance_availability (appliance_id, date, time, available, available_now, next_available, next_available_until, available_for)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    appliance_id,
                    date,
                    time,
                    int(available),
                    available_now,
                    next_available,
                    next_available_until,
                    available_for,
                ),
            )
    conn.commit()
    conn.close()
