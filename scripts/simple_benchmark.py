import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, ".")

import api_server
from api_server import app


def setup_benchmark_db(db_path, num_crew=50):
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

    # Insert crew
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    skills_list = ["BA", "LGV", "TTR", "IC", "ERD"]

    now = datetime.now()
    future = now + timedelta(hours=8)

    crew_data = []
    for i in range(num_crew):
        name = f"CREW, {i}"
        role = roles[i % len(roles)]
        s = skills_list[i % len(skills_list)]
        crew_data.append((i + 1, name, role, s, "42h"))

    c.executemany("INSERT INTO crew VALUES (?, ?, ?, ?, ?)", crew_data)

    # Insert availability for half of them
    avail_data = []
    for i in range(0, num_crew, 2):
        avail_data.append((i + 1, now, future))

    c.executemany(
        "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
        avail_data,
    )

    # Insert appliance
    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)",
        (now, future),
    )

    conn.commit()
    conn.close()


def run_benchmark():
    db_path = "benchmark.db"
    setup_benchmark_db(db_path)
    api_server.DB_PATH = db_path

    client = app.test_client()

    # Warmup
    client.get("/")

    print("Running benchmark (100 iterations)...")
    start_time = time.time()
    iterations = 100
    for _ in range(iterations):
        client.get("/")
    end_time = time.time()

    avg_time = (end_time - start_time) / iterations
    print(f"Average time for /: {avg_time*1000:.2f}ms")

    if os.path.exists(db_path):
        os.remove(db_path)


if __name__ == "__main__":
    run_benchmark()
