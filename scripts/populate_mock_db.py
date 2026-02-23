import os
import sqlite3
from datetime import datetime, timedelta

from config import config

DB_PATH = config.db_path


def populate():
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE crew (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        role TEXT,
        skills TEXT,
        contract_hours TEXT
    );
    """)

    c.execute("""
    CREATE TABLE appliance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    """)

    c.execute("""
    CREATE TABLE crew_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crew_id INTEGER NOT NULL,
        start_time DATETIME NOT NULL,
        end_time DATETIME NOT NULL,
        FOREIGN KEY (crew_id) REFERENCES crew(id)
    );
    """)

    c.execute("""
    CREATE TABLE appliance_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appliance_id INTEGER NOT NULL,
        start_time DATETIME NOT NULL,
        end_time DATETIME NOT NULL,
        FOREIGN KEY (appliance_id) REFERENCES appliance(id)
    );
    """)

    # Add 50 crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    for i in range(50):
        name = f"Crew Member {i:02d}"
        role = roles[i % len(roles)]
        skills = "BA TTR LGV" if i % 4 == 0 else "BA TTR"
        c.execute(
            "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
            (name, role, skills, "42 hours"),
        )

        crew_id = c.lastrowid
        # Available now until tomorrow
        now = datetime.now()
        start = now - timedelta(hours=2)
        end = now + timedelta(hours=6)
        c.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            (crew_id, start.isoformat(), end.isoformat()),
        )

    # Add appliance
    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    app_id = c.lastrowid
    now = datetime.now()
    start = now - timedelta(hours=2)
    end = now + timedelta(hours=6)
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
        (app_id, start.isoformat(), end.isoformat()),
    )

    conn.commit()
    conn.close()
    print(f"Mock DB populated at {DB_PATH}")


if __name__ == "__main__":
    populate()
