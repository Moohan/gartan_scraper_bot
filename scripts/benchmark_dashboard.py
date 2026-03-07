import time
import sqlite3
import os
import tempfile
import sys
from datetime import datetime, timedelta

# Ensure we can import api_server
sys.path.insert(0, ".")

import api_server
from api_server import app

def setup_benchmark_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute("CREATE TABLE crew (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, role TEXT, skills TEXT, contract_hours TEXT)")
    c.execute("CREATE TABLE crew_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, crew_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)")
    c.execute("CREATE TABLE appliance (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)")
    c.execute("CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, appliance_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)")

    # Insert 50 crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    skills_list = ["BA", "LGV", "TTR", "BA LGV", "BA TTR", "LGV TTR", "BA LGV TTR"]

    now = datetime.now()
    future = now + timedelta(hours=8)

    for i in range(50):
        name = f"CREW_{i}"
        role = roles[i % len(roles)]
        skills = skills_list[i % len(skills_list)]
        c.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
                  (name, role, skills, "42h"))
        crew_id = c.lastrowid

        # Make most of them available
        if i % 5 != 0:
            c.execute("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                      (crew_id, now.isoformat(), future.isoformat()))

    # Add P22P6 appliance
    c.execute("INSERT INTO appliance (name) VALUES (?)", ("P22P6",))
    app_id = c.lastrowid
    c.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
              (app_id, now.isoformat(), future.isoformat()))

    conn.commit()
    conn.close()
    return path

def run_benchmark(db_path, iterations=10):
    api_server.DB_PATH = db_path
    app.config["TESTING"] = True
    client = app.test_client()

    print(f"Running benchmark with {iterations} iterations...")
    latencies = []

    # Warm up
    client.get("/")

    for i in range(iterations):
        start_time = time.perf_counter()
        res = client.get("/")
        end_time = time.perf_counter()
        latencies.append(end_time - start_time)
        if res.status_code != 200:
            print(f"Iteration {i} failed with status {res.status_code}")

    avg_latency = sum(latencies) / len(latencies)
    print(f"Average latency: {avg_latency*1000:.2f}ms")
    return avg_latency

if __name__ == "__main__":
    db_path = setup_benchmark_db()
    try:
        run_benchmark(db_path)
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
