import time
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
import sys

# Add root to sys.path
sys.path.insert(0, ".")

import api_server
from api_server import app

def setup_benchmark_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    # Patch DB_PATH in api_server
    api_server.DB_PATH = path

    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute("CREATE TABLE crew (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, role TEXT, skills TEXT, contract_hours TEXT)")
    c.execute("CREATE TABLE crew_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, crew_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)")
    c.execute("CREATE TABLE appliance (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)")
    c.execute("CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, appliance_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)")

    # Insert 50 crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    now = datetime.now()
    for i in range(50):
        name = f"CREW_{i}"
        role = roles[i % len(roles)]
        c.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
                  (name, role, "BA LGV TTR", "42h"))
        crew_id = c.lastrowid
        # Half are available
        if i % 2 == 0:
            # Current availability
            c.execute("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                      (crew_id, now - timedelta(hours=1), now + timedelta(hours=8)))
            # Add some noise (expired availability)
            c.execute("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                      (crew_id, now - timedelta(hours=10), now - timedelta(hours=2)))

    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    c.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)",
              (now - timedelta(hours=1), now + timedelta(hours=8)))

    conn.commit()
    conn.close()
    return path

def run_benchmark(iterations=100):
    app.config["TESTING"] = True
    client = app.test_client()
    latencies = []

    # Warmup
    client.get("/")

    for _ in range(iterations):
        start = time.perf_counter()
        res = client.get("/")
        end = time.perf_counter()
        if res.status_code == 200:
            latencies.append((end - start) * 1000)
        else:
            print(f"Error: {res.status_code}")
            print(res.data)

    if not latencies:
        print("No successful requests.")
        return 0

    avg = sum(latencies) / len(latencies)
    print(f"Average latency over {len(latencies)} iterations: {avg:.2f}ms")
    return avg

if __name__ == "__main__":
    db_path = setup_benchmark_db()
    try:
        run_benchmark()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
