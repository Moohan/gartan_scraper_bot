import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta

# Add root to sys.path
sys.path.insert(0, ".")

import api_server
from api_server import app


def setup_benchmark_db():
    fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(temp_path)
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

    # Insert 50 crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    for i in range(50):
        name = f"CREW_{i:02d}"
        role = roles[i % len(roles)]
        skills = "BA"
        if i % 3 == 0:
            skills += " TTR"
        if i % 4 == 0:
            skills += " LGV"
        c.execute(
            "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
            (name, role, skills, "42h"),
        )

        # Make them all available now
        now = datetime.now()
        end = now + timedelta(hours=8)
        c.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            (i + 1, now, end),
        )

    # Insert appliance
    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)",
        (datetime.now(), datetime.now() + timedelta(hours=8)),
    )

    conn.commit()
    conn.close()
    return temp_path


def run_benchmark(db_path, iterations=50):
    api_server.DB_PATH = db_path
    app.config["TESTING"] = True
    client = app.test_client()

    # Warmup
    client.get("/")

    start_total = time.perf_counter()
    latencies = []

    for _ in range(iterations):
        start = time.perf_counter()
        client.get("/")
        latencies.append(time.perf_counter() - start)

    end_total = time.perf_counter()

    avg_ms = (sum(latencies) / iterations) * 1000
    print(f"Benchmark finished: {iterations} iterations")
    print(f"Average latency: {avg_ms:.2f} ms")
    return avg_ms


if __name__ == "__main__":
    db_path = setup_benchmark_db()
    try:
        run_benchmark(db_path)
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
