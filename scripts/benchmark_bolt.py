import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta

# Add root to sys.path
sys.path.append(os.getcwd())

from api_server import DB_PATH, app


def setup_test_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE crew (id INTEGER PRIMARY KEY, name TEXT, role TEXT, skills TEXT, contract_hours TEXT)"
    )
    c.execute(
        "CREATE TABLE crew_availability (id INTEGER PRIMARY KEY, crew_id INTEGER, start_time DATETIME, end_time DATETIME)"
    )
    c.execute("CREATE TABLE appliance (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute(
        "CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY, appliance_id INTEGER, start_time DATETIME, end_time DATETIME)"
    )

    # Insert 50 crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    now = datetime.now()
    future = now + timedelta(hours=8)

    for i in range(1, 51):
        role = roles[i % len(roles)]
        skills = "BA"
        if i % 3 == 0:
            skills += " LGV"
        if i % 5 == 0:
            skills += " TTR"

        c.execute(
            "INSERT INTO crew VALUES (?, ?, ?, ?, ?)",
            (i, f"Crew {i}", role, skills, "42h"),
        )
        # Make all available
        c.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            (i, now, future),
        )

    c.execute("INSERT INTO appliance VALUES (1, 'P22P6')")
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)",
        (now, future),
    )

    conn.commit()
    conn.close()


def run_benchmark():
    client = app.test_client()

    # Warmup
    client.get("/")

    iterations = 100
    start_time = time.time()
    for _ in range(iterations):
        client.get("/")
    end_time = time.time()

    avg_time = (end_time - start_time) / iterations * 1000
    print(f"Average response time: {avg_time:.2f}ms")


if __name__ == "__main__":
    setup_test_db()
    run_benchmark()
