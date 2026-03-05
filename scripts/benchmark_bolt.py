import time
import os
import sqlite3
from datetime import datetime, timedelta
import api_server
from api_server import app

def setup_benchmark_db(db_path):
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.executescript("""
    CREATE TABLE crew (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        role TEXT,
        skills TEXT,
        contract_hours TEXT
    );
    CREATE TABLE crew_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crew_id INTEGER NOT NULL,
        start_time DATETIME NOT NULL,
        end_time DATETIME NOT NULL,
        FOREIGN KEY (crew_id) REFERENCES crew(id)
    );
    CREATE TABLE appliance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    CREATE TABLE appliance_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appliance_id INTEGER NOT NULL,
        start_time DATETIME NOT NULL,
        end_time DATETIME NOT NULL,
        FOREIGN KEY (appliance_id) REFERENCES appliance(id)
    );
    """)

    # Insert 50 crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    now = datetime.now()
    start_time = now - timedelta(hours=1)
    end_time = now + timedelta(hours=4)

    for i in range(50):
        name = f"Crew Member {i}"
        role = roles[i % len(roles)]
        conn.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
                     (name, role, "BA TTR LGV", "42 hours"))
        crew_id = i + 1
        # Make all of them available
        conn.execute("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                     (crew_id, start_time.isoformat(), end_time.isoformat()))

    conn.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    conn.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)",
                 (start_time.isoformat(), end_time.isoformat()))

    conn.commit()
    conn.close()

def run_benchmark():
    db_path = "benchmark.db"
    setup_benchmark_db(db_path)

    # Override DB_PATH in api_server
    api_server.DB_PATH = db_path

    client = app.test_client()

    # Warm up and verify
    resp = client.get("/")
    if resp.status_code != 200:
        print(f"Error during warm-up: {resp.status_code}")
        print(resp.data.decode())
        return

    iterations = 50
    start_time = time.time()
    for _ in range(iterations):
        client.get("/")
    end_time = time.time()

    avg_latency = (end_time - start_time) / iterations * 1000
    print(f"Average latency for / over {iterations} requests: {avg_latency:.2f}ms")

    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    run_benchmark()
