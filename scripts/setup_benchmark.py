import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "benchmark.db"


def setup():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create tables
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

    # Create indexes
    c.execute(
        "CREATE INDEX idx_crew_availability_crew_times ON crew_availability(crew_id, start_time, end_time)"
    )

    # Insert crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    crew_data = []
    for i in range(100):
        name = f"CREW, {i}"
        role = roles[i % len(roles)]
        skills = "BA"
        if i % 3 == 0:
            skills += " LGV"
        if i % 4 == 0:
            skills += " TTR"
        crew_data.append((name, role, skills, "42h"))

    c.executemany(
        "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
        crew_data,
    )

    # Insert availability for some crew
    now = datetime.now()
    avail_data = []
    for i in range(1, 61):  # First 60 are available
        start = now - timedelta(hours=2)
        end = now + timedelta(hours=6)
        avail_data.append((i, start.isoformat(), end.isoformat()))

    c.executemany(
        "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
        avail_data,
    )

    # Insert appliance
    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)",
        (
            (now - timedelta(hours=2)).isoformat(),
            (now + timedelta(hours=6)).isoformat(),
        ),
    )

    conn.commit()
    conn.close()
    print(f"Benchmark database created at {DB_PATH}")


if __name__ == "__main__":
    setup()
