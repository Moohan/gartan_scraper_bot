import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta

# Add root to path
sys.path.insert(0, ".")

import api_server
from api_server import DB_PATH, app


def setup_dummy_db(db_path, num_crew=50):
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
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

    now = datetime.now()
    future = now + timedelta(hours=8)

    crew_data = []
    for i in range(num_crew):
        name = f"CREW, Member {i}"
        role = "FFC" if i % 5 == 0 else "FFD"
        skills = "BA TTR LGV" if i % 10 == 0 else "BA"
        c.execute(
            "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
            (name, role, skills, "42h"),
        )
        crew_id = c.lastrowid

        # Make half available
        if i % 2 == 0:
            c.execute(
                "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                (crew_id, now.isoformat(), future.isoformat()),
            )

    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    app_id = c.lastrowid
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
        (app_id, now.isoformat(), future.isoformat()),
    )

    conn.commit()
    conn.close()


def benchmark_root(iterations=10):
    client = app.test_client()

    # Warm up
    client.get("/")

    start_time = time.time()
    for _ in range(iterations):
        client.get("/")
    end_time = time.time()

    avg_time = (end_time - start_time) / iterations
    print(f"Average time for /: {avg_time:.4f}s")
    return avg_time


if __name__ == "__main__":
    TEST_DB = "benchmark_test.db"
    api_server.DB_PATH = TEST_DB
    setup_dummy_db(TEST_DB, num_crew=50)

    try:
        benchmark_root()
    finally:
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
