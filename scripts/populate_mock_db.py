import os
import sqlite3
import sys
from datetime import datetime, timedelta

# Add the root directory to the python path so we can import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import config

# Set DB_PATH to benchmark.db for performance testing
DB_PATH = "benchmark.db"


def populate():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
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

    # Add 50 crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    skills_list = ["BA", "BA LGV", "BA TTR", "LGV", "TTR"]

    now = datetime.now()
    future = now + timedelta(hours=8)

    for i in range(1, 51):
        name = f"CREW_MEMBER_{i}"
        role = roles[i % len(roles)]
        skills = skills_list[i % len(skills_list)]
        c.execute(
            "INSERT INTO crew (id, name, role, skills, contract_hours) VALUES (?, ?, ?, ?, ?)",
            (i, name, role, skills, "42h"),
        )

        # Everyone is available now
        c.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            (i, now.isoformat(), future.isoformat()),
        )

    # Add appliance P22P6
    c.execute("INSERT INTO appliance (id, name) VALUES (1, 'P22P6')")
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)",
        (now.isoformat(), future.isoformat()),
    )

    conn.commit()
    conn.close()
    print(f"Populated {DB_PATH} with 50 crew members and 1 appliance.")


if __name__ == "__main__":
    populate()
