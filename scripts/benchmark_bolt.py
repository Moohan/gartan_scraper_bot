import os
import sqlite3
import statistics
import sys
import time
from datetime import datetime, timedelta

# Mocking parts of api_server to work with our test DB
import api_server


def setup_benchmark_db(db_path):
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

    # Insert 50 crew members
    crew_data = []
    for i in range(50):
        crew_data.append((i, f"Crew {i}", "FFC", "BA", "42"))
    c.executemany("INSERT INTO crew VALUES (?, ?, ?, ?, ?)", crew_data)

    # Insert availability for all crew members
    now = datetime.now()
    future = now + timedelta(hours=8)
    avail_data = []
    for i in range(50):
        avail_data.append((i, i, now, future))
    c.executemany("INSERT INTO crew_availability VALUES (?, ?, ?, ?)", avail_data)

    # Insert appliance
    c.execute("INSERT INTO appliance VALUES (1, 'P22P6')")
    c.execute("INSERT INTO appliance_availability VALUES (1, 1, ?, ?)", (now, future))

    conn.commit()
    conn.close()


def benchmark_root(db_path, iterations=100):
    api_server.DB_PATH = db_path

    # Warm up
    with api_server.app.test_client() as client:
        client.get("/")

    latencies = []
    for _ in range(iterations):
        start_time = time.perf_counter()
        with api_server.app.test_client() as client:
            client.get("/")
        end_time = time.perf_counter()
        latencies.append((end_time - start_time) * 1000)

    return latencies


if __name__ == "__main__":
    db_path = "benchmark.db"
    setup_benchmark_db(db_path)

    print(f"Benchmarking root endpoint with 50 crew members...")
    latencies = benchmark_root(db_path)

    print(f"Average latency: {statistics.mean(latencies):.2f} ms")
    print(f"Median latency: {statistics.median(latencies):.2f} ms")
    print(f"95th percentile: {statistics.quantiles(latencies, n=20)[18]:.2f} ms")

    if os.path.exists(db_path):
        os.remove(db_path)
