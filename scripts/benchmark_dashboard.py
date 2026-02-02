import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta

# Add current directory to path so we can import api_server
sys.path.insert(0, ".")
import api_server


def setup_benchmark_db(db_path, num_crew=50):
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
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

    now = datetime.now()
    future = now + timedelta(hours=8)

    crew_data = []
    avail_data = []
    for i in range(1, num_crew + 1):
        # Using comma in name to match real data patterns
        crew_data.append((i, f"CREW, Member {i}", "FFC", "BA LGV TTR", "42h"))
        # Make all of them available
        avail_data.append((i, i, now.isoformat(), future.isoformat()))

    c.executemany("INSERT INTO crew VALUES (?, ?, ?, ?, ?)", crew_data)
    c.executemany("INSERT INTO crew_availability VALUES (?, ?, ?, ?)", avail_data)

    c.execute("INSERT INTO appliance VALUES (1, 'P22P6')")
    c.execute(
        "INSERT INTO appliance_availability VALUES (1, 1, ?, ?)",
        (now.isoformat(), future.isoformat()),
    )

    conn.commit()
    conn.close()


def run_benchmark(num_runs=20):
    api_server.DB_PATH = "benchmark.db"
    setup_benchmark_db(api_server.DB_PATH)

    app = api_server.app
    app.config["TESTING"] = True
    client = app.test_client()

    # Warm up
    client.get("/")

    start_time = time.time()
    for _ in range(num_runs):
        client.get("/")
    end_time = time.time()

    avg_time = (end_time - start_time) / num_runs
    print(f"Average time for dashboard (50 crew members): {avg_time:.4f}s")

    if os.path.exists("benchmark.db"):
        os.remove("benchmark.db")


if __name__ == "__main__":
    run_benchmark()
