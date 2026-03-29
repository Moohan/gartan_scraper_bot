import os
import sqlite3
import statistics
import time
from datetime import datetime, timedelta

from api_server import app
from db_store import init_db

DB_PATH = "benchmark.db"


def setup_benchmark_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = init_db(DB_PATH)
    c = conn.cursor()

    # Insert 50 crew members
    crew_data = []
    for i in range(50):
        crew_data.append((f"Crew Member {i}", "FFD", "BA LGV", "42 hours"))

    c.executemany(
        "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
        crew_data,
    )

    # Get IDs
    c.execute("SELECT id FROM crew")
    crew_ids = [r[0] for r in c.fetchall()]

    # Insert availability for today
    now = datetime.now()
    start_time = now - timedelta(hours=1)
    end_time = now + timedelta(hours=4)

    avail_data = []
    for cid in crew_ids:
        avail_data.append((cid, start_time, end_time))

    c.executemany(
        "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
        avail_data,
    )

    # Appliance
    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    c.execute("SELECT id FROM appliance WHERE name = 'P22P6'")
    app_id = c.fetchone()[0]
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
        (app_id, start_time, end_time),
    )

    conn.commit()
    conn.close()


def benchmark():
    os.environ["DATABASE_URL"] = (
        DB_PATH  # This won't work as api_server uses config.db_path
    )
    # We need to monkeypatch config or api_server.DB_PATH
    import api_server

    api_server.DB_PATH = DB_PATH

    setup_benchmark_db()

    client = app.test_client()
    latencies = []

    # Warm up
    for _ in range(5):
        client.get("/")

    for _ in range(100):
        start = time.perf_counter()
        res = client.get("/")
        end = time.perf_counter()
        if res.status_code != 200:
            print(f"Error: {res.status_code}")
            # print(res.data.decode())
        latencies.append(end - start)

    avg = statistics.mean(latencies)
    median = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18]
    print(f"Benchmark results for 50 crew members:")
    print(f"Average latency: {avg*1000:.2f}ms")
    print(f"Median latency: {median*1000:.2f}ms")
    print(f"95th percentile: {p95*1000:.2f}ms")

    os.remove(DB_PATH)


if __name__ == "__main__":
    benchmark()
