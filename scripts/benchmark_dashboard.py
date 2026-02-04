import time
import os
import sqlite3
from datetime import datetime, timedelta
from api_server import app
from db_store import init_db

DB_PATH = "benchmark.db"

def setup_benchmark_data():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = init_db(db_path=DB_PATH)
    c = conn.cursor()

    # Insert 50 crew members
    crew_data = []
    for i in range(50):
        name = f"Crew Member {i}"
        role = ["WC", "CM", "CC", "FFC", "FFD", "FFT"][i % 6]
        skills = "TTR LGV BA" if i % 4 == 0 else "BA"
        contract_hours = "42.0h"
        crew_data.append((name, role, skills, contract_hours))

    c.executemany(
        "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
        crew_data
    )

    # Get all crew IDs
    c.execute("SELECT id FROM crew")
    crew_ids = [row[0] for row in c.fetchall()]

    # Insert availability for everyone (currently available)
    now = datetime.now()
    start_time = now - timedelta(hours=2)
    end_time = now + timedelta(hours=4)

    availability_data = []
    for cid in crew_ids:
        availability_data.append((cid, start_time, end_time))

    c.executemany(
        "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
        availability_data
    )

    # Insert P22P6 appliance
    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    appliance_id = c.lastrowid
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
        (appliance_id, start_time, end_time)
    )

    conn.commit()
    conn.close()

def benchmark():
    app.config['TESTING'] = True
    # Point api_server to our benchmark DB
    import api_server
    api_server.DB_PATH = DB_PATH

    client = app.test_client()

    # Warm up
    client.get('/')

    start = time.time()
    iterations = 10
    for _ in range(iterations):
        client.get('/')
    end = time.time()

    avg_time = (end - start) / iterations
    print(f"Average response time for dashboard (50 crew members): {avg_time:.4f}s")

if __name__ == "__main__":
    setup_benchmark_data()
benchmark()
