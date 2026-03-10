import os
import sqlite3
import time
from datetime import datetime, timedelta

import api_server
from api_server import DB_PATH, app


def setup_dummy_data():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE crew (id INTEGER PRIMARY KEY, name TEXT, role TEXT, skills TEXT, contract_hours TEXT)"
    )
    conn.execute(
        "CREATE TABLE crew_availability (id INTEGER PRIMARY KEY, crew_id INTEGER, start_time DATETIME, end_time DATETIME)"
    )
    conn.execute("CREATE TABLE appliance (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute(
        "CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY, appliance_id INTEGER, start_time DATETIME, end_time DATETIME)"
    )

    # Insert 50 crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    for i in range(1, 51):
        name = f"Crew {i}"
        role = roles[i % len(roles)]
        skills = "TTR LGV BA" if i % 2 == 0 else "BA"
        conn.execute(
            "INSERT INTO crew (id, name, role, skills, contract_hours) VALUES (?, ?, ?, ?, ?)",
            (i, name, role, skills, "40h"),
        )

    # Make half of them available
    now = datetime.now()
    start = now - timedelta(hours=1)
    end = now + timedelta(hours=4)
    # Format as ISO strings since that's what's registered with sqlite3 adapters in api_server
    start_iso = start.isoformat()
    end_iso = end.isoformat()

    for i in range(1, 26):
        conn.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            (i, start_iso, end_iso),
        )

    conn.execute("INSERT INTO appliance (id, name) VALUES (1, 'P22P6')")
    conn.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)",
        (start_iso, end_iso),
    )

    conn.commit()
    conn.close()


def benchmark():
    client = app.test_client()

    # Warm up and check if it's working
    resp = client.get("/")
    if resp.status_code != 200:
        print(f"Error during warm up: {resp.status_code}")
        print(resp.get_data(as_text=True))
        return

    start_time = time.time()
    iterations = 50
    for _ in range(iterations):
        client.get("/")
    end_time = time.time()

    avg_time = (end_time - start_time) / iterations
    print(f"Average time for dashboard (root): {avg_time*1000:.2f}ms")


if __name__ == "__main__":
    setup_dummy_data()
    benchmark()
